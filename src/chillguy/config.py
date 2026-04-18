import os
from pathlib import Path
import toml
import json

CHILLGUY_DIR = Path.home() / ".chillguy"
CONFIG_FILE = CHILLGUY_DIR / "config.toml"
FAVORITES_FILE = CHILLGUY_DIR / "favorites.json"
HISTORY_FILE = CHILLGUY_DIR / "history.json"
PLAYLISTS_DIR = CHILLGUY_DIR / "playlists"

DEFAULT_RADIO_STATIONS = [
    {"name": "Lofi Girl - Study Beats", "url": "https://www.youtube.com/watch?v=jfKfPfyJRdk"},
    {"name": "Chillhop Radio - Jazzy Lofi Beats", "url": "https://www.youtube.com/watch?v=5yx6BWlEVcY"},
    {"name": "Synthwave Radio - 24/7 Retro", "url": "https://www.youtube.com/watch?v=4xDzrJKXOOY"},
    {"name": "Coffee Shop Radio - Relaxing Jazz", "url": "https://www.youtube.com/watch?v=lP26UCnoH9E"}
]

def init_config():
    """Initializes the ~/.chillguy directory and default config."""
    if not CHILLGUY_DIR.exists():
        CHILLGUY_DIR.mkdir(parents=True)
    
    if not PLAYLISTS_DIR.exists():
        PLAYLISTS_DIR.mkdir(parents=True)
        
    if not CONFIG_FILE.exists():
        default_config = {
            "player": {
                "volume": 100,
                "default_quality": "bestaudio",
                "shuffle": False,
                "repeat": "none" # none, one, all
            },
            "ui": {
                "theme": "chill",
                "show_lyrics": True
            },
            "radio": DEFAULT_RADIO_STATIONS
        }
        with open(CONFIG_FILE, "w") as f:
            toml.dump(default_config, f)
            
    if not FAVORITES_FILE.exists():
        with open(FAVORITES_FILE, "w") as f:
            json.dump([], f)

    if not HISTORY_FILE.exists():
        with open(HISTORY_FILE, "w") as f:
            json.dump([], f)

def load_config():
    init_config()
    with open(CONFIG_FILE, "r") as f:
        return toml.load(f)

def save_config(config_data):
    init_config()
    with open(CONFIG_FILE, "w") as f:
        toml.dump(config_data, f)

def get_favorites():
    init_config()
    with open(FAVORITES_FILE, "r") as f:
        return json.load(f)

def add_favorite(track):
    favs = get_favorites()
    # Normalize track data to avoid duplicates with different keys
    track_id = track.get('id') or track.get('url')
    if any((f.get('id') or f.get('url')) == track_id for f in favs):
        return False
    favs.append(track)
    with open(FAVORITES_FILE, "w") as f:
        json.dump(favs, f)
    return True

def remove_favorite(track_id):
    favs = get_favorites()
    new_favs = [f for f in favs if (f.get('id') or f.get('url')) != track_id]
    with open(FAVORITES_FILE, "w") as f:
        json.dump(new_favs, f)
    return len(favs) != len(new_favs)

def get_history():
    init_config()
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)

def add_to_history(track):
    history = get_history()
    # Remove if already exists to move to top
    track_id = track.get('id') or track.get('url')
    history = [t for t in history if (t.get('id') or t.get('url')) != track_id]
    
    history.insert(0, track)
    # Keep last 50 entries
    history = history[:50]
    
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

def get_radio_stations():
    config = load_config()
    return config.get("radio", DEFAULT_RADIO_STATIONS)

def get_config_path():
    return CONFIG_FILE

def get_favorites_path():
    return FAVORITES_FILE
