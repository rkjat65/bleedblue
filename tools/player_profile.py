"""Visual-first, crawlable player profiles with unique search copy.

Official career numbers stay in HTML (cards, tables, FAQ). Archive pictures
are labelled as scorecard coverage, never as a complete career.
"""
from __future__ import annotations

import html
import re

FORMATS = ('Test', 'ODI', 'T20I')
DASHES = ('\u2014', '\u2013')


def esc(value):
    return html.escape(str(value if value is not None else ''), quote=True)


def clip_meta(text, limit=158):
    text = ' '.join(text.split())
    if len(text) <= limit:
        return text
    sentences = [part.strip().rstrip('.') for part in re.split(r'(?<=\S)\.\s+', text) if part.strip()]
    built = ''
    for sentence in sentences:
        candidate = (built + ' ' + sentence).strip() + '.'
        if len(candidate) <= limit:
            built = candidate.rstrip('.')
        else:
            break
    if built:
        return built + '.'
    cut = text[:limit].rsplit(' ', 1)[0].rstrip('.,;:')
    dangling = {'and', 'or', 'of', 'the', 'a', 'an', 'for', 'to', 'in', 'on', 'with'}
    parts = cut.split()
    while parts and parts[-1].lower() in dangling:
        parts.pop()
    return ' '.join(parts) + '.'


def formats_present(career):
    return [fmt for fmt in FORMATS if fmt in (career or {})]


def format_list(formats):
    if not formats:
        return 'international'
    if len(formats) == 1:
        return formats[0]
    if len(formats) == 2:
        return f'{formats[0]} and {formats[1]}'
    return f'{formats[0]}, {formats[1]} and {formats[2]}'


def plain(stats, key):
    value = (stats or {}).get(key)
    if value is None:
        return None
    if key in ('avg', 'sr', 'bowlAvg', 'bowlSr', 'econ'):
        return f'{value:.2f}'
    if isinstance(value, int):
        return f'{value:,}'
    return str(value)


def primary_role(career):
    rows = list((career or {}).values())
    runs = sum(s.get('runs') or 0 for s in rows)
    wickets = sum(s.get('wickets') or 0 for s in rows)
    stumpings = sum(s.get('stumpings') or 0 for s in rows)
    if stumpings >= 10:
        return 'wicketkeeper'
    if wickets >= 50 and runs >= 2000:
        return 'all-rounder'
    if wickets >= 40 and runs < 1000:
        return 'bowler'
    if wickets >= 80:
        return 'bowler'
    return 'batter'


def format_clause(fmt, stats):
    wickets = stats.get('wickets')
    runs = stats.get('runs')
    bowl = wickets is not None and wickets >= 15
    bat = runs is not None and runs >= 100
    if bowl and bat and runs >= 1000 and wickets >= 50:
        clause = f'{runs:,} {fmt} runs and {wickets:,} wickets'
        if stats.get('avg') is not None:
            clause += f', batting average {stats["avg"]:.2f}'
        return clause
    if bowl and (not bat or (wickets >= 40 and (runs or 0) < 2000)):
        clause = f'{wickets:,} {fmt} wickets'
        if stats.get('bowlAvg') is not None:
            clause += f' at {stats["bowlAvg"]:.2f}'
        return clause
    if runs is not None:
        clause = f'{runs:,} {fmt} runs'
        if stats.get('avg') is not None:
            clause += f' at {stats["avg"]:.2f}'
        return clause
    if wickets:
        return f'{wickets:,} {fmt} wickets'
    if stats.get('matches'):
        return f'{stats["matches"]:,} {fmt} matches'
    return None


def _assert_clean(text):
    for mark in DASHES:
        if mark in text:
            raise ValueError('Profile copy must not use em or en dashes')
    return text


