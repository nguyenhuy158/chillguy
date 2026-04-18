import subprocess
import json
import socket
import os
import tempfile
import time
from threading import Thread
from .utils import logger

class Player:
    def __init__(self):
        self.process = None
        self.ipc_path = os.path.join(tempfile.gettempdir(), f"chillguy_mpv_{os.getpid()}.sock")
        self.current_track = None
        self._stop_requested = False

    def start(self, url: str, title: str = "Unknown"):
        self.stop()
        self.current_track = title
        self._stop_requested = False
        
        logger.info(f"Starting mpv for track: {title}")
        
        # Ensure old socket is gone
        if os.path.exists(self.ipc_path):
            os.remove(self.ipc_path)

        cmd = [
            "mpv",
            "--no-video",
            f"--input-ipc-server={self.ipc_path}",
            "--idle=yes",
            "--force-window=no",
            "--no-terminal",
            url
        ]
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Wait for IPC to start with timeout
            max_retries = 30 # Increased from 20
            for i in range(max_retries):
                if os.path.exists(self.ipc_path):
                    # Test connection
                    if self._send_command("get_property", "mpv-version"):
                        logger.info("mpv IPC socket found and responding.")
                        break
                if self.process.poll() is not None:
                    error_output = self.process.stderr.read()
                    logger.error(f"mpv exited immediately with code {self.process.returncode}: {error_output}")
                    return False
                time.sleep(0.1)
            else:
                logger.error("mpv IPC socket timed out or not responding.")
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
            self._send_command("quit")
            self.process.terminate()
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
