"""Import historical international results without inventing missing scorecards."""
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from import_careers import ROOT, CACHE, BASE, CLASSES, fetch


def parse(body, url):
    soup = BeautifulSoup(body, 'html.parser')
    table = next((t for t in soup.select('table.engineTable') if t.find('caption') and t.find('caption').get_text(strip=True) == 'Match results'), None)
    if table is None:
        raise ValueError('Expected match-results table missing')
    headings = [th.get_text(' ', strip=True) for th in table.select('thead th')]
    rows = []
    for tr in table.select('tr.data1'):
        cells = tr.find_all('td', recursive=False)
        values = {h: td.get_text(' ', strip=True) for h, td in zip(headings, cells) if h}
        menu = tr.find(attrs={'onmouseover': re.compile('engine-dd')})
        if not menu:
            continue
        menu_id = re.search(r"engine-dd\d+", menu['onmouseover'])[0]
        detail = soup.find(id=menu_id)
        link = detail.find('a', href=re.compile(r'/match/\d+\.html')) if detail else None
        if not link:
            raise ValueError('Missing source match identifier')
        match_id = re.search(r'/match/(\d+)\.html', link['href'])[1]
        rows.append({'id': match_id, 'values': values, 'source': urljoin(BASE, link['href'])})
    paging = re.search(r'Page\s+\d+\s+of\s+\d+\s+Showing\s+\d+\s*-\s*\d+\s+of\s+(\d+)', soup.get_text(' ', strip=True))
    next_link = next((a for a in soup.find_all('a', href=True) if a.get_text(strip=True) == 'Next'), None)
    return {'rows': rows, 'expected': int(paging[1]) if paging else None, 'next': urljoin(BASE, next_link['href']) if next_link else None, 'url': url}


def run_scope(cls):
    url = f'{BASE}/ci/engine/stats/index.html?class={cls};template=results;type=team;view=results'
    rows, page, expected, seen = [], 0, None, set()
    try:
        while url:
            if url in seen:
                raise ValueError('Pagination repeated')
            seen.add(url)
            file = CACHE / f'matches-{cls}-{page + 1}.json'
            if file.exists():
                data = json.loads(file.read_text(encoding='utf-8'))
            else:
                data = parse(fetch(url), url)
                file.write_text(json.dumps(data), encoding='utf-8')
                time.sleep(.3)
            rows.extend(data['rows']); page += 1; expected = data['expected'] or expected; url = data['next']
            if page % 15 == 0:
                print(f'Matches class {cls}: {len(rows)}/{expected} team results', flush=True)
        if expected is not None and len(rows) != expected:
            raise ValueError(f'Count mismatch {len(rows)} / {expected}')
        complete, error = True, None
    except Exception as exc:
        complete, error = False, str(exc)
    result = {'class_id': cls, 'rows': rows, 'expected': expected, 'complete': complete, 'error': error}
    (CACHE / f'matches-{cls}-result.json').write_text(json.dumps(result), encoding='utf-8')
    print(f'Match class {cls}: {len(rows)} rows; complete={complete}; {error or ""}', flush=True)
    return {k: v for k, v in result.items() if k != 'rows'}


if __name__ == '__main__':
    CACHE.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run_scope, CLASSES))
    report = {'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'scopes': results}
    (ROOT / 'data/match_import_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
