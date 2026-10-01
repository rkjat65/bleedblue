"""Ball-by-ball tables for the analytics lake: matchups, phases, overs and fantasy points.

Sources are Cricsheet's own files: the six international zips the archive
already refreshes, plus the IPL zip. Men's T20 World Cup matches that
Cricsheet withholds (Afghanistan) come from the archive's reconstructed
files in data/t20wc_matches, with names mapped to Cricsheet ids by
data/t20wc_reconstructed_ids.json.

Conventions (shared by every tool built on these tables):
- Super overs are excluded.
- Balls faced exclude wides. Runs are runs off the bat.
- A bowler is charged runs off the bat plus wides and no-balls, and bowls
  a legal ball when it is neither a wide nor a no-ball.
- A bowler's wicket excludes run outs, retirements, obstructing the field,
  handled the ball and timed out.
- Phases: T20 overs 1-6, 7-15, 16-20; ODI overs 1-10, 11-40, 41-50. Tests have none.
"""
from __future__ import annotations

import json
import zipfile
from collections import defaultdict
from pathlib import Path

import pyarrow as pa

from build_international import download
from venues import canonical_venue

try:
    import orjson
    loads = orjson.loads
except ImportError:  # CI installs only the archive requirements
    loads = json.loads

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / '.data-cache'
INTERNATIONAL = [f'{fmt}_{gender}_json.zip' for gender in ('male', 'female') for fmt in ('tests', 'odis', 't20s')]
IPL_ZIP = 'ipl_json.zip'
COMPETITION = {'Test': 'Test', 'MDM': 'Test', 'ODI': 'ODI', 'T20': 'T20I', 'IT20': 'T20I'}
NOT_BOWLER = {'run out', 'retired hurt', 'retired out', 'retired not out', 'obstructing the field', 'handled the ball', 'timed out'}
NOT_OUT = {'retired hurt', 'retired not out'}
IPL_TEAMS = {'Delhi Daredevils': 'Delhi Capitals', 'Kings XI Punjab': 'Punjab Kings',
             'Royal Challengers Bangalore': 'Royal Challengers Bengaluru', 'Rising Pune Supergiant': 'Rising Pune Supergiants'}


# Men's T20 World Cup matches are the archive's own list (Cricsheet names the event three ways and
# also uses it for regional qualifiers). Women's and ODI World Cups go by event name, qualifiers excluded.
MENS_T20WC = {p.stem for p in (ROOT / 'data/t20wc_matches').glob('*.json')}
QUALIFYING = ('Qualif', 'Region', 'Division', 'League')


def tournament(competition, event, mid=None, gender='Men'):
    name = (event or {}).get('name') or ''
    if competition == 'IPL':
        return 'IPL'
    if competition == 'T20I' and gender == 'Men':
        return 'T20 World Cup' if mid in MENS_T20WC else ''
    if any(word in name for word in QUALIFYING):
        return ''
    if competition == 'T20I' and ('T20 World Cup' in name or 'World Twenty20' in name or 'World T20' in name):
        return 'T20 World Cup'
    if competition == 'ODI' and name in ('ICC Cricket World Cup', 'ICC World Cup', 'World Cup', "ICC Women's World Cup", "Women's World Cup"):
        return 'World Cup'
    return ''


def phase(competition, over):
    """over is 0-based, as Cricsheet stores it."""
    if competition in ('T20I', 'IPL'):
        return 'Powerplay' if over < 6 else 'Middle' if over < 15 else 'Death'
    if competition == 'ODI':
        return 'Powerplay' if over < 10 else 'Middle' if over < 40 else 'Death'
    return None


def fantasy_points(s):
    """The analytics app's fantasy scoring, unchanged."""
    pts = s['runs'] + s['fours'] + 2 * s['sixes']
    pts += 16 if s['runs'] >= 100 else 8 if s['runs'] >= 50 else 0
    pts -= 2 if s['batted'] and s['out'] and s['runs'] == 0 else 0
    pts += 25 * s['wickets'] + 8 * s['lbw_bowled']
    pts += 16 if s['wickets'] >= 5 else 8 if s['wickets'] == 4 else 4 if s['wickets'] == 3 else 0
    pts += 8 * s['catches'] + 12 * s['stumpings'] + 6 * s['run_outs']
    return pts


