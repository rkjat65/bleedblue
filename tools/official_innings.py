"""Reconcile scorecards with the official innings lists, innings by innings.

Career totals come from Statsguru, scorecards from Cricsheet and ESPNcricinfo. They disagree in small,
repeatable ways: a batter who walked in but faced no ball (a declaration, a timed out), an associate match
card that leaves a batter out, a run or a wicket credited differently. For every player whose scorecards do
not add up to the official career, `python tools/official_innings.py` fetches that player's official
innings list and writes the differences to data/official_innings_overlay.json. `apply_overlay` lays them
over the scorecards on every build, so a daily Cricsheet refresh never undoes them.
"""
import json
import re
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OVERLAY = ROOT / 'data/official_innings_overlay.json'
CACHE = ROOT / '.data-cache/official-innings'
CLASS_OF = {('Test', 'Men'): 1, ('ODI', 'Men'): 2, ('T20I', 'Men'): 3, ('Test', 'Women'): 8, ('ODI', 'Women'): 9, ('T20I', 'Women'): 10}


def norm(label):
    label = re.sub(r'\s*(?:women|wmn|\(women\)|-w|\bw)$', '', label.strip(), flags=re.I)
    return re.sub(r'[^a-z]', '', label.lower().replace('&', 'and'))


def team_score(label, team):
    """How well an official opposition label ('P.N.G.', 'CRC-W', 'Czech Rep.') names a team: 3 exact, prefix or initials, 1 an abbreviation."""
    l, t = norm(label), norm(team)
    if not l or not t:
        return 0
    words = [w for w in re.split(r'[^a-z]+', team.lower().replace(' and ', ' ')) if w]
    initials = ''.join(w[0] for w in words)
    if l == t or t.startswith(l) or l.startswith(t) or l == initials:
        return 3
    it = iter(t)
    abbreviation = len(l) <= 4 and l[0] == t[0] and all(ch in it for ch in l)   # the letters in order
    # a name of several words must also start as its initials do (U.A.E. is not the United States)
    return 1 if abbreviation and (len(words) == 1 or l.startswith(initials[:2])) else 0


def same_team(label, team):
    return team_score(label, team) > 0


def near(date):
    """The date and the days either side: sources date a late finish or a time zone differently."""
    day = datetime.strptime(date, '%Y-%m-%d')
    return [date] + [(day + timedelta(days=n)).strftime('%Y-%m-%d') for n in (-1, 1)]


def iso(text):
    try:
        return datetime.strptime(text, '%d %b %Y').strftime('%Y-%m-%d')
    except ValueError:
        return text


def number(text):
    text = re.sub(r'[^0-9.]', '', text or '')
    return int(float(text)) if text else None


def official_rows(eid, cls, kind):
    """The player's official innings, one dict per innings batted or bowled."""
    from import_careers import fetch
    from bs4 import BeautifulSoup
    file = CACHE / f'{eid}-{cls}-{kind}.json'
    if file.exists():
        return json.loads(file.read_text(encoding='utf-8'))
    url = f'https://stats.cricinfo.com/ci/engine/player/{eid}.html?class={cls};template=results;type={kind};view=innings'
    soup = BeautifulSoup(fetch(url), 'html.parser')
    table = next((t for t in soup.select('table.engineTable') if t.find('caption') and 'Innings by innings' in t.find('caption').get_text()), None)
    if table is None:
        raise ValueError('Official innings list is absent for ' + eid)
    heads = [h.get_text(' ', strip=True) for h in table.select('thead th')]
    rows = []
    for tr in table.select('tbody tr'):
        cells = [c.get_text(' ', strip=True) for c in tr.find_all('td')]
        if len(cells) < len(heads):
            continue
        row = dict(zip(heads, cells))
        first = cells[0]
        if first in ('DNB', 'TDNB', 'absent', 'sub') or (kind == 'bowling' and first in ('DNB', 'TDNB', 'sub')):
            continue
        rows.append({'date': iso(row['Start Date']), 'opp': row['Opposition'].replace('v ', '', 1), 'inns': number(row.get('Inns')), 'pos': number(row.get('Pos')),
                     'runs': number(row['Runs']), 'notout': first.endswith('*'), 'balls': number(row.get('BF')), 'fours': number(row.get('4s')), 'sixes': number(row.get('6s')),
                     'dismissal': row.get('Dismissal', ''), 'overs': row.get('Overs'), 'maidens': number(row.get('Mdns')), 'wickets': number(row.get('Wkts'))} if kind == 'batting' else
                    {'date': iso(row['Start Date']), 'opp': row['Opposition'].replace('v ', '', 1), 'inns': number(row.get('Inns')), 'pos': number(row.get('Pos')),
                     'overs': row['Overs'], 'maidens': number(row.get('Mdns')), 'runs': number(row['Runs']), 'wickets': number(row['Wkts'])})
    CACHE.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(rows), encoding='utf-8')
    time.sleep(.15)
    return rows


