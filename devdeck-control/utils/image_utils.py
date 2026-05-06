from PIL import Image


def convert_to_bmp_128x64(input_path, output_path):
    img = Image.open(input_path)
    img = img.convert("L")
    img = img.resize((128, 64), Image.Resampling.LANCZOS)
    img = img.point(lambda x: 255 if x > 128 else 0, mode='1')
    img.save(output_path, format="BMP")