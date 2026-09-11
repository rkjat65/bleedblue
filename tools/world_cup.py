"""Official World Cup history plus ball-by-ball analysis windows.

Title counts, winners, runners-up and semi-finalists come from
data/world_cup_history.json, the complete official record. Cricsheet and
backfill scorecards are attached as coverage only. They must never be used
as the public champion list.

Player tables start at the first year with over-by-over deliveries. Pathway
events (qualifiers, League 2, region finals) are not mixed into those tables.
Unlabelled full-member matches inside an official edition window, including
Afghanistan games Cricsheet withholds, are attached to that edition.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, timedelta
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

# Pathway and neighbouring ICC events that mention "World Cup" in the name.
_BLOCKED = (
    'qualifier', 'qualifying', 'qualification',
    'league',
    'champions trophy',
    'warm-up', 'warmup',
    'sub regional', 'region final',
    'division',
    'play-off', 'playoff',
)

# Days before the official final that still belong to that edition.
# T20 World Cups last about four weeks; ODI World Cups about six.
_WINDOW_BEFORE = {
    'mens-odi': 60,
    'womens-odi': 60,
    'mens-t20': 40,
    'womens-t20': 40,
}

_WINDOWS = None


def load_history():
    return json.loads(HISTORY_PATH.read_text(encoding='utf-8'))


def _event(match):
    return str(match.get('event') or '').lower()


def is_world_cup_match(match):
    event = _event(match)
    if any(token in event for token in _BLOCKED):
        return False
    return 'world cup' in event or 'world twenty20' in event or 'world t20' in event


def edition_windows():
    """Inclusive start/end dates for each official edition."""
    global _WINDOWS
    if _WINDOWS is not None:
        return _WINDOWS
    history = load_history()
    windows = {}
    for key, *_ in FAMILIES:
        pad = _WINDOW_BEFORE[key]
        items = []
        for cup in history['families'][key]['editions']:
            final = cup.get('final_date')
            if not final:
                continue
            end = date.fromisoformat(final[:10])
            if cup.get('start_date'):
                start = date.fromisoformat(cup['start_date'][:10])
            else:
                start = end - timedelta(days=pad)
            items.append((start.isoformat(), end.isoformat(), str(cup['year'])))
        windows[key] = items
    _WINDOWS = windows
    return windows


def in_official_window(day, windows):
    value = (day or '')[:10]
    return next((year for start, end, year in windows if start <= value <= end), None)


def _family_from_event(match):
    event = _event(match)
    women = match.get('gender') == 'Women' or 'women' in event
    t20 = 'twenty20' in event or 't20' in event
    if t20:
        return 'womens-t20' if women else 'mens-t20'
    return 'womens-odi' if women else 'mens-odi'


def family_key(match):
    if not is_world_cup_match(match):
        return None
    key = _family_from_event(match)
    if in_official_window(match.get('date'), edition_windows()[key]) is None:
        return None
    return key


def attach_unlabelled(match, windows=None):
    """Attach empty-event matches that sit inside an official World Cup window.

    Cricsheet withholds Afghanistan, so those games often arrive from
    ESPNcricinfo with batting tables and no tournament name. A bilateral
    series just outside the window is left unattached.
    """
    if match.get('event') or family_key(match):
        return None
    windows = windows or edition_windows()
    fmt, gender = match.get('format'), match.get('gender')
    day = match.get('date')
    for key, _label, want_fmt, want_gender in FAMILIES:
        if fmt != want_fmt or gender != want_gender:
            continue
        if in_official_window(day, windows[key]):
            return key
    return None


def world_cup_family(match, windows=None):
    return family_key(match) or attach_unlabelled(match, windows)


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
    windows = edition_windows()
    buckets = {key: [] for key, *_ in FAMILIES}
    for match in matches:
        key = family_key(match) or attach_unlabelled(match, windows)
        if key:
            buckets[key].append(match)
    return {key: family_record(buckets[key]) for key, *_ in FAMILIES if buckets[key]}


def pretty_date(iso):
    if not iso:
        return ''
    day = date.fromisoformat(iso[:10])
    return f"{day.day} {day.strftime('%B')} {day.year}"


def innings_depth(card):
    inns = (card or {}).get('innings') or []
    if any(inn.get('overs') for inn in inns):
        return 'balls'
    if any((inn.get('batting') or inn.get('bowling')) for inn in inns):
        return 'tables'
    return 'none'


def analysis_window(matches, cards):
    """Describe the ball-by-ball window inside a classified World Cup family.

    Counts for tables-only and Afghanistan gaps are taken from the first
    over-by-over date onward, so a 1975 scorecard does not inflate the
    2003 analysis window.
    """
    first_balls = last_balls = None
    depths = []
    for match in matches:
        depth = innings_depth((cards or {}).get(match['id']))
        day = match['date'][:10]
        depths.append((match, day, depth))
        if depth == 'balls':
            if first_balls is None or day < first_balls:
                first_balls = day
            if last_balls is None or day > last_balls:
                last_balls = day
    counts = Counter()
    afghanistan_without_balls = 0
    window_matches = 0
    for match, day, depth in depths:
        if first_balls and day < first_balls:
            continue
        window_matches += 1
        counts[depth] += 1
        if depth != 'balls' and 'Afghanistan' in (match.get('teams') or []):
            afghanistan_without_balls += 1
    return {
        'from_year': first_balls[:4] if first_balls else None,
        'from_date': first_balls,
        'to_date': last_balls,
        'ball_by_ball': counts['balls'],
        'scorecard_only': counts['tables'],
        'no_innings': counts['none'],
        'matches': window_matches if first_balls else len(matches),
        'afghanistan_without_balls': afghanistan_without_balls,
    }


def analysis_heading(family):
    year = (family.get('analysis') or {}).get('from_year')
    if not year:
        return 'Recorded innings in this archive'
    return f'Ball-by-ball analysis from {year}'


def analysis_lede(family):
    analysis = family.get('analysis') or {}
    if not analysis.get('from_date'):
        return 'This archive does not yet hold over-by-over deliveries for this tournament. Official titles and the timeline above remain complete.'
    text = f"Ball-by-ball data is available from {pretty_date(analysis['from_date'])}."
    text += f" {analysis['ball_by_ball']:,} matches have over-by-over deliveries."
    if analysis.get('scorecard_only'):
        text += f" {analysis['scorecard_only']:,} further matches have batting and bowling tables only."
    if analysis.get('afghanistan_without_balls'):
        text += (
            f" {analysis['afghanistan_without_balls']} Afghanistan World Cup matches in this window "
            'have scorecards without deliveries; Cricsheet does not publish Afghanistan.'
        )
    text += ' The tables below count recorded innings from that window. They are not complete World Cup career records. Missing innings are omitted, never zero-filled.'
    return text


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
        analysis = analysis_window(rec['matches'], cards)
        from_date = analysis.get('from_date')
        dates = {match['id']: match['date'][:10] for match in rec['matches']}
        match_ids = [mid for cup in rec['editions'] for mid in cup['ids']]
        if from_date:
            match_ids = [mid for mid in match_ids if dates.get(mid, '') >= from_date]
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
            'analysis': analysis,
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
    first = family['official']['first_year']
    latest = family['official']['latest_year']
    covered = sum(1 for cup in family['editions'] if cup['archive_matches'])
    analysis = family.get('analysis') or {}
    note = f'{official_n} official editions from {first} to {latest}. {covered} of those years have at least one scorecard in this archive.'
    if analysis.get('from_year'):
        note += f" Ball-by-ball analysis starts in {analysis['from_year']}."
    return note
