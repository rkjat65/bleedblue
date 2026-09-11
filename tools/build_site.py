"""Build Cricket Wicket's searchable, pre-rendered static publication."""
from __future__ import annotations
import argparse, hashlib, html, json, math, re, shutil, unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from cricket_scope import publication_data, FULL_MEMBERS, load_cards, complete_career_counts,career_scorecards
from home_visuals import homepage_hero, homepage_insights, archive_visuals
import cricket_charts as cw
from publication_assets import prepare_assets, social_image
from publication_pages import trust_pages
from portraits import load_portraits, portrait_figure
from profile_research import select_research_players, profile_research_section, opponent_pages, research_index
from editorial_research import build_editorial, entity_context
from studio_page import studio_markup
from data_health import profile_coverage, coverage_page
from player_profile import player_seo, player_intro, profile_nav, career_glance, career_tables, player_faq, player_person, primary_role
from player_questions import prepare_player_questions, question_page, featured_question_cards, player_question_directory, assert_clean_bundle
from entity_pages import (
    team_totals, ground_totals, team_seo, ground_seo, team_intro, ground_intro,
    team_glance, ground_glance, results_table_rows, team_faq, ground_faq,
    team_schema, ground_schema, h2h_path,
)
from world_cup import FAMILIES, classify, player_leaders, title_table, titles_leaderboard

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / '_site'
BASE = 'https://cricket.rkjat.in'
TODAY = date.today().isoformat()
PAGES = {}
PREVIOUS = {}
SETTINGS=json.loads((ROOT/'data/site-settings.json').read_text(encoding='utf-8')) if (ROOT/'data/site-settings.json').exists() else {}
ASSET_VERSION = hashlib.sha256(b''.join(p.read_bytes() for p in sorted((ROOT/'web').glob('*')) if p.is_file())).hexdigest()[:10]
ALIASES = {'SR Tendulkar':'Sachin Tendulkar','V Kohli':'Virat Kohli','RG Sharma':'Rohit Sharma','JJ Bumrah':'Jasprit Bumrah','DG Bradman':'Don Bradman','M Muralitharan':'Muttiah Muralitharan','M Muralidaran':'Muttiah Muralitharan','SK Warne':'Shane Warne','RT Ponting':'Ricky Ponting','KC Sangakkara':'Kumar Sangakkara','DPMD Jayawardene':'Mahela Jayawardene','JH Kallis':'Jacques Kallis','BC Lara':'Brian Lara','SM Gavaskar':'Sunil Gavaskar','R Dravid':'Rahul Dravid','A Kumble':'Anil Kumble','R Ashwin':'Ravichandran Ashwin','RA Jadeja':'Ravindra Jadeja','SC Ganguly':'Sourav Ganguly','V Sehwag':'Virender Sehwag','SS Mandhana':'Smriti Mandhana','H Kaur':'Harmanpreet Kaur','M Raj':'Mithali Raj','J Goswami':'Jhulan Goswami','EA Perry':'Ellyse Perry','MM Lanning':'Meg Lanning','JE Root':'Joe Root','SPD Smith':'Steve Smith','KS Williamson':'Kane Williamson','JM Anderson':'James Anderson','DA Warner':'David Warner','AC Gilchrist':'Adam Gilchrist','ST Jayasuriya':'Sanath Jayasuriya','KL Rahul':'KL Rahul','RR Pant':'Rishabh Pant','HH Pandya':'Hardik Pandya','AC Kerr':'Amelia Kerr','SCJ Broad':'Stuart Broad'}
def load_illustrations(people=None):
    """Map player names to cutouts in web/art/players/{slug}-illustration.webp|.png|.jpg.

    Drop a transparent portrait named after the player slug (virat-kohli-illustration.webp)
    and the next build attaches it. PNG and JPEG are converted to WebP at publish time.
    """
    art=ROOT/'web/art/players'
    found={}
    files={}
    if art.is_dir():
        for path in art.iterdir():
            if path.suffix.lower() not in {'.webp','.png','.jpg','.jpeg'}: continue
            stem=path.stem.lower()
            if not stem.endswith('-illustration'): continue
            key=stem[:-len('-illustration')]
            files.setdefault(key, path)
            if path.suffix.lower()=='.webp': files[key]=path
    names=list((people or {}).values()) if isinstance(people, dict) else list(people or [])
    if not names:
        for key,path in files.items():
            found[key]='/assets/art/players/'+path.stem+'.webp'
        return found
    aliases={'steve-smith':'steven-smith','steven-smith':'steve-smith'}
    for player in names:
        key=slug(player.get('name',''))
        path=files.get(key) or files.get(aliases.get(key,''))
        if path: found[player['name']]='/assets/art/players/'+path.stem+'.webp'
    return found
ILLUSTRATIONS = {}
HERO_CAST = ('Virat Kohli','Rohit Sharma','Smriti Mandhana','Harmanpreet Kaur','MS Dhoni','Ellyse Perry','Sachin Tendulkar','Pat Cummins')
# Cricket host territories, used only for these unambiguous city labels.
HOST_CITIES = {}
for country, cities in {'India':'Mumbai|Chennai|Delhi|New Delhi|Kolkata|Bengaluru|Bangalore|Hyderabad|Ahmedabad|Pune|Nagpur|Mohali|Dharamsala|Ranchi|Rajkot|Indore|Lucknow|Kanpur|Visakhapatnam|Cuttack|Guwahati|Thiruvananthapuram|Raipur', 'Australia':'Sydney|Melbourne|Adelaide|Perth|Brisbane|Hobart|Canberra|Cairns|Darwin', 'England':'London|Manchester|Birmingham|Nottingham|Leeds|Southampton|Chester-le-Street|Cardiff|Bristol|Taunton|Worcester|Leicester|Derby|Hove|Chelmsford', 'New Zealand':'Auckland|Wellington|Christchurch|Hamilton|Dunedin|Napier|Mount Maunganui|Nelson|Queenstown', 'South Africa':'Cape Town|Johannesburg|Durban|Centurion|Pretoria|Gqeberha|Port Elizabeth|Paarl|Bloemfontein|Potchefstroom|East London|Kimberley', 'Pakistan':'Lahore|Karachi|Rawalpindi|Multan|Faisalabad', 'Sri Lanka':'Colombo|Galle|Kandy|Dambulla|Pallekele|Hambantota', 'Bangladesh':'Dhaka|Mirpur|Chattogram|Chittagong|Sylhet', 'Zimbabwe':'Harare|Bulawayo', 'United Arab Emirates':'Dubai|Sharjah|Abu Dhabi', 'Ireland':'Dublin|Belfast|Bready|Malahide', 'West Indies':'Bridgetown|Kingston|Gros Islet|Port of Spain|Providence|Basseterre|St George\'s|North Sound|Roseau', 'Namibia':'Windhoek', 'Netherlands':'Amstelveen|Rotterdam|The Hague', 'Scotland':'Edinburgh|Aberdeen|Glasgow', 'Nepal':'Kirtipur|Kathmandu', 'Oman':'Al Amerat|Muscat'}.items():
    HOST_CITIES.update({city:country for city in cities.split('|')})

def read(path): return json.loads((ROOT / path).read_text(encoding='utf-8'))
def esc(v): return html.escape(str(v if v is not None else ''), quote=True)
def num(v): return '—' if v is None else f'{v:,}' if isinstance(v, int) else f'{v:.2f}' if isinstance(v,float) else str(v)
def slug(v): return re.sub(r'[^a-z0-9]+','-',unicodedata.normalize('NFKD', str(v)).encode('ascii','ignore').decode().lower()).strip('-') or 'unknown'
def fullname(p): return ALIASES.get(p['name'],p['name'])

def stable_routes(proposed, previous, kind):
    """Keep published identity URLs when names or scorecard coverage change."""
    counts=Counter(previous.values())
    result={key:previous[key] for key in proposed if key in previous and counts[previous[key]]==1 and re.fullmatch('/'+kind+r'/[a-z0-9-]+/',previous[key])}
    used=set(result.values())
    for key,path in proposed.items():
        if key in result:continue
        if path in used:path=path.rstrip('/')+'-'+key+'/'
        if path in used:raise ValueError('Conflicting identity URL: '+path)
        result[key]=path;used.add(path)
    return result
def dump(path, value):
    target=OUT/path.lstrip('/');target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(value,separators=(',',':'),ensure_ascii=False),encoding='utf-8')
TEXT_COLUMNS={'Player','Batter','Bowler','Team','Teams','Country','Gender','Format','Match','Result','Coverage','Dismissal','Opponent','Ground','Venue','Metric','Date','Year','First player','Second player'}
HEADER_NAMES={'Mat':'Matches','Inns':'Innings','NO':'Not outs','BF':'Balls faced','Avg':'Batting average','SR':'Strike rate','HS':'Highest score','Ct':'Catches','St':'Stumpings','Dis':'Dismissals','BBI':'Best bowling in an innings','BBM':'Best bowling in a match','Econ':'Runs conceded per over','M':'Maidens','R':'Runs','B':'Balls faced','O':'Overs','W':'Wickets','Min':'Minutes at the crease'}

def table(headings, rows, ident='', caption=''):
    kinds=['text' if h in TEXT_COLUMNS or (i==0 and h!='Rank') else 'number' for i,h in enumerate(headings)]
    css='score-table'+(' scorecard-table '+('batting-table' if headings[0]=='Batter' else 'bowling-table') if headings[0] in ('Batter','Bowler') else '')+(' has-rank' if headings[0]=='Rank' else '')
    labels={**HEADER_NAMES,**({'Avg':'Bowling average','SR':'Balls per wicket'} if caption.startswith('Bowling career') else {})}
    head=''.join('<th scope="col" class="cell-'+k+'" title="'+esc(labels.get(h,h))+'">'+esc(h)+'</th>' for h,k in zip(headings,kinds))
    body=''.join('<tr>'+''.join('<'+('th scope="row"' if i==0 else 'td')+' class="cell-'+kinds[i]+'">'+str(v)+'</'+('th' if i==0 else 'td')+'>' for i,v in enumerate(row))+'</tr>' for row in rows)
    return '<div class="table-wrap" tabindex="0" role="region" aria-label="'+esc(caption or 'Cricket statistics')+'"><table class="'+css+'"'+(' id="'+esc(ident)+'"' if ident else '')+'><caption>'+esc(caption)+'</caption><thead><tr>'+head+'</tr></thead><tbody>'+body+'</tbody></table></div>'

def rate(top,bottom,factor=1):
    if top is None or bottom is None or bottom<=0:return None
    from decimal import Decimal,ROUND_DOWN
    return float((Decimal(top)*factor/Decimal(bottom)).quantize(Decimal('.01'),rounding=ROUND_DOWN))

def decimal_stat(value):return '—' if value is None else f'{value:.2f}'

def stat_value(s,key):
    v=s.get(key)
    if v is None:
        denominator={'avg':'outs','sr':'balls','bowlAvg':'wickets','bowlSr':'wickets','econ':'legal'}.get(key)
        if denominator and (s.get(denominator)==0 or (key in ('avg','sr') and 'innings' in s and not s['innings'] and s.get('runs') is None) or (key in ('bowlAvg','bowlSr','econ') and 'bowling_innings' in s and not s['bowling_innings'] and s.get('wickets') is None)):return '<span class="not-applicable" title="No applicable denominator">N/A</span>'
        return '<span class="missing" title="Not recorded in the verified source">—</span>'
    if key=='dismissals_per_innings':return f'{v:.3f}'
    return esc(decimal_stat(v) if key in ('avg','sr','bowlAvg','bowlSr','econ','dismissals_per_innings') else num(v))

def dismissal_text(b,people):
    kind=b.get('dismissal_kind')
    if not kind:return b['dismissal']
    bowler=people.get(b.get('dismissal_bowler'),{}).get('name','')
    fielders=', '.join(people.get(pid,{}).get('name','substitute') for pid in b.get('fielders',[]))
    if kind=='caught and bowled':return 'c & b '+bowler
    if kind=='caught':return 'c '+(fielders or 'fielder not recorded')+' b '+bowler
    if kind=='stumped':return 'st '+(fielders or 'keeper')+' b '+bowler
    if kind=='bowled':return 'b '+bowler
    if kind in ('lbw','hit wicket'):return kind+' b '+bowler
    if kind=='run out':return 'run out'+(' ('+fielders+')' if fielders else '')
    return kind

