"""Format-first team, ground and series pages.

Every section is computed from the published match records and their
scorecards for one format at a time. Men and women stay separate. Unknown
inputs are left out of averages rather than counted as zero.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from profile_formats import FORMATS, KEYS, esc, lean_table, n, r2, rate

GENDERS = ('Men', 'Women')
ORDINAL = {1: '1st', 2: '2nd', 3: '3rd', 4: '4th'}


# ------------------------------------------------------------------ results

def outcome_for(m, team):
    o = m.get('outcome') or {}
    if o.get('winner') == team:
        return 'Won'
    if o.get('winner'):
        return 'Lost'
    return {'draw': 'Drawn', 'tie': 'Tied'}.get(o.get('result'), 'No result')


def record(matches, team):
    counts = Counter(outcome_for(m, team) for m in matches)
    played = len(matches)
    won = counts['Won']
    rec = {'played': played, 'won': won, 'lost': counts['Lost'], 'drawn': counts['Drawn'], 'tied': counts['Tied'], 'nr': counts['No result']}
    rec['win_pct'] = rate(won * 100, played) if played else None
    rec['last'] = max((m['date'] for m in matches), default='')
    recent = sorted(matches, key=lambda m: (m['date'], m['id']))[-5:]
    rec['form'] = [outcome_for(m, team) for m in recent]
    return rec


def form_chips(form):
    marks = {'Won': 'W', 'Lost': 'L', 'Drawn': 'D', 'Tied': 'T', 'No result': 'N'}
    return '<span class="pf-formguide" aria-label="Last five results, oldest first">' + ''.join(f'<i class="f-{marks[x].lower()}" title="{esc(x)}">{marks[x]}</i>' for x in form) + '</span>'


def record_cells(label, rec, with_last=True):
    cells = [label, n(rec['played']), n(rec['won']), n(rec['lost']), n(rec['drawn'] + rec['tied']), n(rec['nr']), r2(rec['win_pct'], rec['played'])]
    if with_last:
        cells.append(esc(rec['last'][:4]) if rec['last'] else '-')
    return cells


RECORD_HEAD = [('P', 'Played'), ('W', 'Won'), ('L', 'Lost'), ('D/T', 'Drawn or tied'), ('NR', 'No result'), ('Win %', 'Wins as a share of matches played')]


def results_table(caption, groups, team, first='', with_last=True):
    body = [record_cells(label, record(ms, team), with_last) for label, ms in groups if ms]
    if not body:
        return ''
    all_ms = [m for _, ms in groups for m in ms]
    head = [first] + RECORD_HEAD + ([('Last', 'Most recent match')] if with_last else [])
    return lean_table(caption, head, body, record_cells('All', record(all_ms, team), with_last), css='pf-results')


def group_matches(matches, keyfn, order=None, sort_by_size=False, minimum=1, limit=None):
    buckets = defaultdict(list)
    for m in matches:
        key = keyfn(m)
        if key:
            buckets[key].append(m)
    items = [(k, v) for k, v in buckets.items() if len(v) >= minimum]
    if order:
        items.sort(key=lambda kv: (order.index(kv[0]) if kv[0] in order else len(order), str(kv[0])))
    elif sort_by_size:
        items.sort(key=lambda kv: (-len(kv[1]), str(kv[0])))
    else:
        items.sort(key=lambda kv: kv[0])
    return items[:limit] if limit else items


def batted_first(card, team):
    innings = [inn for inn in (card or {}).get('innings') or [] if not inn.get('super_over')]
    if not innings:
        return None
    return innings[0].get('team') == team


def hero(cells, aria):
    tiles = ''.join(f'<div{" class=lead" if i == 0 else ""}><strong>{value}</strong><span>{esc(label)}</span></div>' for i, (label, value) in enumerate(cells))
    return f'<div class="pf-hero" aria-label="{esc(aria)}">{tiles}</div>'


# ------------------------------------------------------------------ totals

def innings_list(matches, cards, team=None):
    """(match, index, innings total) for every recorded regulation innings."""
    out = []
    for m in matches:
        totals = [t for t in (m.get('totals') or []) if not t.get('super_over') and t.get('runs') is not None]
        if not totals:
            card = cards.get(m['id']) or {}
            totals = [{'team': inn.get('team'), 'runs': inn.get('runs'), 'wickets': inn.get('wickets'), 'balls': inn.get('balls'), 'declared': inn.get('declared')} for inn in card.get('innings') or [] if not inn.get('super_over') and inn.get('runs') is not None]
        for index, t in enumerate(totals, 1):
            if team and t.get('team') != team:
                continue
            out.append((m, index, t))
    return out


def total_row(m, t, mp, team_col=True, extra=None):
    opp = next((x for x in m['teams'] if x != t.get('team')), '')
    score = f"{t['runs']}{'/' + str(t['wickets']) if t.get('wickets') is not None and t['wickets'] < 10 else ''}{'d' if t.get('declared') else ''}"
    cells = [f'<a href="{esc(mp[m["id"]])}">{score}</a>']
    if team_col:
        cells.append(esc(t.get('team') or ''))
    cells += [esc(opp), esc(m.get('venue') or ''), esc(m['date'])]
    if extra is not None:
        cells.insert(1, extra)
    return cells


def totals_tables(matches, cards, mp, team=None, fmt='', limit=5):
    rows = innings_list(matches, cards, team)
    out = ''
    who = 'Opponent' if team else 'Opponent'
    if rows:
        highest = sorted(rows, key=lambda x: -x[2]['runs'])[:limit]
        head = ['Total'] + ([] if team else ['Team']) + [who, 'Ground', 'Date']
        out += lean_table(f'Highest {fmt} totals', head, [total_row(m, t, mp, team_col=not team) for m, _, t in highest], css='pf-best', left=tuple(range(1, len(head))))
        all_out = [x for x in rows if x[2].get('wickets') == 10]
        if len(all_out) >= 3:
            lowest = sorted(all_out, key=lambda x: x[2]['runs'])[:limit]
            out += lean_table(f'Lowest all-out {fmt} totals', head, [total_row(m, t, mp, team_col=not team) for m, _, t in lowest], css='pf-best', left=tuple(range(1, len(head))))
    chases = []
    for m, index, t in rows:
        winner = (m.get('outcome') or {}).get('winner')
        if winner != t.get('team'):
            continue
        last = 2 if fmt != 'Test' else 4
        if index == last:
            chases.append((m, t))
    if chases:
        head = ['Chase'] + ([] if team else ['Team']) + [who, 'Ground', 'Date']
        out += lean_table(f'Highest successful {fmt} chases', head, [total_row(m, t, mp, team_col=not team) for m, t in sorted(chases, key=lambda x: -x[1]['runs'])[:limit]], css='pf-best', left=tuple(range(1, len(head))))
    return out


def margin_tables(matches, mp, team, fmt, limit=5):
    by_runs, by_wickets, by_innings = [], [], []
    for m in matches:
        o = m.get('outcome') or {}
        if o.get('winner') != team:
            continue
        by = o.get('by') or {}
        opp = next((x for x in m['teams'] if x != team), '')
        if by.get('innings'):
            by_innings.append((by.get('runs') or 0, m, opp))
        elif by.get('runs'):
            by_runs.append((by['runs'], m, opp))
        elif by.get('wickets'):
            by_wickets.append((by['wickets'], m, opp))
    out = ''
    if by_runs:
        out += lean_table(f'Biggest {fmt} wins by runs', ['Margin', 'Opponent', 'Ground', 'Date'], [[f'<a href="{esc(mp[m["id"]])}">{r} runs</a>', esc(opp), esc(m.get('venue') or ''), esc(m['date'])] for r, m, opp in sorted(by_runs, key=lambda x: -x[0])[:limit]], css='pf-best', left=(1, 2, 3))
    if by_innings:
        out += lean_table(f'{fmt} wins by an innings', ['Margin', 'Opponent', 'Ground', 'Date'], [[f'<a href="{esc(mp[m["id"]])}">an innings and {r} runs</a>', esc(opp), esc(m.get('venue') or ''), esc(m['date'])] for r, m, opp in sorted(by_innings, key=lambda x: -x[0])[:limit]], css='pf-best', left=(1, 2, 3))
    if by_wickets:
        out += lean_table(f'Biggest {fmt} wins by wickets', ['Margin', 'Opponent', 'Ground', 'Date'], [[f'<a href="{esc(mp[m["id"]])}">{w} wickets</a>', esc(opp), esc(m.get('venue') or ''), esc(m['date'])] for w, m, opp in sorted(by_wickets, key=lambda x: (-x[0], x[1]['date']))[:limit]], css='pf-best', left=(1, 2, 3))
    return out


# ------------------------------------------------------------------ leaders

def leaders(matches, cards, people, pp, mp, team=None, fmt='', limit=10, show_team=False):
    bat = defaultdict(lambda: {'inns': 0, 'runs': 0, 'balls': 0, 'outs': 0, 'known_out': True, 'known_balls': True, 'hs': None, 'hs_no': False, 'hundreds': 0, 'fifties': 0, 'team': None, 'matches': set()})
    bowl = defaultdict(lambda: {'inns': 0, 'wickets': 0, 'conceded': 0, 'balls': 0, 'known': True, 'known_balls': True, 'best': None, 'five': 0, 'team': None, 'matches': set()})
    apps = Counter()
    scores, spells = [], []
    for m in matches:
        card = cards.get(m['id'])
        if not card:
            continue
        for squad_team, squad in (card.get('players') or {}).items():
            if team and squad_team != team:
                continue
            for p in squad:
                if p.get('id'):
                    apps[p['id']] += 1
        for inn in card.get('innings') or []:
            if inn.get('super_over'):
                continue
            bat_team = inn.get('team')
            bowl_team = next((x for x in m['teams'] if x != bat_team), '')
            if not team or bat_team == team:
                for b in inn.get('batting') or []:
                    pid = b.get('id')
                    if not pid:
                        continue
                    row = bat[pid]
                    row['inns'] += 1
                    row['team'] = bat_team
                    row['matches'].add(m['id'])
                    if b.get('runs') is None:
                        row['known_out'] = False
                        continue
                    row['runs'] += b['runs']
                    if b.get('out') is None:
                        row['known_out'] = False
                    elif b['out']:
                        row['outs'] += 1
                    if b.get('balls') is None:
                        row['known_balls'] = False
                    else:
                        row['balls'] += b['balls']
                    if row['hs'] is None or b['runs'] > row['hs'] or (b['runs'] == row['hs'] and b.get('out') is False):
                        row['hs'] = b['runs']
                        row['hs_no'] = b.get('out') is False
                    row['hundreds'] += b['runs'] >= 100
                    row['fifties'] += 50 <= b['runs'] < 100
                    scores.append((b['runs'], b.get('out') is False, b.get('balls'), pid, bat_team, m))
            if not team or bowl_team == team:
                for b in inn.get('bowling') or []:
                    pid = b.get('id')
                    if not pid:
                        continue
                    row = bowl[pid]
                    row['inns'] += 1
                    row['team'] = bowl_team
                    row['matches'].add(m['id'])
                    if b.get('wickets') is None or b.get('runs') is None:
                        row['known'] = False
                        continue
                    row['wickets'] += b['wickets']
                    row['conceded'] += b['runs']
                    if b.get('balls') is None:
                        row['known_balls'] = False
                    else:
                        row['balls'] += b['balls']
                    if row['best'] is None or (b['wickets'], -b['runs']) > (row['best'][0], -row['best'][1]):
                        row['best'] = (b['wickets'], b['runs'])
                    row['five'] += b['wickets'] >= 5
                    spells.append((b['wickets'], b['runs'], b.get('balls'), pid, bowl_team, m))
    out = ''
    name = lambda pid: people.get(pid, {}).get('name') or pid
    link = lambda pid: f'<a href="{esc(pp[pid])}">{esc(name(pid))}</a>' if pid in pp else esc(name(pid))
    team_col = ['Team'] if show_team else []
    left = (1,) if show_team else ()
    run_rows = sorted(((pid, r) for pid, r in bat.items() if r['runs'] and pid in people), key=lambda kv: (-kv[1]['runs'], kv[0]))[:limit]
    if run_rows:
        body = []
        for pid, r in run_rows:
            avg = rate(r['runs'], r['outs']) if r['known_out'] and r['outs'] else None
            sr = rate(r['runs'], r['balls'], 100) if r['known_balls'] and r['balls'] else None
            body.append([link(pid)] + ([esc(r['team'])] if show_team else []) + [n(len(r['matches'])), n(r['inns']), n(r['runs']), f"{r['hs']}{'*' if r['hs_no'] else ''}" if r['hs'] is not None else '-', r2(avg, r['outs'] if r['known_out'] else None), r2(sr, r['balls'] if r['known_balls'] else None), n(r['hundreds']), n(r['fifties'])])
        out += lean_table(f'Most {fmt} runs', ['Batter'] + team_col + [('Mat', 'Matches'), ('Inns', 'Innings'), 'Runs', ('HS', 'Highest score'), ('Avg', 'Average'), ('SR', 'Strike rate'), '100', '50'], body, css='pf-bat pf-leaders', left=left)
    wkt_rows = sorted(((pid, r) for pid, r in bowl.items() if r['wickets'] and pid in people), key=lambda kv: (-kv[1]['wickets'], kv[1]['conceded'], kv[0]))[:limit]
    if wkt_rows:
        body = []
        for pid, r in wkt_rows:
            avg = rate(r['conceded'], r['wickets']) if r['known'] else None
            econ = rate(r['conceded'], r['balls'], 6) if r['known_balls'] and r['balls'] else None
            sr = rate(r['balls'], r['wickets']) if r['known_balls'] and r['balls'] else None
            body.append([link(pid)] + ([esc(r['team'])] if show_team else []) + [n(len(r['matches'])), n(r['inns']), n(r['wickets']), f"{r['best'][0]}/{r['best'][1]}" if r['best'] else '-', r2(avg, r['wickets']), r2(econ, r['balls'] if r['known_balls'] else None), r2(sr, r['wickets']), n(r['five'])])
        out += lean_table(f'Most {fmt} wickets', ['Bowler'] + team_col + [('Mat', 'Matches'), ('Inns', 'Innings'), ('Wkts', 'Wickets'), ('BBI', 'Best bowling in an innings'), ('Avg', 'Average'), ('Econ', 'Economy'), ('SR', 'Strike rate'), '5w'], body, css='pf-bowl-leaders pf-leaders', left=left)
    if len(scores) >= 3:
        top = sorted(scores, key=lambda s: (-s[0], not s[1], s[5]['date']))[:5]
        body = [[f'<a href="{esc(mp[m["id"]])}">{runs}{"*" if no else ""}</a>', link(pid)] + ([esc(t)] if show_team else []) + [n(balls), esc(next((x for x in m['teams'] if x != t), '')), esc(m.get('venue') or ''), esc(m['date'])] for runs, no, balls, pid, t, m in top]
        out += lean_table(f'Highest individual {fmt} scores', ['Score', 'Batter'] + team_col + [('BF', 'Balls faced'), 'Opponent', 'Ground', 'Date'], body, css='pf-best', left=tuple(range(1, 6 + len(team_col))))
    if len(spells) >= 3 and any(s[0] for s in spells):
        top = sorted(spells, key=lambda s: (-s[0], s[1], s[5]['date']))[:5]
        body = [[f'<a href="{esc(mp[m["id"]])}">{w}/{c}</a>', link(pid)] + ([esc(t)] if show_team else []) + [n(balls), esc(next((x for x in m['teams'] if x != t), '')), esc(m.get('venue') or ''), esc(m['date'])] for w, c, balls, pid, t, m in top]
        out += lean_table(f'Best {fmt} bowling figures', ['Figures', 'Bowler'] + team_col + [('Balls', 'Balls bowled'), 'Opponent', 'Ground', 'Date'], body, css='pf-best', left=tuple(range(1, 6 + len(team_col))))
    if team and apps:
        most = [(pid, c) for pid, c in apps.most_common(limit) if pid in people]
        out += lean_table(f'Most {fmt} appearances', ['Player', ('Mat', 'Matches')], [[link(pid), n(c)] for pid, c in most], css='pf-leaders pf-apps')
    return out


# ------------------------------------------------------------------ teams

def toss_table(matches, cards, team, fmt):
    won_toss, lost_toss, bat_first, chased, chose_bat, chose_field = [], [], [], [], [], []
    for m in matches:
        card = cards.get(m['id'])
        if not card:
            continue
        toss = card.get('toss') or {}
        if toss.get('winner') == team:
            won_toss.append(m)
            (chose_bat if toss.get('decision') == 'bat' else chose_field).append(m)
        elif toss.get('winner'):
            lost_toss.append(m)
        first = batted_first(card, team)
        if first is True:
            bat_first.append(m)
        elif first is False:
            chased.append(m)
    groups = [('Won the toss', won_toss), ('Lost the toss', lost_toss), ('Chose to bat', chose_bat), ('Chose to field', chose_field),
              ('Batted first', bat_first), ('Batted second' if fmt == 'Test' else 'Chased', chased)]
    if not any(ms for _, ms in groups):
        return ''
    return results_table(f'{fmt} record by toss and batting order', groups, team, first='Situation', with_last=False)


def team_format_panel(name, fmt, matches, cards, people, pp, mp, h2h_path, official=None):
    """`official` maps format to the men's official results line; the headline uses it so it matches
    the overview table, and the splits below say they come from the recorded matches."""
    key = KEYS[fmt]
    body = f'<section class="fmt-panel fmt-{key}" id="{key}" data-fmt-panel="{key}" aria-label="{esc(name)} {esc(fmt)} record">'
    for gender in GENDERS:
        ms = [m for m in matches if m.get('gender') == gender]
        if not ms:
            continue
        rec = record(ms, name)
        span = f"{min(m['date'] for m in ms)[:4]} to {max(m['date'] for m in ms)[:4]}"
        body += (f'<header class="pf-fmt-head"><div><p class="eyebrow">{esc(gender.upper())} · {esc(fmt.upper())} · {esc(span)}</p>'
                 f'<h2>{esc(name)} {esc(gender.lower())} in {esc(fmt)}s</h2></div>{form_chips(rec["form"])}</header>')
        line = (official or {}).get(fmt) if gender == 'Men' else None
        if line and line.get('played'):
            drawn = (line.get('draw') or 0) + (line.get('tied') or 0)
            body += hero([('Played', n(line['played'])), ('Won', n(line['won'])), ('Lost', n(line['lost'])), ('Drawn / tied', n(drawn)), ('No result', n(line.get('nr') or 0)), ('Win %', f"{100 * line['won'] / line['played']:.2f}")], f'{name} {gender} {fmt} official results')
            if line['played'] != rec['played']:
                body += f'<p class="pf-fine">Official results above. The tables below use the {rec["played"]:,} {esc(fmt)}s in these scorecards and results, which can include matches the official count leaves out, such as ones abandoned without a ball bowled.</p>'
        else:
            body += hero([('Played', n(rec['played'])), ('Won', n(rec['won'])), ('Lost', n(rec['lost'])), ('Drawn / tied', n(rec['drawn'] + rec['tied'])), ('No result', n(rec['nr'])), ('Win %', r2(rec['win_pct'], rec['played']))], f'{name} {gender} {fmt} record')
        opp = group_matches(ms, lambda m: next((x for x in m['teams'] if x != name), ''), sort_by_size=True)
        opp_rows = [(f'<a href="{esc(h2h_path(name, o))}">{esc(o)}</a>', group) for o, group in opp]
        body += f'<section class="panel pf-block"><h2>{esc(gender)} {esc(fmt)} results by opponent</h2>{results_table(f"{name} {gender} {fmt} results by opponent", opp_rows, name, first="Opponent")}</section>'
        setting = group_matches(ms, lambda m: m.get('setting') or 'Unknown', order=['Home', 'Away', 'Neutral', 'Unknown'])
        toss = toss_table(ms, cards, name, fmt)
        situ = results_table(f'{name} {gender} {fmt} results home and away', [(esc(k), v) for k, v in setting], name, first='Setting') + toss
        if situ:
            body += f'<section class="panel pf-block"><h2>{esc(gender)} {esc(fmt)} results by situation</h2>{situ}</section>'
        years = group_matches(ms, lambda m: m['date'][:4])
        decades = group_matches(ms, lambda m: m['date'][:3] + '0s')
        if len(years) > 1:
            body += f'<section class="panel pf-block"><h2>{esc(gender)} {esc(fmt)} results by year</h2>'
            if len(years) > 12:
                body += results_table(f'{name} {gender} {fmt} results by decade', [(esc(k), v) for k, v in decades], name, first='Decade')
            body += results_table(f'{name} {gender} {fmt} results by year', [(esc(k), v) for k, v in reversed(years)], name, first='Year', with_last=False) + '</section>'
        records = totals_tables(ms, cards, mp, team=name, fmt=fmt) + margin_tables(ms, mp, name, fmt)
        if records:
            body += f'<section class="panel pf-block"><h2>{esc(gender)} {esc(fmt)} team records</h2>{records}</section>'
        top = leaders(ms, cards, people, pp, mp, team=name, fmt=fmt)
        if top:
            body += f'<section class="panel pf-block"><h2>{esc(gender)} {esc(fmt)} leading players</h2>{top}</section>'
        body += f'<section class="panel pf-block"><h2>Latest {esc(gender.lower())} {esc(fmt)} matches</h2>{recent_results(ms, name, mp)}</section>'
    body += '</section>'
    return body


def recent_results(matches, team, mp, limit=10):
    rows = []
    for m in sorted(matches, key=lambda m: (m['date'], m['id']), reverse=True)[:limit]:
        oc = outcome_for(m, team)
        opp = next((x for x in m['teams'] if x != team), ' v '.join(m['teams']))
        totals = ' · '.join(f"{t['team']} {t['runs']}{'/' + str(t['wickets']) if t.get('wickets') is not None and t['wickets'] < 10 else ''}" for t in (m.get('totals') or []) if not t.get('super_over') and t.get('runs') is not None)
        rows.append([f'<a href="{esc(mp[m["id"]])}">{esc(m["date"])}</a>', esc(opp), f'<i class="pf-oc f-{oc[0].lower()}">{esc(oc)}</i>', esc(totals) or '-', esc(m.get('venue') or '')])
    return lean_table('Latest matches', ['Date', 'Opponent', 'Result', 'Scores', 'Ground'], rows, css='pf-recent', left=(1, 2, 3, 4))


# ------------------------------------------------------------------ grounds

def ground_format_panel(name, fmt, matches, cards, people, pp, mp, team_paths):
    key = KEYS[fmt]
    body = f'<section class="fmt-panel fmt-{key}" id="{key}" data-fmt-panel="{key}" aria-label="{esc(name)} {esc(fmt)} record">'
    for gender in GENDERS:
        ms = [m for m in matches if m.get('gender') == gender]
        if not ms:
            continue
        rows = innings_list(ms, cards)
        by_index = defaultdict(list)
        for m, index, t in rows:
            by_index[index].append(t['runs'])
        first_avg = rate(sum(by_index[1]), len(by_index[1])) if by_index[1] else None
        second_avg = rate(sum(by_index[2]), len(by_index[2])) if by_index[2] else None
        decided, bat_first_wins, chase_wins, toss_wins, toss_known, draws = 0, 0, 0, 0, 0, 0
        for m in ms:
            card = cards.get(m['id']) or {}
            winner = (m.get('outcome') or {}).get('winner')
            innings = [inn for inn in card.get('innings') or [] if not inn.get('super_over')]
            if not winner:
                draws += (m.get('outcome') or {}).get('result') == 'draw'
            if winner and innings:
                decided += 1
                if innings[0].get('team') == winner:
                    bat_first_wins += 1
                else:
                    chase_wins += 1
            toss = card.get('toss') or {}
            if toss.get('winner') and winner:
                toss_known += 1
                toss_wins += toss['winner'] == winner
        span = f"{min(m['date'] for m in ms)[:4]} to {max(m['date'] for m in ms)[:4]}"
        body += (f'<header class="pf-fmt-head"><div><p class="eyebrow">{esc(gender.upper())} · {esc(fmt.upper())} · {esc(span)}</p>'
                 f'<h2>{esc(gender)} {esc(fmt)}s at {esc(name)}</h2></div></header>')
        tiles = [('Matches', n(len(ms))), ('1st inns avg', r2(first_avg, len(by_index[1]))), ('2nd inns avg', r2(second_avg, len(by_index[2])))]
        if fmt == 'Test':
            tiles.append(('Drawn', f'{100 * draws / len(ms):.0f}%' if ms else '-'))
        tiles += [('Bat first wins', f'{100 * bat_first_wins / decided:.0f}%' if decided else '-'), ('Chasing wins', f'{100 * chase_wins / decided:.0f}%' if decided else '-'), ('Toss winner wins', f'{100 * toss_wins / toss_known:.0f}%' if toss_known else '-')]
        body += hero(tiles, f'{name} {gender} {fmt} conditions')
        if fmt == 'Test' and (by_index[3] or by_index[4]):
            body += lean_table(f'Average {fmt} innings total by match innings', ['Innings', ('Inns', 'Recorded innings'), ('Avg', 'Average total')], [[f'{ORDINAL[i]} innings', n(len(by_index[i])), r2(rate(sum(by_index[i]), len(by_index[i])), len(by_index[i]))] for i in (1, 2, 3, 4) if by_index[i]], css='pf-line')
        records = totals_tables(ms, cards, mp, fmt=fmt)
        if records:
            body += f'<section class="panel pf-block"><h2>{esc(gender)} {esc(fmt)} team totals here</h2>{records}</section>'
        teams = Counter(t for m in ms for t in m['teams'])
        team_rows = [(f'<a href="{esc(team_paths[t])}">{esc(t)}</a>' if t in team_paths else esc(t), [m for m in ms if t in m['teams']]) for t, _ in teams.most_common()]
        body += f'<section class="panel pf-block"><h2>{esc(gender)} {esc(fmt)} team records here</h2>' + ''.join('') + lean_table(f'{name}: {gender} {fmt} record by team', ['Team'] + RECORD_HEAD + [('Last', 'Most recent match')], [record_cells(label, record(group, label_team), True) for (label, group), label_team in zip(team_rows, [t for t, _ in teams.most_common()])], css='pf-results') + '</section>'
        top = leaders(ms, cards, people, pp, mp, fmt=fmt, show_team=True)
        if top:
            body += f'<section class="panel pf-block"><h2>{esc(gender)} {esc(fmt)} leading players here</h2>{top}</section>'
        body += f'<section class="panel pf-block"><h2>Latest {esc(gender.lower())} {esc(fmt)} matches here</h2>{recent_matches_table(ms, mp)}</section>'
    body += '</section>'
    return body


def recent_matches_table(matches, mp, result=None, limit=10):
    rows = []
    for m in sorted(matches, key=lambda m: (m['date'], m['id']), reverse=True)[:limit]:
        o = m.get('outcome') or {}
        text = (o.get('winner') + ' won') if o.get('winner') else {'draw': 'Drawn', 'tie': 'Tied'}.get(o.get('result'), 'No result')
        totals = ' · '.join(f"{t['team']} {t['runs']}{'/' + str(t['wickets']) if t.get('wickets') is not None and t['wickets'] < 10 else ''}" for t in (m.get('totals') or []) if not t.get('super_over') and t.get('runs') is not None)
        rows.append([f'<a href="{esc(mp[m["id"]])}">{esc(m["date"])}</a>', esc(' v '.join(m['teams'])), esc(text), esc(totals) or '-'])
    return lean_table('Latest matches', ['Date', 'Match', 'Result', 'Scores'], rows, css='pf-recent', left=(1, 2, 3))


# ------------------------------------------------------------------ series

def editions(matches, gap_days=45):
    """Cluster a series' matches into editions by date gaps."""
    from datetime import date
    ordered = sorted(matches, key=lambda m: (m['date'], m['id']))
    groups = []
    for m in ordered:
        d = date.fromisoformat(m['date'])
        if groups and (d - groups[-1][-1][1]).days <= gap_days:
            groups[-1].append((m, d))
        else:
            groups.append([(m, d)])
    return [[m for m, _ in g] for g in groups]