def player_seo(player, suffix=''):
    """Unique title and description from official career figures only."""
    name = player['name']
    career = player.get('career') or {}
    formats = formats_present(career)
    gender = player.get('gender') or ''
    label = format_list(formats)
    women = "women's " if gender == 'Women' else ''
    title = f'{name}{suffix} stats: {women}{label} career records'
    clauses = [format_clause(fmt, career[fmt]) for fmt in formats]
    clauses = [c for c in clauses if c]
    if clauses:
        joined = clauses[0] if len(clauses) == 1 else ', '.join(clauses[:-1]) + ' and ' + clauses[-1]
        scope = " in women's internationals" if gender == 'Women' else ''
        description = f'{name} has {joined}{scope}. Official {label} tables and career pictures.'
    else:
        teams = ' / '.join(player.get('teams') or [])
        team_bit = f' for {teams}' if teams else ''
        description = (
            f'{name}{team_bit}: international cricket identity in this archive. '
            'Career tables appear when an official snapshot is matched.'
        )
    return _assert_clean(title), _assert_clean(clip_meta(description))


def player_intro(player):
    name = player['name']
    career = player.get('career') or {}
    formats = formats_present(career)
    teams = ' / '.join(player.get('teams') or [])
    gender = (player.get('gender') or '').lower()
    role = primary_role(career) if career else 'player'
    span = ''
    if player.get('first') and player.get('last'):
        span = f', recorded from {player["first"]} to {player["last"]}'
    article = 'an' if role[0] in 'aeiou' else 'a'
    who = f'{name} is {article} {role}'
    if teams:
        who += f' for {teams}'
    if gender:
        who += f" in {gender}'s international cricket"
    who += span + '.'
    clauses = [format_clause(fmt, career[fmt]) for fmt in formats]
    clauses = [c for c in clauses if c]
    if clauses:
        joined = clauses[0] if len(clauses) == 1 else ', '.join(clauses[:-1]) + ' and ' + clauses[-1]
        who += f' Official career: {joined}.'
        who += ' Headline figures and pictures come first; full batting, bowling and fielding tables stay on this page for search and download.'
    return _assert_clean(who)


def profile_nav(has_glance, picture_id, has_tables, has_faq, has_archive):
    links = []
    if has_glance:
        links.append('<a href="#career-glance">By format</a>')
    if picture_id:
        links.append(f'<a href="#{esc(picture_id)}">Pictures</a>')
    if has_tables:
        links.append('<a href="#career-records">Full tables</a>')
    if has_faq:
        links.append('<a href="#player-questions">Questions</a>')
    if has_archive:
        links.append('<a href="#analysis">Explorer</a>')
    if not links:
        return ''
    return '<nav class="profile-jump" aria-label="On this page">' + ''.join(links) + '</nav>'


def _hero(stats):
    wickets = stats.get('wickets') or 0
    runs = stats.get('runs') or 0
    if wickets >= 15 and (runs < 500 or wickets * 25 >= runs):
        return plain(stats, 'wickets') or '0', 'wickets'
    if runs or stats.get('innings'):
        return plain(stats, 'runs') or '0', 'runs'
    if wickets:
        return plain(stats, 'wickets'), 'wickets'
    return plain(stats, 'matches') or '0', 'matches'


