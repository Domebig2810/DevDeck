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
from utils.image_utils import (
    image_file_to_ssd1306,
    render_label_to_ssd1306,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(BASE_DIR, "images")

# ── Hardware-Zuordnung ────────────────────────────────────────────────────────
# Physisches Layout pro Reihe: [OLED][OLED][ENCODER rechts]
#
# Die tatsächliche Verdrahtung (Firmware-Index -> physische Position) wird
# über den Kalibrier-Assistenten ermittelt und in hw_mapping.json gespeichert:
#   buttons:  Firmware-Button-Index (A0..A5) -> logische Position 0-5
#             (zeilenweise links oben -> rechts unten)
#   slots:    logische Position 0-5 -> OLED-Slot (TCA-Kanal)
#   encoders: Firmware-Encoder-Index -> Reihe 0-2 (oben -> unten)
MAPPING_PATH = os.path.join(BASE_DIR, "hw_mapping.json")
_IDENTITY6 = {i: i for i in range(6)}
_IDENTITY3 = {i: i for i in range(3)}


def _resolve_image(path: str) -> str:
    """Relative Bildpfade (z.B. 'images/x.bmp') am Projektordner verankern."""
    if not path:
        return path
    return path if os.path.isabs(path) else os.path.join(BASE_DIR, path)


class Api:
    def __init__(self):
        self._window = None
        self._active_config_id: Optional[int] = None
        self._enc_values = [50.0, 50.0, 50.0]  # angezeigter Wert pro Encoder
        self._test_mode = False
        self._test_events: list = []
        self._load_hw_mapping()
        self._bridge = SerialBridge(
            on_encoder=self._handle_encoder,
            on_encoder_button=self._handle_encoder_button,
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
        result = []
        for rid, cfg in rows:
            d = asdict(cfg)
            # Bild-Previews als Base64 mitliefern, damit sie nach Neustart sichtbar sind
            for b in d["buttons"]:
                img_path = _resolve_image(b.get("image", ""))
                if img_path and os.path.exists(img_path):
                    with open(img_path, "rb") as f:
                        encoded = base64.b64encode(f.read()).decode("utf-8")
                    b["image_preview"] = f"data:image/bmp;base64,{encoded}"
            result.append({"id": rid, "config": d})
        return result

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
        if row_id == self._active_config_id:
            self._sync_device()  # Änderungen sofort auf der Hardware zeigen
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
        if ok:
            self._sync_device()
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
        changed = row_id != self._active_config_id
        self._active_config_id = row_id
        if changed and self._bridge.connected:
            self._sync_device()
        return {"ok": True}

    def get_active_config_id(self):
        return self._active_config_id

    # ── Hardware-Kalibrierung ─────────────────────────────────────────────────

    def _load_hw_mapping(self):
        self._btn_map = dict(_IDENTITY6)   # hw button -> logische Position
        self._slot_map = dict(_IDENTITY6)  # logische Position -> OLED-Slot
        self._enc_map = dict(_IDENTITY3)   # hw encoder -> Reihe
        try:
            with open(MAPPING_PATH, encoding="utf-8") as f:
                data = json.load(f)
            self._btn_map = {int(k): int(v) for k, v in data.get("buttons", {}).items()}
            self._slot_map = {int(k): int(v) for k, v in data.get("slots", {}).items()}
            self._enc_map = {int(k): int(v) for k, v in data.get("encoders", {}).items()}
        except FileNotFoundError:
            pass
        except Exception:
            pass  # kaputte Datei -> Identität behalten

    def hw_test_start(self):
        """Kalibriermodus: zeigt auf jedem OLED-Kanal seine Ziffer, sammelt Events."""
        self._test_mode = True
        self._test_events = []
        if self._bridge.connected:
            for ch in range(NUM_BUTTONS):
                self._bridge.send_image(ch, render_label_to_ssd1306(str(ch)))
        return {"ok": self._bridge.connected}

    def hw_test_events(self):
        return list(self._test_events)

    def hw_test_stop(self):
        self._test_mode = False
        self._test_events = []
        self._sync_device()
        return {"ok": True}

    def save_hw_mapping(self, buttons: dict, slots: dict, encoders: dict):
        """Speichert die Kalibrierung und wendet sie sofort an."""
        data = {
            "buttons": {str(k): int(v) for k, v in buttons.items()},
            "slots": {str(k): int(v) for k, v in slots.items()},
            "encoders": {str(k): int(v) for k, v in encoders.items()},
        }
        with open(MAPPING_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self._load_hw_mapping()
        self.hw_test_stop()
        return {"ok": True}

    def _handle_connect(self, port: str):
        self._sync_device()

    def _handle_disconnect(self):
        pass  # auto-reconnect loop in SerialBridge will pick it back up

    def _sync_device(self):
        """Bespielt alle 6 OLEDs mit dem Inhalt der aktiven Config."""
        if not self._bridge.connected:
            return
        cfg = self._get_active_cfg()
        if cfg is None:
            # Erste Config als Fallback aktivieren
            rows = db.load_all()
            if not rows:
                return
            self._active_config_id, cfg = rows[0]

        for i, btn in enumerate(cfg.buttons[:NUM_BUTTONS]):
            slot = self._slot_map.get(i, i)
            try:
                img_path = _resolve_image(btn.image)
                if btn.display_mode == "image" and img_path and os.path.exists(img_path):
                    raw = image_file_to_ssd1306(img_path)
                else:
                    raw = render_label_to_ssd1306(btn.label or f"Btn {i + 1}")
                # send_image blockiert bis zum ACK der Firmware (Flusskontrolle)
                self._bridge.send_image(slot, raw)
            except Exception:
                self._bridge.send_clear(slot)

    def _get_active_cfg(self) -> Optional[Configuration]:
        if self._active_config_id is None:
            return None
        rows = db.load_all()
        for rid, cfg in rows:
            if rid == self._active_config_id:
                return cfg
        return None

    def _handle_encoder(self, idx: int, delta: int):
        if self._test_mode:
            self._test_events.append({"type": "encoder", "index": idx})
            return
        row = self._enc_map.get(idx, idx)
        cfg = self._get_active_cfg()
        if cfg is None or not (0 <= row < len(cfg.encoders)):
            return
        enc = cfg.encoders[row]

        cmd = enc.clockwise_command if delta > 0 else enc.counter_command
        if cmd:
            run_command(cmd, step=enc.step * abs(delta))

        # Wert mitführen, Overlay nur auf dem OLED direkt neben dem Encoder
        # (Encoder sitzt rechts -> rechtes OLED der Reihe = logischer Button 2*row+1)
        self._enc_values[row] = max(0.0, min(100.0, self._enc_values[row] + delta * enc.step))
        label = (getattr(enc, "label", "") or f"ENC {row + 1}").strip()
        slot = self._slot_map.get(2 * row + 1, 2 * row + 1)
        self._bridge.send_overlay(slot, label, round(self._enc_values[row]), duration_ms=1200)

    def _handle_encoder_button(self, idx: int, pressed: bool):
        if self._test_mode:
            return
        if not pressed:
            return
        row = self._enc_map.get(idx, idx)
        cfg = self._get_active_cfg()
        if cfg is None or not (0 <= row < len(cfg.encoders)):
            return
        enc = cfg.encoders[row]
        if enc.click_command:
            run_command(enc.click_command)

    def _handle_button(self, idx: int, pressed: bool):
        if not pressed:
            return
        if self._test_mode:
            self._test_events.append({"type": "button", "index": idx})
            return
        logical = self._btn_map.get(idx, idx)
        cfg = self._get_active_cfg()
        if cfg is None or not (0 <= logical < len(cfg.buttons)):
            return
        self._bridge.send_flash(self._slot_map.get(logical, logical))
        btn = cfg.buttons[logical]
        if btn.command:
            run_command(btn.command)

    # ── Commands ──────────────────────────────────────────────────────────────

    def run_command(self, command: str, step: Optional[float] = None):
        success, message = run_command(command, step=step)
        return {"success": success, "message": message}

    # ── Images ────────────────────────────────────────────────────────────────

    def convert_image(self, base64_data: str, button_index: int, config_id: Optional[int] = None):
        os.makedirs(IMAGES_DIR, exist_ok=True)
        # Dateiname pro Config, sonst überschreiben sich Configs gegenseitig.
        # Gespeichert wird der relative Pfad, aufgelöst wird via _resolve_image.
        if config_id is not None:
            rel = f"images/cfg_{config_id}_btn_{button_index}.bmp"
        else:
            rel = f"images/btn_{button_index}.bmp"
        out = os.path.join(BASE_DIR, rel)

        img_bytes = base64.b64decode(base64_data)
        img = Image.open(BytesIO(img_bytes))
        img = img.convert("L")
        img = img.resize((128, 64), Image.Resampling.LANCZOS)
        img = img.point(lambda x: 255 if x > 128 else 0, mode="1")
        img.save(out, format="BMP")

        # Base64 zurückgeben für die Anzeige im Frontend
        with open(out, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")

        return {"path": rel, "base64": f"data:image/bmp;base64,{encoded}"}
