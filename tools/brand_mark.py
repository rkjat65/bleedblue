"""The Crickrida mark ("Play K"): a K whose leg is a bat, with a ball and seam.

One geometry drives every rendering, so the header, favicons, app icons and
share images always match. Mark space is 244 x 240 units.
"""
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT_BOLD = ROOT / 'tools/fonts/SpaceGrotesk-Bold.ttf'
FONT_MEDIUM = ROOT / 'tools/fonts/SpaceGrotesk-Medium.ttf'

CYAN = '#00E5FF'      # the bat: the site's primary accent
MAGENTA = '#FF2D78'   # the ball: the site's second accent, and a red cricket ball
INK = '#E8E8ED'       # text on dark
NIGHT = '#0A0A0F'     # page background
PANEL = '#111118'
MUTED = '#8888A0'

W, H = 244, 240
STEM = [(0, 0), (66, 0), (66, 98), (0, 194)]
# Bat: its top end runs parallel to the stem's cut, its foot is flat with a rounded toe.
BAT = [(61.4, 125.9), (95.7, 76.0), (238.4, 234.1), ('q', 243.8, 240.0, 235.8, 240.0), (164.4, 240.0)]
BALL = (176.0, 42.0, 39.0)
SEAM_DIR = (0.5665, -0.8240)   # parallel to the stem's cut
SEAM_NORMAL = (0.8240, 0.5665)
SEAM_OFFSETS = (-5.5, 5.5)
SEAM_WIDTH = 4.5


