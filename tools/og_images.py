#!/usr/bin/env python3
"""Generates 1200x630 social share images into static/og/.

Optional tool (the site build does not need it). Requires Pillow:
    python -m pip install pillow
    python tools/og_images.py

Re-run after adding a guide or changing a title. One image per guide plus
a default card for every other page.
"""
import json
import math
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "static" / "og"
FONTS = Path("C:/Windows/Fonts")

PAPER = (243, 239, 230)
INK = (22, 21, 19)
MUTED = (110, 104, 94)
ACCENT = (210, 64, 31)
W, H = 1200, 630
PAD = 72


def font(names, size):
    for name in names:
        for base in (FONTS, Path("/usr/share/fonts/truetype/dejavu"), Path("/Library/Fonts")):
            p = base / name
            if p.exists():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size)


WORDMARK = lambda s: font(["impact.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"], s)
TITLE = lambda s: font(["georgiab.ttf", "DejaVuSerif-Bold.ttf", "Georgia Bold.ttf"], s)
LABEL = lambda s: font(["arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"], s)


def star(draw, cx, cy, r, fill):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    draw.polygon(pts, fill=fill)


def wrap(draw, text, fnt, width):
    words, lines, line = text.split(), [], ""
    for w in words:
        test = (line + " " + w).strip()
        if draw.textlength(test, font=fnt) <= width:
            line = test
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def card(path, kicker, title, site_name):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    # frame rules, top and bottom (double rule like the site masthead)
    d.rectangle([PAD, 58, W - PAD, 62], fill=INK)
    d.rectangle([PAD, 68, W - PAD, 69], fill=INK)
    d.rectangle([PAD, H - 70, W - PAD, H - 69], fill=INK)
    # wordmark + six stars
    wm = WORDMARK(46)
    d.text((PAD, 92), site_name.upper(), font=wm, fill=INK)
    for i in range(6):
        star(d, W - PAD - 18 - i * 44, 120, 17, ACCENT)
    # kicker
    d.text((PAD, 200), kicker.upper(), font=LABEL(24), fill=ACCENT)
    # title, auto-shrunk to fit four lines
    for size in (78, 70, 62, 56, 50, 44):
        f = TITLE(size)
        lines = wrap(d, title, f, W - 2 * PAD)
        if len(lines) <= 4:
            break
    y = 244
    for ln in lines:
        d.text((PAD, y), ln, font=f, fill=INK)
        y += int(size * 1.12)
    d.text((PAD, H - 56), "Unofficial GTA 6 field guide · checked against multiple sources",
           font=LABEL(20), fill=MUTED)
    OUT.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True)


def logo(path):
    """512x512 square logo for structured data (publisher.logo)."""
    img = Image.new("RGB", (512, 512), INK)
    d = ImageDraw.Draw(img)
    for i, (cx, cy) in enumerate([(136, 176), (256, 176), (376, 176), (136, 336), (256, 336), (376, 336)]):
        star(d, cx, cy, 58, ACCENT if i < 6 else PAPER)
    img.save(path, optimize=True)


def front_matter(src):
    m = re.match(r"^---\r?\n(.*?)\r?\n---", src, re.S)
    data = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                data[k.strip()] = v.strip()
    return data


def main():
    site = json.loads((ROOT / "data/site.json").read_text(encoding="utf-8"))
    name = site["name"]
    card(OUT / "default.png", "GTA 6 map · cheats · money", site["headline"], name)
    logo(OUT / "logo.png")
    count = 2
    for p in sorted((ROOT / "content/guides").glob("*.md")):
        meta = front_matter(p.read_text(encoding="utf-8"))
        slug = meta.get("slug") or p.stem
        card(OUT / f"{slug}.png", "GTA 6 guide", meta.get("short", slug), name)
        count += 1
    print(f"Wrote {count} images to {OUT}")


if __name__ == "__main__":
    sys.exit(main())
