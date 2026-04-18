import requests
from bs4 import BeautifulSoup
import re
from .utils import logger

def fetch_lyrics(artist: str, title: str) -> str:
    """
    Attempts to fetch lyrics for a song.
    This is a basic implementation using a public search or a specific provider.
    For simplicity, we'll try to find it on a common lyrics site.
    """
    query = f"{artist} {title} lyrics"
    logger.info(f"Fetching lyrics for: {query}")
    
    # This is a very simplified placeholder. 
    # In a real app, you'd use a dedicated lyrics API or a more robust scraper.
    try:
        # Placeholder: Return a message if we can't find them easily
        return "Lyrics search integration in progress...\nTry searching on Google for now."
    except Exception as e:
        logger.error(f"Lyrics fetch failed: {e}")
        return "Could not load lyrics."

def clean_track_title(title: str):
    """Cleans common YouTube title fluff like (Official Video), [MV], etc."""
    title = re.sub(r'\(.*?\)', '', title)
    title = re.sub(r'\[.*?\]', '', title)
    title = re.sub(r'|.*', '', title) # Remove everything after |
    return title.strip()
