"""Visual-first team and ground pages with unique, number-rich search copy.

Match counts describe this publication archive. Men's and women's records stay
separate in the cards and tables.
"""
from __future__ import annotations

import hashlib
import html

from player_profile import DASHES, clip_meta, slug

FORMATS = ('Test', 'ODI', 'T20I')
GENDERS = ('Men', 'Women')


def esc(value):
    return html.escape(str(value if value is not None else ''), quote=True)


def _assert_clean(text):
    for mark in DASHES:
        if mark in text:
            raise ValueError('Entity copy must not use em or en dashes')
    return text


def h2h_path(left, right):
    pair = tuple(sorted((left, right)))
    return '/head-to-head/' + slug(pair[0] + '-vs-' + pair[1]) + '-' + hashlib.sha1('|'.join(pair).encode()).hexdigest()[:6] + '/'


def split_results(matches, team=None):
    rows = []
    for gender in GENDERS:
        for fmt in FORMATS:
            subset = [m for m in matches if m.get('format') == fmt and m.get('gender') == gender]
            if not subset:
                continue
            row = {
                'gender': gender,
                'format': fmt,
                'matches': len(subset),
                'first': min(m['date'] for m in subset),
                'last': max(m['date'] for m in subset),
            }
            if team:
                won = sum(m.get('outcome', {}).get('winner') == team for m in subset)
                lost = sum(
                    team in (m.get('teams') or [])
                    and m.get('outcome', {}).get('winner') not in (None, team)
                    for m in subset
                )
                other = len(subset) - won - lost
                decided = won + lost
                row.update({
                    'won': won,
                    'lost': lost,
                    'other': other,
                    'win_rate': (100 * won / decided) if decided else None,
                })
            rows.append(row)
    return rows


def team_totals(matches, team):
    won = sum(m.get('outcome', {}).get('winner') == team for m in matches)
    lost = sum(
        team in (m.get('teams') or [])
        and m.get('outcome', {}).get('winner') not in (None, team)
        for m in matches
    )
    other = len(matches) - won - lost
    formats = [fmt for fmt in FORMATS if any(m.get('format') == fmt for m in matches)]
    return {
        'matches': len(matches),
        'won': won,
        'lost': lost,
        'other': other,
        'formats': formats,
        'first': min((m['date'] for m in matches), default=''),
        'last': max((m['date'] for m in matches), default=''),
        'rows': split_results(matches, team),
        'men': sum(m.get('gender') == 'Men' for m in matches),
        'women': sum(m.get('gender') == 'Women' for m in matches),
    }


def ground_totals(matches):
    formats = [fmt for fmt in FORMATS if any(m.get('format') == fmt for m in matches)]
    return {
        'matches': len(matches),
        'formats': formats,
        'first': min((m['date'] for m in matches), default=''),
        'last': max((m['date'] for m in matches), default=''),
        'rows': split_results(matches),
        'men': sum(m.get('gender') == 'Men' for m in matches),
        'women': sum(m.get('gender') == 'Women' for m in matches),
    }


def _format_list(formats):
    if not formats:
        return 'international'
    if len(formats) == 1:
        return formats[0]
    if len(formats) == 2:
        return f'{formats[0]} and {formats[1]}'
    return f'{formats[0]}, {formats[1]} and {formats[2]}'


def team_seo(name, totals):
    label = _format_list(totals['formats'])
    title = f'{name} cricket records: {label} results'
    parts = []
    if totals['won']:
        parts.append(f'{totals["won"]:,} recorded wins')
    if totals['matches']:
        parts.append(f'{totals["matches"]:,} matches')
    for fmt in totals['formats']:
        n = sum(row['matches'] for row in totals['rows'] if row['format'] == fmt)
        if n:
            parts.append(f'{n:,} {fmt}s')
    joined = ', '.join(parts[:4]) if parts else 'international match records'
    description = (
        f'{name} has {joined} in this archive, men and women. '
        f'Format cards, head-to-head tables and scorecards.'
    )
    return _assert_clean(title), _assert_clean(clip_meta(description))


def ground_place(facts):
    """'Kolkata, India' from the ground facts, or '' when neither is known."""
    facts = facts or {}
    return ', '.join(part for part in (facts.get('city'), facts.get('country')) if part)


def ground_seo(name, totals, facts=None):
    label = _format_list(totals['formats'])
    place = ground_place(facts)
    title = f'{name} cricket records: {label}'
    capacity = f' Capacity {facts["capacity"]:,}.' if facts and facts.get('capacity') else ''
    description = (
        f'{name}{(", " + place) if place else ""} has {totals["matches"]:,} recorded international matches'
        f' ({label}), men and women.{capacity} Innings averages, format cards and scorecards.'
    )
    return _assert_clean(title), _assert_clean(clip_meta(description))


