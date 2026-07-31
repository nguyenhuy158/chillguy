"""Full-screen Textual UI for the chillguy player.

Reuses the existing `Player` (mpv/JSON-IPC) and `search.get_stream_url` — no
new playback or IPC plumbing is introduced here, this module is purely a
presentation layer on top of what `player.py`/`search.py` already expose.

Launched via `chillguy play <query> --ui` or `chillguy ui <query>`. Requires
the optional `textual` dependency: install with `pip install 'chillguy[tui]'`.
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, Static

from .player import Player
from .search import get_stream_url
from .utils import logger

POLL_SECONDS = 0.5


def format_duration(seconds) -> str:
    """Format a seconds value (int/float) as MM:SS, tolerating None/junk."""
    if seconds is None:
        return "--:--"
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return "--:--"
    if seconds < 0:
        return "--:--"
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


def track_duration_label(track: dict) -> str:
    """Best-effort duration label for a track dict from search/queue data."""
    duration = track.get("duration_string") or track.get("duration")
    if isinstance(duration, (int, float)):
        return format_duration(duration)
    if isinstance(duration, str) and duration:
        return duration
    return "--:--"


class ChillguyTUI(App):
    """Full-screen playlist + now-playing view driving an existing Player."""

    TITLE = "chillguy"

    CSS = """
    #now-playing {
        height: auto;
        border: round $accent;
        padding: 0 1;
        margin-bottom: 1;
    }
    #playlist {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("enter", "play_selected", "Play"),
        Binding("space", "toggle_pause", "Play/Pause"),
        Binding("n", "next_track", "Next"),
        Binding("b", "prev_track", "Prev"),
        Binding("p", "prev_track", "Prev", show=False),
        Binding("q", "quit_app", "Quit"),
    ]

    def __init__(self, player: Player) -> None:
        super().__init__()
        self.player = player
        self._ended_handled = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Nothing playing", id="now-playing")
        yield DataTable(id="playlist")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#playlist", DataTable)
        table.cursor_type = "row"
        table.add_columns(" ", "Title", "Duration")
        self.refresh_playlist()

        if self.player.process is not None:
            # mpv already running (e.g. launched mid-queue); just reflect
            # state, don't restart playback.
            self._ended_handled = False
        elif self.player.queue:
            self._start_track(max(self.player.current_index, 0))

        self.set_interval(POLL_SECONDS, self.poll_status)

    # ------------------------------------------------------------ playlist

    def refresh_playlist(self) -> None:
        table = self.query_one("#playlist", DataTable)
        table.clear()
        for i, track in enumerate(self.player.queue):
            marker = "▶" if i == self.player.current_index else ""
            title = str(track.get("title", "Unknown"))
            table.add_row(marker, title, track_duration_label(track), key=str(i))

    def _selected_index(self) -> int | None:
        table = self.query_one("#playlist", DataTable)
        row = table.cursor_row
        if row is None or not (0 <= row < len(self.player.queue)):
            return None
        return row

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        # DataTable owns the "enter" key while focused (bound to its own
        # `select_cursor` action) and consumes it before it can bubble up to
        # an App-level binding, so we hook its RowSelected message directly
        # rather than relying on action_play_selected below.
        if event.data_table.id != "playlist":
            return
        index = event.cursor_row
        if index is not None and 0 <= index < len(self.player.queue):
            self._start_track(index)

    # -------------------------------------------------------------- actions

    def action_play_selected(self) -> None:
        index = self._selected_index()
        if index is not None:
            self._start_track(index)

    def action_toggle_pause(self) -> None:
        self.run_worker(self._toggle_pause_worker, thread=True, group="control")

    def _toggle_pause_worker(self) -> None:
        self.player.toggle_pause()

    def action_next_track(self) -> None:
        index = self.player.current_index + 1
        if index < len(self.player.queue):
            self._start_track(index)
        else:
            self.notify("End of queue", severity="warning")

    def action_prev_track(self) -> None:
        if not self.player.queue:
            return
        index = max(0, self.player.current_index - 1)
        self._start_track(index)

    def action_quit_app(self) -> None:
        self.run_worker(self._quit_worker, thread=True, group="control")

    def _quit_worker(self) -> None:
        try:
            self.player.stop()
        except Exception:
            logger.exception("Error stopping player on quit")
        self.call_from_thread(self.exit)

    # -------------------------------------------------------------- playback

    def _start_track(self, index: int) -> None:
        if not (0 <= index < len(self.player.queue)):
            return
        self.player.current_index = index
        track = self.player.queue[index]
        self._ended_handled = False
        self.refresh_playlist()
        self.query_one("#now-playing", Static).update(f"Loading: {track.get('title', 'Unknown')}...")
        self.run_worker(
            lambda: self._start_track_worker(track),
            thread=True,
            exclusive=True,
            group="playback",
        )

    def _start_track_worker(self, track: dict) -> None:
        ok = False
        try:
            stream_url = get_stream_url(track.get("id") or track.get("url"))
            if stream_url:
                ok = self.player.start(stream_url, track.get("title", "Unknown"))
        except Exception:
            logger.exception("Failed to start track from TUI")
        self.call_from_thread(self._after_start_track, track, ok)

    def _after_start_track(self, track: dict, ok: bool) -> None:
        if not ok:
            self.notify(f"Failed to play: {track.get('title', 'Unknown')}", severity="error")
            return
        self.refresh_playlist()

    # ------------------------------------------------------------- polling

    def poll_status(self) -> None:
        self.run_worker(self._poll_worker, thread=True, exclusive=True, group="poll")

    def _poll_worker(self) -> None:
        pos = self.player.get_property("time-pos")
        dur = self.player.get_property("duration")
        paused = self.player.get_property("pause")
        self.call_from_thread(self._update_now_playing, pos, dur, paused)

    def _update_now_playing(self, pos, dur, paused) -> None:
        track = self.player.current_track
        if track is None:
            self.query_one("#now-playing", Static).update("Nothing playing")
            return

        title = str(track.get("title", "Unknown"))
        if paused is True:
            status = "PAUSED"
        elif paused is False:
            status = "PLAYING"
        else:
            status = "..."

        if pos is None and not dur:
            position = "Loading..."
        else:
            position = f"{format_duration(pos)} / {format_duration(dur)}"

        self.query_one("#now-playing", Static).update(f"{title}  [{status}]  {position}")

        if not self._ended_handled and dur and pos is not None and dur > 0 and pos >= dur - 0.5:
            self._ended_handled = True
            self.action_next_track()
