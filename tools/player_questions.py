"""Dedicated, crawlable URLs for the cricket questions fans search.

Each page is one official-career fact (runs, average, wickets, centuries, sixes)
plus links back to the player profile. Thin careers are not given their own URL.
"""
from __future__ import annotations

import cricket_charts as cw
from player_profile import (
    DASHES, clip_meta, esc, formats_present, primary_role, question_specs, slug,
)

PUBLISH_KINDS = {'runs', 'avg', 'wickets', 'hundreds', 'sixes'}


def select_question_players(people, featured_names=(), extra_ids=()):
    chosen = set()
    featured_names = set(featured_names or ())
    extra_ids = set(extra_ids or ())
    for pid, player in people.items():
        career = player.get('career') or {}
        if not career:
            continue
        if player.get('name') in featured_names or pid in extra_ids:
            chosen.add(pid)
            continue
        runs = sum(s.get('runs') or 0 for s in career.values())
        wickets = sum(s.get('wickets') or 0 for s in career.values())
        if runs >= 1500 or wickets >= 50:
            chosen.add(pid)
    return chosen


def prepare_player_questions(people, player_paths, featured_names=(), extra_ids=(), reserved=None):
    """Assign unique /questions/... URLs for notable players."""
    reserved = set(reserved or ())
    used_titles = set()
    bundle = {}
    for pid in sorted(select_question_players(people, featured_names, extra_ids)):
        player = people[pid]
        path = player_paths.get(pid, '')
        name_slug = slug(player['name'])
        specs = []
        urls = {}
        for spec in question_specs(player, name_slug=name_slug):
            if spec['kind'] not in PUBLISH_KINDS or not spec['publishable']:
                continue
            key = spec['slug']
            if key in reserved:
                key = key + '-' + pid
                spec = {**spec, 'slug': key}
            reserved.add(key)
            spec['url'] = '/questions/' + key + '/'
            spec['player_id'] = pid
            spec['player_url'] = path
            specs.append(spec)
            urls[spec['slug']] = spec['url']
        for spec in specs:
            title = spec['title']
            if title in used_titles:
                spec['title'] = title.rstrip('?') + ' · ' + pid + '?'
            used_titles.add(spec['title'])
        if specs:
            bundle[pid] = {'specs': specs, 'urls': urls, 'name_slug': name_slug}
    return bundle


def _records_path(player, spec):
    gender = 'women' if player.get('gender') == 'Women' else 'men'
    fmt = (spec.get('format') or 'odi').lower()
    kind = spec['kind']
    leaf = {
        'runs': 'most-runs',
        'wickets': 'most-wickets',
        'avg': 'best-batting-average',
        'hundreds': 'most-centuries',
        'sixes': 'most-sixes',
    }.get(kind)
    if not leaf or kind == 'hundreds' and not spec.get('format'):
        if kind == 'hundreds':
            return f'/records/{gender}/odi/most-centuries/'
        return '/records/'
    return f'/records/{gender}/{fmt}/{leaf}/'


def _metric_chart(player, spec):
    career = player.get('career') or {}
    formats = formats_present(career)
    key = {'runs': 'runs', 'avg': 'avg', 'wickets': 'wickets', 'hundreds': 'hundreds', 'sixes': 'sixes'}.get(spec['kind'])
    if not key:
        return ''
    items = [(fmt, career[fmt].get(key)) for fmt in formats]
    if sum(value is not None for _, value in items) < 2:
        return ''
    caption = f'{player["name"]}: official {spec["unit"].split()[-1] if spec.get("unit") else key} by format'
    if spec['kind'] == 'avg':
        caption = f'{player["name"]}: batting average by format'
    elif spec['kind'] == 'runs':
        caption = f'{player["name"]}: official career runs by format'
    elif spec['kind'] == 'wickets':
        caption = f'{player["name"]}: official career wickets by format'
    return cw.hbars(items, caption, 'Official career snapshot. Formats without a recorded value stay blank.')