def balls_of(overs):
    whole, _, part = (overs or '0').partition('.')
    return int(whole or 0) * 6 + int(part or 0)


def survey(cards, people):
    """Per person and format: the scorecard rows, keyed so a difference can be placed in a match."""
    bat, bowl, where = defaultdict(list), defaultdict(list), defaultdict(list)
    for mid, card in cards.items():
        fmt = card['match']['format']
        for team, squad in (card.get('players') or {}).items():
            for p in squad:
                if p.get('id'):
                    where[p['id'], card['match']['date']].append((mid, team))
        for idx, inn in enumerate(card['innings']):
            if inn.get('super_over'):
                continue
            for b in inn['batting']:
                bat[b['id'], fmt].append((mid, idx, inn['team'], b))
            for b in inn.get('bowling', []):
                bowl[b['id'], fmt].append((mid, idx, inn['team'], b))
    return bat, bowl, where


def gaps(cards, people, bat, bowl):
    out = []
    for pid, p in people.items():
        for fmt, c in (p.get('career') or {}).items():
            rows = [r for r in bat.get((pid, fmt), [])]
            bowls = bowl.get((pid, fmt), [])
            ours_wk = sum(b[3].get('wickets') or 0 for b in bowls)
            if ((c.get('innings') or 0) != len(rows) or (c.get('runs') or 0) != sum(r[3].get('runs') or 0 for r in rows)
                    or (c.get('wickets') or 0) != ours_wk or (c.get('bowling_innings') or 0) != len(bowls)):
                out.append((pid, fmt))
    return out


