"""Render India television and streaming listings, grouped by series."""
from __future__ import annotations
import html
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path


def _start_key(item):
    raw=item.get('time_ist','11:59 PM')
    try: clock=datetime.strptime(raw,'%I:%M %p').strftime('%H:%M')
    except ValueError: clock='23:59'
    return item['date'],clock,item['match']


def load_broadcasts(root: Path, today: str):
    data=json.loads((root/'data/broadcasts.json').read_text(encoding='utf-8'))
    active=[]
    fixtures=[]
    for source in data.get('series',[]):
        upcoming=[item for item in source.get('fixtures',[]) if item.get('date','') >= today]
        upcoming.sort(key=_start_key)
        if not upcoming: continue
        series={**source,'fixtures':upcoming}
        active.append(series)
        fixtures.extend({**item,'series':source['name']} for item in upcoming)
    active.sort(key=lambda series:(0 if series.get('india_team') else 1,_start_key(series['fixtures'][0]),series['name']))
    fixtures.sort(key=_start_key)
    data['active_series']=active
    return data,fixtures


def _e(value):
    return html.escape(str(value),quote=True)


def _slug(value):
    return re.sub(r'[^a-z0-9]+','-',unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode().lower()).strip('-')


def _flags(item):
    teams=item.get('teams',[])
    if len(teams)!=2:
        return f'<strong>{_e(item["match"])}</strong>'
    badges=[]
    for team in teams:
        badges.append(f'<span class="watch-team"><img src="/assets/flags/{_slug(team)}.svg" width="28" height="20" alt="" loading="lazy"><span>{_e(team)}</span></span>')
    return badges[0]+'<span class="watch-v">v</span>'+badges[1]


def series_card(series,today,compact=False):
    fixtures=series['fixtures'][:3] if compact else series['fixtures']
    rows=''
    for item in fixtures:
        state='<span class="watch-live">TODAY</span>' if item['date']==today else ''
        rows+=f'''<li><div class="watch-fixture-date">{state}<time datetime="{_e(item['date'])}">{_e(item['date'])}</time><strong>{_e(item.get('time_ist','TBC'))} IST</strong></div><div><div class="watch-matchup">{_flags(item)}</div><p>{_e(item['detail'])}</p></div></li>'''
    remaining=len(series['fixtures'])-len(fixtures)
    more=f'<p class="watch-more">+ {remaining} more match{"es" if remaining!=1 else ""} in this series</p>' if remaining else ''
    official='<span class="watch-official">BCCI schedule</span>' if series.get('india_team') else ''
    return f'''<article class="watch-series{' watch-series-compact' if compact else ''}">
      <div class="watch-series-head"><div><p class="eyebrow">{_e(series['gender'])} · {_e(series['format'])}</p><h3>{_e(series['name'])}</h3>{official}</div><a class="watch-button" href="{_e(series['watch_url'])}" rel="noopener noreferrer">Open provider ↗</a></div>
      <dl class="watch-platforms"><div><dt>TV</dt><dd>{_e(series['tv'])}</dd></div><div><dt>Stream</dt><dd>{_e(series['ott'])}</dd></div></dl>
      <ol class="watch-fixtures">{rows}</ol>{more}
    </article>'''


def homepage_watch(data,today):
    cards=''.join(series_card(series,today,True) for series in data.get('active_series',[])[:4])
    if not cards:
        cards='<p class="panel">No verified India broadcast listing is currently published.</p>'
    return f'''<section class="home-watch" aria-labelledby="home-watch-title"><div class="section-heading"><div><p class="eyebrow">WATCH IN INDIA</p><h2 id="home-watch-title">Today and next on cricket.</h2><p class="muted">Series-wise television and official streaming details, with India Men and India Women first.</p></div><a href="/where-to-watch/">All broadcast listings →</a></div><div class="watch-grid">{cards}</div></section>'''


def _section(title,lede,series,today,section_class=''):
    cards=''.join(series_card(item,today) for item in series)
    return f'''<section class="watch-section {section_class}"><div class="section-heading"><div><p class="eyebrow">INDIA CRICKET</p><h2>{_e(title)}</h2><p class="muted">{_e(lede)}</p></div></div><div class="watch-grid watch-directory">{cards or '<p class="panel">No upcoming series is currently confirmed.</p>'}</div></section>'''


def watch_page(data,fixtures,today):
    active=data.get('active_series',[])
    men=[series for series in active if series.get('india_team')=='Men']
    women=[series for series in active if series.get('india_team')=='Women']
    others=[series for series in active if not series.get('india_team')]
    other_cards=''.join(series_card(item,today) for item in others)
    return f'''<section class="page-head"><div class="eyebrow">WATCH IN INDIA</div><h1>Live cricket telecast and streaming</h1><p>Series-wise television channels, OTT services and IST start times for ongoing and upcoming international cricket.</p></section>
      <div class="watch-summary"><strong>{len(active)}</strong><span>active and upcoming series</span><strong>{len(fixtures)}</strong><span>match listings</span><strong>{_e(data.get('checked_at','')[:10])}</strong><span>last checked</span></div>
      {_section('India Men: upcoming matches','Official BCCI fixtures, with the confirmed Indian television and streaming home.',men,today,'watch-india')}
      {_section('India Women: upcoming matches','Official BCCI fixtures for the senior women’s team. Unannounced broadcast details remain clearly marked.',women,today,'watch-india')}
      <section class="watch-section"><div class="section-heading"><div><p class="eyebrow">OTHER INTERNATIONAL SERIES</p><h2>More cricket available in India</h2><p class="muted">Each broadcaster is shown once for the full series.</p></div></div><div class="watch-grid watch-directory">{other_cards or '<p class="panel">No other verified upcoming series is currently published.</p>'}</div></section>
      <section class="panel watch-notes"><h2>About these listings</h2><p>Times are in Indian Standard Time. Broadcasters may move a match between channels or feeds close to the start, so use the provider button for the final listing. “To be announced” means no official India broadcast announcement has been published yet.</p><p>{_e(data.get('note',''))}</p></section>'''
