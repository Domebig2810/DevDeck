"""
streamdeck_demo.py

Vollständiges Demo: lauscht auf Events, zeigt Overlays beim Drehen,
flasht OLEDs beim Knopfdruck, und rendert ein paar Beispielbilder.

Start:
    python streamdeck_demo.py
"""

from __future__ import annotations

import time
from PIL import Image, ImageDraw, ImageFont

from streamdeck_protocol import StreamDeck, ENC_TO_SLOTS, BTN_TO_SLOT


# ──────────────────────────────────────────────────────────────────
# Beispiel-Belegung (austauschbar gegen eure echte Konfiguration)
# ──────────────────────────────────────────────────────────────────
ENCODER_CONFIG = {
    0: {"label": "VOL",  "value": 50, "min": 0, "max": 100},
    1: {"label": "MIC",  "value": 70, "min": 0, "max": 100},
    2: {"label": "GAIN", "value": 30, "min": 0, "max": 100},
}

BUTTON_LABELS = ["Szene 1", "Szene 2", "Szene 3",
                 "Aufnahme", "Stream", "Clip"]


# ──────────────────────────────────────────────────────────────────
# Bildgenerator – erzeugt schwarz-weiße 128x64 PIL-Images
# ──────────────────────────────────────────────────────────────────
def make_button_image(text: str, big: bool = True) -> Image.Image:
    """Erstellt ein 128x64-Image mit Rahmen und zentriertem Text."""
    img = Image.new("1", (128, 64), 0)
    draw = ImageDraw.Draw(img)

    # Rahmen
    draw.rectangle([(0, 0), (127, 63)], outline=1, width=1)

    # Text-Layout: Default-Font (PIL liefert den ohne Extra-Installation)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    # Zentrieren
    if font:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(((128 - tw) // 2, (64 - th) // 2 - 2), text, fill=1, font=font)
    else:
        draw.text((10, 28), text, fill=1)

    return img


def make_encoder_label_image(label: str, value: int) -> Image.Image:
    """Bild für ein OLED neben einem Encoder im Ruhezustand."""
    img = Image.new("1", (128, 64), 0)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (127, 63)], outline=1, width=1)

    font = ImageFont.load_default()
    draw.text((6, 6), label, fill=1, font=font)
    draw.text((6, 24), f"{value}", fill=1, font=font)

    # Mini-Balken am unteren Rand
    bar_w = int(116 * max(0, min(100, value)) / 100)
    draw.rectangle([(6, 54), (6 + bar_w, 59)], fill=1)
    return img


# ──────────────────────────────────────────────────────────────────
# Hauptlogik
# ──────────────────────────────────────────────────────────────────
def initial_render(sd: StreamDeck):
    """Sendet beim Start die Ruhe-Bilder an alle 6 OLEDs."""
    # OLEDs neben Encodern: Label + aktueller Wert
    for enc_idx, slots in ENC_TO_SLOTS.items():
        cfg = ENCODER_CONFIG[enc_idx]
        # Hier: beide OLEDs des Encoders zeigen dasselbe Label-Bild.
        # Ihr könnt das gerne ändern (z.B. links Label, rechts Icon).
        img = make_encoder_label_image(cfg["label"], cfg["value"])
        for slot in slots:
            sd.send_image(slot, img)
            time.sleep(0.05)  # I²C nicht überfahren

    # Falls Buttons unter eigenen, separaten OLEDs sitzen würden:
    # Bei deinem Layout sind die OLEDs aber gleichzeitig die Encoder-OLEDs.
    # Daher nichts weiteres zu rendern.


def handle_encoder(sd: StreamDeck, idx: int, delta: int):
    cfg = ENCODER_CONFIG[idx]
    cfg["value"] = max(cfg["min"], min(cfg["max"], cfg["value"] + delta))
    print(f"  Encoder {idx} ({cfg['label']}) = {cfg['value']:>3d}  ({delta:+d})")

    # Overlay auf beide zugehörigen OLEDs (1.2 Sekunden sichtbar)
    sd.send_overlay_for_encoder(idx, cfg["label"], cfg["value"], duration_ms=1200)


def handle_encoder_button(sd: StreamDeck, idx: int, pressed: bool):
    if not pressed:
        return
    cfg = ENCODER_CONFIG[idx]
    print(f"  Encoder-Taster {idx} ({cfg['label']}) GEDRÜCKT")
    # Beispiel: bei Druck auf 0 setzen (Mute) und anzeigen
    cfg["value"] = 0 if cfg["value"] > 0 else 50
    sd.send_overlay_for_encoder(idx, cfg["label"] + " M", cfg["value"], duration_ms=800)


def handle_button(sd: StreamDeck, idx: int, pressed: bool):
    if not pressed:
        return
    label = BUTTON_LABELS[idx]
    print(f"  Button {idx} ({label}) GEDRÜCKT")
    sd.send_flash(BTN_TO_SLOT[idx])


def main():
    print("Verbinde zu Stream Deck...")
    sd = StreamDeck(port="COM6")  # automatische Port-Suche
    sd.connect()
    print(f"Verbunden auf {sd.port}")

    print("Rendere Initial-Bilder...")
    initial_render(sd)
    print("Bereit. Drücken, drehen, oder Strg+C zum Beenden.\n")

    try:
        for evt in sd.events():
            if evt.kind == "encoder":
                handle_encoder(sd, evt.index, evt.value)
            elif evt.kind == "encoder_button":
                handle_encoder_button(sd, evt.index, evt.pressed)
            elif evt.kind == "button":
                handle_button(sd, evt.index, evt.pressed)
            elif evt.kind == "error":
                print(f"  [Arduino-Fehler] {evt.raw}")
            elif evt.kind == "raw":
                # Nicht-JSON-Zeile (z.B. Boot-Müll). Ignorieren oder loggen.
                pass
    except KeyboardInterrupt:
        print("\nBeendet.")
    finally:
        sd.close()


if __name__ == "__main__":
    main()