def render_innings(inn,index,people,pp):
    bpo=inn.get('balls_per_over',6)
    def overs(b):return esc(str(b['overs_display'])) if b.get('overs_display') not in (None,'None') else esc(str(b['overs'])) if isinstance(b.get('overs'),(int,float,str)) else ('—' if b.get('balls') is None else str(b['balls']//bpo)+'.'+str(b['balls']%bpo))
    total=str(inn['runs'])+('/'+str(inn['wickets']) if inn['wickets'] is not None and inn['wickets']<10 else '')+('d' if inn.get('declared') else '')
    body='<section id="innings-'+str(index)+'" class="panel innings-panel"><div class="innings-heading"><div><span class="eyebrow">INNINGS '+str(index)+(' · SUPER OVER' if inn.get('super_over') else '')+'</span><h2>'+esc(inn['team'])+'</h2></div><strong class="innings-total">'+esc(total)+'</strong></div>'
    body+=table(['Batter','Dismissal','R','B','4s','6s','SR'],[[a(pp[b['id']],people[b['id']]['name']),esc(dismissal_text(b,people)),esc(num(b['runs']))+('' if b['out'] else '<span class="notout">*</span>'),num(b['balls']),num(b['fours']),num(b['sixes']),decimal_stat(b.get('sr') if b.get('sr') is not None else rate(b['runs'],b['balls'],100))] for b in inn['batting']],caption='Batting scorecard')
    body+='<div class="innings-summary"><span>Extras <strong>'+num(inn['extras'])+'</strong></span><span>Overs <strong>'+overs(inn)+'</strong></span></div>'
    body+=table(['Bowler','O','M','R','W','Econ','WD','NB'],[[a(pp[b['id']],people[b['id']]['name']),overs(b),num(b.get('maidens')),num(b['runs']),num(b['wickets']),decimal_stat(b.get('econ') if b.get('econ') is not None else rate(b['runs'],b['balls'],bpo)),num(b.get('wides')),num(b.get('noballs'))] for b in inn['bowling']],caption='Bowling scorecard')
    if inn['fall']:
        body+=cw.partnerships(inn)
        body+='<details class="innings-details"><summary>Fall of wickets</summary><p>'+esc(' · '.join(f'{w["runs"]}/{w["wicket"]} ({w["player"]})' for w in inn['fall']))+'</p></details>'
    if inn['overs']:
        body+='<details class="innings-details"><summary>Over-by-over totals</summary>'+table(['Over','Runs','Wickets','Total'],[[str(o[k]) for k in ['over','runs','wickets','total']] for o in inn['overs']],caption='Runs and wickets in each over')+'</details>'
    return body+'</section>'

def a(path,label): return f'<a href="{esc(path)}">{esc(label)}</a>'
def pill(s): return f'<span class="pill">{esc(s)}</span>'
def ratios(s):
    s=dict(s)
    for key,top,bottom,factor in [('avg','runs','outs',1),('sr','runs','balls',100),('bowlAvg','conceded','wickets',1),('econ','conceded','legal',6)]:
        s[key]=rate(s.get(top),s.get(bottom),factor)
    return s
def aggregate(formats):
    values=list(formats.values())
    if not values:return {}
    if len(values)==1:return values[0]
    sums={k:sum(v[k] for v in values) if all(v.get(k) is not None for v in values) else None for k in ['matches','innings','runs','outs','balls','wickets','conceded','legal','hundreds','fifties','catches','stumpings']}
    sums['highest']=max((v.get('highest') or 0 for v in values))
    return ratios(sums)
def result(m):
    o=m['outcome']
    if o.get('winner'):
        margin=m.get('margin_text') or ' and '.join('an innings' if k=='innings' and v==1 else f'{v} {k}' for k,v in o.get('by',{}).items())
        return o['winner']+' won'+(' by '+margin if margin else '')
    return {'draw':'Match drawn','tie':'Match tied','no result':'No result'}.get(o.get('result'),'Result not recorded')
def page(path,title,description,body,kind='WebPage',extra=None,noindex=False):
    extra=dict(extra or {})
    faq=extra.pop('faq',None)
    crumb_name=extra.pop('breadcrumb_name',title)
    canonical=BASE+path; section=path.strip('/').split('/')[0]
    crumbs=[{'@type':'ListItem','position':1,'name':'Home','item':BASE+'/'}]
    if len(path.strip('/').split('/'))>1:
        body='<nav class="breadcrumbs" aria-label="Breadcrumb">'+a('/','Home')+' / '+a('/'+section+'/',section.title())+' / <span>'+esc(crumb_name)+'</span></nav>'+body
        crumbs.append({'@type':'ListItem','position':2,'name':section.replace('-',' ').title(),'item':BASE+'/'+section+'/'})
        crumbs.append({'@type':'ListItem','position':3,'name':crumb_name,'item':canonical})
    elif path!='/':
        crumbs.append({'@type':'ListItem','position':2,'name':title,'item':canonical})
    schema={'@context':'https://schema.org','@type':kind,'name':title,'description':description,'url':canonical,'isPartOf':{'@type':'WebSite','name':'Cricket Wicket','url':BASE+'/'}}
    social=extra.get('image') or f'{BASE}/assets/social/site-default.png'
    if not isinstance(social,str):
        extra.pop('image',None)
        social=f'{BASE}/assets/social/site-default.png'
    if extra:schema.update(extra)
    if path!='/':schema['breadcrumb']={'@type':'BreadcrumbList','itemListElement':crumbs}
    ld=json.dumps(schema,ensure_ascii=False).replace('<','\\u003c')
    ld_scripts=f'<script type="application/ld+json">{ld}</script>'
    if faq:
        ld_scripts+=f'<script type="application/ld+json">{json.dumps(faq,ensure_ascii=False).replace("<","\\u003c")}</script>'
    nav=[('/matches/','Matches'),('/players/','Players'),('/teams/','Teams'),('/records/','Records'),('/compare/','Compare'),('/studio/','Studio'),('/series/','Series')]
    home_assets=(f'<link rel="stylesheet" href="/assets/home.css?v={ASSET_VERSION}"><script src="/assets/home.js?v={ASSET_VERSION}" defer></script>' if path=='/' else '')
    studio_assets=(f'<link rel="stylesheet" href="/assets/studio.css?v={ASSET_VERSION}"><script src="/assets/studio-core.js?v={ASSET_VERSION}" defer></script><script src="/assets/studio-images.js?v={ASSET_VERSION}" defer></script><script src="/assets/studio.js?v={ASSET_VERSION}" defer></script>' if path=='/studio/' else '')
    og_type='profile' if kind=='ProfilePage' else 'website'
    verification=('<meta name="google-site-verification" content="'+esc(SETTINGS['google_site_verification'])+'">') if SETTINGS.get('google_site_verification') else ''
    document=f'''<!doctype html><html lang="en"><head><meta charset="utf-8">{verification}<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} | Cricket Wicket</title><meta name="description" content="{esc(description)}"><link rel="sitemap" type="application/xml" href="{BASE}/sitemap.xml"><link rel="canonical" href="{canonical}"><meta name="robots" content="{'noindex,follow' if noindex else 'index,follow,max-image-preview:large'}"><meta name="theme-color" content="#10233f"><meta property="og:type" content="{og_type}"><meta property="og:title" content="{esc(title)} | Cricket Wicket"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{canonical}"><meta property="og:site_name" content="Cricket Wicket"><meta property="og:image" content="{social}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{social}"><link rel="icon" href="/favicon.svg"><link rel="apple-touch-icon" href="/apple-touch-icon.png"><link rel="manifest" href="/site.webmanifest"><link rel="stylesheet" href="/assets/wicket.css?v={ASSET_VERSION}"><link rel="stylesheet" href="/assets/publication.css?v={ASSET_VERSION}"><link rel="stylesheet" href="/assets/portraits.css?v={ASSET_VERSION}"><link rel="stylesheet" href="/assets/profile-research.css?v={ASSET_VERSION}"><link rel="stylesheet" href="/assets/editorial-research.css?v={ASSET_VERSION}"><script src="/assets/analysis-core.js?v={ASSET_VERSION}" defer></script><script src="/assets/wicket.js?v={ASSET_VERSION}" defer></script>{home_assets}{studio_assets}{ld_scripts}</head><body><a class="skip" href="#main">Skip to statistics</a><div class="topline"><div class="wrap">THE GAME IN NUMBERS <span>Tests · ODIs · T20Is · Men & women</span></div></div><header><div class="wrap header"><a class="brand" href="/"><img src="/logo.svg" width="36" height="36" alt="">CRICKET WICKET<span>.</span></a><button id="menu" aria-label="Open navigation" aria-expanded="false" aria-controls="nav">☰</button><nav id="nav">{''.join(f'<a href="{url}" '+('aria-current="page"' if path.startswith(url) else '')+f'>{name}</a>' for url,name in nav)}<a class="search-link" href="/search/">Search</a><a class="ipl-link" href="https://crickrida.rkjat.in/">IPL Analytics</a></nav><button id="theme" aria-label="Toggle dark theme" aria-pressed="false">◐</button></div></header><main id="main" class="wrap">{body}</main><footer><div class="wrap"><strong>CRICKET WICKET</strong><p>Official international careers. Twelve national teams. Every format.</p><div class="footer-links">{a('/about/','About')}{a('/contact/','Contact')}{a('/data-coverage/','Data coverage')}{a('/datasets/','Datasets')}{a('/methodology/','Methodology')}{a('/insights/','Statistical insights')}{a('/questions/','Cricket questions')}{a('/blog/','Daily notes')}{a('/world-cup/','World Cup archive')}{a('/head-to-head/','Head-to-head records')}{a('/records/best-innings/','Best performances')}{a('/milestones/','Player milestones')}{a('/venue-records/','Venue records')}{a('/corrections/','Report a correction')}{a('https://crickrida.rkjat.in/','IPL on Crickrida')}</div><p class="muted">Ball-by-ball data: <a href="https://cricsheet.org/">Cricsheet</a>. Corrections: <a href="mailto:rkideas65@gmail.com">rkideas65@gmail.com</a>.</p></div></footer><div id="toast" role="status" aria-live="polite"></div></body></html>'''
    target=OUT/path.lstrip('/')/'index.html';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(document,encoding='utf-8')
    if not noindex:PAGES[path]={'title':title,'bytes':len(document.encode()),'sha256':hashlib.sha256(document.encode()).hexdigest(),'lastmod':TODAY}
    if path in PAGES and PREVIOUS.get(path,{}).get('sha256')==PAGES[path]['sha256']:PAGES[path]['lastmod']=PREVIOUS[path].get('lastmod',TODAY)
def heading(title,subtitle='',eyebrow='INTERNATIONAL CRICKET'):
    return f'<section class="page-head"><div class="eyebrow">{esc(eyebrow)}</div><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></section>'
def actions():return '<div class="actions"><button data-save>Save page</button><button data-share>Share link</button><button data-csv>Download table CSV</button></div>'
def match_table(matches,paths,limit=40):
    return table(['Date','Match','Format','Result','Coverage'],[[esc(m['date']),a(paths[m['id']],' v '.join(m['teams'])),esc(m['format']+' · '+m['gender']),esc(result(m)),pill('Result only' if m.get('coverage')=='result-only' else 'No play' if m.get('coverage')=='no-play' else 'Scorecard')] for m in matches[:limit]],caption='International match results')
def entity_filter_form(kind,name,matches):
    years=sorted({m['date'][:4] for m in matches},reverse=True)
    controls=options('gender',['Men','Women'])+options('format',['Test','ODI','T20I'])+options('year',years,'Year')
    if years:
        controls+=f'<label>From year<input name="from" type="number" min="{years[-1]}" max="{years[0]}" inputmode="numeric"></label><label>To year<input name="to" type="number" min="{years[-1]}" max="{years[0]}" inputmode="numeric"></label>'
    if kind=='teams':
        opponents=sorted({t for m in matches for t in m['teams'] if t!=name})
        controls+=options('opponent',opponents,'Opponent')
    return f'<form class="filters entity-filter" data-entity-filter="{kind}" data-entity-value="{esc(name)}"><div class="filter-intro"><strong>Filter this archive</strong><span id="entity-count">{len(matches):,} matches</span></div>{controls}<button class="primary">Apply filters</button><button type="reset">Reset</button></form>'
def entity_visuals(kind,name,matches):
    formats=Counter(m['format'] for m in matches)
    maximum=max(formats.values(),default=1)
    format_bars=''.join(f'<div class="entity-format-row"><span>{fmt}</span><div class="entity-track"><i style="width:{formats.get(fmt,0)/maximum*100:.1f}%"></i></div><strong>{formats.get(fmt,0):,}</strong></div>' for fmt in ('Test','ODI','T20I'))
    years=Counter(m['date'][:4] for m in matches); ordered=sorted(years.items())
    year_max=max(years.values(),default=1)
    year_step=max(1,len(ordered)//12)
    year_bars=''.join(f'<div class="entity-year-bar"><i style="height:{count/year_max*100:.1f}%" title="{year}: {count:,} matches"></i>{f"<span>{year}</span>" if i % year_step == 0 or i == len(ordered)-1 else ""}</div>' for i,(year,count) in enumerate(ordered))
    outcome=''
    if kind=='teams':
        won=sum(m.get('outcome',{}).get('winner')==name for m in matches);lost=sum(name in m.get('teams',[]) and m.get('outcome',{}).get('winner') not in (None,name) for m in matches);other=len(matches)-won-lost;om=max(won,lost,other,1)
        outcome=f'<figure class="entity-chart"><figcaption>Team results · wins, losses and other outcomes</figcaption><div class="entity-outcome-bars"><div><i class="win" style="height:{won/om*100:.1f}%"></i><span>Wins</span><strong>{won:,}</strong></div><div><i class="loss" style="height:{lost/om*100:.1f}%"></i><span>Losses</span><strong>{lost:,}</strong></div><div><i class="other" style="height:{other/om*100:.1f}%"></i><span>Other</span><strong>{other:,}</strong></div></div></figure>'
    conditions=''
    if kind=='grounds':
        tests=[m for m in matches if m.get('format')=='Test']
        odis=[m for m in matches if m.get('format')=='ODI']
        t20s=[m for m in matches if m.get('format')=='T20I']
        def innings_runs(sample):
            values=[t.get('runs') for m in sample for t in (m.get('totals') or []) if t.get('runs') is not None]
            return (sum(values)/len(values)) if values else None
        test_draws=sum(1 for m in tests if not m.get('outcome',{}).get('winner'))
        odi_avg=innings_runs(odis); t20_avg=innings_runs(t20s)
        firsts=[(m.get('totals') or [{}])[0].get('runs') for m in matches if m.get('totals')]
        firsts=[n for n in firsts if n is not None]
        first_avg=(sum(firsts)/len(firsts)) if firsts else None
        def fig(label,value,note):
            if value is None: shown='not recorded'
            elif isinstance(value,str): shown=value
            elif isinstance(value,float): shown=f'{value:.1f}'
            else: shown=f'{value:,}'
            return f'<div><span>{esc(label)}</span><strong>{shown}</strong><small>{esc(note)}</small></div>'
        conditions='<section class="venue-conditions"><p class="eyebrow">HOW THIS GROUND PLAYS</p><h2>Recorded innings, not a pitch rating</h2><div class="venue-condition-grid">'
        conditions+=fig('First-innings average', first_avg, f'{len(firsts)} recorded first innings')
        conditions+=fig('Test draws', (f'{100*test_draws/len(tests):.1f}%' if tests else None), f'{len(tests)} Tests · {test_draws} without a winner')
        conditions+=fig('ODI innings average', odi_avg, f'{len(odis)} ODIs')
        conditions+=fig('T20I innings average', t20_avg, f'{len(t20s)} T20Is')
        conditions+='</div><p class="note">Averages use recorded team innings totals at this venue. Missing historical innings are omitted. This is not a pitch report.</p></section>'
    return f'<section class="entity-visuals" aria-label="{esc(name)} archive visuals"><div class="entity-chart"><div class="entity-chart-heading"><div><p class="eyebrow">ARCHIVE AT A GLANCE</p><h2>How this archive is shaped</h2></div><span>{len(matches):,} total matches</span></div><figure><figcaption>Matches by international format</figcaption>{format_bars}</figure></div><figure class="entity-chart entity-year-chart"><figcaption>Matches by year · each bar is an exact annual count</figcaption><div class="entity-year-scroll" tabindex="0" role="img" aria-label="{esc(name)} matches by year">{year_bars}</div></figure>{outcome}</section>'+conditions
def team_badge(team, path=None):
    mark=f'<span class="team-badge"><img src="/assets/flags/{slug(team)}.svg" width="28" height="20" alt="" loading="lazy"><span>{esc(team)}</span></span>'
    return f'<a class="team-badge-link" href="{esc(path)}">{mark}</a>' if path else mark
def stats_table(p):
    return career_tables(p, table, stat_value)

def options(name,values,label=None):return f'<label>{esc(label or name.title())}<select name="{name}"><option value="">All</option>'+''.join(f'<option value="{esc(v)}">{esc(v)}</option>' for v in values)+'</select></label>'

def main():
    global PREVIOUS, ILLUSTRATIONS
    OUT.mkdir(exist_ok=True)
    if (OUT/'build-manifest.json').exists():
        PREVIOUS=json.loads((OUT/'build-manifest.json').read_text(encoding='utf-8')).get('indexable',{})
    arc,careers,hist=publication_data(ROOT)
    people={p['id']:{**p,'career':{}} for p in arc['players']}
    for p in careers['players']:
        prior=people.setdefault(p['id'],{**p,'formats':{}});prior['espn_id']=p['espn_id'];prior['gender']=p['gender'];prior['teams']=p['teams'];prior['career']=p['formats'];prior['name']=fullname(prior);prior['first']=p['first'];prior['last']=p['last']
    for p in people.values():p['name']=fullname(p)
    matches=sorted(arc['matches']+hist['matches'],key=lambda m:(m['date'],m['id']),reverse=True)
    all_cards=load_cards(ROOT,matches,people)
    portraits=load_portraits(ROOT/'data/portraits.json')
    studio_portraits={pid:{k:p[k] for k in ('path','author','license','license_url','source_url')} for pid,p in portraits.items()}
    for pid,p in people.items():
        if p.get('name') in ILLUSTRATIONS: studio_portraits[pid]={'path':ILLUSTRATIONS[p['name']]}
    dump('/data/studio-portraits.json',studio_portraits)
    research_ids=select_research_players(people)
    for key,n in complete_career_counts(career_scorecards(ROOT,all_cards,people),people).items():careers['meta']['enriched_fields'][key]=careers['meta']['enriched_fields'].get(key,0)+n
    for p in people.values():p['name']=p.get('full_name',p['name'])
    ILLUSTRATIONS=load_illustrations(people)
    names=Counter(slug(p['name']) for p in people.values())
    match_labels={m['id']:' v '.join(m['teams'])+' '+m['date']+' '+m['gender']+' '+m['format'] for m in matches}
    duplicate_labels=Counter(match_labels.values())
    match_labels={mid:title+(' · '+mid if duplicate_labels[title]>1 else '') for mid,title in match_labels.items()}
    pp={pid:'/players/'+slug(p['name'])+('-'+pid if names[slug(p['name'])]>1 else '')+'/' for pid,p in people.items()}
    mp={m['id']:'/matches/'+slug('-'.join(m['teams']))+'-'+m['date']+'-'+m['id']+'/' for m in matches}
    previous_routes=json.loads((OUT/'data/routes.json').read_text(encoding='utf-8')) if (OUT/'data/routes.json').exists() else {}
    pp=stable_routes(pp,previous_routes.get('players',{}),'players')
    mp=stable_routes(mp,previous_routes.get('matches',{}),'matches')
    groups={kind:defaultdict(list) for kind in ['teams','grounds','series']}
    appearances=defaultdict(list);innings=defaultdict(list)
    for m in matches:
        for team in m['teams']:groups['teams'][team].append(m)
        if m['venue']:groups['grounds'][m['venue']].append(m)
        if m['event']:groups['series'][m['event']].append(m)
        for pid in m.get('player_ids',[]):appearances[pid].append({'match':m['id'],'date':m['date'],'format':m['format'],'teams':m['teams'],'venue':m['venue'],'result':result(m),'url':mp[m['id']]})
    gp={kind:{name:f'/{kind}/{slug(name)}-{hashlib.sha1(name.encode()).hexdigest()[:6]}/' for name in g} for kind,g in groups.items()}
    editorial=build_editorial(people,matches,pp,mp,gp,all_cards,careers['meta'].get('checked_at',''))
    # Retire the legacy publication and its unscoped global data payloads.
    for name in ['overview','official','about','coverage','batting','bowling','fielding','h2h','formats','tournaments','vendor','images','app.js','styles.css','professional.css','enhancements.js','stats.json','official_records.json','player_images.json']:
        target=(OUT/name).resolve()
        assert target.is_relative_to(OUT.resolve()) and target!=OUT.resolve()
        if target.is_dir():shutil.rmtree(target)
        elif target.exists():target.unlink()
    for file in ['logo.svg','favicon.svg','favicon-16.png','favicon-32.png','apple-touch-icon.png','site.webmanifest','404.html','CNAME']:
        shutil.copy2(ROOT/file,OUT/file)
    (OUT/'.nojekyll').touch()
    shutil.copytree(ROOT/'web',OUT/'assets',dirs_exist_ok=True)
    (OUT/'vendor').mkdir(exist_ok=True)
    shutil.copy2(ROOT/'vendor/chart.umd.min.js',OUT/'vendor/chart.umd.min.js')
    if (ROOT/'analytics_lake').exists():shutil.copytree(ROOT/'analytics_lake',OUT/'data/lake',dirs_exist_ok=True)
    prepare_assets(OUT)
    social_url=social_image(OUT, 'International cricket records, profiles & analysis')
    social_source=OUT/'assets'/social_url.split('/assets/',1)[-1]
    shutil.copy2(social_source, OUT/'assets/social/site-default.png')
    trust_pages(page, heading, a, careers['meta'].get('checked_at',''))
    print('Building scorecards and player analysis...',flush=True)
    for mid,card in all_cards.items():
        m=card['match'];body=heading(' v '.join(m['teams']),f'{m["date"]} · {m["format"]} · {m["gender"]} · {m["venue"]}','MATCH SCORECARD')+f'<div class="result-banner">{esc(result(m))}</div>'+actions()
        body+='<p>'+ ' · '.join(a(gp['teams'][t],t) for t in m['teams'])+' · '+a(gp['grounds'][m['venue']],m['venue'])+'</p>'
        if m['event']:body+='<p>'+a(gp['series'][m['event']],m['event'])+'</p>'
        if card['innings']:body+='<nav class="innings-nav" aria-label="Jump to innings">'+''.join(a('#innings-'+str(i),inn['team']+' · '+str(inn['runs'])+'/'+str(inn['wickets'])+' · Inn '+str(i)) for i,inn in enumerate(card['innings'],1))+'</nav>'
        body+=cw.match_lab(card)
        for index,inn in enumerate(card['innings'],1):
            body+=render_innings(inn,index,people,pp)
            if inn.get('super_over'):continue
            bowl={b['id']:b for b in inn['bowling']};bat={b['id']:(pos,b) for pos,b in enumerate(inn['batting'],1)}
            for pid in set(bowl)|set(bat):
                pos,b=bat.get(pid,(None,{}));w=bowl.get(pid,{});team=inn['team'] if b else next(t for t in m['teams'] if t!=inn['team']);opp=next(t for t in m['teams'] if t!=team);host=HOST_CITIES.get(m.get('city','')) or m.get('host_country');host={'United Kingdom':'England','Wales':'England','Barbados':'West Indies','Jamaica':'West Indies','Trinidad and Tobago':'West Indies','Guyana':'West Indies','Saint Lucia':'West Indies','Antigua and Barbuda':'West Indies','St Kitts and Nevis':'West Indies','Dominica':'West Indies','Grenada':'West Indies'}.get(host,host)
                setting='Unknown' if not host else 'Home' if team==host else 'Away' if opp==host else 'Neutral'
                outcome='Won' if m['outcome'].get('winner')==team else 'Lost' if m['outcome'].get('winner') else 'Draw / tie / no result'
                innings[pid].append({'date':m['date'],'match':mid,'url':mp[mid],'format':m['format'],'opponent':opp,'venue':m['venue'],'setting':setting,'result':outcome,'innings':index,'position':pos,'runs':b.get('runs'),'balls':b.get('balls'),'out':b.get('out'),'fours':b.get('fours'),'sixes':b.get('sixes'),'dismissal':b.get('dismissal'),'wickets':w.get('wickets'),'legal':w.get('balls'),'conceded':w.get('runs')})
        body+='<section class="panel"><h2>Playing XIs</h2><div class="grid two">'+''.join('<div><h3>'+esc(team)+'</h3>'+''.join('<p>'+(a(pp[p['id']],people[p['id']]['name']) if p['id'] in pp else esc(p['name']))+'</p>' for p in squad)+'</div>' for team,squad in card['players'].items())+'</div></section><p class="note">Verified match scorecard. Super overs are excluded from player analysis. A dash means the historical scorecard did not record that field.</p>'
        if not card['innings']:body+='<section class="panel"><h2>No play</h2><p>This match has no recorded innings. Batting and bowling figures do not apply.</p></section>'
        page(mp[mid],match_labels[mid]+' scorecard',f'{result(m)}. {m["format"]} scorecard at {m["venue"]}, including batting, bowling and over-by-over totals.',body,'SportsEvent',{'startDate':m['date'],'sport':'Cricket','location':{'@type':'Place','name':m['venue']}})
    for m in hist['matches']:
        if m['id'] in all_cards:continue
        body=heading(' v '.join(m['teams']),f'{m["date"]} · {m["format"]} · {m["gender"]}','HISTORICAL RESULT')+f'<div class="result-banner">{esc(result(m))}</div><p>{a(gp["grounds"][m["venue"]],m["venue"])}</p>'+actions()+'<section class="panel"><h2>Match coverage</h2><p>This record contains the result. Local innings, lineups and ball data are unavailable.</p>'+ ' · '.join(a(gp['teams'][t],t) for t in m['teams'])+'</section>'
        page(mp[m['id']],match_labels[m['id']]+' result',f'{result(m)}. Historical {m["format"]} result at {m["venue"]}.',body,'SportsEvent',{'startDate':m['date'],'sport':'Cricket'})
    player_q=prepare_player_questions(people,pp,featured_names=set(ILLUSTRATIONS)|set(HERO_CAST),extra_ids=research_ids)
    print('Building career profiles...',flush=True)
    for pid,p in people.items():
        career=p['career'];tot=aggregate(career);path=pp[pid]; rows=sorted(innings[pid],key=lambda r:r['date']);apps=appearances[pid]
        summary={'id':pid,'name':p['name'],'teams':p['teams'],'gender':p['gender'],'career':career,'url':path}
        summary['career']={fmt:{k:v for k,v in s.items() if k not in ('source','sources','enrichment_source')} for fmt,s in career.items()}
        dump(path+'summary.json',summary);dump(path+'analytics.json',{'innings':rows,'appearances':apps,'note':'Available official match scorecards within site coverage. Super overs excluded. Unknown venue setting is not inferred.'})
        suffix=' · '+pid if names[slug(p['name'])]>1 else ''
        title,description=player_seo(p,suffix)
        intro=player_intro(p)
        illustration=ILLUSTRATIONS.get(p['name'])
        person,og_image=player_person(p,pid,path,description,portraits,illustration=illustration,base=BASE)
        years=' to '.join(part for part in (p.get('first'),p.get('last')) if part)
        identity='<div class="player-identity"><span class="gender-mark">'+esc(p['gender'])+'</span>'+''.join(team_badge(t,gp['teams'].get(t)) for t in p['teams'] if t in gp['teams'])+(f'<span class="career-years">{esc(years)}</span>' if years else '')+'</div>'
        subtitle=' · '.join(part for part in [' / '.join(p.get('teams') or []), p.get('gender') or '', years] if part) or 'International career statistics, records and scorecard analysis'
        profile_title='<div class="player-profile-heading">'+heading(p['name'],subtitle,'PLAYER CAREER')+portrait_figure(pid,p['name'],portraits,illustration=illustration)+'</div>'+identity+f'<p class="player-intro">{esc(intro)}</p>'
        glance=career_glance(p,stat_value)
        official_charts=cw.career_lab(career,p['name'])
        archive_charts=cw.player_lab(rows,p['name'])
        tables=stats_table(p)
        pack=player_q.get(pid)
        faq_html,faq_schema=player_faq(p, urls=pack['urls'] if pack else None, name_slug=pack['name_slug'] if pack else slug(p['name']))
        picture_id='official-pictures' if official_charts else ('career-pictures' if archive_charts else '')
        nav_html=profile_nav(bool(glance),picture_id,True,bool(faq_html),bool(rows))
        body=profile_title+profile_coverage(p,rows)+nav_html+actions()
        if tot:
            role=primary_role(career) if career else 'batter'
            keys=[('matches','Internationals'),('wickets','Wickets'),('runs','Career runs')] if role=='bowler' else [('matches','Internationals'),('runs','Career runs'),('hundreds','Centuries'),('wickets','Wickets')]
            body+='<div class="stats">'+''.join(f'<div><strong>{num(tot.get(k))}</strong><span>{label}</span></div>' for k,label in keys)+'</div>'
        body+=glance+official_charts+archive_charts
        checked_dates=sorted({careers['meta']['checked_at'][:10]}|{s['checked_at'][:10] for s in career.values() if s.get('checked_at')})
        snapshot_label=' to '.join(dict.fromkeys([checked_dates[0],checked_dates[-1]])) if checked_dates else ''
        body+='<section class="panel career-tables" id="career-records"><h2>Career records by format</h2>'
        if tables:
            body+='<p class="muted">Official Test, ODI and T20I figures. Every cell is in the HTML so search engines and downloads see the same numbers as the page.</p>'+tables
            if snapshot_label:body+=f'<p class="note">Career records checked: {esc(snapshot_label)}. A dash means not recorded; N/A means the statistic does not apply. Career totals are independent of the scorecard archive.</p>'
        else:
            body+='<p class="note">This archive identity has no matched career record. Do not treat its archive totals as a complete career.</p>'
        body+='</section>'
        body+=faq_html
        body+='<section class="panel" id="analysis" data-analytics="'+path+'analytics.json"><h2>Explore this player’s available match data</h2><p>'+str(len(apps))+' match appearances in available scorecards. Filters below apply to this archive only.</p><button id="load-analysis" class="primary">Open statistical explorer</button><div id="analysis-controls" hidden></div><div id="analysis-results" aria-live="polite"></div></section>'
        body+='<section class="panel"><h2>Recent available appearances</h2>'+table(['Date','Match','Format','Result'],[[x['date'],a(x['url'],' v '.join(x['teams'])),x['format'],esc(x['result'])] for x in apps[:12]],caption='Recent available appearances')+'</section><p>'+ ' · '.join(a(gp['teams'][t],t) for t in p['teams'] if t in gp['teams'])+' · '+a('/compare/','Compare with another player')+'</p>'
        body += profile_research_section(p, rows, path, curated=pid in research_ids)
        extra={'mainEntity':person,'breadcrumb_name':p['name']}
        if og_image:extra['image']=og_image
        if faq_schema:extra['faq']=faq_schema
        page(path,title,description,body,'ProfilePage',extra)
    for spec in editorial['pages']:
        if isinstance(spec, tuple):
            spec=dict(zip(('path','title','description','body'),spec))
        page(spec['path'],spec['title'],spec['description'],spec['body'],spec.get('kind','Article'),spec.get('extra'))
    for pid in research_ids:
        p=people[pid]
        for spec in opponent_pages(p, innings[pid], pp[pid]):
            if isinstance(spec, tuple): spec=dict(zip(('path','title','description','body'),spec))
            page(spec['path'],spec['title'],spec['description'],spec['body'],'Article')
    research_spec=research_index(people,pp,research_ids)
    if isinstance(research_spec, tuple):
        page(research_spec[0],research_spec[1],research_spec[2],research_spec[3],research_spec[4])
    else:
        page('/research/','International player research','Format-specific player versus opposition records, trends, timelines and evidence from the international archive.',research_spec,'CollectionPage')
    print('Building directories, records and research pages...',flush=True)
    build_collections(people,matches,pp,mp,gp,groups,careers,arc,hist,editorial,all_cards)
    build_question_hubs(people,matches,pp,mp,gp,careers,all_cards,player_q,HERO_CAST)
    build_daily_blog(people,pp,careers,all_cards,mp)
    coverage_page(matches,all_cards,careers,page)
    dump('/data/routes.json',{'players':pp,'matches':mp})
    dump('/data/player-index.json',[{'id':pid,'name':p['name'],'url':pp[pid],'teams':p['teams'],'gender':p['gender'],'formats':list(p['career'] or p['formats']),'byFormat':{fmt:{'runs':stats.get('runs'),'wickets':stats.get('wickets')} for fmt,stats in p['career'].items()},'runs':aggregate(p['career']).get('runs'),'wickets':aggregate(p['career']).get('wickets'),'art':ILLUSTRATIONS.get(p['name'])} for pid,p in people.items()])
    dump('/data/match-index.json',[{'id':m['id'],'date':m['date'],'url':mp[m['id']],'teams':m['teams'],'format':m['format'],'gender':m['gender'],'venue':m['venue'],'event':m['event'],'result':result(m),'coverage':'Result only' if m.get('coverage')=='result-only' else 'No play' if m.get('coverage')=='no-play' else 'Scorecard'} for m in matches])
    sitemap_files=[]
    for xml in OUT.glob('sitemap-*.xml'):xml.unlink()
    for index,start in enumerate(range(0,len(PAGES),10000),1):
        paths=list(PAGES)[start:start+10000];name=f'sitemap-{index}.xml';sitemap_files.append(name)
        xml='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{BASE}{esc(path)}</loc><lastmod>{PAGES[path]["lastmod"]}</lastmod></url>' for path in paths)+'</urlset>'
        (OUT/name).write_text(xml,encoding='utf-8')
    (OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<sitemap><loc>{BASE}/{x}</loc></sitemap>' for x in sitemap_files)+'</sitemapindex>',encoding='utf-8')
    # Public JSON indexes power the crawlable search and explorer experience;
    # only the private notebook is excluded from search.
    (OUT/'robots.txt').write_text(f'User-agent: *\nAllow: /\nDisallow: /saved/\nSitemap: {BASE}/sitemap.xml\n',encoding='utf-8')
    try:
        import urllib.request
        urllib.request.urlopen('https://www.google.com/ping?sitemap='+BASE+'/sitemap.xml', timeout=8).read(64)
    except Exception:
        pass
    # Only prune destinations previously owned by the generator, inside this output.
    for path in set(PREVIOUS)-set(PAGES):
        target=(OUT/path.lstrip('/')).resolve()
        assert target.is_relative_to(OUT.resolve()) and target!=OUT.resolve()
        for name in ['index.html','summary.json','analytics.json','records.json']:
            (target/name).unlink(missing_ok=True)
    for index in OUT.rglob('index.html'):
        path='/'+index.parent.relative_to(OUT).as_posix().strip('./')+'/'
        if path=='//':path='/'
        if path in PAGES or path in ('/embed/','/search/','/saved/','/international/'):continue
        for name in ['index.html','summary.json','analytics.json','records.json']:(index.parent/name).unlink(missing_ok=True)
    missing=Counter();not_applicable=Counter()
    for p in people.values():
        for fmt,s in p['career'].items():
            for metric,denominator in [('avg','outs'),('sr','balls'),('bowlAvg','wickets'),('econ','legal'),('bowlSr','wickets')]:
                if s.get(metric) is None:
                    (not_applicable if 'N/A' in stat_value(s,metric) else missing)[fmt+' '+metric]+=1
    dump('/coverage-report.json',{'teams':sorted(FULL_MEMBERS),'matches':len(matches),'scorecards':sum(bool(c['innings']) for c in all_cards.values()),'no_play':sum(not c['innings'] for c in all_cards.values()),'result_only':len(matches)-len(all_cards),'players':len(people),'enriched_fields':careers['meta']['enriched_fields'],'unmatched_careers':sum(not p['career'] for p in people.values()),'unrecorded_rates':dict(missing),'not_applicable_rates':dict(not_applicable)})
    dump('/build-manifest.json',{'built_at':TODAY,'pages':len(PAGES),'players':len(people),'matches':len(matches),'largest_html_bytes':max(x['bytes'] for x in PAGES.values()),'indexable':PAGES})
    print(f'Built {len(PAGES)} indexable pages in {OUT}',flush=True)

def build_evergreen_hubs(people,matches,pp,mp,gp,all_cards):
    """Publish high-intent cricket hubs from the same validated records.

    These pages are deliberately compact landing pages with visible tables and
    links to the underlying scorecards. They make the archive useful to people
    and easy for crawlers to discover without manufacturing thin keyword pages.
    """
    cards=all_cards or {}

    families=classify(matches)
    glance=''
    for key,label,fmt,gender in FAMILIES:
        rec=families.get(key)
        if not rec: continue
        top=rec['titles'].most_common(1)
        champ,count=(top[0] if top else ('Not recorded',0))
        last=rec['editions'][-1]['winner'] if rec['editions'] else 'Not recorded'
        glance+=f'<a class="format-card" href="/world-cup/{key}/"><h3>{esc(label)}</h3><div class="format-card-hero"><strong>{esc(str(count))}</strong><span>titles · {esc(champ)}</span></div><p class="format-card-note">{len(rec["editions"])} recorded editions. Last champion: {esc(last or "not recorded")}.</p></a>'
    world_body=heading('World Cup cricket records','Winners, leading run scorers and wicket takers from recorded World Cup matches in this archive. Qualifiers are excluded.','WORLD CUP DATA')+actions()
    world_body+='<p class="player-intro">These tables use recorded World Cup matches between the twelve national teams. Men\'s ODI World Cups in this archive start in 2003. Earlier tournaments appear only when the source labelled them as a World Cup. The champion is the winner of the last recorded match in each edition.</p>'
    if glance: world_body+='<section class="career-glance-wrap" id="by-format"><p class="eyebrow">THE GLOBAL EVENTS</p><h2>Who has won, and who has scored</h2><div class="career-glance">'+glance+'</div></section>'
    all_wc=[m for rec in families.values() for m in rec['matches']]
    world_body+='<div class="stats">'+''.join(f'<div><strong>{num(value)}</strong><span>{label}</span></div>' for value,label in [(len(all_wc),'Recorded World Cup matches'),(sum(len(rec["editions"]) for rec in families.values()),'Recorded editions'),(sum(m.get("gender")=="Men" for m in all_wc),'Men'),(sum(m.get("gender")=="Women" for m in all_wc),'Women')])+'</div>'
    for key,label,fmt,gender in FAMILIES:
        rec=families.get(key)
        if not rec: continue
        path='/world-cup/'+key+'/'
        leaders=player_leaders([mid for cup in rec['editions'] for mid in cup['ids']],cards,people,25)
        titles=titles_leaderboard(rec,gp['teams'])
        body=heading(label,f'{len(rec["editions"])} recorded editions · {len(rec["matches"]):,} matches','WORLD CUP')+actions()
        body+=f'<p class="player-intro">{esc(label)} in this archive. Champion of an edition is the winner of its last recorded match. Player figures use available scorecards only; a missing innings does not become a zero.</p>'
        if titles:
            body+='<section class="panel" id="winners"><h2>Most titles</h2>'+table(['Team','Titles'],titles,caption=label+' titles in this archive')
            body+=cw.leader_bars([(team,count) for team,count in rec['titles'].most_common(8)],label+' titles',minimum=1)+'</section>'
        body+='<section class="panel"><h2>Edition winners</h2>'+table(['Year','Matches','Champion','Last recorded match','Date'],title_table(rec,gp['teams'],mp),caption=label+' edition winners')+'</section>'
        if leaders['runs']:
            body+='<section class="panel" id="runs"><h2>Leading run scorers</h2>'+table(['Player','Runs','Inns','HS','100s'],[[a(pp.get(r['id'],'/players/'),r['name']),num(r['runs']),num(r['innings']),num(r['highest']),num(r['hundreds'])] for r in leaders['runs']],caption=label+' run scorers from recorded innings')+'</section>'
        if leaders['wickets']:
            body+='<section class="panel" id="wickets"><h2>Leading wicket takers</h2>'+table(['Player','Wickets','Inns','Best'],[[a(pp.get(r['id'],'/players/'),r['name']),num(r['wickets']),num(r['innings']),esc(r['best'] or '')] for r in leaders['wickets']],caption=label+' wicket takers from recorded innings')+'</section>'
        if leaders['scores']:
            body+='<section class="panel"><h2>Highest recorded scores</h2>'+table(['Runs','Player','Balls','Date','Team'],[[num(runs),esc(name),num(balls),esc(day),esc(team or '')] for runs,balls,name,day,mid,team in leaders['scores']],caption=label+' highest individual scores')+'</section>'
        if leaders['spells']:
            body+='<section class="panel"><h2>Best recorded bowling</h2>'+table(['Figures','Player','Date'],[[f'{wkts}/{conceded}',esc(name),esc(day)] for wkts,conceded,name,day,mid in leaders['spells']],caption=label+' best bowling figures')+'</section>'
        body+='<p class="note">Scorecard coverage is incomplete for some editions. Career World Cup totals on other sites can differ when a match is missing here. '+a('/world-cup/','All World Cup records')+' · '+a('/records/','Career records')+'</p>'
        top_team,top_count=(rec['titles'].most_common(1)[0] if rec['titles'] else ('Not recorded',0))
        top_runs=leaders['runs'][0]['name']+' '+num(leaders['runs'][0]['runs']) if leaders['runs'] else 'not recorded'
        description=f'{label}: {top_team} has {top_count} recorded titles. Leading run scorer {top_runs}. Winners, runs and wickets from this archive.'
        page(path,label+' winners, runs and wickets',description,body,'CollectionPage',{'breadcrumb_name':label})
        world_body+='<section class="panel"><h2>'+esc(label)+'</h2>'
        if titles: world_body+=table(['Team','Titles'],titles[:8],caption=label+' titles')
        if leaders['runs']:
            world_body+='<h3>Top run scorers</h3>'+table(['Player','Runs','HS'],[[a(pp.get(r['id'],'/players/'),r['name']),num(r['runs']),num(r['highest'])] for r in leaders['runs'][:8]],caption=label+' runs')
        if leaders['wickets']:
            world_body+='<h3>Top wicket takers</h3>'+table(['Player','Wickets','Best'],[[a(pp.get(r['id'],'/players/'),r['name']),num(r['wickets']),esc(r['best'] or '')] for r in leaders['wickets'][:8]],caption=label+' wickets')
        world_body+='<p>'+a(path,'Full '+label+' records')+'</p></section>'
    recent=sorted(all_wc,key=lambda m:(m['date'],m['id']),reverse=True)[:20]
    if recent: world_body+='<section class="panel"><h2>Recent World Cup matches</h2>'+match_table(recent,mp,20)+'</section>'
    world_body+='<p class="note">Champions Trophy and qualifying events are not mixed into these World Cup title counts. '+a('/records/','Career records')+' · '+a('/questions/','Questions')+'</p>'
    page('/world-cup/','World Cup winners, run scorers and wicket takers','World Cup winners, leading run scorers and wicket takers for men and women in ODIs and T20s, from recorded matches in this archive.',world_body,'CollectionPage')

    # Team-pair pages answer a common search intent while retaining a single
    # canonical overview page for the full rivalry directory.
    pairs=defaultdict(list)
    for m in matches:
        if len(m.get('teams',[]))!=2:continue
        pairs[tuple(sorted(m['teams']))].append(m)
    pair_rows=[]
    for pair,ms in sorted(pairs.items(),key=lambda item:(-len(item[1]),item[0])):
        left,right=pair;path='/head-to-head/'+slug(left+'-vs-'+right)+'-'+hashlib.sha1('|'.join(pair).encode()).hexdigest()[:6]+'/'
        wins=Counter(m.get('outcome',{}).get('winner') for m in ms)
        pair_rows.append([a(path,left+' vs '+right),len(ms),num(wins.get(left,0)),num(wins.get(right,0)),num(sum(not m.get('outcome',{}).get('winner') for m in ms)),', '.join(sorted({m['format'] for m in ms}))])
        format_rows=[]
        for fmt in ('Test','ODI','T20I'):
            for gender in ('Men','Women'):
                subset=[m for m in ms if m['format']==fmt and m['gender']==gender]
                if not subset:continue
                result_counts=Counter(m.get('outcome',{}).get('winner') for m in subset)
                format_rows.append([fmt,gender,len(subset),result_counts.get(left,0),result_counts.get(right,0),sum(not m.get('outcome',{}).get('winner') for m in subset)])
        recent=sorted(ms,key=lambda m:(m['date'],m['id']),reverse=True)[:25]
        pair_body=heading(left+' vs '+right+' head-to-head records',f'{len(ms):,} recorded international matches between {left} and {right}, with format, gender and result breakdowns.','HEAD-TO-HEAD')+actions()
        pair_body+='<div class="stats">'+''.join(f'<div><strong>{num(value)}</strong><span>{label}</span></div>' for value,label in [(len(ms),'Matches'),(wins.get(left,0),left+' wins'),(wins.get(right,0),right+' wins'),(sum(not m.get('outcome',{}).get('winner') for m in ms),'Draws / ties / no result')])+'</div>'
        pair_body+=cw.win_share(left,right,wins.get(left,0),wins.get(right,0),sum(not m.get('outcome',{}).get('winner') for m in ms))
        if format_rows:pair_body+='<section class="panel"><h2>Results by format and gender</h2>'+table(['Format','Gender','Matches',left+' wins',right+' wins','Other'],format_rows,caption=left+' versus '+right+' results by format and gender')+'</section>'
        pair_body+='<section class="panel"><h2>Recent recorded matches</h2>'+match_table(recent,mp,25)+'</section><p class="note">Wins count the match winner recorded in the source. Draws, ties and no-results are grouped as Other; abandoned matches without an outcome remain visible.</p><p>'+a('/head-to-head/','Browse every international head-to-head')+' · '+a(gp['teams'][left],left)+' · '+a(gp['teams'][right],right)+'</p>'
        page(path,left+' vs '+right+' head-to-head records',f'{left} vs {right}: {len(ms):,} recorded matches, {wins.get(left,0):,} wins for {left} and {wins.get(right,0):,} for {right}. Format and gender tables with scorecards.',pair_body,'CollectionPage',{'breadcrumb_name':left+' vs '+right})
    h2h_body=heading('International cricket head-to-head records','Compare every full-member rivalry by format, gender, wins and linked scorecards.','HEAD-TO-HEAD DATA')+actions()
    h2h_body+='<p class="lede">Select a rivalry for a compact breakdown of Tests, ODIs and T20Is. The directory uses the published international match scope and keeps men’s and women’s records visible separately.</p>'
    h2h_body+='<section class="panel"><h2>Most-recorded rivalries</h2>'+table(['Rivalry','Matches','First team wins','Second team wins','Other','Formats'],pair_rows,caption='International head-to-head directory')+'</section>'
    page('/head-to-head/','International cricket head-to-head records','International cricket head-to-head records by team, format, gender, wins and scorecards.',h2h_body,'CollectionPage')

    # Best scorecard performances are derived only from complete innings rows.
    batting=[];bowling=[]
    for card in cards.values():
        m=card['match']
        for inn in card.get('innings',[]):
            if inn.get('super_over'):continue
            team=inn.get('team');opponent=next((t for t in m['teams'] if t!=team),'')
            for b in inn.get('batting',[]):
                if b.get('id') in pp and b.get('runs') is not None:
                    batting.append((b['runs'],b.get('balls'),m,team,opponent,b))
            for b in inn.get('bowling',[]):
                if b.get('id') in pp and b.get('wickets') is not None and b.get('runs') is not None:
                    bowling.append((b['wickets'],b.get('runs'),m,team,opponent,b))
    batting.sort(key=lambda x:(-x[0],-(x[1] or 0),x[2]['date'],x[2]['id']))
    bowling.sort(key=lambda x:(-x[0],x[1],x[2]['date'],x[2]['id']))
    bat_rows=[]
    for runs,balls,m,team,opp,b in batting[:100]:
        sr=rate(runs,balls,100)
        bat_rows.append([a(pp[b['id']],people[b['id']]['name']),m['date'],esc(team),esc(opp),m['format'],num(runs),num(balls),decimal_stat(sr),a(mp[m['id']],'Scorecard')])
    bowl_rows=[]
    for wickets,conceded,m,team,opp,b in bowling[:100]:
        overs_display=b.get('overs_display') or ('—' if b.get('balls') is None else str((b.get('balls') or 0)//6)+'.'+str((b.get('balls') or 0)%6))
        bowl_rows.append([a(pp[b['id']],people[b['id']]['name']),m['date'],esc(team),esc(opp),m['format'],num(wickets),num(conceded),esc(overs_display),a(mp[m['id']],'Scorecard')])
    performance_body=heading('Best international cricket performances','The biggest recorded batting innings and bowling spells in the published international scorecard archive.','PERFORMANCE RECORDS')+actions()
    performance_body+='<p class="lede">These tables rank individual scorecard innings. They do not replace official career records, and historical coverage varies by era. Every row links to the underlying scorecard.</p>'
    performance_body+=cw.leader_bars([(people[b['id']]['name'],runs) for runs,balls,m,team,opp,b in batting[:10]],'Highest individual scores in this archive')
    performance_body+=cw.leader_bars([(people[b['id']]['name'],wickets) for wickets,conceded,m,team,opp,b in bowling[:10]],'Most wickets in an innings in this archive')
    performance_body+='<section class="panel"><h2>Highest individual scores</h2>'+table(['Player','Date','Team','Opponent','Format','Runs','Balls','Strike rate','Match'],bat_rows,caption='Highest individual international batting scores')+'</section>'
    performance_body+='<section class="panel"><h2>Best bowling figures by wickets</h2>'+table(['Player','Date','Team','Opponent','Format','Wickets','Runs conceded','Overs','Match'],bowl_rows,caption='Best individual international bowling figures by wickets')+'</section>'
    performance_body+='<p class="note">Batting strike rate is shown only when balls faced are recorded. Bowling rows are ordered by wickets, then fewest runs conceded. Super overs are excluded.</p>'
    page('/records/best-innings/','Best international cricket innings and bowling figures','Highest individual international batting scores and best bowling figures from verified scorecards.',performance_body,'CollectionPage')

    # Milestones provide a date-oriented entry point for long-tail searches.
    milestones=[];year_counts=defaultdict(Counter)
    for runs,balls,m,team,opp,b in batting:
        if runs>=100 or runs>=50:
            kind='Century' if runs>=100 else 'Fifty'
            milestones.append((m['date'],kind,people[b['id']]['name'],b['id'],team,opp,m,b))
            year_counts[m['date'][:4]][kind]+=1
    for wickets,conceded,m,team,opp,b in bowling:
        if wickets>=5:
            kind='Five-wicket haul' if wickets<10 else 'Ten-wicket haul'
            milestones.append((m['date'],kind,people[b['id']]['name'],b['id'],team,opp,m,b))
            year_counts[m['date'][:4]][kind]+=1
    milestones.sort(key=lambda x:(x[0],x[2]),reverse=True)
    milestone_rows=[]
    for d,kind,name,pid,team,opp,m,b in milestones[:150]:
        value=b.get('runs') if kind in ('Century','Fifty') else b.get('wickets')
        milestone_rows.append([d,kind,a(pp[pid],name),esc(team),esc(opp),m['format'],num(value),a(mp[m['id']],'Scorecard')])
    milestone_year_rows=[[year,num(values.get('Century',0)),num(values.get('Fifty',0)),num(values.get('Five-wicket haul',0)),num(values.get('Ten-wicket haul',0))] for year,values in sorted(year_counts.items(),reverse=True)]
    milestone_body=heading('International cricket player milestones','Centuries, fifties and five-wicket hauls by year, with direct links to the scorecards that recorded them.','PLAYER MILESTONES')+actions()
    milestone_body+='<p class="lede">Milestones are calculated from available scorecard innings. A missing historical innings is not treated as a zero, so the archive is transparent about what it can verify.</p>'
    if milestone_year_rows:milestone_body+='<section class="panel"><h2>Milestones by year</h2>'+table(['Year','Centuries','Fifties','Five-wicket hauls','Ten-wicket hauls'],milestone_year_rows,caption='International player milestones by year')+'</section>'
    milestone_body+='<section class="panel"><h2>Recent recorded milestones</h2>'+table(['Date','Milestone','Player','Team','Opponent','Format','Figure','Match'],milestone_rows,caption='Recent international cricket player milestones')+'</section>'
    milestone_body+='<p class="note">A century is an innings of 100 or more runs. A five-wicket haul is five or more wickets in an innings; ten-wicket hauls are included in that category and separately labelled.</p>'
    page('/milestones/','International cricket player milestones','International cricket centuries, fifties and five-wicket hauls by year with linked scorecards.',milestone_body,'CollectionPage')

    # Venue overview combines match volume with the highest recorded team
    # innings, a useful landing page before the detailed ground directories.
    venue_rows=[]
    venue_groups=defaultdict(list)
    for m in matches:venue_groups[m.get('venue') or 'Unknown ground'].append(m)
    for venue,ms in sorted(venue_groups.items(),key=lambda item:(-len(item[1]),item[0])):
        scores=[(t.get('runs'),t.get('team'),m) for m in ms for t in (m.get('totals') or []) if t.get('runs') is not None]
        best=max(scores,key=lambda x:x[0],default=(None,'',None))
        venue_rows.append([a(gp['grounds'].get(venue,'/grounds/'),venue),len(ms),', '.join(sorted({m['format'] for m in ms})),min(m['date'] for m in ms)[:4]+'–'+max(m['date'] for m in ms)[:4],num(best[0]),esc(best[1])])
    venue_body=heading('International cricket venue records','Match volume, format coverage and highest recorded team totals across international grounds.','VENUE RECORDS')+actions()
    venue_body+='<p class="lede">Use a ground to explore its full match history, then open individual scorecards for innings-level detail. Venue totals use recorded scorecard innings only.</p>'
    venue_body+='<section class="panel"><h2>Most-used international grounds</h2>'+table(['Ground','Matches','Formats','Recorded span','Highest team total','Team'],venue_rows[:150],caption='International cricket venue records')+'</section>'
    venue_body+='<p class="note">A highest team total is the largest recorded innings total at that venue in the published archive. It is not a venue rating and does not infer pitch conditions.</p>'
    page('/venue-records/','International cricket venue records','International cricket grounds ranked by match volume, format coverage and highest recorded team totals.',venue_body,'CollectionPage')

def build_question_hubs(people,matches,pp,mp,gp,careers,all_cards,player_q=None,featured_names=()):
    """Publish useful answers for recurring cricket-statistics searches."""
    cards=all_cards or {}
    questions=[]
    def leader(fmt,metric,gender=None,lower=False):
        candidates=[p for p in people.values() if (gender is None or p.get('gender')==gender) and p.get('career',{}).get(fmt,{}).get(metric) is not None]
        if not candidates:return None
        return sorted(candidates,key=lambda p:((p['career'][fmt][metric] if lower else -p['career'][fmt][metric]),p['name']))[0]
    def record_answer(fmt,metric,label,record_path):
        p=leader(fmt,metric,'Men')
        if not p:return f'The archive has no recorded men’s {fmt} {label.lower()} leader for this snapshot.',record_path
        value=p['career'][fmt][metric]
        return f'{p["name"]} leads the published men’s {fmt} career snapshot for {label.lower()} with {num(value)}. Open the full leaderboard to see the qualification and the other players in the record set.',record_path
    for fmt,metric,label,path in [('Test','runs','career runs','/records/men/test/most-runs/'),('ODI','runs','career runs','/records/men/odi/most-runs/'),('T20I','runs','career runs','/records/men/t20i/most-runs/'),('Test','wickets','career wickets','/records/men/test/most-wickets/'),('ODI','wickets','career wickets','/records/men/odi/most-wickets/'),('T20I','wickets','career wickets','/records/men/t20i/most-wickets/')]:
        answer,link_path=record_answer(fmt,metric,label,path)
        questions.append({'slug':f'most-{fmt.lower()}-{metric}','title':f'Who has the most {fmt} international {label}?','description':f'Find the leading {fmt} international players by {label}, with qualification rules and linked career records.','category':'CAREER RECORDS','answer':answer,'links':[(link_path,f'Open {fmt} {label} leaderboard'),('/records/', 'Browse all records')]})

    batting=[];bowling=[]
    for card in cards.values():
        m=card['match']
        for inn in card.get('innings',[]):
            if inn.get('super_over'):continue
            team=inn.get('team');opp=next((t for t in m['teams'] if t!=team),'')
            for b in inn.get('batting',[]):
                if b.get('id') in pp and b.get('runs') is not None:batting.append((b['runs'],b.get('balls'),m,team,opp,b))
            for b in inn.get('bowling',[]):
                if b.get('id') in pp and b.get('wickets') is not None and b.get('runs') is not None:bowling.append((b['wickets'],b.get('runs'),m,team,opp,b))
    batting.sort(key=lambda x:(-x[0],-(x[1] or 0),x[2]['date'],x[2]['id']))
    bowling.sort(key=lambda x:(-x[0],x[1],x[2]['date'],x[2]['id']))
    for fmt in ('Test','ODI','T20I'):
        scores=[x for x in batting if x[2]['format']==fmt]
        if scores:
            runs,balls,m,team,opp,b=scores[0]
            questions.append({'slug':f'highest-{fmt.lower()}-individual-score','title':f'What is the highest individual score in {fmt} cricket?','description':f'Highest recorded individual {fmt} international score in the Cricket Wicket scorecard archive.','category':'SCORECARD RECORDS','answer':f'{people[b["id"]]["name"]} has the highest recorded {fmt} score in this archive: {num(runs)} for {team} against {opp} on {m["date"]}. {"Balls faced: "+num(balls)+"." if balls is not None else "Balls faced are not recorded for this innings."} Open the scorecard to inspect the complete innings.', 'links':[('/records/best-innings/','Browse best innings'),(mp[m['id']],'Open the scorecard')]})
        spells=[x for x in bowling if x[2]['format']==fmt]
        if spells:
            wickets,conceded,m,team,opp,b=spells[0]
            questions.append({'slug':f'best-{fmt.lower()}-bowling-figures','title':f'What are the best bowling figures in {fmt} cricket?','description':f'Best recorded individual {fmt} international bowling figures, ordered by wickets and runs conceded.','category':'SCORECARD RECORDS','answer':f'{people[b["id"]]["name"]} recorded the best {fmt} figures in this archive: {num(wickets)} wickets for {num(conceded)} runs for {team} against {opp} on {m["date"]}. Open the scorecard for the full spell and match result.', 'links':[('/records/best-innings/','Browse best bowling figures'),(mp[m['id']],'Open the scorecard')]})

    questions.extend([
        {'slug':'difference-between-test-odi-t20i','title':'What is the difference between Test, ODI and T20I cricket?','description':'A clear comparison of the three international formats, innings structure, time and scoring context.','category':'FORMAT GUIDE','answer':'Tests give each side two innings and can run for up to five days. ODIs give each side one innings of up to 50 overs. T20Is give each side one innings of up to 20 overs. The shorter formats make each delivery more scarce; comparing a rate or total without its format and workload can mislead.', 'links':[('/records/','Explore format records'),('/methodology/','Read the statistical definitions')]},
        {'slug':'how-is-batting-average-calculated','title':'How is a cricket batting average calculated?','description':'Learn the batting-average formula and see how not-outs and missing dismissals affect a career record.','category':'STATISTICS EXPLAINED','answer':'Batting average is runs divided by dismissals. A not-out innings adds runs and innings but does not add a dismissal. Cricket Wicket recomputes combined averages from the published runs and dismissals; if the denominator is missing or zero, the page shows an unavailable or inapplicable value rather than inventing one.', 'links':[('/methodology/','Read the full definitions'),('/records/','Browse batting-average records')]},
        {'slug':'what-is-cricket-strike-rate','title':'What is strike rate in cricket?','description':'Understand batting strike rate, bowling strike rate and the denominators required for each.','category':'STATISTICS EXPLAINED','answer':'Batting strike rate is 100 multiplied by runs divided by balls faced. Bowling strike rate is legal balls divided by wickets. Both require a recorded denominator. A dash means the source did not record the required balls or wickets; it is not a zero.', 'links':[('/methodology/','Read the rate definitions'),('/compare/','Compare two players')]},
        {'slug':'how-do-head-to-head-records-work','title':'How do international cricket head-to-head records work?','description':'See how Cricket Wicket counts matches, wins and other results for every full-member rivalry.','category':'RIVALRIES','answer':'A head-to-head page selects matches involving the same two national teams, then separates them by format and gender. Wins use the winner recorded in the match source. Draws, ties, no-results and matches without a winner remain visible in the Other column.', 'links':[('/head-to-head/','Browse every rivalry'),('/teams/','Explore team records')]},
        {'slug':'what-is-a-century-and-five-wicket-haul','title':'What is a century or a five-wicket haul in cricket?','description':'A scorecard guide to centuries, fifties and five-wicket bowling milestones.','category':'SCORECARD TERMS','answer':'A century is an innings of at least 100 runs. A fifty is an innings of at least 50 runs but below 100. A five-wicket haul is an innings with at least five wickets; ten-wicket match hauls are separately labelled when the scorecards support them.', 'links':[('/milestones/','Browse player milestones'),('/records/best-innings/','Browse performance records')]},
        {'slug':'are-international-career-records-complete','title':'Are Cricket Wicket international career records complete?','description':'Understand the difference between official career snapshots and the available scorecard archive.','category':'DATA COVERAGE','answer':'Career tables are independent official international snapshots and may include recognized matches that are outside the ball-by-ball scorecard archive. Match explorers use the published international scorecards and label result-only records. Missing fields remain unavailable; they are never inferred from a partial match.', 'links':[('/methodology/','Read coverage and definitions'),('/data-coverage/','Inspect current coverage')]},
        {'slug':'how-to-compare-cricket-players','title':'How should two cricket players be compared?','description':'A practical, format-aware way to compare international careers without hiding workload or era.','category':'PLAYER COMPARISON','answer':'Choose the same format, gender and data scope first. Read runs or wickets alongside innings, dismissals, balls, average and strike rate, then inspect the playing span and opposition context. Cricket Wicket keeps career snapshots separate from narrower available-scorecard samples so a partial archive is not presented as a full career.', 'links':[('/compare/','Open player comparison'),('/players/','Browse player profiles')]},
        {'slug':'who-has-the-most-womens-odi-runs','title':'Who has the most women’s ODI runs?','description':'The leading women’s ODI run scorer in the published official career snapshot, with a link to the qualified leaderboard.','category':'WOMEN’S RECORDS','answer':'Open the women’s ODI most-runs leaderboard for the current snapshot, qualification and the rest of the table.','links':[('/records/women/odi/most-runs/','Women’s ODI most runs'),('/records/women/t20i/most-runs/','Women’s T20I most runs')]},
        {'slug':'who-has-the-most-odi-sixes','title':'Who has hit the most ODI sixes?','description':'Find the men’s ODI sixes leader in the published career snapshot, with fours and boundary context.','category':'CAREER RECORDS','answer':'Sixes are a career counting statistic. Read them with fours, runs and balls so a sixes lead is not mistaken for a faster innings.','links':[('/records/men/odi/most-sixes/','Men’s ODI most sixes'),('/blog/2026-09-11/','Rohit vs Kohli boundary note')]},
        {'slug':'how-to-read-a-cricket-worm-chart','title':'How do you read a cricket worm chart?','description':'A short guide to worms, Manhattans and partnerships on Cricket Wicket scorecards.','category':'MATCH PICTURES','answer':'A worm plots the innings total at the end of each over. Dots mark wickets. A Manhattan shows runs scored in each over. Partnerships are the runs added between recorded falls of wicket. Cricket Wicket draws these only from recorded overs; historical result-only matches have no worm.','links':[('/matches/','Browse scorecards'),('/studio/','Export a match card')]},
        {'slug':'what-is-a-result-only-match','title':'What does result-only mean on a cricket scorecard?','description':'Why some historical international matches have a result but no innings or player figures.','category':'DATA COVERAGE','answer':'A result-only record confirms the match result, teams, date and venue, but the source does not provide a usable innings or lineup. It remains searchable as an international match while batting and bowling figures stay unavailable.', 'links':[('/matches/','Browse match records'),('/methodology/','Read the archive policy')]},
        {'slug':'which-team-has-most-international-wins','title':'Which international team has the most recorded wins?','description':'Compare national teams by recorded international match wins in the Cricket Wicket archive.','category':'TEAM RECORDS','answer':'The team leaderboard below is calculated from every published international match result. It counts only matches where a winner is recorded, while draws, ties and no-results remain separate. Use the team page to inspect the format and gender mix behind the total.', 'links':[('/teams/','Browse team records'),('/head-to-head/','Compare rivalries')]},
    ])
    women_odi=leader('ODI','runs','Women')
    sixes_odi=leader('ODI','sixes','Men')
    for q in questions:
        if q['slug']=='who-has-the-most-womens-odi-runs' and women_odi:
            q['answer']=f'{women_odi["name"]} leads the published women’s ODI career snapshot with {num(women_odi["career"]["ODI"]["runs"])} runs. Open the leaderboard for qualification, other names and the data date.'
        if q['slug']=='who-has-the-most-odi-sixes' and sixes_odi:
            q['answer']=f'{sixes_odi["name"]} leads the published men’s ODI career snapshot for sixes with {num(sixes_odi["career"]["ODI"]["sixes"])}. Read sixes with fours, runs and balls; a sixes lead is not the same as a faster innings.'
    team_wins=Counter(m.get('outcome',{}).get('winner') for m in matches if m.get('outcome',{}).get('winner'))
    if team_wins:
        winner,n=team_wins.most_common(1)[0]
        for q in questions:
            if q['slug']=='which-team-has-most-international-wins':q['answer']=f'{winner} has the most recorded wins in this published international match archive: {num(n)}. This is a volume count, not a win percentage; use the team and head-to-head pages to inspect formats, genders and opponents.'

    index_body=heading('Cricket questions, answered with data','Clear answers to the cricket questions people ask most: records, formats, player statistics, rivalries and scorecard terms.','CRICKET QUESTIONS')+actions()
    index_body+='<p class="lede">Each answer links directly to a table, profile or scorecard. Record-holder answers use the current published snapshot and show their data date on the linked page.</p><div class="grid three">'+''.join(f'<a class="feature-card" href="/questions/{q["slug"]}/"><span>{q["category"]}</span><h2>{q["title"]}</h2><p>{q["description"]}</p><small>Read the answer →</small></a>' for q in questions)+'</div>'
    featured=featured_question_cards(player_q or {},people,featured_names)
    if featured:
        index_body+='<section class="section-heading"><h2>Stats questions fans search</h2>'+a('/questions/players/','Browse player questions')+'</section>'
        index_body+='<p>Named-player pages use official career figures. The heading, the paragraph and the search snippet all contain the same number.</p><div class="grid three">'+''.join(f'<a class="feature-card" href="{esc(q["url"])}"><span>PLAYER STATS</span><h2>{esc(q["title"])}</h2><p>{esc(q["answer"])}</p><small>Read the answer →</small></a>' for q in featured)+'</div>'
    index_body+='<section class="panel"><h2>Use the data after the answer</h2><p>'+a('/records/','Browse qualified records')+' · '+a('/compare/','Compare two careers')+' · '+a('/players/','Open player profiles')+' · '+a('/questions/players/','Player stats questions')+' · '+a('/head-to-head/','Explore rivalries')+' · '+a('/world-cup/','Open the World Cup archive')+'</p></section>'
    page('/questions/','Cricket questions answered with international data','Answers to common cricket questions about international records, formats, players, scorecards and statistics.',index_body,'CollectionPage')
    for q in questions:
        body=heading(q['title'],q['description'],q['category'])+actions()+'<article class="research-article"><p>'+q['answer']+'</p><h2>Explore the underlying records</h2><p>'+' · '.join(a(path,label) for path,label in q['links'])+'</p><p class="note">This answer is generated from Cricket Wicket’s validated international dataset. Career figures and available scorecard figures are kept as separate layers; see the methodology page for definitions and coverage dates.</p></article>'
        page('/questions/'+q['slug']+'/',q['title'],q['description'],body,'Article',{'headline':q['title'],'author':{'@type':'Organization','name':'Cricket Wicket','url':BASE+'/about/'}})
    if player_q:
        assert_clean_bundle(player_q)
        snapshot=careers['meta'].get('checked_at','')[:10]
        page('/questions/players/','International player stats questions','Dedicated pages for how many runs, wickets, centuries and sixes named international players have scored, from official career snapshots.',player_question_directory(player_q,people,pp,table),'CollectionPage')
        for pid,pack in player_q.items():
            player=people[pid]
            for spec in pack['specs']:
                related=[item for item in pack['specs'] if item['url']!=spec['url']]
                body=heading(spec['title'],spec['description'],'PLAYER STATS')+actions()+question_page(spec,player,related,snapshot)
                extra={'headline':spec['title'],'author':{'@type':'Organization','name':'Cricket Wicket','url':BASE+'/about/'},'faq':{'@context':'https://schema.org','@type':'FAQPage','mainEntity':[{'@type':'Question','name':spec['title'],'acceptedAnswer':{'@type':'Answer','text':spec['answer']}}]},'breadcrumb_name':spec['title']}
                page(spec['url'],spec['title'],spec['description'],body,'Article',extra)

def build_daily_blog(people,pp,careers,all_cards=None,mp=None):
    """Publish a compact series of data-backed daily notes with editorial visuals."""
    left=next((p for p in people.values() if p.get('name')=='Virat Kohli'),None)
    right=next((p for p in people.values() if p.get('name')=='Rohit Sharma'),None)
    if not left or not right or 'ODI' not in left.get('career',{}) or 'ODI' not in right.get('career',{}):return
    a1,a2=left['career']['ODI'],right['career']['ODI']
    post_date='2026-09-10'; checked=esc(careers['meta'].get('checked_at',TODAY)[:10])
    posts=[]
    def publish(slug_name,title,description,visual,alt,lead,content,callout,width=1432,height=1076,*,date=post_date,data_date=checked,methodology=None):
        path='/blog/'+date+'/'+((slug_name.strip('/')+'/') if slug_name else '')
        article='<div class="daily-note">'+heading(title,'A small daily lesson in reading international cricket numbers.','DAILY NOTE')
        article+=f'<p class="daily-byline"><span>Cricket Wicket</span><span>·</span><time datetime="{date}">{date}</time><span>·</span><span>Data checked {esc(data_date)}</span></p>'+actions()
        article+='<article><p>'+lead+'</p><figure class="daily-infographic"><a href="/assets/art/blog/'+visual+'" aria-label="Open full-size infographic"><img src="/assets/art/blog/'+visual+'" width="'+str(width)+'" height="'+str(height)+'" loading="eager" alt="'+esc(alt)+'"></a><figcaption>'+esc(title)+' · Cricket Wicket · data checked '+esc(data_date)+'</figcaption></figure>'+content
        article+='<div class="data-callout">'+callout+'</div><p>'+a('/compare/','Compare two international careers')+' · '+a(pp[left['id']],left['name']+' profile')+' · '+a(pp[right['id']],right['name']+' profile')+' · '+a('/studio/','Create your own visual')+'</p><p class="note">'+esc(methodology or 'Career figures are independent official snapshots. Batting average is runs ÷ dismissals; strike rate is 100 × runs ÷ balls faced. A missing denominator stays unavailable.')+'</p></article></div>'
        extra={'headline':title,'datePublished':date,'dateModified':date,'author':{'@type':'Organization','name':'Cricket Wicket','url':BASE+'/about/'},'publisher':{'@type':'Organization','name':'Cricket Wicket','url':BASE+'/'}}
        if visual.endswith(('.png','.webp','.jpg')):extra.update(image=BASE+'/assets/art/blog/'+visual,mainEntityOfPage=BASE+path)
        page(path,title,description,article,'Article',extra)
        posts.append((date,path,title,description,visual,alt,width,height))

    publish('','How to compare two international batters fairly','A practical Cricket Wicket guide to reading runs, batting average and strike rate together, using a Virat Kohli and Rohit Sharma ODI example.','2026-09-10-compare-batters.svg','Infographic comparing Virat Kohli and Rohit Sharma in ODI runs, batting average and strike rate','When two batters are compared, one number rarely settles the question. Runs show accumulated output, average shows what a player scores per dismissal, and strike rate shows scoring pace. Read the three together, and keep the format and career scope the same.','<h2>What the example shows</h2><p>In this ODI snapshot, '+a(pp[left['id']],left['name'])+' leads the run total with <strong>'+num(a1.get('runs'))+'</strong> from '+num(a1.get('innings'))+' innings. '+a(pp[right['id']],right['name'])+' has '+num(a2.get('runs'))+' runs from '+num(a2.get('innings'))+' innings. That is the volume view.</p><p>The average comparison favours '+left['name']+' in this snapshot, while the strike-rate values are close. Era, role, opposition, venues and opportunity still matter.</p>','<div><strong>'+decimal_stat(a1.get('avg'))+'</strong><span>'+left['name']+' ODI average</span></div><div><strong>'+decimal_stat(a2.get('avg'))+'</strong><span>'+right['name']+' ODI average</span></div><div><strong>'+decimal_stat(a1.get('sr'))+' / '+decimal_stat(a2.get('sr'))+'</strong><span>ODI strike rates · '+left['name']+' / '+right['name']+'</span></div>',1200,760)
    publish('average-needs-dismissals','Why batting average needs its denominator','A Cricket Wicket explainer on dismissals, not-outs and the denominator behind every international batting average.','2026-09-10-average-dismissals-data.svg','Data infographic comparing Virat Kohli and Rohit Sharma ODI runs, dismissals and batting average','A batting average is not runs divided by innings. It is runs divided by dismissals, which is why a not-out can lift a player’s average without adding another dismissal. The denominator carries the context.','<h2>Read the denominator first</h2><p>In the same ODI snapshot, '+a(pp[left['id']],left['name'])+' has <strong>'+num(a1.get('runs'))+'</strong> runs and '+num(a1.get('outs'))+' dismissals, producing an average of '+decimal_stat(a1.get('avg'))+'. '+a(pp[right['id']],right['name'])+' has '+num(a2.get('runs'))+' runs from '+num(a2.get('outs'))+' dismissals, producing '+decimal_stat(a2.get('avg'))+'. A not-out contributes runs but leaves the dismissal count unchanged.</p><p>That makes average useful for comparing scoring returns per opportunity, but it should sit beside innings, not-outs and the format. Cricket Wicket keeps unavailable dismissals visible instead of filling them with an estimate.</p>','<div><strong>'+num(a1.get('outs'))+'</strong><span>'+left['name']+' ODI dismissals</span></div><div><strong>'+num(a2.get('outs'))+'</strong><span>'+right['name']+' ODI dismissals</span></div><div><strong>'+decimal_stat(a1.get('avg'))+' / '+decimal_stat(a2.get('avg'))+'</strong><span>ODI batting averages · '+left['name']+' / '+right['name']+'</span></div>',1200,760)
    publish('strike-rate-needs-balls','Why strike rate needs balls faced','A Cricket Wicket explainer on batting strike rate and the balls-faced denominator that makes pace comparable.','2026-09-10-strike-rate-balls-data.svg','Data infographic comparing Virat Kohli and Rohit Sharma ODI runs, balls faced and batting strike rate','Strike rate describes scoring pace: runs per 100 balls faced. Without balls faced, a run total cannot tell us whether an innings was paced quickly or slowly.','<h2>Pace needs a workload</h2><p>'+a(pp[left['id']],left['name'])+' has '+num(a1.get('runs'))+' ODI runs from '+num(a1.get('balls'))+' balls, a strike rate of '+decimal_stat(a1.get('sr'))+'. '+a(pp[right['id']],right['name'])+' has '+num(a2.get('runs'))+' runs from '+num(a2.get('balls'))+' balls, a strike rate of '+decimal_stat(a2.get('sr'))+'. The formula is simple—100 × runs ÷ balls—but the denominator keeps the comparison honest.</p><p>Strike rate should be read with role, era, opposition and format. A Test rate and a T20I rate answer different questions. If balls are not recorded, the correct result is unavailable, not zero.</p>','<div><strong>'+num(a1.get('balls'))+'</strong><span>'+left['name']+' ODI balls faced</span></div><div><strong>'+num(a2.get('balls'))+'</strong><span>'+right['name']+' ODI balls faced</span></div><div><strong>'+decimal_stat(a1.get('sr'))+' / '+decimal_stat(a2.get('sr'))+'</strong><span>ODI strike rates · '+left['name']+' / '+right['name']+'</span></div>',1200,760)
    for file in sorted((ROOT/'content/blog').glob('*.json')):
        note=json.loads(file.read_text(encoding='utf-8'))
        if note['date']>TODAY:continue
        figures=note['players']
        for row in figures:
            boundary=4*row['fours']+6*row['sixes']
            if boundary!=row['boundary_runs'] or f"{100*boundary/row['runs']:.2f}"!=row['boundary_share']:
                raise ValueError('Blog infographic numbers do not reconcile: '+str(file))
        content=''.join('<h2>'+esc(section['heading'])+'</h2><p>'+section['html']+'</p>' for section in note['sections'])
        content+='<h2>The figures behind the infographic</h2>'+table(['Player','ODI runs','4s','6s','Boundary runs','Boundary share'],[[a(pp[row['id']],row['name']),num(row['runs']),num(row['fours']),num(row['sixes']),num(row['boundary_runs']),row['boundary_share']+'%'] for row in figures],caption=note['scope']+' · checked '+note['data_date'])
        callout=''.join('<div><strong>'+row['boundary_share']+'%</strong><span>'+esc(row['name'])+' · boundary share</span></div>' for row in figures)
        callout+='<div><strong>'+num(abs(figures[0]['boundary_runs']-figures[1]['boundary_runs']))+'</strong><span>Gap in boundary runs</span></div>'
        publish(note['slug'],note['title'],note['description'],note['visual'],note['alt'],note['lead'],content,callout,note['width'],note['height'],date=note['date'],data_date=note['data_date'],methodology=note['methodology'])
    featured=cw.showcase_card(all_cards or {})
    if featured and mp:
        match=featured['match']
        url=mp.get(match['id'],'/matches/')
        title='How a World Cup chase looks as a worm'
        description='Read the India v Australia 2023 ODI World Cup final as a worm, Manhattan and partnership picture, drawn from recorded overs.'
        path='/blog/2026-09-12/how-a-chase-looks/'
        article='<div class="daily-note">'+heading(title,'A daily lesson in reading an international scorecard as a picture.','DAILY NOTE')
        article+=f'<p class="daily-byline"><span>Cricket Wicket</span><span>·</span><time datetime="2026-09-12">2026-09-12</time></p>'+actions()
        article+='<article><p>'+esc(" v ".join(match.get("teams") or []))+' · '+esc(match.get("date"))+' · '+esc(match.get("format"))+'. A worm is the innings total at the end of each over. Dots are wickets. The dashed line is the chase target when both innings are recorded.</p>'
        article+=cw.match_lab(featured)
        article+='<p>'+a(url,'Open the full scorecard')+' · '+a('/studio/','Export a match card in Studio')+'</p><p class="note">Drawn from recorded overs only. Historical result-only matches have no worm.</p></article></div>'
        extra={'headline':title,'datePublished':'2026-09-12','dateModified':'2026-09-12','author':{'@type':'Organization','name':'Cricket Wicket','url':BASE+'/about/'},'publisher':{'@type':'Organization','name':'Cricket Wicket','url':BASE+'/'}}
        page(path,title,description,article,'Article',extra)
        posts.append(('2026-09-12',path,title,description,'','',1200,760))
    posts.sort(key=lambda item:item[0],reverse=True)
    cards=''
    for date,path,title,description,visual,alt,width,height in posts:
        img=f'<img src="/assets/art/blog/{visual}" width="{width}" height="{height}" loading="lazy" alt="{esc(alt)}">' if visual else ''
        cards+='<a class="feature-card daily-index-card" href="'+path+'">'+img+'<span>'+esc(date)+'</span><h2>'+esc(title)+'</h2><p>'+esc(description)+'</p><small>Read this note →</small></a>'
    index=heading('Cricket Wicket daily notes','Small, useful lessons from international cricket records, written with the data in view.','DAILY NOTES')+actions()+'<div class="grid two daily-index-grid">'+cards+'</div><section class="panel"><h2>Keep exploring</h2><p>'+a('/questions/','Cricket questions answered with data')+' · '+a('/records/','International records')+' · '+a('/insights/','Statistical insights')+'</p></section>'
    page('/blog/','Cricket Wicket daily cricket notes','Short, data-backed cricket lessons about international records, player statistics and scorecards.',index,'CollectionPage')

def build_collections(people,matches,pp,mp,gp,groups,careers,arc,hist,editorial=None,all_cards=None):
    ranked=sorted(people.values(),key=lambda p:aggregate(p['career']).get('runs') or 0,reverse=True)
    latest=matches[:8]
    faces=[]
    for name in HERO_CAST:
        src=ILLUSTRATIONS.get(name)
        player=next((p for p in people.values() if p.get('name')==name),None)
        if src and player:faces.append((name,src,pp[player['id']]))
    body=homepage_hero(len(people),len(matches),faces)
    body+='<div class="stats">'+''.join(f'<div><strong>{num(n)}</strong><span>{label}</span></div>' for n,label in [(len(people),'Player profiles'),(len(matches),'Match records'),(len(groups['teams']),'National teams'),('3','Formats covered')])+'</div>'
    body+=homepage_insights(matches,mp,people,gp)
    featured=cw.showcase_card(all_cards or {})
    if featured:body+=cw.homepage_lab(featured,mp.get(featured['match']['id'],'/matches/'))
    body+='<div class="section-heading"><h2>Start with a question</h2></div><div class="grid three">'+''.join(f'<a class="feature-card" href="{path}"><span>{category}</span><h3>{question}</h3><p>{desc}</p></a>' for path,category,question,desc in [('/records/men/odi/most-runs/','CAREER RECORDS','Who leads the run charts?','Explore qualified records across all three formats.'),('/compare/','PLAYER COMPARISON','How do their careers compare?','Choose a format and compare like-for-like figures.'),('/teams/','TEAMS & GROUNDS','Where does a team win?','Discover results, venues and international rivalries.')])+'</div><div class="section-heading"><h2>Recent recorded results</h2>'+a('/matches/','All matches →')+'</div>'+match_table(latest,mp)
    body+='<div class="section-heading"><h2>Explore the major archives</h2></div><div class="grid three">'+''.join(f'<a class="feature-card" href="{path}"><span>{category}</span><h3>{title}</h3><p>{desc}</p></a>' for path,category,title,desc in [('/world-cup/','WORLD CUP','World Cup records','Tournament results, scorecards and player pathways.'),('/head-to-head/','RIVALRIES','Head-to-head records','Compare every full-member international rivalry.'),('/records/best-innings/','PERFORMANCES','Best innings','Highest scores and bowling figures from scorecards.'),('/milestones/','MILESTONES','Player milestones','Centuries, fifties and five-wicket hauls by year.'),('/venue-records/','VENUES','Venue records','Ground volume, formats and highest team totals.'),('/blog/2026-09-11/','DAILY NOTE','Rohit vs Kohli: the boundary story','More sixes, a different scoring mix. See the numbers in our latest infographic.')])+'</div>'
    body+='<div class="section-heading"><h2>Career leaders</h2>'+a('/players/','Player directory →')+'</div><div class="grid two leader-grid">'
    for metric,title in [('runs','The run makers'),('wickets','The wicket takers')]:
        leaders=sorted(ranked,key=lambda p:aggregate(p['career']).get(metric) or 0,reverse=True)[:8]
        body+='<section class="leader-panel"><h3>'+title+'</h3>'+table(['Player','Team',metric.title()],[[a(pp[p['id']],p['name']),esc(' / '.join(p['teams'])),num(aggregate(p['career']).get(metric))] for p in leaders])+ '</section>'
    body+='</div>'
    body+='<p class="note">Career data updated '+careers['meta']['checked_at'][:10]+'. Historical result-only matches are labeled. '+a('/methodology/','Understand coverage →')+'</p>'
    page('/','Cricket stats, player records & scorecards','Cricket Wicket: international cricket career statistics, player comparisons, match scorecards, team records and analysis.',body,'WebSite')
    # Crawlable pagination supplies all directory entries without requiring JavaScript.
    for kind,items,size,title in [('players',ranked,100,'Cricket player directory'),('matches',matches,100,'International match results')]:
        for i in range(0,len(items),size):
            number=i//size+1;path=f'/{kind}/' if number==1 else f'/{kind}/page/{number}/'
            body=heading(title+(' · Page '+str(number) if number>1 else ''),'Search the international archive. Player figures are career snapshots; match coverage is labeled.')
            body+=f'<form class="filters" data-directory="{kind}"><label>Search<input name="q" placeholder="Search {kind}"></label>'+options('gender',['Men','Women'])+options('format',['Test','ODI','T20I'])
            body+=options('team',sorted(groups['teams']))
            if kind=='matches':body+=options('year',sorted({m['date'][:4] for m in matches},reverse=True))
            body+='<button class="primary">Apply filters</button><button type="reset">Reset</button></form>'+actions()+'<div id="directory-results" aria-live="polite">'
            if kind=='players':body+=table(['Player','Team','Gender','Career runs','Career wickets'],[[a(pp[p['id']],p['name']),' '.join(team_badge(t,gp['teams'].get(t)) for t in p['teams'] if t in gp['teams']),p['gender'],num(aggregate(p['career']).get('runs')),num(aggregate(p['career']).get('wickets'))] for p in items[i:i+size]])
            else:body+=match_table(items[i:i+size],mp,size)
            body+='</div><nav class="pagination" aria-label="Directory pages">'+(a(f'/{kind}/' if number==2 else f'/{kind}/page/{number-1}/','← Previous') if number>1 else '')+f'<span>Page {number} / {math.ceil(len(items)/size)}</span>'+(a(f'/{kind}/page/{number+1}/','Next →') if i+size<len(items) else '')+'</nav>'
            page(path,title+(' · Page '+str(number) if number>1 else ''),f'Browse {title.lower()}, page {number}. Search by name, format and gender.',body,'CollectionPage')
    for kind,g in groups.items():
        title={'teams':'International teams','grounds':'Cricket grounds','series':'International series'}[kind]
        all_years=sorted({m['date'][:4] for ms in g.values() for m in ms},reverse=True)
        listing=heading(title,'Browse international results and follow the links to individual matches.')+f'<form class="filters entity-index-filter" data-entity-index-filter="{kind}"><div class="filter-intro"><strong>Filter the directory</strong><span id="entity-index-count">{len(g):,} entries</span></div>'+options('gender',['Men','Women'])+options('format',['Test','ODI','T20I'])+options('year',all_years,'Year')+f'<label>From year<input name="from" type="number" min="{all_years[-1]}" max="{all_years[0]}" inputmode="numeric"></label><label>To year<input name="to" type="number" min="{all_years[-1]}" max="{all_years[0]}" inputmode="numeric"></label><button class="primary">Apply filters</button><button type="reset">Reset</button></form><div class="grid three" id="entity-directory-results">'
        for name,ms in sorted(g.items(),key=lambda item:len(item[1]),reverse=True):
            span=f'{ms[-1]["date"][:4]} to {ms[0]["date"][:4]}'
            listing+=f'<a class="feature-card entity-index-card" data-entity-card="{esc(name)}" href="{gp[kind][name]}"><h2>{esc(name)}</h2><p>{len(ms):,} recorded matches</p><small>{esc(span)}</small></a>'
            extra={'breadcrumb_name':name}
            if kind=='teams':
                totals=team_totals(ms,name)
                title1,description=team_seo(name,totals)
                body=heading(name,f'{totals["matches"]:,} recorded matches · {totals["first"][:4]} to {totals["last"][:4]}','TEAMS')+actions()
                body+=f'<p class="player-intro">{esc(team_intro(name,totals))}</p>'
                body+=team_glance(name,totals)+entity_visuals(kind,name,ms)+cw.result_decades(ms,name)
                body+='<div class="stats">'+''.join(f'<div><strong>{n:,}</strong><span>{esc(label)}</span></div>' for label,n in [('Won',totals['won']),('Lost',totals['lost']),('Draw / tie / no result',totals['other']),('Matches',totals['matches'])])+'</div>'
                body+='<section class="panel" id="career-records"><h2>Results by format and gender</h2><p class="muted">Official match winners in this archive. Other is draws, ties and no results.</p>'
                body+=table(['Format','Gender','Matches','Wins','Losses','Other','Win rate'],results_table_rows(totals),caption=name+' results by format and gender')+'</section>'
                rivals=defaultdict(Counter)
                for m in ms:
                    opp=next(t for t in m['teams'] if t!=name);rivals[opp]['played']+=1;rivals[opp]['wins']+=int(m['outcome'].get('winner')==name)
                body+='<section class="panel"><h2>Head-to-head results</h2>'+table(['Opponent','Matches','Wins'],[[a(h2h_path(name,opp),opp),str(s['played']),str(s['wins'])] for opp,s in sorted(rivals.items(),key=lambda x:x[1]['played'],reverse=True)],caption=name+' against each full-member opponent')+'</section>'
                squad=[p for p in ranked if name in p['teams']]
                body+='<section class="panel"><h2>Explore players</h2><p class="note">Players linked to this team; career totals can include other representative teams.</p>'+table(['Player','Gender','Career runs','Career wickets'],[[a(pp[p['id']],p['name']),p['gender'],num(aggregate(p['career']).get('runs')),num(aggregate(p['career']).get('wickets'))] for p in squad[:30]],caption=name+' players by career runs')+'</section>'
                faq_html,faq_schema=team_faq(name,totals,gp[kind][name])
                body+=faq_html
                extra.update({'mainEntity':team_schema(name,gp[kind][name],description),'faq':faq_schema})
            elif kind=='grounds':
                totals=ground_totals(ms)
                title1,description=ground_seo(name,totals)
                body=heading(name,f'{totals["matches"]:,} recorded matches · {totals["first"][:4]} to {totals["last"][:4]}','GROUNDS')+actions()
                body+=f'<p class="player-intro">{esc(ground_intro(name,totals))}</p>'
                body+=ground_glance(name,totals)+entity_visuals(kind,name,ms)
                body+='<section class="panel" id="career-records"><h2>Recorded matches by format</h2>'+table(['Format','Men','Women'],[[fmt,str(sum(m['format']==fmt and m['gender']=='Men' for m in ms)),str(sum(m['format']==fmt and m['gender']=='Women' for m in ms))] for fmt in ['Test','ODI','T20I']],caption=name+' matches by format and gender')+'</section>'
                faq_html,faq_schema=ground_faq(name,totals)
                body+=faq_html
                extra.update({'mainEntity':ground_schema(name,gp[kind][name],description),'faq':faq_schema})
            else:
                title1=name+' match records'
                description=f'{name}: international cricket results, format breakdowns and linked scorecards.'
                body=heading(name,f'{len(ms):,} recorded matches · {ms[-1]["date"][:4]} to {ms[0]["date"][:4]}',kind.upper())+actions()+entity_visuals(kind,name,ms)
                body+='<section class="panel"><h2>Recorded matches by format</h2>'+table(['Format','Men','Women'],[[fmt,str(sum(m['format']==fmt and m['gender']=='Men' for m in ms)),str(sum(m['format']==fmt and m['gender']=='Women' for m in ms))] for fmt in ['Test','ODI','T20I']],caption=name+' matches by format')+'</section>'
            body+='<h2>Recent recorded matches</h2>'+entity_filter_form(kind,name,ms)+'<div id="entity-results" aria-live="polite">'+match_table(ms,mp,50)+'</div>'
            from urllib.parse import urlencode
            query={'team':name} if kind=='teams' else {'q':name}
            body+='<p>'+a('/matches/?'+urlencode(query),'Search all matching matches →')+' · '+a('/questions/','Cricket questions')+'</p>'
            page(gp[kind][name],title1,description,body,'CollectionPage',extra)
        page('/'+kind+'/',title,'Explore '+title.lower()+' and their international match records.',listing+'</div>','CollectionPage')
    records_body=heading('Cricket records','Qualified career leaderboards. Choose a format and gender for meaningful comparisons.')
    metrics=[('most-runs','runs','Most runs',False,0),('most-wickets','wickets','Most wickets',False,0),('most-centuries','hundreds','Most centuries',False,0),('most-matches','matches','Most appearances',False,0),('best-batting-average','avg','Highest batting average',False,20),('best-bowling-average','bowlAvg','Lowest bowling average',True,20),('most-fifties','fifties','Most fifties',False,0),('most-fours','fours','Most fours',False,0),('most-sixes','sixes','Most sixes',False,0),('best-batting-strike-rate','sr','Highest batting strike rate',False,500),('best-bowling-strike-rate','bowlSr','Lowest bowling strike rate',True,20),('best-economy','econ','Lowest economy rate',True,300)]
    for gender in ['Men','Women']:
        for fmt in ['Test','ODI','T20I']:
            entries=[{'id':p['id'],'name':p['name'],'url':pp[p['id']],'teams':p['teams'],**{k:v for k,v in p['career'][fmt].items() if k not in ['source','sources','disciplines']}} for p in ranked if p['gender']==gender and fmt in p['career']]
            feed=f'/data/records-{gender.lower()}-{fmt.lower()}.json';dump(feed,entries)
            records_body+=f'<section class="panel"><h2>{gender} · {fmt}</h2><div class="link-grid">'
            for key,field,label,lower,minimum in metrics:
                path=f'/records/{gender.lower()}/{fmt.lower()}/{key}/';records_body+=a(path,label)
                minimum_field={'bowlAvg':'wickets','bowlSr':'wickets','econ':'legal','sr':'balls'}.get(field,'innings')
                minimum_label={'wickets':'wickets','legal':'legal balls','balls':'balls faced','innings':'batting innings'}[minimum_field]
                qualified=[p for p in entries if p.get(field) is not None and (p.get(minimum_field) or 0)>=minimum]
                qualified.sort(key=lambda p:(p[field] if lower else -p[field],p['name']))
                qualification=f'Minimum {minimum} '+minimum_label if minimum else 'All recorded careers; no minimum qualification'
                bowling_record=field in ('wickets','bowlAvg','bowlSr','econ')
                innings_field='bowling_innings' if bowling_record else 'innings';runs_field='conceded' if bowling_record else 'runs'
                rows=[];previous=None;rank=0
                for i,p in enumerate(qualified[:100],1):
                    if p[field]!=previous:rank=i
                    previous=p[field];rows.append([str(rank),a(p['url'],p['name']),esc(' / '.join(p['teams'])),num(p[field]),num(p.get('matches')),num(p.get(innings_field)),num(p.get(runs_field)),num(p.get('wickets'))])
                scope_nav='<nav class="scope-nav" aria-label="Leaderboard scope">'+''.join(a(f'/records/{g.lower()}/{f.lower()}/{key}/',g+' · '+f) for g in ('Men','Women') for f in ('Test','ODI','T20I'))+'</nav>'
                body=heading(f'{gender} {fmt}: {label}',qualification,'CAREER LEADERBOARD')+scope_nav+actions()+cw.leader_bars([(p['name'],p[field]) for p in qualified[:10]],f'Top recorded {label.lower()} · {gender} {fmt}')+f'<form class="filters" data-records="{feed}" data-field="{field}" data-minimum-field="{minimum_field}" data-lower="{str(lower).lower()}"><label>Minimum {minimum_label}<input name="minimum" type="number" min="0" value="{minimum}"></label><label>Player or team<input name="q"></label><button class="primary">Apply</button><button type="reset">Reset</button></form><div id="record-results" aria-live="polite">'+table(['Rank','Player','Teams',label,'Matches','Bowling innings' if bowling_record else 'Batting innings','Runs conceded' if bowling_record else 'Runs','Wickets'],rows)+'</div><p class="note">Tied figures share a competition rank. The initial table lists up to 100 qualifying records; filters browse all careers in this format. Snapshot '+careers['meta']['checked_at'][:10]+'.</p>'
                if qualified:
                    top=qualified[0];body+='<section class="panel"><h2>What this table shows</h2><p>'+esc(top['name'])+' leads this snapshot. '+esc(label)+': '+num(top[field])+'. '+esc(qualification)+'. Changing the qualification can change the leader.</p><p>'+a('/methodology/','Definitions and coverage')+'</p></section>'
                page(path,f'{gender} {fmt} {label.lower()} records',f'{label} in {gender.lower()} {fmt} cricket. {qualification}. Career leaderboard with ties and player profiles.',body,'CollectionPage')
            records_body+='</div></section>'
    page('/records/','International cricket records','Test, ODI and T20I batting and bowling career records for men and women, with transparent qualification rules.',records_body,'CollectionPage')
    # Flexible comparisons use only the two selected summary files.
    choices=''.join(f'<option value="{pp[p["id"]]}">{esc(p["name"])} · {p["gender"]}</option>' for p in ranked[:80])
    compare=heading('Compare cricket careers','Search for two players and choose a format. Career records are compared independently of archive coverage.')+actions()+f'<form id="compare-form" class="filters"><label>Find another player<input id="compare-search" placeholder="Search all players"></label><label>First player<select name="a">{choices}</select></label><label>Second player<select name="b">{choices}</select></label>'+options('format',['Test','ODI','T20I'])+'<label>Data scope<select name="basis"><option value="career">Career records</option><option value="archive">Available archive</option></select></label><label>From year (archive)<input type="number" name="from" min="1877" max="2100"></label><label>To year (archive)<input type="number" name="to" min="1877" max="2100"></label><label>Opponent (archive)<input name="opponent" placeholder="e.g. Australia"></label><label>Venue setting (archive)<select name="setting"><option value="">All</option><option>Home</option><option>Away</option><option>Neutral</option><option>Unknown</option></select></label><label>Recent batting innings (archive)<select name="recent"><option value="">All</option><option>10</option><option>20</option><option>50</option></select></label><label>Minimum batting innings<input type="number" name="minimum" min="0" value="0"></label><button class="primary">Compare</button></form><div id="compare-result" aria-live="polite"><p>Select two players to compare their career records.</p></div>'
    if not editorial: compare+='<section class="panel"><h2>Featured comparisons</h2>'
    for left,right in [('Virat Kohli','Rohit Sharma'),('Sachin Tendulkar','Don Bradman'),('Joe Root','Steve Smith'),('Mithali Raj','Meg Lanning'),('Jasprit Bumrah','James Anderson'),('Shubman Gill','Joe Root'),('Smriti Mandhana','Ellyse Perry')]:
        p1=next((p for p in ranked if p['name']==left),None);p2=next((p for p in ranked if p['name']==right),None)
        if not p1 or not p2:continue
        path='/compare/'+slug(left)+'-vs-'+slug(right)+'/'
        if not editorial: compare+='<p>'+a(path,left+' vs '+right)+'</p>'
        pair_art=''
        if left in ILLUSTRATIONS and right in ILLUSTRATIONS:
            pair_art='<div class="comparison-avatars"><div><img src="'+ILLUSTRATIONS[left]+'" width="420" height="480" alt="'+esc(left)+'"><strong>'+esc(left)+'</strong></div><span aria-hidden="true">VS</span><div><img src="'+ILLUSTRATIONS[right]+'" width="420" height="480" alt="'+esc(right)+'"><strong>'+esc(right)+'</strong></div></div>'
        bits=[]
        faq_items=[]
        for fmt in ['ODI','Test','T20I']:
            s1=p1['career'].get(fmt,{});s2=p2['career'].get(fmt,{})
            if (s1.get('wickets') or 0)>=20 and (s2.get('wickets') or 0)>=20:
                bits.append(f'{fmt} wickets {s1["wickets"]:,} and {s2["wickets"]:,}')
                leader=left if s1['wickets']>=s2['wickets'] else right
                faq_items.append((f'Who has more {fmt} wickets, {left} or {right}?', f'{leader} has more recorded {fmt} wickets: {left} {s1["wickets"]:,}, {right} {s2["wickets"]:,}.'))
            elif s1.get('runs') is not None and s2.get('runs') is not None:
                bits.append(f'{fmt} runs {s1["runs"]:,} and {s2["runs"]:,}')
                leader=left if s1['runs']>=s2['runs'] else right
                faq_items.append((f'Who has more {fmt} runs, {left} or {right}?', f'{leader} has more recorded {fmt} runs: {left} {s1["runs"]:,}, {right} {s2["runs"]:,}.'))
        intro=(left+' vs '+right+': '+', '.join(bits)+'. Different eras and sample sizes need context.') if bits else 'Career comparison by format. Different eras and sample sizes need context.'
        content=heading(left+' vs '+right,intro,'PLAYER COMPARISON')+pair_art+actions()
        content+=f'<p class="player-intro">{esc(intro)}</p>'
        for fmt in ['Test','ODI','T20I']:
            if fmt not in p1['career'] and fmt not in p2['career']:continue
            s1=p1['career'].get(fmt,{});s2=p2['career'].get(fmt,{})
            focus='bowling' if (s1.get('wickets') or 0)>(s1.get('runs') or 0) and (s2.get('wickets') or 0)>(s2.get('runs') or 0) else 'batting'
            content+='<section class="panel"><h2>'+fmt+'</h2>'+cw.pair_lab(left,right,s1,s2,focus)+table([left,'Metric',right],[[num(s1.get(k)),label,num(s2.get(k))] for k,label in [('matches','Matches'),('innings','Innings'),('runs','Runs'),('avg','Batting average'),('sr','Strike rate'),('hundreds','Centuries'),('fifties','Fifties'),('fours','Fours'),('sixes','Sixes'),('balls','Balls faced'),('wickets','Wickets'),('five_w','Five-wicket innings'),('bowlSr','Bowling strike rate'),('bowlAvg','Bowling average'),('econ','Economy')]],caption=left+' vs '+right+' '+fmt+' career figures')+'</section>'
        if faq_items:
            content+='<section class="panel player-faq" id="player-questions"><h2>Questions fans ask</h2><dl>'+''.join(f'<div><dt>{esc(q)}</dt><dd>{esc(ans)}</dd></div>' for q,ans in faq_items[:6])+'</dl></section>'
        content+='<p>'+a(pp[p1['id']],left+' profile')+' · '+a(pp[p2['id']],right+' profile')+' · '+a('/compare/','Choose other players')+'</p>'
        extra={'breadcrumb_name':left+' vs '+right}
        if faq_items:
            extra['faq']={'@context':'https://schema.org','@type':'FAQPage','mainEntity':[{'@type':'Question','name':q,'acceptedAnswer':{'@type':'Answer','text':ans}} for q,ans in faq_items[:6]]}
        page(path,left+' vs '+right+' stats: Test, ODI and T20I',intro if len(intro)<158 else intro[:157].rsplit(' ',1)[0]+'.',content,'WebPage',extra)
    if editorial: compare += '<section class="panel"><h2>Featured comparisons</h2>'+editorial['comparison_cards']+'</section>'
    else: compare+='</section>'
    page('/compare/','Compare cricket players','Compare international cricketers by format, career runs, averages, centuries and wickets.',compare)
    entity_index=[{'name':name,'url':url,'kind':kind} for kind,g in gp.items() for name,url in g.items()];dump('/data/entity-index.json',entity_index)
    page('/studio/','International cricket content studio','Create and export publication-ready cricket visuals from verified career, match and innings data.',studio_markup(a),'SoftwareApplication',{'applicationCategory':'DesignApplication'})
    page('/embed/','Cricket Wicket player card','An embeddable international cricket career summary.','<div id="embed-result" aria-live="polite">Loading career card…</div>',noindex=True)
    page('/search/','Search cricket statistics','Find cricket players, teams, series and grounds.',heading('Find your next cricket answer','Search players, teams, series and grounds.')+'<form id="search-form" class="hero-search" role="search"><label>Search<input name="q" type="search" placeholder="Player, team or match" required autocomplete="off"></label><button class="primary">Search</button></form><div id="search-results" aria-live="polite"></div>',noindex=True)
    page('/saved/','Saved cricket research','Your saved cricket pages and filtered searches on this device.',heading('Your cricket notebook','Saved pages and searches stay in this browser on this device.')+'<button id="clear-saved">Clear saved pages</button><div id="saved-results"></div>',noindex=True)
    page('/corrections/','Report a cricket data correction','Prepare a precise correction with the player, match, metric and supporting evidence.',heading('Help improve the record','Create a correction report to share with the site owner. This form does not send your information automatically.')+'<form id="correction-form" class="panel"><label>Page URL<input name="url" type="url" required></label><label>What needs correcting?<textarea name="issue" required></textarea></label><label>Correct value and supporting evidence<textarea name="evidence" required></textarea></label><button class="primary">Download correction report</button></form><p class="note">Review the downloaded report before sharing it. No account or personal details are required.</p>')
    methods=heading('Data coverage & methodology','Clear definitions, dates and limits for every layer of the archive.')+'<div class="stats">'+''.join(f'<div><strong>{num(v)}</strong><span>{label}</span></div>' for v,label in [(careers['meta']['players'],'Career records'),(arc['meta']['matches'],'Ball-data scorecards'),(hist['meta']['added_matches'],'Historical matches'),(careers['meta']['archive_players_without_career'],'Unmatched identities')])+'</div><section class="panel"><h2>Career records</h2><p>The publication focuses on the twelve full-member national teams, for men and women. Only recognized senior Tests, ODIs and T20Is appear in match browsing. Official player careers retain all recognized internationals, including matches against associates and recognized representative teams. Snapshot '+careers['meta']['checked_at'][:10]+'. A missing field is displayed as a dash, never inferred from a partial archive. Career and delivery-derived figures are never added together.</p><h2>Match and player analysis</h2><p>Ball-by-ball data is provided by <a href="https://cricsheet.org/">Cricsheet</a>. The explorer combines verified historical scorecards with delivery-derived scorecards and excludes super overs. Historical scorecards contribute innings statistics even where ball-by-ball data is unavailable. Result-only matches have no inferred individual figures. Unknown balls faced remain unknown; rates require a complete denominator for the selected innings.</p><h2>Venue setting</h2><p>Home, away and neutral are assigned only for recognized host cities using the cricket team’s host territory. Other locations remain Unknown. These categories describe the venue, not which team is named first.</p><h2>Statistical definitions</h2><p>Batting average = runs / dismissals. Strike rate = 100 × runs / balls faced. Bowling average = conceded runs / wickets. Economy = 6 × conceded runs / legal balls. Combined averages are recomputed from totals, not averaged across formats. No dismissals or no wickets makes the corresponding average N/A. A dash means an unrecorded source field. Rates are displayed to two decimal places; computed rates are truncated consistently. Historical scorecards retain their original over lengths.</p><h2>Record qualifications</h2><p>Average leaderboards default to 20 batting innings or 20 bowling wickets. Ties share a rank. Results by team include men and women unless filtered. Historical results may lack innings totals, lineups and deliveries.</p><h2>Corrections and freshness</h2><p>Changes pass identity, count and scorecard checks before publication. '+a('/corrections/','Prepare a correction report')+'. This publication does not supply live scores, future fixtures or official rankings.</p></section>'
    page('/methodology/','Cricket data coverage & methodology','Understand career data, scorecard coverage, archive filters, record qualification and update dates.',methods)
    insights=heading('The numbers, explained','Reproducible observations from the published data. Every claim links to its supporting table.')+'<div class="grid three">'
    for gender,fmt in [('Men','Test'),('Women','ODI'),('Men','T20I')]:
        eligible=[p for p in ranked if p['gender']==gender and fmt in p['career'] and p['career'][fmt].get('runs') is not None];eligible.sort(key=lambda p:p['career'][fmt]['runs'],reverse=True)
        top=eligible[:5];path='/insights/'+gender.lower()+'-'+fmt.lower()+'-run-leaders/';title=gender+' '+fmt+': the leading run scorers'
        insights+=f'<a class="feature-card" href="{path}"><span>CAREER SNAPSHOT</span><h2>{title}</h2><p>Read the table and understand its limits.</p></a>'
        content=heading(title,'An analysis of the current career snapshot.','STATISTICAL EXPLAINER')+actions()
        if top:
            p=top[0];content+='<section class="panel"><h2>The leader in this snapshot</h2><p>'+a(pp[p['id']],p['name'])+' has '+num(p['career'][fmt]['runs'])+' runs from '+num(p['career'][fmt]['matches'])+' matches in this record set.</p>'+table(['Player','Matches','Runs','Average'],[[a(pp[p['id']],p['name'])]+[num(p['career'][fmt].get(k)) for k in ['matches','runs','avg']] for p in top])+'<h2>How to read the ranking</h2><p>Total runs measure accumulated output. They do not adjust for era, batting position, opposition or opportunity. Use average and innings qualifications alongside volume, and inspect individual profiles before drawing comparisons.</p><p>'+a(f'/records/{gender.lower()}/{fmt.lower()}/most-runs/','Explore the full leaderboard')+'</p><p class="note">Snapshot '+careers['meta']['checked_at'][:10]+'. Figures are generated from the same validated career table as the leaderboard.</p></section>'
        page(path,title,'A data-backed look at '+gender.lower()+' '+fmt+' run leaders, their records and how to interpret the ranking.',content)
    if editorial: insights += '<section class="panel"><h2>Original statistical research</h2>'+editorial['insight_cards']+'</section>'
    page('/insights/','Cricket statistical insights','Original explanations of international cricket records, with linked tables and transparent methodology.',insights+'</div>','CollectionPage')
    # The previous international URLs remain valid; the script resolves query IDs.
    page('/international/','International cricket archive','Find international match records and player profiles.',heading('International cricket archive')+'<p>'+a('/matches/','Browse match records')+' · '+a('/players/','Browse player careers')+'</p><p id="legacy-status">Opening the requested record when an ID is supplied…</p>',noindex=True)
    build_evergreen_hubs(people,matches,pp,mp,gp,all_cards)

if __name__=='__main__': main()
