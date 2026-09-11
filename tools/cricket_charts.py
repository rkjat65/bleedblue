"""Server-rendered cricket analytics charts.

Missing inputs stay missing. These pictures describe published scorecards
and career snapshots, never inferred ball tracking or wagon-wheel geometry.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal, ROUND_DOWN
import html
import math

PHASES = {
    'T20I': ((1, 6, 'Powerplay'), (7, 16, 'Middle overs'), (17, 99, 'Death overs')),
    'ODI': ((1, 10, 'Powerplay'), (11, 40, 'Middle overs'), (41, 99, 'Death overs')),
}


def _esc(value):
    return html.escape(str(value if value is not None else ''), quote=True)


def _n(value):
    if value is None:
        return 'not recorded'
    if isinstance(value, float):
        return f'{value:.2f}'
    return f'{value:,}' if isinstance(value, int) else str(value)


def _rate(top, bottom, factor=1):
    if top is None or bottom is None or bottom <= 0:
        return None
    return float((Decimal(top) * factor / Decimal(bottom)).quantize(Decimal('.01'), rounding=ROUND_DOWN))


def _svg(width, height, inner, label):
    return f'<svg class="cw-svg" viewBox="0 0 {width} {height}" role="img" aria-label="{_esc(label)}" preserveAspectRatio="xMidYMid meet">{inner}</svg>'


def figure(caption, aria, body, note=''):
    if not body:
        return ''
    note_html = f'<p class="note">{_esc(note)}</p>' if note else ''
    return f'<figure class="cw-figure"><figcaption>{_esc(caption)}</figcaption>{body}{note_html}</figure>'


def _ticks(maximum, count=4):
    if maximum <= 0:
        return [0]
    step = max(1, int(math.ceil(maximum / count)))
    # Prefer round cricket scores: 50, 100, 150...
    magnitude = 10 ** max(0, len(str(step)) - 1)
    nice = max(magnitude, int(math.ceil(step / magnitude) * magnitude))
    values = list(range(0, int(maximum) + nice, nice))
    return values[: count + 2] or [0, int(maximum)]


def _polyline(points):
    return ' '.join(f'{x:.1f},{y:.1f}' for x, y in points)


def worm(innings, target=None):
    """Cumulative runs against overs, with wickets marked on the line."""
    series = []
    for inn in innings:
        overs = [o for o in inn.get('overs') or [] if o.get('total') is not None]
        if not overs:
            continue
        points = [(0, 0)] + [(o['over'], o['total']) for o in overs]
        wickets = [(o['over'], o['total'], o.get('wickets') or 0) for o in overs if o.get('wickets')]
        series.append((inn.get('team') or f'Innings {len(series)+1}', points, wickets))
    if not series:
        return ''
    max_over = max(p[0] for _, points, _ in series for p in points)
    max_runs = max(p[1] for _, points, _ in series for p in points)
    if target:
        max_runs = max(max_runs, target)
    max_over = max(max_over, 1)
    max_runs = max(max_runs, 1)
    left, right, top, bottom = 42, 686, 18, 196
    plot_w, plot_h = right - left, bottom - top

    def xy(over, runs):
        return left + over / max_over * plot_w, bottom - runs / max_runs * plot_h

    grid = ''
    for value in _ticks(max_runs):
        if value > max_runs:
            continue
        x, y = xy(0, value)
        grid += f'<line class="cw-grid" x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}"/><text class="cw-axis" x="{left-6}" y="{y+3:.1f}" text-anchor="end">{value}</text>'
    for value in _ticks(max_over, 5):
        if value > max_over:
            continue
        x, y = xy(value, 0)
        grid += f'<line class="cw-grid" x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bottom}"/><text class="cw-axis" x="{x:.1f}" y="{bottom+14}" text-anchor="middle">{value}</text>'
    paths = ''
    dots = ''
    legend = ''
    for index, (team, points, wickets) in enumerate(series[:4]):
        cls = f'cw-c{index}'
        mapped = [xy(o, r) for o, r in points]
        paths += f'<polyline class="cw-line {cls}" fill="none" points="{_polyline(mapped)}"/>'
        for over, runs, count in wickets:
            x, y = xy(over, runs)
            for n in range(min(count, 3)):
                dots += f'<circle class="cw-wicket" cx="{x:.1f}" cy="{y-n*5:.1f}" r="3.4"/>'
        legend += f'<span class="cw-key"><i class="{cls}"></i>{_esc(team)}</span>'
    target_line = ''
    if target:
        x1, y1 = xy(0, target)
        x2, y2 = xy(max_over, target)
        target_line = f'<line class="cw-target" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/><text class="cw-axis" x="{right}" y="{y1-5:.1f}" text-anchor="end">Target {_n(target)}</text>'
    svg = _svg(720, 228, f'<rect class="cw-plot" x="{left}" y="{top}" width="{plot_w}" height="{plot_h}"/>{grid}{target_line}{paths}{dots}<text class="cw-axis" x="360" y="222" text-anchor="middle">Overs</text>', 'Worm chart of cumulative runs by over')
    return figure('Worm · cumulative runs by over', 'Worm chart of cumulative innings totals', svg + f'<div class="cw-legend">{legend}<span class="cw-key"><i class="cw-wicket"></i>Wicket</span></div>', 'Each point is the innings total at the end of that over. Dots mark wickets in the over. The picture uses recorded over totals only.')


def manhattan(inn, title=None):
    """Runs scored in each over, with wickets as ticks on the bar."""
    overs = [o for o in inn.get('overs') or [] if o.get('runs') is not None]
    if len(overs) < 2:
        return ''
    peak = max(max(o['runs'] for o in overs), 1)
    width = max(720, len(overs) * 10)
    left, right, top, bottom = 36, width - 12, 14, 168
    plot_w, plot_h = right - left, bottom - top
    slot = plot_w / len(overs)
    bar_w = max(2, slot * 0.72)
    bars = ''
    for i, over in enumerate(overs):
        h = over['runs'] / peak * plot_h
        x = left + i * slot + (slot - bar_w) / 2
        y = bottom - h
        wkts = over.get('wickets') or 0
        bars += f'<rect class="cw-man-bar{" cw-man-w" if wkts else ""}" x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{max(h, 1):.1f}"/>'
        for n in range(min(wkts, 4)):
            bars += f'<circle class="cw-wicket" cx="{x+bar_w/2:.1f}" cy="{y-5-n*6:.1f}" r="2.6"/>'
    labels = ''
    step = max(1, len(overs) // 10)
    for i, over in enumerate(overs):
        if i % step == 0 or i == len(overs) - 1:
            x = left + i * slot + slot / 2
            labels += f'<text class="cw-axis" x="{x:.1f}" y="{bottom+14}" text-anchor="middle">{over["over"]}</text>'
    grid = ''
    for value in _ticks(peak, 3):
        if value > peak:
            continue
        y = bottom - value / peak * plot_h
        grid += f'<line class="cw-grid" x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}"/><text class="cw-axis" x="{left-6}" y="{y+3:.1f}" text-anchor="end">{value}</text>'
    team = inn.get('team') or 'Innings'
    caption = title or f'Manhattan · {team} runs per over'
    svg = _svg(width, 196, f'<rect class="cw-ground" x="{left}" y="{top}" width="{plot_w}" height="{plot_h}"/>{grid}{bars}{labels}', caption)
    return f'<div class="cw-scroll" tabindex="0">{figure(caption, caption, svg, "Bar height is runs in that over. Dots above a bar are wickets in the over.")}</div>'


def partnerships(inn):
    fall = [w for w in (inn.get('fall') or []) if w.get('runs') is not None and w.get('wicket') is not None]
    if not fall:
        return ''
    fall = sorted(fall, key=lambda w: (w['wicket'], w['runs']))
    rows = []
    previous = 0
    for wicket in fall:
        added = wicket['runs'] - previous
        if added < 0:
            return ''
        label = f"{wicket['wicket']}{({1:'st',2:'nd',3:'rd'}.get(wicket['wicket'],'th'))} wicket"
        rows.append((label, added, wicket.get('player') or ''))
        previous = wicket['runs']
    total = inn.get('runs')
    if total is not None and total > previous:
        rows.append(('Unbroken stand', total - previous, ''))
    peak = max((runs for _, runs, _ in rows), default=0)
    if peak <= 0:
        return ''
    bars = ''
    for label, runs, player in rows:
        width = runs / peak * 100
        who = f' · {_esc(player)}' if player else ''
        bars += f'<div class="cw-hbar"><span>{label}{who}</span><div class="cw-htrack"><i style="width:{width:.2f}%"></i></div><strong>{runs}</strong></div>'
    team = inn.get('team') or 'Innings'
    return figure(f'Partnerships · {team}', f'Partnership runs for {team}', bars, 'Stands are the runs added between recorded falls of wicket. An unbroken stand is the remainder after the last fall.')


def phases(inn, fmt):
    bands = PHASES.get(fmt)
    overs = [o for o in inn.get('overs') or [] if o.get('runs') is not None and o.get('over')]
    if not bands or not overs:
        return ''
    rows = []
    for start, end, label in bands:
        chunk = [o for o in overs if start <= o['over'] <= end]
        if not chunk and start > max(o['over'] for o in overs):
            continue
        runs = sum(o['runs'] for o in chunk)
        wickets = sum(o.get('wickets') or 0 for o in chunk)
        balls = len(chunk)
        rows.append((label, runs, wickets, balls))
    if not rows or not any(r[1] or r[2] for r in rows):
        return ''
    peak = max(max(r[1] for r in rows), 1)
    bars = ''
    for label, runs, wickets, balls in rows:
        bars += f'<div class="cw-phase"><div class="cw-phase-head"><strong>{_esc(label)}</strong><span>{runs} runs · {wickets} wkts · {balls} overs</span></div><div class="cw-htrack"><i style="width:{runs/peak*100:.2f}%"></i></div></div>'
    return figure(f'Phases · {inn.get("team") or "innings"}', 'Runs and wickets by innings phase', bars, 'Limited-overs phases use recorded overs only. A short innings simply has fewer death overs.')


def scoring_mix(batting, caption='Scoring mix'):
    if not batting or not all(b.get('runs') is not None and b.get('fours') is not None and b.get('sixes') is not None for b in batting):
        return ''
    runs = sum(b['runs'] for b in batting)
    fours = 4 * sum(b['fours'] for b in batting)
    sixes = 6 * sum(b['sixes'] for b in batting)
    if fours + sixes > runs:
        return ''
    other = runs - fours - sixes
    return donut([('Fours', fours, 'cw-c0'), ('Sixes', sixes, 'cw-c1'), ('Other runs', other, 'cw-c2')], caption, 'Boundary runs are 4 x fours + 6 x sixes. Other runs are the remainder of recorded batter runs. Extras are not in this mix.')


def donut(parts, caption, note=''):
    parts = [(label, value, cls) for label, value, cls in parts if value]
    total = sum(value for _, value, _ in parts)
    if total <= 0 or len(parts) < 2:
        return ''
    cx, cy, outer, inner = 84, 84, 72, 40
    angle = -math.pi / 2
    paths = ''
    legend = ''
    for label, value, cls in parts:
        sweep = value / total * 2 * math.pi
        if abs(sweep - 2 * math.pi) < 1e-9:
            paths += f'<circle class="{cls}" cx="{cx}" cy="{cy}" r="{(outer+inner)/2:.1f}" fill="none" stroke-width="{outer-inner}"/>'
        else:
            def pt(radius, theta):
                return cx + radius * math.cos(theta), cy + radius * math.sin(theta)
            x1, y1 = pt(outer, angle)
            x2, y2 = pt(outer, angle + sweep)
            x3, y3 = pt(inner, angle + sweep)
            x4, y4 = pt(inner, angle)
            large = 1 if sweep > math.pi else 0
            paths += f'<path class="cw-slice {cls}" d="M{x1:.1f} {y1:.1f} A{outer} {outer} 0 {large} 1 {x2:.1f} {y2:.1f} L{x3:.1f} {y3:.1f} A{inner} {inner} 0 {large} 0 {x4:.1f} {y4:.1f} Z"/>'
        share = 100 * value / total
        legend += f'<div><i class="{cls}"></i><span>{_esc(label)}</span><strong>{_n(value)} · {share:.1f}%</strong></div>'
        angle += sweep
    svg = _svg(168, 168, paths, caption)
    return figure(caption, caption, f'<div class="cw-donut">{svg}<div class="cw-donut-legend">{legend}</div></div>', note)


def form_strip(rows, key='runs', caption='Recent recorded innings'):
    sample = [r for r in rows if r.get(key) is not None][-20:]
    if len(sample) < 3:
        return ''
    if key == 'wickets' and sum(1 for r in sample if r[key] > 0) < 3:
        return ''
    peak = max(max(r[key] for r in sample), 1)
    bars = ''
    for row in sample:
        value = row[key]
        kind = ''
        if key == 'runs':
            kind = 'hundred' if value >= 100 else 'fifty' if value >= 50 else 'duck' if value == 0 else ''
        elif key == 'wickets':
            kind = 'five' if value >= 5 else 'wicket' if value > 0 else 'duck'
        notout = ' notout' if key == 'runs' and row.get('out') is False else ''
        height = max(6, value / peak * 100)
        mark = f'{value}{"*" if notout else ""}'
        title = f"{row.get('date','')} · {row.get('opponent') or row.get('format') or ''} · {mark}"
        bars += f'<i class="{kind}{notout}" style="height:{height:.1f}%" title="{_esc(title)}"></i>'
    unit = 'runs' if key == 'runs' else 'wickets'
    return figure(caption, caption, f'<div class="cw-form" role="img" aria-label="{_esc(caption)}">{bars}</div><div class="cw-form-key"><span class="duck">0</span><span>1-49</span><span class="fifty">50-99</span><span class="hundred">100+</span></div>' if key == 'runs' else f'<div class="cw-form" role="img" aria-label="{_esc(caption)}">{bars}</div>', f'Each bar is one innings, oldest on the left. Height is {unit}. A hollow bar is a not-out.' if key == 'runs' else f'Each bar is one bowling innings. Height is {unit}.')


def trajectory(rows, key='runs', caption='Career trajectory in this archive'):
    batting = [r for r in sorted(rows, key=lambda r: (r.get('date') or '', r.get('match') or '')) if r.get(key) is not None]
    if len(batting) < 4:
        return ''
    yearly = []
    by_year = defaultdict(int)
    for row in batting:
        by_year[row['date'][:4]] += row[key]
    running = 0
    for year in sorted(by_year):
        running += by_year[year]
        yearly.append((year, running, by_year[year]))
    peak = max(y[1] for y in yearly)
    if peak <= 0:
        return ''
    left, right, top, bottom = 48, 686, 16, 168
    plot_w, plot_h = right - left, bottom - top
    n = max(len(yearly) - 1, 1)

    def xy(i, value):
        return left + i / n * plot_w, bottom - value / peak * plot_h

    points = [xy(i, value) for i, (_, value, _) in enumerate(yearly)]
    area = _polyline([(left, bottom)] + points + [(points[-1][0], bottom)])
    line = _polyline(points)
    grid = ''
    for value in _ticks(peak):
        if value > peak:
            continue
        y = bottom - value / peak * plot_h
        grid += f'<line class="cw-grid" x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}"/><text class="cw-axis" x="{left-6}" y="{y+3:.1f}" text-anchor="end">{_n(value)}</text>'
    labels = ''
    step = max(1, len(yearly) // 6)
    for i, (year, _, _) in enumerate(yearly):
        if i % step == 0 or i == len(yearly) - 1:
            x, y = xy(i, 0)
            labels += f'<text class="cw-axis" x="{x:.1f}" y="{bottom+14}" text-anchor="middle">{year}</text>'
    svg = _svg(720, 196, f'{grid}<polygon class="cw-area" points="{area}"/><polyline class="cw-line cw-c0" fill="none" points="{line}"/>{labels}', caption)
    return figure(caption, caption, svg, f'Running total of recorded {key} by calendar year in available scorecards. Years without a recorded {key} do not add to the line.')


def dismissals(rows):
    kinds = Counter()
    known = 0
    for row in rows:
        if row.get('runs') is None and row.get('position') is None:
            continue
        if row.get('out') is False:
            kinds['Not out'] += 1
            known += 1
        elif row.get('out') is True:
            text = (row.get('dismissal') or '').lower()
            label = next((name for name in ('caught and bowled', 'caught', 'bowled', 'lbw', 'run out', 'stumped', 'hit wicket') if text.startswith(name)), 'Other dismissal')
            kinds[label] += 1
            known += 1
        else:
            kinds['Not recorded'] += 1
    if known < 5:
        return ''
    labels = {
        'caught': 'Caught', 'bowled': 'Bowled', 'lbw': 'LBW', 'run out': 'Run out',
        'stumped': 'Stumped', 'caught and bowled': 'Caught and bowled', 'hit wicket': 'Hit wicket',
        'Other dismissal': 'Other dismissal', 'Not out': 'Not out', 'Not recorded': 'Not recorded',
    }
    palette = {
        'caught': 'cw-c0', 'bowled': 'cw-c1', 'lbw': 'cw-c2', 'run out': 'cw-c3',
        'stumped': 'cw-c4', 'caught and bowled': 'cw-c6', 'hit wicket': 'cw-c7',
        'Other dismissal': 'cw-c5', 'Not out': 'cw-c8', 'Not recorded': 'cw-c5',
    }
    parts = [(labels[k], kinds[k], palette[k]) for k in labels if kinds.get(k)]
    return donut(parts, 'How innings ended', 'Dismissals use the wording on the scorecard. Not recorded stays a separate slice; it is never treated as not out.')


def batting_order(rows):
    groups = defaultdict(list)
    for row in rows:
        pos = row.get('position')
        if pos and row.get('runs') is not None:
            groups[int(pos)].append(row)
    if sum(len(v) for v in groups.values()) < 6:
        return ''
    peak = max((sum(r['runs'] for r in sample) for sample in groups.values()), default=1) or 1
    cells = ''
    for pos in range(1, 12):
        sample = groups.get(pos, [])
        inns = len(sample)
        runs = sum(r['runs'] for r in sample) if sample else 0
        avg = _rate(runs, sum(1 for r in sample if r.get('out')) if sample and all(r.get('out') is not None for r in sample) else None)
        fill = runs / peak * 100 if sample else 0
        cells += f'<div class="cw-order-cell" title="Position {pos}: {inns} innings, {runs} runs"><span>{pos}</span><strong>{_n(avg) if avg is not None else (inns or "-")}</strong><i style="height:{fill:.1f}%"></i><small>{inns} inns</small></div>'
    return figure('Batting order in this archive', 'Runs and average by batting position', f'<div class="cw-order">{cells}</div>', 'Average is runs divided by recorded dismissals at that position. A dash in the average means dismissals were not fully recorded.')


def result_split(rows):
    groups = [('Won', []), ('Lost', []), ('Draw / tie / no result', [])]
    for row in rows:
        if row.get('runs') is None:
            continue
        result = row.get('result') or ''
        if result == 'Won':
            groups[0][1].append(row)
        elif result == 'Lost':
            groups[1][1].append(row)
        else:
            groups[2][1].append(row)
    bars = []
    for label, sample in groups:
        if not sample:
            continue
        runs = sum(r['runs'] for r in sample)
        outs = sum(1 for r in sample if r.get('out')) if all(r.get('out') is not None for r in sample) else None
        bars.append((f'{label} · {len(sample)} inns', _rate(runs, outs)))
    if len(bars) < 2 or all(v is None for _, v in bars):
        return ''
    return hbars(bars, 'Batting average by match result', 'Average uses recorded dismissals in each result group. Draw, tie and no-result sit together because none of them is a win or a loss.')


def hbars(items, caption, note=''):
    values = [v for _, v in items if v is not None]
    if not values:
        return ''
    peak = max(values)
    if peak <= 0:
        return ''
    rows = ''
    for label, value in items:
        width = 0 if value is None else value / peak * 100
        rows += f'<div class="cw-hbar"><span>{_esc(label)}</span><div class="cw-htrack"><i style="width:{width:.2f}%"></i></div><strong>{_n(value)}</strong></div>'
    return figure(caption, caption, rows, note)


def bowling_spells(bowling, people=None):
    rows = [b for b in bowling or [] if b.get('wickets') is not None and b.get('runs') is not None]
    if len(rows) < 2:
        return ''
    rows = sorted(rows, key=lambda b: (-(b['wickets'] or 0), b['runs']))[:8]
    peak = max(max(b['wickets'] or 0 for b in rows), 1)
    bars = ''
    for b in rows:
        name = (people or {}).get(b.get('id'), {}).get('name') or b.get('name') or 'Bowler'
        econ = _rate(b['runs'], b.get('balls'), 6)
        width = (b['wickets'] or 0) / peak * 100
        bars += f'<div class="cw-hbar"><span>{_esc(name)}</span><div class="cw-htrack"><i class="cw-bowl" style="width:{max(width, 2):.2f}%"></i></div><strong>{b["wickets"]}/{b["runs"]}{(" · "+_n(econ)) if econ is not None else ""}</strong></div>'
    return figure('Bowling spells · wickets, with economy', 'Bowling figures by wickets', bars, 'Bar length is wickets. The label is wickets/runs and economy when legal balls are recorded.')


def butterfly(left, right, rows, caption='Side-by-side comparison'):
    usable = [(label, a, b) for label, a, b in rows if a is not None or b is not None]
    if not usable:
        return ''
    body = f'<div class="cw-fly-head"><span>{_esc(left)}</span><span>{_esc(right)}</span></div>'
    for label, a, b in usable:
        peak = max([v for v in (a, b) if v is not None] + [0.01])
        left_w = 0 if a is None else a / peak * 100
        right_w = 0 if b is None else b / peak * 100
        body += f'<div class="cw-fly-row"><div class="cw-fly-l"><strong>{_n(a)}</strong><div class="cw-htrack cw-htrack-rev"><i style="width:{left_w:.2f}%"></i></div></div><span>{_esc(label)}</span><div class="cw-fly-r"><div class="cw-htrack"><i class="cw-c1" style="width:{right_w:.2f}%"></i></div><strong>{_n(b)}</strong></div></div>'
    return figure(caption, caption, body, 'Each row has its own scale. Bar length compares the two values for that metric only, not an overall ranking.')


def win_share(left, right, wins_left, wins_right, other, caption=None):
    total = (wins_left or 0) + (wins_right or 0) + (other or 0)
    if total <= 0:
        return ''
    caption = caption or f'{left} vs {right} · result share'
    segs = [(left, wins_left or 0, 'cw-c0'), (right, wins_right or 0, 'cw-c1'), ('Other', other or 0, 'cw-c5')]
    bars = ''.join(f'<i class="{cls}" style="width:{value/total*100:.2f}%" title="{_esc(label)}: {value}"></i>' for label, value, cls in segs if value)
    legend = ''.join(f'<span class="cw-key"><i class="{cls}"></i>{_esc(label)} {_n(value)} ({value/total*100:.1f}%)</span>' for label, value, cls in segs)
    return figure(caption, caption, f'<div class="cw-stack" role="img" aria-label="{_esc(caption)}">{bars}</div><div class="cw-legend">{legend}</div>', 'Other groups draws, ties and matches with no winner recorded.')


def leader_bars(items, caption, unit='', minimum=3):
    items = [(name, value) for name, value in items if value is not None][:12]
    if len(items) < minimum:
        return ''
    peak = max(v for _, v in items)
    if peak <= 0:
        return ''
    rows = ''
    for rank, (name, value) in enumerate(items, 1):
        rows += f'<div class="cw-hbar cw-lead"><span><b>{rank}</b> {_esc(name)}</span><div class="cw-htrack"><i style="width:{value/peak*100:.2f}%"></i></div><strong>{_n(value)}{html.escape(unit)}</strong></div>'
    return figure(caption, caption, rows)


def result_decades(matches, team):
    buckets = defaultdict(lambda: [0, 0, 0])
    for match in matches:
        decade = match['date'][:3] + '0'
        winner = match.get('outcome', {}).get('winner')
        if winner == team:
            buckets[decade][0] += 1
        elif winner:
            buckets[decade][1] += 1
        else:
            buckets[decade][2] += 1
    if len(buckets) < 3:
        return ''
    decades = sorted(buckets)
    peak = max(sum(buckets[d]) for d in decades)
    cols = ''
    for decade in decades:
        won, lost, other = buckets[decade]
        total = won + lost + other
        h = max(6, total / peak * 128)
        cols += f'<div class="cw-stack-col" title="{decade}s: {won} wins, {lost} losses, {other} other"><div class="cw-stack-v" style="height:{h:.0f}px"><i class="cw-c0" style="flex:{max(won,0)}"></i><i class="cw-c1" style="flex:{max(lost,0)}"></i><i class="cw-c5" style="flex:{max(other,0)}"></i></div><span>{decade}s</span></div>'
    return figure(f'{team} results by decade', f'{team} wins, losses and other results by decade', f'<div class="cw-stack-chart" role="img">{cols}</div><div class="cw-legend"><span class="cw-key"><i class="cw-c0"></i>Wins</span><span class="cw-key"><i class="cw-c1"></i>Losses</span><span class="cw-key"><i class="cw-c5"></i>Other</span></div>', 'Column height is matches in that decade. Segments are wins, losses and other outcomes. The current decade is incomplete.')


def match_lab(card):
    innings = [inn for inn in card.get('innings') or [] if not inn.get('super_over')]
    with_overs = [inn for inn in innings if inn.get('overs')]
    if not with_overs and not any(inn.get('fall') for inn in innings):
        return ''
    fmt = card.get('match', {}).get('format', '')
    target = None
    if len(with_overs) == 2 and fmt in ('ODI', 'T20I') and with_overs[0].get('runs') is not None:
        target = with_overs[0]['runs'] + 1
    body = '<section class="cw-lab" id="match-charts"><div class="cw-lab-head"><p class="eyebrow">MATCH PICTURE</p><h2>Worm, Manhattan and the stands that built the innings</h2><p class="muted">These are the pictures used to read a cricket match: how the total grew, where the overs leaked or exploded, and which wickets hurt.</p></div>'
    body += worm(with_overs, target)
    if with_overs:
        body += '<div class="cw-lab-grid">' + ''.join(manhattan(inn) for inn in with_overs) + '</div>'
        phase_html = ''.join(phases(inn, fmt) for inn in with_overs)
        if phase_html:
            body += '<div class="cw-lab-grid">' + phase_html + '</div>'
    stands = ''.join(partnerships(inn) for inn in innings)
    if stands:
        body += '<div class="cw-lab-grid">' + stands + '</div>'
    mixes = ''.join(scoring_mix(inn.get('batting') or [], f'Scoring mix · {inn.get("team") or "innings"}') for inn in innings)
    spells = ''.join(bowling_spells(inn.get('bowling') or []) for inn in innings)
    extras = mixes + spells
    if extras:
        body += '<div class="cw-lab-grid">' + extras + '</div>'
    return body + '</section>'


def player_lab(rows, name):
    batting = [r for r in rows if r.get('position') is not None or r.get('runs') is not None or r.get('balls') is not None]
    bowling = [r for r in rows if any(r.get(k) is not None for k in ('wickets', 'legal', 'conceded'))]
    bowl_wkts = sum(r['wickets'] for r in bowling if r.get('wickets'))
    charts = [
        form_strip(batting, 'runs', f'{name}: last recorded batting innings'),
        form_strip(bowling, 'wickets', f'{name}: last recorded bowling innings') if bowl_wkts >= 15 else '',
        trajectory(batting, 'runs', f'{name}: cumulative runs in this archive'),
        trajectory(bowling, 'wickets', f'{name}: cumulative wickets in this archive') if bowl_wkts >= 15 else '',
        scoring_mix(batting, f'{name}: where the runs came from'),
        dismissals(batting),
        batting_order(batting),
        result_split(batting),
    ]
    charts = [c for c in charts if c]
    if not charts:
        return ''
    return '<section class="cw-lab" id="career-pictures"><div class="cw-lab-head"><p class="eyebrow">CAREER IN PICTURES</p><h2>Form, trajectory and how innings end</h2><p class="muted">Built from available scorecards against the twelve national teams. Official career tables above remain the complete record.</p></div><div class="cw-lab-grid">' + ''.join(charts) + '</div></section>'


def pair_lab(left, right, s1, s2, focus='batting'):
    if focus == 'bowling':
        rows = [('Wickets', s1.get('wickets'), s2.get('wickets')), ('Bowling average', s1.get('bowlAvg'), s2.get('bowlAvg')), ('Balls per wicket', s1.get('bowlSr'), s2.get('bowlSr')), ('Economy', s1.get('econ'), s2.get('econ'))]
    elif focus == 'all-round':
        rows = [('Runs', s1.get('runs'), s2.get('runs')), ('Wickets', s1.get('wickets'), s2.get('wickets')), ('Batting average', s1.get('avg'), s2.get('avg')), ('Bowling average', s1.get('bowlAvg'), s2.get('bowlAvg'))]
    else:
        rows = [('Runs', s1.get('runs'), s2.get('runs')), ('Batting average', s1.get('avg'), s2.get('avg')), ('Strike rate', s1.get('sr'), s2.get('sr')), ('Hundreds', s1.get('hundreds'), s2.get('hundreds')), ('Sixes', s1.get('sixes'), s2.get('sixes'))]
    return butterfly(left, right, rows, f'{left} and {right} on the same scale')


def showcase_card(all_cards):
    """Pick a complete limited-overs match that rewards a worm chart."""
    ranked = []
    preferred = None
    for card in all_cards.values():
        match = card.get('match') or {}
        inns = [i for i in card.get('innings') or [] if i.get('overs') and not i.get('super_over') and i.get('runs') is not None]
        if len(inns) < 2 or match.get('format') not in ('ODI', 'T20I'):
            continue
        if any(len(i['overs']) < 8 for i in inns):
            continue
        score = (match.get('date') or '', sum(i['runs'] for i in inns), card)
        ranked.append(score)
        event = (match.get('event') or '').lower()
        teams = set(match.get('teams') or [])
        if match.get('date') == '2023-11-19' and 'India' in teams and 'Australia' in teams:
            preferred = card
        elif preferred is None and 'world cup' in event and match.get('gender') == 'Men' and match.get('format') == 'ODI' and match.get('date', '') >= '2023-11-01':
            preferred = card
    if preferred:
        return preferred
    ranked.sort(reverse=True)
    return ranked[0][2] if ranked else None


def homepage_lab(card, url):
    if not card:
        return ''
    match = card['match']
    title = ' v '.join(match.get('teams') or [])
    charts = match_lab(card)
    if not charts:
        return ''
    return f'''<section class="home-match-lab" aria-labelledby="match-lab-title"><div class="section-heading"><div><p class="eyebrow">HOW A MATCH UNFOLDS</p><h2 id="match-lab-title">The pictures that make a scorecard readable.</h2><p class="muted">{_esc(title)} · {_esc(match.get("date"))} · {_esc(match.get("format"))} · {_esc(match.get("gender"))}. Worms, Manhattans and partnerships, drawn from recorded overs.</p></div><a href="{_esc(url)}">Open the scorecard →</a></div>{charts}</section>'''
