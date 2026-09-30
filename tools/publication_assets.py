"""Responsive image encoding, consistent brand icons and social preview graphics."""
from pathlib import Path
import hashlib
import html
import brand_mark
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent


def font(size, bold=False):
    candidates = [ROOT/'web/fonts'/('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'),
                  Path('C:/Windows/Fonts')/('segoeuib.ttf' if bold else 'segoeui.ttf'),
                  Path('/usr/share/fonts/truetype/dejavu')/('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')]
    for path in candidates:
        if path.exists(): return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


def icon(size):
    """The Crickrida mark on its night tile (see brand_mark.py)."""
    return brand_mark.icon(size)


def prepare_assets(out):
    dest=out/'assets/art';dest.mkdir(parents=True,exist_ok=True)
    source=ROOT/'web/art/cricket-hero-v2.png'
    with Image.open(source) as original:
        for width in (640,960,1536):
            target=dest/f'cricket-hero-{width}.webp'
            if not target.exists() or target.stat().st_mtime<source.stat().st_mtime:
                original.convert('RGB').resize((width,round(original.height*width/original.width)),Image.Resampling.LANCZOS).save(target,'WEBP',quality=82,method=6)
    # Keep source artwork in Git; publish only the responsive encodings.
    (dest/'cricket-hero-v1.png').unlink(missing_ok=True)
    (dest/'cricket-hero-v2.png').unlink(missing_ok=True)
    players=out/'assets/art/players'
    if players.exists():
        for path in list(players.iterdir()):
            if path.suffix.lower() in {'.png','.jpg','.jpeg'} and path.stem.endswith('-illustration'):
                Image.open(path).convert('RGBA').save(players/(path.stem+'.webp'),'WEBP',quality=88,method=6)
    for size,name in ((16,'favicon-16.png'),(32,'favicon-32.png'),(180,'apple-touch-icon.png'),(192,'icon-192.png'),(512,'icon-512.png')):
        icon(size).save(out/name)
    icon(64).save(out/'favicon.ico',sizes=[(16,16),(32,32),(48,48),(64,64)])
    brand_mark.icon(512, pad=0.26, rounded=False).convert('RGB').save(out/'icon-maskable.png')
    brand=out/'assets/brand';brand.mkdir(parents=True,exist_ok=True)
    brand_mark.icon(1024).save(brand/'crickrida-icon.png')
    brand_mark.wordmark(1500,300,stem='#0A0A0F',text='#0A0A0F').save(brand/'crickrida-wordmark.png')
    brand_mark.wordmark(1500,300).save(brand/'crickrida-wordmark-dark.png')
    (brand/'crickrida-mark.svg').write_text(brand_mark.svg_mark(stem='#0A0A0F'),encoding='utf-8')
    (brand/'crickrida-mark-on-dark.svg').write_text(brand_mark.svg_mark(stem=brand_mark.INK),encoding='utf-8')
    (brand/'crickrida-icon.svg').write_text(brand_mark.svg_icon(),encoding='utf-8')


def social_image(out,title,category='INTERNATIONAL CRICKET'):
    key=hashlib.sha256((title+'|'+category+'|play-k').encode()).hexdigest()[:16]
    url=f'/assets/social/{key}.png';target=out/url.lstrip('/')
    if target.exists(): return url
    target.parent.mkdir(parents=True,exist_ok=True)
    brand_mark.social_card(title,category).save(target,optimize=True)
    return url
