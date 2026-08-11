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

# Physical sticker size: 2in (width) x 1in (height), logo/header in the top
# half, barcode in the bottom half. DPI controls the pixel resolution used
# when rendering/printing (embedded in the PNG so printers size it correctly).
STICKER_WIDTH_IN = 2.0
STICKER_HEIGHT_IN = 1.0
STICKER_DPI = int(os.environ.get("STICKER_DPI", "300"))

CANVAS_WIDTH = round(STICKER_WIDTH_IN * STICKER_DPI)
CANVAS_HEIGHT = round(STICKER_HEIGHT_IN * STICKER_DPI)
HEADER_HEIGHT = CANVAS_HEIGHT // 2  # top half
BARCODE_AREA_HEIGHT = CANVAS_HEIGHT - HEADER_HEIGHT  # bottom half
MARGIN = max(2, STICKER_DPI // 75)  # small breathing room around each half


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


def _build_header(width: int, height: int) -> Image.Image:
    """Return a header image (top half): organization logo if present, else org name text."""
    header = Image.new("RGB", (width, height), "white")
    max_w, max_h = width - MARGIN * 2, height - MARGIN * 2

    if os.path.exists(LOGO_PATH):
        logo = _load_logo_on_white(LOGO_PATH)
        # Scale logo to fit within the header while preserving aspect ratio.
        ratio = min(max_w / logo.width, max_h / logo.height)
        new_size = (max(1, int(logo.width * ratio)), max(1, int(logo.height * ratio)))
        logo = logo.resize(new_size)
        x = (width - logo.width) // 2
        y = (height - logo.height) // 2
        header.paste(logo, (x, y))
    else:
        draw = ImageDraw.Draw(header)
        font = _load_font(max(10, height // 3))
        text = ORG_NAME
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(
            ((width - text_w) / 2, (height - text_h) / 2),
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
    """Build a printable 2in x 1in sticker: org header in the top half,
    barcode centered in the bottom half."""
    canvas = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), "white")

    header_img = _build_header(CANVAS_WIDTH, HEADER_HEIGHT)
    canvas.paste(header_img, (0, 0))

    barcode_img = generate_barcode_image(barcode_string)
    # Fit the barcode within the bottom half, preserving aspect ratio (no
    # stretching/distortion), then center it in that half.
    max_w = CANVAS_WIDTH - MARGIN * 2
    max_h = BARCODE_AREA_HEIGHT - MARGIN * 2
    ratio = min(max_w / barcode_img.width, max_h / barcode_img.height)
    new_size = (max(1, int(barcode_img.width * ratio)), max(1, int(barcode_img.height * ratio)))
    barcode_img = barcode_img.resize(new_size)

    x = (CANVAS_WIDTH - barcode_img.width) // 2
    y = HEADER_HEIGHT + (BARCODE_AREA_HEIGHT - barcode_img.height) // 2
    canvas.paste(barcode_img, (x, y))

    output = io.BytesIO()
    canvas.save(output, format="PNG", dpi=(STICKER_DPI, STICKER_DPI))
    output.seek(0)
    return output
