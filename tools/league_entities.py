"""IPL tabs on ground pages and T20 World Cup tabs on team pages.

Both come from the analytics app's ball-by-ball exports in data/leagues/.
IPL grounds are matched to archive grounds through the archive's own venue
canonicaliser, applied to every name the app recorded for that ground.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

from entity_formats import hero
from profile_formats import esc, lean_table, n, r2, rate
from venues import canonical_venue


def load(root, name):
    path = Path(root) / 'data' / 'leagues' / name
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def ground_index(venues, grounds):
    """{archive ground name: app venue record} for IPL venues with an archive page."""
    claims = defaultdict(list)
    for venue in (venues.get('venues') or {}).values():
        # Newest name first: a renamed ground that the archive still splits goes to its current page.
        aliases = sorted(venue.get('aliases') or [], key=lambda a: a.get('last', ''), reverse=True)
        names = [canonical_venue(a['name'], a.get('first', ''), 'T20') for a in aliases] + [canonical_venue(venue['name'], '', 'T20')]
        hits = [g for g in names if g in grounds]
        if hits:
            claims[hits[0]].append(venue)
    # Two app venues on one ground would need merging; keep the larger and leave the other out.
    return {ground: max(found, key=lambda v: v['matches']) for ground, found in claims.items()}


def _player(row, pp):
    path = pp.get(row.get('id')) if row.get('id') else None
    return f'<a href="{esc(path)}">{esc(row["player"])}</a>' if path else esc(row['player'])


def _total(t):
    if not t:
        return '-'
    wickets = '' if t['wickets'] >= 10 else f'/{t["wickets"]}'
    return f'{t["runs"]}{wickets}'


def _overs(balls):
    return f'{balls // 6}.{balls % 6}' if balls else '-'


def records_table(caption, data, pp):
    body = []
    for label, t in (('Highest total', data.get('highest_total')), ('Lowest completed total', data.get('lowest_total'))):
        if t:
            body.append([label, esc(_total(t)), esc(t['team']), esc(t['opponent']), esc(t['edition'])])
    b = data.get('best_innings')
    if b:
        body.append(['Highest score', esc(f'{b["runs"]} ({b["balls"]})'), _player(b, pp) + f' <small>{esc(b["team"])}</small>', esc(b['opponent']), esc(b['edition'])])
    w = data.get('best_bowling')
    if w:
        body.append(['Best bowling', esc(f'{w["wickets"]}/{w["conceded"]}'), _player(w, pp) + f' <small>{esc(w["team"])}</small>', esc(w['opponent']), esc(w['edition'])])
    return lean_table(caption, ['Record', 'Figure', ('By', 'Team or player'), ('Against', 'Opponent'), 'Season'], body, left=(2, 3))


def leaders_tables(label, data, pp):
    bat = [[_player(r, pp), n(r['innings']), n(r['runs']), r2(rate(r['runs'], r['balls'], 100), r['balls'])] for r in data.get('top_batters') or []]
    bowl = [[_player(r, pp), n(r['innings']), n(r['wickets']), r2(rate(r['conceded'], r['balls'], 6), r['balls'])] for r in data.get('top_bowlers') or []]
    return (lean_table(f'Most {label} runs', ['Batter', ('Inns', 'Innings'), 'Runs', ('SR', 'Strike rate')], bat)
            + lean_table(f'Most {label} wickets', ['Bowler', ('Inns', 'Innings'), ('Wkts', 'Wickets'), ('Econ', 'Runs conceded per over')], bowl))


def pct(part, whole):
    return r2(rate(part, whole, 100), whole)


def ground_panel(ground, venue, meta, pp):
    seasons = venue.get('seasons') or []
    span = seasons[0]['edition'] if len(seasons) == 1 else f"{seasons[0]['edition']} to {seasons[-1]['edition']}" if seasons else ''
    decided = venue.get('decided') or 0
    tosses = (venue.get('toss_bat') or 0) + (venue.get('toss_field') or 0)
    body = '<section class="fmt-panel fmt-ipl" id="ipl" data-fmt-panel="ipl" aria-label="IPL at this ground">'
    body += (f'<header class="pf-fmt-head"><div><p class="eyebrow">IPL{(" · " + esc(span)) if span else ""}</p>'
             f'<h2>IPL at {esc(ground)}</h2></div>'
             '<p class="pf-cov is-complete" title="Every IPL match here has ball-by-ball data">Ball by ball, every match</p></header>')
    body += hero([('Matches', n(venue['matches'])), ('1st innings avg', esc(f'{venue["avg_first"]:.1f}') if venue.get('avg_first') is not None else '-'),
                  ('Won batting first', pct(venue['bat_first_won'], decided)), ('Won chasing', pct(venue['chase_won'], decided)),
                  ('Highest total', esc(_total(venue.get('highest_total')))), ('Toss: chose field', pct(venue['toss_field'], tosses))], f'IPL at {ground}')
    results = lean_table(f'How IPL matches at {ground} were decided', ['Result', 'Matches', ('%', 'Share of matches with a result')],
                         [['Won batting first', n(venue['bat_first_won']), pct(venue['bat_first_won'], decided)],
                          ['Won chasing', n(venue['chase_won']), pct(venue['chase_won'], decided)],
                          ['Tied', n(venue['tied']), '-'], ['No result', n(venue['no_result']), '-']])
    toss = lean_table(f'IPL toss at {ground}', ['Toss', 'Matches', ('%', 'Share')],
                      [['Chose to field', n(venue['toss_field']), pct(venue['toss_field'], tosses)],
                       ['Chose to bat', n(venue['toss_bat']), pct(venue['toss_bat'], tosses)],
                       ['Toss winner won the match', n(venue['toss_winner_won']), pct(venue['toss_winner_won'], decided)]])
    body += f'<section class="panel pf-block"><h2>How IPL matches here are won</h2>{results}{toss}</section>'
    body += f'<section class="panel pf-block"><h2>IPL records at {esc(ground)}</h2>{records_table(f"IPL records at {ground}", venue, pp)}</section>'
    body += f'<section class="panel pf-block"><h2>Leading IPL players here</h2>{leaders_tables("IPL", venue, pp)}</section>'
    if len(seasons) > 1:
        body += ('<section class="panel pf-block"><h2>IPL matches by season</h2>'
                 + lean_table(f'IPL matches at {ground} by season', ['Season', 'Matches'], [[esc(s['edition']), n(s['matches'])] for s in reversed(seasons)])
                 + '</section>')
    body += (f'<section class="panel pf-block lg-deep"><h2>Ball-by-ball IPL analysis</h2>'
             f'<p>Phase scoring, toss trends and every IPL match at {esc(ground)}.</p>'
             f'<p><a class="button primary" href="/ipl/venues/{quote(venue["name"], safe="")}">Open IPL venue analysis</a></p>'
             f'<p class="pf-fine">Source: Cricsheet ball-by-ball data to {esc(meta.get("last", ""))}. Averages use every first innings, including shortened matches. '
             'Lowest totals count completed innings only: all out or the full 20 overs.</p></section>')
    body += '</section>'
    return body


def team_panel(team, data, meta, pp):
    editions = data.get('editions') or []
    span = editions[0]['edition'] if len(editions) == 1 else f"{editions[0]['edition']} to {editions[-1]['edition']}" if editions else ''
    titles = data.get('titles') or []
    pill = (f'{len(titles)} title{"s" if len(titles) != 1 else ""}: {", ".join(titles)}' if titles else 'Ball by ball, every match')
    body = '<section class="fmt-panel fmt-t20wc" id="t20wc" data-fmt-panel="t20wc" aria-label="Men\'s T20 World Cup record">'
    body += (f'<header class="pf-fmt-head"><div><p class="eyebrow">MEN\'S T20 WORLD CUP{(" · " + esc(span)) if span else ""}</p>'
             f'<h2>{esc(team)} at the T20 World Cup</h2></div><p class="pf-cov is-complete">{esc(pill)}</p></header>')
    body += hero([('Played', n(data['matches'])), ('Won', n(data['won'])), ('Lost', n(data['lost'])), ('Tied', n(data['tied'])),
                  ('No result', n(data['no_result'])), ('Win %', pct(data['won'], data['matches']))], f"{team} T20 World Cup record")
    rows = [[esc(e['edition']), n(e['played']), n(e['won']), n(e['lost']), esc(e['finish'] or '-')] for e in reversed(editions)]
    body += ('<section class="panel pf-block"><h2>T20 World Cup by edition</h2>'
             + lean_table(f'{team} at each T20 World Cup', ['Edition', ('P', 'Played'), ('W', 'Won'), ('L', 'Lost'), 'Finish'], rows,
                          foot=['All', n(data['matches']), n(data['won']), n(data['lost']), esc(f'{len(titles)} titles' if len(titles) != 1 else '1 title')], left=(4,))
             + '</section>')
    opp = [[esc(o['team']), n(o['played']), n(o['won']), n(o['lost']), pct(o['won'], o['played'])] for o in data.get('opponents') or []]
    body += ('<section class="panel pf-block"><h2>T20 World Cup results by opponent</h2>'
             + lean_table(f'{team} T20 World Cup results by opponent', ['Opponent', ('P', 'Played'), ('W', 'Won'), ('L', 'Lost'), ('Win %', 'Wins as a share of matches played')], opp)
             + '</section>')
    body += f'<section class="panel pf-block"><h2>T20 World Cup team records</h2>{records_table(f"{team} T20 World Cup records", data, pp)}</section>'
    body += f'<section class="panel pf-block"><h2>Leading T20 World Cup players</h2>{leaders_tables("T20 World Cup", data, pp)}</section>'
    body += (f'<section class="panel pf-block lg-deep"><h2>Ball-by-ball T20 World Cup analysis</h2>'
             f'<p>Phase splits, matchups and every {esc(team)} T20 World Cup match.</p>'
             f'<p><a class="button primary" href="/t20-world-cup/teams/{quote(team, safe="")}">Open T20 World Cup analysis</a> '
             '<a class="button" href="/world-cup/">World Cup archive</a></p>'
             f'<p class="pf-fine">Source: Cricsheet ball-by-ball data to {esc(meta.get("last", ""))}. Matches abandoned without a ball are not counted. '
             'Tied includes matches settled by a super over or bowl-out. These matches are T20Is, so they are also in the T20I tab.</p></section>')
    body += '</section>'
    return body


def switch_item(key, label, count):
    return f'<a href="#{key}" data-fmt="{key}" class="fmt-{key}">{esc(label)}<small>{count:,}</small></a>'
