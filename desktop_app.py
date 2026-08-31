import os
import sys
import time
import socket
import logging
import threading
import urllib.request
import uvicorn
import webview

# Ensure WebView2 user data folder is in writable AppData to prevent Admin / System32 blank screen errors
appdata_dir = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
wv2_data_dir = os.path.join(appdata_dir, "AssetVault", "webview2_data")
os.makedirs(wv2_data_dir, exist_ok=True)
os.environ["WEBVIEW2_USER_DATA_FOLDER"] = wv2_data_dir

# Add backend directory to module search path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app as fastapi_app
from app.services.watcher_service import watcher_service

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("assetvault.desktop")

class DesktopServerThread(threading.Thread):
    def __init__(self, host: str, port: int):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.server = None

    def run(self):
        config = uvicorn.Config(
            app=fastapi_app,
            host=self.host,
            port=self.port,
            log_level="warning",
            access_log=False
        )
        self.server = uvicorn.Server(config)
        logger.info(f"Starting embedded backend server on http://{self.host}:{self.port}...")
        self.server.run()

    def stop(self):
        if self.server:
            self.server.should_exit = True

def find_available_port(start_port: int = 8000) -> int:
    """Finds an available local TCP port."""
    for port in range(start_port, start_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port

def wait_for_server(url: str, timeout: float = 15.0) -> bool:
    """Waits until the backend server responds to HTTP requests."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.15)
    return False

class DesktopApi:
    def choose_folder(self):
        """Native folder picker invoked directly from JS bridge."""
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            folder = filedialog.askdirectory(title="Select Media Folder for AssetVault")
            root.destroy()
            return folder or None
        except Exception:
            return None

def main():
    host = "127.0.0.1"
    port = find_available_port(8000)
    server_url = f"http://{host}:{port}"

    # 1. Start backend server in daemon thread
    server_thread = DesktopServerThread(host=host, port=port)
    server_thread.start()

    # 2. Wait for backend startup
    if not wait_for_server(server_url):
        logger.error("Failed to start embedded backend server within timeout.")

    logger.info("Embedded server active. Initializing native PyWebView window...")

    api = DesktopApi()

    # 3. Create PyWebView Window
    window = webview.create_window(
        title="AssetVault - Media Asset Management",
        url=server_url,
        js_api=api,
        width=1360,
        height=860,
        min_size=(980, 620),
        background_color="#090e1c",
        text_select=True,
        zoomable=True
    )

    # 4. Clean Shutdown Lifecycle Handler
    def on_window_closed():
        logger.info("Desktop window closed by user. Initiating clean process shutdown...")
        try:
            watcher_service.stop_all()
        except Exception as e:
            logger.warning(f"Error stopping file watchers: {e}")

        try:
            server_thread.stop()
        except Exception as e:
            logger.warning(f"Error stopping server: {e}")

        logger.info("Shutdown complete. Exiting process.")
        # Force clean exit to terminate all threads without hanging
        os._exit(0)

    window.events.closed += on_window_closed

    # 5. Start GUI event loop (blocks until window is closed)
    webview.start(debug=False, private_mode=False, storage_path=wv2_data_dir)

if __name__ == "__main__":
    main()
