"""Interactive tools on the shared lake: Matchups, Phases, Fantasy, Quiz and the Tools hub.

Each page ships a crawlable shell (heading, method notes, controls); the
browser fills the results from the Parquet lake through web/lake.js. The
Quiz needs no database: it reads small JSON pools written here at build time.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

from profile_formats import format_role

TOOL_PAGES = {'/matchups/': 'matchups', '/phases/': 'phases', '/fantasy/': 'fantasy', '/quiz/': 'quiz'}
COMPETITIONS = [('all', 'All cricket'), ('Test', 'Tests'), ('ODI', 'ODIs'), ('T20I', 'T20Is'), ('IPL', 'IPL'), ('T20WC', 'T20 World Cup')]


def esc(value):
    return html.escape(str(value), quote=True)


def seg(ident, label, items, value):
    buttons = ''.join(f'<button type="button" data-value="{esc(v)}" aria-pressed="{"true" if v == value else "false"}">{esc(t)}</button>' for v, t in items)
    return f'<div class="tl-field"><span class="tl-label" id="{ident}-label">{esc(label)}</span><div class="tl-seg" id="{ident}" role="group" aria-labelledby="{ident}-label">{buttons}</div></div>'


def field(ident, label, control):
    return f'<label class="tl-field" for="{ident}"><span class="tl-label">{esc(label)}</span>{control}</label>'


def mast(eyebrow, title, lede):
    return f'<div class="tl-mast"><p class="eyebrow">{esc(eyebrow)}</p><h1>{esc(title)}</h1><p class="tl-lede">{esc(lede)}</p></div>'


def status(ident='tl-status'):
    return f'<p class="tl-status" id="{ident}" role="status" aria-live="polite">Loading ball-by-ball data…</p>'


def noscript():
    return '<noscript><p class="tl-empty">This tool runs in your browser and needs JavaScript.</p></noscript>'


GENDER = [('Men', 'Men'), ('Women', 'Women')]


def matchups_markup():
    controls = (seg('mu-comp', 'Competition', COMPETITIONS, 'all') + seg('mu-gender', 'Gender', GENDER, 'Men')
                + field('mu-batter', 'Batter', '<input id="mu-batter" type="search" autocomplete="off" placeholder="Type a batter">')
                + field('mu-bowler', 'Bowler', '<input id="mu-bowler" type="search" autocomplete="off" placeholder="Type a bowler">')
                + field('mu-from', 'From year', '<input id="mu-from" type="number" min="2000" max="2100" inputmode="numeric">')
                + field('mu-to', 'To year', '<input id="mu-to" type="number" min="2000" max="2100" inputmode="numeric">')
                + '<div class="tl-actions"><button type="button" id="mu-swap">Swap</button><button type="button" id="mu-clear">Clear</button></div>')
    return (mast('BATTER V BOWLER', 'Matchups',
                 'Every ball between a batter and a bowler in Tests, ODIs, T20Is, the IPL and the T20 World Cup. Pick one player to see their toughest opponents, or both for the full duel.')
            + f'<section class="panel tl-controls" aria-label="Choose players">{controls}</section>{status()}{noscript()}'
            + '<section class="panel tl-out" id="mu-out" aria-live="polite"></section>'
            + '<p class="note">Balls faced exclude wides. Dismissals count only wickets credited to the bowler, so run outs are left out. '
              'Ball-by-ball records start when Cricsheet has them: Tests and ODIs from the early 2000s, T20Is and the IPL from the start. '
              'Cricsheet does not publish Afghanistan matches; their men\'s T20 World Cup games are rebuilt from public play-by-play.</p>')


def phases_markup():
    comps = [('T20I', 'T20Is'), ('IPL', 'IPL'), ('T20WC', 'T20 World Cup'), ('ODI', 'ODIs')]
    controls = (seg('ph-comp', 'Competition', comps, 'IPL') + seg('ph-gender', 'Gender', GENDER, 'Men')
                + field('ph-from', 'From season', '<select id="ph-from"></select>') + field('ph-to', 'To season', '<select id="ph-to"></select>')
                + field('ph-team', 'Batting team', '<select id="ph-team"><option value="">All teams</option></select>')
                + field('ph-venue', 'Ground', '<select id="ph-venue"><option value="">All grounds</option></select>'))
    return (mast('HOW INNINGS ARE BUILT', 'Phases',
                 'Run rate, wickets, boundaries and dot balls in the powerplay, the middle overs and the death, over by over, for T20Is, ODIs, the IPL and the T20 World Cup.')
            + f'<section class="panel tl-controls" aria-label="Filters">{controls}</section>{status()}{noscript()}'
            + '<section class="tl-out" id="ph-out" aria-live="polite"></section>'
            + '<p class="note">T20 phases are overs 1 to 6, 7 to 15 and 16 to 20; ODI phases are overs 1 to 10, 11 to 40 and 41 to 50. '
              'Run rate counts every run, extras included, per six legal balls. Wickets include run outs. Super overs are excluded.</p>')


def fantasy_markup():
    comps = [('IPL', 'IPL'), ('T20I-Men', "Men's T20Is"), ('T20I-Women', "Women's T20Is")]
    controls = (seg('fa-comp', 'Competition', comps, 'IPL')
                + field('fa-team1', 'Team 1', '<select id="fa-team1"></select>') + field('fa-team2', 'Team 2', '<select id="fa-team2"></select>')
                + field('fa-venue', 'Ground (optional)', '<select id="fa-venue"><option value="">Any ground</option></select>'))
    points = ('<details class="tl-rules"><summary>How points are counted</summary><ul>'
              '<li>Batting: 1 a run, 1 a four bonus, 2 a six bonus, 8 for a fifty or 16 for a hundred, minus 2 for a duck.</li>'
              '<li>Bowling: 25 a wicket, 8 more for each bowled or lbw, and 4, 8 or 16 for three, four or five wickets.</li>'
              '<li>Fielding: 8 a catch, 12 a stumping, 6 a run out as the first fielder named.</li>'
              '<li>Projection: the average of the last 10 matches. With two or more matches at the chosen ground, '
              'the ground average counts for 40%.</li>'
              '<li>XI: highest projections first, at most 7 from one team, at least 3 bowlers or all-rounders. Captain and vice-captain are the top two.</li></ul></details>')
    return (mast('FANTASY PICKS', 'Fantasy',
                 'Pick two teams and, if you like, a ground. Projections come from each player\'s last 10 matches and their record at that ground.')
            + f'<section class="panel tl-controls" aria-label="Choose teams">{controls}</section>{status()}{noscript()}'
            + '<section class="tl-out" id="fa-out" aria-live="polite"></section>' + points
            + '<p class="note">Squads are the players who appeared for each team in its latest season (IPL) or its last 15 matches (T20Is). '
              'These are form guides from past matches, not predictions of selection.</p>')


QUIZ_MODES = [('ipl', 'IPL'), ('t20wc', "Men's T20 World Cup"), ('test', "Men's Tests"), ('odi', "Men's ODIs"), ('t20i', "Men's T20Is"),
              ('wodi', "Women's ODIs"), ('wt20i', "Women's T20Is")]


def quiz_markup():
    modes = ''.join(f'<option value="{k}">{esc(v)}</option>' for k, v in QUIZ_MODES)
    controls = (field('qz-mode', 'Competition', f'<select id="qz-mode">{modes}</select>')
                + seg('qz-level', 'Level', [('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')], 'medium'))
    return (mast('GUESS THE PLAYER', 'Quiz', 'Name the player from their career numbers. Four choices, one answer; keep the streak going.')
            + f'<section class="panel tl-controls" aria-label="Quiz settings">{controls}<p class="tl-streak" id="qz-streak"></p></section>'
            + status() + noscript() + '<section class="panel tl-out" id="qz-out" aria-live="polite"></section>'
            + '<p class="note">Easy picks players with 60 or more matches, medium 30, hard 12. International careers are the official records; '
              'IPL and T20 World Cup careers come from ball-by-ball data.</p>')


def tools_markup(link):
    cards = [
        ('/studio/', 'STUDIO', 'Build a chart and export it', 'Pick players, measures and a breakdown, then export a PNG or SVG image.'),
        ('/matchups/', 'MATCHUPS', 'Batter v bowler', 'Every ball between two players, across Tests, ODIs, T20Is, the IPL and the T20 World Cup.'),
        ('/phases/', 'PHASES', 'Powerplay, middle, death', 'How innings are built, over by over, with phase leaders and grounds.'),
        ('/compare/', 'COMPARE', 'Two or three careers', 'Side by side by format, with the best figure marked in every row.'),
        ('/fantasy/', 'FANTASY', 'Projected XI', 'Form and ground records turned into a suggested team.'),
        ('/quiz/', 'QUIZ', 'Guess the player', 'Career numbers as clues, four choices, keep the streak.'),
    ]
    tiles = ''.join(f'<a class="feature-card tl-card" href="{u}"><p class="eyebrow">{e}</p><h2>{esc(t)}</h2><p>{esc(d)}</p></a>' for u, e, t, d in cards)
    return (mast('TOOLS', 'Cricket tools', 'Everything runs in your browser on the same ball-by-ball and career data as the rest of the site.')
            + f'<div class="tl-hub">{tiles}</div>')


# ------------------------------------------------------------------ quiz data

def _league_role(c):
    matches = c.get('matches') or 0
    runs, wickets = c.get('runs') or 0, c.get('wickets') or 0
    bats, bowls = runs >= 12 * matches, wickets >= 0.35 * matches
    if bats and bowls:
        return 'All-rounder'
    if bowls or runs < 6 * matches:
        return 'Bowler'
    return 'Batter'


ROLE = {'batter': 'Batter', 'bowler': 'Bowler', 'all-rounder': 'All-rounder', 'keeper': 'Wicketkeeper'}


def _r(v, d=2):
    return None if v is None else round(v, d)


def quiz_pools(root, routes, fullname):
    """{mode: [player clue rows]} from official careers and the league snapshots."""
    pools = {k: [] for k, _ in QUIZ_MODES}
    careers = json.loads((Path(root) / 'data/careers.json').read_text(encoding='utf-8'))['players']
    for p in careers:
        for fmt, mode in (('Test', 'test'), ('ODI', 'odi'), ('T20I', 't20i')):
            s = (p.get('formats') or {}).get(fmt)
            if not s or not s.get('matches'):
                continue
            if p.get('gender') == 'Women':
                mode = {'odi': 'wodi', 't20i': 'wt20i'}.get(mode)
                if not mode:
                    continue
            raw = s.get('span') or f"{p.get('first') or ''}-{p.get('last') or ''}"
            first = int(raw[:4]) if raw[:4].isdigit() else 0
            last = int(raw[-4:]) if raw[-4:].isdigit() else first
            span = str(first) if first == last else f'{first} to {last}'
            pools[mode].append({'id': p['id'], 'name': fullname(p), 'path': routes.get(p['id']), 'role': ROLE[format_role(s)],
                                'first': first, 'last': last, 'span': span, 'matches': s['matches'], 'runs': s.get('runs'), 'avg': s.get('avg'), 'sr': s.get('sr'),
                                'hs': s.get('highest_display'), 'hundreds': s.get('hundreds'), 'fifties': s.get('fifties'),
                                'wickets': s.get('wickets'), 'econ': s.get('econ'), 'best': s.get('best_bowling'), 'teams': ' / '.join(p.get('teams') or [])})
    for key in ('ipl', 't20wc'):
        path = Path(root) / 'data/leagues' / f'{key}.json'
        if not path.exists():
            continue
        for pid, p in json.loads(path.read_text(encoding='utf-8'))['players'].items():
            c = p['career']
            seasons = [s['edition'] for s in p.get('seasons') or []]
            if not c.get('matches') or not seasons:
                continue
            outs, balls, bowl_balls = c.get('outs') or 0, c.get('balls') or 0, c.get('bowl_balls') or 0
            pools[key].append({'id': pid, 'name': p['name'], 'path': routes.get(pid), 'role': _league_role(c),
                               'first': int(seasons[0]), 'last': int(seasons[-1]),
                               'span': seasons[0] if seasons[0] == seasons[-1] else f'{seasons[0]} to {seasons[-1]}',
                               'matches': c['matches'], 'runs': c.get('runs'), 'avg': _r(c['runs'] / outs) if outs else None,
                               'sr': _r(c['runs'] * 100 / balls) if balls else None,
                               'hs': (f"{c['hs']}{'*' if c.get('hs_not_out') else ''}" if c.get('innings') else None),
                               'hundreds': c.get('hundreds'), 'fifties': c.get('fifties'), 'wickets': c.get('wickets'),
                               'econ': _r(c['conceded'] * 6 / bowl_balls) if bowl_balls else None, 'best': c.get('best'),
                               'teams': ' / '.join(t['team'] for t in p.get('teams') or [])})
    for rows in pools.values():
        rows[:] = [r for r in rows if r['matches'] >= 12]
        rows.sort(key=lambda r: r['id'])
    return pools
