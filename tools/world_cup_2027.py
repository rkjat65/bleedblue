"""The 2027 men's Cricket World Cup page, with every ODI World Cup before it.

Tournament facts and the schedule live in data/world_cup_2027.json, so the
fixtures can be added the moment the ICC publishes them. History comes from
the same official World Cup record as /world-cup/mens-odi/.
"""
from __future__ import annotations

import html
import json
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

PATH = '/world-cup/2027/'


def esc(value):
    return html.escape(str(value if value is not None else ''), quote=True)


def load(root):
    return json.loads((Path(root) / 'data/world_cup_2027.json').read_text(encoding='utf-8'))


def long_date(iso):
    d = date.fromisoformat(iso)
    return f'{d.day} {d.strftime("%B %Y")}'


def short_date(iso):
    d = date.fromisoformat(iso)
    return f'{d.strftime("%a")} {d.day} {d.strftime("%b")}'


def ist(local_time, offset_minutes):
    """Local start time to India Standard Time (UTC+5:30)."""
    if not local_time:
        return ''
    t = datetime.strptime(local_time, '%H:%M') + timedelta(minutes=330 - offset_minutes)
    return t.strftime('%H:%M')


def team_link(name, team_paths):
    path = team_paths.get(name)
    return f'<a href="{esc(path)}">{esc(name)}</a>' if path else esc(name)


def result_only(cup):
    """'Australia won by 6 wickets' becomes 'won by 6 wickets' under the champion's name."""
    text, winner = cup.get('final_result') or '', cup.get('winner') or ''
    return text[len(winner) + 1:] if winner and text.startswith(winner + ' ') else text


def finishes(editions):
    """Per team: titles, finals, semi-finals reached and best finish, from the official record."""
    out = {}
    for cup in editions:
        for team, stage in ([(cup.get('winner'), 3), (cup.get('runner_up'), 2)] + [(t, 1) for t in cup.get('losing_semi_finalists') or []]):
            if not team:
                continue
            r = out.setdefault(team, {'titles': [], 'finals': 0, 'semis': 0, 'best': 0})
            if stage == 3:
                r['titles'].append(cup['year'])
            if stage >= 2:
                r['finals'] += 1
            r['semis'] += 1
            r['best'] = max(r['best'], stage)
    return out


def best_label(r):
    if not r:
        return 'Group stage'
    return {3: 'Champions', 2: 'Runners-up', 1: 'Semi-finals'}.get(r['best'], 'Group stage')


def venue_record(ground, ground_matches):
    """ODIs at a ground in the archive: count, first year and first-innings average."""
    odis = [m for m in ground_matches if m.get('format') == 'ODI' and m.get('gender') == 'Men']
    if not odis:
        return None
    firsts = [(m.get('totals') or [{}])[0].get('runs') for m in odis if m.get('totals')]
    firsts = [r for r in firsts if r is not None]
    return {'odis': len(odis), 'first': min(m['date'] for m in odis)[:4], 'avg_first': sum(firsts) / len(firsts) if firsts else None}


