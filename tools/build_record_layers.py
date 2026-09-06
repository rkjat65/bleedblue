"""Join independently sourced career records and historical results to the archive.

Never add an archive subtotal to a career total. Null means not supplied.
The original delivery-derived dataset stays unchanged and separately selectable.
"""
import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from import_careers import ROOT, CACHE, CLASSES, BASE

TEAMS = {'IND': 'India', 'AUS': 'Australia', 'ENG': 'England', 'PAK': 'Pakistan', 'NZ': 'New Zealand', 'SA': 'South Africa', 'SL': 'Sri Lanka', 'WI': 'West Indies', 'BAN': 'Bangladesh', 'ZIM': 'Zimbabwe', 'AFG': 'Afghanistan', 'IRE': 'Ireland', 'ICC': 'ICC World XI', 'Asia': 'Asia XI', 'Afr': 'Africa XI', 'SCOT': 'Scotland', 'NED': 'Netherlands', 'UAE': 'United Arab Emirates', 'USA': 'United States of America', 'NEP': 'Nepal', 'OMA': 'Oman', 'NAM': 'Namibia', 'CAN': 'Canada', 'HK': 'Hong Kong', 'PNG': 'Papua New Guinea', 'KENYA': 'Kenya', 'BER': 'Bermuda', 'EAf': 'East Africa'}
MATCH_TEAMS = {'U.A.E.': 'United Arab Emirates', 'U.S.A.': 'United States of America', 'Hong Kong, China': 'Hong Kong', 'P.N.G.': 'Papua New Guinea', 'Czech Rep.': 'Czech Republic', 'Cayman': 'Cayman Islands', 'Falkland Isl': 'Falkland Islands', 'World XI': 'ICC World XI', 'Int XI': 'International XI', 'Y. Eng': 'Young England', 'T & T': 'Trinidad and Tobago', 'SK': 'South Korea', 'CRC': 'Costa Rica', 'DNK': 'Denmark', 'SCO': 'Scotland', 'NL': 'Netherlands', 'IDN': 'Indonesia', 'ROU': 'Romania', 'SGP': 'Singapore', 'HKG': 'Hong Kong', 'PNG': 'Papua New Guinea', 'THA': 'Thailand', 'CAM': 'Cambodia', 'CMR': 'Cameroon', 'IOM': 'Isle of Man', 'NGA': 'Nigeria', 'MYA': 'Myanmar', 'TAN': 'Tanzania', 'VAN': 'Vanuatu'}


def number(value):
    if value is None or str(value).strip() in ('', '-', '—'):
        return None
    text = str(value).replace(',', '').rstrip('*')
    try:
        value = float(text)
        return int(value) if value.is_integer() else value
    except ValueError:
        return None


def load_rows(prefix):
    result = CACHE / f'{prefix}-result.json'
    if result.exists():
        data = json.loads(result.read_text(encoding='utf-8'))
        for row in data['rows']:
            teams=re.findall(r'\(([^)]+)\)',row.get('values',{}).get('Player',''))
            if teams:row['team_codes']=teams[-1].split('/')
        return data['rows'], data.get('complete', False)
    rows = []
    for path in sorted(CACHE.glob(prefix + '-*.json'), key=lambda p: int(p.stem.rsplit('-', 1)[-1])):
        rows.extend(json.loads(path.read_text(encoding='utf-8'))['rows'])
    return rows, False


