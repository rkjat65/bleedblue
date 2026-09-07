"""Collect individually licensed Commons portraits for a curated player list.

Run: python tools/fetch_portraits.py [--refresh] [--limit 10]
Only Wikipedia article lead images hosted on Commons are eligible. Exact name,
country, and (when supplied) stable player ID resolve identity before requesting
metadata. Commons author and an allowed commercial-use license are required.
Cached responses make collection resumable; rejected files are never published.
Images are resized proportionally, without generating or changing player faces.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
from html import unescape
from html.parser import HTMLParser
from io import BytesIO
import json
from pathlib import Path
import re
import time
from urllib.parse import urlencode, quote, urlparse
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / '.data-cache' / 'portraits'
USER_AGENT = 'CricketWicket/1.0 (https://cricket.rkjat.in; international cricket reference)'

# Explicit article disambiguation and country prevent collisions (e.g. Rashid
# Khan of Afghanistan versus the Pakistan player, and two Australian Smiths).
TARGETS = [
    ('Sachin Tendulkar', 'India', 'Sachin Tendulkar'),
    ('Virat Kohli', 'India', 'Virat Kohli'),
    ('Rohit Sharma', 'India', 'Rohit Sharma'),
    ('Jasprit Bumrah', 'India', 'Jasprit Bumrah'),
    ('Smriti Mandhana', 'India', 'Smriti Mandhana'),
    ('Harmanpreet Kaur', 'India', 'Harmanpreet Kaur'),
    ('Mithali Raj', 'India', 'Mithali Raj'),
    ('Jhulan Goswami', 'India', 'Jhulan Goswami'),
    ('Ellyse Perry', 'Australia', 'Ellyse Perry'),
    ('Meg Lanning', 'Australia', 'Meg Lanning'),
    ('Alyssa Healy', 'Australia', 'Alyssa Healy'),
    ('Steven Smith', 'Australia', 'Steve Smith (cricketer)'),
    ('Ricky Ponting', 'Australia', 'Ricky Ponting'),
    ('Shane Warne', 'Australia', 'Shane Warne'),
    ('Joe Root', 'England', 'Joe Root'),
    ('James Anderson', 'England', 'James Anderson (cricketer)'),
    ('Nat Sciver-Brunt', 'England', 'Nat Sciver-Brunt'),
    ('Heather Knight', 'England', 'Heather Knight'),
    ('Kane Williamson', 'New Zealand', 'Kane Williamson'),
    ('Sophie Devine', 'New Zealand', 'Sophie Devine'),
    ('Suzie Bates', 'New Zealand', 'Suzie Bates'),
    ('Melie Kerr', 'New Zealand', 'Amelia Kerr'),
    ('Kumar Sangakkara', 'Sri Lanka', 'Kumar Sangakkara'),
    ('Mahela Jayawardene', 'Sri Lanka', 'Mahela Jayawardene'),
    ('Chamari Athapaththu', 'Sri Lanka', 'Chamari Athapaththu'),
    ('Jacques Kallis', 'South Africa', 'Jacques Kallis'),
    ('Dale Steyn', 'South Africa', 'Dale Steyn'),
    ('Laura Wolvaardt', 'South Africa', 'Laura Wolvaardt'),
    ('Marizanne Kapp', 'South Africa', 'Marizanne Kapp'),
    ('Babar Azam', 'Pakistan', 'Babar Azam'),
    ('Wasim Akram', 'Pakistan', 'Wasim Akram'),
    ('Bismah Maroof', 'Pakistan', 'Bismah Maroof'),
    ('Nida Dar', 'Pakistan', 'Nida Dar'),
    ('Shakib Al Hasan', 'Bangladesh', 'Shakib Al Hasan'),
    ('Tamim Iqbal', 'Bangladesh', 'Tamim Iqbal'),
    ('Jahanara Alam', 'Bangladesh', 'Jahanara Alam'),
    ('Brian Lara', 'West Indies', 'Brian Lara'),
    ('Chris Gayle', 'West Indies', 'Chris Gayle'),
    ('Stafanie Taylor', 'West Indies', 'Stafanie Taylor'),
    ('Hayley Matthews', 'West Indies', 'Hayley Matthews'),
    ('Rashid Khan', 'Afghanistan', 'Rashid Khan'),
    ('Mujeeb Ur Rahman', 'Afghanistan', 'Mujeeb Ur Rahman'),
    ('Sikandar Raza', 'Zimbabwe', 'Sikandar Raza'),
    ('Andy Flower', 'Zimbabwe', 'Andy Flower'),
    ('Paul Stirling', 'Ireland', 'Paul Stirling'),
    ("Kevin O'Brien", 'Ireland', "Kevin O'Brien (cricketer)"),
    ('Gaby Lewis', 'Ireland', 'Gaby Lewis'),
    ('Rahul Dravid', 'India', 'Rahul Dravid'),
    ('Ravichandran Ashwin', 'India', 'Ravichandran Ashwin'),
    ('MS Dhoni', 'India', 'MS Dhoni'),
    ('Ravindra Jadeja', 'India', 'Ravindra Jadeja'),
    ('Rishabh Pant', 'India', 'Rishabh Pant'),
    ('Pat Cummins', 'Australia', 'Pat Cummins'),
    ('Ben Stokes', 'England', 'Ben Stokes'),
    ('Sophie Ecclestone', 'England', 'Sophie Ecclestone'),
    ('Beth Mooney', 'Australia', 'Beth Mooney'),
    ('AB de Villiers', 'South Africa', 'AB de Villiers'),
    ('Muttiah Muralitharan', 'Sri Lanka', 'Muttiah Muralitharan'),
]


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain(value):
    parser = PlainText()
    parser.feed(value)
    return re.sub(r'\s+', ' ', unescape(' '.join(parser.parts))).strip()


def get(url, refresh=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / (hashlib.sha256(url.encode()).hexdigest() + '.bin')
    if path.exists() and not refresh:
        return path.read_bytes()
    time.sleep(.35)
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={'User-Agent': USER_AGENT}), timeout=45) as response:
                value = response.read(20_000_001)
            if len(value) > 20_000_000:
                raise ValueError('Image exceeds 20 MB download limit')
            path.write_bytes(value)
            return value
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt * 2)


def query(host, params, refresh=False):
    data = json.loads(get('https://' + host + '/w/api.php?' + urlencode(
        {'action': 'query', 'format': 'json', **params}), refresh))
    if data.get('error'):
        raise ValueError(data['error'].get('info', 'Wikimedia API error'))
    return list(data.get('query', {}).get('pages', {}).values())


def licensed(metadata):
    name = plain(metadata.get('LicenseShortName', {}).get('value', ''))
    url = metadata.get('LicenseUrl', {}).get('value', '')
    if name == 'Public domain':
        return name, url or 'https://creativecommons.org/publicdomain/mark/1.0/'
    if name in ('CC0', 'CC0 1.0'):
        return 'CC0 1.0', 'https://creativecommons.org/publicdomain/zero/1.0/'
    if re.fullmatch(r'CC BY(?:-SA)? [1-4]\.0', name):
        if url.startswith('//'):
            url = 'https:' + url
        if urlparse(url).hostname == 'creativecommons.org' and '/licenses/' in url:
            return name, url
    raise ValueError('License needs manual review: ' + (name or 'missing'))


def collect(player, article, refresh=False):
    page = query('en.wikipedia.org', {'titles': article, 'redirects': 1,
                 'prop': 'pageimages', 'piprop': 'name|original'}, refresh)[0]
    original = page.get('original', {}).get('source', '')
    if '/wikipedia/commons/' not in original or not page.get('pageimage'):
        raise ValueError('No Commons lead photograph')
    file_title = 'File:' + page['pageimage'].replace('_', ' ')
    file = query('commons.wikimedia.org', {'titles': file_title, 'prop': 'imageinfo',
                 'iiprop': 'url|extmetadata|size|sha1', 'iiurlwidth': 480}, refresh)[0]
    info = file.get('imageinfo', [{}])[0]
    metadata = info.get('extmetadata', {})
    name, license_url = licensed(metadata)
    author = plain(metadata.get('Artist', {}).get('value', ''))
    if not author:
        raise ValueError('No verified artist credit')
    source_url = info['descriptionurl']
    if urlparse(source_url).hostname != 'commons.wikimedia.org':
        raise ValueError('File is not hosted on Commons')
    image_url = info.get('thumburl', info['url'])
    image = ImageOps.exif_transpose(Image.open(BytesIO(get(image_url, refresh)))).convert('RGB')
    image.thumbnail((480, 640), Image.Resampling.LANCZOS)
    asset = ROOT / 'web' / 'portraits' / (player['id'] + '.webp')
    asset.parent.mkdir(parents=True, exist_ok=True)
    image.save(asset, 'WEBP', quality=84, method=6)
    return {'name': player['name'], 'country': player['teams'][0], 'gender': player['gender'],
            'path': '/assets/portraits/' + asset.name, 'width': image.width, 'height': image.height,
            'author': author, 'license': name, 'license_url': license_url,
            'source_url': source_url, 'source_file': file['title'], 'source_sha1': info['sha1'],
            'source_original_url': info['url'],
            'identity_article': 'https://en.wikipedia.org/wiki/' + quote(page['title'].replace(' ', '_')),
            'description': plain(metadata.get('ImageDescription', {}).get('value', '')),
            'changes': 'Resized to WebP; displayed as a portrait.',
            'verified_at': date.today().isoformat()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    players = json.loads((ROOT / '_site/data/player-index.json').read_text(encoding='utf-8'))
    path = ROOT / 'data/portraits.json'
    data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'players': {}}
    report = []
    for name, country, article in TARGETS[:args.limit]:
        matches = [p for p in players if p['name'] == name and country in p['teams']]
        if len(matches) != 1:
            report.append({'name': name, 'status': 'skipped', 'reason': 'Identity needs manual review'})
            print('SKIP', name, 'identity needs review', flush=True)
            continue
        player = matches[0]
        if player['id'] in data['players'] and not args.refresh:
            continue
        try:
            data['players'][player['id']] = collect(player, article, args.refresh)
            print('OK', name, data['players'][player['id']]['license'], flush=True)
        except Exception as exc:
            report.append({'name': name, 'status': 'skipped', 'reason': str(exc)})
            print('SKIP', name, str(exc), flush=True)
        data['meta'] = {'source': 'Wikimedia Commons; individually credited photographs',
                        'updated_at': date.today().isoformat(), 'count': len(data['players']),
                        'coverage': 'Curated portraits; initials are used for players without a verified image.',
                        'reuse_guidance': 'https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia'}
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (CACHE / 'collection-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Verified portraits:', len(data['players']), 'Skipped this run:', len(report), flush=True)


if __name__ == '__main__':
    main()
