"""IPL scorecards built into the site at the app's own addresses.

Merge step 5 moves the app's pages into this static build one type at a
time. Caddy serves a static file under /ipl or /t20-world-cup when the build
has one and falls back to the app otherwise, so addresses never change.

IPL scorecards come from Cricsheet's IPL zip and use the same scorecard
template as international matches. T20 World Cup matches already have
international scorecards here, so their app addresses point to those.
"""
from __future__ import annotations

import html
import json
import zipfile
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

from build_international import NON_BOWLER

IPL_TEAMS = {'Delhi Daredevils': 'Delhi Capitals', 'Kings XI Punjab': 'Punjab Kings',
             'Royal Challengers Bangalore': 'Royal Challengers Bengaluru', 'Rising Pune Supergiant': 'Rising Pune Supergiants'}
# Short names and club colours for the badges (no flags for franchises).
CLUBS = {
    'Chennai Super Kings': ('CSK', '#F9CD05'), 'Mumbai Indians': ('MI', '#1E6AC9'), 'Royal Challengers Bengaluru': ('RCB', '#EC1C24'),
    'Kolkata Knight Riders': ('KKR', '#6B3FA0'), 'Sunrisers Hyderabad': ('SRH', '#FF822A'), 'Delhi Capitals': ('DC', '#2A64C5'),
    'Punjab Kings': ('PBKS', '#DD1F2D'), 'Rajasthan Royals': ('RR', '#EA1A85'), 'Gujarat Titans': ('GT', '#5B7CB8'),
    'Lucknow Super Giants': ('LSG', '#3FA9F5'), 'Deccan Chargers': ('DEC', '#8DA9C4'), 'Kochi Tuskers Kerala': ('KTK', '#E36F1E'),
    'Pune Warriors': ('PWI', '#3B9AD9'), 'Gujarat Lions': ('GL', '#E04F16'), 'Rising Pune Supergiants': ('RPS', '#B5458F'),
}
SECTION = [('/dashboard', 'Overview'), ('/matches', 'Matches'), ('/batting', 'Batting'), ('/bowling', 'Bowling'), ('/players', 'Players'),
           ('/records', 'Records'), ('/teams', 'Teams'), ('/venues', 'Venues'), ('/seasons', 'Seasons')]


def esc(value):
    return html.escape(str(value if value is not None else ''), quote=True)


def club(team):
    return IPL_TEAMS.get(team, team)


def club_badge(team, path=None):
    short, colour = CLUBS.get(club(team), (''.join(w[0] for w in team.split()[:3]).upper(), '#8888A0'))
    mark = f'<span class="team-badge club-badge"><span class="club-mark" style="--club:{colour}">{esc(short)}</span><span>{esc(team)}</span></span>'
    return f'<a class="team-badge-link" href="{esc(path)}">{mark}</a>' if path else mark


def section_bar(prefix, active='/matches'):
    """The IPL / T20 World Cup section links, as on the app's own pages."""
    toggle = ''.join(f'<a href="{p}{active}"{" aria-current=page" if p == prefix else ""}>{t}</a>' for p, t in (('/ipl', 'IPL'), ('/t20-world-cup', 'T20 WC')))
    links = ''.join(f'<a href="{prefix}{path}"{" aria-current=page" if path == active else ""}>{label}</a>' for path, label in SECTION)
    return f'<nav class="league-bar" aria-label="IPL and T20 World Cup pages"><span class="league-toggle">{toggle}</span><span class="league-links">{links}</span></nav>'