def reconcile(pid, fmt, people, cards, bat, bowl, where):
    p = people[pid]
    eid = p.get('espn_id')
    if not eid:
        return [], ['no espn id']
    cls = CLASS_OF.get((fmt, p.get('gender')))
    ops, notes, aliases = [], [], []
    for kind, ours_all in (('batting', bat), ('bowling', bowl)):
        ours = ours_all.get((pid, fmt), [])
        try:
            official = official_rows(eid, cls, kind)
        except Exception as error:   # one unreachable page never stops the pass
            notes.append(f'{kind} unavailable: {error!r}'[:120])
            continue
        mine = defaultdict(list)
        for mid, idx, team, b in ours:
            mine[mid].append((idx, team, b))
        # Place each official innings in a match: the matches this person played on that date. Two on one
        # day are told apart by the opposition, then by a row that already carries the same runs.
        by_match = defaultdict(list)
        for row in official:
            options = [m for m in where.get((pid, row['date']), []) if cards[m[0]]['match']['format'] == fmt]
            if not options:   # the match is dated a day either side in the scorecards
                options = [m for d in near(row['date'])[1:] for m in where.get((pid, d), [])
                           if cards[m[0]]['match']['format'] == fmt and any(same_team(row['opp'], t) for t in cards[m[0]]['match']['teams'] if t != m[1])]
            if len(options) > 1:
                def rank(m):
                    others = [t for t in cards[m[0]]['match']['teams'] if t != m[1]]
                    same = any(r[2].get('runs') == row.get('runs') and (kind != 'batting' or r[2].get('balls') == row.get('balls')) for r in mine.get(m[0], []))
                    return (max((team_score(row['opp'], t) for t in others), default=0), same)
                best = max(rank(m) for m in options)
                options = [m for m in options if rank(m) == best]
            if not options:
                src = alias_evidence(pid, fmt, kind, row, people, cards)
                if src:
                    aliases.append((src, eid))
                    continue
            if len(options) != 1:
                notes.append(f'{kind} {row["date"]} {row["opp"]}: {len(options)} matches')
                continue
            by_match[options[0]].append(row)
        # a row we hold in a match the official list never mentions is not that person's
        for mid in mine:
            if not any(key[0] == mid for key in by_match) and not any(row for row in official if cards[mid]['match']['date'] in near(row['date'])):
                for idx, team, b in mine[mid]:
                    ops.append({'op': 'drop_' + kind, 'match': mid, 'team': team, 'inn': idx, 'id': eid})
        for (mid, team), rows in by_match.items():
            have = sorted(mine.get(mid, []), key=lambda r: r[0])
            rows = sorted(rows, key=lambda r: (r['inns'] or 9))
            for k, row in enumerate(rows):
                if k < len(have):
                    idx, _, b = have[k]
                    if kind == 'batting':
                        if (b.get('runs'), bool(b.get('out'))) != (row['runs'], not row['notout']) or (row['balls'] is not None and b.get('balls') != row['balls']):
                            ops.append({'op': 'fix_batting', 'match': mid, 'team': team, 'inn': idx, 'id': eid, 'runs': row['runs'], 'balls': row['balls'], 'out': not row['notout']})
                    elif (b.get('wickets'), b.get('runs')) != (row['wickets'], row['runs']):
                        ops.append({'op': 'fix_bowling', 'match': mid, 'team': team, 'inn': idx, 'id': eid, 'wickets': row['wickets'], 'runs': row['runs']})
                else:
                    card = cards[mid]
                    want_team = team if kind == 'batting' else next((t for t in card['match']['teams'] if t != team), None)
                    # the innings of this side, by the official innings number where it fits
                    candidates = [i for i, inn in enumerate(card['innings']) if inn['team'] == want_team and not inn.get('super_over')]
                    if not candidates:
                        notes.append(f'{kind} {row["date"]}: no innings for {want_team}')
                        continue
                    n = row['inns']
                    target = next((i for i in candidates if n and i == n - 1), None)
                    if target is None:
                        used = {h[0] for h in have}
                        target = next((i for i in candidates if i not in used), candidates[-1])
                    if kind == 'batting':
                        ops.append({'op': 'add_batting', 'match': mid, 'team': team, 'inn': target, 'id': eid, 'pos': row['pos'], 'runs': row['runs'], 'balls': row['balls'],
                                    'fours': row['fours'], 'sixes': row['sixes'], 'out': not row['notout'], 'dismissal': row['dismissal']})
                    else:
                        ops.append({'op': 'add_bowling', 'match': mid, 'team': team, 'inn': target, 'id': eid, 'balls': balls_of(row['overs']), 'maidens': row['maidens'], 'runs': row['runs'], 'wickets': row['wickets']})
            for idx, _, b in have[len(rows):]:   # more rows held than the official list has
                ops.append({'op': 'drop_' + kind, 'match': mid, 'team': team, 'inn': idx, 'id': eid})
    return ops, notes, aliases