def normalize_format(layers):
    b = layers.get('batting', {}).get('values', {})
    w = layers.get('bowling', {}).get('values', {})
    f = layers.get('fielding', {}).get('values', {})
    appearances = [number(v.get('Mat')) for v in (b, w, f) if number(v.get('Mat')) is not None]
    inns, notouts = number(b.get('Inns')), number(b.get('NO'))
    legal = number(w.get('Balls'))
    if legal is None and re.fullmatch(r'\d+(?:\.[0-5])?', w.get('Overs', '')):
        parts = w['Overs'].split('.')
        legal = int(parts[0]) * 6 + (int(parts[1]) if len(parts) > 1 else 0)
    return {
        'matches': max(appearances) if appearances else None,
        'innings': inns, 'runs': number(b.get('Runs')), 'balls': number(b.get('BF')),
        'outs': inns - notouts if inns is not None and notouts is not None else None,
        'notouts': notouts, 'highest': number(b.get('HS')), 'highest_display': b.get('HS'),
        'avg': number(b.get('Ave')), 'sr': number(b.get('SR')),
        'hundreds': number(b.get('100')), 'fifties': number(b.get('50')), 'ducks': number(b.get('0')),
        'fours': number(b.get('4s')), 'sixes': number(b.get('6s')),
        'wickets': number(w.get('Wkts')), 'conceded': number(w.get('Runs')), 'legal': legal,
        'bowling_innings': number(w.get('Inns')), 'maidens': number(w.get('Mdns')),
        'bowlAvg': number(w.get('Ave')), 'econ': number(w.get('Econ')), 'bowlSr': number(w.get('SR')),
        'best_bowling': w.get('BBI'), 'five_w': number(w.get('5')), 'ten_w': number(w.get('10')),
        'best_match': w.get('BBM'), 'four_w': number(w.get('4')),
        'catches': number(f.get('Ct')), 'stumpings': number(f.get('St')),
        'fielding_innings': number(f.get('Inns')), 'dismissals': number(f.get('Dis')),
        'keeper_catches': number(f.get('Ct Wk')), 'fielder_catches': number(f.get('Ct Fi')),
        'dismissals_per_innings': number(f.get('D/I')), 'most_dismissals': f.get('MD'),
        'span': b.get('Span') or w.get('Span') or f.get('Span'),
        'disciplines': sorted(layers),
        'match_count_conflict': len(set(appearances)) > 1,
    }


def source_dates(pattern):
    dates = []
    for path in CACHE.glob(pattern):
        if not path.stem.rsplit('-', 1)[-1].isdigit():
            continue
        page = json.loads(path.read_text(encoding='utf-8'))
        dates.append(page.get('checked_at') or datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec='seconds'))
    return {'source_checked_from': min(dates) if dates else None, 'checked_at': max(dates) if dates else None}


def write(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, separators=(',', ':'), ensure_ascii=False), encoding='utf-8')
    temp.replace(path)


