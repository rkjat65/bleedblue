"""IPL team pages at the app's addresses, /ipl/teams/<team>.

Built from the same Cricsheet cards and season tables as the scorecards and
season pages. Renamed franchises are one team, as on the app.
"""
from __future__ import annotations

from collections import defaultdict
from urllib.parse import quote

import league_seasons as ls
from league_matches import CLUBS, club, club_badge, esc

STAGE_RANK = {'Final': 4, 'Qualifier 2': 3, 'Semi Final': 3, 'Qualifier 1': 2, 'Eliminator': 2, 'Elimination Final': 2, '3rd Place Play-Off': 3}


def team_path(team):
    return '/ipl/teams/' + quote(club(team), safe='')


def season_finish(team, cards, standings):
    """League position and how far the team went, for one season."""
    pos = next((i + 1 for i, r in enumerate(standings) if r['team'] == team), None)
    final = next((c for c in cards if c['match'].get('stage') == 'Final'), None)
    if final and team in {club(t) for t in final['match']['teams']}:
        return pos, 'Champions' if club(ls.winner_of(final['match']) or '') == team else 'Runners-up'
    played = [c['match']['stage'] for c in cards if c['match'].get('stage') and team in {club(t) for t in c['match']['teams']}]
    return pos, ('Playoffs' if played else 'League stage')


