"""Records hub: career, innings, team and partnership records per format and gender.

Career tables come from the official snapshots. Innings, team and partnership
records come from available scorecards and say so. Every table is pre-rendered
for search; a JSON feed of the same rows powers the client-side filters.
"""
from __future__ import annotations

from collections import defaultdict

from profile_formats import esc, lean_table, n, r2, rate

FORMATS = ('Test', 'ODI', 'T20I')
GENDERS = ('Men', 'Women')

CAREER_METRICS = [
    ('most-runs', 'runs', 'Most runs', False, 0, 'bat'),
    ('most-wickets', 'wickets', 'Most wickets', False, 0, 'bowl'),
    ('most-centuries', 'hundreds', 'Most centuries', False, 0, 'bat'),
    ('most-fifties', 'fifties', 'Most fifties', False, 0, 'bat'),
    ('most-matches', 'matches', 'Most appearances', False, 0, 'bat'),
    ('best-batting-average', 'avg', 'Highest batting average', False, 20, 'bat'),
    ('best-batting-strike-rate', 'sr', 'Highest batting strike rate', False, 500, 'bat'),
    ('most-fours', 'fours', 'Most fours', False, 0, 'bat'),
    ('most-sixes', 'sixes', 'Most sixes', False, 0, 'bat'),
    ('most-ducks', 'ducks', 'Most ducks', False, 0, 'bat'),
    ('best-bowling-average', 'bowlAvg', 'Lowest bowling average', True, 20, 'bowl'),
    ('best-bowling-strike-rate', 'bowlSr', 'Lowest bowling strike rate', True, 20, 'bowl'),
    ('best-economy', 'econ', 'Lowest economy rate', True, 300, 'bowl'),
    ('most-five-wicket-hauls', 'five_w', 'Most five-wicket innings', False, 0, 'bowl'),
    ('most-catches', 'catches', 'Most catches', False, 0, 'field'),
    ('most-stumpings', 'stumpings', 'Most stumpings', False, 0, 'field'),
]
MINIMUM_FIELD = {'bowlAvg': 'wickets', 'bowlSr': 'wickets', 'econ': 'legal', 'sr': 'balls'}
MINIMUM_LABEL = {'wickets': 'wickets', 'legal': 'legal balls', 'balls': 'balls faced', 'innings': 'batting innings'}

INNINGS_RECORDS = [
    ('highest-scores', 'Highest individual scores', 'bat'),
    ('highest-strike-rate-innings', 'Highest strike rate in an innings', 'bat'),
    ('most-sixes-in-an-innings', 'Most sixes in an innings', 'bat'),
    ('best-bowling-innings', 'Best bowling figures in an innings', 'bowl'),
    ('most-runs-in-a-year', 'Most runs in a calendar year', 'year'),
    ('most-wickets-in-a-year', 'Most wickets in a calendar year', 'year'),
    ('highest-partnerships', 'Highest partnerships', 'stand'),
    ('highest-team-totals', 'Highest team totals', 'team'),
    ('lowest-team-totals', 'Lowest all-out totals', 'team'),
    ('highest-chases', 'Highest successful chases', 'team'),
    ('biggest-wins-by-runs', 'Biggest wins by runs', 'team'),
    ('biggest-wins-by-wickets', 'Biggest wins by wickets', 'team'),
]
CATEGORY_LABEL = {'bat': 'Batting', 'bowl': 'Bowling', 'field': 'Fielding', 'year': 'Calendar year', 'stand': 'Partnerships', 'team': 'Team'}


def ordinal(k):
    return {1: '1st', 2: '2nd', 3: '3rd'}.get(k, f'{k}th')


# ---------------------------------------------------------------- collection

