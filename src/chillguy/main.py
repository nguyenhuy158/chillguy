import typer
import questionary
from rich.console import Console
from rich.panel import Panel
from .utils import doctor as run_doctor
from .config import init_config, load_config, save_config, get_favorites, add_favorite, get_config_path, get_favorites_path
from .search import search_youtube, get_stream_url
from .player import Player
from .ui import interactive_player
from .utils import logger, doctor as run_doctor, read_logs, get_log_path
import sys
import os
from threading import Thread
import readchar
from rich.table import Table
from rich import box
import time

app = typer.Typer(help="Chillguy: A chill YouTube music player for your terminal.")
console = Console()
player = Player()

# Current track info for favorite toggling
current_track_data = None

def key_listener(p: Player):
    global current_track_data
    while True:
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
            elif key == 'f':
                if current_track_data:
                    if add_favorite(current_track_data):
                        logger.info(f"Added {current_track_data['title']} to favorites.")
            elif key == 'q':
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
    path = get_config_path()
    
    console.print(Panel(f"[bold cyan]Configuration[/bold cyan]\n[dim]Path: {path}[/dim]", expand=False))
    
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
    
    # Flatten config for selection
    options = []
    for section, values in cfg.items():
        if isinstance(values, dict):
            for key, val in values.items():
                options.append(f"{section}.{key} (current: {val})")
        else:
            options.append(f"{section} (current: {values})")
    
    selected = questionary.select(
        "Which setting do you want to change?",
        choices=options + ["Cancel"]
    ).ask()
    
    if not selected or selected == "Cancel":
        return

    key_path = selected.split(" (current:")[0]
    
    if "." in key_path:
        section, key = key_path.split(".")
        current_val = cfg[section][key]
    else:
        section, key = None, key_path
        current_val = cfg[key]
        
    new_val = questionary.text(f"Enter new value for {key_path}:", default=str(current_val)).ask()
    
    if new_val is None:
        return
        
    # Simple type conversion
    if isinstance(current_val, int):
        try:
            new_val = int(new_val)
        except ValueError:
            console.print("[red]Value must be an integer.[/red]")
            return
    elif isinstance(current_val, bool):
        new_val = new_val.lower() in ("true", "yes", "1", "y")

    if section:
        cfg[section][key] = new_val
    else:
        cfg[key] = new_val
        
    save_config(cfg)
    console.print(f"[green]✔ Updated {key_path} to {new_val}[/green]")

@app.command()
def favorites(
    list_favs: bool = typer.Option(False, "--list", "-l", help="List all favorites in a table")
):
    """List and play your favorite tracks."""
    favs = get_favorites()
    if not favs:
        console.print("[yellow]You haven't added any favorites yet.[/yellow]")
        return
    
    if list_favs:
        table = Table(title="Your Favorites", box=box.ROUNDED)
        table.add_column("Title", style="white")
        table.add_column("Duration", style="dim")
        table.add_column("ID", style="dim")
        
        for f in favs:
            table.add_row(f['title'], f.get('duration_string', '??:??'), f.get('id', 'N/A'))
        
        console.print(table)
        return

    choices = [f"{f['title']}" for f in favs]
    selected_title = questionary.select(
        "Your Favorites:",
        choices=choices
    ).ask()
    
    if selected_title:
        selected = next(f for f in favs if f['title'] == selected_title)
        play_track(selected)

@app.command()
def log(
    lines: int = typer.Option(20, "--lines", "-n", help="Number of lines to show"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output")
):
    """View application logs."""
    log_path = get_log_path()
    if not log_path.exists():
        console.print("[red]Log file not found.[/red]")
        return

    if follow:
        console.print(f"[bold cyan]Following logs at {log_path}... (Ctrl+C to stop)[/bold cyan]")
        try:
            with open(log_path, "r") as f:
                f.seek(0, os.SEEK_END)
                while True:
                    line = f.readline()
                    if not line:
                        time.sleep(0.1)
                        continue
                    console.print(line.strip())
        except KeyboardInterrupt:
            return
    else:
        content = read_logs(lines)
        console.print(Panel(content, title=f"Last {lines} lines of chillguy.log", box=box.ROUNDED))

@app.command()
def play(

    query: str = typer.Argument(None, help="Search query or YouTube URL"),
    best: bool = typer.Option(False, "--best", "-b", help="Auto-select the best match")
):
    """Play music from YouTube."""
    init_config()
    
    if not query:
        try:
            query = questionary.text("What do you want to listen to?").ask()
        except Exception as e:
            logger.error(f"Failed to get query from questionary: {e}")
            return
        if not query:
            return

    with console.status("[bold cyan]Searching YouTube..."):
        results = search_youtube(query)

    if not results:
        console.print("[red]No results found.[/red]")
        return

    # If multiple results, let user choose
    selected = None
    if len(results) > 1 and not best:
        if not sys.stdin.isatty():
            logger.info("Not a TTY, auto-selecting first result.")
            selected = results[0]
        else:
            try:
                choices = [f"{r['title']} ({r.get('duration_string', '??:??')})" for r in results]
                selected_label = questionary.select(
                    "Select a track:",
                    choices=choices
                ).ask()
                
                if selected_label is None:
                    return
                
                idx = choices.index(selected_label)
                selected = results[idx]
            except Exception as e:
                logger.error(f"Interactive selection failed: {e}. Falling back to best match.")
                selected = results[0]
    else:
        selected = results[0]

    play_track(selected)

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print(Panel("[bold cyan]Chillguy[/bold cyan]\nTerminal YouTube Music Player", expand=False))
        console.print(r"Use [bold]chillguy play <query>[/bold] to start.")
        init_config()

if __name__ == "__main__":
    app()
