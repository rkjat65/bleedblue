"""IPL and T20 World Cup tabs on player profiles.

Figures come from the analytics app's ball-by-ball export (data/leagues/),
keyed by the same Cricsheet id as the international careers. Every match in
these competitions has ball-by-ball data, so the records are complete.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

from cricket_charts import _n, _svg, _ticks, figure
from profile_formats import esc, lean_table, n, r2, rate

LEAGUES = (
    ('ipl', 'IPL', 'the IPL', '/ipl'),
    ('t20wc', 'T20 World Cup', 'T20 World Cups', '/t20-world-cup'),
)
LABELS = {key: label for key, label, _, _ in LEAGUES}


def load_leagues(root):
    out = {}
    for key, *_ in LEAGUES:
        path = Path(root) / 'data' / 'leagues' / f'{key}.json'
        if path.exists():
            data = json.loads(path.read_text(encoding='utf-8'))
            # Every edition the competition has held, so charts show real gaps and no phantom years.
            data.setdefault('meta', {})['editions'] = sorted({s['edition'] for p in data.get('players', {}).values() for s in p.get('seasons') or []})
            out[key] = data
    return out


def season_bars(record, key, caption, editions):
    """Bars per edition across the player's span; editions missed show as gaps."""
    played = {s['edition']: s.get(key) or 0 for s in record.get('seasons') or []}
    if len(played) < 2:
        return ''
    first, last = min(played), max(played)
    axis = [e for e in (editions or sorted(played)) if first <= e <= last]
    peak = max(played.values())
    if peak <= 0:
        return ''
    left, right, top, bottom = 40, 470, 16, 140
    plot_h, slot = bottom - top, (right - left) / len(axis)
    bar_w = max(3, min(26, slot * 0.68))
    grid = ''.join(f'<line class="cw-grid" x1="{left}" y1="{bottom - v / peak * plot_h:.1f}" x2="{right}" y2="{bottom - v / peak * plot_h:.1f}"/>'
                   f'<text class="cw-axis" x="{left - 6}" y="{bottom - v / peak * plot_h + 3:.1f}" text-anchor="end">{_n(v)}</text>'
                   for v in _ticks(peak) if v <= peak)
    best = max(played, key=lambda e: played[e])
    step = max(1, -(-len(axis) // 8))
    bars = ''
    for i, edition in enumerate(axis):
        x = left + i * slot + (slot - bar_w) / 2
        if edition in played:
            value = played[edition]
            h = value / peak * plot_h
            bars += (f'<rect class="cw-bar cw-fmt{" is-best" if edition == best else ""}" x="{x:.1f}" y="{bottom - h:.1f}" width="{bar_w:.1f}" '
                     f'height="{max(h, 0.8 if value else 0):.1f}" rx="2"><title>{edition}: {_n(value)} {key}</title></rect>')
            if len(axis) <= 16 and value:
                bars += f'<text class="cw-bar-value" x="{x + bar_w / 2:.1f}" y="{bottom - h - 4:.1f}" text-anchor="middle">{_n(value)}</text>'
        if i % step == 0 or i == len(axis) - 1:
            bars += f'<text class="cw-axis" x="{x + bar_w / 2:.1f}" y="{bottom + 14}" text-anchor="middle">{edition}</text>'
    return figure(caption, caption, _svg(480, 160, grid + bars, caption), f'{key.title()} in each edition played. The brightest bar is the best; an empty slot is an edition missed.')


def player_leagues(pid, leagues):
    """[(key, record)] for each competition this player appeared in."""
    found = []
    for key, *_ in LEAGUES:
        record = ((leagues.get(key) or {}).get('players') or {}).get(pid)
        if record and (record.get('career') or {}).get('matches'):
            found.append((key, record))
    return found


def figures(c):
    """Derived rates; a rate without a denominator stays unknown."""
    innings = c.get('innings') or 0
    return {
        **c,
        'notouts': innings - (c.get('outs') or 0),
        'avg': rate(c.get('runs'), c.get('outs')),
        'sr': rate(c.get('runs'), c.get('balls'), 100),
        'highest': (f"{c['hs']}{'*' if c.get('hs_not_out') else ''}" if innings else None),
        'bowlAvg': rate(c.get('conceded'), c.get('wickets')),
        'econ': rate(c.get('conceded'), c.get('bowl_balls'), 6),
        'bowlSr': rate(c.get('bowl_balls'), c.get('wickets')),
        'dot_pct': rate(c.get('dots'), c.get('bowl_balls'), 100),
        'overs': (f"{c['bowl_balls'] // 6}.{c['bowl_balls'] % 6}" if c.get('bowl_balls') else None),
    }


def role(c):
    runs, wickets = c.get('runs') or 0, c.get('wickets') or 0
    if (c.get('stumpings') or 0) >= 3:
        return 'keeper'
    if wickets >= 25 and runs >= 500:
        return 'all-rounder'
    if wickets >= 5 and wickets * 20 > runs:
        return 'bowler'
    return 'batter'


def span(record):
    seasons = [s['edition'] for s in record.get('seasons') or []]
    if not seasons:
        return ''
    return seasons[0] if seasons[0] == seasons[-1] else f'{seasons[0]} to {seasons[-1]}'


def hero(f, kind, label):
    if kind == 'bowler':
        spec = [(n(f['wickets']), 'Wickets'), (r2(f['econ'], f['bowl_balls']), 'Economy'), (r2(f['bowlAvg'], f['wickets']), 'Average'),
                (r2(f['bowlSr'], f['wickets']), 'Strike rate'), (esc(f['best'] or '-'), 'Best'), (r2(f['dot_pct'], f['bowl_balls']), 'Dot ball %')]
    elif kind == 'all-rounder':
        spec = [(n(f['runs']), 'Runs'), (r2(f['sr'], f['balls']), 'Strike rate'), (r2(f['avg'], f['outs']), 'Bat avg'),
                (n(f['wickets']), 'Wickets'), (r2(f['econ'], f['bowl_balls']), 'Economy'), (n(f['awards']), 'Player of match')]
    elif kind == 'keeper':
        spec = [(n(f['runs']), 'Runs'), (r2(f['sr'], f['balls']), 'Strike rate'), (r2(f['avg'], f['outs']), 'Average'),
                (n(f['fifties'] + f['hundreds']), '50+ scores'), (n(f['catches']), 'Catches'), (n(f['stumpings']), 'Stumpings')]
    else:
        spec = [(n(f['runs']), 'Runs'), (r2(f['sr'], f['balls']), 'Strike rate'), (r2(f['avg'], f['outs']), 'Average'),
                (n(f['hundreds']), 'Hundreds'), (n(f['fifties']), 'Fifties'), (esc(f['highest'] or '-'), 'Highest')]
    tiles = ''.join(f'<div{" class=lead" if i == 0 else ""}><strong>{v}</strong><span>{t}</span></div>' for i, (v, t) in enumerate(spec))
    return f'<div class="pf-hero" aria-label="{esc(label)} career headline figures">{tiles}</div>'


def career_lines(f, label, want_bowling):
    out = lean_table(f'{label} batting record', ['Batting', ('Mat', 'Matches'), ('Inns', 'Innings'), ('NO', 'Not outs'), 'Runs', ('HS', 'Highest score'),
                     ('Avg', 'Batting average'), ('BF', 'Balls faced'), ('SR', 'Strike rate'), '100', '50', '0', '4s', '6s'],
                     [['Career', n(f['matches']), n(f['innings']), n(f['notouts']), n(f['runs']), esc(f['highest'] or '-'), r2(f['avg'], f['outs']),
                       n(f['balls']), r2(f['sr'], f['balls']), n(f['hundreds']), n(f['fifties']), n(f['ducks']), n(f['fours']), n(f['sixes'])]], css='pf-line')
    if want_bowling:
        out += lean_table(f'{label} bowling record', ['Bowling', ('Mat', 'Matches'), ('Inns', 'Bowling innings'), 'Overs', ('Runs', 'Runs conceded'), ('Wkts', 'Wickets'),
                          ('BBI', 'Best bowling in an innings'), ('Avg', 'Bowling average'), ('Econ', 'Runs conceded per over'), ('SR', 'Balls per wicket'),
                          ('Dot %', 'Share of legal balls with no run'), '4w', '5w'],
                          [['Career', n(f['matches']), n(f['bowl_innings']), esc(f['overs'] or '-'), n(f['conceded']), n(f['wickets']), esc(f['best'] or '-'),
                            r2(f['bowlAvg'], f['wickets']), r2(f['econ'], f['bowl_balls']), r2(f['bowlSr'], f['wickets']), r2(f['dot_pct'], f['bowl_balls']),
                            n(f['four_w']), n(f['five_w'])]], css='pf-line')
    out += lean_table(f'{label} fielding and awards', ['Other', ('Ct', 'Catches'), ('St', 'Stumpings'), ('PoM', 'Player of the match awards')],
                      [['Career', n(f['catches']), n(f['stumpings']), n(f['awards'])]], css='pf-line')
    return out


def season_table(record, label, want_bowling):
    head = ['Season', 'Team', ('Mat', 'Matches'), 'Runs', ('HS', 'Highest score'), ('Avg', 'Batting average'), ('SR', 'Strike rate'), '50+']
    if want_bowling:
        head += [('Wkts', 'Wickets'), ('BBI', 'Best bowling in an innings'), ('Econ', 'Runs conceded per over')]
    body = []
    for s in reversed(record.get('seasons') or []):
        f = figures(s)
        row = [esc(s['edition']), esc(' / '.join(s.get('teams') or []) or '-'), n(f['matches']), n(f['runs']), esc(f['highest'] or '-'),
               r2(f['avg'], f['outs']), r2(f['sr'], f['balls']), n(f['hundreds'] + f['fifties'])]
        if want_bowling:
            row += [n(f['wickets']), esc(f['best'] or '-'), r2(f['econ'], f['bowl_balls'])]
        body.append(row)
    c = figures(record['career'])
    foot = ['Career', '', n(c['matches']), n(c['runs']), esc(c['highest'] or '-'), r2(c['avg'], c['outs']), r2(c['sr'], c['balls']), n(c['hundreds'] + c['fifties'])]
    if want_bowling:
        foot += [n(c['wickets']), esc(c['best'] or '-'), r2(c['econ'], c['bowl_balls'])]
    return lean_table(f'{label} record by season', head, body, foot=foot, left=(1,))


def teams_line(record):
    parts = []
    for t in record.get('teams') or []:
        years = t['first'] if t['first'] == t['last'] else f"{t['first']} to {t['last']}"
        parts.append(f'<span class="lg-team"><b>{esc(t["team"])}</b> {esc(years)} · {t["matches"]:,} matches</span>')
    return f'<div class="lg-teams">{"".join(parts)}</div>' if parts else ''


def app_link(prefix, name, kind):
    section = 'bowling' if kind == 'bowler' else 'batting'
    return f'{prefix}/{section}/{quote(name, safe="")}'


def league_panel(player, key, record, meta):
    label = LABELS[key]
    _, _, plural, prefix = next(x for x in LEAGUES if x[0] == key)
    c = figures(record['career'])
    kind = role(c)
    want_bowling = kind in ('bowler', 'all-rounder') or (c.get('wickets') or 0) >= 5 or (c.get('bowl_innings') or 0) >= 10
    chart_wickets = kind in ('bowler', 'all-rounder') or (c.get('wickets') or 0) >= 15
    name = player['name']
    years = span(record)
    body = f'<section class="fmt-panel fmt-{key}" id="{key}" data-fmt-panel="{key}" aria-label="{esc(label)} career">'
    body += (f'<header class="pf-fmt-head"><div><p class="eyebrow">{esc(label.upper())} CAREER{(" · " + esc(years)) if years else ""}</p>'
             f'<h2 id="{key}-summary">{esc(name)} in {esc(plural)}</h2></div>'
             f'<p class="pf-cov is-complete" title="Every match in this competition has ball-by-ball data">Ball by ball, every match</p></header>')
    body += hero(c, kind, label)
    body += teams_line(record)
    body += f'<section class="panel pf-block"><h2>{esc(label)} career record</h2>{career_lines(c, label, want_bowling)}</section>'
    editions = meta.get('editions')
    charts = []
    if kind == 'bowler':
        charts.append(season_bars(record, 'wickets', f'{label} wickets by season', editions))
    else:
        charts.append(season_bars(record, 'runs', f'{label} runs by season', editions))
        if chart_wickets:
            charts.append(season_bars(record, 'wickets', f'{label} wickets by season', editions))
    charts = ''.join(x for x in charts if x)
    if charts:
        body += f'<section class="panel pf-block"><h2>{esc(label)} career in charts</h2><div class="pf-charts">{charts}</div></section>'
    body += f'<section class="panel pf-block"><h2>{esc(label)} season by season</h2>{season_table(record, label, want_bowling)}</section>'
    analysis = app_link(prefix, record['name'], kind)
    body += (f'<section class="panel pf-block lg-deep"><h2>Ball-by-ball {esc(label)} analysis</h2>'
             f'<p>Phase splits, bowler and batter matchups, dismissal patterns and every innings for {esc(name)} in the {esc(label)} analytics.</p>'
             f'<p><a class="button primary" href="{esc(analysis)}">Open {esc(label)} analysis</a> '
             f'<a class="button" href="{prefix}/records">{esc(label)} records</a></p>'
             f'<p class="pf-fine">Source: Cricsheet ball-by-ball data, {meta.get("matches", 0):,} matches to {esc(meta.get("last", ""))}. '
             'Balls faced exclude wides. Bowlers are charged wides and no-balls. Super overs are excluded.'
             f'{" T20 World Cup matches are T20Is, so they are also counted in the T20I record." if key == "t20wc" else ""}</p></section>')
    body += '</section>'
    return body


def overview_block(found):
    """A short cross-competition table for the overview tab."""
    if not found:
        return ''
    body = []
    for key, record in found:
        c = figures(record['career'])
        label = LABELS[key]
        body.append([f'<a href="#{key}" data-fmt-link="{key}">{esc(label)}</a>', esc(span(record)), n(c['matches']), n(c['runs']),
                     r2(c['avg'], c['outs']), r2(c['sr'], c['balls']), n(c['wickets']), r2(c['econ'], c['bowl_balls']), esc(c['best'] or '-')])
    table = lean_table('IPL and T20 World Cup records', ['Competition', 'Span', ('Mat', 'Matches'), 'Runs', ('Avg', 'Batting average'), ('SR', 'Strike rate'),
                       ('Wkts', 'Wickets'), ('Econ', 'Runs conceded per over'), ('BBI', 'Best bowling in an innings')], body, css='pf-leagues', left=(1,))
    return (f'<section class="panel pf-block" id="league-records"><h2>IPL and T20 World Cup</h2>{table}'
            '<p class="pf-fine">From ball-by-ball data. T20 World Cup matches are also part of the T20I record above.</p></section>')


def chips(found):
    return ''.join(f'<a class="pf-chip fmt-{key}" href="#{key}" data-fmt-link="{key}"><i></i><b>{esc(LABELS[key])}</b>'
                   f'<span>{record["career"]["matches"]:,} matches</span></a>' for key, record in found)


def switch_items(found):
    return ''.join(f'<a href="#{key}" data-fmt="{key}" class="fmt-{key}">{esc(LABELS[key])}<small>{record["career"]["matches"]:,}</small></a>'
                   for key, record in found)


def seo_clause(found):
    """'9,336 IPL runs' style phrase for the description, or ''."""
    for key, record in found:
        if key != 'ipl':
            continue
        c = record['career']
        if (c.get('wickets') or 0) >= 25 and (c.get('wickets') or 0) * 20 > (c.get('runs') or 0):
            return f'{c["wickets"]:,} IPL wickets'
        if (c.get('runs') or 0) >= 100:
            return f'{c["runs"]:,} IPL runs'
        return f'{c["matches"]:,} IPL matches'
    return ''