def career_glance(player, stat_value):
    career = player.get('career') or {}
    formats = formats_present(career)
    if not formats:
        return ''
    peak_runs = max((career[fmt].get('runs') or 0) for fmt in formats) or 1
    cards = ''
    for fmt in formats:
        stats = career[fmt]
        hero, unit = _hero(stats)
        share = (stats.get('runs') or 0) / peak_runs * 100
        if unit == 'wickets':
            fields = [
                ('Matches', stat_value(stats, 'matches')),
                ('Average', stat_value(stats, 'bowlAvg')),
                ('Economy', stat_value(stats, 'econ')),
                ('Strike rate', stat_value(stats, 'bowlSr')),
                ('Best innings', stat_value(stats, 'best_bowling')),
                ('Five-fors', stat_value(stats, 'five_w')),
            ]
            extra = ''
            if (stats.get('runs') or 0) >= 200:
                extra = f'<p class="format-card-note">{plain(stats, "runs")} runs · batting average {plain(stats, "avg") or "N/A"}</p>'
        else:
            fields = [
                ('Matches', stat_value(stats, 'matches')),
                ('Average', stat_value(stats, 'avg')),
                ('Strike rate', stat_value(stats, 'sr')),
                ('Hundreds', stat_value(stats, 'hundreds')),
                ('Highest', stat_value(stats, 'highest_display')),
                ('Fifties', stat_value(stats, 'fifties')),
            ]
            extra = ''
            if (stats.get('wickets') or 0) >= 15:
                extra = f'<p class="format-card-note">{plain(stats, "wickets")} wickets · bowling average {plain(stats, "bowlAvg") or "N/A"}</p>'
        figures = ''.join(f'<div><dt>{label}</dt><dd>{value}</dd></div>' for label, value in fields)
        cards += (
            f'<article class="format-card" data-career-format="{fmt}">'
            f'<h3>{fmt}</h3>'
            f'<p class="format-card-meta">{stat_value(stats, "matches")} matches'
            f'{(" · " + esc(stats["span"])) if stats.get("span") else ""}</p>'
            f'<div class="format-card-hero"><strong>{esc(hero)}</strong><span>{unit}</span></div>'
            f'<dl>{figures}</dl>{extra}'
            f'<div class="format-card-share" title="{fmt} share of recorded career runs">'
            f'<i style="width:{share:.1f}%"></i></div></article>'
        )
    women = "women's " if player.get('gender') == 'Women' else ''
    heading = f'{player["name"]}: {women}{format_list(formats)} stats'
    return (
        f'<section class="career-glance-wrap" id="career-glance">'
        f'<p class="eyebrow">BY FORMAT</p><h2>{esc(heading)}</h2>'
        f'<p class="muted">Headline official figures. Full batting, bowling and fielding tables follow the pictures.</p>'
        f'<div class="career-glance">{cards}</div></section>'
    )


def career_tables(player, table, stat_value):
    career = player.get('career') or {}
    formats = formats_present(career)
    if not formats:
        return ''
    bat_keys = [
        ('matches', 'Mat'), ('innings', 'Inns'), ('notouts', 'NO'), ('runs', 'Runs'),
        ('highest_display', 'HS'), ('avg', 'Avg'), ('balls', 'BF'), ('sr', 'SR'),
        ('hundreds', '100s'), ('fifties', '50s'), ('ducks', '0s'), ('fours', '4s'), ('sixes', '6s'),
    ]
    bowl_keys = [
        ('matches', 'Mat'), ('bowling_innings', 'Inns'), ('legal', 'Balls'), ('maidens', 'Mdns'),
        ('conceded', 'Runs'), ('wickets', 'Wkts'), ('best_bowling', 'BBI'), ('best_match', 'BBM'),
        ('bowlAvg', 'Avg'), ('econ', 'Econ'), ('bowlSr', 'SR'), ('four_w', '4w'),
        ('five_w', '5w'), ('ten_w', '10w'),
    ]
    field_keys = [
        ('matches', 'Mat'), ('fielding_innings', 'Inns'), ('catches', 'Ct'), ('stumpings', 'St'),
        ('dismissals', 'Dis'), ('dismissals_per_innings', 'Dis/inns'), ('most_dismissals', 'Best'),
    ]
    batting_rows = [[fmt] + [stat_value(career[fmt], key) for key, _ in bat_keys] for fmt in formats]
    body = table(
        ['Format'] + [label for _, label in bat_keys],
        batting_rows,
        ident='batting-career',
        caption='Batting career records by format',
    )
    bowl_any = any(
        (career[fmt].get('bowling_innings') or 0) or (career[fmt].get('wickets') or 0) or (career[fmt].get('legal') or 0)
        for fmt in formats
    )
    if bowl_any:
        bowling_rows = [[fmt] + [stat_value(career[fmt], key) for key, _ in bowl_keys] for fmt in formats]
        body += table(
            ['Format'] + [label for _, label in bowl_keys],
            bowling_rows,
            ident='bowling-career',
            caption='Bowling career records by format',
        )
    field_any = any((career[fmt].get('dismissals') or 0) or (career[fmt].get('catches') or 0) for fmt in formats)
    if field_any:
        fielding_rows = [[fmt] + [stat_value(career[fmt], key) for key, _ in field_keys] for fmt in formats]
        body += table(
            ['Format'] + [label for _, label in field_keys],
            fielding_rows,
            ident='fielding-career',
            caption='Fielding career records by format',
        )
    return body


