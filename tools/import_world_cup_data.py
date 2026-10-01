"""Bring the World Cup research archives into the publication.

Cricsheet withholds Afghanistan's matches, and older World Cups have no deliveries there. Two
collections kept in the IPL-Analytics checkout fill much of that gap; they are read, never changed:

  data/odi_world_cup/scorecards   men's ODI World Cup scorecards 1975 to 2023 (ESPNcricinfo ids,
                                  over-by-over summaries where the source has them)
  T20 World Cup/t20wc_matches     men's T20 World Cup matches in Cricsheet format, including the
                                  Afghanistan matches rebuilt from ESPNcricinfo deliveries

Writes two files the build reads:

  data/world_cup_scorecards.json  scorecards, in the historical-scorecard shape, for official
                                  matches the archive has none for
  data/world_cup_overs.json       runs and wickets for every over, by match and batting team,
                                  for official matches without Cricsheet deliveries; an innings
                                  is only kept when its overs add up to the scorecard total

Usage: python tools/import_world_cup_data.py [path to IPL-Analytics]
"""
from __future__ import annotations

import glob
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from league_matches import card_from  # noqa: E402

DEFAULT_SOURCE = ROOT.parent / 'IPL-Analytics'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def archive_state():
    official = read(ROOT / 'data/official_match_registry.json')['matches']
    cricsheet = {m['id'] for m in read(ROOT / 'data/international.json')['matches']}
    historical = {}
    for f in glob.glob(str(ROOT / 'data/historical_scorecards/*.json')):
        historical.update(read(f))
    return official, cricsheet, historical


# ------------------------------------------------------------------ identities

def identity_index():
    """(team, name) -> ESPNcricinfo id from the career snapshots, plus a surname and initial key."""
    exact, loose = {}, defaultdict(set)
    for p in read(ROOT / 'data/careers.json')['players']:
        for team in p['teams']:
            exact[(team, p['name'])] = p['espn_id']
            parts = p['name'].replace('-', ' ').split()
            if len(parts) > 1:
                loose[(team, parts[-1].lower(), parts[0][0].lower())].add(p['espn_id'])
    return exact, loose


def espn_id_for(team, name, exact, loose):
    if (team, name) in exact:
        return exact[(team, name)]
    parts = name.replace('-', ' ').split()
    if len(parts) > 1:
        found = loose.get((team, parts[-1].lower(), parts[0][0].lower()), set())
        if len(found) == 1:
            return next(iter(found))
    return 'unlinked:' + re.sub(r'[^a-z]+', '-', name.lower()).strip('-')


# ------------------------------------------------------------------ conversions

