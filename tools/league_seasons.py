"""IPL season pages at the app's addresses, /ipl/seasons/<season>.

Built from the same Cricsheet cards as the IPL scorecards. Points: 2 for a
win (a tie settled by a super over counts as a win), 1 for no result. Net
run rate follows the standard rule: a side bowled out is charged its full
overs, and in a match with a revised target the side batting first is
credited with the target minus one from the revised overs. Playoffs are not
part of the table.
"""
from __future__ import annotations

from collections import defaultdict
from urllib.parse import quote

from league_matches import club, club_badge, esc

# League matches each side plays, by season (16 when nine sides met twice in 2012 and 2013).
LEAGUE_MATCHES = {'2012': 16, '2013': 16}
# Matches that do not count: Punjab Kings v Delhi Capitals at Dharamsala on 8 May 2025 was
# called off for security reasons and replayed in full.
VOID = {'1473495'}
NOT_BOWLER = {'run out', 'retired hurt', 'retired out', 'retired not out', 'obstructing the field', 'handled the ball', 'timed out'}


def season_path(season):
    return '/ipl/seasons/' + quote(season, safe='')


def year_of(cards):
    return min(c['match']['date'] for c in cards)[:4]


def winner_of(m):
    o = m['outcome']
    if o.get('winner'):
        return o['winner']
    if o.get('result') == 'tie' and o.get('eliminator'):
        return o['eliminator']
    return None


def table(cards, season=None):
    """League standings: points, then net run rate."""
    rows = defaultdict(lambda: {'p': 0, 'w': 0, 'l': 0, 'nr': 0, 'pts': 0, 'rf': 0, 'bf': 0, 'ra': 0, 'bb': 0})
    for card in cards:
        m = card['match']
        if m.get('stage') or m['id'] in VOID:
            continue
        teams = [club(t) for t in m['teams']]
        for t in teams:
            rows[t]['p'] += 1
        win = winner_of(m)
        if win:
            rows[club(win)]['w'] += 1
            rows[club(win)]['pts'] += 2
            rows[next(t for t in teams if t != club(win))]['l'] += 1
            innings = [i for i in card['innings'] if not i.get('super_over')]
            target = card.get('target') or {}
            for idx, inn in enumerate(innings[:2]):
                bat = club(inn['team'])
                bowl = next(t for t in teams if t != bat)
                runs, balls = inn['runs'], inn['balls']
                quota = (target.get('overs') or 20) * 6 if idx == 1 else 20 * 6
                if idx == 0 and target.get('overs') and target['overs'] < 20:
                    runs, balls = target['runs'] - 1, target['overs'] * 6
                elif inn['wickets'] >= 10:
                    balls = quota
                rows[bat]['rf'] += runs
                rows[bat]['bf'] += balls
                rows[bowl]['ra'] += runs
                rows[bowl]['bb'] += balls
        else:
            for t in teams:
                rows[t]['nr'] += 1
                rows[t]['pts'] += 1
    # Cricsheet has no record of matches abandoned without a ball. Every side plays the same number of
    # league matches, so a shortfall is that many no-results: one point each, no effect on net run rate.
    expected = LEAGUE_MATCHES.get(season, 14) if season else max((r['p'] for r in rows.values()), default=0)
    for r in rows.values():
        missing = expected - r['p']
        r['p'] += missing
        r['nr'] += missing
        r['pts'] += missing
    out = []
    for team, r in rows.items():
        nrr = (r['rf'] * 6 / r['bf'] if r['bf'] else 0) - (r['ra'] * 6 / r['bb'] if r['bb'] else 0)
        out.append({'team': team, **r, 'nrr': nrr})
    return sorted(out, key=lambda r: (-r['pts'], -r['nrr'], r['team']))


