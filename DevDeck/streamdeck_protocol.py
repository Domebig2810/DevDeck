"""
streamdeck_protocol.py

Modul für die JSON-basierte Kommunikation mit dem Stream-Deck-Arduino.
Kapselt:
  - Auto-Erkennung des Arduino-Ports
  - Empfangen von Encoder-/Button-Events als typisierte Objekte
  - Senden von Bildern, Overlays, Flash, Clear

Abhängigkeiten:
    pip install pyserial pillow

Beispiel:
    from streamdeck_protocol import StreamDeck

    sd = StreamDeck()  # oder StreamDeck(port="COM6")
    sd.connect()

    for event in sd.events():
        if event.kind == "encoder":
            print(f"Encoder {event.index} dreht {event.value:+d}")
        elif event.kind == "button":
            print(f"Button {event.index} {'gedrückt' if event.value else 'losgelassen'}")
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Generator, Optional

import serial
import serial.tools.list_ports
from PIL import Image


# ──────────────────────────────────────────────────────────────────
# Layout-Konstante: welche zwei OLED-Slots gehören zu welchem Encoder
# ──────────────────────────────────────────────────────────────────
ENC_TO_SLOTS = {
    0: (0, 1),
    1: (2, 3),
    2: (4, 5),
}

# Welcher Button (0–5) sitzt unter welchem OLED-Slot
# Da Button-Index = OLED-Index, ist das die Identitäts-Abbildung
BTN_TO_SLOT = {i: i for i in range(6)}


# ──────────────────────────────────────────────────────────────────
# Events vom Arduino
# ──────────────────────────────────────────────────────────────────
@dataclass
class StreamDeckEvent:
    """Repräsentiert ein Event vom Arduino."""
    kind: str          # "encoder", "encoder_button", "button", "ready", "error", "raw"
    index: int = -1    # Index (Encoder 0–2, Button 0–5)
    value: int = 0     # Delta (Encoder) oder Press-State (Buttons: 1=press, 0=release)
    raw: Optional[dict] = None  # Originales JSON-Dict, falls man's braucht

    @property
    def pressed(self) -> bool:
        """Bequemer Zugriff: True wenn Button/Encoder-Taster gerade gedrückt wurde."""
        return self.kind in ("button", "encoder_button") and self.value == 1

    @property
    def released(self) -> bool:
        return self.kind in ("button", "encoder_button") and self.value == 0


# ──────────────────────────────────────────────────────────────────
# Hauptklasse
# ──────────────────────────────────────────────────────────────────
class StreamDeck:
    """High-Level-Schnittstelle zum Arduino-Stream-Deck."""

    BAUD = 115200
    NUM_SLOTS = 6

    def __init__(self, port: Optional[str] = None, baud: int = BAUD):
        self.port = port
        self.baud = baud
        self.ser: Optional[serial.Serial] = None

    # ───── Verbindung ─────
    def find_port(self) -> str:
        """Sucht automatisch nach einem angeschlossenen Arduino."""
        for p in serial.tools.list_ports.comports():
            desc = (p.description or "").lower()
            if any(k in desc for k in ("arduino", "uno", "usb-serial")):
                return p.device
        raise RuntimeError(
            "Kein Arduino gefunden. Verfügbare Ports:\n" +
            "\n".join(f"  {p.device} – {p.description}"
                      for p in serial.tools.list_ports.comports())
        )

    def connect(self, wait_for_ready: bool = True, timeout: float = 5.0):
        """Öffnet die Serial-Verbindung. Wartet optional auf das ready-Event."""
        if not self.port:
            self.port = self.find_port()
        self.ser = serial.Serial(self.port, self.baud, timeout=0.5)
        time.sleep(2.0)  # Arduino-Reset abwarten

        if wait_for_ready:
            t0 = time.time()
            while time.time() - t0 < timeout:
                line = self._readline()
                if line is None:
                    continue
                try:
                    obj = json.loads(line)
                    if obj.get("event") == "ready":
                        return
                except json.JSONDecodeError:
                    continue
            raise TimeoutError("Arduino hat nicht 'ready' gemeldet")

    def close(self):
        if self.ser:
            self.ser.close()
            self.ser = None

    # ───── Events empfangen ─────
    def _readline(self) -> Optional[str]:
        if not self.ser:
            return None
        try:
            raw = self.ser.readline()
        except serial.SerialException:
            return None
        if not raw:
            return None
        return raw.decode(errors="ignore").strip()

    def poll(self) -> Optional[StreamDeckEvent]:
        """Liest ein Event nicht-blockierend (oder bis Serial-Timeout abläuft)."""
        line = self._readline()
        if not line:
            return None
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            return StreamDeckEvent(kind="raw", raw={"line": line})

        kind = obj.get("event", "")
        return StreamDeckEvent(
            kind=kind,
            index=obj.get("index", -1),
            value=obj.get("value", 0),
            raw=obj,
        )

    def events(self) -> Generator[StreamDeckEvent, None, None]:
        """Endlos-Generator über alle eingehenden Events."""
        while True:
            evt = self.poll()
            if evt is not None:
                yield evt

    # ───── Befehle senden ─────
    def _send(self, payload: dict):
        if not self.ser:
            raise RuntimeError("Nicht verbunden")
        msg = json.dumps(payload, separators=(",", ":")) + "\n"
        self.ser.write(msg.encode())

    def send_image(self, slot: int, image):
        """
        Sendet ein Bild auf einen OLED-Slot.
        `image` darf sein:
          - PIL.Image (wird zu 128x64 1-bit konvertiert)
          - bytes der Länge 1024 (raw SSD1306-Page-Layout)
        """
        if isinstance(image, (bytes, bytearray)):
            if len(image) != 1024:
                raise ValueError(f"Bitmap muss 1024 Byte sein, ist {len(image)}")
            raw = bytes(image)
        else:
            raw = pil_to_ssd1306_bytes(image)

        self._send({
            "cmd": "image",
            "slot": slot,
            "data": base64.b64encode(raw).decode("ascii"),
        })

    def send_overlay(self, slot: int, label: str, value: int, duration_ms: int = 1000):
        """Zeigt eine temporäre Wertanzeige (Label + große Zahl + Pegelbalken)."""
        self._send({
            "cmd": "overlay",
            "slot": slot,
            "label": label[:15],
            "value": int(value),
            "duration_ms": int(duration_ms),
        })

    def send_overlay_for_encoder(self, encoder_index: int, label: str,
                                  value: int, duration_ms: int = 1000):
        """Bequemlichkeit: Overlay auf beide OLEDs eines Encoders gleichzeitig."""
        for slot in ENC_TO_SLOTS[encoder_index]:
            self.send_overlay(slot, label, value, duration_ms)

    def send_flash(self, slot: int):
        """Kurzes Invertieren des Bildschirms als Klick-Feedback."""
        self._send({"cmd": "flash", "slot": slot})

    def send_clear(self, slot: int):
        """Setzt den Slot in den Default-Zustand zurück."""
        self._send({"cmd": "clear", "slot": slot})


# ──────────────────────────────────────────────────────────────────
# Bitmap-Konvertierung
# ──────────────────────────────────────────────────────────────────
def pil_to_ssd1306_bytes(img: Image.Image) -> bytes:
    """
    Wandelt ein PIL-Image in das 1024-Byte SSD1306-Page-Layout.

    Der SSD1306 speichert das Display in 8 "Pages" (vertikale Streifen zu je
    8 Pixeln). Innerhalb einer Page entspricht ein Byte = 8 vertikalen Pixeln,
    LSB oben. Die Pages werden zeilenweise (Page 0, Page 1, ...) abgelegt.
    """
    img = img.convert("1").resize((128, 64))
    px = img.load()

    buf = bytearray(1024)
    for page in range(8):
        for x in range(128):
            b = 0
            for bit in range(8):
                if px[x, page * 8 + bit]:
                    b |= (1 << bit)
            buf[page * 128 + x] = b
    return bytes(buf)
