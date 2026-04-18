import typer
import questionary
from rich.console import Console
from rich.panel import Panel
from .utils import doctor as run_doctor
from .config import init_config, load_config, get_favorites, add_favorite
from .search import search_youtube, get_stream_url
from .player import Player
from .ui import interactive_player
from .utils import logger
import sys
from threading import Thread
import readchar

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

@app.command()
def favorites():
    """List and play your favorite tracks."""
    favs = get_favorites()
    if not favs:
        console.print("[yellow]You haven't added any favorites yet.[/yellow]")
        return
    
    choices = [f"{f['title']}" for f in favs]
    selected_title = questionary.select(
        "Your Favorites:",
        choices=choices
    ).ask()
    
    if selected_title:
        selected = next(f for f in favs if f['title'] == selected_title)
        play_track(selected)

def play_track(track):
    global current_track_data
    current_track_data = track
    
    logger.info(f"Preparing to play: {track['title']}")
    with console.status(f"[bold green]Fetching stream for {track['title']}..."):
        try:
            stream_url = get_stream_url(track['id'] if 'id' in track else track['url'])
        except Exception as e:
            logger.exception("Failed to get stream URL")
            console.print(f"[red]Error fetching stream: {e}[/red]")
            return

    if not stream_url:
        logger.error("Could not extract stream URL.")
        console.print("[red]Could not extract stream URL.[/red]")
        return

    if not player.start(stream_url, track['title']):
        logger.error("Player failed to start.")
        console.print("[red]Failed to start playback. Check ~/.chillguy/chillguy.log for details.[/red]")
        return
    
    # Start key listener thread
    kt = Thread(target=key_listener, args=(player,), daemon=True)
    kt.start()
    
    try:
        interactive_player(player, track['title'])
    except KeyboardInterrupt:
        player.stop()
    except Exception as e:
        logger.exception("Error in interactive player")
    finally:
        player.stop()

@app.command()
def play(query: str = typer.Argument(None, help="Search query or YouTube URL")):
    """Play music from YouTube."""
    init_config()
    
    if not query:
        query = questionary.text("What do you want to listen to?").ask()
        if not query:
            return

    with console.status("[bold cyan]Searching YouTube..."):
        results = search_youtube(query)

    if not results:
        console.print("[red]No results found.[/red]")
        return

    # If multiple results, let user choose
    if len(results) > 1:
        if not sys.stdin.isatty():
            logger.info("Not a TTY, auto-selecting first result.")
            selected = results[0]
        else:
            choices = [f"{r['title']} ({r.get('duration_string', '??:??')})" for r in results]
            selected_label = questionary.select(
                "Select a track:",
                choices=choices
            ).ask()
            
            if selected_label is None:
                return
            
            idx = choices.index(selected_label)
            selected = results[idx]
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