def edition_label(ms):
    first, last = ms[0]['date'], ms[-1]['date']
    if first[:4] == last[:4]:
        return first[:4]
    return f'{first[:4]}/{last[2:4]}'


def scoreline(ms):
    teams = Counter(t for m in ms for t in m['teams'])
    if len(teams) != 2:
        return ''
    a, b = [t for t, _ in teams.most_common(2)]
    wins = Counter((m.get('outcome') or {}).get('winner') for m in ms)
    other = len(ms) - wins[a] - wins[b]
    return f'<span class="pf-scoreline"><b>{esc(a)}</b> {wins[a]} <i>-</i> {wins[b]} <b>{esc(b)}</b>' + (f' <small>{other} drawn or no result</small>' if other else '') + '</span>'


def series_format_panel(name, fmt, matches, cards, people, pp, mp):
    key = KEYS[fmt]
    body = f'<section class="fmt-panel fmt-{key}" id="{key}" data-fmt-panel="{key}" aria-label="{esc(name)} {esc(fmt)} editions">'
    for gender in GENDERS:
        ms = [m for m in matches if m.get('gender') == gender]
        if not ms:
            continue
        eds = editions(ms)
        span = f"{ms[-1]['date'][:4]} to {ms[0]['date'][:4]}" if ms else ''
        body += (f'<header class="pf-fmt-head"><div><p class="eyebrow">{esc(gender.upper())} · {esc(fmt.upper())} · {len(eds)} EDITION{"S" if len(eds) != 1 else ""}</p>'
                 f'<h2>{esc(name)}: {esc(gender.lower())} {esc(fmt)} editions</h2></div></header>')
        for ed in reversed(eds):
            label = edition_label(ed)
            teams = sorted({t for m in ed for t in m['teams']})
            line = scoreline(ed)
            head = f'<div class="pf-block-head"><h2>{esc(name)} {esc(label)}</h2><span class="pill">{len(ed)} match{"es" if len(ed) != 1 else ""} · {esc(ed[0]["date"])} to {esc(ed[-1]["date"])}</span></div>'
            body += f'<section class="panel pf-block pf-edition">{head}' + (f'<p class="pf-edition-line">{line}</p>' if line else f'<p class="pf-edition-line"><small>{esc(", ".join(teams))}</small></p>')
            body += recent_matches_table(ed, mp, limit=len(ed))
            top = leaders(ed, cards, people, pp, mp, fmt=fmt, limit=5, show_team=True)
            if top:
                body += f'<details class="pf-edition-leaders"><summary>Leading players of {esc(label)}</summary>{top}</details>'
            body += '</section>'
    body += '</section>'
    return body


