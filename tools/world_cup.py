"""Official World Cup history plus available scorecards.

Title counts, winners, runners-up and semi-finalists come from
data/world_cup_history.json, the complete official record. Cricsheet and
backfill scorecards are attached as available coverage only. They must never
be used as the public champion list.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from player_profile import esc

ROOT = Path(__file__).resolve().parent.parent
HISTORY_PATH = ROOT / 'data' / 'world_cup_history.json'

FAMILIES = (
    ('mens-odi', "Men's ODI World Cup", 'ODI', 'Men'),
    ('womens-odi', "Women's ODI World Cup", 'ODI', 'Women'),
    ('mens-t20', "Men's T20 World Cup", 'T20I', 'Men'),
    ('womens-t20', "Women's T20 World Cup", 'T20I', 'Women'),
)


def load_history():
    return json.loads(HISTORY_PATH.read_text(encoding='utf-8'))


def _event(match):
    return str(match.get('event') or '').lower()


def is_world_cup_match(match):
    event = _event(match)
    if 'qualifier' in event or 'super league' in event or 'champions trophy' in event:
        return False
    return 'world cup' in event or 'world twenty20' in event or 'world t20' in event


def family_key(match):
    if not is_world_cup_match(match):
        return None
    event = _event(match)
    women = match.get('gender') == 'Women' or 'women' in event
    t20 = 'twenty20' in event or 't20' in event
    if t20:
        return 'womens-t20' if women else 'mens-t20'
    return 'womens-odi' if women else 'mens-odi'


def editions(matches, gap_days=150):
    ordered = sorted(matches, key=lambda m: (m['date'], m['id']))
    groups = []
    current = []
    for match in ordered:
        if current:
            previous = date.fromisoformat(current[-1]['date'][:10])
            this = date.fromisoformat(match['date'][:10])
            if (this - previous).days > gap_days:
                groups.append(current)
                current = []
        current.append(match)
    if current:
        groups.append(current)
    return groups


def edition_champion(matches):
    for match in reversed(matches):
        winner = (match.get('outcome') or {}).get('winner')
        if winner:
            return winner, match
    return None, matches[-1] if matches else None


def family_record(matches):
    cups = []
    for group in editions(matches):
        winner, final = edition_champion(group)
        cups.append({
            'year': group[-1]['date'][:4],
            'start': group[0]['date'],
            'end': group[-1]['date'],
            'matches': len(group),
            'winner': winner,
            'final': final,
            'ids': [m['id'] for m in group],
        })
    titles = Counter(cup['winner'] for cup in cups if cup['winner'])
    return {'editions': cups, 'titles': titles, 'matches': matches}


def classify(matches):
    buckets = {key: [] for key, *_ in FAMILIES}
    for match in matches:
        key = family_key(match)
        if key:
            buckets[key].append(match)
    return {key: family_record(buckets[key]) for key, *_ in FAMILIES if buckets[key]}


def player_leaders(match_ids, cards, people, limit=20):
    batting = defaultdict(lambda: {'runs': 0, 'innings': 0, 'balls': 0, 'highest': None, 'fours': 0, 'sixes': 0, 'hundreds': 0, 'complete_balls': True})
    bowling = defaultdict(lambda: {'wickets': 0, 'innings': 0, 'conceded': 0, 'legal': 0, 'best': None, 'complete': True})
    scores = []
    spells = []
    for match_id in match_ids:
        card = cards.get(match_id) or {}
        match = card.get('match') or {}
        for inn in card.get('innings') or []:
            if inn.get('super_over'):
                continue
            for batter in inn.get('batting') or []:
                pid = batter.get('id')
                if not pid:
                    continue
                row = batting[pid]
                row['innings'] += 1
                if batter.get('runs') is None:
                    continue
                row['runs'] += batter['runs']
                if batter.get('runs') >= 100:
                    row['hundreds'] += 1
                if row['highest'] is None or batter['runs'] > row['highest']:
                    row['highest'] = batter['runs']
                if batter.get('balls') is None:
                    row['complete_balls'] = False
                else:
                    row['balls'] += batter['balls']
                if batter.get('fours') is not None:
                    row['fours'] += batter['fours']
                if batter.get('sixes') is not None:
                    row['sixes'] += batter['sixes']
                scores.append((batter['runs'], batter.get('balls'), people.get(pid, {}).get('name') or pid, match.get('date'), match_id, inn.get('team')))
            for bowler in inn.get('bowling') or []:
                pid = bowler.get('id')
                if not pid:
                    continue
                row = bowling[pid]
                row['innings'] += 1
                wkts = bowler.get('wickets')
                conceded = bowler.get('runs')
                legal = bowler.get('balls')
                if wkts is None or conceded is None:
                    row['complete'] = False
                    continue
                row['wickets'] += wkts
                row['conceded'] += conceded
                if legal is None:
                    row['complete'] = False
                else:
                    row['legal'] += legal
                best = row['best']
                if best is None or wkts > best[0] or (wkts == best[0] and conceded < best[1]):
                    row['best'] = (wkts, conceded)
                spells.append((wkts, conceded, people.get(pid, {}).get('name') or pid, match.get('date'), match_id))
    run_rows = []
    for pid, row in batting.items():
        name = people.get(pid, {}).get('name')
        if not name or not row['runs']:
            continue
        run_rows.append({
            'id': pid, 'name': name, 'runs': row['runs'], 'innings': row['innings'],
            'highest': row['highest'], 'hundreds': row['hundreds'],
            'avg': None, 'sr': (100 * row['runs'] / row['balls']) if row['complete_balls'] and row['balls'] else None,
        })
    run_rows.sort(key=lambda r: (-r['runs'], r['name']))
    wicket_rows = []
    for pid, row in bowling.items():
        name = people.get(pid, {}).get('name')
        if not name or not row['wickets']:
            continue
        best = row['best']
        wicket_rows.append({
            'id': pid, 'name': name, 'wickets': row['wickets'], 'innings': row['innings'],
            'best': f'{best[0]}/{best[1]}' if best else None,
            'avg': (row['conceded'] / row['wickets']) if row['complete'] and row['wickets'] else None,
        })
    wicket_rows.sort(key=lambda r: (-r['wickets'], r['name']))
    scores.sort(key=lambda row: (-row[0], row[4]))
    spells.sort(key=lambda row: (-row[0], row[1], row[4]))
    return {
        'runs': run_rows[:limit],
        'wickets': wicket_rows[:limit],
        'scores': scores[:15],
        'spells': [row for row in spells if row[0] >= 3][:15],
    }


def _team_html(name, team_paths):
    if not name:
        return esc('Not recorded')
    path = team_paths.get(name)
    return f'<a href="{esc(path)}">{esc(name)}</a>' if path else esc(name)


def _teams_html(names, team_paths):
    return ', '.join(_team_html(name, team_paths) for name in names if name) or esc('No knockout stage')


def merge_official(matches, cards, people):
    history = load_history()
    archive = classify(matches)
    families = {}
    for key, label, fmt, gender in FAMILIES:
        official = history['families'][key]
        rec = archive.get(key) or {'editions': [], 'titles': Counter(), 'matches': []}
        by_year = {str(cup['year']): cup for cup in rec['editions']}
        editions_out = []
        for cup in official['editions']:
            year = str(cup['year'])
            found = by_year.get(year) or {}
            editions_out.append({
                **cup,
                'year': year,
                'archive_matches': found.get('matches', 0),
                'archive_ids': found.get('ids') or [],
                'archive_final': found.get('final'),
            })
        match_ids = [mid for cup in rec['editions'] for mid in cup['ids']]
        families[key] = {
            'key': key,
            'label': label,
            'format': fmt,
            'gender': gender,
            'official': official,
            'editions': editions_out,
            'titles': Counter(official['titles']),
            'records': official.get('records') or [],
            'archive': rec,
            'leaders': player_leaders(match_ids, cards, people, 25) if match_ids else {'runs': [], 'wickets': [], 'scores': [], 'spells': []},
            'archive_match_count': len(rec['matches']),
        }
    return {'meta': {k: history[k] for k in ('source', 'checked_at', 'note') if k in history}, 'families': families}


def timeline_table(family, team_paths):
    rows = []
    for cup in reversed(family['editions']):
        hosts = ', '.join(cup.get('hosts') or []) or 'Not recorded'
        semis = cup.get('losing_semi_finalists') or []
        if cup.get('knockout') is False:
            semi_html = esc('No knockout stage')
        elif semis:
            semi_html = _teams_html(semis, team_paths)
        else:
            semi_html = esc('Not listed')
        result = cup.get('final_result') or ''
        if cup.get('winner_score') and cup.get('runner_up_score'):
            result = f'{result} ({cup["winner_score"]} v {cup["runner_up_score"]})' if result else f'{cup["winner_score"]} v {cup["runner_up_score"]}'
        rows.append([
            cup['year'],
            esc(hosts),
            _team_html(cup.get('winner'), team_paths),
            _team_html(cup.get('runner_up'), team_paths),
            semi_html,
            esc(result or 'Not recorded'),
        ])
    return rows


def titles_leaderboard(family, team_paths):
    return [
        [_team_html(team, team_paths), str(count)]
        for team, count in family['titles'].most_common()
    ]


def official_record_rows(family):
    return [
        [esc(row['metric']), esc(row['holder']), esc(str(row['value'])), esc(row.get('detail') or '')]
        for row in family.get('records') or []
    ]


def coverage_note(family):
    official_n = len(family['editions'])
    archive_n = family['archive_match_count']
    covered = sum(1 for cup in family['editions'] if cup['archive_matches'])
    return (
        f'{official_n} official editions. {covered} of those years have at least one scorecard in this archive '
        f'({archive_n:,} recorded matches). Player tables below use available innings only.'
    )