def fixtures_section(wc, team_paths):
    fixtures = wc.get('fixtures') or []
    if not fixtures:
        return ('<section class="panel wc-block" id="schedule"><p class="eyebrow">SCHEDULE</p><h2>Full schedule</h2>'
                f'<p class="wc-wait">{esc(wc["schedule_note"])} Every fixture appears here, with local and India times, as soon as it is published.</p>'
                '<div class="wc-keydates"><div><span>Opening day</span><strong>' + esc(long_date(wc['start'])) + '</strong></div>'
                '<div><span>Semi-finals</span><strong>17 and 18 November 2027</strong></div>'
                '<div><span>Final</span><strong>' + esc(long_date(wc['end'])) + '</strong></div></div></section>')
    teams = sorted({t for f in fixtures for t in (f.get('team1'), f.get('team2')) if t})
    venues = sorted({f['venue'] for f in fixtures if f.get('venue')})
    stages = list(dict.fromkeys(f.get('stage') or '' for f in fixtures))
    offset = wc.get('utc_offset_minutes', 120)
    rows = ''
    for f in fixtures:
        t1, t2 = f.get('team1') or 'TBC', f.get('team2') or 'TBC'
        rows += (f'<tr data-teams="{esc(t1)}|{esc(t2)}" data-venue="{esc(f.get("venue") or "")}" data-stage="{esc(f.get("stage") or "")}">'
                 f'<th scope="row">{esc(f.get("match", ""))}</th><td class=t>{esc(short_date(f["date"]))}</td>'
                 f'<td>{esc(f.get("time") or "TBC")}</td><td>{esc(ist(f.get("time"), offset) or "TBC")}</td>'
                 f'<td class=t>{esc(f.get("stage") or "")}</td><td class=t>{team_link(t1, team_paths)} v {team_link(t2, team_paths)}</td>'
                 f'<td class=t>{esc(f.get("venue") or "TBC")}</td></tr>')
    opt = lambda items: ''.join(f'<option value="{esc(i)}">{esc(i)}</option>' for i in items)  # noqa: E731
    controls = (f'<div class="wc-filters" role="group" aria-label="Filter the schedule"><label>Team<select data-wc-filter="teams"><option value="">All teams</option>{opt(teams)}</select></label>'
                f'<label>Venue<select data-wc-filter="venue"><option value="">All venues</option>{opt(venues)}</select></label>'
                f'<label>Stage<select data-wc-filter="stage"><option value="">All stages</option>{opt(stages)}</select></label></div>')
    script = ("<script>(function(){var s=document.getElementById('schedule');if(!s)return;var f=s.querySelectorAll('[data-wc-filter]');"
              "function go(){var v={};f.forEach(function(x){v[x.dataset.wcFilter]=x.value});var n=0;s.querySelectorAll('tbody tr').forEach(function(r){"
              "var ok=(!v.teams||r.dataset.teams.split('|').indexOf(v.teams)>-1)&&(!v.venue||r.dataset.venue===v.venue)&&(!v.stage||r.dataset.stage===v.stage);"
              "r.hidden=!ok;if(ok)n++});s.querySelector('[data-wc-count]').textContent=n+' matches'}f.forEach(function(x){x.addEventListener('change',go)});})();</script>")
    return (f'<section class="panel wc-block" id="schedule"><div class="wc-block-head"><div><p class="eyebrow">SCHEDULE</p><h2>Full schedule</h2></div><span class="wc-count" data-wc-count>{len(fixtures)} matches</span></div>'
            f'{controls}<div class="table-wrap" tabindex="0" role="region" aria-label="2027 World Cup schedule"><table class="score-table wc-table"><caption>All 2027 World Cup fixtures, local time (UTC+2) and India time</caption>'
            '<thead><tr><th scope="col">No.</th><th scope="col" class=t>Date</th><th scope="col">Local</th><th scope="col">IST</th><th scope="col" class=t>Stage</th><th scope="col" class=t>Match</th><th scope="col" class=t>Venue</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div><p class="note">Local time is South Africa, Zimbabwe and Namibia time (UTC+2). IST is India Standard Time (UTC+5:30). Teams marked TBC are decided by earlier results.</p>{script}</section>')