def alias_evidence(pid, fmt, kind, row, people, cards):
    """The scorecard row that is this official innings under another id (Cricsheet 'R Limbu' for Statsguru 'Rohit Limbu'):
    same date, the player's side against the named opposition, and the same runs and balls (or wickets and runs)."""
    teams = set(people[pid].get('teams') or [])
    found = set()
    for card in cards.values():
        m = card['match']
        if m['date'] not in near(row['date']) or m['format'] != fmt or not (teams & set(m['teams'])):
            continue
        mine = next(iter(teams & set(m['teams'])))
        other = next((t for t in m['teams'] if t != mine), '')
        if not same_team(row['opp'], other):
            continue
        for inn in card['innings']:
            if inn.get('super_over') or (inn['team'] == mine) != (kind == 'batting'):
                continue
            for b in (inn['batting'] if kind == 'batting' else inn.get('bowling', [])):
                if b['id'] == pid or (people.get(b['id']) or {}).get('career'):
                    continue
                if kind == 'batting' and b.get('runs') == row['runs'] and b.get('balls') == row['balls'] and bool(b.get('out')) == (not row['notout']):
                    found.add((b['id'], b['name']))
                elif kind == 'bowling' and b.get('wickets') == row['wickets'] and b.get('runs') == row['runs'] and b.get('balls') == balls_of(row['overs']):
                    found.add((b['id'], b['name']))
    return next(iter(found)) if len(found) == 1 else None


def compatible(a, b):
    """Two names that could be one person: the same surname and the same first initial."""
    x, y = re.sub(r'[^a-z ]', '', a.lower()).split(), re.sub(r'[^a-z ]', '', b.lower()).split()
    return bool(x and y and x[-1] == y[-1] and x[0][0] == y[0][0])


def apply_overlay(root, cards, people):
    """Lay the official innings differences over the scorecards (idempotent)."""
    path = root / 'data/official_innings_overlay.json'
    if not path.exists():
        return {}
    import json as _json
    data = _json.loads(path.read_text(encoding='utf-8'))
    ops = data['ops']
    identities = {p['espn_id']: pid for pid, p in people.items() if p.get('espn_id')}
    applied = defaultdict(int)
    merge = {a['from']: identities[a['espn']] for a in data.get('aliases', []) if a['espn'] in identities and a['from'] != identities[a['espn']]}
    if merge:
        for card in cards.values():
            for squad in (card.get('players') or {}).values():
                for p in squad:
                    p['id'] = merge.get(p.get('id'), p.get('id'))
            for inn in card['innings']:
                for b in inn['batting'] + inn.get('bowling', []):
                    b['id'] = merge.get(b.get('id'), b.get('id'))
                    if b.get('dismissal_bowler'):
                        b['dismissal_bowler'] = merge.get(b['dismissal_bowler'], b['dismissal_bowler'])
                    if b.get('fielders'):
                        b['fielders'] = [merge.get(f, f) for f in b['fielders']]
            m = card['match']
            if m.get('player_ids'):
                m['player_ids'] = sorted({merge.get(i, i) for i in m['player_ids']})
        for src, dst in merge.items():
            if src in people and not people[src].get('career'):
                people.pop(src)
        applied['alias'] = len(merge)
    order = {'drop_batting': 0, 'drop_bowling': 0, 'fix_batting': 1, 'fix_bowling': 1, 'add_batting': 2, 'add_bowling': 2}
    for op in sorted(ops, key=lambda o: order[o['op']]):
        card = cards.get(op['match'])
        pid = identities.get(op['id'])
        if not card or not pid or op['inn'] >= len(card['innings']):
            continue
        inn = card['innings'][op['inn']]
        kind = 'bowling' if op['op'].endswith('bowling') else 'batting'
        rows = inn.setdefault(kind, [])
        ids = {pid, *[r.get('id') for r in rows if (r.get('id') or '').split('~')[0] == pid]}
        row = next((r for r in rows if r.get('id') in ids), None)
        if op['op'].startswith('drop'):
            if row is not None:
                rows.remove(row)
                applied[op['op']] += 1
        elif op['op'] == 'fix_batting' and row is not None:
            before = (row.get('runs'), row.get('balls'), row.get('out'))
            row['runs'], row['out'] = op['runs'], op['out']
            if op['balls'] is not None:
                row['balls'] = op['balls']
            if not op['out']:
                row['dismissal'] = 'not out'
            applied['fix_batting'] += before != (row.get('runs'), row.get('balls'), row.get('out'))
        elif op['op'] == 'fix_bowling' and row is not None:
            before = (row.get('wickets'), row.get('runs'))
            row['wickets'], row['runs'] = op['wickets'], op['runs']
            applied['fix_bowling'] += before != (row['wickets'], row['runs'])
        elif op['op'] == 'add_batting' and row is None:
            new = {'name': people[pid].get('name', ''), 'id': pid, 'runs': op['runs'], 'balls': op['balls'], 'fours': op['fours'], 'sixes': op['sixes'], 'out': op['out'],
                   'dismissal': op['dismissal'] if op['out'] else 'not out'}
            rows.insert(min(max((op['pos'] or len(rows) + 1) - 1, 0), len(rows)), new)
            applied['add_batting'] += 1
        elif op['op'] == 'add_bowling' and row is None:
            rows.append({'name': people[pid].get('name', ''), 'id': pid, 'balls': op['balls'], 'maidens': op['maidens'], 'runs': op['runs'], 'wickets': op['wickets'], 'wides': None, 'noballs': None})
            applied['add_bowling'] += 1
    return dict(applied)


