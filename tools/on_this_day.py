"""Calendar history from published match dates and scorecards, never invented milestones."""
from __future__ import annotations

import calendar
import hashlib
import html
import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw
from publication_assets import font

ROOT = Path(__file__).resolve().parent.parent
IST = timezone(timedelta(hours=5, minutes=30))
MONTHS = list(calendar.month_name)


def india_today():
    return datetime.now(IST).date()


def day_path(key):
    month, day = map(int, key.split('-'))
    date(2000, month, day)  # Leap-day anniversaries have their own page.
    return f'/on-this-day/{MONTHS[month].lower()}-{day}/'


def day_label(key):
    month, day = map(int, key.split('-'))
    return f'{day} {MONTHS[month]}'


def calendar_keys():
    return [f'{m:02d}-{d:02d}' for m in range(1, 13) for d in range(1, calendar.monthrange(2000, m)[1] + 1)]


def focus_players(people, matches, roster, today):
    """Contracted players first; an expired roster is not treated as current."""
    current = set()
    if roster.get('valid_until', '') >= today.isoformat():
        names = set(roster.get('names', []))
        ids = set(roster.get('ids', []))
        current = {pid for pid, p in people.items() if (p.get('name') in names or pid in ids) and 'India' in p.get('teams', [])}
    else:
        # Recent appearances remain a useful editorial focus, not a retirement claim.
        since = (today - timedelta(days=365)).isoformat()
        recent = {pid for m in matches if 'India' in m['teams'] and since <= m['date'] < today.isoformat() for pid in m.get('player_ids', [])}
        current = {pid for pid in recent if 'India' in people.get(pid, {}).get('teams', [])}
    return current


def build_catalog(matches, cards, people, player_routes, match_routes, roster, today):
    focus = focus_players(people, matches, roster, today)
    days = {key: [] for key in calendar_keys()}
    seen = set()
    for m in matches:
        mid = str(m['id'])
        if mid in seen or m['date'] >= today.isoformat():
            continue
        seen.add(mid)
        try:
            played = date.fromisoformat(m['date'])
        except ValueError:
            continue
        key = played.strftime('%m-%d')
        india = 'India' in m['teams']
        fmt = m['format']
        winner = m.get('outcome', {}).get('winner')
        match_name = ' v '.join(m['teams'])
        margin = m.get('margin_text') or ' and '.join('an innings' if k == 'innings' else f'{v} {k}' for k, v in m.get('outcome', {}).get('by', {}).items())
        result = f'{winner} won' + (f' by {margin}' if margin else '') if winner else {'draw': 'Match drawn', 'tie': 'Match tied', 'no result': 'No result'}.get(m.get('outcome', {}).get('result'), 'International match')
        base = {'date': m['date'], 'year': played.year, 'format': fmt, 'gender': m['gender'], 'india': india,
                'match_id': mid, 'url': match_routes[mid], 'match': match_name, 'venue': m.get('venue', ''),
                'event': m.get('event', ''), 'result': result, 'current': False, 'player_id': None,
                'player_url': None, 'date_basis': 'match-start', 'source': m.get('source', '')}
        test = fmt == 'Test'
        totals = m.get('totals', [])
        own = next((x for x in totals if x.get('team') == ('India' if india else winner)), None)
        score = f"{own['runs']}/{own['wickets']}" if own and own.get('runs') is not None and own.get('wickets') is not None else fmt
        # Tests are only start anniversaries. Their eventual result/innings are not a dated achievement.
        title = f'{match_name}: a Test began' if test else result if winner else match_name
        detail = f"{match_name} · {m.get('venue', '')}".strip(' ·')
        days[key].append({**base, 'id': mid + '-match', 'kind': 'match', 'title': title, 'detail': detail,
                          'metric': 'TEST' if test else score, 'metric_label': 'Match began' if test else 'India innings' if own and india else 'Winning innings' if own else 'International cricket',
                          'priority': (300 if india else 25) + (70 if winner == 'India' and not test else 0), 'player_name': ''})
        if test:
            continue
        card = cards.get(mid)
        if not card:
            continue
        for ix, inn in enumerate(card.get('innings', [])):
            if inn.get('super_over'):
                continue
            for kind in ('batting', 'bowling'):
                owner = inn['team'] if kind == 'batting' else next((t for t in m['teams'] if t != inn['team']), '')
                is_india = owner == 'India'
                for row in inn.get(kind, []):
                    pid = row.get('id')
                    p = people.get(pid, {})
                    name = p.get('name') or row.get('name', '')
                    current = is_india and pid in focus
                    if kind == 'batting':
                        runs = row.get('runs')
                        if runs is None or runs < (50 if is_india else 100):
                            continue
                        metric = str(runs) + ('*' if row.get('out') is False else '')
                        metric_label = f"off {row['balls']} balls" if row.get('balls') else 'Runs in the innings'
                        title = f'{name}: {metric} against ' + next(t for t in m['teams'] if t != owner)
                        priority = (700 if current else 400 if is_india else 30) + (200 if runs >= 100 else 0) + min(runs, 300)
                    else:
                        wickets, conceded = row.get('wickets'), row.get('runs')
                        if wickets is None or conceded is None or wickets < (3 if is_india and fmt == 'T20I' else 4 if is_india else 5):
                            continue
                        metric, metric_label = f'{wickets}/{conceded}', 'Wickets / runs'
                        title = f'{name}: {metric} against {inn["team"]}'
                        priority = (700 if current else 400 if is_india else 30) + (200 if wickets >= 5 else 0) + wickets * 20
                    days[key].append({**base, 'id': f'{mid}-{ix}-{kind}-{pid}', 'kind': kind, 'india': is_india,
                                      'current': current, 'player_id': pid, 'player_name': name, 'player_url': player_routes.get(pid),
                                      'title': title, 'detail': f'{match_name} · {result}', 'metric': metric, 'metric_label': metric_label,
                                      'priority': priority})
    for events in days.values():
        events.sort(key=lambda e: (-e['priority'], -e['year'], e['id']))
    return days


