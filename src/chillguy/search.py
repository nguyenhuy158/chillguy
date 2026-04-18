import yt_dlp
from typing import List, Dict, Any
from .utils import logger

def search_youtube(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Searches YouTube for videos or playlists based on a query."""
    logger.info(f"Searching YouTube for: {query}")
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True, 
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'socket_timeout': 10,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Check if it's already a URL
            if query.startswith(('http://', 'https://')):
                info = ydl.extract_info(query, download=False)
                if 'entries' in info:
                    logger.info(f"Found playlist/results with {len(info['entries'])} entries.")
                    return list(info['entries'])
                logger.info("Found single video from URL.")
                return [info]
            
            # Search for videos
            video_search = f"ytsearch{max_results}:{query}"
            video_info = ydl.extract_info(video_search, download=False)
            videos = video_info.get('entries', [])
            for v in videos: v['_type_label'] = 'Music'
            
            # Search for playlists
            playlist_search = f"ytsearchplaylist{max_results}:{query}"
            playlist_info = ydl.extract_info(playlist_search, download=False)
            playlists = playlist_info.get('entries', [])
            for p in playlists: p['_type_label'] = 'Playlist'
            
            # Combine and return
            results = videos + playlists
            logger.info(f"Search returned {len(videos)} videos and {len(playlists)} playlists.")
            return results
        except Exception as e:
            logger.exception("YouTube search failed")
            return []

def get_playlist_tracks(url: str) -> List[Dict[str, Any]]:
    """Extracts all tracks from a YouTube playlist URL."""
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:
                return list(info['entries'])
            return [info]
        except Exception as e:
            logger.exception(f"Failed to extract playlist: {url}")
            return []

def get_stream_url(video_id: str) -> str:
    """Extracts the direct audio stream URL from a video ID."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_id, download=False)
        return info.get('url')