def innings_rows(matches, cards, people, gender, fmt):
    """Every recorded batting and bowling innings for one gender and format."""
    bats, bowls, stands = [], [], []
    for m in matches:
        if m.get('gender') != gender or m.get('format') != fmt:
            continue
        card = cards.get(m['id'])
        if not card:
            continue
        for inn in card.get('innings') or []:
            if inn.get('super_over'):
                continue
            bat_team = inn.get('team')
            bowl_team = next((x for x in m['teams'] if x != bat_team), '')
            for b in inn.get('batting') or []:
                if b.get('id') not in people or b.get('runs') is None:
                    continue
                bats.append({'pid': b['id'], 'runs': b['runs'], 'balls': b.get('balls'), 'fours': b.get('fours'), 'sixes': b.get('sixes'), 'no': b.get('out') is False,
                             'team': bat_team, 'opp': bowl_team, 'venue': m.get('venue') or '', 'date': m['date'], 'match': m['id']})
            for b in inn.get('bowling') or []:
                if b.get('id') not in people or b.get('wickets') is None or b.get('runs') is None:
                    continue
                bowls.append({'pid': b['id'], 'wickets': b['wickets'], 'conceded': b['runs'], 'balls': b.get('balls'), 'maidens': b.get('maidens'),
                              'team': bowl_team, 'opp': bat_team, 'venue': m.get('venue') or '', 'date': m['date'], 'match': m['id']})
            stands.extend(partnerships(inn, m, people))
    return bats, bowls, stands


def partnerships(inn, m, people):
    """Stands rebuilt from the batting order and the fall of wickets; abandoned if the order is inconsistent."""
    fall = sorted((w for w in inn.get('fall') or [] if w.get('runs') is not None and w.get('wicket')), key=lambda w: w['wicket'])
    batting = inn.get('batting') or []
    if len(batting) < 2 or not fall:
        return []
    names = [b.get('name') for b in batting]
    ids = [b.get('id') for b in batting]
    if len(set(names)) != len(names):
        return []
    at_crease = [0, 1]
    next_in = 2
    previous = 0
    out = []
    bat_team = inn.get('team')
    opp = next((x for x in m['teams'] if x != bat_team), '')
    for w in fall:
        if w['wicket'] != len(out) + 1:
            return []
        if w.get('player') not in names:
            return []
        gone = names.index(w['player'])
        if gone not in at_crease:
            return []
        pair = tuple(sorted(at_crease))
        out.append({'runs': w['runs'] - previous, 'wicket': w['wicket'], 'pids': (ids[pair[0]], ids[pair[1]]), 'team': bat_team, 'opp': opp,
                    'venue': m.get('venue') or '', 'date': m['date'], 'match': m['id'], 'unbroken': False})
        previous = w['runs']
        if next_in >= len(batting):
            at_crease = [x for x in at_crease if x != gone]
            break
        at_crease[at_crease.index(gone)] = next_in
        next_in += 1
    total = inn.get('runs')
    if total is not None and total > previous and len(at_crease) == 2 and len(out) < 10:
        pair = tuple(sorted(at_crease))
        out.append({'runs': total - previous, 'wicket': len(out) + 1, 'pids': (ids[pair[0]], ids[pair[1]]), 'team': bat_team, 'opp': opp,
                    'venue': m.get('venue') or '', 'date': m['date'], 'match': m['id'], 'unbroken': True})
    return [s for s in out if s['runs'] >= 0 and all(pid in people for pid in s['pids'])]


def team_rows(matches, cards, gender, fmt):
    totals, wins = [], []
    for m in matches:
        if m.get('gender') != gender or m.get('format') != fmt:
            continue
        card = cards.get(m['id']) or {}
        innings = [inn for inn in card.get('innings') or [] if not inn.get('super_over') and inn.get('runs') is not None]
        if not innings:
            innings = [t for t in (m.get('totals') or []) if not t.get('super_over') and t.get('runs') is not None]
        winner = (m.get('outcome') or {}).get('winner')
        for index, t in enumerate(innings, 1):
            opp = next((x for x in m['teams'] if x != t.get('team')), '')
            totals.append({'team': t.get('team'), 'runs': t['runs'], 'wickets': t.get('wickets'), 'balls': t.get('balls'), 'declared': t.get('declared'),
                           'index': index, 'chase': index == (4 if fmt == 'Test' else 2) and winner == t.get('team'), 'opp': opp,
                           'venue': m.get('venue') or '', 'date': m['date'], 'match': m['id']})
        by = (m.get('outcome') or {}).get('by') or {}
        if winner and (by.get('runs') or by.get('wickets')) and not by.get('innings'):
            wins.append({'team': winner, 'opp': next((x for x in m['teams'] if x != winner), ''), 'runs': by.get('runs'), 'wickets': by.get('wickets'),
                         'venue': m.get('venue') or '', 'date': m['date'], 'match': m['id']})
    return totals, wins


# ------------------------------------------------------------------- tables

