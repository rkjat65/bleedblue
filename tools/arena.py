"""Homepage "arena" modules: match centre, animated stat bands, leader bars and explore tiles.

Everything renders as static, crawlable HTML. web/arena.js adds countdowns, count-ups
and reveal motion on top; the page stays complete without JavaScript.
"""
from __future__ import annotations

import html
import re
import unicodedata
from datetime import datetime


def _e(value):
    return html.escape(str(value if value is not None else ''), quote=True)


def _slug(value):
    return re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFKD', str(value)).encode('ascii', 'ignore').decode().lower()).strip('-')


def _flag(team, size=28):
    h = round(size * 5 / 7)
    return f'<img src="/assets/flags/{_slug(team)}.svg" width="{size}" height="{h}" alt="" loading="lazy">'


def _ist_iso(date, clock):
    try:
        return f'{date}T{datetime.strptime(clock, "%I:%M %p").strftime("%H:%M")}:00+05:30'
    except (TypeError, ValueError):
        return ''


def _pretty_date(date):
    try:
        return datetime.strptime(date, '%Y-%m-%d').strftime('%a %d %b')
    except ValueError:
        return date


ICONS = {
    'bat': '<path d="M14.5 3.5l6 6-9.8 9.8a2 2 0 0 1-2.8 0l-3.2-3.2a2 2 0 0 1 0-2.8zM4.2 19.8l2-2"/><circle cx="19" cy="18" r="2.2"/>',
    'ball': '<circle cx="12" cy="12" r="8.5"/><path d="M6.5 5.8c2.4 3.6 2.4 8.8 0 12.4M17.5 5.8c-2.4 3.6-2.4 8.8 0 12.4"/>',
    'stumps': '<path d="M7 21V7M12 21V7M17 21V7M5.5 5h5M13.5 5h5"/>',
    'trophy': '<path d="M8 4h8v5a4 4 0 0 1-8 0zM8 6H5a3 3 0 0 0 3 4M16 6h3a3 3 0 0 1-3 4M12 13v4M8 20h8M9.5 17h5"/>',
    'versus': '<path d="M4 5l4 9 4-9M20 6.5c-.8-1-2-1.5-3.2-1.5-1.8 0-3 1-3 2.4 0 3.3 6.4 1.9 6.4 5.4 0 1.5-1.4 2.7-3.3 2.7-1.4 0-2.7-.6-3.5-1.6"/><path d="M4 19h16"/>',
    'chart': '<path d="M4 20V4M4 20h16M8 16v-4M12 16V8M16 16v-6M20 16V6"/>',
    'star': '<path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z"/>',
    'pin': '<path d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
    'calendar': '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/>',
    'tv': '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M8 21h8M9 3l3 3 3-3"/>',
    'compare': '<path d="M7 4v16M17 4v16M3 8h8M13 16h8"/><circle cx="7" cy="8" r="2"/><circle cx="17" cy="16" r="2"/>',
    'book': '<path d="M5 4h10a4 4 0 0 1 4 4v12H9a4 4 0 0 1-4-4z"/><path d="M5 16a4 4 0 0 1 4-4h10"/>',
}


def icon(name, size=22):
    return (f'<svg class="arena-icon" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')


def match_centre(fixtures, today, limit=12):
    """Horizontally scrolling fixture cards with IST start times; arena.js adds live countdowns."""
    cards = ''
    for item in fixtures[:limit]:
        teams = item.get('teams') or []
        start = _ist_iso(item.get('date'), item.get('time_ist'))
        if len(teams) == 2:
            sides = ''.join(f'<span class="mc-team">{_flag(t, 36)}<strong>{_e(t)}</strong></span>' for t in teams)
            sides = sides.replace('</span><span class="mc-team">', '</span><span class="mc-vs" aria-hidden="true">VS</span><span class="mc-team">', 1)
        else:
            sides = f'<span class="mc-team mc-team-wide"><strong>{_e(item.get("match", "TBC"))}</strong></span>'
        is_today = item.get('date') == today
        state = '<span class="mc-state mc-today">Today</span>' if is_today else f'<span class="mc-state">{_e(_pretty_date(item.get("date", "")))}</span>'
        cards += (f'<li class="mc-card{" is-today" if is_today else ""}"><a href="/where-to-watch/" data-start="{_e(start)}">'
                  f'<div class="mc-top">{state}<span class="mc-countdown" data-countdown aria-live="off"></span></div>'
                  f'<div class="mc-teams">{sides}</div>'
                  f'<p class="mc-detail">{_e(item.get("detail", ""))}</p>'
                  f'<div class="mc-foot"><span class="mc-series">{_e(item.get("series", ""))}</span>'
                  f'<time datetime="{_e(start or item.get("date", ""))}">{_e(item.get("time_ist", "TBC"))} IST</time></div></a></li>')
    if not cards:
        cards = '<li class="mc-card mc-empty"><p>No verified upcoming fixture is published right now.</p></li>'
    return f'''<section class="arena-section match-centre" id="match-centre" aria-labelledby="mc-title">
      <div class="section-heading"><div><p class="eyebrow"><span class="live-dot" aria-hidden="true"></span> MATCH CENTRE</p><h2 id="mc-title">Upcoming international fixtures</h2><p class="muted">Start times in IST, with a live countdown. Open a card for Indian TV and streaming details.</p></div>
      <div class="mc-controls"><button type="button" class="mc-arrow" data-mc-prev aria-label="Scroll fixtures left">←</button><button type="button" class="mc-arrow" data-mc-next aria-label="Scroll fixtures right">→</button><a href="/where-to-watch/">Where to watch →</a></div></div>
      <ol class="mc-rail" data-mc-rail tabindex="0" aria-label="Upcoming fixtures">{cards}</ol>
    </section>'''


