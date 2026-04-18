import subprocess
import json
import socket
import os
import tempfile
import time
from threading import Thread

class Player:
    def __init__(self):
        self.process = None
        self.ipc_path = os.path.join(tempfile.gettempdir(), "chillguy_mpv.sock")
        self.current_track = None
        self._stop_requested = False

    def start(self, url: str, title: str = "Unknown"):
        self.stop()
        self.current_track = title
        self._stop_requested = False
        
        # Ensure old socket is gone
        if os.path.exists(self.ipc_path):
            os.remove(self.ipc_path)

        cmd = [
            "mpv",
            "--no-video",
            f"--input-ipc-server={self.ipc_path}",
            "--idle=yes",
            url
        ]
        
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        # Wait a bit for IPC to start
        time.sleep(1)

    def _send_command(self, *args):
        if not os.path.exists(self.ipc_path):
            return None
        
        try:
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.connect(self.ipc_path)
            command = {"command": list(args)}
            client.send(json.dumps(command).encode() + b"\n")
            res = client.recv(1024)
            client.close()
            return json.loads(res.decode())
        except Exception:
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
