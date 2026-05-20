import json
import sys
from dataclasses import asdict
from typing import Optional

import webview

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
        configs = [Configuration(**c) for c in data]
        db.replace_all(configs)
        return self.load_all()

    def export_json(self):
        rows = db.load_all()
        return json.dumps([asdict(cfg) for _, cfg in rows], indent=4)

    # ── Commands ──────────────────────────────────────────────────────────────

    def run_command(self, command: str, step: Optional[float] = None):
        success, message = run_command(command, step=step)
        return {"success": success, "message": message}

    # ── Images ────────────────────────────────────────────────────────────────

    def convert_image(self, input_path: str, button_index: int):
        import os

        os.makedirs("images", exist_ok=True)
        out = f"images/btn_{button_index}.bmp"
        convert_to_bmp_128x64(input_path, out)
        return {"path": out}
