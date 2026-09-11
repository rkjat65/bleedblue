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


def ground_seo(name, totals):
    label = _format_list(totals['formats'])
    title = f'{name} cricket records: {label}'
    description = (
        f'{name} has {totals["matches"]:,} recorded international matches'
        f' ({label}), men and women. Innings averages, format cards and scorecards.'
    )
    return _assert_clean(title), _assert_clean(clip_meta(description))


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


def _card(title, hero, unit, fields, share=0):
    figures = ''.join(f'<div><dt>{esc(label)}</dt><dd>{esc(value)}</dd></div>' for label, value in fields)
    return (
        f'<article class="format-card"><h3>{esc(title)}</h3>'
        f'<div class="format-card-hero"><strong>{esc(hero)}</strong><span>{esc(unit)}</span></div>'
        f'<dl>{figures}</dl>'
        f'<div class="format-card-share"><i style="width:{share:.1f}%"></i></div></article>'
    )


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
        )
    return (
        f'<section class="career-glance-wrap" id="by-format">'
        f'<p class="eyebrow">BY FORMAT AND GENDER</p>'
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
        )
    return (
        f'<section class="career-glance-wrap" id="by-format">'
        f'<p class="eyebrow">BY FORMAT AND GENDER</p>'
        f'<h2>{esc(name)}: recorded internationals</h2>'
        f'<p class="muted">Each card is a gender and format slice of the published archive.</p>'
        f'<div class="career-glance">{cards}</div></section>'
    )


def results_table_rows(totals):
    return [
        [
            row['format'],
            row['gender'],
            f'{row["matches"]:,}',
            f'{row["won"]:,}',
            f'{row["lost"]:,}',
            f'{row["other"]:,}',
            f'{row["win_rate"]:.1f}%' if row.get('win_rate') is not None else 'N/A',
        ]
        for row in totals['rows']
    ]


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
        f'<p class="muted">Answers use recorded matches at this venue. Innings averages sit in the ground picture above.</p>'
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


def ground_schema(name, url, description, base='https://cricket.rkjat.in'):
    return {
        '@type': 'StadiumOrArena',
        'name': name,
        'url': base.rstrip('/') + url,
        'description': description,
        'sport': 'Cricket',
    }
