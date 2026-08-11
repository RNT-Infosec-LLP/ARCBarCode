"""Barcode generation (python-barcode) + sticker composition (Pillow)."""
import io
import os

import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ORG_NAME = os.environ.get("ORG_NAME", "ARC")
LOGO_PATH = os.environ.get("LOGO_PATH", "logo.png")  # optional, falls back to text header
STICKER_WIDTH = 500
HEADER_HEIGHT = 80
PADDING = 10


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """Best-effort font loader that falls back to PIL's default bitmap font."""
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


def _load_logo_on_white(path: str) -> Image.Image:
    """Load a (possibly transparent) logo and flatten it onto a white background."""
    logo = Image.open(path)
    if logo.mode in ("RGBA", "LA") or (logo.mode == "P" and "transparency" in logo.info):
        logo = logo.convert("RGBA")
        flattened = Image.new("RGB", logo.size, "white")
        flattened.paste(logo, mask=logo.split()[-1])
        return flattened
    return logo.convert("RGB")


def _build_header(width: int) -> Image.Image:
    """Return a header image: organization logo if present, else org name text."""
    header = Image.new("RGB", (width, HEADER_HEIGHT), "white")

    if os.path.exists(LOGO_PATH):
        logo = _load_logo_on_white(LOGO_PATH)
        # Scale logo to fit within the header while preserving aspect ratio.
        ratio = min(width / logo.width, HEADER_HEIGHT / logo.height)
        new_size = (max(1, int(logo.width * ratio)), max(1, int(logo.height * ratio)))
        logo = logo.resize(new_size)
        x = (width - logo.width) // 2
        y = (HEADER_HEIGHT - logo.height) // 2
        header.paste(logo, (x, y))
    else:
        draw = ImageDraw.Draw(header)
        font = _load_font(32)
        text = ORG_NAME
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(
            ((width - text_w) / 2, (HEADER_HEIGHT - text_h) / 2),
            text,
            fill="black",
            font=font,
        )

    return header


def generate_barcode_image(barcode_string: str) -> Image.Image:
    """Generate a code128 barcode image for the given string."""
    code128 = barcode.get_barcode_class("code128")
    writer = ImageWriter()
    writer.set_options({"write_text": True, "module_height": 10, "quiet_zone": 2})
    instance = code128(barcode_string, writer=writer)

    buffer = io.BytesIO()
    instance.write(buffer)
    buffer.seek(0)
    return Image.open(buffer).convert("RGB")


def generate_sticker(barcode_string: str) -> io.BytesIO:
    """Build a printable sticker: org header on top, barcode underneath."""
    barcode_img = generate_barcode_image(barcode_string)

    # Fit barcode width to the sticker width, preserving aspect ratio.
    ratio = STICKER_WIDTH / barcode_img.width
    barcode_img = barcode_img.resize(
        (STICKER_WIDTH, int(barcode_img.height * ratio))
    )

    header_img = _build_header(STICKER_WIDTH)

    canvas_height = HEADER_HEIGHT + barcode_img.height + PADDING * 3
    canvas = Image.new("RGB", (STICKER_WIDTH, canvas_height), "white")
    canvas.paste(header_img, (0, PADDING))
    canvas.paste(barcode_img, (0, HEADER_HEIGHT + PADDING * 2))

    output = io.BytesIO()
    canvas.save(output, format="PNG")
    output.seek(0)
    return output
