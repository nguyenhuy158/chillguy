import subprocess
import json
import socket
import os
import tempfile
import time
import atexit
import signal
from threading import Thread
from .utils import logger

class Player:
    def __init__(self):
        self.process = None
        # Use a shorter path for the socket to avoid macOS AF_UNIX length limits
        self.ipc_path = f"/tmp/cg_{os.getpid()}.s"
        self.queue = []
        self.current_index = -1
        self.shuffle = False
        self.repeat = "none" # none, one, all
        self._stop_requested = False
        atexit.register(self.stop)

    @property
    def current_track(self):
        if 0 <= self.current_index < len(self.queue):
            return self.queue[self.current_index]
        return None

    def add_to_queue(self, track: dict, position: int = -1):
        if position == -1:
            self.queue.append(track)
        else:
            self.queue.insert(position, track)
        logger.info(f"Added to queue: {track.get('title')}")

    def clear_queue(self):
        self.queue = []
        self.current_index = -1
        self.stop()

    def start(self, url: str, title: str = "Unknown"):
        self.stop()
        self._stop_requested = False
        
        logger.info(f"Starting mpv for track: {title}")
        
        # Ensure old socket is gone
        if os.path.exists(self.ipc_path):
            try:
                os.remove(self.ipc_path)
            except OSError:
                pass

        # Load initial volume from config
        from .config import load_config
        config = load_config()
        initial_volume = config.get("player", {}).get("volume", 100)

        cmd = [
            "mpv",
            "--no-video",
            "--vid=no",
            "--audio-display=no",
            f"--input-ipc-server={self.ipc_path}",
            "--idle=yes",
            "--force-window=no",
            "--no-terminal",
            f"--volume={initial_volume}",
            f"--force-media-title={title}",
            url
        ]
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                preexec_fn=os.setsid if hasattr(os, "setsid") else None
            )
            
            # Wait for IPC to start with timeout
            max_retries = 50 # Increased
            for i in range(max_retries):
                if os.path.exists(self.ipc_path):
                    # Test connection with a generic property
                    if self._send_command("get_property", "mpv-version"):
                        logger.info(f"mpv IPC socket found and responding at {self.ipc_path}")
                        break
                if self.process.poll() is not None:
                    error_output = self.process.stderr.read()
                    logger.error(f"mpv exited immediately with code {self.process.returncode}: {error_output}")
                    return False
                time.sleep(0.1)
            else:
                logger.error(f"mpv IPC socket timed out or not responding at {self.ipc_path}")
                return False
                
            return True
        except Exception as e:
            logger.exception("Failed to start mpv process")
            return False

    def _send_command(self, *args):
        if not os.path.exists(self.ipc_path):
            return None
        
        try:
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.settimeout(0.5)
            client.connect(self.ipc_path)
            command = {"command": list(args)}
            client.send(json.dumps(command).encode() + b"\n")
            res = client.recv(4096)
            client.close()
            if not res:
                return None
            return json.loads(res.decode())
        except Exception as e:
            logger.debug(f"IPC command failed: {args} - {e}")
            return None

    def toggle_pause(self):
        self._send_command("cycle", "pause")

    def seek(self, seconds: int):
        self._send_command("seek", seconds, "relative")

    def adjust_volume(self, amount: int):
        self._send_command("add", "volume", amount)

    def stop(self):
        if self.process:
            logger.info("Stopping mpv process...")
            try:
                # Try graceful quit via IPC
                self._send_command("quit")
                
                # Wait a bit
                for _ in range(10):
                    if self.process.poll() is not None:
                        break
                    time.sleep(0.1)
                
                if self.process.poll() is None:
                    # Try SIGTERM to the process group
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                    
                    for _ in range(5):
                        if self.process.poll() is not None:
                            break
                        time.sleep(0.1)
                
                if self.process.poll() is None:
                    # Aggressive SIGKILL
                    logger.warning("mpv still running, sending SIGKILL...")
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            except Exception as e:
                logger.error(f"Error during player stop: {e}")
            
            self.process = None
            
        if os.path.exists(self.ipc_path):
            try:
                os.remove(self.ipc_path)
            except OSError:
                pass

    def get_property(self, prop_name: str):
        res = self._send_command("get_property", prop_name)
        if res and res.get("status") == "success":
            return res.get("data")
        return None

    def is_playing(self):
        return self.get_property("pause") is False