def render_card(event, key, out, illustrations):
    """A real, downloadable data graphic, with existing original player art where available."""
    dest = out / 'assets/on-this-day'
    dest.mkdir(parents=True, exist_ok=True)
    identity = json.dumps([event, key], sort_keys=True).encode()
    version = hashlib.sha256(identity).hexdigest()[:10]
    path = dest / f'{key}-{version}.png'
    if path.exists():
        return '/assets/on-this-day/' + path.name
    im = Image.new('RGB', (1200, 675), '#0a0a0f')
    draw = ImageDraw.Draw(im)
    draw.rounded_rectangle((20, 20, 1180, 655), radius=26, fill='#111118', outline='#282836', width=2)
    draw.rectangle((55, 55, 61, 116), fill='#00e5ff')
    draw.text((78, 52), 'ON THIS DAY', font=font(20, True), fill='#00e5ff')
    draw.text((76, 78), day_label(key).upper(), font=font(32, True), fill='#e8e8ed')
    draw.text((855, 60), 'CRICKET WICKET', font=font(23, True), fill='#e8e8ed')
    draw.text((860, 96), 'THE GAME IN NUMBERS', font=font(14), fill='#8888a0')
    if event:
        draw.text((60, 157), f"{event['year']}  /  {event['gender'].upper()}  /  {event['format']}", font=font(22), fill='#8888a0')
        draw.text((54, 193), event['metric'], font=font(108, True), fill='#b8ff00' if event['kind'] == 'batting' else '#ff2d78' if event['kind'] == 'bowling' else '#00e5ff')
        draw.text((62, 318), event['metric_label'], font=font(23), fill='#e8e8ed')
        portrait = illustrations.get(event.get('player_name'))
        source = out / portrait.lstrip('/') if portrait else None
        if source and source.is_file():
            cutout = Image.open(source).convert('RGBA')
            cutout.thumbnail((370, 445), Image.Resampling.LANCZOS)
            im.paste(cutout, (800 + (370-cutout.width)//2, 590-cutout.height), cutout)
        else:
            # A neutral cricket motif, never an invented photograph of the historical game.
            for x in (905, 975, 1045):
                draw.rounded_rectangle((x, 280, x+16, 551), radius=8, fill='#00e5ff')
            draw.rounded_rectangle((892, 260, 1072, 273), radius=6, fill='#ffb800')
            draw.ellipse((1035, 164, 1090, 219), fill='#ff2d78')
        lines, line = [], ''
        for word in event['title'].split():
            candidate = (line + ' ' + word).strip()
            if draw.textlength(candidate, font=font(34, True)) > 710 and line:
                lines.append(line); line = word
            else:
                line = candidate
        lines.append(line)
        for i, line in enumerate(lines[:3]):
            draw.text((60, 380+i*43), line, font=font(34, True), fill='#e8e8ed')
        draw.text((62, 553), 'TEST MATCH START ANNIVERSARY' if event['format'] == 'Test' else 'INTERNATIONAL MATCH RECORD', font=font(16), fill='#8888a0')
    else:
        draw.text((60, 225), 'A day to explore', font=font(60, True), fill='#e8e8ed')
        draw.text((60, 310), 'No dated match in this archive yet.', font=font(29), fill='#8888a0')
    draw.line((60, 596, 1140, 596), fill='#282836', width=2)
    draw.text((62, 616), 'INDIA & INTERNATIONAL CRICKET HISTORY', font=font(16), fill='#8888a0')
    draw.text((922, 616), 'cricket.rkjat.in', font=font(18, True), fill='#00e5ff')
    im.save(path, optimize=True)
    return '/assets/on-this-day/' + path.name


def event_html(event):
    e = lambda v: html.escape(str(v), quote=True)
    meta = f"{event['gender']} · {event['format']}" + (' · Test began' if event['format'] == 'Test' else '')
    focus = 'India player spotlight' if event['current'] else 'Team India' if event['india'] else 'International history'
    player = f' · <a href="{e(event["player_url"])}">Player profile</a>' if event.get('player_url') else ''
    return f'''<article class="otd-event" data-india="{str(event['india']).lower()}" data-player="{str(bool(event['player_id'] and event['india'])).lower()}" data-gender="{e(event['gender'])}" data-format="{e(event['format'])}">
      <time datetime="{event['date']}">{event['year']}</time><div><p class="otd-event-meta">{e(focus)} · {e(meta)}</p><h3>{e(event['title'])}</h3><p>{e(event['detail'])}</p><div class="otd-event-links"><a href="{e(event['url'])}">View scorecard →</a>{player}</div></div><strong class="otd-event-stat">{e(event['metric'])}<small>{e(event['metric_label'])}</small></strong></article>'''


def content(key, events, image, view='page'):
    e = lambda v: html.escape(str(v), quote=True)
    label = day_label(key)
    lead = events[0] if events else None
    description = lead['title'] if lead else 'Explore international cricket history'
    alt = f'On this day, {label}: {description}' + (f". {lead['year']}; {lead['metric']}, {lead['metric_label']}." if lead else '')
    title = f'<p class="eyebrow">ON THIS DAY</p><h2>{label} in cricket history</h2>' if view == 'home' else f'<p class="eyebrow">THE CRICKET CALENDAR</p><h1>On this day: {label}</h1>'
    out = f'<div class="otd-heading"><div>{title}<p>India’s moments. Today’s players. The scorecards behind the memories.</p></div>'
    out += f'<a class="button" href="/on-this-day/">Explore today’s history →</a></div>' if view == 'home' else '</div>'
    out += f'<div class="otd-feature"><a class="otd-art" href="{day_path(key) if view == "home" else e(lead["url"]) if lead else "/matches/"}"><img src="{e(image)}" alt="{e(alt)}" width="1200" height="675" loading="lazy"></a><div class="otd-feature-copy">'
    if lead:
        out += f'<p class="eyebrow">{lead["year"]} · {e(lead["gender"])} · {e(lead["format"])}</p><h3>{e(lead["title"])}</h3><p>{e(lead["detail"])}</p><a href="{e(lead["url"])}">Read the scorecard →</a>'
    else:
        out += '<h3>No dated match in this archive yet</h3><p>Browse another calendar day to discover more cricket history.</p>'
    out += f'<a class="otd-download" href="{e(image)}" download="cricket-wicket-on-this-day-{key}.png">Download this card ↓</a></div></div>'
    if view == 'home':
        more = [x for x in events[1:] if not lead or x['match_id'] != lead['match_id']][:2]
        if more:
            out += '<div class="otd-more">' + ''.join(f'<a href="{e(x["url"])}"><span>{x["year"]} · {e(x["format"])}</span><strong>{e(x["title"])}</strong></a>' for x in more) + '</div>'
        return out
    keys = calendar_keys(); index = keys.index(key)
    prev, nxt = keys[(index-1) % 366], keys[(index+1) % 366]
    out += f'<nav class="otd-date-nav" aria-label="Cricket history calendar"><a href="{day_path(prev)}">← {day_label(prev)}</a><a href="/on-this-day/">Today</a><a href="{day_path(nxt)}">{day_label(nxt)} →</a></nav>'
    month, day = map(int, key.split('-'))
    out += '<form class="otd-calendar filters"><label>Month<select name="month">' + ''.join(f'<option value="{m}"'+(' selected' if m == month else '')+f'>{MONTHS[m]}</option>' for m in range(1,13)) + '</select></label><label>Day<select name="day">' + ''.join(f'<option value="{d}"'+(' selected' if d == day else '')+f'>{d}</option>' for d in range(1,32)) + '</select></label><button class="primary">Explore date</button><span class="note">Anniversaries across all years</span><span class="otd-calendar-error" role="status"></span></form>'
    out += '<h2>From the archive</h2><form class="otd-filters filters"><label>Focus<select name="focus"><option value="all">All history · India first</option><option value="india">Team India</option><option value="players">India players</option></select></label><label>Team<select name="gender"><option value="">Men &amp; women</option><option>Men</option><option>Women</option></select></label><label>Format<select name="format"><option value="">All formats</option><option>Test</option><option>ODI</option><option>T20I</option></select></label><button>Apply filters</button></form><p class="otd-result-count note" role="status"></p>'
    out += '<div class="otd-events">' + ''.join(event_html(x) for x in events) + '</div><p class="otd-empty note" hidden>No matching history for these filters. Try another format or date.</p><button class="otd-show-more" hidden>Show more history</button>'
    out += '<details class="otd-method"><summary>About these dates and player spotlights</summary><p>Entries come from the published international match archive and link to their scorecards. Matches use the recorded start date. Tests are shown only as start anniversaries; their later innings and results are not claimed to have happened on that date. Limited-overs performances use the match date recorded in the scorecard.</p><p>India comes first, across men’s and women’s cricket. Player spotlights prioritise the current India retainership list; after it expires, players with an India appearance in the previous year are prioritised. This is an editorial focus, not a claim about selection in every format. Dates and figures are refreshed from the archive, with no invented birthdays or milestones.</p><p>“Today” follows India Standard Time. Missing historical scorecards limit the available performances.</p></details>'
    return out


def publish_history(matches, cards, people, player_routes, match_routes, page, dump, out, illustrations, today=None):
    today = today or india_today()
    roster = json.loads((ROOT/'data/india-player-focus.json').read_text(encoding='utf-8'))
    catalog = build_catalog(matches, cards, people, player_routes, match_routes, roster, today)
    archive = '<details class="otd-calendar-index"><summary>Browse the full cricket calendar</summary><div class="otd-months">'
    for month in range(1,13):
        archive += f'<section><h3>{MONTHS[month]}</h3><div>' + ''.join(f'<a href="{day_path(k)}" aria-label="{day_label(k)}">{int(k[3:])}</a>' for k in catalog if int(k[:2]) == month) + '</div></section>'
    archive += '</div></details>'
    for key, events in catalog.items():
        image = render_card(events[0] if events else None, key, out, illustrations)
        markup = content(key, events, image)
        label = day_label(key)
        extra = {'image': 'https://cricket.rkjat.in' + image}
        page(day_path(key), f'On this day in cricket: {label}', f'Cricket history on {label}: India matches, player performances and international scorecards across the years.', f'<section class="otd-section" data-otd-key="{key}">{markup}</section>', 'CollectionPage', extra)
        home = content(key, events, image, 'home')
        dump(f'/data/on-this-day/{key}.json', {'key': key, 'home': home, 'page': markup, 'built_at': today.isoformat()})
        if key == today.strftime('%m-%d'):
            page('/on-this-day/', 'On this day in cricket history', 'Today in cricket history: Team India, player performances and memorable international matches, with scorecards and a daily card.', f'<section class="otd-section" data-otd-live="page" data-otd-key="{key}">{markup}</section>'+archive, 'CollectionPage', extra)
            home_today = f'<section class="otd-section otd-home" aria-label="On this day in cricket" data-otd-live="home" data-otd-key="{key}">{home}</section>'
    return home_today