def entity_switch(formats, counts, extra=None):
    from profile_formats import format_switch
    return format_switch(formats, {fmt: {'matches': counts.get(fmt)} for fmt in formats}, extra)


# ------------------------------------------------------------- head-to-head

def h2h_format_panel(left, right, fmt, matches, cards, people, pp, mp, host_of):
    """One rivalry, one format: per gender record, venues, years, totals, margins and leaders."""
    key = KEYS[fmt]
    body = f'<section class="fmt-panel fmt-{key}" id="{key}" data-fmt-panel="{key}" aria-label="{esc(left)} v {esc(right)} {esc(fmt)} record">'
    for gender in GENDERS:
        ms = [m for m in matches if m.get('gender') == gender]
        if not ms:
            continue
        wins = Counter((m.get('outcome') or {}).get('winner') for m in ms)
        other = len(ms) - wins[left] - wins[right]
        span = f"{min(m['date'] for m in ms)[:4]} to {max(m['date'] for m in ms)[:4]}"
        body += (f'<header class="pf-fmt-head"><div><p class="eyebrow">{esc(gender.upper())} · {esc(fmt.upper())} · {esc(span)}</p>'
                 f'<h2>{esc(left)} v {esc(right)}: {esc(gender.lower())} {esc(fmt)}s</h2></div>{form_chips(record(ms, left)["form"])}</header>')
        body += hero([('Matches', n(len(ms))), (f'{left} wins', n(wins[left])), (f'{right} wins', n(wins[right])), ('Drawn / tied / NR', n(other)),
                      (f'{left} win %', r2(rate(wins[left] * 100, len(ms)), len(ms))), ('Last played', esc(max(m['date'] for m in ms)[:4]))], f'{left} v {right} {gender} {fmt}')
        share = max(1, len(ms))
        body += (f'<div class="pf-share"><span class="pf-share-label">Share of results</span><div class="pf-share-bar">'
                 f'<i class="f-w" style="width:{100 * wins[left] / share:.2f}%" title="{esc(left)} {wins[left]}"></i>'
                 f'<i class="f-d" style="width:{100 * other / share:.2f}%" title="Drawn, tied or no result {other}"></i>'
                 f'<i class="f-l" style="width:{100 * wins[right] / share:.2f}%" title="{esc(right)} {wins[right]}"></i></div>'
                 f'<div class="pf-share-legend"><span><i class="f-w"></i>{esc(left)} <b>{wins[left]}</b></span><span><i class="f-d"></i>Other <b>{other}</b></span><span><i class="f-l"></i>{esc(right)} <b>{wins[right]}</b></span></div></div>')
        def where(m):
            host = host_of(m)
            return f'In {host}' if host in (left, right) else 'Neutral venue' if host else 'Unknown venue'
        venues = group_matches(ms, where, order=[f'In {left}', f'In {right}', 'Neutral venue', 'Unknown venue'])
        head = ['Where', ('P', 'Played'), (left, f'{left} wins'), (right, f'{right} wins'), ('Other', 'Drawn, tied or no result'), ('Last', 'Most recent match')]
        def rows_for(groups):
            out = []
            for label, group in groups:
                w = Counter((m.get('outcome') or {}).get('winner') for m in group)
                out.append([esc(label), n(len(group)), n(w[left]), n(w[right]), n(len(group) - w[left] - w[right]), esc(max(m['date'] for m in group)[:4])])
            return out
        foot = ['All', n(len(ms)), n(wins[left]), n(wins[right]), n(other), esc(max(m['date'] for m in ms)[:4])]
        body += f'<section class="panel pf-block"><h2>{esc(gender)} {esc(fmt)} results by venue</h2>{lean_table(f"{left} v {right} {gender} {fmt} by venue", head, rows_for(venues), foot, css="pf-results")}'
        grounds = group_matches(ms, lambda m: m.get('venue'), minimum=2, limit=12, sort_by_size=True)
        if grounds:
            body += lean_table(f'{left} v {right} {gender} {fmt} by ground', ['Ground'] + head[1:], rows_for(grounds), css='pf-results')
        body += '</section>'
        years = group_matches(ms, lambda m: m['date'][:4])
        if len(years) > 1:
            decades = group_matches(ms, lambda m: m['date'][:3] + '0s')
            body += f'<section class="panel pf-block"><h2>{esc(gender)} {esc(fmt)} results by year</h2>'
            if len(years) > 12:
                body += lean_table(f'{left} v {right} {gender} {fmt} by decade', ['Decade'] + head[1:], rows_for(decades), foot, css='pf-results')
            body += lean_table(f'{left} v {right} {gender} {fmt} by year', ['Year'] + head[1:], rows_for(list(reversed(years))), css='pf-results') + '</section>'
        records = totals_tables(ms, cards, mp, fmt=fmt) + margin_tables(ms, mp, left, fmt, limit=3) + margin_tables(ms, mp, right, fmt, limit=3)
        if records:
            body += f'<section class="panel pf-block"><h2>{esc(gender)} {esc(fmt)} records in this rivalry</h2>{records}</section>'
        top = leaders(ms, cards, people, pp, mp, fmt=fmt, show_team=True)
        if top:
            body += f'<section class="panel pf-block"><h2>{esc(gender)} {esc(fmt)} leading players</h2>{top}</section>'
        body += f'<section class="panel pf-block"><h2>Latest {esc(gender.lower())} {esc(fmt)} matches</h2>{recent_matches_table(ms, mp)}</section>'
    body += '</section>'
    return body
