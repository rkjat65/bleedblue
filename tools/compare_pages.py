"""Player comparison pages: two or three careers, format by format, with the best figure marked.

Official career snapshots drive the tables. Available innings power the
year-by-year overlay and the opposition split, and each panel says how much
of the official career those innings cover.
"""
from __future__ import annotations

from collections import defaultdict

from profile_formats import FORMATS, KEYS, coverage, esc, format_switch, lean_table, n, r2, rate, is_bat, is_bowl, bat_totals, bowl_totals
from portraits import portrait_figure

LOWER_BETTER = {'bowlAvg', 'econ', 'bowlSr', 'ducks'}
BAT_METRICS = [('matches', 'Matches'), ('innings', 'Innings'), ('runs', 'Runs'), ('highest_display', 'Highest'), ('avg', 'Average'), ('sr', 'Strike rate'), ('hundreds', 'Hundreds'), ('fifties', 'Fifties'), ('ducks', 'Ducks'), ('fours', 'Fours'), ('sixes', 'Sixes')]
BOWL_METRICS = [('bowling_innings', 'Bowling innings'), ('wickets', 'Wickets'), ('best_bowling', 'Best bowling'), ('bowlAvg', 'Bowling average'), ('econ', 'Economy'), ('bowlSr', 'Bowling strike rate'), ('five_w', 'Five-fors')]
FIELD_METRICS = [('catches', 'Catches'), ('stumpings', 'Stumpings')]
KEY_BAT = ['runs', 'avg', 'sr', 'hundreds', 'fifties']
KEY_BOWL = ['wickets', 'bowlAvg', 'econ', 'bowlSr', 'five_w']
RATE_KEYS = {'avg', 'sr', 'bowlAvg', 'econ', 'bowlSr'}

PAIRS = [
    ('Virat Kohli', 'Rohit Sharma'), ('Sachin Tendulkar', 'Don Bradman'), ('Joe Root', 'Steve Smith'), ('Mithali Raj', 'Meg Lanning'),
    ('Jasprit Bumrah', 'James Anderson'), ('Virat Kohli', 'Sachin Tendulkar'), ('Joe Root', 'Kane Williamson'), ('Steve Smith', 'Kane Williamson'),
    ('Brian Lara', 'Sachin Tendulkar'), ('Shane Warne', 'Muttiah Muralitharan'), ('Ellyse Perry', 'Sophie Devine'), ('Smriti Mandhana', 'Harmanpreet Kaur'),
    ('Amelia Kerr', 'Ellyse Perry'), ('Jhulan Goswami', 'Cathryn Fitzpatrick'), ('Shubman Gill', 'Joe Root'), ('Smriti Mandhana', 'Ellyse Perry'),
    ('Virat Kohli', 'Joe Root', 'Kane Williamson'), ('Sachin Tendulkar', 'Ricky Ponting', 'Kumar Sangakkara'),
]
NAME_HINTS = {'Muttiah Muralitharan': ('Muthiah Muralidaran', 'M Muralitharan', 'M Muralidaran'), 'Steve Smith': ('Steven Smith', 'SPD Smith'), 'Ricky Ponting': ('RT Ponting',), 'Kumar Sangakkara': ('KC Sangakkara',)}


def find_player(people, name):
    for p in people.values():
        if p.get('name') == name and p.get('career'):
            return p
    for alt in NAME_HINTS.get(name, ()):
        for p in people.values():
            if p.get('name') == alt and p.get('career'):
                return p
    return None


def value_text(stats, key):
    v = (stats or {}).get(key)
    if v is None:
        return '<span class="missing">-</span>'
    if key in RATE_KEYS:
        return f'{v:.2f}'
    if isinstance(v, (int, float)):
        return f'{v:,}'
    return esc(v)


def best_index(values, key):
    known = [(i, v) for i, v in enumerate(values) if isinstance(v, (int, float))]
    if len(known) < 2:
        return set()
    pick = min if key in LOWER_BETTER else max
    target = pick(v for _, v in known)
    return {i for i, v in known if v == target}


