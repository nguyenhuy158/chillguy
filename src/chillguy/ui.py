from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import ProgressBar
from rich.layout import Layout
from rich.table import Table
from rich import box
from rich.text import Text
import time
import readchar
import subprocess
import shutil
import questionary
from .player import Player
from .utils import logger
from .config import load_config


console = Console()

from rich.markup import escape

console = Console()

def get_theme_style():
    try:
        config = load_config()
        theme = config.get("ui", {}).get("theme", "chill")
    except Exception:
        theme = "chill"
    
    themes = {
        "chill": "cyan",
        "lavender": "magenta",
        "midnight": "blue",
        "forest": "green",
        "sunset": "orange3",
        "rose": "red"
    }
    return themes.get(theme, "cyan")

def select_interactive(prompt: str, choices: list[str]) -> str | None:
    """Interactively select an option using fzf if available, otherwise questionary."""
    if not choices:
        return None
        
    try:
        config = load_config()
        use_fzf = config.get("ui", {}).get("use_fzf", "auto")
    except Exception:
        use_fzf = "auto"
    
    fzf_available = shutil.which("fzf") is not None
    
    should_use_fzf = False
    if use_fzf == "true":
        should_use_fzf = True
        if not fzf_available:
            logger.warning("fzf forced in config but not found on system. Falling back to questionary.")
            should_use_fzf = False
    elif use_fzf == "auto":
        should_use_fzf = fzf_available
    
    if should_use_fzf:
        try:
            input_str = "\n".join(choices)
            cmd = ["fzf", "--height", "40%", "--layout=reverse", "--border", "--prompt", f"{prompt} > "]
            
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=None,
                text=True
            )
            stdout, _ = process.communicate(input=input_str)
            
            if process.returncode == 0:
                selected = stdout.strip()
                return selected if selected in choices else None
            return None
        except Exception as e:
            logger.error(f"fzf failed: {e}. Falling back to questionary.")
            
    try:
        return questionary.select(prompt, choices=choices).ask()
    except Exception as e:
        logger.error(f"Questionary selection failed: {e}")
        return None

def create_player_layout(player: Player, position, duration, volume, paused, lyrics=""):
    layout = Layout()
    style = get_theme_style()
    
    track_title = "Nothing playing"
    if player.current_track:
        track_title = player.current_track.get('title', 'Unknown')
        # Clean title of any newlines or weird chars that might break UI
        track_title = track_title.replace('\n', ' ').replace('\r', ' ').strip()
        if len(track_title) > 50:
            track_title = track_title[:47] + "..."

    # Header
    status = "[bold yellow]PAUSED[/bold yellow]" if paused else "[bold green]PLAYING[/bold green]"
    header = Panel(
        f"[bold {style}]Chillguy Player[/bold {style}] - {status}",
        box=box.ROUNDED,
        style=style
    )
    
    # Progress
    progress = 0
    if duration and duration > 0:
        progress = (position / duration) * 100
        
    def format_time(seconds):
        if seconds is None or seconds < 0: return "00:00"
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}:{s:02d}"

    # Main Player Panel
    # Use escape() to handle titles with [ or ]
    safe_title = escape(str(track_title))
    
    time_info = f"{format_time(position)} / {format_time(duration)}"
    if position == 0 and duration == 0:
        time_info = "Loading..."

    # Use Text object for track_info to avoid markup issues with dynamic content
    track_info_text = Text()
    track_info_text.append(f"{safe_title}\n", style="bold white")
    track_info_text.append(f"{time_info}\n")
    track_info_text.append(f"Volume: {volume}% | Shuffle: {'On' if player.shuffle else 'Off'} | Repeat: {player.repeat}", style="dim")
    
    pb = ProgressBar(total=100, completed=progress, width=40)
    
    player_panel = Panel(
        Group(track_info_text, "", pb),
        title="Now Playing",
        box=box.ROUNDED,
        padding=(1, 2),
        border_style=style
    )
    
    # Queue Panel
    queue_table = Table(box=box.SIMPLE, expand=True)
    queue_table.add_column("Up Next", style="dim")
    
    for i, track in enumerate(player.queue[player.current_index + 1 : player.current_index + 6]):
        title = str(track.get('title', 'Unknown'))
        if len(title) > 30: title = title[:27] + "..."
        queue_table.add_row(f"{i+1}. {escape(title)}")
        
    queue_panel = Panel(queue_table, title="Queue", box=box.ROUNDED, border_style=style)

    # Lyrics/Side Panel
    lyrics_panel = Panel(lyrics or "[dim]No lyrics available[/dim]", title="Lyrics", box=box.ROUNDED, border_style=style)

    # Footer
    controls = Table.grid(expand=True)
    controls.add_column(justify="left")
    controls.add_row(r"[dim]\[space] Play/Pause  \[n/b] Next/Prev  \[<-/->] Seek 5s  \[+/-] Vol  \[s] Shuffle  \[r] Repeat  \[q] Quit[/dim]")

    footer_panel = Panel(controls, box=box.MINIMAL, border_style=style)

    # Split layout
    layout.split_column(
        Layout(header, size=3),
        Layout(name="main"),
        Layout(footer_panel, size=3)
    )
    
    layout["main"].split_row(
        Layout(player_panel, ratio=2),
        Layout(name="side", ratio=1)
    )
    
    layout["side"].split_column(
        Layout(queue_panel, ratio=1),
        Layout(lyrics_panel, ratio=1)
    )
    
    return layout

def interactive_player(player: Player, track_title: str):
    """Main interactive loop for the player."""
    
    with Live(auto_refresh=True, screen=True) as live:
        try:
            while True:
                pos = player.get_property("time-pos") or 0
                dur = player.get_property("duration") or 0
                vol = player.get_property("volume") or 0
                paused = player.get_property("pause")
                
                # Fetch lyrics only once per track (simplified)
                lyrics = "" # TODO: Integrate lyrics provider
                
                live.update(create_player_layout(player, pos, dur, vol, paused, lyrics))
                
                # Check for finished track
                if dur > 0 and pos >= dur - 0.5:
                    break
                    
                # Small sleep to prevent CPU spike
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            player.stop()
        except Exception as e:
            logger.exception("UI Error")
