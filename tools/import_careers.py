"""Import sourced career tables from ESPNcricinfo Statsguru, keeping raw provenance.

Each scope follows the source's Next links. Cached parsed pages allow resuming
without repeatedly downloading pages. A failed scope is reported, never described
as complete. Run --refresh to explicitly refresh cached source pages.
"""
from __future__ import annotations
import argparse
import csv
import io
import json
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / '.data-cache' / 'careers'
BASE = 'https://stats.cricinfo.com'
CLASSES = {1: ('Test', 'Men'), 2: ('ODI', 'Men'), 3: ('T20I', 'Men'), 8: ('Test', 'Women'), 9: ('ODI', 'Women'), 10: ('T20I', 'Women')}


def fetch(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'BleedBlueRecords/1.0 (cricket.rkjat.in)', 'Accept': 'text/html,application/json'})
            with urllib.request.urlopen(req, timeout=45) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))
        except (TimeoutError, urllib.error.URLError, ConnectionError):
            if attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))
    raise RuntimeError('Source unavailable')


def parse_page(body, url):
    soup = BeautifulSoup(body, 'html.parser')
    tables = [t for t in soup.select('table.engineTable') if t.find('caption') and 'Overall figures' in t.find('caption').get_text()]
    if not tables:
        raise ValueError('Expected career table is absent; refusing to import an error page')
    table = tables[0]
    headers = [h.get_text(' ', strip=True) for h in table.select('thead th')]
    rows = []
    for row in table.select('tr.data1'):
        cells = row.find_all('td', recursive=False)
        link = row.find('a', href=re.compile(r'/player/\d+\.html'))
        if not link:
            continue
        espn_id = re.search(r'/player/(\d+)\.html', link['href']).group(1)
        values = {h: c.get_text(' ', strip=True) for h, c in zip(headers, cells) if h}
        teams = re.findall(r'\(([^)]+)\)', cells[0].get_text(' ', strip=True))
        rows.append({'espn_id': espn_id, 'name': link.get_text(' ', strip=True), 'team_codes': teams[-1].split('/') if teams else [], 'values': values})
    pagination = re.search(r'Page\s+(\d+)\s+of\s+(\d+)\s+Showing\s+\d+\s*-\s*\d+\s+of\s+(\d+)', soup.get_text(' ', strip=True))
    next_link = next((a for a in soup.find_all('a', href=True) if a.get_text(strip=True) == 'Next'), None)
    return {'rows': rows, 'url': url, 'next': urljoin(BASE, next_link['href']) if next_link else None, 'expected': int(pagination[3]) if pagination else None, 'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds')}


def scope(class_id, discipline, refresh=False):
    key = f'{class_id}-{discipline}'
    url = f'{BASE}/ci/engine/stats/index.html?class={class_id};page_size=200;template=results;type={discipline}'
    rows, pages, seen = [], 0, set()
    expected = None
    try:
        while url:
            if url in seen:
                raise ValueError('Pagination loop')
            seen.add(url)
            page_file = CACHE / f'{key}-{pages + 1}.json'
            if page_file.exists() and not refresh:
                page = json.loads(page_file.read_text(encoding='utf-8'))
            else:
                page = parse_page(fetch(url), url)
                page_file.write_text(json.dumps(page), encoding='utf-8')
                time.sleep(.25)
            expected = page['expected'] or expected
            rows.extend(page['rows']); pages += 1
            url = page['next']
            if pages % 10 == 0:
                print(f'{key}: {len(rows)}/{expected} records', flush=True)
        if expected is not None and len({r['espn_id'] for r in rows}) != expected:
            raise ValueError(f'Source count mismatch: {len(rows)} / {expected}')
        status = {'complete': True, 'error': None}
    except Exception as error:
        status = {'complete': False, 'error': str(error)}
    out = {'class_id': class_id, 'discipline': discipline, 'rows': rows, 'pages': pages, 'expected': expected, **status}
    (CACHE / f'{key}-result.json').write_text(json.dumps(out), encoding='utf-8')
    print(f'{key}: {len(rows)} rows; complete={status["complete"]} {status["error"] or ""}', flush=True)
    return out


def main(refresh=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    registry = CACHE / 'people.csv'
    if refresh or not registry.exists():
        registry.write_bytes(fetch('https://cricsheet.org/register/people.csv'))
    scopes = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(scope, cls, discipline, refresh) for cls in CLASSES for discipline in ('batting', 'bowling', 'fielding')]
        for future in as_completed(futures):
            scopes.append(future.result())
    # A separately resumed scope may have completed while other imports ran.
    scopes = [json.loads((CACHE / f'{cls}-{discipline}-result.json').read_text(encoding='utf-8')) for cls in CLASSES for discipline in ('batting', 'bowling', 'fielding')]
    report = {'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'scopes': [{k: v for k, v in scope.items() if k != 'rows'} for scope in scopes]}
    (ROOT / 'data/career_import_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    main(parser.parse_args().refresh)