def leaders(cards, names, limit=10):
    bat, bowl = defaultdict(lambda: {'runs': 0, 'balls': 0, 'inns': 0, 'hs': 0, 'hs_out': True, 'sixes': 0}), defaultdict(lambda: {'wkts': 0, 'balls': 0, 'runs': 0, 'best': (0, 0)})
    for card in cards:
        for inn in card['innings']:
            if inn.get('super_over'):
                continue
            for b in inn['batting']:
                r = bat[b['id']]
                r['runs'] += b['runs']; r['balls'] += b['balls']; r['inns'] += 1; r['sixes'] += b['sixes']
                if b['runs'] > r['hs'] or (b['runs'] == r['hs'] and not b['out']):
                    r['hs'], r['hs_out'] = b['runs'], b['out']
                names.setdefault(b['id'], b['name'])
            for w in inn['bowling']:
                r = bowl[w['id']]
                r['wkts'] += w['wickets']; r['balls'] += w['balls']; r['runs'] += w['runs']
                if (w['wickets'], -w['runs']) > (r['best'][0], -r['best'][1]) or r['best'] == (0, 0):
                    r['best'] = (w['wickets'], w['runs'])
                names.setdefault(w['id'], w['name'])
    runs = sorted(bat.items(), key=lambda kv: (-kv[1]['runs'], kv[1]['balls']))[:limit]
    wkts = sorted(bowl.items(), key=lambda kv: (-kv[1]['wkts'], kv[1]['runs']))[:limit]
    sixes = sorted(bat.items(), key=lambda kv: -kv[1]['sixes'])[:1]
    return runs, wkts, sixes


def records(cards):
    best = {'total': None, 'low': None, 'score': None, 'bowling': None}
    for card in cards:
        m = card['match']
        for inn in card['innings']:
            if inn.get('super_over'):
                continue
            row = (inn, m)
            if not best['total'] or inn['runs'] > best['total'][0]['runs']:
                best['total'] = row
            if inn['wickets'] >= 10 or inn['balls'] >= 120:
                if not best['low'] or inn['runs'] < best['low'][0]['runs']:
                    best['low'] = row
            for b in inn['batting']:
                if not best['score'] or (b['runs'], -b['balls']) > (best['score'][0]['runs'], -best['score'][0]['balls']):
                    best['score'] = (b, m, inn['team'])
            for w in inn['bowling']:
                if not best['bowling'] or (w['wickets'], -w['runs']) > (best['bowling'][0]['wickets'], -best['bowling'][0]['runs']):
                    best['bowling'] = (w, m, next(t for t in m['teams'] if t != inn['team']))
    return best


