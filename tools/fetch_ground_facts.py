"""Pull ground facts for every published ground: city, country, capacity, opening year, bowling ends and coordinates.

Sources, in order of trust: the Cricinfo-derived data/ground_metadata.json for city and country, Wikidata claims
(capacity P1083, inception P571, coordinates P625, country P17, place P131) and the Wikipedia infobox for ends and
fallbacks. Every ground is cached under .data-cache so a rerun only fetches what is missing.

Usage: python tools/fetch_ground_facts.py [--only "Eden Gardens" ...] [--refresh]
"""
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from cricket_scope import publication_data  # noqa: E402
from venues import canonicalise_matches  # noqa: E402

CACHE = ROOT / '.data-cache/free-backfill/ground-facts'
OUT = ROOT / 'data/ground_facts.json'
HEADERS = {'User-Agent': 'CricketWicket/1.0 (https://cricket.rkjat.in; rkdevanda65@gmail.com)', 'Accept': 'application/json'}
WIKI = 'https://en.wikipedia.org/w/api.php'
DATA = 'https://www.wikidata.org/w/api.php'
STOP = {'the', 'cricket', 'stadium', 'ground', 'oval', 'international', 'sports', 'club', 'park', 'field', 'complex', 'national', 'association', 'of', 'and', 'at'}
NOT_A_CITY = re.compile(r'\d|ward|district|municipal|county|division|province|state|region|borough|parish|territory|island|metropolitan'
                        r'|australia|zealand|africa|england|scotland|wales|ireland|indies|india|pakistan|lanka|bangladesh|zimbabwe|emirates'
                        r'|pradesh|nadu|bengal|maharashtra|karnataka|gujarat|punjab|sindh|kerala|odisha|queensland|tasmania|gauteng|cape$', re.I)


def get(url, params, attempts=4):
    query = url + '?' + urllib.parse.urlencode({**params, 'format': 'json'})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(query, headers=HEADERS), timeout=40) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise
            time.sleep(2 * (attempt + 1))
        except (TimeoutError, urllib.error.URLError, ConnectionError):
            if attempt == attempts - 1:
                raise
            time.sleep(2 * (attempt + 1))


def tokens(text):
    return {t for t in re.sub(r'[^a-z0-9 ]', ' ', (text or '').lower()).split() if t not in STOP}


def search(query):
    try:
        rows = get(WIKI, {'action': 'query', 'list': 'search', 'srsearch': query, 'srlimit': 5})['query']['search']
    except Exception:
        return []
    return [r['title'] for r in rows if not r['title'].startswith('List of')]


def page(title):
    result = get(WIKI, {'action': 'query', 'prop': 'pageprops|coordinates|extracts|revisions', 'exintro': 1, 'explaintext': 1,
                        'ppprop': 'wikibase_item', 'rvprop': 'content', 'rvslots': 'main', 'titles': title, 'redirects': 1, 'formatversion': 2})
    p = result['query']['pages'][0]
    if p.get('missing'):
        return None
    text = ''
    if p.get('revisions'):
        text = p['revisions'][0].get('slots', {}).get('main', {}).get('content', '')
    coords = (p.get('coordinates') or [{}])[0]
    return {'title': p.get('title'), 'qid': p.get('pageprops', {}).get('wikibase_item'), 'lat': coords.get('lat'), 'lon': coords.get('lon'),
            'extract': (p.get('extract') or '')[:1200], 'text': text}


def clean_wiki(value):
    value = re.sub(r'<!--.*?-->', '', value, flags=re.S)
    value = re.sub(r'<ref[^>]*/>|<ref[^>]*>.*?</ref>', '', value, flags=re.S)
    value = re.sub(r'\{\{[^{}]*\}\}', '', value)
    value = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', value)
    value = re.sub(r'<[^>]+>', ' ', value)
    return re.sub(r'\s+', ' ', value).strip(' ;,')


VENUE_BOX = re.compile(r'\{\{Infobox\s*(venue|stadium|cricket ground|sports venue|sports complex|arena)', re.I)


def is_venue(text):
    return bool(VENUE_BOX.search(text or ''))


def infobox(text):
    start = text.find('{{Infobox')
    if start < 0:
        return {}
    box = text[start:start + 8000]
    fields = {}
    for m in re.finditer(r'^\s*\|\s*([a-z_0-9]+)\s*=\s*(.*)$', box, flags=re.M):
        fields[m.group(1).lower()] = m.group(2)
    return fields


