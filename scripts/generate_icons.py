import os

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "static")
os.makedirs(OUT_DIR, exist_ok=True)


def make_icon(size, filename, bg="#000000", fg="#00d1ff"):
    img = Image.new("RGBA", (size, size), bg)
    draw = ImageDraw.Draw(img)
    # draw a simple rounded square with gradient-like effect
    pad = int(size * 0.08)
    bbox = (pad, pad, size - pad, size - pad)
    draw.ellipse(bbox, fill=fg)
    # draw letter G
    try:
        font_size = int(size * 0.5)
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()
    text = "G"
    w, h = draw.textsize(text, font=font)
    draw.text(((size - w) / 2, (size - h) / 2 - size * 0.03), text, font=font, fill="white")
    out_path = os.path.join(OUT_DIR, filename)
    img.save(out_path)
    print("Wrote", out_path)


if __name__ == "__main__":
    make_icon(192, "espaceimage-192.png")
    make_icon(512, "espaceimage-512.png")
