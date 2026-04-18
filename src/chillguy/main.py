import typer
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.live import Live
from rich.layout import Layout
import sys
import os
import random
import time
from threading import Thread
import readchar

from .utils import logger, doctor as run_doctor, read_logs, get_log_path, ensure_single_instance
from .config import (
    init_config, load_config, save_config, get_favorites, 
    add_favorite, get_config_path, get_history, add_to_history, 
    get_radio_stations
)
from .search import search_youtube, get_stream_url, get_playlist_tracks
from .player import Player
from .ui import create_player_layout, select_interactive

app = typer.Typer(help="Chillguy: A chill YouTube music player for your terminal.")
console = Console()
player = Player()

# State management
current_track_data = None
skip_requested = False
back_requested = False
exit_requested = False

def key_listener(p: Player):
    global current_track_data, skip_requested, back_requested, exit_requested
    while not exit_requested:
        try:
            key = readchar.readkey()
            if key == ' ':
                p.toggle_pause()
            elif key == readchar.key.RIGHT:
                p.seek(5)
            elif key == readchar.key.LEFT:
                p.seek(-5)
            elif key == '+':
                p.adjust_volume(5)
            elif key == '-':
                p.adjust_volume(-5)
            elif key == 'n':
                skip_requested = True
            elif key == 'b':
                back_requested = True
            elif key == 's':
                p.shuffle = not p.shuffle
                if p.shuffle:
                    remaining = p.queue[p.current_index + 1:]
                    random.shuffle(remaining)
                    p.queue[p.current_index + 1:] = remaining
            elif key == 'r':
                modes = ["none", "one", "all"]
                curr_idx = modes.index(p.repeat)
                p.repeat = modes[(curr_idx + 1) % 3]
            elif key == 'f':
                if current_track_data:
                    if add_favorite(current_track_data):
                        logger.info(f"Added {current_track_data['title']} to favorites.")
            elif key == 'q':
                exit_requested = True
                p.stop()
                break
        except Exception as e:
            logger.debug(f"Key listener error: {e}")
            break

@app.command()
def doctor():
    """Check if system dependencies are installed."""
    run_doctor()

config_app = typer.Typer(help="Manage configuration.")
app.add_typer(config_app, name="config")

@config_app.callback(invoke_without_command=True)
def config_main(ctx: typer.Context):
    """Show current configuration."""
    if ctx.invoked_subcommand is not None:
        return
    init_config()
    cfg = load_config()
    console.print(Panel(f"[bold cyan]Configuration[/bold cyan]\n[dim]Path: {get_config_path()}[/dim]", expand=False))
    table = Table(box=box.ROUNDED)
    table.add_column("Section", style="cyan")
    table.add_column("Key", style="yellow")
    table.add_column("Value", style="green")
    for section, values in cfg.items():
        if isinstance(values, dict):
            for key, val in values.items():
                table.add_row(section, key, str(val))
        else:
            table.add_row("root", section, str(values))
    console.print(table)

@config_app.command()
def edit():
    """Interactively edit configuration settings."""
    init_config()
    cfg = load_config()
    options = []
    for section, values in cfg.items():
        if isinstance(values, dict):
            for key, val in values.items():
                options.append(f"{section}.{key} (current: {val})")
        else:
            options.append(f"{section} (current: {values})")
    selected = select_interactive("Which setting do you want to change?", choices=options + ["Cancel"])
    if not selected or selected == "Cancel": return
    key_path = selected.split(" (current:")[0]
    
    if key_path == "ui.theme":
        new_val = select_interactive(
            "Select Theme:",
            choices=["chill", "lavender", "midnight", "forest", "sunset", "rose"]
        )
    else:
        if "." in key_path:
            section, key = key_path.split(".")
            current_val = cfg[section][key]
        else:
            section, key = None, key_path
            current_val = cfg[key]
        new_val = questionary.text(f"Enter new value for {key_path}:", default=str(current_val)).ask()

    if new_val is None: return
    
    # Update logic
    if "." in key_path:
        section, key = key_path.split(".")
        current_val = cfg[section][key]
        if isinstance(current_val, int): new_val = int(new_val)
        elif isinstance(current_val, bool): new_val = str(new_val).lower() in ("true", "yes", "1", "y")
        cfg[section][key] = new_val
    else:
        current_val = cfg[key_path]
        if isinstance(current_val, int): new_val = int(new_val)
        cfg[key_path] = new_val
        
    save_config(cfg)
    console.print(f"[green]✔ Updated {key_path} to {new_val}[/green]")

@app.command()
def favorites(list_favs: bool = typer.Option(False, "--list", "-l", help="List favorites")):
    """View and play favorites."""
    favs = get_favorites()
    if not favs:
        console.print("[yellow]No favorites yet.[/yellow]")
        return
    if list_favs:
        table = Table(title="Favorites", box=box.ROUNDED)
        table.add_column("Title"); table.add_column("ID", style="dim")
        for f in favs: table.add_row(f['title'], f.get('id', 'N/A'))
        console.print(table); return
    choices = [f['title'] for f in favs]
    selected = select_interactive("Play favorite:", choices=choices)
    if selected:
        track = next(f for f in favs if f['title'] == selected)
        play_track(track)