def first_int(value, low=500, high=200000):
    for m in re.finditer(r'\d[\d,]{2,}', re.sub(r'<!--.*?-->', '', value or '', flags=re.S)):
        n = int(m.group(0).replace(',', ''))
        if low <= n <= high:
            return n
    return None


def first_year(value):
    m = re.search(r'\b(1[6-9]\d\d|20\d\d)\b', re.sub(r'<!--.*?-->', '', value or '', flags=re.S))
    return int(m.group(1)) if m else None


def ends(fields):
    names = []
    for key in ('end1', 'end2'):
        value = clean_wiki(fields.get(key, ''))
        value = re.split(r'\s*(?:<br|\n|;|\(|/)', value)[0].strip()
        value = re.sub(r'^[A-Za-z ]{2,14}:\s*', '', value)
        if 3 <= len(value) <= 40 and not re.search(r'\d', value):
            names.append(value)
    return names if len(names) == 2 else []


def claims(qid):
    entity = get(DATA, {'action': 'wbgetentities', 'ids': qid, 'props': 'claims'})['entities'][qid].get('claims', {})

    def values(prop):
        rows = []
        for c in entity.get(prop, []):
            value = c.get('mainsnak', {}).get('datavalue', {}).get('value')
            if value is None:
                continue
            when = c.get('qualifiers', {}).get('P585', [{}])[0].get('datavalue', {}).get('value', {}).get('time', '')
            rows.append((c.get('rank'), when, value))
        return rows

    capacity = None
    caps = values('P1083')
    if caps:
        preferred = [r for r in caps if r[0] == 'preferred'] or caps
        preferred.sort(key=lambda r: r[1], reverse=True)
        try:
            capacity = int(float(preferred[0][2]['amount']))
        except (KeyError, TypeError, ValueError):
            capacity = None
    inception = None
    for _, _, value in values('P571'):
        year = first_year(value.get('time', ''))
        if year:
            inception = year
            break
    lat = lon = None
    for _, _, value in values('P625'):
        lat, lon = value.get('latitude'), value.get('longitude')
        break
    places = [v['id'] for _, _, v in values('P131') if isinstance(v, dict) and 'id' in v]
    countries = [v['id'] for _, _, v in values('P17') if isinstance(v, dict) and 'id' in v]
    labels = {}
    ids = list(dict.fromkeys(places + countries))[:6]
    if ids:
        entities = get(DATA, {'action': 'wbgetentities', 'ids': '|'.join(ids), 'props': 'labels', 'languages': 'en'})['entities']
        labels = {k: v.get('labels', {}).get('en', {}).get('value') for k, v in entities.items()}
    return {'capacity': capacity, 'opened': inception, 'lat': lat, 'lon': lon,
            'place': next((labels.get(i) for i in places if labels.get(i)), None),
            'country': next((labels.get(i) for i in countries if labels.get(i)), None)}


CRICKET_SPORT = 'Q5375'
OTHER_SPORT = re.compile(r'\b(football|soccer|rugby|athletics|baseball|hockey|racecourse|horse racing|golf)\b', re.I)


def plain(text):
    return re.sub(r'[^a-z0-9]+', ' ', (text or '').lower()).strip()