def build(season, cards, lp, people_names, result_fn, pretty_date, a, prev_next):
    """(title, description, body, extra) for one IPL season."""
    cards = sorted(cards, key=lambda c: (c['match']['date'], c['match']['id']))
    year = year_of(cards)
    final = next((c for c in reversed(cards) if c['match'].get('stage') == 'Final'), None)
    champ = club(winner_of(final['match'])) if final and winner_of(final['match']) else None
    runner = next((club(t) for t in final['match']['teams'] if club(t) != champ), None) if champ else None
    names = dict(people_names)
    link = lambda pid, name: a(lp.get(pid) or '/ipl/players/' + quote(name, safe=''), names.get(pid) or name)  # noqa: E731
    mlink = lambda m, text: a('/ipl/matches/' + m['id'], text)  # noqa: E731
    team_link = lambda t: club_badge(club(t), '/ipl/teams/' + quote(club(t), safe=''))  # noqa: E731

    standings = table(cards, season)
    runs, wkts, sixes = leaders(cards, names)
    rec = records(cards)
    first, last = cards[0]['match']['date'], cards[-1]['match']['date']
    sub = f'{len(cards)} matches · {pretty_date(first)} to {pretty_date(last)}'
    body = (f'<section class="page-head"><div class="eyebrow">INDIAN PREMIER LEAGUE · SEASON</div><h1>IPL {year}</h1>'
            f'<p>{esc(sub)}</p></section>')
    if champ:
        body += (f'<section class="season-final"><span class="eyebrow">CHAMPIONS</span><div class="season-champ">{team_link(champ)}</div>'
                 f'<p>{mlink(final["match"], esc(result_fn(final["match"])))} in the final against {esc(runner)} at {esc(final["match"]["venue"])}, {esc(pretty_date(final["match"]["date"]))}.</p></section>')
    rows = ''.join(f'<tr{" class=is-playoff" if i < 4 else ""}><th scope="row">{i + 1}</th><td class=t>{team_link(r["team"])}</td><td>{r["p"]}</td><td>{r["w"]}</td><td>{r["l"]}</td>'
                   f'<td>{r["nr"]}</td><td><b>{r["pts"]}</b></td><td>{r["nrr"]:+.3f}</td></tr>' for i, r in enumerate(standings))
    body += ('<section class="panel" id="table"><h2>Points table</h2><div class="table-wrap" tabindex="0" role="region" aria-label="Points table">'
             '<table class="score-table season-table"><caption>League stage standings</caption><thead><tr><th scope="col">#</th><th scope="col" class=t>Team</th>'
             '<th scope="col" title="Played">P</th><th scope="col" title="Won">W</th><th scope="col" title="Lost">L</th><th scope="col" title="No result">NR</th>'
             f'<th scope="col" title="Points">Pts</th><th scope="col" title="Net run rate">NRR</th></tr></thead><tbody>{rows}</tbody></table></div>'
             '<p class="note">League matches only. Matches abandoned without a ball count as no result. Net run rate is worked out from the scorecards: a side bowled out is charged its full overs and shortened matches use the revised target. In a few rain-affected seasons it can differ slightly from the official figure.</p></section>')
    playoffs = [c for c in cards if c['match'].get('stage')]
    if playoffs:
        prow = ''.join(f'<tr><th scope="row">{esc(c["match"]["stage"])}</th><td class=t>{esc(pretty_date(c["match"]["date"]))}</td>'
                       f'<td class=t>{mlink(c["match"], esc(" v ".join(c["match"]["teams"])))}</td><td class=t>{esc(result_fn(c["match"]))}</td></tr>' for c in playoffs)
        body += ('<section class="panel" id="playoffs"><h2>Playoffs</h2><div class="table-wrap" tabindex="0" role="region" aria-label="Playoffs"><table class="score-table">'
                 f'<caption>Playoff results</caption><thead><tr><th scope="col">Stage</th><th scope="col" class=t>Date</th><th scope="col" class=t>Match</th><th scope="col" class=t>Result</th></tr></thead><tbody>{prow}</tbody></table></div></section>')
    bat_rows = ''.join(f'<tr><th scope="row">{link(pid, names.get(pid, pid))}</th><td>{r["inns"]}</td><td><b>{r["runs"]:,}</b></td><td>{r["hs"]}{"" if r["hs_out"] else "*"}</td>'
                       f'<td>{(r["runs"] * 100 / r["balls"]) if r["balls"] else 0:.2f}</td></tr>' for pid, r in runs)
    bowl_rows = ''.join(f'<tr><th scope="row">{link(pid, names.get(pid, pid))}</th><td><b>{r["wkts"]}</b></td><td>{(r["runs"] * 6 / r["balls"]) if r["balls"] else 0:.2f}</td>'
                        f'<td>{r["best"][0]}/{r["best"][1]}</td></tr>' for pid, r in wkts)
    body += ('<section class="panel" id="leaders"><h2>Leading players</h2><div class="grid two"><div class="table-wrap" tabindex="0" role="region" aria-label="Most runs"><table class="score-table">'
             f'<caption>Most runs</caption><thead><tr><th scope="col">Batter</th><th scope="col">Inns</th><th scope="col">Runs</th><th scope="col">HS</th><th scope="col">SR</th></tr></thead><tbody>{bat_rows}</tbody></table></div>'
             '<div class="table-wrap" tabindex="0" role="region" aria-label="Most wickets"><table class="score-table">'
             f'<caption>Most wickets</caption><thead><tr><th scope="col">Bowler</th><th scope="col">Wkts</th><th scope="col">Econ</th><th scope="col">Best</th></tr></thead><tbody>{bowl_rows}</tbody></table></div></div></section>')
    facts = []
    if rec['total']:
        inn, m = rec['total']
        facts.append(('Highest total', f'{inn["runs"]}/{inn["wickets"]}', f'{inn["team"]} v {next(t for t in m["teams"] if t != inn["team"])}', m))
    if rec['low']:
        inn, m = rec['low']
        facts.append(('Lowest completed total', f'{inn["runs"]}' + ('' if inn['wickets'] >= 10 else f'/{inn["wickets"]}'), f'{inn["team"]} v {next(t for t in m["teams"] if t != inn["team"])}', m))
    if rec['score']:
        b, m, team = rec['score']
        facts.append(('Highest score', f'{b["runs"]}{"" if b["out"] else "*"} ({b["balls"]})', f'{names.get(b["id"], b["name"])}, {team}', m))
    if rec['bowling']:
        w, m, team = rec['bowling']
        facts.append(('Best bowling', f'{w["wickets"]}/{w["runs"]}', f'{names.get(w["id"], w["name"])}, {team}', m))
    if sixes and sixes[0][1]['sixes']:
        pid, r = sixes[0]
        facts.append(('Most sixes', str(r['sixes']), names.get(pid, pid), None))
    body += ('<section class="panel" id="records"><h2>Season records</h2><div class="season-facts">'
             + ''.join(f'<div><span>{esc(k)}</span><strong>{esc(v)}</strong><small>{esc(who)}{(" · " + mlink(m, "scorecard")) if m else ""}</small></div>' for k, v, who, m in facts) + '</div></section>')
    mrows = ''.join(f'<tr><th scope="row">{esc(c["match"].get("match_number") or c["match"].get("stage") or "")}</th><td class=t>{esc(pretty_date(c["match"]["date"]))}</td>'
                    f'<td class=t>{mlink(c["match"], esc(" v ".join(c["match"]["teams"])))}</td><td class=t>{esc(result_fn(c["match"]))}</td><td class=t>{esc(c["match"]["venue"])}</td></tr>' for c in cards)
    body += ('<section class="panel" id="matches"><h2>Every match</h2><div class="table-wrap" tabindex="0" role="region" aria-label="All matches"><table class="score-table">'
             f'<caption>All IPL {year} matches</caption><thead><tr><th scope="col">No.</th><th scope="col" class=t>Date</th><th scope="col" class=t>Match</th><th scope="col" class=t>Result</th><th scope="col" class=t>Venue</th></tr></thead><tbody>{mrows}</tbody></table></div></section>')
    prev, nxt = prev_next
    body += ('<p class="pf-links">' + ' · '.join(x for x in ((a(season_path(prev[0]), '← IPL ' + prev[1]) if prev else ''), a('/ipl/seasons', 'All seasons'),
                                                        (a(season_path(nxt[0]), 'IPL ' + nxt[1] + ' →') if nxt else '')) if x) + '</p>')
    body += '<p class="note">From Cricsheet ball-by-ball data. Super overs are left out of player figures.</p>'
    title = f'IPL {year}: points table, results, top run-scorers and champions'
    lead = f'{champ} won IPL {year}, beating {runner} in the final. ' if champ else ''
    top = f'Top run-scorer {names.get(runs[0][0], runs[0][0])} ({runs[0][1]["runs"]:,}); most wickets {names.get(wkts[0][0], wkts[0][0])} ({wkts[0][1]["wkts"]}).' if runs and wkts else ''
    description = lead + f'Points table, playoffs, leading players and all {len(cards)} matches.'
    if len(description) + len(top) < 300:
        description += ' ' + top
    extra = {'breadcrumb_name': f'IPL {year}', 'about': {'@type': 'SportsEvent', 'name': f'Indian Premier League {year}', 'startDate': first, 'endDate': last}}
    return title, description, body, extra
