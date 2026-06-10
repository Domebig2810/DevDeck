"""
Serial bridge between the DevDeck Arduino (JSON firmware) and devdeck-control.

Protocol (Arduino → PC), one JSON object per line:
  {"event":"ready"}
  {"event":"encoder","index":0,"value":1}         # delta, +/-
  {"event":"encoder_button","index":0,"value":1}  # 1=press, 0=release
  {"event":"button","index":3,"value":1}          # 1=press, 0=release

Protocol (PC → Arduino):
  {"cmd":"image","slot":2,"data":"<base64>"}      # 1024 byte SSD1306 bitmap
  {"cmd":"overlay","slot":2,"label":"VOL","value":75,"duration_ms":1000}
  {"cmd":"clear","slot":2}
  {"cmd":"flash","slot":3}
"""

import base64
import json
import threading
import time
from typing import Callable, Optional

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

# Encoder i steuert die beiden OLEDs seiner Reihe
ENC_TO_SLOTS = {0: (0, 1), 1: (2, 3), 2: (4, 5)}

# USB Vendor IDs for Arduino / compatible boards
_ARDUINO_VIDS = {
    0x2341,  # Arduino SA (auch UNO R4 WiFi)
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
    keywords = ("arduino", "uno", "ch340", "ch341", "ftdi", "cp210", "usb serial", "uart")
    return any(k in desc or k in mfg for k in keywords)


class SerialBridge:
    def __init__(
        self,
        on_encoder: Callable[[int, int], None],
        on_encoder_button: Callable[[int, bool], None],
        on_button: Callable[[int, bool], None],
        on_connect: Optional[Callable[[str], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None,
    ):
        self._on_encoder = on_encoder              # (index, delta)
        self._on_encoder_button = on_encoder_button  # (index, pressed)
        self._on_button = on_button                # (index, pressed)
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        self._port: Optional["serial.Serial"] = None
        self._thread: Optional[threading.Thread] = None
        self._watch_thread: Optional[threading.Thread] = None
        self._running = False
        self._auto = False
        self._baud = 115200
        self._write_lock = threading.Lock()
        self._ack = threading.Event()
        self._ack_ok = False

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
            self._port = serial.Serial(port, baud, timeout=0.5)
            time.sleep(2.0)  # Arduino-Reset / Boot abwarten
            self._port.reset_input_buffer()
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
            try:
                self._port.close()
            except Exception:
                pass
        self._port = None

    @property
    def connected(self) -> bool:
        return self._port is not None and self._port.is_open

    @property
    def port_name(self) -> Optional[str]:
        return self._port.name if self.connected else None

    # ── Befehle an das Arduino ────────────────────────────────────────────────

    def send_image(self, slot: int, raw_1024: bytes):
        """Bild senden mit ACK-Flusskontrolle und bis zu 2 Wiederholungen.

        Die Firmware bestätigt jede Zeile mit {"event":"ack","ok":0|1};
        ok:0 heißt: Daten kamen unvollständig an (RX-Puffer-Überlauf).
        Alte Firmware ohne ACK: Timeout wirkt als einfache Drossel.
        """
        if len(raw_1024) != 1024:
            return
        payload = {
            "cmd": "image",
            "slot": slot,
            "data": base64.b64encode(raw_1024).decode("ascii"),
        }
        for _ in range(3):
            self._ack.clear()
            self._send(payload)
            if self._ack.wait(timeout=0.8) and self._ack_ok:
                return
            time.sleep(0.05)

    def send_overlay(self, slot: int, label: str, value: int, duration_ms: int = 1000):
        self._send({
            "cmd": "overlay",
            "slot": slot,
            "label": (label or "")[:15],
            "value": int(value),
            "duration_ms": int(duration_ms),
        })

    def send_flash(self, slot: int):
        self._send({"cmd": "flash", "slot": slot})

    def send_clear(self, slot: int):
        self._send({"cmd": "clear", "slot": slot})

    # ── Internal ──────────────────────────────────────────────────────────────

    def _send(self, payload: dict):
        if not self.connected:
            return
        msg = json.dumps(payload, separators=(",", ":")) + "\n"
        try:
            with self._write_lock:
                self._port.write(msg.encode())
        except Exception:
            pass

    def _watch_loop(self):
        """Periodically scan for an Arduino and connect when found."""
        while self._auto:
            if not self.connected:
                port = self.detect_arduino()
                if port:
                    ok = self.connect(port, self._baud)
                    if ok and self._on_connect:
                        try:
                            self._on_connect(port)
                        except Exception:
                            pass
            time.sleep(2)

    def _read_loop(self):
        while self._running:
            try:
                raw = self._port.readline()
            except Exception:
                self._running = False
                self._port = None
                if self._on_disconnect:
                    try:
                        self._on_disconnect()
                    except Exception:
                        pass
                break

            if not raw:
                continue

            line = raw.decode(errors="replace").strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            event = obj.get("event", "")
            index = obj.get("index", -1)
            value = obj.get("value", 0)

            try:
                if event == "ack":
                    self._ack_ok = obj.get("ok", 1) == 1
                    self._ack.set()
                elif event == "encoder":
                    self._on_encoder(index, value)
                elif event == "encoder_button":
                    self._on_encoder_button(index, value == 1)
                elif event == "button":
                    self._on_button(index, value == 1)
            except Exception:
                pass