def compare_table(players, stats_list, metrics, caption):
    """Rows are measures, columns are players; the best figure in each row is marked."""
    body = []
    for key, label in metrics:
        values = [(s or {}).get(key) for s in stats_list]
        if all(v is None for v in values):
            continue
        best = best_index(values, key)
        cells = [esc(label)]
        for i, s in enumerate(stats_list):
            text = value_text(s, key)
            cells.append(f'<span class="cmp-best">{text}</span>' if i in best else text)
        body.append(cells)
    if not body:
        return ''
    return lean_table(caption, ['Measure'] + [p['name'] for p in players], body, css='pf-line cmp-table')


def key_bars(players, stats_list, keys, colours):
    """Normalised bars per measure: each row scales to its own best."""
    out = ''
    labels = dict(BAT_METRICS + BOWL_METRICS + FIELD_METRICS)
    for key in keys:
        values = [(s or {}).get(key) for s in stats_list]
        known = [v for v in values if isinstance(v, (int, float))]
        if len(known) < 2:
            continue
        top = max(known) or 1
        best = best_index(values, key)
        rows = ''
        for i, (p, v) in enumerate(zip(players, values)):
            width = 0 if not isinstance(v, (int, float)) else (v / top * 100 if key not in LOWER_BETTER else max(6, (min(known) / v) * 100 if v else 0))
            rows += (f'<div class="cmp-bar{" is-best" if i in best else ""}"><span>{esc(p["name"])}</span><div class="cw-htrack"><i style="width:{width:.1f}%;background:{colours[i]}"></i></div>'
                     f'<strong>{value_text(stats_list[i], key)}</strong></div>')
        out += f'<div class="cmp-measure"><h3>{esc(labels.get(key, key))}{" · lower is better" if key in LOWER_BETTER else ""}</h3>{rows}</div>'
    return f'<div class="cmp-bars">{out}</div>' if out else ''


def opposition_table(players, rows_list, fmt):
    """Batting average and innings against each opponent, players as columns."""
    per = []
    opponents = set()
    for rows in rows_list:
        groups = defaultdict(list)
        for r in rows:
            if is_bat(r) and r.get('opponent'):
                groups[r['opponent']].append(r)
        per.append(groups)
        opponents.update(k for k, v in groups.items() if len(v) >= 3)
    if not opponents:
        return ''
    body = []
    for opp in sorted(opponents, key=lambda o: -sum(len(g.get(o, [])) for g in per)):
        cells = [esc(opp)]
        avgs = []
        for groups in per:
            t = bat_totals(groups.get(opp, []))
            avgs.append(t['avg'] if t['innings'] >= 3 else None)
        best = best_index(avgs, 'avg')
        for i, groups in enumerate(per):
            t = bat_totals(groups.get(opp, []))
            if not t['innings']:
                cells.append('<span class="missing">-</span>')
                continue
            text = f"{r2(t['avg'], t['outs'])} <small>{t['runs'] if t['runs'] is not None else '-'} r · {t['innings']} inns</small>"
            cells.append(f'<span class="cmp-best">{text}</span>' if i in best else text)
        body.append(cells)
    return lean_table(f'{fmt} batting average by opponent', ['Opponent'] + [p['name'] for p in players], body[:14], css='cmp-table cmp-opp')


def masthead(players, formats, title):
    genders = sorted({(p.get('gender') or '').upper() for p in players if p.get('gender')})
    eyebrow = ' · '.join(['PLAYER COMPARISON'] + genders)
    fmt_text = ', '.join(formats[:-1]) + (' and ' if len(formats) > 1 else '') + formats[-1] if formats else 'International'
    sub = f"{fmt_text} careers side by side: official records first, recorded innings for year-by-year and opposition views."
    actions = '<div class="actions pf-actions"><a class="button primary" href="/compare/">Choose players</a><button data-save>Save page</button><button data-share>Share link</button><button data-csv>Download table CSV</button></div>'
    return f'<header class="pf-mast cmp-mast"><div class="pf-id"><p class="eyebrow">{esc(eyebrow)}</p><h1>{esc(title)}</h1><p class="pf-sub">{esc(sub)}</p>{actions}</div></header>'


