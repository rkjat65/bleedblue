"""Responsive image encoding, consistent brand icons and social preview graphics."""
from pathlib import Path
import hashlib
import html
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
    """Draw the same simple wicket mark used by logo.svg, at retina resolution."""
    unit=4; im=Image.new('RGBA',(64*unit,64*unit)); draw=ImageDraw.Draw(im)
    draw.rounded_rectangle((0,0,256,256),radius=64,fill='#205ed2')
    for x in (20,32,44): draw.line((x*unit,23*unit,x*unit,50*unit), fill='white',width=16)
    for start,end in ((18,36),(38,48)): draw.line((start*unit,18*unit,end*unit,18*unit), fill='white',width=16)
    draw.line((14*unit,52*unit,50*unit,52*unit),fill='#9fcaff',width=8)
    draw.ellipse((43*unit,6*unit,55*unit,18*unit), fill='#efb75b')
    draw.arc((44*unit,6*unit,52*unit,18*unit),80,270,fill='#10233f',width=4)
    return im.resize((size,size),Image.Resampling.LANCZOS)


def prepare_assets(out):
    dest=out/'assets/art';dest.mkdir(parents=True,exist_ok=True)
    source=ROOT/'web/art/cricket-hero-v2.png'
    with Image.open(source) as original:
        for width in (640,960,1536):
            target=dest/f'cricket-hero-{width}.webp'
            if not target.exists() or target.stat().st_mtime<source.stat().st_mtime:
                original.convert('RGB').resize((width,round(original.height*width/original.width)),Image.Resampling.LANCZOS).save(target,'WEBP',quality=82,method=6)
    # The source artwork stays in the repository; published pages use responsive encodings.
    (dest/'cricket-hero-v1.png').unlink(missing_ok=True)
    for size,name in ((16,'favicon-16.png'),(32,'favicon-32.png'),(180,'apple-touch-icon.png'),(192,'icon-192.png'),(512,'icon-512.png')):
        icon(size).save(out/name)
    icon(64).save(out/'favicon.ico',sizes=[(16,16),(32,32),(48,48),(64,64)])
    masked=Image.new('RGB',(512,512),'#205ed2');masked.paste(icon(358),(77,77),icon(358));masked.save(out/'icon-maskable.png')
    brand=out/'assets/brand';brand.mkdir(parents=True,exist_ok=True)
    icon(1024).save(brand/'cricket-wicket-icon.png')
    wordmark=Image.new('RGBA',(1500,300));wordmark.paste(icon(240),(30,30))
    d=ImageDraw.Draw(wordmark);d.text((310,65),'CRICKET WICKET',font=font(90,True),fill='#10233f');d.text((315,184),'INTERNATIONAL CRICKET, IN PERSPECTIVE',font=font(25),fill='#4e6686');wordmark.save(brand/'cricket-wicket-wordmark.png')


def social_image(out,title,category='INTERNATIONAL CRICKET'):
    key=hashlib.sha256((title+'|'+category).encode()).hexdigest()[:16]
    url=f'/assets/social/{key}.png';target=out/url.lstrip('/')
    if target.exists(): return url
    target.parent.mkdir(parents=True,exist_ok=True)
    im=Image.new('RGB',(1200,630),'#081b35');d=ImageDraw.Draw(im)
    for radius,colour in ((330,'#0b2447'),(235,'#102f59'),(140,'#17427a')):
        d.ellipse((1110-radius,180-radius,1110+radius,180+radius),fill=colour)
    im.paste(icon(66),(60,48),icon(66));d.text((145,60),'CRICKET WICKET',font=font(29,True),fill='white')
    d.text((64,170),category.upper(),font=font(20,True),fill='#8fbfff')
    lines=[];line='';titlefont=font(58,True)
    for word in title.split():
        candidate=(line+' '+word).strip()
        if d.textlength(candidate,font=titlefont)>1020 and line:lines.append(line);line=word
        else:line=candidate
    if line:lines.append(line)
    for i,line in enumerate(lines[:4]):d.text((60,215+i*73),line,font=titlefont,fill='#f2f7ff')
    d.line((60,545,1140,545),fill='#2d4b70',width=2)
    d.text((64,571),'TESTS  /  ODIs  /  T20Is     •     MEN & WOMEN',font=font(18),fill='#adc5e4')
    d.text((912,570),'cricket.rkjat.in',font=font(21,True),fill='#efb75b')
    im.save(target,optimize=True)
    return url
