import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

import webview

import db.database as db
from api import Api

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
DIST_INDEX = os.path.join(FRONTEND_DIR, "dist", "index.html")


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


def start_vite(port: int) -> subprocess.Popen:
    # shutil.which löst auch npm.cmd unter Windows auf
    npm = shutil.which("npm")
    if npm is None:
        raise FileNotFoundError("npm")
    return subprocess.Popen(
        [npm, "run", "dev", "--", "--port", str(port)],
        cwd=FRONTEND_DIR,
    )


def stop_vite(vite: subprocess.Popen):
    if sys.platform == "win32":
        # terminate() trifft unter Windows nur den npm.cmd-Wrapper,
        # der node-Kindprozess liefe weiter -> ganzen Prozessbaum beenden
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(vite.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        vite.terminate()


def main():
    db.init_db()
    api = Api()

    # In einer PyInstaller-App gibt es keinen Dev-Server -> Standard ist prod
    frozen = getattr(sys, "frozen", False)
    dev_mode = os.environ.get("DEVDECK_DEV", "0" if frozen else "1") == "1"
    vite = None

    if dev_mode:
        try:
            port = find_free_port()
            vite = start_vite(port)
            url = f"http://localhost:{port}"
            wait_for_vite(url)
        except FileNotFoundError:
            if not os.path.exists(DIST_INDEX):
                print(
                    "npm wurde nicht gefunden und frontend/dist existiert nicht.\n"
                    "Entweder Node.js installieren (Dev-Modus) oder das Frontend "
                    "einmal bauen: cd frontend && npm install && npm run build",
                    file=sys.stderr,
                )
                sys.exit(1)
            print("npm nicht gefunden – nutze gebautes Frontend (frontend/dist).")
            dev_mode = False
            url = DIST_INDEX
    else:
        url = DIST_INDEX

    webview.create_window(
        title="DevDeck Control",
        url=url,
        js_api=api,
        width=1200,
        height=800,
        min_size=(800, 600),
    )
    webview.start(debug=dev_mode)

    if vite is not None:
        stop_vite(vite)


if __name__ == "__main__":
    main()
