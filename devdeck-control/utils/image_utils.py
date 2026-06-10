from PIL import Image, ImageDraw, ImageFont


def convert_to_bmp_128x64(input_path, output_path):
    img = Image.open(input_path)
    img = img.convert("L")
    img = img.resize((128, 64), Image.Resampling.LANCZOS)
    img = img.point(lambda x: 255 if x > 128 else 0, mode='1')
    img.save(output_path, format="BMP")


def pil_to_ssd1306_bytes(img: Image.Image) -> bytes:
    """
    Wandelt ein PIL-Image in das 1024-Byte SSD1306-Page-Layout.

    Der SSD1306 speichert das Display in 8 "Pages" (vertikale Streifen zu je
    8 Pixeln). Ein Byte = 8 vertikale Pixel, LSB oben.
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


def image_file_to_ssd1306(path: str) -> bytes:
    img = Image.open(path).convert("L").resize((128, 64), Image.Resampling.LANCZOS)
    img = img.point(lambda x: 255 if x > 128 else 0, mode="1")
    return pil_to_ssd1306_bytes(img)


def render_label_to_ssd1306(text: str) -> bytes:
    """Rendert einen Text zentriert auf 128x64 für die OLED-Anzeige."""
    img = Image.new("1", (128, 64), 0)
    draw = ImageDraw.Draw(img)

    text = (text or "").strip()
    if text:
        size = 22 if len(text) <= 8 else 16 if len(text) <= 12 else 12
        try:
            font = ImageFont.load_default(size=size)
        except TypeError:  # Pillow < 10.1
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((128 - w) // 2 - bbox[0], (64 - h) // 2 - bbox[1]), text, fill=1, font=font)
        draw.rectangle([0, 0, 127, 63], outline=1)

    return pil_to_ssd1306_bytes(img)