def plays_cricket(qid):
    """False only when Wikidata lists sports for the venue and cricket is not one of them."""
    try:
        entity = get(DATA, {'action': 'wbgetentities', 'ids': qid, 'props': 'claims'})['entities'][qid].get('claims', {})
    except Exception:
        return True
    sports = [c.get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id') for c in entity.get('P641', [])]
    return not sports or CRICKET_SPORT in sports


SAME_COUNTRY = [
    {'united kingdom', 'england', 'scotland', 'wales', 'northern ireland', 'ireland'},
    {'west indies', 'barbados', 'jamaica', 'trinidad and tobago', 'guyana', 'antigua and barbuda', 'saint lucia', 'st lucia', 'grenada',
     'saint kitts and nevis', 'st kitts and nevis', 'saint vincent and the grenadines', 'st vincent', 'dominica', 'united states virgin islands'},
    {'united arab emirates', 'uae'},
]


def same_country(a, b):
    """True unless both countries are known and clearly different (UK nations and Caribbean islands count as one)."""
    if not a or not b:
        return True
    a, b = a.lower(), b.lower()
    if a == b:
        return True
    return any(a in group and b in group for group in SAME_COUNTRY)


def score(p, name, spellings, city, country, direct=False):
    """Rank a Wikipedia page as this ground. -99 rejects it outright."""
    if not p or not p.get('text') or not is_venue(p['text']):
        return -99
    title, extract = p['title'], p['extract'].lower()
    first = extract.split('. ')[0]
    want, have = tokens(name), tokens(title)
    exact = plain(title) in {plain(name), *map(plain, spellings)}
    contains = bool(want) and (want <= have or (len(want) >= 2 and len(want & have) >= len(want) - 1))
    if not (exact or contains or direct):
        return -99
    points = 0
    if exact or direct:
        points += 4
    elif contains:
        points += 2
    if re.search(r'\{\{Infobox\s*cricket ground', p['text'], re.I):
        points += 2
    if 'cricket' in title.lower():
        points += 1
    if 'cricket' in first:
        points += 1
    elif OTHER_SPORT.search(first):
        points -= 3
    if (city and city.lower() in extract) or (country and country.lower() in extract):
        points += 1
    if 'cricket' not in extract:
        points -= 2
    return points


def choose(name, spellings, city, country):
    ranked, tried = [], set()
    # A page titled exactly as the ground (or one of its recorded spellings), following redirects, is the strongest signal.
    for title in [name] + [s for s in spellings if s != name][:3]:
        try:
            p = page(title)
        except Exception:
            continue
        if not p:
            continue
        tried.add(p['title'])
        points = score(p, name, spellings, city, country, direct=True)
        if points >= 3:
            ranked.append((points, p))
    queries = [f'{name} {city or country or ""} cricket'.strip(), name] + [s for s in spellings if s != name][:2]
    seen = []
    for q in queries:
        for title in search(q):
            if title not in seen and title not in tried:
                seen.append(title)
    for title in seen[:12]:
        try:
            p = page(title)
        except Exception:
            continue
        points = score(p, name, spellings, city, country)
        if points >= 3:
            ranked.append((points, p))
    ranked.sort(key=lambda r: -r[0])
    for _, p in ranked[:3]:
        # Wikidata's sport list is often incomplete (rugby only for shared grounds), so only trust it when the page itself is not clearly a cricket ground.
        clearly_cricket = bool(re.search(r'\{\{Infobox\s*cricket ground', p['text'], re.I)) or 'cricket' in p['extract'].lower().split('. ')[0]
        if clearly_cricket or not p.get('qid') or plays_cricket(p['qid']):
            return p
    return None


def city_from_place(label):
    if not label or NOT_A_CITY.search(label) or len(label) > 30:
        return None
    return label


def facts_for(name, hint, refresh=False):
    file = CACHE / (re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') + '.json')
    if file.exists() and refresh != 'all':
        cached = json.loads(file.read_text(encoding='utf-8'))
        if cached.get('status') == 'matched' or (cached.get('status') == 'unmatched' and refresh != 'unmatched'):
            return cached
    forced = HINT_OVERRIDES.get(name, {})
    out = {'name': name, 'city': hint.get('city'), 'country': hint.get('country'), 'capacity': None, 'opened': None, 'ends': [],
           'lat': None, 'lon': None, 'wikipedia': None, 'wikidata': None, 'status': 'unmatched', 'checked_at': datetime.now(timezone.utc).isoformat()}
    try:
        p = choose(name, hint.get('spellings') or [], hint.get('city'), hint.get('country'))
        if p:
            out['wikipedia'] = 'https://en.wikipedia.org/wiki/' + urllib.parse.quote(p['title'].replace(' ', '_'))
            out['status'] = 'matched'
            fields = infobox(p['text'])
            out['ends'] = ends(fields)
            out['capacity'] = first_int(fields.get('capacity') or fields.get('seating_capacity') or '')
            out['opened'] = first_year(fields.get('opened') or fields.get('established') or fields.get('built') or fields.get('opened_date') or '')
            out['lat'], out['lon'] = p.get('lat'), p.get('lon')
            if p.get('qid'):
                out['wikidata'] = p['qid']
                wd = claims(p['qid'])
                if not same_country(hint.get('country'), wd.get('country')):
                    # The page is a ground in another country: keep the known place, drop everything else.
                    return finish({**out, 'capacity': None, 'opened': None, 'ends': [], 'lat': None, 'lon': None,
                                   'wikipedia': None, 'wikidata': None, 'status': 'unmatched', 'rejected': p['title']}, file)
                out['capacity'] = wd['capacity'] or out['capacity']
                out['opened'] = out['opened'] or wd['opened']
                if out['lat'] is None and wd['lat'] is not None:
                    out['lat'], out['lon'] = wd['lat'], wd['lon']
                out['city'] = out['city'] or city_from_place(wd['place'])
                out['country'] = out['country'] or wd['country']
        out.update(forced)
        time.sleep(0.2)
    except Exception as error:  # keep going; the ground simply has no facts this run
        out['status'] = 'error'
        out['error'] = str(error)[:200]
    return finish(out, file)


def finish(out, file):
    if out['lat'] is not None:
        out['lat'], out['lon'] = round(float(out['lat']), 5), round(float(out['lon']), 5)
    for key in ('city', 'country'):
        if out.get(key):
            out[key] = out[key].replace('—', '-').replace('–', '-').strip()
    out['ends'] = [e.replace('—', '-').replace('–', '-').strip() for e in out.get('ends') or []]
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    return out


# Places the source data gets wrong or leaves vague; checked by hand.
HINT_OVERRIDES = {
    'International Sports Stadium': {'city': 'Coffs Harbour', 'country': 'Australia'},
    'Simonds Stadium': {'city': 'Geelong', 'country': 'Australia'},
    "Sir Paul Getty's Ground": {'city': 'Wormsley', 'country': 'England'},
}


def published_grounds():
    arc, careers, hist = publication_data(ROOT)
    matches = arc['matches'] + hist['matches']
    canonicalise_matches(matches)
    metadata = json.loads((ROOT / 'data/ground_metadata.json').read_text(encoding='utf-8'))['venues'] if (ROOT / 'data/ground_metadata.json').exists() else {}
    known_cities = {v['city'] for v in metadata.values() if v.get('city')}
    grounds = defaultdict(lambda: {'matches': 0, 'spellings': Counter(), 'cities': Counter(), 'countries': Counter()})
    for m in matches:
        if not m.get('venue'):
            continue
        g = grounds[m['venue']]
        g['matches'] += 1
        raw = m.get('venue_recorded') or m['venue']
        g['spellings'][raw] += 1
        meta = metadata.get(raw) or metadata.get(m['venue'])
        if meta:
            if meta.get('city'):
                g['cities'][meta['city']] += 1
            if meta.get('country'):
                g['countries'][meta['country']] += 1
        elif raw in known_cities:
            g['cities'][raw] += 1
        if m.get('city'):
            g['cities'][m['city']] += 1
        if m.get('host_country'):
            g['countries'][m['host_country']] += 1
    hints = {}
    for name, g in grounds.items():
        hints[name] = {'matches': g['matches'], 'spellings': [s for s, _ in g['spellings'].most_common(4)],
                       'city': g['cities'].most_common(1)[0][0] if g['cities'] else None,
                       'country': g['countries'].most_common(1)[0][0] if g['countries'] else None}
        hints[name].update(HINT_OVERRIDES.get(name, {}))
    return hints


def main(argv):
    only = [argv[i + 1] for i, a in enumerate(argv) if a == '--only' and i + 1 < len(argv)]
    refresh = 'all' if '--refresh' in argv else ('unmatched' if '--retry-unmatched' in argv else '')
    hints = published_grounds()
    names = [n for n in hints if not only or n in only]
    print(f'Grounds: {len(names)} (of {len(hints)} published)', flush=True)
    results = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(facts_for, n, hints[n], refresh): n for n in names}
        for i, f in enumerate(as_completed(futures), 1):
            r = f.result()
            results[r['name']] = {**r, 'matches': hints[r['name']]['matches'], 'spellings': hints[r['name']]['spellings']}
            if i % 25 == 0 or i == len(names):
                print(f'  {i}/{len(names)}', flush=True)
    if only:
        for r in results.values():
            print(json.dumps(r, ensure_ascii=False))
        return
    counts = Counter(r['status'] for r in results.values())
    facts = {'meta': {'checked_at': datetime.now(timezone.utc).isoformat(), 'grounds': len(results), 'matched': counts.get('matched', 0),
                      'unmatched': counts.get('unmatched', 0), 'errors': counts.get('error', 0),
                      'with_capacity': sum(1 for r in results.values() if r['capacity']), 'with_city': sum(1 for r in results.values() if r['city']),
                      'with_country': sum(1 for r in results.values() if r['country']), 'with_coordinates': sum(1 for r in results.values() if r['lat'] is not None)},
             'grounds': {n: results[n] for n in sorted(results)}}
    OUT.write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(facts['meta'], indent=1), flush=True)


if __name__ == '__main__':
    main(sys.argv[1:])