def overs_text(balls, per_over=6):
    return f'{balls // per_over}.{balls % per_over}' if balls % per_over else str(balls // per_over)


def from_odi_scorecard(sc):
    """An odi_world_cup scorecard in the historical-scorecard shape, plus its over summaries."""
    innings, overs = [], {}
    for inn in sc.get('innings') or []:
        team = inn['team']
        batting = [{'espn_id': b['player']['espn_id'], 'name': b['player']['name'], 'runs': b.get('runs'), 'balls': b.get('balls'),
                    'minutes': b.get('minutes'), 'fours': b.get('fours'), 'sixes': b.get('sixes'), 'sr': b.get('strike_rate'),
                    'out': bool(b.get('is_out')), 'dismissal': (b.get('dismissal') or '').strip() or ('not out' if not b.get('is_out') else '')}
                   for b in inn.get('batting') or [] if b.get('player') and (b.get('runs') is not None or b.get('balls'))]
        bowling = [{'espn_id': b['player']['espn_id'], 'name': b['player']['name'], 'balls': b.get('balls'), 'overs': b.get('overs'),
                    'maidens': b.get('maidens'), 'runs': b.get('runs'), 'wickets': b.get('wickets'), 'econ': b.get('economy'),
                    'wides': b.get('wides'), 'noballs': b.get('noballs')}
                   for b in inn.get('bowling') or [] if b.get('player')]
        fall = [{'player': (f.get('player') or {}).get('name'), 'runs': f.get('runs'), 'wicket': f.get('wicket'), 'balls': f.get('balls'), 'overs': f.get('overs')}
                for f in inn.get('fall_of_wickets') or []]
        extras = inn.get('extras') or {}
        innings.append({'team': team, 'runs': inn.get('runs'), 'wickets': inn.get('wickets'), 'balls': inn.get('balls'), 'overs_display': inn.get('overs_display'),
                        'balls_per_over': inn.get('balls_per_over') or 6, 'extras': extras.get('extras') if isinstance(extras, dict) else extras,
                        'super_over': False, 'declared': False, 'batting': batting, 'bowling': bowling, 'overs': [], 'fall': fall})
        timeline = [(o.get('overNumber'), o.get('overRuns'), o.get('overWickets')) for o in inn.get('over_summaries') or []]
        if timeline and all(n is not None and r is not None for n, r, _ in timeline):
            overs[team] = timeline_rows(timeline)
    players = {team: [{'espn_id': p['espn_id'], 'name': p['name']} for p in xi if p.get('espn_id')] for team, xi in (sc.get('playing_xi') or {}).items()}
    card = {'innings': innings, 'players': players, 'coverage': 'scorecard', 'source': 'ESPNcricinfo scorecard via the men\'s ODI World Cup archive'}
    return card, overs


def from_cricsheet(raw, exact, loose):
    """A Cricsheet-format match without a registry (rebuilt from ESPNcricinfo deliveries)."""
    card = card_from(raw, 'x')
    ids = {}
    innings = []
    for inn in card['innings']:
        if inn.get('super_over'):
            continue
        team = inn['team']
        other = next(t for t in raw['info']['teams'] if t != team)
        for b in inn['batting']:
            ids[b['name']] = espn_id_for(team, b['name'], exact, loose)
        for b in inn['bowling']:
            ids[b['name']] = espn_id_for(other, b['name'], exact, loose)
        innings.append({'team': team, 'runs': inn['runs'], 'wickets': inn['wickets'], 'balls': inn['balls'], 'overs_display': overs_text(inn['balls']),
                        'balls_per_over': 6, 'extras': inn.get('extras'), 'super_over': False, 'declared': False,
                        'batting': [{'espn_id': ids[b['name']], 'name': b['name'], 'runs': b['runs'], 'balls': b['balls'], 'minutes': None, 'fours': b['fours'],
                                     'sixes': b['sixes'], 'sr': round(100 * b['runs'] / b['balls'], 2) if b['balls'] else None, 'out': b['out'], 'dismissal': b['dismissal']}
                                    for b in inn['batting']],
                        'bowling': [{'espn_id': ids[b['name']], 'name': b['name'], 'balls': b['balls'], 'overs': overs_text(b['balls']), 'maidens': b['maidens'],
                                     'runs': b['runs'], 'wickets': b['wickets'], 'econ': round(6 * b['runs'] / b['balls'], 2) if b['balls'] else None,
                                     'wides': b['wides'], 'noballs': b['noballs']} for b in inn['bowling']],
                        'overs': [], 'fall': inn.get('fall') or []})
    players = {team: [{'espn_id': espn_id_for(team, n, exact, loose), 'name': n} for n in names] for team, names in raw['info'].get('players', {}).items()}
    return {'innings': innings, 'players': players, 'coverage': 'scorecard', 'source': 'Rebuilt from ESPNcricinfo deliveries via the T20 World Cup archive'}


def timeline_rows(timeline):
    rows, total = [], 0
    for number, runs, wickets in sorted(timeline):
        total += runs
        rows.append({'over': int(number), 'runs': int(runs), 'wickets': int(wickets or 0), 'total': total})
    return rows


def cricsheet_overs(raw):
    out = {}
    for inn in raw.get('innings') or []:
        if inn.get('super_over'):
            continue
        timeline = [(o['over'] + 1, sum(d['runs']['total'] for d in o['deliveries']),
                     sum(1 for d in o['deliveries'] for w in d.get('wickets', []) if w.get('kind') not in ('retired hurt', 'retired not out')))
                    for o in inn.get('overs') or []]
        if timeline:
            out[inn['team']] = timeline_rows(timeline)
    return out


# ------------------------------------------------------------------ main

def main(source=DEFAULT_SOURCE):
    odi_dir, t20_dir = Path(source) / 'data/odi_world_cup/scorecards', Path(source) / 'T20 World Cup/t20wc_matches'
    if not odi_dir.is_dir() or not t20_dir.is_dir():
        sys.exit(f'World Cup archives not found under {source}')
    official, cricsheet, historical = archive_state()
    exact, loose = identity_index()
    cards, overs, report = {}, {}, defaultdict(int)
    for path in sorted(odi_dir.glob('*.json')):
        mid = path.stem
        if mid not in official or mid in cricsheet:
            continue
        card, timeline = from_odi_scorecard(read(path))
        if mid not in historical and card['innings']:
            cards[mid] = card
            report['odi_scorecards_added'] += 1
        if timeline:
            overs[mid] = timeline
    for path in sorted(t20_dir.glob('*.json')):
        mid = path.stem
        if mid not in official or mid in cricsheet:
            continue
        raw = read(path)
        if not raw.get('innings'):
            continue
        if mid not in historical:
            cards[mid] = from_cricsheet(raw, exact, loose)
            report['t20_scorecards_added'] += 1
        timeline = cricsheet_overs(raw)
        if timeline:
            overs[mid] = timeline
    # Keep an innings' overs only when they add up to its scorecard total.
    checked = {}
    for mid, by_team in overs.items():
        card = historical.get(mid) or cards.get(mid)
        totals = {inn['team']: inn.get('runs') for inn in (card or {}).get('innings') or [] if not inn.get('super_over')}
        kept = {team: rows for team, rows in by_team.items() if totals.get(team) is not None and rows[-1]['total'] == totals[team]}
        report['innings_overs_rejected'] += len(by_team) - len(kept)
        if kept:
            checked[mid] = kept
    report['matches_with_overs'] = len(checked)
    unlinked = sum(1 for c in cards.values() for squad in c['players'].values() for p in squad if p['espn_id'].startswith('unlinked:'))
    report['unlinked_players'] = unlinked
    (ROOT / 'data/world_cup_scorecards.json').write_text(json.dumps(cards, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    (ROOT / 'data/world_cup_overs.json').write_text(json.dumps(checked, separators=(',', ':')), encoding='utf-8')
    print(json.dumps(dict(report), indent=1))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SOURCE)