@app.command()
def history(list_history: bool = typer.Option(False, "--list", "-l", help="List history")):
    """View and play history."""
    items = get_history()
    if not items:
        console.print("[yellow]History empty.[/yellow]")
        return
    if list_history:
        table = Table(title="History", box=box.ROUNDED)
        table.add_column("Title"); table.add_column("ID", style="dim")
        for i in items: table.add_row(i['title'], i.get('id', 'N/A'))
        console.print(table); return
    choices = [i['title'] for i in items]
    selected = select_interactive("Play history:", choices=choices)
    if selected:
        track = next(i for i in items if i['title'] == selected)
        play_track(track)

@app.command()
def radio():
    """Listen to chill radio."""
    stations = get_radio_stations()
    choices = [s['name'] for s in stations]
    selected = select_interactive("Select Station:", choices=choices)
    if selected:
        s = next(st for st in stations if st['name'] == selected)
        play_track({"title": s['name'], "url": s['url'], "id": None})

@app.command()
def log(lines: int = 20, follow: bool = False):
    """View logs."""
    path = get_log_path()
    if follow:
        try:
            with open(path, "r") as f:
                f.seek(0, os.SEEK_END)
                while True:
                    line = f.readline()
                    if not line: time.sleep(0.1); continue
                    console.print(line.strip())
        except KeyboardInterrupt: return
    else:
        console.print(Panel(read_logs(lines), title="Logs"))

def play_track(track):
    player.clear_queue()
    player.add_to_queue(track)
    player.current_index = 0
    play_queue()

def play_queue():
    global skip_requested, back_requested, current_track_data, exit_requested
    
    # Check if thread is already running
    if not hasattr(play_queue, "_thread_started"):
        kt = Thread(target=key_listener, args=(player,), daemon=True)
        kt.start()
        play_queue._thread_started = True

    while 0 <= player.current_index < len(player.queue) and not exit_requested:
        track = player.queue[player.current_index]
        current_track_data = track
        add_to_history(track)
        from rich.markup import escape
        safe_title = escape(track['title'])
        with console.status(f"[bold green]Streaming {safe_title}..."):
            try:
                url = get_stream_url(track.get('id') or track.get('url'))
                if not url or not player.start(url, track['title']):
                    player.current_index += 1; continue
            except Exception:
                player.current_index += 1; continue
        skip_requested = False
        back_requested = False
        run_player_loop(player)
        
        if exit_requested:
            break
            
        if back_requested: player.current_index = max(0, player.current_index - 1)
        elif player.repeat == "one": pass
        else:
            if player.repeat == "all" and player.current_index == len(player.queue) - 1:
                player.current_index = 0
            else: player.current_index += 1

def run_player_loop(p: Player):
    global skip_requested, back_requested, exit_requested
    with Live(auto_refresh=True, screen=True) as live:
        while not exit_requested:
            try:
                if skip_requested or back_requested: break
                pos = p.get_property("time-pos") or 0
                dur = p.get_property("duration") or 0
                vol = p.get_property("volume") or 0
                paused = p.get_property("pause")
                live.update(create_player_layout(p, pos, dur, vol, paused))
                if dur > 0 and pos >= dur - 0.5: break
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"UI Update loop error: {e}")
                time.sleep(1) # Wait a bit before retrying to avoid spamming logs

@app.command()
def play(query: str = typer.Argument(None), best: bool = False):
    """Play from YouTube."""
    ensure_single_instance()
    if not query:
        query = questionary.text("Search:").ask()
        if not query: return
    with console.status("[bold cyan]Searching..."):
        results = search_youtube(query)
    if not results:
        console.print("[red]No results.[/red]"); return
    player.clear_queue()
    
    if len(results) > 1 and not best:
        # Create choices with [Music] or [Playlist] tag
        choices = []
        for r in results[:10]:
            rtype = r.get('_type_label', 'Music')
            if rtype == 'Playlist':
                count = r.get('playlist_count') or r.get('item_count') or r.get('n_entries') or '?'
                duration = f"{count} tracks"
            else:
                duration = r.get('duration_string') or r.get('duration') or '??:??'
                if isinstance(duration, (int, float)):
                    m, s = divmod(int(duration), 60)
                    duration = f"{m:02d}:{s:02d}"
            choices.append(f"[{rtype}] {r['title']} ({duration})")
            
        sel = select_interactive("Select:", choices=choices)
        if not sel: return
        selected = results[choices.index(sel)]
        
        if selected.get('_type_label') == 'Playlist':
            with console.status("[bold cyan]Loading playlist tracks..."):
                url = selected.get('webpage_url') or selected.get('url') or selected.get('id')
                if url and not url.startswith('http'):
                    url = f"https://www.youtube.com/playlist?list={url}"
                tracks = get_playlist_tracks(url)
                for t in tracks: player.add_to_queue(t)
        else:
            player.add_to_queue(selected)
    else:
        # For best match or single result, if it's a playlist we still might want to expand it
        selected = results[0]
        if selected.get('_type_label') == 'Playlist':
            with console.status("[bold cyan]Loading playlist tracks..."):
                url = selected.get('webpage_url') or selected.get('url') or selected.get('id')
                if url and not url.startswith('http'):
                    url = f"https://www.youtube.com/playlist?list={url}"
                tracks = get_playlist_tracks(url)
                for t in tracks: player.add_to_queue(t)
        else:
            for r in results: player.add_to_queue(r)
            
    if not player.queue:
        console.print("[red]No tracks found.[/red]"); return
        
    player.current_index = 0
    play_queue()

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print(Panel("[bold cyan]Chillguy[/bold cyan]\nTerminal YouTube Music Player", expand=False))
        init_config()

if __name__ == "__main__":
    app()
