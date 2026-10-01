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
    # The homepage no longer uses stadium artwork; remove encodings left by earlier builds.
    for name in ('cricket-hero-640.webp','cricket-hero-960.webp','cricket-hero-1536.webp','cricket-hero-v1.png','cricket-hero-v2.png'):
        (dest/name).unlink(missing_ok=True)
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


TEAM_CODES={'Netherlands':'NED','United States of America':'USA','United Arab Emirates':'UAE','Papua New Guinea':'PNG','Hong Kong':'HK',
            'South Korea':'KOR','Ivory Coast':'CIV','Isle of Man':'IOM','Cayman Islands':'CAY','Saudi Arabia':'KSA','Turks and Caicos Island':'TCI',
            'Czech Republic':'CZE','Costa Rica':'CRC','Sierra Leone':'SLE','St Helena':'SHN','Timor-Leste':'TLS','Cook Islands':'COK','East Africa':'EAF',
            'Young England':'YEN','Trinidad and Tobago':'TTO','Falkland Islands':'FLK','Denmark':'DEN','Germany':'GER','Switzerland':'SUI','Portugal':'POR',
            'Greece':'GRE','Bahamas':'BAH','Bahrain':'BRN','Malaysia':'MAS','Indonesia':'INA','Philippines':'PHI','Singapore':'SIN','Swaziland':'SWZ',
            'Eswatini':'SWZ','Guernsey':'GUE','Jersey':'JER','Gibraltar':'GIB','Mongolia':'MGL','Maldives':'MDV','Bhutan':'BHU','Myanmar':'MYA',
            'ICC World XI':'WXI','World XI':'WXI','World':'WLD','Asia XI':'AXI','Africa XI':'FXI','International XI':'IXI','Kuwait':'KUW','Qatar':'QAT',
            'Oman':'OMA','Nigeria':'NGR','Botswana':'BOT','Tanzania':'TAN','Zambia':'ZAM','Malawi':'MWI','Cameroon':'CMR','Gambia':'GAM','Lesotho':'LES'}


def team_code(team):
    if team in TEAM_CODES:return TEAM_CODES[team]
    words=[w for w in team.replace('-',' ').split() if w.lower() not in ('and','of','the')]
    return ''.join(w[0] for w in words[:3]).upper() if len(words)>1 else team[:3].upper()


def team_flags(out,teams):
    """Hand-drawn flags exist for the full members and a few associates. Every other side gets a
    neutral badge with its code rather than a guessed flag."""
    from player_profile import slug
    dest=out/'assets/flags';dest.mkdir(parents=True,exist_ok=True)
    for team in teams:
        target=dest/f'{slug(team)}.svg'
        if target.exists():continue
        code=team_code(team)
        target.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 28 20" role="img" aria-label="{html.escape(team)}">'
                          '<rect width="28" height="20" rx="3" fill="#1d2735"/><rect x=".5" y=".5" width="27" height="19" rx="2.5" fill="none" stroke="#3a4a5f"/>'
                          f'<text x="14" y="13.4" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="{7.8 if len(code)<3 else 7}" font-weight="700" fill="#e6edf3">{code}</text></svg>',encoding='utf-8')


def social_image(out,title,category='INTERNATIONAL CRICKET'):
    key=hashlib.sha256((title+'|'+category+'|play-k').encode()).hexdigest()[:16]
    url=f'/assets/social/{key}.png';target=out/url.lstrip('/')
    if target.exists(): return url
    target.parent.mkdir(parents=True,exist_ok=True)
    brand_mark.social_card(title,category).save(target,optimize=True)
    return url