def identity_strip(players, pp, portraits, illustrations):
    cards = ''
    for i, p in enumerate(players):
        spans = [s.get('span') for s in p['career'].values() if s.get('span')]
        first = min((s.split('-')[0] for s in spans), default='')
        last = max((s.split('-')[-1] for s in spans), default='')
        art = portrait_figure(p['id'], p['name'], portraits, compact=True, illustration=illustrations.get(p['name']))
        cards += (f'<a class="cmp-id" href="{esc(pp[p["id"]])}" style="--who:var(--cmp-{i})">{art}<strong>{esc(p["name"])}</strong>'
                  f'<small>{esc(" / ".join(p.get("teams") or []))}{(" · " + first + " to " + last) if first else ""}</small></a>')
        if i < len(players) - 1:
            cards += '<span class="cmp-vs" aria-hidden="true">VS</span>'
    return f'<div class="cmp-identity cmp-{len(players)}">{cards}</div>'


def faq_items(players, fmt_list):
    items = []
    for fmt in fmt_list:
        stats = [p['career'].get(fmt) or {} for p in players]
        if all((s.get('wickets') or 0) >= 20 for s in stats):
            key, word = 'wickets', 'wickets'
        elif all(s.get('runs') is not None for s in stats):
            key, word = 'runs', 'runs'
        else:
            continue
        ranked = sorted(zip(players, stats), key=lambda x: -(x[1].get(key) or 0))
        names = ' or '.join(p['name'] for p in players)
        answer = f"{ranked[0][0]['name']} has the most recorded {fmt} {word}: " + ', '.join(f"{p['name']} {s.get(key):,}" for p, s in ranked) + '.'
        items.append((f'Who has more {fmt} {word}, {names}?', answer))
    return items[:6]