def _bat_points(steps=8):
    pts = []
    for p in BAT:
        if p[0] == 'q':
            (x0, y0), (cx, cy, x1, y1) = pts[-1], p[1:]
            for i in range(1, steps + 1):
                t = i / steps
                pts.append(((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1,
                            (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1))
        else:
            pts.append(p)
    return pts


def _seam_segments(length=120):
    cx, cy, _ = BALL
    for k in SEAM_OFFSETS:
        ox, oy = cx + k * SEAM_NORMAL[0], cy + k * SEAM_NORMAL[1]
        yield (ox - length * SEAM_DIR[0], oy - length * SEAM_DIR[1], ox + length * SEAM_DIR[0], oy + length * SEAM_DIR[1])


def mark_paths():
    """SVG path data for the stem, the bat and the seam lines, in mark space."""
    stem = 'M' + ' L'.join(f'{x:g},{y:g}' for x, y in STEM) + 'Z'
    b = BAT
    bat = f'M{b[0][0]:g},{b[0][1]:g} L{b[1][0]:g},{b[1][1]:g} L{b[2][0]:g},{b[2][1]:g} Q{b[3][1]:g},{b[3][2]:g} {b[3][3]:g},{b[3][4]:g} L{b[4][0]:g},{b[4][1]:g}Z'
    seams = ' '.join(f'M{x0:.1f},{y0:.1f} L{x1:.1f},{y1:.1f}' for x0, y0, x1, y1 in _seam_segments())
    return stem, bat, seams


def svg_mark(stem='currentColor', bat=CYAN, ball=MAGENTA, mask_id='crSeam', label='Crickrida', width=None, height=None, extra=''):
    """The mark alone. The seam is cut out, so it shows whatever sits behind."""
    stem_d, bat_d, seams_d = mark_paths()
    cx, cy, r = BALL
    size = (f' width="{width}"' if width else '') + (f' height="{height}"' if height else '')
    aria = f' role="img" aria-label="{label}"' if label else ' aria-hidden="true"'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}"{size}{aria}{extra}>'
            f'<defs><mask id="{mask_id}"><rect width="{W}" height="{H}" fill="#fff"/>'
            f'<path d="{seams_d}" stroke="#000" stroke-width="{SEAM_WIDTH}" stroke-linecap="round"/></mask></defs>'
            f'<path d="{stem_d}" fill="{stem}"/><path d="{bat_d}" fill="{bat}"/>'
            f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" fill="{ball}" mask="url(#{mask_id})"/></svg>')


def svg_icon(tile=NIGHT, stem=INK, bat=CYAN, ball=MAGENTA, radius=58, pad=44):
    """Square app icon: the mark centred on a rounded tile (256 x 256)."""
    inner = 256 - 2 * pad
    scale = inner / max(W, H)
    dx = (256 - W * scale) / 2
    dy = (256 - H * scale) / 2
    mark = svg_mark(stem=stem, bat=bat, ball=ball, mask_id='crIcon', label=None)
    body = mark[mark.index('>') + 1:-len('</svg>')]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" role="img" aria-label="Crickrida">'
            f'<rect width="256" height="256" rx="{radius}" fill="{tile}"/>'
            f'<g transform="translate({dx:.2f} {dy:.2f}) scale({scale:.4f})">{body}</g></svg>')


@lru_cache(maxsize=8)
def font(size, bold=True):
    path = FONT_BOLD if bold else FONT_MEDIUM
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


def draw_mark(im, box, stem=INK, bat=CYAN, ball=MAGENTA, seam=None):
    """Draw the mark into ``box`` (x, y, w, h) of an RGBA image. ``seam`` is the
    colour behind the ball; None cuts the seam out to transparency."""
    x, y, w, h = box
    s = min(w / W, h / H)
    ox, oy = x + (w - W * s) / 2, y + (h - H * s) / 2
    pt = lambda px, py: (ox + px * s, oy + py * s)
    d = ImageDraw.Draw(im)
    d.polygon([pt(*p) for p in STEM], fill=stem)
    d.polygon([pt(*p) for p in _bat_points()], fill=bat)
    cx, cy, r = BALL
    d.ellipse([pt(cx - r, cy - r), pt(cx + r, cy + r)], fill=ball)
    colour = seam if seam else (0, 0, 0, 0)
    for x0, y0, x1, y1 in _seam_segments():
        layer = Image.new('L', im.size, 0)
        ImageDraw.Draw(layer).line([pt(x0, y0), pt(x1, y1)], fill=255, width=max(1, round(SEAM_WIDTH * s)))
        ball = Image.new('L', im.size, 0)
        ImageDraw.Draw(ball).ellipse([pt(cx - r, cy - r), pt(cx + r, cy + r)], fill=255)
        cut = Image.composite(layer, Image.new('L', im.size, 0), ball)
        im.paste(Image.new('RGBA', im.size, colour), (0, 0), cut)


def icon(size, tile=NIGHT, stem=INK, bat=CYAN, ball=MAGENTA, pad=0.17, rounded=True):
    """Square icon at ``size`` px, drawn at 4x and reduced for smooth edges."""
    big = size * 4
    im = Image.new('RGBA', (big, big), (0, 0, 0, 0))
    if tile:
        ImageDraw.Draw(im).rounded_rectangle((0, 0, big - 1, big - 1), radius=round(big * 0.22) if rounded else 0, fill=tile)
    inset = round(big * pad)
    draw_mark(im, (inset, inset, big - 2 * inset, big - 2 * inset), stem=stem, bat=bat, ball=ball, seam=tile)
    return im.resize((size, size), Image.Resampling.LANCZOS)


def wordmark(width, height, stem=INK, bat=CYAN, ball=MAGENTA, text=INK, background=None, tagline=None, tagline_colour=MUTED):
    """Mark plus the lowercase wordmark, left aligned and vertically centred."""
    scale = 3
    big = Image.new('RGBA', (width * scale, height * scale), background or (0, 0, 0, 0))
    mark_h = round(height * scale * (0.62 if tagline else 0.72))
    top = (height * scale - mark_h) // 2 - (round(height * scale * 0.06) if tagline else 0)
    draw_mark(big, (0, top, round(mark_h * W / H), mark_h), stem=stem, bat=bat, ball=ball, seam=background)
    f = font(round(mark_h * 0.78))
    d = ImageDraw.Draw(big)
    x = round(mark_h * W / H + mark_h * 0.16)
    bbox = d.textbbox((0, 0), 'crickrida', font=f)
    ty = top + mark_h - bbox[3] + round(mark_h * 0.02)
    d.text((x, ty), 'crickrida', font=f, fill=text)
    if tagline:
        tf = font(round(mark_h * 0.2), bold=False)
        d.text((x + round(mark_h * 0.02), top + mark_h + round(mark_h * 0.14)), tagline, font=tf, fill=tagline_colour)
    return big.resize((width, height), Image.Resampling.LANCZOS)


def social_card(title, category, lines_font=58):
    """1200 x 630 share image in the site palette."""
    im = Image.new('RGBA', (1200, 630), NIGHT)
    glow = Image.new('RGBA', (1200, 630), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for radius, alpha in ((360, 10), (250, 16), (150, 24)):
        gd.ellipse((1120 - radius, 110 - radius, 1120 + radius, 110 + radius), fill=(0, 229, 255, alpha))
    im.alpha_composite(glow)
    im.alpha_composite(wordmark(360, 70), (60, 44))
    d = ImageDraw.Draw(im)
    d.text((64, 170), category.upper(), font=font(20), fill=CYAN)
    lines, line, tf = [], '', font(lines_font)
    for word in title.split():
        candidate = (line + ' ' + word).strip()
        if d.textlength(candidate, font=tf) > 1040 and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    for i, text in enumerate(lines[:4]):
        d.text((60, 212 + i * 72), text, font=tf, fill=INK)
    d.line((60, 548, 1140, 548), fill='#1E1E2A', width=2)
    d.text((64, 570), 'INTERNATIONALS  ·  IPL  ·  T20 WORLD CUP', font=font(18, bold=False), fill=MUTED)
    d.text((1140 - d.textlength('crickrida.com', font=font(22)), 566), 'crickrida.com', font=font(22), fill=CYAN)
    return im.convert('RGB')
