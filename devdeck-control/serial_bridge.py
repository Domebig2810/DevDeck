"""
Serial bridge between DevDeck Arduino and devdeck-control.

Protocol (Arduino → PC):
  ENC:<idx>:<delta>   encoder turned (delta = +N or -N)
  BTN:<idx>           encoder button pressed
  READY               Arduino boot complete

Protocol (PC → Arduino):
  LABEL:<idx>:<text>  update OLED label for encoder idx
  VAL:<idx>:<0-100>   update OLED value display for encoder idx
"""

import threading
from typing import Callable, Optional

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False


class SerialBridge:
    def __init__(self, on_encoder: Callable[[int, int], None], on_button: Callable[[int], None]):
        self._on_encoder = on_encoder  # (index, delta)
        self._on_button = on_button    # (index)
        self._port: Optional["serial.Serial"] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    # ── Public API ────────────────────────────────────────────────────────────

    @staticmethod
    def list_ports() -> list[str]:
        if not HAS_SERIAL:
            return []
        return [p.device for p in serial.tools.list_ports.comports()]

    def connect(self, port: str, baud: int = 115200) -> bool:
        if not HAS_SERIAL:
            return False
        self.disconnect()
        try:
            self._port = serial.Serial(port, baud, timeout=1)
            self._running = True
            self._thread = threading.Thread(target=self._read_loop, daemon=True)
            self._thread.start()
            return True
        except Exception:
            self._port = None
            return False

    def disconnect(self):
        self._running = False
        if self._port and self._port.is_open:
            self._port.close()
        self._port = None

    @property
    def connected(self) -> bool:
        return self._port is not None and self._port.is_open

    def send_label(self, idx: int, text: str):
        self._send(f"LABEL:{idx}:{text}")

    def send_value(self, idx: int, value: int):
        self._send(f"VAL:{idx}:{value}")

    # ── Internal ──────────────────────────────────────────────────────────────

    def _send(self, line: str):
        if self.connected:
            try:
                self._port.write((line + "\n").encode())
            except Exception:
                pass

    def _read_loop(self):
        while self._running:
            try:
                raw = self._port.readline()
            except Exception:
                self._running = False
                break

            if not raw:
                continue

            line = raw.decode(errors="replace").strip()
            if not line:
                continue

            parts = line.split(":")
            if parts[0] == "ENC" and len(parts) == 3:
                try:
                    idx = int(parts[1])
                    delta = int(parts[2])
                    self._on_encoder(idx, delta)
                except ValueError:
                    pass
            elif parts[0] == "BTN" and len(parts) == 2:
                try:
                    idx = int(parts[1])
                    self._on_button(idx)
                except ValueError:
                    pass
