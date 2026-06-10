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
import time
from typing import Callable, Optional

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

# USB Vendor IDs for Arduino / compatible boards
_ARDUINO_VIDS = {
    0x2341,  # Arduino SA
    0x1A86,  # CH340 (Nano clones)
    0x0403,  # FTDI
    0x10C4,  # Silicon Labs CP210x
    0x239A,  # Adafruit
    0x1B4F,  # SparkFun
}


def _is_arduino_port(port_info) -> bool:
    vid = getattr(port_info, "vid", None)
    if vid in _ARDUINO_VIDS:
        return True
    desc = (getattr(port_info, "description", "") or "").lower()
    mfg = (getattr(port_info, "manufacturer", "") or "").lower()
    keywords = ("arduino", "ch340", "ch341", "ftdi", "cp210", "usb serial", "uart")
    return any(k in desc or k in mfg for k in keywords)


class SerialBridge:
    def __init__(
        self,
        on_encoder: Callable[[int, int], None],
        on_button: Callable[[int], None],
        on_connect: Optional[Callable[[str], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None,
    ):
        self._on_encoder = on_encoder
        self._on_button = on_button
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        self._port: Optional["serial.Serial"] = None
        self._thread: Optional[threading.Thread] = None
        self._watch_thread: Optional[threading.Thread] = None
        self._running = False
        self._auto = False  # auto-reconnect mode

    # ── Public API ────────────────────────────────────────────────────────────

    @staticmethod
    def list_ports() -> list[str]:
        if not HAS_SERIAL:
            return []
        return [p.device for p in serial.tools.list_ports.comports()]

    @staticmethod
    def detect_arduino() -> Optional[str]:
        """Return the first port that looks like an Arduino, or None."""
        if not HAS_SERIAL:
            return None
        for p in serial.tools.list_ports.comports():
            if _is_arduino_port(p):
                return p.device
        return None

    def start_auto_connect(self, baud: int = 115200):
        """Watch for an Arduino in the background and connect automatically."""
        if not HAS_SERIAL:
            return
        self._auto = True
        self._baud = baud
        if self._watch_thread is None or not self._watch_thread.is_alive():
            self._watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
            self._watch_thread.start()

    def stop_auto_connect(self):
        self._auto = False

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

    @property
    def port_name(self) -> Optional[str]:
        return self._port.name if self.connected else None

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

    def _watch_loop(self):
        """Periodically scan for an Arduino and connect when found."""
        while self._auto:
            if not self.connected:
                port = self.detect_arduino()
                if port:
                    ok = self.connect(port, getattr(self, "_baud", 115200))
                    if ok and self._on_connect:
                        self._on_connect(port)
            time.sleep(2)

    def _read_loop(self):
        while self._running:
            try:
                raw = self._port.readline()
            except Exception:
                self._running = False
                self._port = None
                if self._on_disconnect:
                    self._on_disconnect()
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
