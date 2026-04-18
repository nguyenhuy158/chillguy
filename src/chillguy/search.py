import yt_dlp
from typing import List, Dict, Any

def search_youtube(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Searches YouTube for videos based on a query."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'extract_flat': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Check if it's already a URL
            if query.startswith(('http://', 'https://')):
                info = ydl.extract_info(query, download=False)
                if 'entries' in info:
                    return info['entries']
                return [info]
            
            # Otherwise search
            search_query = f"ytsearch{max_results}:{query}"
            info = ydl.extract_info(search_query, download=False)
            return info.get('entries', [])
        except Exception as e:
            return []

def get_stream_url(video_id: str) -> str:
    """Extracts the direct audio stream URL from a video ID."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_id, download=False)
        return info.get('url')