def card_from(raw, mid):
    """A scorecard in the same shape as build_international's, without career totals."""
    info = raw['info']
    gender = 'Women' if info.get('gender') == 'female' else 'Men'
    registry = info.get('registry', {}).get('people', {})
    key_for = lambda name: registry.get(name, gender + ':' + name)  # noqa: E731
    players = {team: [{'id': key_for(n), 'name': n} for n in names] for team, names in info.get('players', {}).items()}
    cards = []
    for inning in raw.get('innings', []):
        batting, bowling = {}, {}
        runs = wickets = legal = extra = 0
        fall, timeline = [], []
        for over in inning.get('overs', []):
            over_runs = over_wkts = 0
            spell = defaultdict(lambda: [0, 0])
            for d in over['deliveries']:
                batter, bowler = d['batter'], d['bowler']
                b = batting.setdefault(batter, {'name': batter, 'id': key_for(batter), 'runs': 0, 'balls': 0, 'fours': 0, 'sixes': 0, 'out': False, 'dismissal': 'not out'})
                batting.setdefault(d['non_striker'], {'name': d['non_striker'], 'id': key_for(d['non_striker']), 'runs': 0, 'balls': 0, 'fours': 0, 'sixes': 0, 'out': False, 'dismissal': 'not out'})
                w = bowling.setdefault(bowler, {'name': bowler, 'id': key_for(bowler), 'balls': 0, 'runs': 0, 'wickets': 0, 'maidens': 0, 'wides': 0, 'noballs': 0})
                r, e = d['runs'], d.get('extras', {})
                is_legal = not (e.get('wides') or e.get('noballs'))
                charged = r['total'] - e.get('byes', 0) - e.get('legbyes', 0) - e.get('penalty', 0)
                runs += r['total']; over_runs += r['total']; legal += is_legal; extra += r['extras']
                b['runs'] += r['batter']; b['balls'] += not e.get('wides', 0)
                b['fours'] += r['batter'] == 4 and not r.get('non_boundary', False)
                b['sixes'] += r['batter'] == 6 and not r.get('non_boundary', False)
                w['balls'] += is_legal; w['runs'] += charged
                w['wides'] += e.get('wides', 0); w['noballs'] += e.get('noballs', 0)
                spell[bowler][0] += is_legal; spell[bowler][1] += charged
                for wicket in d.get('wickets', []):
                    kind, name = wicket['kind'], wicket['player_out']
                    out = kind not in {'retired hurt'}
                    if name in batting:
                        batting[name].update({'dismissal_kind': kind, 'dismissal_bowler': key_for(bowler), 'out': out,
                                              'fielders': [key_for(f['name']) for f in wicket.get('fielders', []) if f.get('name')],
                                              'dismissal': kind + (' b ' + bowler if kind not in NON_BOWLER else '')})
                    wickets += out; over_wkts += out
                    w['wickets'] += kind not in NON_BOWLER
                    if out:
                        fall.append({'player': name, 'runs': runs, 'wicket': wickets, 'balls': legal})
            for who, (count, cost) in spell.items():
                bowling[who]['maidens'] += count == 6 and cost == 0
            timeline.append({'over': over['over'] + 1, 'runs': over_runs, 'wickets': over_wkts, 'total': runs})
        cards.append({'team': inning['team'], 'runs': runs, 'wickets': wickets, 'balls': legal, 'extras': extra,
                      'super_over': inning.get('super_over', False), 'declared': False, 'batting': list(batting.values()),
                      'bowling': list(bowling.values()), 'fall': fall, 'overs': timeline})
    event = info.get('event', {})
    match = {'id': mid, 'date': info['dates'][0], 'format': 'T20', 'gender': gender, 'teams': info['teams'], 'venue': info.get('venue', ''),
             'city': info.get('city', ''), 'event': event.get('name', ''), 'season': str(info.get('season', '')), 'match_number': event.get('match_number'),
             'stage': event.get('stage'), 'outcome': info.get('outcome', {}),
             'totals': [{k: c[k] for k in ('team', 'runs', 'wickets', 'balls', 'super_over')} for c in cards]}
    target = next((inn['target'] for inn in raw.get('innings', []) if inn.get('target') and not inn.get('super_over')), None)
    return {'match': match, 'innings': cards, 'players': players, 'toss': info.get('toss', {}), 'awards': info.get('player_of_match', []), 'target': target}


def ipl_cards(zip_path):
    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            mid = Path(name).stem
            if name.endswith('.json') and mid.isdigit():
                yield card_from(json.loads(archive.read(name)), mid)


def links_for(card, people, pp):
    """Names and links for every player in a card: site profiles' IPL tab, else the app's profile."""
    lpeople, lpp = {}, {}
    names = {p['id']: p['name'] for squad in card['players'].values() for p in squad}
    for inn in card['innings']:
        for row in inn['batting'] + inn['bowling']:
            names.setdefault(row['id'], row['name'])
    for pid, name in names.items():
        if pid in pp and pid in people:
            lpeople[pid] = {'name': people[pid]['name']}
            lpp[pid] = pp[pid] + '#ipl'
        else:
            lpeople[pid] = {'name': name}
            lpp[pid] = '/ipl/players/' + quote(name, safe='')
    return lpeople, lpp


def league_gp(card):
    m = card['match']
    return {'teams': {t: '/ipl/teams/' + quote(club(t), safe='') for t in m['teams']},
            'grounds': {m['venue']: '/ipl/venues/' + quote(m['venue'], safe='')},
            'series': {m['event']: '/ipl/seasons/' + quote(m['season'], safe='')} if m.get('event') else {}}


def label(m):
    bits = [f'IPL {m["date"][:4]}']   # Cricsheet labels early seasons '2007/08'; the IPL calls it 2008
    if m.get('match_number'):
        bits.append(f'match {m["match_number"]}')
    elif m.get('stage'):
        bits.append(str(m['stage']))
    return ', '.join(bits)
