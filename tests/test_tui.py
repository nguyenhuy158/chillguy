"""Headless smoke tests for the Textual UI.

The mpv/player layer is fully mocked (FakePlayer subclasses Player but
overrides every method that would touch a real mpv process or IPC socket),
and `get_stream_url` is patched so nothing hits the network. These tests must
pass without mpv or network access.
"""

import asyncio
from unittest.mock import patch

import pytest

pytest.importorskip("textual")

from chillguy.player import Player  # noqa: E402
from chillguy.tui import ChillguyTUI, format_duration, track_duration_label  # noqa: E402
from textual.widgets import DataTable  # noqa: E402


class FakePlayer(Player):
    """Player stand-in with no real mpv/IPC interaction."""

    def __init__(self):
        super().__init__()
        self.start_calls = []
        self.stop_called = False
        self.pause_toggled = False
        self._paused = False

    def start(self, url, title="Unknown"):
        self.start_calls.append((url, title))
        return True

    def stop(self):
        self.stop_called = True

    def toggle_pause(self):
        self.pause_toggled = True
        self._paused = not self._paused

    def get_property(self, prop_name):
        return {"time-pos": 1.0, "duration": 100.0, "pause": self._paused}.get(prop_name)


def make_queue():
    return [
        {"id": "abc123", "title": "Track One", "duration": 125},
        {"id": "def456", "title": "Track Two", "duration": 200},
    ]


async def _wait_until(predicate, timeout=2.0, interval=0.05):
    elapsed = 0.0
    while elapsed < timeout:
        if predicate():
            return True
        await asyncio.sleep(interval)
        elapsed += interval
    return predicate()


def test_format_duration():
    assert format_duration(None) == "--:--"
    assert format_duration(65) == "01:05"
    assert format_duration(-1) == "--:--"


def test_track_duration_label():
    assert track_duration_label({"duration": 90}) == "01:30"
    assert track_duration_label({}) == "--:--"


def test_playlist_renders_with_tracks():
    player = FakePlayer()
    for t in make_queue():
        player.add_to_queue(t)

    async def run():
        with patch("chillguy.tui.get_stream_url", return_value="https://stream.example/audio"):
            app = ChillguyTUI(player)
            async with app.run_test() as pilot:
                await pilot.pause()
                table = app.query_one("#playlist", DataTable)
                assert table.row_count == 2

    asyncio.run(run())


def test_enter_plays_selected_track():
    player = FakePlayer()
    for t in make_queue():
        player.add_to_queue(t)

    async def run():
        with patch("chillguy.tui.get_stream_url", return_value="https://stream.example/audio"):
            app = ChillguyTUI(player)
            async with app.run_test() as pilot:
                await pilot.pause()
                table = app.query_one("#playlist", DataTable)
                table.move_cursor(row=1)
                await pilot.press("enter")
                await pilot.pause()
                await _wait_until(lambda: len(player.start_calls) >= 2)
                assert player.start_calls
                assert player.start_calls[-1][1] == "Track Two"

    asyncio.run(run())


def test_autostart_on_launch_mirrors_real_cli_shape():
    # Mirrors how `chillguy ui`/`play --ui` actually hand off to the TUI:
    # _build_queue() populates the queue and sets current_index = 0 *before*
    # mpv ever runs, so player.process is still None at mount time. on_mount
    # must key off `process is None` (mpv not actually running yet), not
    # `current_track is not None` (which is already true here) - otherwise
    # the first track never auto-plays.
    player = FakePlayer()
    for t in make_queue():
        player.add_to_queue(t)
    player.current_index = 0
    assert player.process is None

    async def run():
        with patch("chillguy.tui.get_stream_url", return_value="https://stream.example/audio"):
            app = ChillguyTUI(player)
            async with app.run_test() as pilot:
                await pilot.pause()
                await _wait_until(lambda: player.start_calls)
                assert player.start_calls
                assert player.start_calls[0][1] == "Track One"
                table = app.query_one("#playlist", DataTable)
                assert table.get_row_at(0)[0] == "▶"

    asyncio.run(run())


def test_next_and_prev_track_bindings():
    player = FakePlayer()
    for t in make_queue():
        player.add_to_queue(t)
    player.current_index = 0

    async def run():
        with patch("chillguy.tui.get_stream_url", return_value="https://stream.example/audio"):
            app = ChillguyTUI(player)
            async with app.run_test() as pilot:
                await pilot.pause()
                await _wait_until(lambda: player.start_calls)

                await pilot.press("n")
                await pilot.pause()
                await _wait_until(lambda: player.current_index == 1)
                assert player.current_index == 1

                await pilot.press("b")
                await pilot.pause()
                await _wait_until(lambda: player.current_index == 0)
                assert player.current_index == 0

    asyncio.run(run())


def test_space_toggles_pause():
    player = FakePlayer()
    for t in make_queue():
        player.add_to_queue(t)
    player.current_index = 0

    async def run():
        with patch("chillguy.tui.get_stream_url", return_value="https://stream.example/audio"):
            app = ChillguyTUI(player)
            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press("space")
                await _wait_until(lambda: player.pause_toggled)
                assert player.pause_toggled

    asyncio.run(run())


def test_quit_stops_player_and_exits():
    player = FakePlayer()
    for t in make_queue():
        player.add_to_queue(t)
    player.current_index = 0

    async def run():
        with patch("chillguy.tui.get_stream_url", return_value="https://stream.example/audio"):
            app = ChillguyTUI(player)
            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press("q")
                await _wait_until(lambda: player.stop_called)
                assert player.stop_called

    asyncio.run(run())