def player_faq(player):
    name = player['name']
    career = player.get('career') or {}
    formats = formats_present(career)
    items = []

    def add(question, answer):
        question, answer = _assert_clean(question), _assert_clean(answer)
        items.append((question, answer))

    for fmt in formats:
        stats = career[fmt]
        runs = plain(stats, 'runs')
        inns = plain(stats, 'innings')
        matches = plain(stats, 'matches')
        avg = plain(stats, 'avg')
        sr = plain(stats, 'sr')
        hs = stats.get('highest_display')
        if runs is not None and inns:
            answer = f'{name} has {runs} runs in {inns} {fmt} innings'
            if matches:
                answer += f' from {matches} matches'
            if avg:
                answer += f' at an average of {avg}'
            if sr:
                answer += f' and a strike rate of {sr}'
            if hs and hs not in ('-', '—'):
                answer += f'. Highest score: {hs}'
            add(f'How many {fmt} runs has {name} scored?', answer + '.')
        wickets = plain(stats, 'wickets')
        if stats.get('wickets') and stats['wickets'] >= 5:
            answer = f'{name} has taken {wickets} wickets in {fmt}'
            if matches:
                answer += f' from {matches} matches'
            if plain(stats, 'bowlAvg'):
                answer += f' at a bowling average of {plain(stats, "bowlAvg")}'
            if stats.get('best_bowling') and stats['best_bowling'] not in ('-', '—'):
                answer += f'. Best innings: {stats["best_bowling"]}'
            add(f'How many {fmt} wickets has {name} taken?', answer + '.')
    if not items:
        return '', None
    hundreds = sum(career[fmt].get('hundreds') or 0 for fmt in formats)
    if hundreds:
        parts = [f'{plain(career[fmt], "hundreds")} in {fmt}' for fmt in formats if career[fmt].get('hundreds')]
        add(
            f'How many international centuries does {name} have?',
            f'{name} has {hundreds:,} international hundreds: ' + '; '.join(parts) + '.',
        )
    teams = player.get('teams') or []
    if teams:
        add(
            f'Which teams has {name} played international cricket for?',
            f'{name} is recorded for {" and ".join(teams)} in this publication.',
        )
    if player.get('first') and player.get('last'):
        add(
            f'When did {name} play international cricket?',
            f'This career snapshot covers {player["first"]} to {player["last"]}. Dates follow the official record, not only the scorecard archive.',
        )
    items = items[:6]
    if not items:
        return '', None
    html_items = ''.join(f'<div><dt>{esc(q)}</dt><dd>{esc(a)}</dd></div>' for q, a in items)
    markup = (
        f'<section class="panel player-faq" id="player-questions">'
        f'<h2>Questions fans ask about {esc(name)}</h2>'
        f'<p class="muted">Answers use official career figures on this page. Archive pictures can differ when a scorecard is missing.</p>'
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


def player_person(player, pid, path, description, portraits, illustration=None, base='https://cricket.rkjat.in'):
    person = {
        '@type': 'Person',
        'name': player['name'],
        'identifier': pid,
        'url': base.rstrip('/') + path,
        'description': description,
        'jobTitle': 'Cricketer',
        'knowsAbout': 'Cricket',
    }
    if player.get('gender') == 'Men':
        person['gender'] = 'Male'
    elif player.get('gender') == 'Women':
        person['gender'] = 'Female'
    teams = player.get('teams') or []
    if teams:
        person['memberOf'] = [{'@type': 'SportsTeam', 'name': team, 'sport': 'Cricket'} for team in teams]
    if illustration:
        person['image'] = {
            '@type': 'ImageObject',
            'contentUrl': base.rstrip('/') + illustration,
            'caption': player['name'],
        }
        return person, base.rstrip('/') + illustration
    from portraits import portrait_schema
    image = portrait_schema(pid, portraits, base=base)
    if image:
        person['image'] = image
        return person, image['contentUrl']
    return person, None
