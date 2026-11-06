"""Generate the skill icons (docs/assets/icon-108.png and icon-512.png)."""

import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = 2048
BG, FG, WAVE = (15, 23, 42), (56, 189, 248), (125, 211, 252)

img = Image.new("RGB", (S, S), BG)
d = ImageDraw.Draw(img)
c = S // 2
cy = c + 140  # visual centre, a bit low to leave room for the waves
w = 120  # stroke width

# Power symbol: open ring + vertical bar.
r = 430
d.arc([c - r, cy - r, c + r, cy + r], start=-55, end=235, fill=FG, width=w)
d.rounded_rectangle([c - w // 2, cy - r - 80, c + w // 2, cy - 40], radius=w // 2, fill=FG)

# Signal waves above, like a broadcast (the Echo sending the magic packet).
for i, rr in enumerate((700, 880)):
    d.arc([c - rr, cy - rr, c + rr, cy + rr], start=-125, end=-55,
          fill=WAVE, width=int(w * 0.75))

for size in (512, 108):
    img.resize((size, size), Image.LANCZOS).save(
        os.path.join(ROOT, "docs", "assets", f"icon-{size}.png"), optimize=True)
print("icons written")