class Lake:
    def __init__(self):
        self.matches = []
        self.names = {}            # id -> latest Cricsheet name
        self.teams = defaultdict(set)
        self.genders = defaultdict(set)
        self.matchups = defaultdict(lambda: [0, 0, 0, 0, 0, 0, 0])            # balls runs outs dots fours sixes innings
        self.phase_players = defaultdict(lambda: [0, 0, 0, 0, 0, 0, 0])       # innings balls runs outs dots fours sixes
        self.phase_teams = []
        self.overs = []
        self.fantasy = []
        self.studio = {'matches': [], 'batting': [], 'bowling': []}   # IPL rows for Studio's scorecard tables
        self.seen = set()

    # ------------------------------------------------------------ one match
    def add(self, mid, info, innings, competition, ids):
        if mid in self.seen:
            return
        self.seen.add(mid)
        date = (info.get('dates') or [''])[0]
        year = int(date[:4]) if date else None
        gender = 'Women' if info.get('gender') == 'female' else 'Men'
        tour = tournament(competition, info.get('event'), mid, gender)
        team_name = (lambda t: IPL_TEAMS.get(t, t)) if competition == 'IPL' else (lambda t: t)
        teams = [team_name(t) for t in info.get('teams') or []]
        outcome = info.get('outcome') or {}
        winner = team_name(outcome['winner']) if outcome.get('winner') else None
        toss = info.get('toss') or {}
        venue = canonical_venue(info.get('venue'), date, competition) if info.get('venue') else None
        result = 'win' if winner else outcome.get('result') or 'no result'
        if outcome.get('result') == 'tie':
            result = 'tie'
        batted_first = None
        for idx, inn in enumerate(innings):
            if inn.get('super_over'):
                continue
            batted_first = team_name(inn['team'])
            break
        self.matches.append({
            'match_id': mid, 'competition': competition, 'gender': gender, 'tournament': tour, 'season': year, 'date': date,
            'team_1': teams[0] if teams else None, 'team_2': teams[1] if len(teams) > 1 else None, 'winner': winner, 'result': result,
            'venue': venue, 'city': info.get('city'), 'toss_winner': team_name(toss['winner']) if toss.get('winner') else None,
            'toss_decision': toss.get('decision'), 'batted_first': batted_first,
            'event': (info.get('event') or {}).get('name'), 'stage': (info.get('event') or {}).get('stage'),
        })
        for name, pid in ids.items():
            self.names[pid] = name
            self.genders[pid].add(gender)
        lineups = {team_name(t): ps for t, ps in (info.get('players') or {}).items()}
        for team, ps in lineups.items():
            for p in ps:
                if p in ids:
                    self.teams[ids[p]].add(team)
        fan = defaultdict(lambda: dict(runs=0, balls=0, fours=0, sixes=0, batted=False, out=False, wickets=0, lbw_bowled=0,
                                       catches=0, stumpings=0, run_outs=0)) if competition in ('T20I', 'IPL') else None
        team_of = {}
        if fan is not None:
            for team, ps in lineups.items():
                for p in ps:
                    if p in ids:
                        fan[ids[p]]
                        team_of[ids[p]] = team
        number = 0
        for inn in innings:
            if inn.get('super_over'):
                continue
            number += 1
            bat_team = team_name(inn['team'])
            bowl_team = next((t for t in teams if t != bat_team), None)
            touched, phase_rows, over_rows = set(), {}, {}
            card_bat, card_bowl, over_spell = {}, {}, {}
            for over in inn.get('overs') or []:
                o = over.get('over', 0)
                ph = phase(competition, o)
                for d in over.get('deliveries') or []:
                    runs = d.get('runs') or {}
                    extras = d.get('extras') or {}
                    rb, total = runs.get('batter', 0), runs.get('total', 0)
                    wide, noball = extras.get('wides', 0), extras.get('noballs', 0)
                    faced, legal = not wide, not wide and not noball
                    batter, bowler = ids.get(d.get('batter')), ids.get(d.get('bowler'))
                    wickets = d.get('wickets') or []
                    bowler_wkt = [w for w in wickets if w.get('kind') not in NOT_BOWLER]
                    striker_out = any(w.get('player_out') == d.get('batter') and w.get('kind') not in NOT_BOWLER for w in wickets)
                    four, six = faced and rb == 4, faced and rb == 6
                    if competition == 'IPL':
                        for who in (d.get('batter'), d.get('non_striker')):
                            if who in ids and ids[who] not in card_bat:
                                card_bat[ids[who]] = {'runs': 0, 'balls': 0, 'fours': 0, 'sixes': 0, 'out': False, 'dismissal': None}
                        if batter:
                            c = card_bat[batter]; c['runs'] += rb; c['balls'] += faced; c['fours'] += four; c['sixes'] += six
                        for w in wickets:
                            out_id = ids.get(w.get('player_out'))
                            if out_id in card_bat and w.get('kind') not in NOT_OUT:
                                card_bat[out_id]['out'] = True; card_bat[out_id]['dismissal'] = w.get('kind')
                        if bowler:
                            b = card_bowl.setdefault(bowler, {'wickets': 0, 'legal': 0, 'conceded': 0})
                            b['wickets'] += len(bowler_wkt); b['legal'] += legal; b['conceded'] += rb + wide + noball
                            sp = over_spell.setdefault((o, bowler), [0, 0]); sp[0] += legal; sp[1] += rb + wide + noball
                    if batter and bowler:
                        m = self.matchups[(competition, gender, tour, year, batter, bowler)]
                        m[0] += faced; m[1] += rb; m[2] += striker_out; m[3] += faced and rb == 0
                        m[4] += four; m[5] += six
                        k = (mid, number, batter, bowler)
                        if k not in touched:
                            touched.add(k); m[6] += 1
                    if ph:
                        # batting by phase
                        if batter:
                            key = (competition, gender, tour, year, batter, bat_team, 'bat', ph)
                            r = self.phase_players[key]
                            ik = (mid, number) + key
                            if ik not in touched:
                                touched.add(ik); r[0] += 1
                            out_here = any(w.get('player_out') == d.get('batter') and w.get('kind') not in NOT_OUT for w in wickets)
                            r[1] += faced; r[2] += rb; r[3] += out_here; r[4] += faced and rb == 0; r[5] += four; r[6] += six
                        if bowler:
                            key = (competition, gender, tour, year, bowler, bowl_team, 'bowl', ph)
                            r = self.phase_players[key]
                            ik = (mid, number) + key
                            if ik not in touched:
                                touched.add(ik); r[0] += 1
                            conceded = rb + wide + noball
                            r[1] += legal; r[2] += conceded; r[3] += len(bowler_wkt); r[4] += legal and conceded == 0
                            r[5] += four; r[6] += six
                        t = phase_rows.setdefault(ph, [0, 0, 0, 0, 0, 0])   # balls runs wickets dots fours sixes
                        t[0] += legal; t[1] += total; t[2] += len(wickets); t[3] += legal and total == 0; t[4] += four; t[5] += six
                        ov = over_rows.setdefault(o + 1, [0, 0, 0])
                        ov[0] += legal; ov[1] += total; ov[2] += len(wickets)
                    if fan is not None:
                        if batter:
                            s = fan[batter]; team_of.setdefault(batter, bat_team)
                            s['batted'] = True; s['runs'] += rb; s['balls'] += faced; s['fours'] += four; s['sixes'] += six
                        if d.get('non_striker') in ids:
                            fan[ids[d['non_striker']]]['batted'] = True
                            team_of.setdefault(ids[d['non_striker']], bat_team)
                        if bowler:
                            team_of.setdefault(bowler, bowl_team)
                            fan[bowler]['wickets'] += len(bowler_wkt)
                            fan[bowler]['lbw_bowled'] += sum(w.get('kind') in ('lbw', 'bowled') for w in bowler_wkt)
                        for w in wickets:
                            out_id = ids.get(w.get('player_out'))
                            if out_id and w.get('kind') not in NOT_OUT:
                                fan[out_id]['out'] = True
                            fielders = [f.get('name') for f in w.get('fielders') or [] if f.get('name')]
                            first = ids.get(fielders[0]) if fielders else None
                            if first and w.get('kind') == 'caught':
                                fan[first]['catches'] += 1
                            elif first and w.get('kind') == 'stumped':
                                fan[first]['stumpings'] += 1
                            elif first and w.get('kind') == 'run out':
                                fan[first]['run_outs'] += 1
            if competition == 'IPL':
                base = {'match_id': mid, 'date': date, 'year': year, 'format': 'IPL', 'gender': gender, 'innings_number': number, 'venue': venue}
                for pos, (pid, c) in enumerate(card_bat.items(), 1):
                    self.studio['batting'].append({**base, 'player_id': pid, 'team': bat_team, 'opponent': bowl_team, 'position': pos, **c})
                maidens = defaultdict(int)
                for (o, pid), (balls, conceded) in over_spell.items():
                    maidens[pid] += balls >= 6 and conceded == 0
                for pid, b in card_bowl.items():
                    self.studio['bowling'].append({**base, 'player_id': pid, 'team': bowl_team, 'opponent': bat_team, 'maidens': maidens[pid], **b})
            for ph, t in phase_rows.items():
                self.phase_teams.append({'match_id': mid, 'innings': number, 'team': bat_team, 'opponent': bowl_team, 'phase': ph,
                                         'balls': t[0], 'runs': t[1], 'wickets': t[2], 'dots': t[3], 'fours': t[4], 'sixes': t[5]})
            for o, v in over_rows.items():
                self.overs.append({'match_id': mid, 'innings': number, 'team': bat_team, 'over': o, 'balls': v[0], 'runs': v[1], 'wickets': v[2]})
        if competition == 'IPL':
            by = outcome.get('by') or {}
            self.studio['matches'].append({'match_id': mid, 'date': date, 'year': year, 'format': 'IPL', 'gender': gender,
                                           'team_1': teams[0] if teams else None, 'team_2': teams[1] if len(teams) > 1 else None,
                                           'winner': winner, 'result': outcome.get('result'), 'margin_runs': by.get('runs'),
                                           'margin_wickets': by.get('wickets'), 'venue': venue, 'city': info.get('city'),
                                           'series': 'Indian Premier League', 'coverage': 'ball-by-ball'})
        if fan is not None:
            for pid, s in fan.items():
                team = team_of.get(pid)
                if not team:
                    continue
                self.fantasy.append({'match_id': mid, 'competition': competition, 'gender': gender, 'tournament': tour, 'season': year,
                                     'date': date, 'team': team, 'opponent': next((t for t in teams if t != team), None), 'venue': venue,
                                     'player_id': pid, 'runs': s['runs'], 'balls': s['balls'], 'fours': s['fours'], 'sixes': s['sixes'],
                                     'out': s['out'], 'wickets': s['wickets'], 'lbw_bowled': s['lbw_bowled'], 'catches': s['catches'],
                                     'stumpings': s['stumpings'], 'run_outs': s['run_outs'], 'points': fantasy_points(s)})

    # ------------------------------------------------------------ sources
    def add_zip(self, path, competition=None):
        with zipfile.ZipFile(path) as archive:
            for filename in archive.namelist():
                if not filename.endswith('.json'):
                    continue
                data = loads(archive.read(filename))
                info = data.get('info') or {}
                comp = competition or COMPETITION.get(info.get('match_type'))
                if not comp or info.get('team_type', 'international') != ('club' if comp == 'IPL' else 'international'):
                    continue
                ids = (info.get('registry') or {}).get('people') or {}
                self.add(Path(filename).stem, info, data.get('innings') or [], comp, ids)

    def add_reconstructed(self, folder, id_map):
        """Men's T20 World Cup matches Cricsheet withholds, from the archive's compact files."""
        for path in sorted(Path(folder).glob('*.json')):
            data = json.loads(path.read_text(encoding='utf-8'))
            match = data['match']
            if match.get('source') == 'Cricsheet' or not data.get('deliveries') or match['id'] in self.seen:
                continue
            ix = {k: i for i, k in enumerate(data['fields'])}
            ids, innings = {}, {}
            for row in data['deliveries']:
                if row[ix['super_over']]:
                    continue
                bat_team, bowl_team = row[ix['batting_team']], row[ix['bowling_team']]
                for key, team in (('batter', bat_team), ('non_striker', bat_team), ('bowler', bowl_team), ('player_out', bat_team)):
                    name = row[ix[key]]
                    if name and name in id_map.get(team, {}):
                        ids[name] = id_map[team][name]['id']
                inn = innings.setdefault(row[ix['innings']], {'team': bat_team, 'overs': {}})
                extras = row[ix['extras']] or 0
                delivery = {'batter': row[ix['batter']], 'bowler': row[ix['bowler']], 'non_striker': row[ix['non_striker']],
                            'runs': {'batter': row[ix['batter_runs']], 'extras': extras, 'total': row[ix['total_runs']]},
                            # The compact rows keep legality, not the extras type: an illegal ball faced is a no-ball, otherwise a wide.
                            'extras': ({} if row[ix['legal']] else {'noballs': 1} if row[ix['batter_ball']] else {'wides': max(1, extras)})}
                if row[ix['wicket']]:
                    delivery['wickets'] = [{'player_out': row[ix['player_out']], 'kind': row[ix['wicket_kind']]}]
                inn['overs'].setdefault(row[ix['over']], []).append(delivery)
            info = {'dates': [match['date']], 'gender': 'male', 'teams': match['teams'], 'venue': match.get('venue'),
                    'outcome': match.get('result') or {}, 'event': {'name': "ICC Men's T20 World Cup"}}
            ordered = [{'team': inn['team'], 'overs': [{'over': o, 'deliveries': ds} for o, ds in sorted(inn['overs'].items())]}
                       for _, inn in sorted(innings.items())]
            self.add(match['id'], info, ordered, 'T20I', ids)


