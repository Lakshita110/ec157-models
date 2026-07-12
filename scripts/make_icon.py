"""Regenerate the home-screen app icons (DEV ONLY — output is committed).

    pip install pillow            # not a runtime dependency
    python scripts/make_icon.py   # optionally: python scripts/make_icon.py 🏋️

Writes src/jim/static/icon-{180,192,512}.png. The app just serves those bytes,
so production needs neither Pillow nor an emoji font — which matters, because
Render's Linux containers have no Segoe UI Emoji to render with.

iOS ignores SVG for `apple-touch-icon` and will screenshot the page instead, so
a real raster icon is the difference between a proper app tile and a blurry
thumbnail of the chat.
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

EMOJI = sys.argv[1] if len(sys.argv) > 1 else "💪"
EMOJI_FONT = "C:/Windows/Fonts/seguiemj.ttf"  # color emoji font (Windows)
OUT_DIR = Path(__file__).resolve().parent.parent / "src" / "jim" / "static"
SIZES = (180, 192, 512)  # apple-touch-icon, android, maskable/splash

BG_TOP = (31, 34, 24)     # brand near-black, lifted slightly at the top
BG_BOTTOM = (15, 16, 13)  # --bg
SS = 4                    # supersample, then downscale for clean edges


def render(size: int) -> Image.Image:
    big = size * SS
    img = Image.new("RGB", (big, big), BG_BOTTOM)

    # Vertical brand gradient so the tile isn't a flat black square.
    draw = ImageDraw.Draw(img)
    for y in range(big):
        t = y / big
        draw.line(
            [(0, y), (big, y)],
            fill=tuple(round(BG_TOP[c] + (BG_BOTTOM[c] - BG_TOP[c]) * t) for c in range(3)),
        )

    # Segoe UI Emoji only rasterizes color glyphs at specific sizes; 109px is the
    # documented bitmap strike. Render there, then scale to taste.
    font = ImageFont.truetype(EMOJI_FONT, 109)
    glyph = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(glyph).text((80, 80), EMOJI, font=font, embedded_color=True, anchor="mm")

    target = int(big * 0.62)  # generous padding: iOS masks the corners
    glyph = glyph.resize((target, target), Image.LANCZOS)
    img.paste(glyph, ((big - target) // 2, (big - target) // 2), glyph)

    return img.resize((size, size), Image.LANCZOS)


OUT_DIR.mkdir(parents=True, exist_ok=True)
for s in SIZES:
    path = OUT_DIR / f"icon-{s}.png"
    render(s).save(path, "PNG", optimize=True)
    print(f"wrote {path.relative_to(OUT_DIR.parent.parent.parent)}  ({path.stat().st_size} bytes)")
# The Windows console is cp1252 and cannot encode an emoji — print its codepoint.
codepoints = " ".join(f"U+{ord(c):04X}" for c in EMOJI)
print(f"\nIcon: {codepoints} — rerun with a different emoji to change it, e.g."
      ' python scripts/make_icon.py "\U0001f3cb"')