def leaders_race(boards):
    """Tabbed leaderboard bars. boards: [(key, title, [(name, url, team, value)])]."""
    tabs = ''
    panels = ''
    for index, (key, title, rows) in enumerate(boards):
        top = max((v for *_, v in rows), default=1) or 1
        items = ''
        for rank, (name, url, team, value) in enumerate(rows, 1):
            items += (f'<li style="--w:{value / top * 100:.1f}%;--i:{rank}"><span class="race-rank">{rank}</span>'
                      f'<span class="race-who">{_flag(team.split(" / ")[0], 22) if team else ""}<a href="{_e(url)}">{_e(name)}</a><small>{_e(team)}</small></span>'
                      f'<span class="race-bar" aria-hidden="true"><i></i></span><strong>{value:,}</strong></li>')
        selected = 'true' if index == 0 else 'false'
        tabs += f'<button type="button" role="tab" id="race-tab-{key}" aria-controls="race-{key}" aria-selected="{selected}" data-race-tab>{_e(title)}</button>'
        panels += f'<div class="race-panel" role="tabpanel" id="race-{key}" aria-labelledby="race-tab-{key}"><h3>{_e(title)}</h3><ol class="race-list">{items}</ol></div>'
    return f'''<section class="arena-section arena-leaders" id="leaders" aria-labelledby="leaders-title">
      <div class="section-heading"><div><p class="eyebrow">ALL-TIME LEADERS</p><h2 id="leaders-title">Career leaders</h2><p class="muted">Official international totals across Tests, ODIs and T20Is.</p></div><a href="/players/">Player directory →</a></div>
      <div class="race-tabs" role="tablist" aria-label="Leaderboard">{tabs}</div><div class="race-grid" data-race>{panels}</div>
    </section>'''


def result_cards(matches, routes, result, limit=8):
    """Recent results as scoreboard cards with the winner highlighted."""
    cards = ''
    for m in matches[:limit]:
        winner = (m.get('outcome') or {}).get('winner')
        sides = ''
        for team in m['teams'][:2]:
            mark = ' is-winner' if team == winner else ''
            sides += f'<span class="rc-team{mark}">{_flag(team, 30)}<strong>{_e(team)}</strong>{"<b>WON</b>" if mark else ""}</span>'
        cards += (f'<li><a class="rc-card" href="{_e(routes[m["id"]])}"><div class="rc-meta"><span class="rc-format rc-{_e(m["format"].lower())}">{_e(m["format"])}</span>'
                  f'<span>{_e(m["gender"])}</span><time datetime="{_e(m["date"])}">{_e(_pretty_date(m["date"]))} {_e(m["date"][:4])}</time></div>'
                  f'<div class="rc-teams">{sides}</div><p class="rc-result">{_e(result(m))}</p><span class="rc-open">Scorecard →</span></a></li>')
    return f'''<section class="arena-section" id="results" aria-labelledby="results-title">
      <div class="section-heading"><div><p class="eyebrow">LATEST</p><h2 id="results-title">Recent match results</h2></div><a href="/matches/">All matches →</a></div>
      <ol class="rc-grid">{cards}</ol>
    </section>'''


def explore_bento(tiles):
    """Large, icon-led entry points. tiles: [(url, icon, kicker, title, text)]; the first tile is featured."""
    heights = (38, 62, 45, 80, 56, 92, 70, 100, 64, 86)
    art = ('<svg class="bento-art" viewBox="0 0 300 120" preserveAspectRatio="none" aria-hidden="true">'
           + ''.join(f'<rect x="{8 + n * 29}" y="{120 - h * 1.1:.0f}" width="18" height="{h * 1.1:.0f}" rx="4" style="--n:{n}"/>' for n, h in enumerate(heights))
           + '<polyline points="' + ' '.join(f'{17 + n * 29},{112 - h * 1.05:.0f}' for n, h in enumerate(heights)) + '" pathLength="100"/></svg>')
    cells = ''.join(f'<a class="bento-tile{" bento-feature" if i == 0 else ""}" href="{_e(url)}" style="--i:{i}">{art if i == 0 else ""}<span class="bento-icon">{icon(ic, 26)}</span>'
                    f'<span class="bento-kicker">{_e(kicker)}</span><h3>{_e(title)}</h3><p>{_e(text)}</p><span class="bento-go" aria-hidden="true">→</span></a>'
                    for i, (url, ic, kicker, title, text) in enumerate(tiles))
    return f'''<section class="arena-section" id="explore" aria-labelledby="explore-title">
      <div class="section-heading"><div><p class="eyebrow">EXPLORE</p><h2 id="explore-title">Browse cricket records</h2><p class="muted">Every route into the archive, one tap away.</p></div></div>
      <div class="bento">{cells}</div>
    </section>'''
