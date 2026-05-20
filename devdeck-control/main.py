import os
import socket
import subprocess
import time
import urllib.request

import webview

import db.database as db
from api import Api


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def wait_for_vite(url: str, timeout: int = 10):
    for _ in range(timeout * 2):
        try:
            urllib.request.urlopen(url)
            return
        except Exception:
            time.sleep(0.5)


def main():
    db.init_db()
    api = Api()

    dev_mode = os.environ.get("DEVDECK_DEV", "1") == "1"
    vite = None

    if dev_mode:
        port = find_free_port()
        vite = subprocess.Popen(
            ["npm", "run", "dev", "--", "--port", str(port)],
            cwd=os.path.abspath("frontend"),
        )
        url = f"http://localhost:{port}"
        wait_for_vite(url)
    else:
        url = os.path.abspath("frontend/dist/index.html")

    webview.create_window(
        title="DevDeck",
        url=url,
        js_api=api,
        width=1200,
        height=800,
        min_size=(800, 600),
    )
    webview.start(debug=dev_mode)

    if vite is not None:
        vite.terminate()


if __name__ == "__main__":
    main()

# TODO: to bundle:
# pip install pyinstaller
# pyinstaller --name "DevDeck" --windowed main.py
