"""Download public Cricsheet internationals and build the browsable archive.

Uses all available men's and women's Tests, ODIs and T20Is. Raw ZIPs are
cached locally; use --refresh to download again. No API key is required.
"""
from __future__ import annotations
import argparse
import json
import urllib.request
import zipfile
from pathlib import Path
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / '.data-cache'
DEST = ROOT / 'data'
SOURCES = [f'{fmt}_{gender}_json.zip' for gender in ('male', 'female') for fmt in ('tests', 'odis', 't20s')]
NON_BOWLER = {'run out', 'retired hurt', 'obstructing the field', 'retired out'}
NOT_OUT = {'retired hurt', 'obstructing the field'}


def download(name, refresh=False):
    path = CACHE / name
    if refresh or not path.exists():
        print('Downloading', name, flush=True)
        request = urllib.request.Request('https://cricsheet.org/downloads/' + name, headers={'User-Agent': 'BleedBlueArchive/1.0'})
        temp = path.with_suffix('.tmp')
        with urllib.request.urlopen(request, timeout=120) as response, temp.open('wb') as target:
            while block := response.read(1024 * 1024):
                target.write(block)
        with zipfile.ZipFile(temp) as archive:
            assert archive.namelist(), 'Empty ZIP'
        temp.replace(path)
    return path


def blank():
    return dict(matches=0, innings=0, runs=0, balls=0, outs=0, fours=0, sixes=0, hundreds=0, fifties=0, highest=0, wickets=0, conceded=0, legal=0, catches=0, stumpings=0)


def write_json(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, separators=(',', ':'), ensure_ascii=False), encoding='utf-8')
    temp.replace(path)


