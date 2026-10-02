"""Gate publication on crawlability, links, statistics and page-weight budgets."""
import json
from concurrent.futures import ThreadPoolExecutor
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit, unquote
from html import unescape
from cricket_scope import publication_data, load_cards, REPRESENTATIVE

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
        assert len(re.findall(r'<h1(?:\s[^>]*)?>', text)) == 1, path
        assert f'rel="canonical" href="https://crickrida.com{path}"' in text, path
        assert '<meta name="description" content="' in text, path
        assert 'noindex' not in text, path
        schema = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text).group(1))
        assert schema['url'] == 'https://crickrida.com' + path, path
        for url in re.findall(r'(?:href|src)="([^"]+)"', text):
            if url.startswith('/') and not url.startswith('//'):
                links.add(unquote(urlsplit(unescape(url)).path))
        if path.startswith('/players/') and '/page/' not in path and path != '/players/':
            weights.append(len(text.encode()))
            assert 'Career records by format' in text
            assert 'career-stat-grid' not in text
            assert 'international.json' not in text and 'careers.json' not in text
    print('Checking internal destinations...', flush=True)
    # /ipl and /t20-world-cup are served by the crickrida app on the same domain, not this build.
    app_prefixes = ('/ipl/', '/t20-world-cup/')
    for link in links:
        if link in paths or link.startswith(app_prefixes): continue
        target = SITE / link.lstrip('/')
        if not target.is_file() and not (target / 'index.html').is_file():
            errors.append(link)
    assert not errors, f'Broken generated links: {errors[:30]}'
    sitemap_paths = set()
    for xml in SITE.glob('sitemap-*.xml'):
        tree = ET.parse(xml)
        sitemap_paths.update(e.text.replace('https://crickrida.com', '') for e in tree.findall('.//{*}loc'))
    assert sitemap_paths == paths, 'Sitemap and publication disagree'
    archive,careers,history=publication_data(ROOT)
    from build_site import assemble_people
    people=assemble_people(archive,careers)
    matches=archive['matches']+history['matches']
    cards=load_cards(ROOT,matches,people)
    assert set(routes['matches'])=={m['id'] for m in matches}
    # Scorecards must add up to the official careers, innings by innings (tools/official_innings.py closes the gaps).
    from official_innings import survey,gaps
    bat,bowl,_=survey(cards,people)
    open_gaps=gaps(cards,people,bat,bowl)
    print(f'{len(open_gaps)} player formats do not reconcile with the official career',flush=True)
    assert len(open_gaps)<=120,f'Scorecards no longer add up to official careers: {len(open_gaps)} player formats'
    homepage = (SITE/'index.html').read_text(encoding='utf-8')
    # The homepage is intentionally insight-led: users should see cricket
    # questions and useful records before archive-volume charts.
    assert 'Compare teams, players and tournaments' in homepage
    assert 'TEAM HEAD-TO-HEAD' in homepage
    assert 'WORLD CUP' in homepage
    assert 'WORLD CUP RECORDS' in homepage
    assert 'Career records by format' in homepage
    assert 'FEATURED SCORECARD' in homepage
    assert 'Worm · cumulative runs by over' in homepage or 'MATCH CHARTS' in homepage
    assert 'archive-chart-data' not in homepage, 'Legacy matches-per-year chart is still on the homepage'
    official=json.loads((ROOT/'data/official_match_registry.json').read_text(encoding='utf-8'))['matches']
    index=read(SITE/'data/match-index.json')
    since=json.loads((ROOT/'data/official_match_registry.json').read_text(encoding='utf-8'))['checked_at'][:10]
    published={m['id']:m for m in index}
    assert set(official)<=set(published), len(set(official)-set(published))   # every official international, associates included
    assert all(published[mid]['date']>=since for mid in set(published)-set(official))   # only recent Cricsheet matches are provisional
    assert all(len(m['teams'])==2 for m in index)
    assert not any(set(p['teams'])&REPRESENTATIVE for p in read(SITE/'data/player-index.json'))
    expected=Counter();appearances=Counter()
    for m in matches:
        if m['id'] in cards and not cards[m['id']]['innings']:continue   # no play is not an appearance
        for pid in m['player_ids']:appearances[pid,m['format']]+=1
    for card in cards.values():
        fmt=card['match']['format']
        for inn in card['innings']:
            if inn.get('super_over'):continue
            for b in inn['batting']:expected[b['id'],fmt,'runs']+=b['runs'] or 0
            for b in inn['bowling']:expected[b['id'],fmt,'wickets']+=b['wickets'] or 0
    print('Reconciling player analysis...', flush=True)
    def analysis(pid):
        return pid,read(SITE / routes['players'][pid].lstrip('/') / 'analytics.json')
    for pid,payload in pool.map(analysis,routes['players']):
        for fmt in ('Test','ODI','T20I'):
            rows = [r for r in payload['innings'] if r['format'] == fmt]
            assert sum(r.get('runs') or 0 for r in rows) == expected[pid,fmt,'runs'], (pid, fmt, 'runs')
            assert sum(r.get('wickets') or 0 for r in rows) == expected[pid,fmt,'wickets'], (pid, fmt, 'wickets')
            assert sum(x['format'] == fmt for x in payload['appearances']) == appearances[pid,fmt], (pid, fmt, 'appearances')
        assert all(r['match'] in routes['matches'] for r in payload['innings'])
    assert not (SITE/'stats.json').exists(), 'Legacy unscoped data was published'
    pool.shutdown()
    print('Measuring publication weight...',flush=True)
    total_bytes = sum(p.stat().st_size for p in SITE.rglob('*') if p.is_file())
    # Every official international (associates included) puts the raw publication at about 2.3 GB.
    # crickrida.com is served from R2 copies stored gzip-compressed (about a fifth of that); the
    # GitHub Pages fallback artifact limit is 10 GB.
    assert total_bytes < 3_500_000_000, 'Publication exceeds the 3.5 GB budget'
    # Format-first profiles render every format's splits and milestones in HTML so they are
    # crawlable. With associate opponents in the splits, the heaviest careers (long all-rounders
    # such as Shakib Al Hasan) reach about 300 KB raw, about 40 KB compressed.
    assert max(weights) < 340_000, 'Player HTML exceeds 340 KB budget'
    report = {'pages': len(paths), 'internal_targets': len(links), 'archive_players_reconciled': len(routes['players']),
              'site_bytes': total_bytes, 'largest_player_html_bytes': max(weights),
              'median_player_html_bytes': sorted(weights)[len(weights)//2], 'passed': True}
    (SITE / 'audit-report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
