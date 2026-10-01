"""Format-first player profiles.

Every figure on a profile is shown per format. The official career snapshot
is the complete record; archive splits come from available scorecards and
carry their coverage of the official innings count. Unknown inputs never
become zero, and a partial denominator never becomes a rate.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal, ROUND_DOWN
import html

FORMATS = ('Test', 'ODI', 'T20I')
KEYS = {'Test': 'test', 'ODI': 'odi', 'T20I': 't20i'}
LONG = {'Test': 'Test', 'ODI': 'ODI', 'T20I': 'T20I'}
RESULTS = ('Won', 'Lost', 'Drawn', 'Tied', 'No result', 'Draw / tie / no result')
SETTINGS = ('Home', 'Away', 'Neutral', 'Unknown')
ORDINAL = {1: '1st', 2: '2nd', 3: '3rd', 4: '4th'}
BAT_HEAD = [('Mat', 'Matches'), ('Inns', 'Innings'), ('NO', 'Not outs'), ('Runs', 'Runs'), ('HS', 'Highest score'), ('Avg', 'Batting average'), ('BF', 'Balls faced'), ('SR', 'Strike rate'), ('100', 'Hundreds'), ('50', 'Fifties'), ('0', 'Ducks'), ('4s', 'Fours'), ('6s', 'Sixes')]
BOWL_HEAD = [('Mat', 'Matches'), ('Inns', 'Bowling innings'), ('Balls', 'Balls bowled'), ('Mdns', 'Maidens'), ('Runs', 'Runs conceded'), ('Wkts', 'Wickets'), ('BBI', 'Best bowling in an innings'), ('Avg', 'Bowling average'), ('Econ', 'Runs conceded per over'), ('SR', 'Balls per wicket'), ('4w', 'Four-wicket innings'), ('5w', 'Five-wicket innings')]


def esc(value):
    return html.escape(str(value if value is not None else ''), quote=True)


def rate(top, bottom, factor=1):
    if top is None or bottom is None or bottom <= 0:
        return None
    return float((Decimal(top) * factor / Decimal(bottom)).quantize(Decimal('.01'), rounding=ROUND_DOWN))


def n(value):
    """Integers with thousands separators; unknown stays a dash."""
    if value is None:
        return '<span class="missing">-</span>'
    return f'{value:,}'


def r2(value, denominator=None):
    if value is None:
        if denominator == 0:
            return '<span class="not-applicable">N/A</span>'
        return '<span class="missing">-</span>'
    return f'{value:.2f}'


def is_bat(row):
    return row.get('position') is not None or row.get('runs') is not None or row.get('balls') is not None


def is_bowl(row):
    return any(row.get(k) is not None for k in ('wickets', 'legal', 'conceded'))


def complete_sum(rows, key):
    if not rows:
        return 0
    return sum(r[key] for r in rows) if all(r.get(key) is not None for r in rows) else None


def bat_totals(rows):
    bat = [r for r in rows if is_bat(r)]
    t = {'matches': len({r['match'] for r in rows}), 'innings': len(bat)}
    known_out = all(r.get('out') is not None for r in bat)
    t['outs'] = sum(1 for r in bat if r.get('out')) if known_out else None
    t['notouts'] = sum(1 for r in bat if r.get('out') is False) if known_out else None
    for key in ('runs', 'balls', 'fours', 'sixes'):
        t[key] = complete_sum(bat, key)
    known_runs = all(r.get('runs') is not None for r in bat)
    if known_runs and bat:
        best = max(bat, key=lambda r: (r['runs'], r.get('out') is False))
        t['highest'] = best['runs']
        t['highest_display'] = f"{best['runs']}{'*' if best.get('out') is False else ''}"
        t['hundreds'] = sum(r['runs'] >= 100 for r in bat)
        t['fifties'] = sum(50 <= r['runs'] < 100 for r in bat)
        t['ducks'] = sum(r['runs'] == 0 and r.get('out') for r in bat)
    else:
        t['highest'] = t['highest_display'] = t['hundreds'] = t['fifties'] = t['ducks'] = None
    t['avg'] = rate(t['runs'], t['outs'])
    t['sr'] = rate(t['runs'], t['balls'], 100)
    return t


def best_bowling(rows):
    known = [r for r in rows if r.get('wickets') is not None and r.get('conceded') is not None]
    if not known:
        return None, None
    best = max(known, key=lambda r: (r['wickets'], -r['conceded']))
    return best, f"{best['wickets']}/{best['conceded']}"


def bowl_totals(rows):
    bowl = [r for r in rows if is_bowl(r)]
    t = {'matches': len({r['match'] for r in rows}), 'bowling_innings': len(bowl)}
    for key in ('wickets', 'legal', 'conceded', 'maidens'):
        t[key] = complete_sum(bowl, key)
    known = all(r.get('wickets') is not None for r in bowl)
    t['four_w'] = sum(r['wickets'] == 4 for r in bowl) if known else None
    t['five_w'] = sum(r['wickets'] >= 5 for r in bowl) if known else None
    _, t['best_bowling'] = best_bowling(bowl)
    t['bowlAvg'] = rate(t['conceded'], t['wickets'])
    t['econ'] = rate(t['conceded'], t['legal'], 6)
    t['bowlSr'] = rate(t['legal'], t['wickets'])
    return t


def coverage(stats, rows):
    """How much of the official career the scorecards cover, per format."""
    bat = [r for r in rows if is_bat(r)]
    bowl = [r for r in rows if is_bowl(r)]
    official_inns = (stats or {}).get('innings')
    official_runs = (stats or {}).get('runs')
    official_bowl = (stats or {}).get('bowling_innings')
    official_wkts = (stats or {}).get('wickets')
    archive_runs = complete_sum(bat, 'runs')
    archive_wkts = complete_sum(bowl, 'wickets')
    complete_bat = official_inns is not None and official_inns == len(bat) and official_runs == archive_runs
    complete_bowl = (official_bowl or 0) == len(bowl) and (official_wkts or 0) == (archive_wkts or 0)
    pct = None
    if official_inns:
        pct = min(100, round(100 * len(bat) / official_inns))
    return {
        'official_innings': official_inns, 'archive_innings': len(bat),
        'official_bowling_innings': official_bowl, 'archive_bowling_innings': len(bowl),
        'complete': bool(stats) and complete_bat and complete_bowl, 'complete_batting': complete_bat,
        'complete_bowling': complete_bowl, 'pct': pct, 'matches': len({r['match'] for r in rows}),
    }


def coverage_label(cov):
    if not cov['archive_innings'] and not cov['archive_bowling_innings']:
        return 'No scorecards yet'
    if cov['complete']:
        return 'Complete: every official innings is in the scorecards'
    official = cov['official_innings']
    if official:
        return f"Scorecards for {cov['archive_innings']:,} of {official:,} official batting innings"
    return f"{cov['archive_innings']:,} batting innings in scorecards"


def format_role(stats):
    """Role within one format, from the official snapshot."""
    s = stats or {}
    matches = s.get('matches') or 0
    runs = s.get('runs') or 0
    wickets = s.get('wickets') or 0
    if (s.get('stumpings') or 0) >= 5:
        return 'keeper'
    if not matches:
        return 'batter'
    runs_pm = runs / matches
    wkts_pm = wickets / matches
    if wickets >= 10 and wkts_pm >= 0.8 and runs_pm >= 15:
        return 'all-rounder'
    if wickets >= 10 and (runs_pm < 12 or wkts_pm >= 1.2 and runs_pm < 20):
        return 'bowler'
    if wickets >= 15 and runs < 300:
        return 'bowler'
    return 'batter'


def role_label(career, rows):
    roles = Counter(format_role(s) for s in (career or {}).values())
    role = roles.most_common(1)[0][0] if roles else 'batter'
    if role == 'keeper':
        return 'Wicketkeeper-batter'
    if role == 'all-rounder':
        return 'All-rounder'
    if role == 'bowler':
        return 'Bowler'
    positions = [r['position'] for r in rows if r.get('position')]
    if positions:
        positions.sort()
        median = positions[len(positions) // 2]
        if median <= 3:
            return 'Top-order batter'
        if median <= 6:
            return 'Middle-order batter'
        return 'Lower-order batter'
    return 'Batter'


# ---------------------------------------------------------------- tables

def lean_table(caption, head, body, foot=None, css='', titles=True, left=()):
    """A compact table: labels left, figures right, totals in the footer.

    `left` lists the 1-based indices of text columns that should also align left.
    """
    if not body:
        return ''
    cols = [(h, h) if isinstance(h, str) else h for h in head]
    left = set(left)
    ths = ''.join((f'<th scope="col"{" class=t" if i in left else ""} title="{esc(title)}">{esc(label)}</th>' if titles and title != label else f'<th scope="col"{" class=t" if i in left else ""}>{esc(label)}</th>') for i, (label, title) in enumerate(cols))
    rows = ''.join('<tr><th scope="row">' + cells[0] + '</th>' + ''.join(f'<td{" class=t" if i in left else ""}>{c}</td>' for i, c in enumerate(cells) if i) + '</tr>' for cells in body)
    tfoot = ''
    if foot:
        foot_rows = foot if isinstance(foot[0], list) else [foot]
        tfoot = '<tfoot>' + ''.join('<tr><th scope="row">' + row[0] + '</th>' + ''.join(f'<td>{c}</td>' for c in row[1:]) + '</tr>' for row in foot_rows) + '</tfoot>'
    return (f'<div class="table-wrap pf-wrap{(" " + css) if css else ""}" tabindex="0" role="region" aria-label="{esc(caption)}">'
            f'<table class="score-table pf-table"><caption>{esc(caption)}</caption><thead><tr>{ths}</tr></thead>'
            f'<tbody>{rows}</tbody>{tfoot}</table></div>')


def bat_cells(label, t):
    return [label, n(t['matches']), n(t['innings']), n(t['notouts']), n(t['runs']), t['highest_display'] or n(None),
            r2(t['avg'], t['outs']), n(t['balls']), r2(t['sr'], t['balls']), n(t['hundreds']), n(t['fifties']), n(t['ducks']), n(t['fours']), n(t['sixes'])]


def bowl_cells(label, t):
    return [label, n(t['matches']), n(t['bowling_innings']), n(t['legal']), n(t['maidens']), n(t['conceded']), n(t['wickets']),
            t['best_bowling'] or n(None), r2(t['bowlAvg'], t['wickets']), r2(t['econ'], t['legal']), r2(t['bowlSr'], t['wickets']), n(t['four_w']), n(t['five_w'])]


def innings_label(row, fmt, discipline):
    index = row.get('innings') or 0
    if fmt == 'Test':
        return f'{ORDINAL.get(index, str(index))} innings of the match'
    if discipline == 'bat':
        return 'Batting first' if index == 1 else 'Chasing'
    return 'Bowling first' if index == 1 else 'Defending a total'


def split_groups(rows, fmt, discipline):
    """Ordered (key, title, [(label, rows)]) groups for one discipline."""
    sample = [r for r in rows if (is_bat(r) if discipline == 'bat' else is_bowl(r))]
    if not sample:
        return []
    weight = lambda group: len(group)
    groups = []

    def grouped(keyfn, order=None, minimum=1, limit=None, sort_by_size=False):
        buckets = defaultdict(list)
        for row in sample:
            key = keyfn(row)
            if key is None or key == '':
                continue
            buckets[key].append(row)
        items = [(k, v) for k, v in buckets.items() if len(v) >= minimum]
        if order:
            items.sort(key=lambda kv: (order.index(kv[0]) if kv[0] in order else len(order), str(kv[0])))
        elif sort_by_size:
            items.sort(key=lambda kv: (-weight(kv[1]), str(kv[0])))
        else:
            items.sort(key=lambda kv: kv[0])
        if limit:
            items = items[:limit]
        return [(str(k), v) for k, v in items]

    groups.append(('opposition', 'Opposition', grouped(lambda r: r.get('opponent'), sort_by_size=True)))
    groups.append(('setting', 'Home and away', grouped(lambda r: r.get('setting') or 'Unknown', order=list(SETTINGS))))
    groups.append(('innings', 'Match innings' if fmt == 'Test' else ('Batting first or chasing' if discipline == 'bat' else 'Bowling first or defending'),
                   grouped(lambda r: innings_label(r, fmt, discipline), order=[f'{ORDINAL[i]} innings of the match' for i in (1, 2, 3, 4)] + ['Batting first', 'Chasing', 'Bowling first', 'Defending a total'])))
    if discipline == 'bat':
        groups.append(('position', 'Batting position', [(f'No. {k}', v) for k, v in grouped(lambda r: int(r['position']) if r.get('position') else None)]))
    groups.append(('result', 'Match result', grouped(lambda r: r.get('result') or 'No result', order=list(RESULTS))))
    groups.append(('year', 'Year', grouped(lambda r: r['date'][:4])))
    groups.append(('ground', 'Ground', grouped(lambda r: r.get('venue'), minimum=3, limit=15, sort_by_size=True)))
    events = grouped(lambda r: r.get('event'), minimum=3, limit=12, sort_by_size=True)
    if events:
        groups.append(('event', 'Series and tournaments', events))
    return [(key, title, items) for key, title, items in groups if items]


class _Official(dict):
    """An official career line read like archive totals; absent figures stay missing."""
    def __missing__(self, key):
        return None


def split_section(rows, fmt, name, want_bowling, stats=None, played=None):
    """Tabbed batting and bowling splits for one format. When the scorecards hold less than the
    official career (matches against other teams, or no scorecard), the footer shows both lines."""
    bat_groups = split_groups(rows, fmt, 'bat')
    bowl_groups = split_groups(rows, fmt, 'bowl') if want_bowling else []
    if not bat_groups and not bowl_groups:
        return ''
    keys = []
    for key, title, _ in bat_groups + bowl_groups:
        if (key, title) not in keys:
            keys.append((key, title))
    tabs = ''.join(f'<button type="button" role="tab" data-tab="{key}" aria-selected="{"true" if i == 0 else "false"}"{" class=is-active" if i == 0 else ""}>{esc(title)}</button>' for i, (key, title) in enumerate(keys))
    bat_all = bat_totals(rows)
    bowl_all = bowl_totals(rows)
    if played:   # every match in the scorecards, including those where the player did not bat or bowl
        bat_all = {**bat_all, 'matches': played}
        bowl_all = {**bowl_all, 'matches': played}
    official = _Official(stats or {})
    bat_gap = bool(stats) and official['runs'] is not None and (official['runs'], official['innings']) != (bat_all['runs'], bat_all['innings'])
    bowl_gap = bool(stats) and official['wickets'] is not None and (official['wickets'], official['bowling_innings']) != (bowl_all['wickets'], bowl_all['bowling_innings'])
    # When the innings reconcile, a remaining match difference is only abandoned matches (the source
    # does not say whether a toss was made), so the footer takes the official match count.
    if not bat_gap and official['matches']:
        bat_all = {**bat_all, 'matches': official['matches']}
    if not bowl_gap and official['matches']:
        bowl_all = {**bowl_all, 'matches': official['matches']}
    bat_foot = [bat_cells('In these scorecards', bat_all), bat_cells('Official career', official)] if bat_gap else bat_cells('All', bat_all)
    bowl_foot = [bowl_cells('In these scorecards', bowl_all), bowl_cells('Official career', official)] if bowl_gap else bowl_cells('All', bowl_all)
    panels = ''
    for i, (key, title) in enumerate(keys):
        body = ''
        for gkey, gtitle, items in bat_groups:
            if gkey != key:
                continue
            body += lean_table(f'{name}: {fmt} batting by {gtitle.lower()}', [('', '')] + BAT_HEAD,
                               [bat_cells(esc(label), bat_totals(group)) for label, group in items], bat_foot, css='pf-bat', titles=False)
        for gkey, gtitle, items in bowl_groups:
            if gkey != key:
                continue
            body += lean_table(f'{name}: {fmt} bowling by {gtitle.lower()}', [('', '')] + BOWL_HEAD,
                               [bowl_cells(esc(label), bowl_totals(group)) for label, group in items], bowl_foot, css='pf-bowl', titles=False)
        panels += f'<div class="pf-tabpanel{" is-active" if i == 0 else ""}" role="tabpanel" data-tab-panel="{key}">{body}</div>'
    note = ('<p class="pf-fine">The official career includes innings these scorecards do not hold, mostly older matches without a full scorecard. '
            'Splits use the scorecards; the last footer line is the official total.</p>') if bat_gap or bowl_gap else ''
    return f'<div class="pf-tabs" role="tablist" aria-label="Split by">{tabs}</div>{panels}{note}'


# ------------------------------------------------------------- milestones

def milestone_lists(rows, fmt, name, stats, want_bowling):
    bat = sorted((r for r in rows if is_bat(r) and r.get('runs') is not None), key=lambda r: (r['date'], r['match'], r.get('innings') or 0))
    bowl = sorted((r for r in rows if is_bowl(r) and r.get('wickets') is not None), key=lambda r: (r['date'], r['match'], r.get('innings') or 0))
    out = ''

    def entry(row, figure):
        return (f'<li><a href="{esc(row["url"])}"><b>{figure}</b><span>v {esc(row["opponent"])}</span>'
                f'<small>{esc(row.get("venue", ""))} · {esc(row["date"])}</small></a></li>')

    hundreds = [r for r in bat if r['runs'] >= 100]
    official_hundreds = (stats or {}).get('hundreds')
    if hundreds:
        count = f'{len(hundreds)}' if official_hundreds in (None, len(hundreds)) else f'{len(hundreds)} of {official_hundreds}'
        out += f'<div class="pf-ms"><h3>Hundreds <span>{count}</span></h3><ol class="pf-ms-list">' + ''.join(entry(r, f"{r['runs']}{'*' if r.get('out') is False else ''}") for r in reversed(hundreds)) + '</ol></div>'
    if want_bowling:
        fivers = [r for r in bowl if r['wickets'] >= 5]
        official_five = (stats or {}).get('five_w')
        if fivers:
            count = f'{len(fivers)}' if official_five in (None, len(fivers)) else f'{len(fivers)} of {official_five}'
            out += f'<div class="pf-ms"><h3>Five-wicket innings <span>{count}</span></h3><ol class="pf-ms-list">' + ''.join(entry(r, f"{r['wickets']}/{r['conceded'] if r.get('conceded') is not None else '?'}") for r in reversed(fivers)) + '</ol></div>'
    return out


def best_tables(rows, fmt, name, want_bowling):
    bat = [r for r in rows if is_bat(r) and r.get('runs') is not None]
    bowl = [r for r in rows if is_bowl(r) and r.get('wickets') is not None and r.get('conceded') is not None]
    out = ''
    if len(bat) >= 3:
        top = sorted(bat, key=lambda r: (-r['runs'], r.get('out') is not False, r['date']))[:10]
        body = [[f'<a href="{esc(r["url"])}">{r["runs"]}{"*" if r.get("out") is False else ""}</a>', n(r.get('balls')), r2(rate(r.get('runs'), r.get('balls'), 100), r.get('balls')), n(r.get('fours')), n(r.get('sixes')), esc(r['opponent']), esc(r.get('venue', '')), esc(r['date'])] for r in top]
        out += lean_table(f'{name}: highest {fmt} scores', ['Score', ('BF', 'Balls faced'), ('SR', 'Strike rate'), ('4s', 'Fours'), ('6s', 'Sixes'), 'Opponent', 'Ground', 'Date'], body, css='pf-best', left=(5, 6, 7))
    if want_bowling and len(bowl) >= 3 and any(r['wickets'] > 0 for r in bowl):
        top = sorted(bowl, key=lambda r: (-r['wickets'], r['conceded'], r['date']))[:10]
        body = [[f'<a href="{esc(r["url"])}">{r["wickets"]}/{r["conceded"]}</a>', n(r.get('legal')), n(r.get('maidens')), r2(rate(r.get('conceded'), r.get('legal'), 6), r.get('legal')), esc(r['opponent']), esc(r.get('venue', '')), esc(r['date'])] for r in top]
        out += lean_table(f'{name}: best {fmt} bowling', ['Figures', ('Balls', 'Balls bowled'), ('Mdns', 'Maidens'), ('Econ', 'Runs per over'), 'Opponent', 'Ground', 'Date'], body, css='pf-best', left=(4, 5, 6))
    return out


def recent_form(rows, want_bowling):
    """Last ten batting innings and, for bowlers, last ten bowling innings."""
    bat = sorted((r for r in rows if is_bat(r)), key=lambda r: (r['date'], r['match'], r.get('innings') or 0))[-10:]
    bowl = sorted((r for r in rows if is_bowl(r)), key=lambda r: (r['date'], r['match'], r.get('innings') or 0))[-10:]
    tiles = ''
    if len(bat) >= 3:
        t = bat_totals(bat)
        tiles += (f'<div class="pf-form"><span>Last {len(bat)} batting innings</span>'
                  f'<div><b>{n(t["runs"])}</b><small>runs</small></div><div><b>{r2(t["avg"], t["outs"])}</b><small>average</small></div>'
                  f'<div><b>{r2(t["sr"], t["balls"])}</b><small>strike rate</small></div><div><b>{n(t["fifties"])}</b><small>50s</small></div><div><b>{n(t["hundreds"])}</b><small>100s</small></div></div>')
    if want_bowling and len(bowl) >= 3:
        t = bowl_totals(bowl)
        tiles += (f'<div class="pf-form"><span>Last {len(bowl)} bowling innings</span>'
                  f'<div><b>{n(t["wickets"])}</b><small>wickets</small></div><div><b>{r2(t["bowlAvg"], t["wickets"])}</b><small>average</small></div>'
                  f'<div><b>{r2(t["econ"], t["legal"])}</b><small>economy</small></div><div><b>{r2(t["bowlSr"], t["wickets"])}</b><small>strike rate</small></div><div><b>{t["best_bowling"] or n(None)}</b><small>best</small></div></div>')
    return tiles


def recent_matches(rows, apps, fmt, limit=10):
    by_match = defaultdict(list)
    for r in rows:
        by_match[r['match']].append(r)
    body = []
    for app in [x for x in apps if x['format'] == fmt][:limit]:
        mine = by_match.get(app['match'], [])
        bats = [r for r in mine if is_bat(r)]
        bowls = [r for r in mine if is_bowl(r)]
        scores = ' & '.join(f"{r['runs']}{'*' if r.get('out') is False else ''}" if r.get('runs') is not None else '-' for r in bats) or '<span class="pf-dnb">did not bat</span>'
        figures = ' & '.join(f"{r['wickets']}/{r['conceded']}" if r.get('wickets') is not None and r.get('conceded') is not None else '-' for r in bowls)
        opponent = next((r['opponent'] for r in mine), None) or ' v '.join(app['teams'])
        body.append([f'<a href="{esc(app["url"])}">{esc(app["date"])}</a>', esc(opponent), scores, figures or '<span class="pf-dnb">-</span>', esc(app.get('venue', '')), esc(app['result'])])
    return lean_table(f'Latest {fmt} matches', ['Date', 'Opponent', ('Bat', 'Batting'), ('Bowl', 'Bowling'), 'Ground', 'Result'], body, css='pf-recent', left=(1, 2, 3, 4, 5))


# ----------------------------------------------------------------- panels

RANKED = {'matches', 'runs', 'hundreds', 'wickets', 'catches', 'stumpings', 'five_w'}


def ordinal(n):
    return f'{n:,}' + ('th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th'))


def rank_note(ranks, scope, key, gender):
    """'3rd among men' under a counting figure, for the top 100 only; a long tail rank adds nothing."""
    rank = (ranks or {}).get((scope, key))
    if key not in RANKED or not rank or rank > 100 or gender not in ('Men', 'Women'):
        return ''
    return f'<small class="pf-rank">{ordinal(rank)} among {gender.lower()}</small>'


def hero_tiles(stats, role, fmt, stat_value, ranks=None, gender=None):
    s = stats or {}
    if role == 'bowler':
        spec = [('wickets', 'Wickets'), ('bowlAvg', 'Average'), ('econ', 'Economy'), ('bowlSr', 'Strike rate'), ('best_bowling', 'Best'), ('five_w', 'Five-fors')]
    elif role == 'all-rounder':
        spec = [('runs', 'Runs'), ('avg', 'Bat avg'), ('sr', 'Strike rate'), ('wickets', 'Wickets'), ('bowlAvg', 'Bowl avg'), ('econ', 'Economy')]
    elif role == 'keeper':
        spec = [('runs', 'Runs'), ('avg', 'Average'), ('sr', 'Strike rate'), ('hundreds', 'Hundreds'), ('catches', 'Catches'), ('stumpings', 'Stumpings')]
    else:
        spec = [('runs', 'Runs'), ('avg', 'Average'), ('sr', 'Strike rate'), ('hundreds', 'Hundreds'), ('fifties', 'Fifties'), ('highest_display', 'Highest')]
    tiles = ''.join(f'<div{" class=lead" if i == 0 else ""}><strong>{stat_value(s, key)}</strong><span>{label}</span>{rank_note(ranks, fmt, key, gender)}</div>' for i, (key, label) in enumerate(spec))
    return f'<div class="pf-hero" aria-label="{esc(fmt)} career headline figures">{tiles}</div>'


def official_lines(stats, fmt, stat_value, want_bowling):
    """The official career line for one format: batting, bowling, fielding."""
    s = stats or {}
    out = lean_table(f'Official {fmt} batting record', ['Batting'] + BAT_HEAD,
                     [['Career'] + [stat_value(s, key) for key in ('matches', 'innings', 'notouts', 'runs', 'highest_display', 'avg', 'balls', 'sr', 'hundreds', 'fifties', 'ducks', 'fours', 'sixes')]], css='pf-line')
    if want_bowling or (s.get('wickets') or 0) or (s.get('bowling_innings') or 0):
        out += lean_table(f'Official {fmt} bowling record', ['Bowling'] + BOWL_HEAD[:6] + [('BBI', 'Best bowling in an innings'), ('BBM', 'Best bowling in a match'), ('Avg', 'Bowling average'), ('Econ', 'Runs conceded per over'), ('SR', 'Balls per wicket'), ('4w', 'Four-wicket innings'), ('5w', 'Five-wicket innings'), ('10w', 'Ten-wicket matches')],
                          [['Career'] + [stat_value(s, key) for key in ('matches', 'bowling_innings', 'legal', 'maidens', 'conceded', 'wickets', 'best_bowling', 'best_match', 'bowlAvg', 'econ', 'bowlSr', 'four_w', 'five_w', 'ten_w')]], css='pf-line')
    if (s.get('dismissals') or 0) or (s.get('catches') or 0):
        out += lean_table(f'Official {fmt} fielding record', ['Fielding', ('Mat', 'Matches'), ('Inns', 'Fielding innings'), ('Ct', 'Catches'), ('St', 'Stumpings'), ('Dis', 'Dismissals'), ('Dis/Inns', 'Dismissals per innings'), ('Best', 'Most dismissals in an innings')],
                          [['Career'] + [stat_value(s, key) for key in ('matches', 'fielding_innings', 'catches', 'stumpings', 'dismissals', 'dismissals_per_innings', 'most_dismissals')]], css='pf-line')
    return out


def format_panel(player, fmt, stats, rows, apps, charts, stat_value, ranks=None):
    """One complete per-format view: official line, charts, splits, milestones."""
    name = player['name']
    key = KEYS[fmt]
    role = format_role(stats) if stats else ('bowler' if sum(r.get('wickets') or 0 for r in rows) > sum(r.get('runs') or 0 for r in rows) / 20 else 'batter')
    cov = coverage(stats, rows)
    bowl_rows = [r for r in rows if is_bowl(r)]
    want_bowling = role in ('bowler', 'all-rounder') or (stats or {}).get('wickets', 0) and (stats or {}).get('wickets') >= 10 or sum(r.get('wickets') or 0 for r in bowl_rows) >= 10
    span = (stats or {}).get('span') or (f"{rows[0]['date'][:4]}-{rows[-1]['date'][:4]}" if rows else '')
    matches = (stats or {}).get('matches')
    head = (f'<header class="pf-fmt-head"><div><p class="eyebrow">{esc(fmt.upper())} CAREER{(" · " + esc(span.replace("-", " to "))) if span else ""}</p>'
            f'<h2 id="{key}-summary">{esc(name)} in {esc(fmt)}s</h2></div>'
            f'<p class="pf-cov{" is-complete" if cov["complete"] else ""}" title="Scorecard coverage of the official career">{esc(coverage_label(cov))}</p></header>')
    body = f'<section class="fmt-panel fmt-{key}" id="{key}" data-fmt-panel="{key}" aria-label="{esc(fmt)} career">'
    body += head
    if stats:
        body += hero_tiles(stats, role, fmt, stat_value, ranks, player.get('gender'))
        body += f'<section class="panel pf-block"><h2>Official {esc(fmt)} record</h2>{official_lines(stats, fmt, stat_value, want_bowling)}</section>'
    else:
        body += '<p class="pf-flag">No official career snapshot is matched for this format. Figures below come from available scorecards only.</p>'
    figures = charts(rows, fmt, name, want_bowling, role)
    if figures:
        body += f'<section class="panel pf-block"><h2>{esc(fmt)} career in charts</h2><div class="pf-charts">{figures}</div></section>'
    form = recent_form(rows, want_bowling)
    if form:
        body += f'<section class="panel pf-block"><h2>Recent {esc(fmt)} form</h2><div class="pf-forms">{form}</div></section>'
    splits = split_section(rows, fmt, name, want_bowling, stats, sum(1 for a in apps if a.get('format') == fmt))
    if splits:
        scope = 'complete career' if cov['complete_batting'] and (not want_bowling or cov['complete_bowling']) else f'{cov["archive_innings"]:,} recorded innings'
        body += f'<section class="panel pf-block pf-splits"><div class="pf-block-head"><h2>{esc(fmt)} record by situation</h2><span class="pill">{esc(scope)}</span></div>{splits}<p class="pf-fine">- not recorded in the scorecards · N/A no dismissals or balls to divide by</p></section>'
    milestones = milestone_lists(rows, fmt, name, stats, want_bowling)
    if milestones:
        body += f'<section class="panel pf-block"><h2>{esc(fmt)} milestones</h2><div class="pf-ms-grid">{milestones}</div></section>'
    best = best_tables(rows, fmt, name, want_bowling)
    if best:
        body += f'<section class="panel pf-block"><h2>Best {esc(fmt)} performances</h2>{best}</section>'
    recent = recent_matches(rows, apps, fmt)
    if recent:
        body += f'<section class="panel pf-block"><h2>Latest {esc(fmt)} matches</h2>{recent}</section>'
    body += '</section>'
    return body


def format_switch(formats, career, extra=None):
    extra = extra or {}
    items = ['<a href="#overview" data-fmt="overview" class="is-active" aria-current="true">Overview</a>']
    for fmt in formats:
        matches = (career.get(fmt) or {}).get('matches')
        count = f'<small>{matches:,}</small>' if matches else ''
        items.append(f'<a href="#{KEYS[fmt]}" data-fmt="{KEYS[fmt]}" class="fmt-{KEYS[fmt]}">{esc(fmt)}{count}</a>')
    if extra.get('switch'):
        items.append(extra['switch'])
    keys = ['overview', 'test', 'odi', 't20i'] + list(extra.get('keys') or [])
    script = ("<script>(function(){var h=(location.hash||'').slice(1).toLowerCase(),d=document.documentElement;d.classList.add('fmt-js');"
              "var ok={" + ','.join(f'{k}:1' for k in keys) + "};if(!ok[h])h='overview';d.dataset.fmt=h;var s=document.currentScript.parentNode;"
              "s.querySelectorAll('[data-fmt]').forEach(function(a){var on=a.dataset.fmt===h;a.classList.toggle('is-active',on);on?a.setAttribute('aria-current','true'):a.removeAttribute('aria-current')});"
              "var st=document.createElement('style');st.id='fmt-boot';st.textContent='.fmt-js .fmt-panel:not(#'+h+'){display:none}';document.head.appendChild(st);})();</script>")
    return f'<nav class="fmt-switch" data-fmt-switch aria-label="Choose a format">{"".join(items)}{script}</nav>'


def format_chips(formats, career, extra_chips=''):
    chips = ''
    for fmt in formats:
        s = career.get(fmt) or {}
        detail = f"{s['matches']:,} {'match' if s['matches'] == 1 else 'matches'}" if s.get('matches') else 'scorecards only'
        chips += f'<a class="pf-chip fmt-{KEYS[fmt]}" href="#{KEYS[fmt]}" data-fmt-link="{KEYS[fmt]}"><i></i><b>{esc(fmt)}</b><span>{detail}</span></a>'
    chips += extra_chips
    return f'<div class="pf-chips">{chips}</div>' if chips else ''


def masthead(player, portrait, badges, role, formats, career, totals, compare_path, extra_chips=''):
    years = ' to '.join(part for part in (player.get('first'), player.get('last')) if part)
    parts = [role, years]
    if totals.get('matches'):
        parts.append(f"{totals['matches']:,} internationals")
    sub = ' · '.join(p for p in parts if p)
    eyebrow = 'PLAYER · ' + ' · '.join(x for x in [' / '.join(player.get('teams') or []).upper(), (player.get('gender') or '').upper()] if x)
    return (f'<header class="pf-mast">{portrait}<div class="pf-id"><p class="eyebrow">{esc(eyebrow)}</p><h1>{esc(player["name"])}</h1>'
            f'<p class="pf-sub">{esc(sub)}</p><div class="pf-teams">{badges}</div>{format_chips(formats, career, extra_chips)}</div></header>')


def overview_hero(totals, career, stat_value, ranks=None, gender=None):
    keeper = sum((s.get('stumpings') or 0) for s in career.values()) >= 5
    spec = [('matches', 'Internationals'), ('runs', 'Runs'), ('hundreds', 'Hundreds'), ('wickets', 'Wickets'), ('catches', 'Catches')]
    if keeper:
        spec.append(('stumpings', 'Stumpings'))
    tiles = ''
    for i, (key, label) in enumerate(spec):
        value = totals.get(key)
        shown = f'{value:,}' if isinstance(value, int) else stat_value(totals, key)
        tiles += f'<div{" class=lead" if i == 0 else ""}><strong>{shown}</strong><span>{label}</span>{rank_note(ranks, "All", key, gender)}</div>'
    return f'<div class="pf-hero pf-hero-all" aria-label="Career totals across formats">{tiles}</div>'


def share_strip(career, formats):
    """Runs and wickets by format as proportional bars."""
    out = ''
    for key, label in (('runs', 'Runs by format'), ('wickets', 'Wickets by format')):
        values = [(fmt, career[fmt].get(key) or 0) for fmt in formats if fmt in career]
        total = sum(v for _, v in values)
        if total <= 0 or sum(v > 0 for _, v in values) < 2 or (key == 'wickets' and total < 20):
            continue
        segs = ''.join(f'<i class="fmt-{KEYS[fmt]}" style="width:{100 * v / total:.2f}%" title="{esc(fmt)}: {v:,}"></i>' for fmt, v in values if v)
        legend = ''.join(f'<span class="fmt-{KEYS[fmt]}"><i></i>{esc(fmt)} <b>{v:,}</b> <small>{100 * v / total:.0f}%</small></span>' for fmt, v in values if v)
        out += f'<div class="pf-share"><span class="pf-share-label">{label}</span><div class="pf-share-bar">{segs}</div><div class="pf-share-legend">{legend}</div></div>'
    return out


def coverage_table(formats, career, rows_by_fmt):
    body = []
    for fmt in formats:
        cov = coverage(career.get(fmt), rows_by_fmt.get(fmt, []))
        first = min((r['date'] for r in rows_by_fmt.get(fmt, [])), default='-')
        last = max((r['date'] for r in rows_by_fmt.get(fmt, [])), default='-')
        status = 'Complete' if cov['complete'] else ('No scorecards' if not cov['matches'] else f"{cov['pct']}%" if cov['pct'] is not None else 'Partial')
        body.append([esc(fmt), n(cov['official_innings']), n(cov['archive_innings']), n(cov['official_bowling_innings']), n(cov['archive_bowling_innings']), esc(first), esc(last), esc(status)])
    return lean_table('Scorecard coverage of the official career', ['Format', ('Official bat inns', 'Official batting innings'), ('In scorecards', 'Batting innings with a scorecard'), ('Official bowl inns', 'Official bowling innings'), ('In scorecards', 'Bowling innings with a scorecard'), ('First', 'First scorecard'), ('Latest', 'Latest scorecard'), 'Coverage'], body, css='pf-coverage', left=(7,))


def overview_panel(player, formats, career, totals, rows_by_fmt, blocks, stat_value, ranks=None):
    """The cross-format view: official tables by format, format cards and the tools."""
    body = '<section class="fmt-panel fmt-overview" id="overview" data-fmt-panel="overview" aria-label="Career overview">'
    if career:
        body += overview_hero(totals, career, stat_value, ranks, player.get('gender'))
    body += '<section class="panel career-tables pf-block" id="career-records"><h2>Career records by format</h2>'
    if blocks['tables']:
        body += blocks['tables']
        if blocks['snapshot']:
            body += f'<p class="pf-fine">Career records checked {esc(blocks["snapshot"])}. Independent of the scorecard archive.</p>'
    else:
        body += '<p class="pf-flag">This archive identity has no matched career record. Do not treat its archive totals as a complete career.</p>'
    body += '</section>'
    body += blocks.get('leagues', '')
    if blocks['glance']:
        body += blocks['glance']
    strip = share_strip(career, formats) if career else ''
    if strip:
        body += f'<section class="panel pf-block"><h2>Where the career sits</h2>{strip}</section>'
    if any(rows_by_fmt.values()):
        body += f'<section class="panel pf-block"><h2>Scorecard coverage</h2>{coverage_table(formats, career, rows_by_fmt)}</section>'
    body += blocks['explorer']
    body += blocks['research']
    body += blocks['recent']
    body += '</section>'
    return body


def profile_body(player, *, portrait, badges, rows, apps, career, totals, blocks, charts, stat_value, compare_path, extra=None, ranks=None):
    """Assemble the whole profile: masthead, format switch, overview and one panel per format.

    `extra` adds competition tabs after the formats: keys, chips, switch items and panels.
    """
    extra = extra or {}
    rows_by_fmt = defaultdict(list)
    for r in rows:
        rows_by_fmt[r['format']].append(r)
    formats = [fmt for fmt in FORMATS if fmt in career or rows_by_fmt.get(fmt)]
    role = role_label(career, rows)
    body = masthead(player, portrait, badges, role, formats, career, totals, compare_path, extra.get('chips', ''))
    body += format_switch(formats, career, extra)
    body += overview_panel(player, formats, career, totals, rows_by_fmt, blocks, stat_value, ranks)
    for fmt in formats:
        body += format_panel(player, fmt, career.get(fmt), rows_by_fmt.get(fmt, []), apps, charts, stat_value, ranks)
    body += extra.get('panels', '')
    body += blocks.get('faq', '')   # questions close the page, below every tab
    return body