def question_page(spec, player, related, snapshot=''):
    name = player['name']
    hero = spec.get('hero') or ''
    unit = spec.get('unit') or ''
    profile = spec.get('player_url') or '/players/'
    records = _records_path(player, spec)
    body = (
        f'<p class="eyebrow">PLAYER STATS</p>'
        f'<div class="question-hero"><strong>{esc(hero)}</strong><span>{esc(unit)}</span></div>'
        f'<article class="research-article question-article"><p class="question-answer">{esc(spec["answer"])}</p>'
        f'{_metric_chart(player, spec)}'
        f'<h2>See the full {esc(name)} record</h2>'
        f'<p>This is the official international snapshot, not a scorecard sample. '
        f'<a href="{esc(profile)}">{esc(name)} career profile</a> has format cards, pictures and the complete batting, bowling and fielding tables. '
        f'<a href="{esc(records)}">Open the related leaderboard</a> to see this figure in rank order.</p>'
    )
    if related:
        links = ''.join(
            f'<a class="feature-card" href="{esc(item["url"])}"><span>{esc(item.get("format") or "Career")}</span>'
            f'<h2>{esc(item["title"])}</h2><p>{esc(item["description"])}</p></a>'
            for item in related[:5]
        )
        body += f'<h2>More {esc(name)} questions</h2><div class="grid two question-related">{links}</div>'
    note = 'Official career figures. A missing field stays missing; it is never inferred from a partial scorecard.'
    if snapshot:
        note = f'Career records checked: {esc(snapshot)}. ' + note
    body += f'<p class="note">{note}</p></article>'
    return body


def featured_question_cards(bundle, people, featured_names):
    cards = []
    seen = set()
    for name in featured_names:
        match = next(((pid, player) for pid, player in people.items() if player.get('name') == name), None)
        if not match or match[0] not in bundle:
            continue
        specs = bundle[match[0]]['specs']
        role = primary_role(match[1].get('career') or {})

        def hero_n(spec):
            try:
                return int(str(spec.get('hero') or '0').replace(',', ''))
            except ValueError:
                return 0

        wickets = next((s for s in specs if s['kind'] == 'wickets' and s.get('format') == 'Test'), None) or next((s for s in specs if s['kind'] == 'wickets'), None)
        runs = next((s for s in specs if s['kind'] == 'runs' and s.get('format') == 'ODI'), None) or next((s for s in specs if s['kind'] == 'runs'), None)
        if role == 'bowler' or (wickets and hero_n(wickets) >= 150 and hero_n(runs) < 2000):
            pick = wickets or runs
        else:
            pick = runs or wickets
        if pick is None and specs:
            pick = specs[0]
        if pick and pick['url'] not in seen:
            seen.add(pick['url'])
            cards.append(pick)
    return cards


def player_question_directory(bundle, people, player_paths, table):
    rows = []
    for pid, pack in sorted(bundle.items(), key=lambda item: people[item[0]]['name']):
        player = people[pid]
        count = str(len(pack['specs']))
        first = pack['specs'][0]['url']
        name = f'<a href="{esc(player_paths[pid])}">{esc(player["name"])}</a>'
        ask = f'<a href="{esc(first)}">{count} questions</a>'
        rows.append([name, esc(' / '.join(player.get('teams') or [])), esc(player.get('gender') or ''), ask])
    body = (
        '<section class="page-head"><div class="eyebrow">PLAYER STATS QUESTIONS</div>'
        '<h1>International player questions</h1>'
        '<p>Each linked question is a dedicated page with the official career figure in the heading, the HTML and the search snippet.</p></section>'
        '<p>These pages cover established internationals: 1,500 career runs or 50 wickets, plus featured names. '
        'Shorter careers keep their answers on the player profile.</p>'
    )
    body += table(['Player', 'Teams', 'Gender', 'Questions'], rows, caption='Player stats questions from official careers')
    return body


def assert_clean_bundle(bundle):
    titles = []
    for pack in bundle.values():
        for spec in pack['specs']:
            for mark in DASHES:
                if mark in spec['title'] or mark in spec['answer'] or mark in spec['description']:
                    raise ValueError('Question copy must not use em or en dashes: ' + spec['title'])
            titles.append(spec['title'])
    if len(titles) != len(set(titles)):
        raise ValueError('Duplicate player question titles')
    return True
