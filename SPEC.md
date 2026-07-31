# Technical Specification: chillguy

## Overview
`chillguy` is a CLI application that enables users to stream audio from YouTube directly in the terminal. It leverages `yt-dlp` for metadata and stream extraction, and `mpv` as the playback engine.

## Architecture

### Components
1.  **CLI Interface (`main.py`)**: Uses `typer` to handle commands like `play`, `doctor`, and `favorites`.
2.  **Search Engine (`search.py`)**: Interfaces with `yt-dlp` to search for videos and extract direct stream URLs.
3.  **Playback Engine (`player.py`)**: Manages a background `mpv` process via JSON IPC for real-time control (play/pause, seek, volume).
4.  **UI Module (`ui.py`)**: Provides a live-updating dashboard using `rich.live`.
5.  **Config Manager (`config.py`)**: Manages user data in `~/.chillguy/`.
6.  **Textual UI (`tui.py`, optional)**: Full-screen playlist + now-playing view built on `textual`, driving the same `Player`/`search.get_stream_url` used elsewhere (no separate playback path). Enabled via the `tui` extra; launched with `chillguy ui` or `chillguy play --ui`.

## Controls
- `space`: Toggle Pause
- `Right Arrow`: Seek +5s
- `Left Arrow`: Seek -5s
- `+`: Increase Volume
- `-`: Decrease Volume
- `q`: Quit Player

## Dependencies
- `mpv`: System-level audio player.
- `yt-dlp`: Stream extractor.
- `typer`: CLI framework.
- `rich`: UI rendering.
- `questionary`: Interactive prompts.
- `readchar`: Keyboard event handling.
