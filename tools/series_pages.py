"""Series as fans think of them: one edition of a tour or tournament per page.

Cricsheet names an event ("Sri Lanka tour of India", "ICC Men's T20 World Cup") but not its
edition, so matches of one event and gender are split into editions wherever more than 45 days
pass without a match. Each edition gets its result, standings or series score, every match and
its leading players; each event keeps a page listing its editions; /series/ shows the latest
editions and a browse by year.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from entity_formats import edition_label, editions, leaders
from player_profile import slug
from profile_formats import esc, lean_table

MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
FULL_MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December')
FORMAT_ORDER = ('Test', 'ODI', 'T20I')
PLURAL = {'Test': 'Tests', 'ODI': 'ODIs', 'T20I': 'T20Is'}


def day(date):
    return f'{int(date[8:10])} {MONTHS[int(date[5:7]) - 1]} {date[:4]}'


def date_range(first, last):
    if first == last:
        return day(first)
    if first[:4] == last[:4]:
        return f'{int(first[8:10])} {MONTHS[int(first[5:7]) - 1]} to {day(last)}'
    return f'{day(first)} to {day(last)}'


def flag(team, size=22):
    return f'<img class="sr-flag" src="/assets/flags/{slug(team)}.svg" width="{size}" height="{round(size * 5 / 7)}" alt="" loading="lazy">'


def build_editions(series_groups, series_paths):
    """[{event, gender, label, title, path, event_path, matches}] newest first."""
    out = []
    for event, ms in series_groups.items():
        genders = {m['gender'] for m in ms}
        used = set()
        for gender in ('Men', 'Women'):
            eds = editions([m for m in ms if m['gender'] == gender])
            repeats = Counter(edition_label(ed) for ed in eds)
            for ed in eds:
                label = edition_label(ed)
                women = gender == 'Women' and 'women' not in event.lower() and len(genders) > 1
                month = MONTHS[int(ed[0]['date'][5:7]) - 1]
                # Two editions in one season (rounds of a league, two tours a year) are told apart by month.
                key = label.replace('/', '-') + (f'-{month.lower()}' if repeats[label] > 1 else '') + ('-women' if women else '')
                base, n = key, 2
                while key in used:
                    key, n = f'{base}-{n}', n + 1
                used.add(key)
                title = f'{event} {label}' + (f' ({FULL_MONTHS[int(ed[0]["date"][5:7]) - 1]}{"" if n == 2 else " " + str(n - 1)})' if repeats[label] > 1 else '') + (' (women)' if women else '')
                out.append({'event': event, 'gender': gender, 'label': label, 'title': title, 'matches': ed,
                            'event_path': series_paths[event], 'path': series_paths[event] + key + '/',
                            'start': ed[0]['date'], 'end': ed[-1]['date']})
    out.sort(key=lambda e: (e['end'], e['start'], e['title']), reverse=True)
    return out


def attach_results(eds, results, host_of):
    """Cricsheet withholds some teams' scorecards (Afghanistan's among them); their results come
    without an event name. A result joins a tournament edition (three or more teams) when it is in
    the same format and gender, inside the edition's dates and in one of its host countries, and
    either team already plays in it or the event is an ICC one. Each result joins one edition."""
    by_kind = defaultdict(list)
    for m in results:
        by_kind[(m['format'], m['gender'])].append(m)
    used = set()
    for ed in sorted(eds, key=lambda e: -len(e['matches'])):
        ms = ed['matches']
        teams = {t for m in ms for t in m['teams']}
        if len(teams) < 3:
            continue
        hosts = {h for h in (host_of(m) for m in ms) if h}
        kind = (ms[0]['format'], ms[0]['gender'])
        icc = ed['event'].upper().startswith('ICC')
        extra = [m for m in by_kind[kind] if m['id'] not in used and ed['start'] <= m['date'] <= ed['end'] and host_of(m) in hosts
                 and (icc or teams & set(m['teams']))]
        if extra:
            used.update(m['id'] for m in extra)
            ed['matches'] = sorted(ms + extra, key=lambda m: (m['date'], m['id']))
            ed['added'] = sum(1 for m in extra if not m.get('player_ids'))


def _winner(m):
    return (m.get('outcome') or {}).get('winner')


def summary(ed):
    """One line: the series score for two teams, or the field and the last match for a tournament."""
    ms = ed['matches']
    teams = Counter(t for m in ms for t in m['teams'])
    if len(teams) == 2:
        a, b = sorted(teams)
        parts = []
        formats = [f for f in FORMAT_ORDER if any(m['format'] == f for m in ms)]
        for fmt in formats:
            sub = [m for m in ms if m['format'] == fmt]
            wins = Counter(_winner(m) for m in sub)
            other = len(sub) - wins[a] - wins[b]
            hi, lo = (a, b) if wins[a] >= wins[b] else (b, a)
            text = f'Series drawn {wins[a]}-{wins[b]}' if wins[hi] == wins[lo] else f'{hi} won {wins[hi]}-{wins[lo]}'
            if other:
                text += f' ({other} drawn or no result)'
            parts.append((f'{PLURAL[fmt]}: ' if len(formats) > 1 else '') + text)
        return ' · '.join(parts)
    last = ms[-1]
    w = _winner(last)
    if w:
        loser = next((t for t in last['teams'] if t != w), '')
        return f'{len(teams)} teams · last match: {w} beat {loser}'
    return f'{len(teams)} teams'


def card(ed):
    ms = ed['matches']
    teams = sorted({t for m in ms for t in m['teams']})
    formats = ' · '.join(f for f in FORMAT_ORDER if any(m['format'] == f for m in ms))
    shown = teams if len(teams) <= 4 else teams[:4]
    sides = (' v '.join(f'{flag(t)}{esc(t)}' for t in shown) if len(teams) == 2
             else ''.join(flag(t) for t in shown) + (f' <small>+{len(teams) - len(shown)}</small>' if len(teams) > len(shown) else ''))
    return (f'<a class="series-card" href="{esc(ed["path"])}" data-g="{ed["gender"].lower()}" data-f="{esc(formats.lower())}">'
            f'<span class="sc-meta">{esc(formats)} · {esc(ed["gender"])} · {len(ms)} match{"es" if len(ms) != 1 else ""}</span>'
            f'<h3>{esc(ed["title"])}</h3><p class="sc-teams">{sides}</p><p class="sc-result">{esc(summary(ed))}</p>'
            f'<small>{esc(date_range(ed["start"], ed["end"]))}</small></a>')


def standings(ms):
    """Played, won, lost and other per team across the edition, most wins first."""
    rows = defaultdict(lambda: [0, 0, 0, 0])
    for m in ms:
        w = _winner(m)
        for t in m['teams']:
            r = rows[t]
            r[0] += 1
            if w == t:
                r[1] += 1
            elif w:
                r[2] += 1
            else:
                r[3] += 1
    return sorted(rows.items(), key=lambda kv: (-kv[1][1], kv[1][2], kv[0]))


def match_rows(ms, mp, result, team_paths):
    rows = []
    for m in ms:
        sides = ' v '.join(f'{flag(t, 18)}{esc(t)}' for t in m['teams'])
        rows.append([f'<a href="{esc(mp[m["id"]])}">{esc(day(m["date"]))}</a>', sides, esc(m['format']), esc(result(m)), esc(m.get('venue') or '')])
    return lean_table('Every match', ['Date', 'Match', 'Format', 'Result', 'Ground'], rows, css='pf-recent sr-matches', left=(1, 2, 3, 4))


def edition_page(ed, cards, people, pp, mp, result, team_paths, host_of):
    """(title, description, body) for one edition."""
    ms = ed['matches']
    teams = sorted({t for m in ms for t in m['teams']})
    hosts = sorted({h for h in (host_of(m) for m in ms) if h})
    formats = [f for f in FORMAT_ORDER if any(m['format'] == f for m in ms)]
    sub = ' · '.join(x for x in (date_range(ed['start'], ed['end']), ' and '.join(hosts) if hosts else '', f'{len(ms)} match{"es" if len(ms) != 1 else ""}') if x)
    body = (f'<section class="page-head sr-head"><div class="eyebrow">{esc(" · ".join(formats).upper())} · {esc(ed["gender"].upper())} · SERIES</div>'
            f'<h1>{esc(ed["title"])}</h1><p>{esc(sub)}</p></section>')
    line = summary(ed)
    team_links = ''.join(f'<a class="sr-team" href="{esc(team_paths.get(t, "#"))}">{flag(t, 28)}<span>{esc(t)}</span></a>' for t in teams)
    body += f'<section class="panel sr-summary"><p class="eyebrow">RESULT</p><p class="sr-line">{esc(line)}</p><div class="sr-teams">{team_links}</div></section>'
    if len(teams) > 2:
        rows = [[f'<a href="{esc(team_paths[t])}">{esc(t)}</a>' if t in team_paths else esc(t), str(p), str(w), str(l), str(o)] for t, (p, w, l, o) in standings(ms)]
        body += '<section class="panel pf-block"><h2>Results by team</h2>' + lean_table('Results by team in this edition', ['Team', ('P', 'Played'), ('W', 'Won'), ('L', 'Lost'), ('Other', 'Tied, drawn or no result')], rows, css='sr-standings') + '<p class="pf-fine">All matches of the edition, group and knockout together. Not an official points table.</p></section>'
    note = (f'<p class="pf-fine">{ed["added"]} of these result{"s have" if ed["added"] != 1 else " has"} no published scorecard, so {"they count" if ed["added"] != 1 else "it counts"} in the results but not in the leading players.</p>' if ed.get('added') else '')
    body += '<section class="panel pf-block"><h2>Every match</h2>' + match_rows(ms, mp, result, team_paths) + note + '</section>'
    for fmt in formats:
        top = leaders([m for m in ms if m['format'] == fmt], cards, people, pp, mp, fmt=fmt, limit=5, show_team=True)
        if top:
            body += f'<section class="panel pf-block"><h2>Leading players{(" in the " + PLURAL[fmt]) if len(formats) > 1 else ""}</h2>{top}</section>'
    body += f'<p class="pf-links"><a href="{esc(ed["event_path"])}">Every edition of {esc(ed["event"])}</a> · <a href="/series/year/{ed["start"][:4]}/">All series in {ed["start"][:4]}</a> · <a href="/series/">Latest series</a></p>'
    description = f'{ed["title"]}: {line}. Every match, result and the leading run-scorers and wicket-takers, {date_range(ed["start"], ed["end"])}.'
    return f'{ed["title"]}: results, scorecards and stats', description[:300], body


def event_hub(event, eds, gp_series):
    """The event's own page: every edition, newest first."""
    ms = [m for e in eds for m in e['matches']]
    body = (f'<section class="page-head"><div class="eyebrow">SERIES AND TOURNAMENTS</div><h1>{esc(event)}</h1>'
            f'<p>{len(eds)} edition{"s" if len(eds) != 1 else ""} · {len(ms):,} matches · {ms and min(m["date"] for m in ms)[:4]} to {ms and max(m["date"] for m in ms)[:4]}</p></section>')
    body += '<div class="series-grid">' + ''.join(card(e) for e in eds) + '</div>'
    return body