def table(rows, columns=None):
    if columns:
        return pa.table(columns)
    return pa.Table.from_pylist(rows)


def build(write_table, refresh=False, people_names=None, routes=None):
    """Build every ball table with `write_table(name, rows_or_table)`; returns manifest entries."""
    CACHE.mkdir(exist_ok=True)
    lake = Lake()
    for name in INTERNATIONAL:
        print('Ball lake:', name, flush=True)
        lake.add_zip(download(name, refresh))
    id_map = json.loads((ROOT / 'data/t20wc_reconstructed_ids.json').read_text(encoding='utf-8'))
    lake.add_reconstructed(ROOT / 'data/t20wc_matches', id_map)
    print('Ball lake:', IPL_ZIP, flush=True)
    lake.add_zip(download(IPL_ZIP, refresh), 'IPL')

    people_names = people_names or {}
    routes = routes or {}
    players = [{'player_id': pid, 'name': people_names.get(pid) or name, 'teams': ' / '.join(sorted(lake.teams.get(pid, ()))),
                'gender': ' / '.join(sorted(lake.genders.get(pid, ()))), 'path': routes.get(pid)} for pid, name in lake.names.items()]
    players.sort(key=lambda p: p['player_id'])
    matchups = sorted(lake.matchups.items(), key=lambda kv: (kv[0][4], kv[0][5], kv[0][0], kv[0][3] or 0))
    mcols = ('competition', 'gender', 'tournament', 'year', 'batter_id', 'bowler_id')
    vcols = ('balls', 'runs', 'outs', 'dots', 'fours', 'sixes', 'innings')
    matchup_table = pa.table({**{c: [k[i] for k, _ in matchups] for i, c in enumerate(mcols)},
                              **{c: pa.array([v[i] for _, v in matchups], pa.int32()) for i, c in enumerate(vcols)}})
    phases = sorted(lake.phase_players.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][3] or 0, kv[0][4]))
    pcols = ('competition', 'gender', 'tournament', 'year', 'player_id', 'team', 'role', 'phase')
    pvals = ('innings', 'balls', 'runs', 'outs', 'dots', 'fours', 'sixes')
    phase_table = pa.table({**{c: [k[i] for k, _ in phases] for i, c in enumerate(pcols)},
                            **{c: pa.array([v[i] for _, v in phases], pa.int32()) for i, c in enumerate(pvals)}})
    order = {m['match_id']: (m['competition'], m['gender'], m['season'] or 0, m['date']) for m in lake.matches}
    lake.matches.sort(key=lambda m: order[m['match_id']])
    lake.phase_teams.sort(key=lambda r: (order[r['match_id']], r['match_id'], r['innings'], r['phase']))
    lake.overs.sort(key=lambda r: (order[r['match_id']], r['match_id'], r['innings'], r['over']))
    lake.fantasy.sort(key=lambda r: (r['competition'], r['gender'], r['team'] or '', r['date'], r['match_id']))
    tables = {
        'ball_matches': write_table('ball_matches', lake.matches),
        'ball_players': write_table('ball_players', players),
        'ball_matchups': write_table('ball_matchups', matchup_table),
        'ball_phase_players': write_table('ball_phase_players', phase_table),
        'ball_phase_teams': write_table('ball_phase_teams', lake.phase_teams),
        'ball_overs': write_table('ball_overs', lake.overs),
        'ball_fantasy': write_table('ball_fantasy', lake.fantasy),
    }
    names = {p['player_id']: p['name'] for p in players}
    for key in ('batting', 'bowling'):
        for row in lake.studio[key]:
            row['player'] = names.get(row['player_id'], row['player_id'])
    return tables, lake.studio