def build(wc, family, team_paths, ground_paths, ground_matches, leaders, record_rows, today=None):
    """Return (title, description, body, kind, extra) for the 2027 page."""
    today = date.fromisoformat(today) if isinstance(today, str) else (today or date.today())
    start, end = date.fromisoformat(wc['start']), date.fromisoformat(wc['end'])
    days = (start - today).days
    editions = family['editions']
    titles = Counter(c['winner'] for c in editions if c.get('winner'))
    record = finishes(editions)
    last = editions[-1]

    hero = (f'<section class="wc-hero" aria-labelledby="wc-title"><div class="wc-hero-copy"><p class="eyebrow">{esc(" · ".join(wc["hosts"]).upper())} · {esc(long_date(wc["start"]).upper())} TO {esc(long_date(wc["end"]).upper())}</p>'
            f'<h1 id="wc-title">Cricket World Cup 2027</h1><p class="wc-lede">The 14th men\'s ODI World Cup returns to Africa for the first time since 2003: 14 teams, 57 matches and 12 venues across South Africa, Zimbabwe and Namibia.</p>'
            '<div class="wc-hero-links"><a class="button primary" href="#schedule">Schedule</a><a class="button" href="#teams">Teams</a><a class="button" href="#history">Every World Cup since 1975</a></div></div>'
            f'<div class="wc-countdown" data-wc-start="{esc(wc["start"])}" aria-live="polite"><strong data-wc-days>{max(days, 0):,}</strong><span>days to the opening match</span>'
            f'<small>Defending champions: {team_link(last["winner"], team_paths)} ({last["year"]})</small></div></section>'
            "<script>(function(){var c=document.querySelector('[data-wc-start]');if(!c)return;var d=Math.ceil((new Date(c.dataset.wcStart+'T08:00:00Z')-Date.now())/864e5);"
            "if(d>0)c.querySelector('[data-wc-days]').textContent=d.toLocaleString('en-GB');})();</script>")
    facts = [('Teams', str(wc['teams_total'])), ('Matches', str(wc['matches_total'])), ('Venues', str(len(wc['venues']))), ('Host nations', str(len(wc['hosts']))),
             ('Final', long_date(wc['end'])), ('Editions so far', str(len(editions)))]
    body = hero + '<div class="wc-facts">' + ''.join(f'<div><strong>{esc(v)}</strong><span>{esc(k)}</span></div>' for k, v in facts) + '</div>'
    body += '<nav class="wc-jump" aria-label="On this page">' + ''.join(f'<a href="#{i}">{t}</a>' for i, t in (('schedule', 'Schedule'), ('format', 'Format'), ('teams', 'Teams'), ('venues', 'Venues'), ('history', 'History'), ('records', 'Records'), ('questions', 'Questions'))) + '</nav>'
    body += fixtures_section(wc, team_paths)

    stages = ''.join(f'<li><div class="wc-stage-n">{s["matches"]}</div><div><h3>{esc(s["stage"])}</h3><p>{esc(s["detail"])}</p></div></li>' for s in wc['format'])
    body += (f'<section class="panel wc-block" id="format"><p class="eyebrow">FORMAT</p><h2>How 14 teams become one champion</h2><ol class="wc-stages">{stages}</ol>'
             '<p class="note">The format returns to a second-round league like the 2003 tournament in Africa, which used a Super Six.</p></section>')

    cards = ''
    for q in wc['qualified']:
        r = record.get(q['team'])
        won = ', '.join(str(y) for y in r['titles']) if r and r['titles'] else ''
        cards += (f'<article class="wc-team"><h3>{team_link(q["team"], team_paths)}</h3><p class="wc-route">{esc(q["route"])}</p>'
                  f'<dl><div><dt>Titles</dt><dd>{len(r["titles"]) if r else 0}</dd></div><div><dt>Finals</dt><dd>{r["finals"] if r else 0}</dd></div>'
                  f'<div><dt>Best</dt><dd>{esc(best_label(r))}</dd></div></dl>{f"<p class=wc-won>Won {esc(won)}</p>" if won else ""}</article>')
    cards += ''.join('<article class="wc-team is-open"><h3>Qualifier</h3><p class="wc-route">To be decided</p><p class="wc-won">One of four places from the 2027 Qualifier</p></article>' for _ in range(wc['teams_total'] - len(wc['qualified'])))
    body += (f'<section class="panel wc-block" id="teams"><p class="eyebrow">TEAMS</p><h2>{len(wc["qualified"])} of {wc["teams_total"]} places decided</h2>'
             f'<p>{esc(wc["qualifier_note"])}</p><div class="wc-teams">{cards}</div><p class="note">Titles, finals and best finish come from every ODI World Cup since 1975.</p></section>')

    vrows = []
    for v in wc['venues']:
        rec = venue_record(v['ground'], ground_matches.get(v['ground'], [])) if v.get('ground') else None
        name = f'<a href="{esc(ground_paths[v["ground"]])}">{esc(v["name"])}</a>' if v.get('ground') in ground_paths else esc(v['name'])
        vrows.append([name, esc(v['city']), esc(v['country']), f'{v["capacity"]:,}', f'{rec["odis"]:,}' if rec else '-', esc(rec['first']) if rec else 'New',
                      f'{rec["avg_first"]:.0f}' if rec and rec['avg_first'] is not None else '-'])
    vhead = ''.join(f'<th scope="col"{" class=t" if i < 3 else ""}>{h}</th>' for i, h in enumerate(['Venue', 'City', 'Country', 'Capacity', "Men's ODIs", 'First ODI', '1st inns avg']))
    vbody = ''.join('<tr><th scope="row">' + r[0] + '</th>' + ''.join(f'<td{" class=t" if i < 2 else ""}>{c}</td>' for i, c in enumerate(r[1:])) + '</tr>' for r in vrows)
    body += (f'<section class="panel wc-block" id="venues"><p class="eyebrow">VENUES</p><h2>Twelve grounds in three countries</h2>'
             f'<div class="table-wrap" tabindex="0" role="region" aria-label="2027 World Cup venues"><table class="score-table wc-table"><caption>2027 World Cup venues with their men\'s ODI record in this archive</caption><thead><tr>{vhead}</tr></thead><tbody>{vbody}</tbody></table></div>'
             '<p class="note">Capacities are approximate. ODI counts and first-innings averages come from the matches in this archive; Victoria Falls has not yet hosted a men\'s ODI.</p></section>')

    timeline = ''
    for cup in reversed(editions):
        hosts = ', '.join(cup.get('hosts') or [])
        semis = ', '.join(cup.get('losing_semi_finalists') or [])
        timeline += (f'<article class="wc-edition{" is-africa" if cup["year"] == 2003 else ""}"><div class="wc-edition-head"><span class="wc-year">{cup["year"]}</span><span class="wc-host">{esc(hosts)}</span></div>'
                     f'<p class="wc-champ">{team_link(cup.get("winner"), team_paths)}</p><p class="wc-final">beat {team_link(cup.get("runner_up"), team_paths)}'
                     f'{(" · " + esc(result_only(cup))) if cup.get("final_result") else ""}</p>'
                     f'{f"<p class=wc-semis>Semi-finals: {esc(semis)}</p>" if semis else ""}'
                     f'{f"<p class=wc-meta>Final at {esc(cup["final_venue"])}</p>" if cup.get("final_venue") else ""}</article>')
    bars = ''.join(f'<div class="wc-title-bar"><span>{team_link(t, team_paths)}</span><i style="width:{n / max(titles.values()) * 100:.0f}%"></i><strong>{n}</strong></div>' for t, n in titles.most_common())
    body += (f'<section class="panel wc-block" id="history"><p class="eyebrow">HISTORY</p><h2>Every men\'s ODI World Cup, 1975 to {last["year"]}</h2>'
             f'<div class="wc-history-top"><div><h3>Most titles</h3><div class="wc-title-bars">{bars}</div></div>'
             f'<p class="wc-history-note">{len(editions)} tournaments, {len(titles)} different champions. Australia have won {titles.get("Australia", 0)}; the 2003 final in Johannesburg, the last time Africa hosted, was one of them.</p></div>'
             f'<div class="wc-editions">{timeline}</div><p><a class="button" href="/world-cup/mens-odi/">Full men\'s ODI World Cup records</a></p></section>')

    if record_rows:
        rec_head = ''.join(f'<th scope="col" class=t>{h}</th>' for h in ('Record', 'Holder', 'Value', 'Detail'))
        rec_body = ''.join('<tr><th scope="row">' + r[0] + '</th>' + ''.join(f'<td class=t>{c}</td>' for c in r[1:]) + '</tr>' for r in record_rows)
        body += (f'<section class="panel wc-block" id="records"><p class="eyebrow">RECORDS</p><h2>World Cup landmarks</h2>'
                 f'<div class="table-wrap" tabindex="0" role="region" aria-label="World Cup records"><table class="score-table wc-table"><caption>Official men\'s ODI World Cup records</caption><thead><tr>{rec_head}</tr></thead><tbody>{rec_body}</tbody></table></div>')
        lead = ''
        if leaders.get('runs'):
            lead += '<div><h3>Most runs, ball-by-ball era</h3><ol class="wc-leaders">' + ''.join(f'<li><span>{r["link"]}</span><strong>{r["runs"]:,}</strong></li>' for r in leaders['runs'][:5]) + '</ol></div>'
        if leaders.get('wickets'):
            lead += '<div><h3>Most wickets, ball-by-ball era</h3><ol class="wc-leaders">' + ''.join(f'<li><span>{r["link"]}</span><strong>{r["wickets"]:,}</strong></li>' for r in leaders['wickets'][:5]) + '</ol></div>'
        if lead:
            body += f'<div class="wc-two">{lead}</div>'
        body += '</section>'

    faq = [
        ('When is the 2027 Cricket World Cup?', f'From {long_date(wc["start"])} to {long_date(wc["end"])}. The semi-finals are on 17 and 18 November and the final on {long_date(wc["end"])}.'),
        ('Where is the 2027 Cricket World Cup being played?', 'In South Africa, Zimbabwe and Namibia, at 12 venues: eight in South Africa, three in Zimbabwe and one in Namibia.'),
        ('How many teams play in the 2027 World Cup?', f'{wc["teams_total"]} teams and {wc["matches_total"]} matches. {len(wc["qualified"])} have qualified; the last four places come from the 2027 Qualifier.'),
        ('Who won the last Cricket World Cup?', f'{last["winner"]} won the {last["year"]} World Cup, beating {last["runner_up"]} in the final{(" at " + last["final_venue"]) if last.get("final_venue") else ""}.'),
        ('Which team has won the most Cricket World Cups?', f'{titles.most_common(1)[0][0]}, with {titles.most_common(1)[0][1]} titles.'),
        ('When was the World Cup last held in Africa?', 'In 2003, hosted by South Africa, Zimbabwe and Kenya. Australia beat India in the final at the Wanderers in Johannesburg.'),
    ]
    body += ('<section class="panel wc-block player-faq" id="questions"><p class="eyebrow">QUESTIONS</p><h2>2027 World Cup questions</h2><dl>'
             + ''.join(f'<div><dt>{esc(q)}</dt><dd>{esc(a)}</dd></div>' for q, a in faq) + '</dl></section>')
    body += ('<p class="note">Tournament facts from the ICC and published reports: ' + ' · '.join(f'<a href="{esc(s["url"])}">{esc(s["label"])}</a>' for s in wc['sources'])
             + '. History and records from the official World Cup record. ' + '<a href="/world-cup/">All World Cups</a></p>')

    schema_faq = {'@context': 'https://schema.org', '@type': 'FAQPage',
                  'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in faq]}
    extra = {'startDate': wc['start'], 'endDate': wc['end'], 'sport': 'Cricket', 'eventStatus': 'https://schema.org/EventScheduled',
             'location': [{'@type': 'Place', 'name': v['name'], 'address': {'@type': 'PostalAddress', 'addressLocality': v['city'], 'addressCountry': v['country']}} for v in wc['venues']],
             'organizer': {'@type': 'Organization', 'name': 'International Cricket Council', 'url': 'https://www.icc-cricket.com/'},
             'faq': schema_faq, 'breadcrumb_name': 'Cricket World Cup 2027'}
    title = 'Cricket World Cup 2027: schedule, venues, teams and every past winner'
    description = (f'Cricket World Cup 2027 in South Africa, Zimbabwe and Namibia, {short_date(wc["start"])[4:]} to {short_date(wc["end"])[4:]}: '
                   f'schedule, 12 venues, {wc["teams_total"]} teams, format and every winner since 1975.')
    return title, description, body, 'SportsEvent', extra


def promo(wc, today=None):
    """A strip linking to the 2027 page, for the homepage and the World Cup hub."""
    today = date.fromisoformat(today) if isinstance(today, str) else (today or date.today())
    days = (date.fromisoformat(wc['start']) - today).days
    count = (f'<span class="wc-promo-days"><strong data-wc-days>{days:,}</strong> days to go</span>' if days > 0 else '')
    return (f'<a class="wc-promo" href="{PATH}" data-wc-start="{esc(wc["start"])}"><span class="wc-promo-copy"><span class="eyebrow">ICC MEN\'S CRICKET WORLD CUP 2027</span>'
            f'<strong>South Africa, Zimbabwe and Namibia · {esc(short_date(wc["start"]))} to {esc(short_date(wc["end"]))} 2027</strong>'
            f'<span>Schedule, venues, the 14 teams and every World Cup winner since 1975</span></span>{count}</a>'
            "<script>(function(){document.querySelectorAll('.wc-promo[data-wc-start]').forEach(function(c){var d=Math.ceil((new Date(c.dataset.wcStart+'T08:00:00Z')-Date.now())/864e5),"
            "n=c.querySelector('[data-wc-days]');if(n&&d>0)n.textContent=d.toLocaleString('en-GB');});})();</script>")
