import shutil
import logging
import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

console = Console()

def get_logger():
    log_dir = Path.home() / ".chillguy"
    if not log_dir.exists():
        log_dir.mkdir(parents=True)
    
    log_file = log_dir / "chillguy.log"
    
    logging.basicConfig(
        filename=str(log_file),
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger("chillguy")

logger = get_logger()

def check_dependencies():
    """Checks if required system tools are installed."""
    dependencies = {
        "mpv": "Used for audio playback backend.",
        "yt-dlp": "Used for YouTube metadata and stream extraction."
    }
    
    # Optional but recommended for yt-dlp
    js_runtimes = ["node", "deno", "quickjs", "bun"]
    
    # Optional addons
    addons = {
        "fzf": "Used for fuzzy finding in selections (optional)."
    }
    
    missing = []
    found = []
    
    for dep, desc in dependencies.items():
        if shutil.which(dep):
            found.append(dep)
        else:
            missing.append((dep, desc))
            
    found_js = [js for js in js_runtimes if shutil.which(js)]
    
    found_addons = []
    for addon, desc in addons.items():
        if shutil.which(addon):
            found_addons.append(addon)
    
    return found, missing, found_js, found_addons

def doctor():
    """Prints a diagnostic report of the system dependencies."""
    found, missing, found_js, found_addons = check_dependencies()
    
    if not missing:
        console.print("[green]✔ All core system dependencies are satisfied![/green]")
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

    if not found_js:
        console.print("\n[yellow]⚠ No JavaScript runtime found (node, deno, etc.).[/yellow]")
        console.print("  [dim]yt-dlp may fail to extract some YouTube formats. Install Node.js or Deno for best results.[/dim]")
    else:
        console.print(f"\n[green]✔ Found JS runtime: {found_js[0]}[/green]")

    if "fzf" in found_addons:
        console.print("\n[green]✔ Found fzf: Selection menus will use fuzzy finding.[/green]")
    else:
        console.print("\n[dim]ℹ fzf not found: Selection menus will use standard prompts.[/dim]")
        console.print("  [dim]Install fzf (brew install fzf) for a better experience.[/dim]")

def get_log_path():
    return Path.home() / ".chillguy" / "chillguy.log"

def read_logs(lines: int = 20):
    log_file = get_log_path()
    if not log_file.exists():
        return "Log file not found."
    
    with open(log_file, "r") as f:
        content = f.readlines()
        return "".join(content[-lines:])