def directory(eds, today):
    """The /series/ page: latest editions, then browse by year and by tournament."""
    latest = [e for e in eds if e['end'] <= today][:24]
    years = sorted({e['start'][:4] for e in eds}, reverse=True)
    events = Counter(e['event'] for e in eds)
    body = ('<section class="page-head"><div class="eyebrow">INTERNATIONAL CRICKET</div><h1>International series</h1>'
            f'<p>{len(eds):,} tours and tournaments with scorecards since {years[-1] if years else ""}, each edition with its result, matches and leading players.</p></section>')
    body += '<h2 class="team-group">Latest series</h2><div class="series-grid">' + ''.join(card(e) for e in latest) + '</div>'
    body += '<h2 class="team-group">Browse by year</h2><nav class="sr-years">' + ''.join(f'<a href="/series/year/{y}/">{y}</a>' for y in years) + '</nav>'
    paths = {e['event']: e['event_path'] for e in eds}
    regular = sorted((ev for ev, n in events.items() if n >= 3), key=lambda ev: (-events[ev], ev))
    body += ('<h2 class="team-group">Tournaments and trophies <small>played three or more times</small></h2><div class="sr-events">'
             + ''.join(f'<a href="{esc(paths[ev])}"><span>{esc(ev)}</span><b>{events[ev]}</b></a>' for ev in regular) + '</div>')
    return body, years, events