def main(refresh=False):
    CACHE.mkdir(exist_ok=True)
    DEST.mkdir(exist_ok=True)
    (DEST / 'scorecards').mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        archives = list(pool.map(lambda name: download(name, refresh), SOURCES))
    players, matches, details = {}, [], {}
    for path in archives:
        print('Processing', path.name, flush=True)
        with zipfile.ZipFile(path) as archive:
            for filename in archive.namelist():
                mid = Path(filename).stem
                if not mid.isdigit() or not filename.endswith('.json'):
                    continue
                raw = json.loads(archive.read(filename))
                info = raw['info']
                fmt = {'T20': 'T20I'}.get(info['match_type'], info['match_type'])
                gender = 'Women' if info.get('gender') == 'female' else 'Men'
                teams = info['teams']
                registry = info.get('registry', {}).get('people', {})
                key_for = lambda name: registry.get(name, gender + ':' + name)
                match_players = {}
                for team, names in info.get('players', {}).items():
                    match_players[team] = []
                    for name in names:
                        key = key_for(name)
                        match_players[team].append({'id': key, 'name': name})
                        p = players.setdefault(key, {'id': key, 'name': name, 'teams': [], 'gender': gender, 'formats': {}, 'first': info['dates'][0], 'last': info['dates'][0]})
                        if team not in p['teams']:
                            p['teams'].append(team)
                        p['first'] = min(p['first'], info['dates'][0])
                        p['last'] = max(p['last'], info['dates'][0])
                        p['formats'].setdefault(fmt, blank())['matches'] += 1
                cards = []
                for inning in raw.get('innings', []):
                    batting, bowling = {}, {}
                    runs, wickets, legal, extra = 0, 0, 0, 0
                    fall, timeline = [], []
                    for over in inning.get('overs', []):
                        over_runs, over_wkts = 0, 0
                        for delivery in over['deliveries']:
                            batter, bowler = delivery['batter'], delivery['bowler']
                            b = batting.setdefault(batter, {'name': batter, 'id': key_for(batter), 'runs': 0, 'balls': 0, 'fours': 0, 'sixes': 0, 'out': False, 'dismissal': 'not out'})
                            batting.setdefault(delivery['non_striker'], {'name': delivery['non_striker'], 'id': key_for(delivery['non_striker']), 'runs': 0, 'balls': 0, 'fours': 0, 'sixes': 0, 'out': False, 'dismissal': 'not out'})
                            w = bowling.setdefault(bowler, {'name': bowler, 'id': key_for(bowler), 'balls': 0, 'runs': 0, 'wickets': 0})
                            r, e = delivery['runs'], delivery.get('extras', {})
                            is_legal = not (e.get('wides') or e.get('noballs'))
                            runs += r['total']; over_runs += r['total']; legal += is_legal
                            extra += r['extras']
                            b['runs'] += r['batter']; b['balls'] += not e.get('wides', 0)
                            b['fours'] += r['batter'] == 4 and not r.get('non_boundary', False)
                            b['sixes'] += r['batter'] == 6 and not r.get('non_boundary', False)
                            w['balls'] += is_legal
                            w['runs'] += r['total'] - e.get('byes', 0) - e.get('legbyes', 0) - e.get('penalty', 0)
                            for wicket in delivery.get('wickets', []):
                                kind, name = wicket['kind'], wicket['player_out']
                                out = kind not in {'retired hurt'}
                                if name in batting:
                                    batting[name]['out'] = out
                                    batting[name]['dismissal'] = kind + (' b ' + bowler if kind not in NON_BOWLER else '')
                                wickets += out; over_wkts += out
                                w['wickets'] += kind not in NON_BOWLER
                                if out:
                                    fall.append({'player': name, 'runs': runs, 'wicket': wickets, 'balls': legal})
                                if not inning.get('super_over'):
                                    if kind == 'caught and bowled' and key_for(bowler) in players:
                                        players[key_for(bowler)]['formats'][fmt]['catches'] += 1
                                    for fielder in wicket.get('fielders', []):
                                        fp = players.get(key_for(fielder.get('name', '')))
                                        if fp and fmt in fp['formats']:
                                            fp['formats'][fmt]['catches'] += kind == 'caught'
                                            fp['formats'][fmt]['stumpings'] += kind == 'stumped'
                        timeline.append({'over': over['over'] + 1, 'runs': over_runs, 'wickets': over_wkts, 'total': runs})
                    penalties = inning.get('penalty_runs', {})
                    runs += penalties.get('pre', 0) + penalties.get('post', 0)
                    extra += penalties.get('pre', 0) + penalties.get('post', 0)
                    if not inning.get('super_over'):
                        for row in batting.values():
                            p = players.get(row['id'])
                            if not p: continue
                            stat = p['formats'][fmt]
                            stat['innings'] += 1
                            for key in ('runs', 'balls', 'fours', 'sixes'):
                                stat[key] += row[key]
                            stat['outs'] += row['out']
                            stat['highest'] = max(stat['highest'], row['runs'])
                            stat['hundreds'] += row['runs'] >= 100
                            stat['fifties'] += 50 <= row['runs'] < 100
                        for row in bowling.values():
                            p = players.get(row['id'])
                            if not p: continue
                            stat = p['formats'][fmt]
                            stat['wickets'] += row['wickets']; stat['conceded'] += row['runs']; stat['legal'] += row['balls']
                    cards.append({'team': inning['team'], 'runs': runs, 'wickets': wickets, 'balls': legal, 'extras': extra, 'super_over': inning.get('super_over', False), 'declared': inning.get('declared', False), 'batting': list(batting.values()), 'bowling': list(bowling.values()), 'fall': fall, 'overs': timeline})
                match = {'id': mid, 'date': info['dates'][0], 'format': fmt, 'gender': gender, 'teams': teams, 'venue': info['venue'], 'city': info.get('city', ''), 'event': info.get('event', {}).get('name', ''), 'outcome': info.get('outcome', {}), 'totals': [{k: c[k] for k in ('team', 'runs', 'wickets', 'balls', 'super_over')} for c in cards], 'shard': mid[:3], 'player_ids': [p['id'] for roster in match_players.values() for p in roster]}
                matches.append(match)
                details[mid] = {'match': match, 'innings': cards, 'players': match_players, 'toss': info.get('toss', {}), 'awards': info.get('player_of_match', []), 'source': 'https://cricsheet.org/downloads/' + path.name}
    assert len(matches) == len({m['id'] for m in matches}), 'Duplicate source match IDs'
    matches.sort(key=lambda m: (m['date'], m['id']), reverse=True)
    shards = defaultdict(dict)
    for mid, detail in details.items():
        shards[mid[:3]][mid] = detail
    for shard, data in shards.items():
        write_json(DEST / 'scorecards' / (shard + '.json'), data)
    meta = {'generated': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'first': min(m['date'] for m in matches), 'last': max(m['date'] for m in matches), 'matches': len(matches), 'players': len(players), 'teams': sorted(set(t for m in matches for t in m['teams'])), 'sources': ['https://cricsheet.org/downloads/' + s for s in SOURCES], 'formats': dict(Counter(m['format'] for m in matches)), 'gender': dict(Counter(m['gender'] for m in matches)), 'note': 'All available Cricsheet international files at download time. Historical coverage is incomplete; Cricsheet withholds Afghanistan matches. Not live scores or complete career records.'}
    write_json(DEST / 'international.json', {'meta': meta, 'matches': matches, 'players': list(players.values())})
    write_json(DEST / 'manifest.json', meta)
    selected_matches = {m['id']: m for fmt in ('Test', 'ODI', 'T20I') for m in [m for m in matches if m['format'] == fmt][:4]}
    featured_names = {'V Kohli', 'RG Sharma', 'JJ Bumrah', 'MS Dhoni'}
    top_players = sorted(players.values(), key=lambda p: sum(s['runs'] for s in p['formats'].values()), reverse=True)[:5]
    selected_players = {p['id']: p for p in top_players + [p for p in players.values() if p['name'] in featured_names]}
    format_summary = {fmt: {'matches': sum(m['format'] == fmt for m in matches), 'women': sum(m['format'] == fmt and m['gender'] == 'Women' for m in matches), 'teams': len({t for m in matches if m['format'] == fmt for t in m['teams']})} for fmt in ('Test', 'ODI', 'T20I')}
    write_json(DEST / 'home.json', {'meta': meta, 'matches': sorted(selected_matches.values(), key=lambda m: (m['date'], m['id']), reverse=True), 'players': list(selected_players.values()), 'format_summary': format_summary})
    print(json.dumps(meta, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    main(parser.parse_args().refresh)
