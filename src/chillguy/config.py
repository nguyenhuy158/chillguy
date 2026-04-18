import os
from pathlib import Path
import toml
import json

CHILLGUY_DIR = Path.home() / ".chillguy"
CONFIG_FILE = CHILLGUY_DIR / "config.toml"
FAVORITES_FILE = CHILLGUY_DIR / "favorites.json"
PLAYLISTS_DIR = CHILLGUY_DIR / "playlists"

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
                "default_quality": "bestaudio"
            },
            "ui": {
                "theme": "chill"
            }
        }
        with open(CONFIG_FILE, "w") as f:
            toml.dump(default_config, f)
            
    if not FAVORITES_FILE.exists():
        with open(FAVORITES_FILE, "w") as f:
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
    if any(f['id'] == track['id'] for f in favs):
        return False
    favs.append(track)
    with open(FAVORITES_FILE, "w") as f:
        json.dump(favs, f)
    return True

def remove_favorite(track_id):
    favs = get_favorites()
    new_favs = [f for f in favs if f['id'] != track_id]
    with open(FAVORITES_FILE, "w") as f:
        json.dump(new_favs, f)
    return len(favs) != len(new_favs)

def get_config_path():
    return CONFIG_FILE

def get_favorites_path():
    return FAVORITES_FILE
