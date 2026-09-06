"""Gate publication on crawlability, links, statistics and page-weight budgets."""
import json
from concurrent.futures import ThreadPoolExecutor
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit, unquote
from html import unescape

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / '_site'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    manifest = read(SITE / 'build-manifest.json')
    routes = read(SITE / 'data/routes.json')
    paths = set(manifest['indexable'])
    assert len(routes['players']) == manifest['players']
    assert len(routes['matches']) == manifest['matches']
    assert len(set(routes['players'].values())) == manifest['players']
    assert len(set(routes['matches'].values())) == manifest['matches']
    assert set(routes['players'].values()) | set(routes['matches'].values()) <= paths
    titles=[v['title'] for v in manifest['indexable'].values()]
    assert len(titles)==len(set(titles)), 'Duplicate indexable page titles'
    errors, links, weights = [], set(), []
    print('Auditing rendered pages...', flush=True)
    def rendered(path):
        return path,(SITE/path.lstrip('/')/'index.html').read_text(encoding='utf-8')
    pool=ThreadPoolExecutor(max_workers=12)
    for index,(path,text) in enumerate(pool.map(rendered,paths)):
        if index and index % 5000 == 0: print(f'Checked {index} pages', flush=True)
        assert text.count('<h1>') == 1, path
        assert f'rel="canonical" href="https://cricket.rkjat.in{path}"' in text, path
        assert '<meta name="description" content="' in text, path
        assert 'noindex' not in text, path
        schema = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text).group(1))
        assert schema['url'] == 'https://cricket.rkjat.in' + path, path
        for url in re.findall(r'(?:href|src)="([^"]+)"', text):
            if url.startswith('/') and not url.startswith('//'):
                links.add(unquote(urlsplit(unescape(url)).path))
        if path.startswith('/players/') and '/page/' not in path and path != '/players/':
            weights.append(len(text.encode()))
            assert 'Career records by format' in text
            assert 'international.json' not in text and 'careers.json' not in text
    print('Checking internal destinations...', flush=True)
    for link in links:
        if link in paths: continue
        target = SITE / link.lstrip('/')
        if not target.is_file() and not (target / 'index.html').is_file():
            errors.append(link)
    assert not errors, f'Broken generated links: {errors[:30]}'
    sitemap_paths = set()
    for xml in SITE.glob('sitemap-*.xml'):
        tree = ET.parse(xml)
        sitemap_paths.update(e.text.replace('https://cricket.rkjat.in', '') for e in tree.findall('.//{*}loc'))
    assert sitemap_paths == paths, 'Sitemap and publication disagree'
    archive = read(ROOT / 'data/international.json')
    print('Reconciling player analysis...', flush=True)
    def analysis(p):
        return p,read(SITE / routes['players'][p['id']].lstrip('/') / 'analytics.json')
    for p,payload in pool.map(analysis,archive['players']):
        for fmt, stats in p['formats'].items():
            rows = [r for r in payload['innings'] if r['format'] == fmt]
            assert sum(r.get('runs') or 0 for r in rows) == stats['runs'], (p['name'], fmt, 'runs')
            assert sum(r.get('wickets') or 0 for r in rows) == stats['wickets'], (p['name'], fmt, 'wickets')
            assert sum(x['format'] == fmt for x in payload['appearances']) == stats['matches'], (p['name'], fmt, 'appearances')
    pool.shutdown()
    print('Measuring publication weight...',flush=True)
    total_bytes = sum(p.stat().st_size for p in SITE.rglob('*') if p.is_file())
    assert total_bytes < 950_000_000, 'Publication exceeds hosting budget'
    assert max(weights) < 100_000, 'Player HTML exceeds 100 KB budget'
    report = {'pages': len(paths), 'internal_targets': len(links), 'archive_players_reconciled': len(archive['players']),
              'site_bytes': total_bytes, 'largest_player_html_bytes': max(weights),
              'median_player_html_bytes': sorted(weights)[len(weights)//2], 'passed': True}
    (SITE / 'audit-report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
