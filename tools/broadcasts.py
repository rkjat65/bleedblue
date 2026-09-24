"""Render current India television and streaming listings from dated source data."""
from __future__ import annotations
import html
import json
from datetime import datetime
from pathlib import Path


def load_broadcasts(root: Path, today: str):
    data=json.loads((root/'data/broadcasts.json').read_text(encoding='utf-8'))
    fixtures=[]
    for series in data.get('series',[]):
        for item in series.get('fixtures',[]):
            if item.get('date','') < today:
                continue
            fixtures.append({**item,'series':series['name'],'format':series['format'],'gender':series['gender'],'tv':series['tv'],'ott':series['ott'],'watch_url':series['watch_url'],'source_url':series['source_url']})
    def start_key(item):
        raw=item.get('time_ist','11:59 PM')
        try: clock=datetime.strptime(raw,'%I:%M %p').strftime('%H:%M')
        except ValueError: clock='23:59'
        return item['date'],clock,item['match']
    fixtures.sort(key=start_key)
    return data,fixtures


def _e(value):
    return html.escape(str(value),quote=True)


def _flags(item):
    def slug(value):
        import re,unicodedata
        return re.sub(r'[^a-z0-9]+','-',unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode().lower()).strip('-')
    teams=item.get('teams',[])
    if len(teams)!=2:
        return f'<strong>{_e(item["match"])}</strong>'
    badges=[]
    for team in teams:
        badges.append(f'<span class="watch-team"><img src="/assets/flags/{slug(team)}.svg" width="28" height="20" alt="" loading="lazy"><span>{_e(team)}</span></span>')
    return badges[0]+'<span class="watch-v">v</span>'+badges[1]


def fixture_card(item,today):
    state='TODAY' if item['date']==today else 'UPCOMING'
    return f'''<article class="watch-card">
      <div class="watch-date"><span>{state}</span><time datetime="{_e(item['date'])}">{_e(item['date'])}</time><strong>{_e(item.get('time_ist','Time TBC'))} IST</strong></div>
      <div class="watch-match"><div class="watch-matchup">{_flags(item)}</div><p>{_e(item['detail'])} · {_e(item['series'])}</p></div>
      <dl class="watch-platforms"><div><dt>TV</dt><dd>{_e(item['tv'])}</dd></div><div><dt>Stream</dt><dd>{_e(item['ott'])}</dd></div></dl>
      <a class="watch-button" href="{_e(item['watch_url'])}" rel="noopener noreferrer">Open provider ↗</a>
    </article>'''


def homepage_watch(fixtures,today):
    cards=''.join(fixture_card(item,today) for item in fixtures[:4])
    if not cards:
        cards='<p class="panel">No verified India broadcast listing is currently published.</p>'
    return f'''<section class="home-watch" aria-labelledby="home-watch-title"><div class="section-heading"><div><p class="eyebrow">WATCH IN INDIA</p><h2 id="home-watch-title">Today and next on cricket.</h2><p class="muted">Television channels and official streaming platforms, checked before publication.</p></div><a href="/where-to-watch/">All broadcast listings →</a></div><div class="watch-grid">{cards}</div></section>'''


def watch_page(data,fixtures,today):
    cards=''.join(fixture_card(item,today) for item in fixtures)
    sources=[]
    seen=set()
    for item in fixtures:
        key=(item['series'],item['source_url'])
        if key in seen: continue
        seen.add(key)
        sources.append(f'<li><a href="{_e(item["source_url"])}" rel="noopener noreferrer">{_e(item["series"])} listing</a></li>')
    return f'''<section class="page-head"><div class="eyebrow">WATCH IN INDIA</div><h1>Live cricket telecast and streaming</h1><p>Verified television channels, OTT services and start times for ongoing and upcoming international cricket.</p></section>
      <div class="watch-summary"><strong>{len(fixtures)}</strong><span>upcoming match listings</span><strong>{_e(data.get('territory','India'))}</strong><span>broadcast territory</span><strong>{_e(data.get('checked_at','')[:10])}</strong><span>last checked</span></div>
      <div class="watch-grid watch-directory">{cards or '<p class="panel">No verified upcoming listing is currently published.</p>'}</div>
      <section class="panel watch-notes"><h2>How to use these listings</h2><p>Times are in Indian Standard Time. A provider may move a match between its channels or feeds close to the start, so use the provider button for the final listing. “No Indian TV listing” means a verified television channel was not found; the named official stream remains available.</p><p>{_e(data.get('note',''))}</p><details><summary>Listing sources</summary><ul>{''.join(sources)}</ul></details></section>'''
