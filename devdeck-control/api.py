import base64
import json
import os
import re
import sys
from dataclasses import asdict
from io import BytesIO
from typing import Optional

import webview
from PIL import Image

import db.database as db
from models.configuration import (
    NUM_BUTTONS,
    NUM_ENCODERS,
    ButtonConfig,
    Configuration,
    EncoderConfig,
)
from utils.command_runner import run_command
from utils.image_utils import convert_to_bmp_128x64


class Api:
    def __init__(self):
        self._window = None

    def _win(self):
        if self._window is None:
            self._window = webview.windows[0]
        return self._window

    # ── Window controls ───────────────────────────────────────────────────────

    def get_platform(self):
        return sys.platform  # "darwin" | "win32" | "linux"

    def minimize(self):
        self._win().minimize()

    def maximize(self):
        self._win().toggle_fullscreen()

    def close(self):
        self._win().destroy()

    # ── Configs ───────────────────────────────────────────────────────────────

    def load_all(self):
        rows = db.load_all()
        return [{"id": rid, "config": asdict(cfg)} for rid, cfg in rows]

    def create_config(self, name: str):
        cfg = Configuration(
            name=name,
            buttons=[ButtonConfig() for _ in range(NUM_BUTTONS)],
            encoders=[EncoderConfig() for _ in range(NUM_ENCODERS)],
        )
        row_id = db.insert(cfg)
        return {"id": row_id, "config": asdict(cfg)}

    def update_config(self, row_id: int, config_dict: dict):
        cfg = Configuration(**config_dict)
        db.update(row_id, cfg)
        return {"ok": True}

    def delete_config(self, row_id: int):
        db.delete(row_id)
        return {"ok": True}

    def import_json(self, json_str: str):
        data = json.loads(json_str)
        existing = db.load_all()
        existing_names = {cfg.name for _, cfg in existing}

        for c in data:
            cfg = Configuration(**c)
            # Klammern am Ende entfernen: "Amogus (1) (2)" -> "Amogus"
            base_name = re.sub(r"(\s*\(\d+\))+$", "", cfg.name).strip()

            if base_name not in existing_names:
                cfg.name = base_name
            else:
                counter = 1
                while f"{base_name} ({counter})" in existing_names:
                    counter += 1
                cfg.name = f"{base_name} ({counter})"

            existing_names.add(cfg.name)
            db.insert(cfg)

        return self.load_all()

    def export_json(self, selected_id: int):
        from pathlib import Path

        rows = db.load_all()

        selected = next((cfg for rid, cfg in rows if rid == selected_id), None)
        if not selected:
            return None

        data = json.dumps([asdict(selected)], indent=4)

        name = selected.name.strip()
        safe_name = (
            "".join(c for c in name if c not in r'\/:*?"<>|').strip()
            or "devdeck-configs"
        )

        downloads = Path.home() / "Downloads"
        downloads.mkdir(exist_ok=True)

        out_path = downloads / f"{safe_name}.json"
        counter = 1
        while out_path.exists():
            out_path = downloads / f"{safe_name}-{counter:02d}.json"
            counter += 1

        out_path.write_text(data, encoding="utf-8")
        return str(out_path)

    def reveal_in_finder(self, path: str):
        import subprocess
        import sys

        if sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path])
        elif sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", path])
        else:
            subprocess.Popen(["xdg-open", str(Path(path).parent)])

    # ── Commands ──────────────────────────────────────────────────────────────

    def run_command(self, command: str, step: Optional[float] = None):
        success, message = run_command(command, step=step)
        return {"success": success, "message": message}

    # ── Images ────────────────────────────────────────────────────────────────

    def convert_image(self, base64_data: str, button_index: int):
        os.makedirs("images", exist_ok=True)
        out = f"images/btn_{button_index}.bmp"

        img_bytes = base64.b64decode(base64_data)
        img = Image.open(BytesIO(img_bytes))
        img = img.convert("L")
        img = img.resize((128, 64), Image.Resampling.LANCZOS)
        img = img.point(lambda x: 255 if x > 128 else 0, mode="1")
        img.save(out, format="BMP")

        # Base64 zurückgeben für die Anzeige im Frontend
        with open(out, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")

        return {"path": out, "base64": f"data:image/bmp;base64,{encoded}"}
