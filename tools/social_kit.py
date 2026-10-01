"""Profile pictures, headers, grid posts and highlight covers for X and Instagram.

Everything is drawn from the same mark geometry and palette as the site
(tools/brand_mark.py), so the accounts match crickrida.com. Output goes to
brand/social/. The decorative bars are real: total IPL runs in each season.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from brand_mark import CYAN, INK, MAGENTA, MUTED, NIGHT, draw_mark, font, wordmark, W as MARK_W, H as MARK_H

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'brand' / 'social'
GRID = (20, 20, 29, 255)
GOLD = '#FFB800'
VIOLET = '#A78BFA'
LIME = '#B8FF00'
ROSE = '#FF5C7A'


def rgb(hex_colour, alpha=255):
    h = hex_colour.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)


def canvas(w, h):
    return Image.new('RGBA', (w, h), rgb(NIGHT))


def grid(im, step):
    d = ImageDraw.Draw(im)
    for x in range(0, im.width, step):
        d.line((x, 0, x, im.height), fill=GRID, width=1)
    for y in range(0, im.height, step):
        d.line((0, y, im.width, y), fill=GRID, width=1)


def glow(im, cx, cy, radius, colour=CYAN, strength=60):
    layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=rgb(colour, strength))
    layer = layer.filter(ImageFilter.GaussianBlur(radius * 0.45))
    im.alpha_composite(layer)


def mark(im, cx, cy, size, stem=INK):
    """The mark centred at (cx, cy), drawn at 4x and reduced; the seam shows the background."""
    big = Image.new('RGBA', (size * 4, round(size * 4 * MARK_H / MARK_W)), (0, 0, 0, 0))
    draw_mark(big, (0, 0, big.width, big.height), stem=stem, seam=None)
    small = big.resize((size, round(size * MARK_H / MARK_W)), Image.Resampling.LANCZOS)
    im.alpha_composite(small, (round(cx - small.width / 2), round(cy - small.height / 2)))


def text(im, xy, value, size, colour=INK, bold=True, anchor='la', spacing=0):
    d = ImageDraw.Draw(im)
    f = font(size, bold)
    if not spacing:
        d.text(xy, value, font=f, fill=colour, anchor=anchor)
        return d.textlength(value, font=f)
    x, y = xy
    total = sum(d.textlength(c, font=f) for c in value) + spacing * (len(value) - 1)
    if anchor[0] == 'm':
        x -= total / 2
    for c in value:
        d.text((x, y), c, font=f, fill=colour, anchor='l' + anchor[1])
        x += d.textlength(c, font=f) + spacing
    return total


def season_runs():
    """Total IPL runs scored in each season, from the league snapshot."""
    path = ROOT / 'data' / 'leagues' / 'ipl.json'
    if not path.exists():
        return []
    totals = {}
    for p in json.loads(path.read_text(encoding='utf-8'))['players'].values():
        for s in p.get('seasons') or []:
            totals[s['edition']] = totals.get(s['edition'], 0) + (s.get('runs') or 0)
    return [totals[k] for k in sorted(totals)]


def bars(im, box, values, alpha=70, gap=0.32):
    """Season bars in cyan, the latest in magenta, faded so they sit behind text."""
    if not values:
        return
    x0, y0, x1, y1 = box
    layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    slot = (x1 - x0) / len(values)
    peak = max(values)
    for i, v in enumerate(values):
        h = (y1 - y0) * v / peak
        colour = MAGENTA if i == len(values) - 1 else CYAN
        left = x0 + i * slot + slot * gap / 2
        d.rounded_rectangle((left, y1 - h, left + slot * (1 - gap), y1), radius=max(2, slot * 0.12), fill=rgb(colour, alpha))
    im.alpha_composite(layer)


def profile(size=1080):
    """Circle-safe avatar: the mark fills about 58% of the width, centred on night."""
    s = size * 2
    im = canvas(s, s)
    glow(im, s * 0.52, s * 0.5, s * 0.36, CYAN, 46)
    glow(im, s * 0.70, s * 0.32, s * 0.16, MAGENTA, 40)
    mark(im, s / 2 + s * 0.012, s / 2, round(s * 0.58))
    return im.resize((size, size), Image.Resampling.LANCZOS).convert('RGB')


def x_header():
    """1500 x 500. Text sits right of centre; the avatar covers the bottom-left corner."""
    scale = 2
    im = canvas(1500 * scale, 500 * scale)
    grid(im, 50 * scale)
    bars(im, (1010 * scale, 300 * scale, 1460 * scale, 460 * scale), season_runs(), alpha=70)
    glow(im, 640 * scale, 200 * scale, 420 * scale, CYAN, 26)
    lock = wordmark(720 * scale, 150 * scale)
    im.alpha_composite(lock, (430 * scale, 70 * scale))
    text(im, (442 * scale, 262 * scale), 'Cricket in numbers.', 44 * scale, INK, bold=True)
    text(im, (444 * scale, 330 * scale), 'TESTS  ·  ODIS  ·  T20IS  ·  IPL  ·  T20 WORLD CUP', 19 * scale, MUTED, bold=False, spacing=2 * scale)
    text(im, (444 * scale, 380 * scale), 'crickrida.com', 26 * scale, CYAN, bold=True)
    return im.resize((1500, 500), Image.Resampling.LANCZOS).convert('RGB')


def instagram_grid():
    """Three 1080 x 1440 posts that read as one banner on the profile grid.
    Post them right tile first, so they appear left to right."""
    w, h = 1080, 1440
    im = canvas(w * 3, h)
    grid(im, 60)
    values = season_runs()
    bars(im, (120, 1170, w * 3 - 120, 1330), values, alpha=60)
    # Left tile: the mark.
    glow(im, w * 0.5, 620, 420, CYAN, 40)
    glow(im, w * 0.66, 460, 190, MAGENTA, 34)
    mark(im, w * 0.5, 640, 560)
    # Middle tile: the name.
    text(im, (w * 1.5, 560), 'crickrida', 190, INK, anchor='ms')
    text(im, (w * 1.5, 680), 'Cricket in numbers.', 66, CYAN, bold=False, anchor='ms')
    text(im, (w * 1.5, 800), 'Free. No sign-up.', 44, MUTED, bold=False, anchor='ms')
    # Right tile: what is inside, in the site's format colours.
    rows = [('Tests', ROSE), ('ODIs', CYAN), ('T20Is', LIME), ('IPL', GOLD), ('T20 World Cup', VIOLET)]
    d = ImageDraw.Draw(im)
    x, y = w * 2 + 190, 300
    for label, colour in rows:
        d.ellipse((x, y - 17, x + 34, y + 17), fill=colour)
        text(im, (x + 64, y), label, 72, INK, anchor='lm')
        y += 120
    text(im, (x, y + 10), 'Men and women.', 40, MUTED, bold=False, anchor='lm')
    text(im, (w * 2.5, 1060), 'crickrida.com', 58, CYAN, anchor='ms')
    return [im.crop((i * w, 0, (i + 1) * w, h)).convert('RGB') for i in range(3)], im.convert('RGB')


def highlight(label, colour):
    """1080 x 1920 story cover; Instagram shows the centre as a circle."""
    im = canvas(1080, 1920)
    glow(im, 540, 960, 330, colour, 50)
    d = ImageDraw.Draw(im)
    d.ellipse((540 - 300, 960 - 300, 540 + 300, 960 + 300), outline=colour, width=14)
    size = 150 if len(label) <= 4 else 112 if len(label) <= 6 else 92
    text(im, (540, 960), label, size, INK, anchor='mm')
    return im.convert('RGB')


HIGHLIGHTS = [('IPL', GOLD), ('T20 WC', VIOLET), ('Tests', ROSE), ('ODIs', CYAN), ('T20Is', LIME), ('Records', MAGENTA)]


def circle_preview(im, size=400):
    """How a platform's round crop will show the avatar."""
    small = im.resize((size, size), Image.Resampling.LANCZOS).convert('RGBA')
    mask = Image.new('L', (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    mask = mask.resize((size, size), Image.Resampling.LANCZOS)
    out = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    out.paste(small, (0, 0), mask)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    avatar = profile(1080)
    avatar.save(OUT / 'profile-1080.png', optimize=True)
    avatar.resize((400, 400), Image.Resampling.LANCZOS).save(OUT / 'x-profile-400.png', optimize=True)
    circle_preview(avatar).save(OUT / 'preview-profile-circle.png', optimize=True)
    x_header().save(OUT / 'x-header-1500x500.png', optimize=True)
    tiles, banner = instagram_grid()
    for i, tile in enumerate(tiles, 1):
        tile.save(OUT / f'instagram-grid-{i}.png', optimize=True)
    banner.resize((1620, 720), Image.Resampling.LANCZOS).save(OUT / 'preview-instagram-grid.png', optimize=True)
    for label, colour in HIGHLIGHTS:
        highlight(label, colour).save(OUT / f'instagram-highlight-{label.lower().replace(" ", "-")}.png', optimize=True)
    print('\n'.join(sorted(p.name for p in OUT.glob('*.png'))))


if __name__ == '__main__':
    main()