def main():
    archive = json.loads((ROOT / 'data/international.json').read_text(encoding='utf-8'))
    archived = {p['id']: p for p in archive['players']}
    write(ROOT / 'data/player_archive.json', {'meta': archive['meta'], 'players': archive['players'], 'matches': []})
    registry = list(csv.DictReader((CACHE / 'people.csv').read_text(encoding='utf-8').splitlines()))
    espn_to_id = {}
    for row in registry:
        for key in ('key_cricinfo', 'key_cricinfo_2', 'key_cricinfo_3'):
            if row.get(key):
                espn_to_id[row[key]] = row['identifier']
    source_ids={r['espn_id'] for cls in CLASSES for r in load_rows(f'{cls}-batting')[0]}
    # A register alias is not sufficient to merge two separately listed careers.
    # Keep the primary identity URL and split independently present source IDs.
    for row in registry:
        ids=[row[k] for k in ('key_cricinfo','key_cricinfo_2','key_cricinfo_3') if row.get(k) in source_ids]
        if len(ids)>1:
            for eid in ids[1:]:espn_to_id[eid]='espn-'+eid
    write(ROOT / 'data/identity_registry.json', {'espn_to_id': espn_to_id, 'source': 'Cricsheet register'})
    # Resolve source country abbreviations only through exact player-ID links
    # with one country on each side; ambiguous mappings remain unexpanded.
    country_candidates = {}
    for cls in CLASSES:
        rows, _ = load_rows(f'{cls}-batting')
        for row in rows:
            prior = archived.get(espn_to_id.get(row['espn_id']))
            if prior and len(prior['teams']) == 1 and len(row['team_codes']) == 1:
                country_candidates.setdefault(row['team_codes'][0], set()).add(prior['teams'][0])
    team_names = {code: next(iter(names)) for code, names in country_candidates.items() if len(names) == 1}
    team_names.update(TEAMS)
    team_names.update({'BLZ-W': 'Belize', 'GAM-W': 'Gambia', 'PER-W': 'Peru'})
    def match_team(name):
        base = re.sub(r'(?: Women| Wmn|-W)$', '', name)
        return MATCH_TEAMS.get(base, team_names.get(base, team_names.get(base + '-W', base)))
    records, scopes = {}, []
    for cls, (fmt, gender) in CLASSES.items():
        for discipline in ('batting', 'bowling', 'fielding'):
            rows, complete = load_rows(f'{cls}-{discipline}')
            scopes.append({'format': fmt, 'gender': gender, 'discipline': discipline, 'rows': len(rows), 'complete': complete, 'source': f'{BASE}/ci/engine/stats/index.html?class={cls};template=results;type={discipline}'})
            for row in rows:
                eid = row['espn_id']
                pid = espn_to_id.get(eid, 'espn-' + eid)
                prior = archived.get(pid)
                if prior and prior['gender']!=gender:prior=None
                p = records.setdefault(pid, {'id': pid, 'espn_id': eid, 'name': prior['name'] if prior else row['name'], 'source_name': row['name'], 'teams': prior['teams'][:] if prior else [], 'gender': gender, 'layers': {}, 'formats': {}})
                for team in row['team_codes']:
                    team = team_names.get(team, team_names.get(team.removesuffix('-W'), team))
                    if team not in p['teams']:
                        p['teams'].append(team)
                p['layers'].setdefault(fmt, {})[discipline] = row
    for p in records.values():
        for fmt, layers in p.pop('layers').items():
            p['formats'][fmt] = normalize_format(layers)
            cls = next(cls for cls, pair in CLASSES.items() if pair == (fmt, p['gender']))
            p['formats'][fmt]['source'] = f'{BASE}/ci/engine/player/{p["espn_id"]}.html?class={cls};template=results;type=batting'
            p['formats'][fmt]['sources'] = {discipline: f'{BASE}/ci/engine/player/{p["espn_id"]}.html?class={cls};template=results;type={discipline}' for discipline in layers}
        spans = [s['span'] for s in p['formats'].values() if s.get('span')]
        p['first'] = min((s.split('-')[0] for s in spans), default='')
        p['last'] = max((s.split('-')[-1] for s in spans), default='')
    meta = {'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'source': 'ESPNcricinfo Statsguru', 'players': len(records), 'combined_players': len(set(records) | set(archived)), 'archive_players_with_career': sum(pid in archived for pid in records), 'historical_players_added': sum(pid not in archived for pid in records), 'scopes': scopes, 'complete_import': all(s['complete'] for s in scopes), 'note': 'Career snapshots are independent of ball-by-ball archive totals. Missing source fields are null, never zero-filled. Sources may update between individual table requests.'}
    meta['built_at'] = meta['checked_at']
    unmatched = [{**p, 'career_status': 'not matched to imported career tables', 'espn_id': next((eid for eid, pid in espn_to_id.items() if pid == p['id']), None)} for pid, p in archived.items() if pid not in records]
    meta['archive_players_without_career'] = len(unmatched)
    write(ROOT / 'data/unmatched_players.json', {'note': 'These archive identities have no matching career row in the imported source tables. Archive appearances may include differently classified matches. No career total is inferred.', 'players': unmatched})
    meta.update(source_dates('*-batting-*.json'))
    for discipline in ('bowling', 'fielding'):
        dates = source_dates(f'*-{discipline}-*.json')
        if dates['checked_at']:
            meta['checked_at'] = max(meta['checked_at'], dates['checked_at'])
            meta['source_checked_from'] = min(meta['source_checked_from'], dates['source_checked_from'])
    write(ROOT / 'data/careers.json', {'meta': meta, 'players': list(records.values())})
    write(ROOT / 'data/career_manifest.json', meta)
    featured = {'V Kohli', 'RG Sharma', 'JJ Bumrah', 'MS Dhoni'}
    ranked = sorted(records.values(), key=lambda p: sum(f['runs'] or 0 for f in p['formats'].values()), reverse=True)
    home_players = {p['id']: p for p in ranked[:5] + [p for p in records.values() if p['name'] in featured]}
    write(ROOT / 'data/home_careers.json', {'meta': meta, 'players': list(home_players.values())})

    existing_ids = {m['id'] for m in archive['matches']}
    catalog, match_scopes, official = {}, [], {}
    for cls, (fmt, gender) in CLASSES.items():
        rows, complete = load_rows(f'matches-{cls}')
        match_scopes.append({'format': fmt, 'gender': gender, 'rows': len(rows), 'complete': complete})
        for row in rows:
            mid, v = row['id'], row['values']
            official[mid] = cls
            if mid in existing_ids:
                continue
            team = match_team(v['Team'])
            opp = re.sub(r'^v\s+', '', v['Opposition'])
            opp = match_team(opp)
            outcome = {'result': {'draw': 'draw', 'tied': 'tie', 'n/r': 'no result', 'aban': 'no result'}.get(v['Result'], v['Result'])}
            if v['Result'] in ('won', 'lost'):
                outcome = {'winner': team if v['Result'] == 'won' else opp}
            margin = v.get('Margin', '')
            date = datetime.strptime(v['Start Date'], '%d %b %Y').date().isoformat()
            catalog[mid] = {'id': mid, 'date': date, 'format': fmt, 'gender': gender, 'teams': sorted([team, opp]), 'venue': v.get('Ground', ''), 'city': '', 'event': '', 'outcome': outcome, 'margin_text': margin if margin != '-' else '', 'totals': [], 'player_ids': [], 'coverage': 'result-only', 'source': row['source'], 'source_list': f'{BASE}/ci/engine/stats/index.html?class={cls};template=results;type=team;view=results'}
    match_meta = {'checked_at': meta['checked_at'], 'source': 'ESPNcricinfo Statsguru', 'added_matches': len(catalog), 'first': min((m['date'] for m in catalog.values()), default=None), 'last': max((m['date'] for m in catalog.values()), default=None), 'teams': sorted({t for m in catalog.values() for t in m['teams']}), 'gender': dict(Counter(m['gender'] for m in catalog.values())), 'scopes': match_scopes, 'complete_import': all(s['complete'] for s in match_scopes), 'note': 'Historical results without local scorecards. Missing innings and deliveries are not invented.'}
    match_meta['built_at'] = meta['built_at']
    match_meta.update(source_dates('matches-*.json'))
    match_meta['format_summary'] = {fmt: {'matches': sum(m['format'] == fmt for m in archive['matches']) + sum(m['format'] == fmt for m in catalog.values()), 'women': sum(m['format'] == fmt and m['gender'] == 'Women' for m in archive['matches']) + sum(m['format'] == fmt and m['gender'] == 'Women' for m in catalog.values()), 'teams': len({t for m in archive['matches'] + list(catalog.values()) if m['format'] == fmt for t in m['teams']})} for fmt in ('Test', 'ODI', 'T20I')}
    write(ROOT / 'data/historical_matches.json', {'meta': match_meta, 'matches': sorted(catalog.values(), key=lambda m: m['date'], reverse=True)})
    write(ROOT / 'data/historical_manifest.json', match_meta)
    write(ROOT / 'data/official_match_registry.json', {'matches': official, 'source': 'Statsguru international class tables', 'checked_at': match_meta['checked_at']})
    print(json.dumps({k: v for k, v in meta.items() if k != 'scopes'}, indent=2))
    print('Historical matches added:', len(catalog))


if __name__ == '__main__':
    main()