def main(argv):
    sys.path.insert(0, str(ROOT / 'tools'))
    from cricket_scope import publication_data, load_cards
    from build_site import assemble_people
    archive, careers, history = publication_data(ROOT)
    people = assemble_people(archive, careers)
    check = '--check' in argv
    cards = load_cards(ROOT, archive['matches'] + history['matches'], people, overlay=check)
    bat, bowl, where = survey(cards, people)
    todo = gaps(cards, people, bat, bowl)
    if check:
        formats = sum(len(p.get('career') or {}) for p in people.values())
        print(f'{len(todo)} of {formats} player formats still do not reconcile')
        for pid, fmt in todo[:80]:
            print(' ', people[pid]['name'], fmt, people[pid].get('teams'))
        return
    only = [a for a in argv if not a.startswith('-')]
    if only:
        todo = [t for t in todo if people[t[0]]['name'] in only or t[0] in only]
    print(f'{len(todo)} player formats do not reconcile', flush=True)
    ops, notes, evidence = [], [], defaultdict(list)

    def work(item):
        pid, fmt = item
        return (item, *reconcile(pid, fmt, people, cards, bat, bowl, where))
    with ThreadPoolExecutor(4) as pool:
        for (pid, fmt), got, note, alias in pool.map(work, todo):
            ops += got
            for (src, name), eid in alias:
                evidence[src, eid, name].append((pid, fmt))
            notes += [f'{people[pid]["name"]} {fmt}: {n}' for n in note]
    if any('unavailable' in n for n in notes):
        # A page that would not load means a partial overlay: keep the last complete one.
        print(f'{sum("unavailable" in n for n in notes)} official pages unavailable: overlay kept as it was')
        return
    unique = {json.dumps(o, sort_keys=True): o for o in ops}
    by_espn = {p['espn_id']: pid for pid, p in people.items() if p.get('espn_id')}
    aliases, rejected = [], []
    for (src, eid, name), where_found in evidence.items():
        dst = people[by_espn[eid]]
        if (compatible(name, dst['name']) or len(where_found) >= 2) and not (people.get(src) or {}).get('career'):
            aliases.append({'from': src, 'espn': eid, 'name': f"{name} = {dst['name']}"})
        else:
            rejected.append(f"{name} / {dst['name']}")
    OVERLAY.write_text(json.dumps({'checked_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'source': 'ESPNcricinfo Statsguru innings lists',
                                   'aliases': aliases, 'ops': list(unique.values())}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(len(aliases), 'identity links;', len(rejected), 'rejected', rejected[:12])
    kinds = defaultdict(int)
    for o in unique.values():
        kinds[o['op']] += 1
    print(dict(kinds), flush=True)
    for n in notes[:40]:
        print('note:', n)
    print(len(notes), 'notes')


if __name__ == '__main__':
    main(sys.argv[1:])