def year_page(year, eds):
    chosen = [e for e in eds if e['start'][:4] == year]
    chosen.sort(key=lambda e: (e['start'], e['title']))
    chips = ('<div class="rh-switch sr-filter" role="group" aria-label="Filter series">'
             '<div class="rh-seg" data-sr="g"><button type="button" data-v="" aria-pressed="true">All</button><button type="button" data-v="men" aria-pressed="false">Men</button><button type="button" data-v="women" aria-pressed="false">Women</button></div>'
             '<div class="rh-seg" data-sr="f"><button type="button" data-v="" aria-pressed="true">All</button>' + ''.join(f'<button type="button" class="fmt-{f.lower()}" data-v="{f.lower()}" aria-pressed="false">{f}</button>' for f in FORMAT_ORDER) + '</div></div>')
    script = ("<script>(function(){var pick={g:'',f:''};function show(){document.querySelectorAll('.series-card').forEach(function(c){"
              "c.hidden=!!(pick.g&&c.dataset.g!==pick.g)||!!(pick.f&&c.dataset.f.split(' · ').indexOf(pick.f)<0);});"
              "document.querySelectorAll('.sr-filter .rh-seg').forEach(function(s){s.querySelectorAll('button').forEach(function(b){b.setAttribute('aria-pressed',String(b.dataset.v===pick[s.dataset.sr]));});});}"
              "document.querySelectorAll('.sr-filter button').forEach(function(b){b.addEventListener('click',function(){pick[b.parentNode.dataset.sr]=b.dataset.v;show();});});})();</script>")
    body = (f'<section class="page-head"><div class="eyebrow">SERIES BY YEAR</div><h1>International series in {year}</h1>'
            f'<p>{len(chosen):,} tours and tournaments that started in {year}, in date order.</p></section>')
    body += chips + '<div class="series-grid">' + ''.join(card(e) for e in chosen) + '</div>' + script
    return f'International cricket series in {year}', f'Every international tour and tournament that started in {year}: results, series scores and scorecards.', body