def rank_rows(rows, key, reverse=True):
    ordered = sorted(rows, key=key, reverse=reverse)
    ranked, previous, rank = [], None, 0
    for i, row in enumerate(ordered, 1):
        value = key(row)
        if value != previous:
            rank = i
        previous = value
        ranked.append((rank, row))
    return ranked


def score_text(t):
    return f"{t['runs']}{'/' + str(t['wickets']) if t.get('wickets') is not None and t['wickets'] < 10 else ''}{'d' if t.get('declared') else ''}"


def innings_record_table(key, rows, people, pp, mp, limit=100):
    """(header, body, feed) for one innings, year, stand or team record."""
    name = lambda pid: people.get(pid, {}).get('name') or pid
    link = lambda pid: f'<a href="{esc(pp[pid])}">{esc(name(pid))}</a>' if pid in pp else esc(name(pid))
    mlink = lambda row, text: f'<a href="{esc(mp[row["match"]])}">{text}</a>' if row.get('match') in mp else esc(text)
    feed = []
    if key == 'highest-scores':
        ranked = rank_rows(rows, lambda r: (r['runs'], r['no'], -(r['balls'] or 9999)))[:limit]
        head = ['Rank', 'Score', 'Player', 'Team', ('BF', 'Balls faced'), ('SR', 'Strike rate'), ('4s', 'Fours'), ('6s', 'Sixes'), 'Opponent', 'Ground', 'Date']
        body = [[str(rk), mlink(r, f"{r['runs']}{'*' if r['no'] else ''}"), link(r['pid']), esc(r['team']), n(r['balls']), r2(rate(r['runs'], r['balls'], 100), r['balls']), n(r['fours']), n(r['sixes']), esc(r['opp']), esc(r['venue']), esc(r['date'])] for rk, r in ranked]
        feed = [{'v': f"{r['runs']}{'*' if r['no'] else ''}", 'p': name(r['pid']), 'u': pp.get(r['pid'], ''), 't': r['team'], 'o': r['opp'], 'g': r['venue'], 'd': r['date'], 'm': mp.get(r['match'], ''), 'x': [r['balls'], r['fours'], r['sixes']]} for _, r in rank_rows(rows, lambda r: (r['runs'], r['no'], -(r['balls'] or 9999)))[:600]]
        return head, body, feed, (2, 3, 8, 9)
    if key == 'highest-strike-rate-innings':
        pool = [r for r in rows if r.get('balls') and r['runs'] >= 50]
        ranked = rank_rows(pool, lambda r: (rate(r['runs'], r['balls'], 100), r['runs']))[:limit]
        head = ['Rank', ('SR', 'Strike rate'), 'Player', 'Team', 'Score', ('BF', 'Balls faced'), 'Opponent', 'Ground', 'Date']
        body = [[str(rk), mlink(r, r2(rate(r['runs'], r['balls'], 100))), link(r['pid']), esc(r['team']), f"{r['runs']}{'*' if r['no'] else ''}", n(r['balls']), esc(r['opp']), esc(r['venue']), esc(r['date'])] for rk, r in ranked]
        feed = [{'v': r2(rate(r['runs'], r['balls'], 100)), 'p': name(r['pid']), 'u': pp.get(r['pid'], ''), 't': r['team'], 'o': r['opp'], 'g': r['venue'], 'd': r['date'], 'm': mp.get(r['match'], ''), 'x': [f"{r['runs']}{'*' if r['no'] else ''}", r['balls']]} for _, r in rank_rows(pool, lambda r: (rate(r['runs'], r['balls'], 100), r['runs']))[:600]]
        return head, body, feed, (2, 3, 6, 7)
    if key == 'most-sixes-in-an-innings':
        pool = [r for r in rows if r.get('sixes')]
        ranked = rank_rows(pool, lambda r: (r['sixes'], r['runs']))[:limit]
        head = ['Rank', ('6s', 'Sixes'), 'Player', 'Team', 'Score', ('BF', 'Balls faced'), 'Opponent', 'Ground', 'Date']
        body = [[str(rk), mlink(r, str(r['sixes'])), link(r['pid']), esc(r['team']), f"{r['runs']}{'*' if r['no'] else ''}", n(r['balls']), esc(r['opp']), esc(r['venue']), esc(r['date'])] for rk, r in ranked]
        feed = [{'v': r['sixes'], 'p': name(r['pid']), 'u': pp.get(r['pid'], ''), 't': r['team'], 'o': r['opp'], 'g': r['venue'], 'd': r['date'], 'm': mp.get(r['match'], ''), 'x': [f"{r['runs']}{'*' if r['no'] else ''}", r['balls']]} for _, r in rank_rows(pool, lambda r: (r['sixes'], r['runs']))[:600]]
        return head, body, feed, (2, 3, 6, 7)
    if key == 'best-bowling-innings':
        pool = [r for r in rows if r['wickets']]
        ranked = rank_rows(pool, lambda r: (r['wickets'], -r['conceded']))[:limit]
        head = ['Rank', 'Figures', 'Player', 'Team', ('Balls', 'Balls bowled'), ('Econ', 'Runs per over'), 'Opponent', 'Ground', 'Date']
        body = [[str(rk), mlink(r, f"{r['wickets']}/{r['conceded']}"), link(r['pid']), esc(r['team']), n(r['balls']), r2(rate(r['conceded'], r['balls'], 6), r['balls']), esc(r['opp']), esc(r['venue']), esc(r['date'])] for rk, r in ranked]
        feed = [{'v': f"{r['wickets']}/{r['conceded']}", 'p': name(r['pid']), 'u': pp.get(r['pid'], ''), 't': r['team'], 'o': r['opp'], 'g': r['venue'], 'd': r['date'], 'm': mp.get(r['match'], ''), 'x': [r['balls']]} for _, r in rank_rows(pool, lambda r: (r['wickets'], -r['conceded']))[:600]]
        return head, body, feed, (2, 3, 6, 7)
    if key in ('most-runs-in-a-year', 'most-wickets-in-a-year'):
        metric = 'runs' if key == 'most-runs-in-a-year' else 'wickets'
        agg = defaultdict(lambda: {'v': 0, 'inns': 0, 'matches': set(), 'team': None, 'hs': 0, 'best': None, 'hundreds': 0, 'five': 0})
        for r in rows:
            a = agg[(r['pid'], r['date'][:4])]
            a['v'] += r[metric]
            a['inns'] += 1
            a['matches'].add(r['match'])
            a['team'] = r['team']
            if metric == 'runs':
                a['hs'] = max(a['hs'], r['runs'])
                a['hundreds'] += r['runs'] >= 100
            else:
                a['five'] += r['wickets'] >= 5
                if a['best'] is None or (r['wickets'], -r['conceded']) > (a['best'][0], -a['best'][1]):
                    a['best'] = (r['wickets'], r['conceded'])
        items = [(pid, year, a) for (pid, year), a in agg.items() if a['v']]
        ranked = rank_rows(items, lambda x: (x[2]['v'], -x[2]['inns']))[:limit]
        if metric == 'runs':
            head = ['Rank', 'Runs', 'Player', 'Team', 'Year', ('Mat', 'Matches'), ('Inns', 'Innings'), ('HS', 'Highest score'), '100']
            body = [[str(rk), n(a['v']), link(pid), esc(a['team']), esc(year), n(len(a['matches'])), n(a['inns']), n(a['hs']), n(a['hundreds'])] for rk, (pid, year, a) in ranked]
            feed = [{'v': a['v'], 'p': name(pid), 'u': pp.get(pid, ''), 't': a['team'], 'o': '', 'g': '', 'd': year, 'm': '', 'x': [len(a['matches']), a['inns'], a['hs'], a['hundreds']]} for _, (pid, year, a) in rank_rows(items, lambda x: (x[2]['v'], -x[2]['inns']))[:600]]
        else:
            head = ['Rank', ('Wkts', 'Wickets'), 'Player', 'Team', 'Year', ('Mat', 'Matches'), ('Inns', 'Innings'), ('BBI', 'Best bowling'), '5w']
            body = [[str(rk), n(a['v']), link(pid), esc(a['team']), esc(year), n(len(a['matches'])), n(a['inns']), f"{a['best'][0]}/{a['best'][1]}" if a['best'] else '-', n(a['five'])] for rk, (pid, year, a) in ranked]
            feed = [{'v': a['v'], 'p': name(pid), 'u': pp.get(pid, ''), 't': a['team'], 'o': '', 'g': '', 'd': year, 'm': '', 'x': [len(a['matches']), a['inns'], f"{a['best'][0]}/{a['best'][1]}" if a['best'] else '-', a['five']]} for _, (pid, year, a) in rank_rows(items, lambda x: (x[2]['v'], -x[2]['inns']))[:600]]
        return head, body, feed, (2, 3)
    if key == 'highest-partnerships':
        ranked = rank_rows(rows, lambda s: (s['runs'], s['unbroken']))[:limit]
        head = ['Rank', 'Runs', 'Wicket', 'Batters', 'Team', 'Opponent', 'Ground', 'Date']
        body = [[str(rk), mlink(s, f"{s['runs']}{'*' if s['unbroken'] else ''}"), f"{ordinal(s['wicket'])}", link(s['pids'][0]) + ', ' + link(s['pids'][1]), esc(s['team']), esc(s['opp']), esc(s['venue']), esc(s['date'])] for rk, s in ranked]
        feed = [{'v': f"{s['runs']}{'*' if s['unbroken'] else ''}", 'p': name(s['pids'][0]) + ', ' + name(s['pids'][1]), 'u': '', 't': s['team'], 'o': s['opp'], 'g': s['venue'], 'd': s['date'], 'm': mp.get(s['match'], ''), 'x': [ordinal(s['wicket'])]} for _, s in rank_rows(rows, lambda s: (s['runs'], s['unbroken']))[:600]]
        return head, body, feed, (2, 3, 4, 5, 6)
    if key in ('highest-team-totals', 'lowest-team-totals', 'highest-chases'):
        if key == 'highest-team-totals':
            pool, keyfn, reverse = rows, (lambda t: (t['runs'], -(t['wickets'] if t['wickets'] is not None else 10))), True
        elif key == 'lowest-team-totals':
            pool, keyfn, reverse = [t for t in rows if t.get('wickets') == 10], (lambda t: (t['runs'], t['balls'] or 0)), False
        else:
            pool, keyfn, reverse = [t for t in rows if t['chase']], (lambda t: (t['runs'], -(t['wickets'] if t['wickets'] is not None else 10))), True
        ranked = rank_rows(pool, keyfn, reverse)[:limit]
        head = ['Rank', 'Total', 'Team', ('Overs', 'Overs faced'), 'Opponent', 'Ground', 'Date']
        overs = lambda t: (str(t['balls'] // 6) + ('.' + str(t['balls'] % 6) if t['balls'] % 6 else '')) if isinstance(t.get('balls'), int) and t['balls'] else '-'
        body = [[str(rk), mlink(t, score_text(t)), esc(t['team']), overs(t), esc(t['opp']), esc(t['venue']), esc(t['date'])] for rk, t in ranked]
        feed = [{'v': score_text(t), 'p': t['team'], 'u': '', 't': t['team'], 'o': t['opp'], 'g': t['venue'], 'd': t['date'], 'm': mp.get(t['match'], ''), 'x': [overs(t)]} for _, t in rank_rows(pool, keyfn, reverse)[:600]]
        return head, body, feed, (2, 4, 5)
    if key in ('biggest-wins-by-runs', 'biggest-wins-by-wickets'):
        field = 'runs' if key.endswith('runs') else 'wickets'
        pool = [w for w in rows if w.get(field)]
        ranked = rank_rows(pool, lambda w: (w[field], w['date']), True)[:limit]
        head = ['Rank', 'Margin', 'Winner', 'Opponent', 'Ground', 'Date']
        body = [[str(rk), mlink(w, f"{w[field]} {field}"), esc(w['team']), esc(w['opp']), esc(w['venue']), esc(w['date'])] for rk, w in ranked]
        feed = [{'v': f"{w[field]} {field}", 'p': w['team'], 'u': '', 't': w['team'], 'o': w['opp'], 'g': w['venue'], 'd': w['date'], 'm': mp.get(w['match'], ''), 'x': []} for _, w in rank_rows(pool, lambda w: (w[field], w['date']), True)[:600]]
        return head, body, feed, (2, 3, 4)
    raise KeyError(key)


def career_table(field, label, kind, entries, minimum, lower, pp):
    """Ranked career leaderboard with the columns that make the metric legible."""
    minimum_field = MINIMUM_FIELD.get(field, 'innings')
    qualified = [p for p in entries if p.get(field) is not None and (p.get(minimum_field) or 0) >= minimum]
    qualified.sort(key=lambda p: ((p[field] if lower else -p[field]), p['name']))
    ranked = rank_rows(qualified, lambda p: p[field], reverse=not lower)[:100]
    fmt_value = lambda p: r2(p[field]) if field in ('avg', 'sr', 'bowlAvg', 'bowlSr', 'econ') else n(p[field])
    if kind == 'bowl':
        head = ['Rank', label, 'Player', 'Team', 'Span', ('Mat', 'Matches'), ('Inns', 'Bowling innings'), 'Balls', 'Runs', ('Wkts', 'Wickets'), ('BBI', 'Best bowling'), ('Avg', 'Bowling average'), ('Econ', 'Economy'), ('SR', 'Strike rate'), '5w']
        body = [[str(rk), fmt_value(p), f'<a href="{esc(p["url"])}">{esc(p["name"])}</a>', esc(' / '.join(p['teams'])), esc(p.get('span') or '-'), n(p.get('matches')), n(p.get('bowling_innings')), n(p.get('legal')), n(p.get('conceded')), n(p.get('wickets')), esc(p.get('best_bowling') or '-'), r2(p.get('bowlAvg'), p.get('wickets')), r2(p.get('econ'), p.get('legal')), r2(p.get('bowlSr'), p.get('wickets')), n(p.get('five_w'))] for rk, p in ranked]
    elif kind == 'field':
        head = ['Rank', label, 'Player', 'Team', 'Span', ('Mat', 'Matches'), ('Inns', 'Fielding innings'), ('Ct', 'Catches'), ('St', 'Stumpings'), ('Dis', 'Dismissals'), ('Dis/Inns', 'Dismissals per innings')]
        body = [[str(rk), fmt_value(p), f'<a href="{esc(p["url"])}">{esc(p["name"])}</a>', esc(' / '.join(p['teams'])), esc(p.get('span') or '-'), n(p.get('matches')), n(p.get('fielding_innings')), n(p.get('catches')), n(p.get('stumpings')), n(p.get('dismissals')), f"{p['dismissals_per_innings']:.3f}" if p.get('dismissals_per_innings') is not None else '-'] for rk, p in ranked]
    else:
        head = ['Rank', label, 'Player', 'Team', 'Span', ('Mat', 'Matches'), ('Inns', 'Innings'), ('NO', 'Not outs'), 'Runs', ('HS', 'Highest score'), ('Avg', 'Average'), ('SR', 'Strike rate'), '100', '50', ('0', 'Ducks')]
        body = [[str(rk), fmt_value(p), f'<a href="{esc(p["url"])}">{esc(p["name"])}</a>', esc(' / '.join(p['teams'])), esc(p.get('span') or '-'), n(p.get('matches')), n(p.get('innings')), n(p.get('notouts')), n(p.get('runs')), esc(p.get('highest_display') or '-'), r2(p.get('avg'), p.get('outs')), r2(p.get('sr'), p.get('balls')), n(p.get('hundreds')), n(p.get('fifties')), n(p.get('ducks'))] for rk, p in ranked]
    return head, body, qualified


def records_table(head, body, caption, left=()):
    return lean_table(caption, head, [[c for c in row] for row in body], css='pf-records', left=left)


def records_index(gender_format_links):
    """Hub page grouped by category, then gender and format."""
    out = ''
    categories = [('bat', 'Batting'), ('bowl', 'Bowling'), ('team', 'Team'), ('stand', 'Partnerships'), ('year', 'Calendar year'), ('field', 'Fielding')]
    for cat, title in categories:
        keys = [(k, label) for k, f, label, lower, minimum, kind in CAREER_METRICS if kind == cat] + [(k, label) for k, label, kind in INNINGS_RECORDS if kind == cat]
        if not keys:
            continue
        out += f'<section class="panel pf-block records-cat"><h2>{esc(title)} records</h2><div class="records-grid">'
        for key, label in keys:
            links = ''.join(f'<a href="/records/{g.lower()}/{f.lower()}/{key}/" class="fmt-{f.lower()}">{esc(g)} {esc(f)}</a>' for g in GENDERS for f in FORMATS if (g, f, key) in gender_format_links)
            if links:
                out += f'<div class="records-item"><h3>{esc(label)}</h3><div class="records-links">{links}</div></div>'
        out += '</div></section>'
    return out