def compare_body(players, rows_by_pid, pp, portraits, illustrations, stat_value=None):
    names = [p['name'] for p in players]
    formats = [f for f in FORMATS if any(f in p['career'] for p in players)]
    colours = ['var(--cmp-0)', 'var(--cmp-1)', 'var(--cmp-2)']
    title = ' vs '.join(names)
    body = masthead(players, formats, title) + identity_strip(players, pp, portraits, illustrations)
    body += format_switch(formats, {f: {} for f in formats})
    # Overview: every format at a glance
    body += '<section class="fmt-panel fmt-overview" id="overview" data-fmt-panel="overview" aria-label="Overview">'
    glance = []
    for fmt in formats:
        stats = [p['career'].get(fmt) for p in players]
        for key, label in (('matches', 'Matches'), ('runs', 'Runs'), ('avg', 'Average'), ('sr', 'Strike rate'), ('hundreds', 'Hundreds'), ('wickets', 'Wickets'), ('bowlAvg', 'Bowling average'), ('econ', 'Economy')):
            values = [(s or {}).get(key) for s in stats]
            if all(v is None for v in values) or (key in ('wickets', 'bowlAvg', 'econ') and not any(((s or {}).get('wickets') or 0) >= 10 for s in stats)):
                continue
            best = best_index(values, key)
            glance.append([f'<a href="#{KEYS[fmt]}" data-fmt-link="{KEYS[fmt]}" class="fmt-{KEYS[fmt]} cmp-fmt-link">{fmt}</a> · {label}'] + [f'<span class="cmp-best">{value_text(s, key)}</span>' if i in best else value_text(s, key) for i, s in enumerate(stats)])
    body += f'<section class="panel pf-block" id="career-records"><h2>Career records by format</h2>{lean_table("Official careers side by side", ["Format · measure"] + names, glance, css="pf-line cmp-table")}</section>'
    items = faq_items(players, formats)
    if items:
        body += '<section class="panel pf-block player-faq" id="player-questions"><h2>Questions fans ask</h2><dl>' + ''.join(f'<div><dt>{esc(q)}</dt><dd>{esc(a)}</dd></div>' for q, a in items) + '</dl></section>'
    body += '<p class="pf-links">' + ' · '.join(f'<a href="{esc(pp[p["id"]])}">{esc(p["name"])} profile</a>' for p in players) + f' · <a href="/compare/#filters={"&".join(f"{k}={pp[p["id"]]}" for k, p in zip("abc", players))}">Open in the comparison tool</a></p>'
    body += '</section>'
    # One panel per format
    for fmt in formats:
        key = KEYS[fmt]
        stats = [p['career'].get(fmt) for p in players]
        present = [p for p, s in zip(players, stats) if s]
        rows_list = [[r for r in rows_by_pid.get(p['id'], []) if r['format'] == fmt] for p in players]
        bowl_focus = all(((s or {}).get('wickets') or 0) >= 25 for s in stats)
        body += f'<section class="fmt-panel fmt-{key}" id="{key}" data-fmt-panel="{key}" aria-label="{esc(fmt)} comparison">'
        missing = [p['name'] for p, s in zip(players, stats) if not s]
        body += f'<header class="pf-fmt-head"><div><p class="eyebrow">{esc(fmt.upper())} CAREERS</p><h2>{esc(title)} in {esc(fmt)}s</h2></div>' + (f'<p class="pf-cov">{esc(", ".join(missing))} did not play {esc(fmt)}s</p>' if missing else '') + '</header>'
        tiles = ''
        for i, (p, s) in enumerate(zip(players, stats)):
            if not s:
                continue
            spec = [('wickets', 'Wickets'), ('bowlAvg', 'Average'), ('econ', 'Economy'), ('five_w', 'Five-fors')] if bowl_focus else [('runs', 'Runs'), ('avg', 'Average'), ('sr', 'Strike rate'), ('hundreds', 'Hundreds')]
            cells = ''.join(f'<div><strong>{value_text(s, k)}</strong><span>{label}</span></div>' for k, label in spec)
            tiles += f'<div class="cmp-tiles" style="--who:var(--cmp-{i})"><h3><a href="{esc(pp[p["id"]])}">{esc(p["name"])}</a><small>{esc(s.get("span") or "")} · {n(s.get("matches"))} matches</small></h3><div class="cmp-tile-row">{cells}</div></div>'
        body += f'<div class="cmp-tile-grid cmp-{len(players)}">{tiles}</div>'
        body += f'<section class="panel pf-block"><h2>{esc(fmt)} measures side by side</h2>{key_bars(players, stats, KEY_BOWL + KEY_BAT[:2] if bowl_focus else KEY_BAT + [k for k in KEY_BOWL[:2] if any(((s or {}).get("wickets") or 0) >= 10 for s in stats)], colours)}'
        body += compare_table(players, stats, BAT_METRICS + BOWL_METRICS + FIELD_METRICS, f'{fmt} official career records') + '</section>'
        from cricket_charts import cumulative_overlay
        overlay = cumulative_overlay([(p['name'], rows, colours[i]) for i, (p, rows) in enumerate(zip(players, rows_list))], 'wickets' if bowl_focus else 'runs', f'{fmt} {"wickets" if bowl_focus else "runs"} by year, cumulative')
        covs = ' · '.join(f"{p['name']}: {coverage(s, rows)['archive_innings']:,} of {n((s or {}).get('innings'))} innings" for p, s, rows in zip(players, stats, rows_list) if s)
        opp = opposition_table(players, rows_list, fmt) if not bowl_focus else ''
        if overlay or opp:
            body += f'<section class="panel pf-block"><div class="pf-block-head"><h2>{esc(fmt)} year by year and by opponent</h2><span class="pill">recorded innings</span></div>{overlay}{opp}<p class="pf-fine">Scorecard coverage · {esc(covs)}</p></section>'
        body += '</section>'
    description = f'{title}: ' + '; '.join(f"{fmt} runs " + ' v '.join(f"{(p['career'].get(fmt) or {}).get('runs') or 0:,}" for p in players) for fmt in formats[:2]) + '. Official careers by format, year-by-year overlay and opposition splits.'
    return body, items, description[:158]


def comparison_cards(entries):
    """entries: [(path, names, blurb)] for the compare index."""
    return '<div class="grid three">' + ''.join(f'<a class="feature-card" href="{esc(path)}"><span>CAREER COMPARISON</span><h2>{esc(" vs ".join(names))}</h2><p>{esc(blurb)}</p></a>' for path, names, blurb in entries) + '</div>'
