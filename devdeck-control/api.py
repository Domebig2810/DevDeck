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
from serial_bridge import SerialBridge
from utils.command_runner import run_command
from utils.image_utils import convert_to_bmp_128x64


class Api:
    def __init__(self):
        self._window = None
        self._active_config_id: Optional[int] = None
        self._bridge = SerialBridge(
            on_encoder=self._handle_encoder,
            on_button=self._handle_button,
            on_connect=self._handle_connect,
            on_disconnect=self._handle_disconnect,
        )
        self._bridge.start_auto_connect()

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

    # ── Serial ────────────────────────────────────────────────────────────────

    def serial_list_ports(self):
        return SerialBridge.list_ports()

    def serial_connect(self, port: str):
        ok = self._bridge.connect(port)
        if ok and self._active_config_id is not None:
            self._push_labels_to_arduino()
        return {"ok": ok}

    def serial_disconnect(self):
        self._bridge.disconnect()
        return {"ok": True}

    def serial_bridge_start_auto(self):
        self._bridge.start_auto_connect()
        return {"ok": True}

    def serial_bridge_stop_auto(self):
        self._bridge.stop_auto_connect()
        self._bridge.disconnect()
        return {"ok": True}

    def serial_status(self):
        return {"connected": self._bridge.connected, "port": self._bridge.port_name}

    def serial_detect(self):
        from serial_bridge import SerialBridge as _SB
        return {"port": _SB.detect_arduino()}

    def set_active_config(self, row_id: int):
        self._active_config_id = row_id
        if self._bridge.connected:
            self._push_labels_to_arduino()
        return {"ok": True}

    def get_active_config_id(self):
        return self._active_config_id

    def _handle_connect(self, port: str):
        self._push_labels_to_arduino()

    def _handle_disconnect(self):
        pass  # auto-reconnect loop in SerialBridge will pick it back up

    def _push_labels_to_arduino(self):
        cfg = self._get_active_cfg()
        if cfg is None:
            return
        for i, enc in enumerate(cfg.encoders[:3]):
            label = enc.label if hasattr(enc, "label") and enc.label else f"ENC{i}"
            self._bridge.send_label(i, label)

    def _get_active_cfg(self) -> Optional[Configuration]:
        if self._active_config_id is None:
            return None
        rows = db.load_all()
        for rid, cfg in rows:
            if rid == self._active_config_id:
                return cfg
        return None

    def _handle_encoder(self, idx: int, delta: int):
        cfg = self._get_active_cfg()
        if cfg is None or idx >= len(cfg.encoders):
            return
        enc = cfg.encoders[idx]
        if delta > 0:
            cmd = enc.clockwise_command
        else:
            cmd = enc.counter_command
        if cmd:
            run_command(cmd, step=enc.step * abs(delta))
        # Keep Arduino display in sync
        self._bridge.send_value(idx, 50)  # neutral display; remove if not desired

    def _handle_button(self, idx: int):
        cfg = self._get_active_cfg()
        if cfg is None or idx >= len(cfg.encoders):
            return
        enc = cfg.encoders[idx]
        if enc.click_command:
            run_command(enc.click_command)

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
