"""Official team and innings records, independent of the scorecard archive."""
from __future__ import annotations

import json
from pathlib import Path

from player_profile import esc

ROOT = Path(__file__).resolve().parent.parent


def load_team_records():
    path = ROOT / 'data' / 'official_team_records.json'
    return json.loads(path.read_text(encoding='utf-8'))


def load_innings_records():
    path = ROOT / 'data' / 'official_innings_records.json'
    return json.loads(path.read_text(encoding='utf-8'))


def team_formats(payload, team, gender='Men'):
    return ((payload.get('teams') or {}).get(team) or {}).get(gender) or {}


def format_result(row):
    played = row.get('played')
    won = row.get('won')
    lost = row.get('lost')
    extra = []
    if row.get('draw'):
        extra.append(f'{row["draw"]} draws')
    if row.get('tied'):
        extra.append(f'{row["tied"]} ties')
    if row.get('nr'):
        extra.append(f'{row["nr"]} no results')
    tail = ', ' + ', '.join(extra) if extra else ''
    return f'{played:,} matches, {won:,} wins, {lost:,} losses{tail}'


def official_team_panel(team, payload, table):
    rows = team_formats(payload, team)
    if not rows:
        return ''
    table_rows = []
    for fmt in ('Test', 'ODI', 'T20I'):
        row = rows.get(fmt)
        if not row:
            continue
        table_rows.append([
            fmt,
            f'{row["played"]:,}',
            f'{row["won"]:,}',
            f'{row["lost"]:,}',
            f'{row.get("draw") or row.get("tied") or 0:,}',
            f'{row.get("nr") or 0:,}',
            esc(row.get('span') or ''),
        ])
    if not table_rows:
        return ''
    html = '<section class="panel" id="official-results"><h2>Official career results</h2>'
    html += '<p class="muted">Complete men\'s results from ESPNcricinfo team summaries, not from the ball-by-ball archive. Draws apply to Tests; ties and no results apply to limited overs.</p>'
    html += table(['Format', 'Played', 'Won', 'Lost', 'Draw / tied', 'No result', 'Span'], table_rows, caption=team + ' official men\'s results')
    html += '<p class="note">Women\'s team results and the match list below use published scorecards in this archive.</p></section>'
    return html


def official_innings_table(payload, table):
    rows = [
        [esc(r['metric']), esc(r['holder']), esc(r.get('team') or ''), esc(r['value']), esc(r.get('detail') or '')]
        for r in payload.get('records') or []
    ]
    if not rows:
        return ''
    return table(['Record', 'Player', 'Team', 'Value', 'Detail'], rows, caption='Official international innings and career landmarks')


def official_h2h(payload, left, right):
    h2h = payload.get('h2h') or {}
    key = '|'.join(sorted((left, right)))
    row = h2h.get(f'{left}|{right}')
    swapped = False
    if not row:
        row = h2h.get(f'{right}|{left}')
        swapped = True
    if not row:
        row = h2h.get(key)
    if not row:
        return None
    out = {}
    for fmt, stats in row.items():
        left_wins = stats['right_wins'] if swapped else stats['left_wins']
        right_wins = stats['left_wins'] if swapped else stats['right_wins']
        out[fmt] = {
            'played': stats['played'],
            'left_wins': left_wins,
            'right_wins': right_wins,
            'other': stats.get('other', 0),
        }
    return out