def ground_masthead(name, totals, facts=None, actions=''):
    """Masthead with the ground's place, size and history above the format switch."""
    facts = facts or {}
    place = ground_place(facts)
    eyebrow = 'GROUND' + (' · ' + place.upper().replace(', ', ' · ') if place else '')
    span = f'{totals["first"][:4]} to {totals["last"][:4]}' if totals.get('first') and totals.get('last') else ''
    sub = ' · '.join(part for part in (f'{totals["matches"]:,} recorded internationals', span, _format_list(totals['formats'])) if part)
    chips = []
    if facts.get('capacity'):
        chips.append(('Capacity', f'{facts["capacity"]:,}'))
    if facts.get('opened'):
        chips.append(('Opened', str(facts['opened'])))
    if facts.get('ends'):
        chips.append(('Ends', ' and '.join(facts['ends'])))
    if totals.get('men') is not None:
        chips.append(('Men and women', f'{totals["men"]:,} and {totals["women"]:,}'))
    links = []
    if facts.get('lat') is not None and facts.get('lon') is not None:
        links.append(('Map', f'https://www.openstreetmap.org/?mlat={facts["lat"]}&mlon={facts["lon"]}#map=16/{facts["lat"]}/{facts["lon"]}'))
    if facts.get('wikipedia'):
        links.append(('Wikipedia', facts['wikipedia']))
    chip_html = ''.join(f'<div class="gr-fact"><span>{esc(label)}</span><strong>{esc(value)}</strong></div>' for label, value in chips)
    link_html = ' · '.join(f'<a href="{esc(url)}" rel="noopener">{esc(label)}</a>' for label, url in links)
    return (
        f'<header class="pf-mast gr-mast"><div class="pf-id"><p class="eyebrow">{esc(eyebrow)}</p><h1>{esc(name)}</h1>'
        f'<p class="pf-sub">{esc(sub)}</p>'
        + (f'<div class="gr-facts">{chip_html}</div>' if chip_html else '')
        + (f'<p class="gr-links pf-fine">{link_html}</p>' if link_html else '')
        + actions + '</div></header>'
    )


def team_intro(name, totals):
    span = ''
    if totals['first'] and totals['last']:
        span = f', recorded from {totals["first"][:4]} to {totals["last"][:4]}'
    text = (
        f'{name} has {totals["matches"]:,} recorded international matches{span}: '
        f'{totals["men"]:,} men and {totals["women"]:,} women. '
        f'{totals["won"]:,} wins, {totals["lost"]:,} losses and {totals["other"]:,} draws, ties or no results. '
        'Cards below keep Tests, ODIs and T20Is, and men and women, as separate records.'
    )
    return _assert_clean(text)


def ground_intro(name, totals):
    span = ''
    if totals['first'] and totals['last']:
        span = f' from {totals["first"][:4]} to {totals["last"][:4]}'
    text = (
        f'{name} has {totals["matches"]:,} recorded international matches{span}: '
        f'{totals["men"]:,} men and {totals["women"]:,} women. '
        'How this ground plays uses recorded innings totals, not a pitch rating.'
    )
    return _assert_clean(text)


KEYS = {'Test': 'test', 'ODI': 'odi', 'T20I': 't20i'}


def _card(title, hero, unit, fields, share=0, fmt=None):
    figures = ''.join(f'<div><dt>{esc(label)}</dt><dd>{esc(value)}</dd></div>' for label, value in fields)
    inner = (
        f'<h3>{esc(title)}</h3>'
        f'<div class="format-card-hero"><strong>{esc(hero)}</strong><span>{esc(unit)}</span></div>'
        f'<dl>{figures}</dl>'
        f'<div class="format-card-share"><i style="width:{share:.1f}%"></i></div>'
    )
    if fmt in KEYS:
        return f'<a class="format-card fmt-{KEYS[fmt]}" href="#{KEYS[fmt]}" data-fmt-link="{KEYS[fmt]}">{inner}<span class="format-card-cta">Open the {esc(fmt)} record →</span></a>'
    return f'<article class="format-card">{inner}</article>'



def team_glance(name, totals):
    rows = totals['rows']
    if not rows:
        return ''
    peak = max(row['matches'] for row in rows) or 1
    cards = ''
    for row in rows:
        rate = f'{row["win_rate"]:.1f}%' if row['win_rate'] is not None else 'N/A'
        cards += _card(
            f"{row['gender']}'s {row['format']}",
            f'{row["won"]:,}',
            'wins',
            [
                ('Matches', f'{row["matches"]:,}'),
                ('Losses', f'{row["lost"]:,}'),
                ('Other', f'{row["other"]:,}'),
                ('Win rate', rate),
                ('From', row['first'][:4]),
                ('To', row['last'][:4]),
            ],
            row['matches'] / peak * 100,
            fmt=row['format'],
        )
    return (
        f'<section class="panel pf-block career-glance-wrap" id="by-format">'
        f'<h2>{esc(name)}: Tests, ODIs and T20Is</h2>'
        f'<p class="muted">Wins count a recorded winner. Other is draws, ties and no results. Men and women stay separate.</p>'
        f'<div class="career-glance">{cards}</div></section>'
    )


