import shutil
from rich.console import Console
from rich.panel import Panel

console = Console()

def check_dependencies():
    """Checks if required system tools are installed."""
    dependencies = {
        "mpv": "Used for audio playback backend.",
        "yt-dlp": "Used for YouTube metadata and stream extraction."
    }
    
    missing = []
    found = []
    
    for dep, desc in dependencies.items():
        if shutil.which(dep):
            found.append(dep)
        else:
            missing.append((dep, desc))
            
    return found, missing

def doctor():
    """Prints a diagnostic report of the system dependencies."""
    found, missing = check_dependencies()
    
    if not missing:
        console.print("[green]✔ All system dependencies are satisfied![/green]")
        for dep in found:
            console.print(f"  - {dep} found at {shutil.which(dep)}")
    else:
        console.print("[red]✘ Missing system dependencies:[/red]")
        for dep, desc in missing:
            console.print(f"  - [bold]{dep}[/bold]: {desc}")
            if dep == "mpv":
                console.print("    [dim]Install via: brew install mpv (macOS), sudo apt install mpv (Linux)[/dim]")
            elif dep == "yt-dlp":
                console.print("    [dim]Install via: pip install yt-dlp or brew install yt-dlp[/dim]")
        
        console.print("\n[yellow]Please install the missing tools to use chillguy.[/yellow]")
