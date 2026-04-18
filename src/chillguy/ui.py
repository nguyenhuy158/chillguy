from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import ProgressBar
from rich.layout import Layout
from rich.table import Table
from rich import box
import time
import readchar
from .player import Player

console = Console()

def create_player_layout(track_title, position, duration, volume, paused):
    layout = Layout()
    
    # Header
    status = "[bold yellow]PAUSED[/bold yellow]" if paused else "[bold green]PLAYING[/bold green]"
    header = Panel(
        f"[bold cyan]Chillguy Player[/bold cyan] - {status}",
        box=box.ROUNDED,
        style="cyan"
    )
    
    # Track Info
    progress = 0
    if duration and duration > 0:
        progress = (position / duration) * 100
        
    def format_time(seconds):
        if not seconds: return "00:00"
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}:{s:02d}"

    track_panel = Panel(
        f"[bold white]{track_title}[/bold white]\n"
        f"{format_time(position)} / {format_time(duration)}\n"
        f"Volume: {volume}%",
        title="Now Playing",
        box=box.ROUNDED
    )
    
    # Progress Bar
    pb = ProgressBar(total=100, completed=progress, width=40)
    
    # Controls Help
    controls = Table.grid(expand=True)
    controls.add_column(justify="left")
    controls.add_row(r"[dim]\[space] Play/Pause  \[<-/->] Seek 5s  \[+/-] Vol  \[q] Quit[/dim]")
    
    layout.split_column(
        Layout(header, size=3),
        Layout(track_panel, size=7),
        Layout(Panel(pb, box=box.MINIMAL), size=3),
        Layout(controls, size=1)
    )
    
    return layout

def playback_session(player: Player, track_title: str):
    with Live(refresh_per_second=4, screen=True) as live:
        while True:
            # Get player state
            pos = player.get_property("time-pos") or 0
            dur = player.get_property("duration") or 0
            vol = player.get_property("volume") or 0
            paused = player.get_property("pause")
            
            live.update(create_player_layout(track_title, pos, dur, vol, paused))
            
            # Check for keys (non-blocking if possible, but readchar is blocking)
            # We'll use a small timeout or check if a key is pressed
            # For simplicity in this version, we'll use a tight loop or a separate thread for keys
            # But let's try a simple approach first
            
            # TODO: Better key handling. For now, let's just implement the loop.
            # To avoid blocking the UI, we might need a separate thread for readchar.
            time.sleep(0.2)
            
            # This is a placeholder for key handling
            # In a real app, I'd use a thread or a non-blocking key reader
            break # Just for testing structure

def interactive_player(player: Player, track_title: str):
    """Main interactive loop for the player."""
    track_title = track_title[:50] + "..." if len(track_title) > 50 else track_title
    
    with Live(auto_refresh=True, screen=True) as live:
        try:
            while True:
                pos = player.get_property("time-pos") or 0
                dur = player.get_property("duration") or 0
                vol = player.get_property("volume") or 0
                paused = player.get_property("pause")
                
                live.update(create_player_layout(track_title, pos, dur, vol, paused))
                
                # Check for finished track
                if dur > 0 and pos >= dur - 0.5:
                    break
                    
                # Small sleep to prevent CPU spike
                time.sleep(0.1)
                
                # This part is tricky because readchar blocks.
                # In a full implementation, I'd use a separate thread to set player commands.
        except KeyboardInterrupt:
            player.stop()