def ground_glance(name, totals):
    rows = totals['rows']
    if not rows:
        return ''
    peak = max(row['matches'] for row in rows) or 1
    cards = ''
    for row in rows:
        cards += _card(
            f"{row['gender']}'s {row['format']}",
            f'{row["matches"]:,}',
            'matches',
            [
                ('From', row['first'][:4]),
                ('To', row['last'][:4]),
            ],
            row['matches'] / peak * 100,
            fmt=row['format'],
        )
    return (
        f'<section class="panel pf-block career-glance-wrap" id="by-format">'
        f'<h2>{esc(name)}: recorded internationals</h2>'
        f'<p class="muted">Each card is a gender and format slice of the published archive.</p>'
        f'<div class="career-glance">{cards}</div></section>'
    )


def team_faq(name, totals, team_url):
    items = []

    def add(question, answer):
        items.append((_assert_clean(question), _assert_clean(answer)))

    add(
        f'How many international matches has {name} played?',
        f'{name} has {totals["matches"]:,} recorded international matches in this archive: '
        f'{totals["men"]:,} men and {totals["women"]:,} women.',
    )
    for fmt in totals['formats']:
        won = sum(row['won'] for row in totals['rows'] if row['format'] == fmt)
        matches = sum(row['matches'] for row in totals['rows'] if row['format'] == fmt)
        men = next((row for row in totals['rows'] if row['format'] == fmt and row['gender'] == 'Men'), None)
        women = next((row for row in totals['rows'] if row['format'] == fmt and row['gender'] == 'Women'), None)
        answer = f'{name} has won {won:,} recorded {fmt} matches from {matches:,} {fmt}s.'
        if men:
            answer += f' Men: {men["won"]:,} wins from {men["matches"]:,}.'
        if women:
            answer += f' Women: {women["won"]:,} wins from {women["matches"]:,}.'
        add(f'How many {fmt}s has {name} won?', answer)
    add(
        f'How many international wins does {name} have?',
        f'{name} has {totals["won"]:,} recorded wins, {totals["lost"]:,} losses and {totals["other"]:,} other results. '
        'This is an archive volume count, not an official ranking.',
    )
    items = items[:6]
    html_items = ''.join(f'<div><dt>{esc(q)}</dt><dd>{esc(a)}</dd></div>' for q, a in items)
    markup = (
        f'<section class="panel player-faq" id="team-questions">'
        f'<h2>Questions fans ask about {esc(name)}</h2>'
        f'<p class="muted">Answers use recorded match results on this page. Open a scorecard for innings detail.</p>'
        f'<dl>{html_items}</dl></section>'
    )
    schema = {
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        'mainEntity': [
            {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}}
            for q, a in items
        ],
    }
    return markup, schema


def ground_faq(name, totals):
    items = []

    def add(question, answer):
        items.append((_assert_clean(question), _assert_clean(answer)))

    add(
        f'How many international matches have been played at {name}?',
        f'{name} has {totals["matches"]:,} recorded international matches: '
        f'{totals["men"]:,} men and {totals["women"]:,} women.',
    )
    for fmt in totals['formats']:
        n = sum(row['matches'] for row in totals['rows'] if row['format'] == fmt)
        add(f'How many {fmt}s have been played at {name}?', f'{name} has {n:,} recorded {fmt} matches in this archive.')
    items = items[:6]
    html_items = ''.join(f'<div><dt>{esc(q)}</dt><dd>{esc(a)}</dd></div>' for q, a in items)
    markup = (
        f'<section class="panel player-faq" id="ground-questions">'
        f'<h2>Questions fans ask about {esc(name)}</h2>'
        f'<p class="muted">Answers use recorded matches at this venue. Innings averages appear in the venue charts above.</p>'
        f'<dl>{html_items}</dl></section>'
    )
    schema = {
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        'mainEntity': [
            {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}}
            for q, a in items
        ],
    }
    return markup, schema


def team_schema(name, url, description, base='https://cricket.rkjat.in'):
    return {
        '@type': 'SportsTeam',
        'name': name,
        'sport': 'Cricket',
        'url': base.rstrip('/') + url,
        'description': description,
    }


def ground_schema(name, url, description, facts=None, base='https://cricket.rkjat.in'):
    facts = facts or {}
    schema = {
        '@type': 'StadiumOrArena',
        'name': name,
        'url': base.rstrip('/') + url,
        'description': description,
        'sport': 'Cricket',
    }
    if facts.get('city') or facts.get('country'):
        address = {'@type': 'PostalAddress'}
        if facts.get('city'):
            address['addressLocality'] = facts['city']
        if facts.get('country'):
            address['addressCountry'] = facts['country']
        schema['address'] = address
    if facts.get('lat') is not None and facts.get('lon') is not None:
        schema['geo'] = {'@type': 'GeoCoordinates', 'latitude': facts['lat'], 'longitude': facts['lon']}
    if facts.get('capacity'):
        schema['maximumAttendeeCapacity'] = facts['capacity']
    if facts.get('wikipedia'):
        schema['sameAs'] = [facts['wikipedia']]
    return schema