def build_all(by_season, links, names, result_fn, pretty_date, a):
    """{team: (title, description, body, extra)} for every IPL franchise."""
    seasons = sorted(by_season, key=lambda s: ls.year_of(by_season[s]))
    tables = {s: ls.table(by_season[s], s) for s in seasons}
    all_cards = [c for s in seasons for c in sorted(by_season[s], key=lambda c: (c['match']['date'], c['match']['id']))]
    teams = sorted({club(t) for c in all_cards for t in c['match']['teams']})
    pages = {}
    for team in teams:
        mine = [c for c in all_cards if team in {club(t) for t in c['match']['teams']}]
        rows, titles, finals, playoffs = [], [], 0, 0
        for s in seasons:
            cards = by_season[s]
            if not any(team in {club(t) for t in c['match']['teams']} for c in cards):
                continue
            r = next((x for x in tables[s] if x['team'] == team), None)
            pos, finish = season_finish(team, cards, tables[s])
            year = ls.year_of(cards)
            titles += [year] if finish == 'Champions' else []
            finals += finish in ('Champions', 'Runners-up')
            playoffs += finish != 'League stage'
            rows.append((s, year, r, pos, finish))
        won = sum(1 for c in mine if club(ls.winner_of(c['match']) or '') == team)
        nr = sum(1 for c in mine if not ls.winner_of(c['match']))
        lost = len(mine) - won - nr
        h2h = defaultdict(lambda: [0, 0, 0])
        for c in mine:
            opp = next(club(t) for t in c['match']['teams'] if club(t) != team)
            w = ls.winner_of(c['match'])
            h2h[opp][0] += 1
            h2h[opp][1] += club(w or '') == team
            h2h[opp][2] += bool(w) and club(w) != team
        bat, bowl = defaultdict(lambda: [0, 0, 0]), defaultdict(lambda: [0, 0, 0])   # runs balls inns / wkts balls runs
        top_total = low_total = None
        for c in mine:
            for inn in c['innings']:
                if inn.get('super_over'):
                    continue
                if club(inn['team']) == team:
                    for b in inn['batting']:
                        x = bat[b['id']]; x[0] += b['runs']; x[1] += b['balls']; x[2] += 1
                        names.setdefault(b['id'], b['name'])
                    if not top_total or inn['runs'] > top_total[0]['runs']:
                        top_total = (inn, c['match'])
                    if (inn['wickets'] >= 10 or inn['balls'] >= 120) and (not low_total or inn['runs'] < low_total[0]['runs']):
                        low_total = (inn, c['match'])
                else:
                    for w in inn['bowling']:
                        x = bowl[w['id']]; x[0] += w['wickets']; x[1] += w['balls']; x[2] += w['runs']
                        names.setdefault(w['id'], w['name'])
        who = lambda pid: a(links.get(pid) or '/ipl/players/' + quote(names.get(pid, pid), safe=''), names.get(pid, pid))  # noqa: E731
        short, colour = CLUBS.get(team, ('', '#8888A0'))
        first, last = rows[0][1], rows[-1][1]
        sub = f'{len(rows)} seasons, {first} to {last} · {len(mine)} matches · {won} won, {lost} lost'
        title_line = f'{len(titles)} title{"s" if len(titles) != 1 else ""}: {", ".join(titles)}' if titles else 'No titles'
        body = (f'<section class="team-mast" style="--club:{colour}"><span class="club-mark club-mark-lg">{esc(short)}</span><div><div class="eyebrow">INDIAN PREMIER LEAGUE · TEAM</div>'
                f'<h1>{esc(team)}</h1><p>{esc(sub)}</p><p class="team-titles">{esc(title_line)}</p></div></section>')
        body += ('<div class="season-facts">' + ''.join(f'<div><span>{k}</span><strong>{v}</strong></div>' for k, v in (
            ('Titles', len(titles)), ('Finals', finals), ('Playoffs', playoffs), ('Win %', f'{won * 100 / max(1, won + lost):.1f}'), ('Matches', len(mine)))) + '</div>')
        srows = ''
        for s, year, r, pos, finish in reversed(rows):
            nrr = f'{r["nrr"]:+.3f}' if r else '-'
            srows += (f'<tr><th scope="row">{a(ls.season_path(s), year)}</th><td>{r["p"] if r else "-"}</td><td>{r["w"] if r else "-"}</td><td>{r["l"] if r else "-"}</td>'
                      f'<td>{r["pts"] if r else "-"}</td><td>{nrr}</td><td>{pos or "-"}</td><td class=t><span class="finish finish-{finish.split()[0].lower()}">{esc(finish)}</span></td></tr>')
        body += ('<section class="panel" id="seasons"><h2>Season by season</h2><div class="table-wrap" tabindex="0" role="region" aria-label="Season by season">'
                 '<table class="score-table season-table"><caption>League record and finish in each IPL season</caption><thead><tr><th scope="col">Season</th><th scope="col">P</th><th scope="col">W</th>'
                 f'<th scope="col">L</th><th scope="col">Pts</th><th scope="col" title="Net run rate">NRR</th><th scope="col" title="League position">Pos</th><th scope="col" class=t>Finish</th></tr></thead><tbody>{srows}</tbody></table></div></section>')
        hrows = ''.join(f'<tr><th scope="row">{club_badge(opp, team_path(opp))}</th><td>{p}</td><td>{w}</td><td>{l}</td><td>{w * 100 / max(1, w + l):.1f}</td></tr>'
                        for opp, (p, w, l) in sorted(h2h.items(), key=lambda kv: -kv[1][0]))
        body += ('<section class="panel" id="h2h"><h2>Head to head</h2><div class="table-wrap" tabindex="0" role="region" aria-label="Head to head">'
                 '<table class="score-table season-table"><caption>Results against each team, playoffs included</caption><thead><tr><th scope="col" class=t>Opponent</th><th scope="col">P</th>'
                 f'<th scope="col">W</th><th scope="col">L</th><th scope="col">Win %</th></tr></thead><tbody>{hrows}</tbody></table></div></section>')
        tb = sorted(bat.items(), key=lambda kv: -kv[1][0])[:10]
        tw = sorted(bowl.items(), key=lambda kv: (-kv[1][0], kv[1][2]))[:10]
        body += ('<section class="panel" id="players"><h2>Leading players for ' + esc(team) + '</h2><div class="grid two">'
                 '<div class="table-wrap" tabindex="0" role="region" aria-label="Most runs"><table class="score-table"><caption>Most runs</caption><thead><tr><th scope="col">Batter</th><th scope="col">Inns</th><th scope="col">Runs</th><th scope="col">SR</th></tr></thead><tbody>'
                 + ''.join(f'<tr><th scope="row">{who(pid)}</th><td>{x[2]}</td><td><b>{x[0]:,}</b></td><td>{x[0] * 100 / x[1] if x[1] else 0:.2f}</td></tr>' for pid, x in tb)
                 + '</tbody></table></div><div class="table-wrap" tabindex="0" role="region" aria-label="Most wickets"><table class="score-table"><caption>Most wickets</caption><thead><tr><th scope="col">Bowler</th><th scope="col">Wkts</th><th scope="col">Econ</th></tr></thead><tbody>'
                 + ''.join(f'<tr><th scope="row">{who(pid)}</th><td><b>{x[0]}</b></td><td>{x[2] * 6 / x[1] if x[1] else 0:.2f}</td></tr>' for pid, x in tw)
                 + '</tbody></table></div></div></section>')
        facts = []
        if top_total:
            inn, m = top_total
            facts.append(('Highest total', f'{inn["runs"]}/{inn["wickets"]}', f'v {next(t for t in m["teams"] if club(t) != team)}, {m["date"][:4]}', m))
        if low_total:
            inn, m = low_total
            facts.append(('Lowest completed total', str(inn['runs']) + ('' if inn['wickets'] >= 10 else f'/{inn["wickets"]}'), f'v {next(t for t in m["teams"] if club(t) != team)}, {m["date"][:4]}', m))
        if facts:
            body += ('<section class="panel" id="records"><h2>Team records</h2><div class="season-facts">'
                     + ''.join(f'<div><span>{esc(k)}</span><strong>{esc(v)}</strong><small>{esc(d)} · {a("/ipl/matches/" + m["id"], "scorecard")}</small></div>' for k, v, d, m in facts) + '</div></section>')
        recent = list(reversed(mine))[:10]
        rrows = ''.join(f'<tr><th scope="row">{esc(pretty_date(c["match"]["date"]))}</th><td class=t>{a("/ipl/matches/" + c["match"]["id"], esc(" v ".join(c["match"]["teams"])))}</td><td class=t>{esc(result_fn(c["match"]))}</td></tr>' for c in recent)
        body += ('<section class="panel" id="recent"><h2>Latest matches</h2><div class="table-wrap" tabindex="0" role="region" aria-label="Latest matches"><table class="score-table">'
                 f'<caption>Latest {esc(team)} matches</caption><thead><tr><th scope="col">Date</th><th scope="col" class=t>Match</th><th scope="col" class=t>Result</th></tr></thead><tbody>{rrows}</tbody></table></div></section>')
        body += '<p class="note">From Cricsheet ball-by-ball data. Renamed franchises are counted as one team. Matches abandoned without a ball are not listed.</p>'
        title = f'{team} IPL record: titles, every season, head to head and top players'
        description = (f'{team} in the IPL: no titles, {len(rows)} seasons and {len(mine)} matches ({won} won). '
                       'Finish in every season, head to head and leading run-scorers and wicket-takers.')
        if titles:
            description = f'{team} in the IPL: {len(titles)} title{"s" if len(titles) != 1 else ""} ({", ".join(titles)}), {len(rows)} seasons and {len(mine)} matches ({won} won). Every season, head to head and top players.'
        pages[team] = (title, description, body, {'breadcrumb_name': team, 'about': {'@type': 'SportsTeam', 'name': team, 'sport': 'Cricket'}})
    return pages
