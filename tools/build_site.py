"""Build Cricket Wicket's searchable, pre-rendered static publication."""
from __future__ import annotations
import argparse, hashlib, html, json, math, re, shutil, unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from cricket_scope import publication_data, FULL_MEMBERS, load_cards, complete_career_counts,career_scorecards
from home_visuals import homepage_hero, homepage_insights, archive_visuals
from publication_assets import prepare_assets, social_image
from publication_pages import trust_pages
from portraits import load_portraits, portrait_figure, portrait_schema
from profile_research import select_research_players, profile_research_section, opponent_pages, research_index
from editorial_research import build_editorial, entity_context
from studio_page import studio_markup
from data_health import profile_coverage, coverage_page

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / '_site'
BASE = 'https://cricket.rkjat.in'
TODAY = date.today().isoformat()
PAGES = {}
PREVIOUS = {}
SETTINGS=json.loads((ROOT/'data/site-settings.json').read_text(encoding='utf-8')) if (ROOT/'data/site-settings.json').exists() else {}
ASSET_VERSION = hashlib.sha256(b''.join(p.read_bytes() for p in sorted((ROOT/'web').glob('*')) if p.is_file())).hexdigest()[:10]
ALIASES = {'SR Tendulkar':'Sachin Tendulkar','V Kohli':'Virat Kohli','RG Sharma':'Rohit Sharma','JJ Bumrah':'Jasprit Bumrah','DG Bradman':'Don Bradman','M Muralitharan':'Muttiah Muralitharan','M Muralidaran':'Muttiah Muralitharan','SK Warne':'Shane Warne','RT Ponting':'Ricky Ponting','KC Sangakkara':'Kumar Sangakkara','DPMD Jayawardene':'Mahela Jayawardene','JH Kallis':'Jacques Kallis','BC Lara':'Brian Lara','SM Gavaskar':'Sunil Gavaskar','R Dravid':'Rahul Dravid','A Kumble':'Anil Kumble','R Ashwin':'Ravichandran Ashwin','RA Jadeja':'Ravindra Jadeja','SC Ganguly':'Sourav Ganguly','V Sehwag':'Virender Sehwag','SS Mandhana':'Smriti Mandhana','H Kaur':'Harmanpreet Kaur','M Raj':'Mithali Raj','J Goswami':'Jhulan Goswami','EA Perry':'Ellyse Perry','MM Lanning':'Meg Lanning','JE Root':'Joe Root','SPD Smith':'Steve Smith','KS Williamson':'Kane Williamson','JM Anderson':'James Anderson','DA Warner':'David Warner','AC Gilchrist':'Adam Gilchrist','ST Jayasuriya':'Sanath Jayasuriya','KL Rahul':'KL Rahul','RR Pant':'Rishabh Pant','HH Pandya':'Hardik Pandya','AC Kerr':'Amelia Kerr','SCJ Broad':'Stuart Broad'}
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
    if inn['fall']:body+='<details class="innings-details"><summary>Fall of wickets</summary><p>'+esc(' · '.join(f'{w["runs"]}/{w["wicket"]} ({w["player"]})' for w in inn['fall']))+'</p></details>'
    if inn['overs']:
        peak=max([o['runs'] for o in inn['overs']]+[1]);body+='<details class="innings-details"><summary>Over-by-over progression</summary><div class="spark" role="img" aria-label="Runs by over">'+''.join(f'<i class="{"wicket" if o["wickets"] else ""}" style="height:{max(2,o["runs"] / peak*100)}%" title="Over {o["over"]}: {o["runs"]} runs; {o["wickets"]} wickets"></i>' for o in inn['overs'])+'</div>'+table(['Over','Runs','Wickets','Total'],[[str(o[k]) for k in ['over','runs','wickets','total']] for o in inn['overs']])+'</details>'
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
    canonical=BASE+path; section=path.strip('/').split('/')[0]
    if len(path.strip('/').split('/'))>1:
        body='<nav class="breadcrumbs" aria-label="Breadcrumb">'+a('/','Home')+' / '+a('/'+section+'/',section.title())+' / <span>'+esc(title)+'</span></nav>'+body
    schema={'@context':'https://schema.org','@type':kind,'name':title,'description':description,'url':canonical,'isPartOf':{'@type':'WebSite','name':'Cricket Wicket','url':BASE+'/'}}
    if extra:schema.update(extra)
    if path!='/':schema['breadcrumb']={'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Home','item':BASE+'/'},{'@type':'ListItem','position':2,'name':title,'item':canonical}]}
    ld=json.dumps(schema,ensure_ascii=False).replace('<','\\u003c')
    nav=[('/matches/','Matches'),('/players/','Players'),('/teams/','Teams'),('/records/','Records'),('/compare/','Compare'),('/studio/','Studio'),('/series/','Series')]
    home_assets=(f'<link rel="stylesheet" href="/assets/home.css?v={ASSET_VERSION}"><script src="/assets/home.js?v={ASSET_VERSION}" defer></script>' if path=='/' else '')
    studio_assets=(f'<link rel="stylesheet" href="/assets/studio.css?v={ASSET_VERSION}"><script src="/assets/studio-core.js?v={ASSET_VERSION}" defer></script><script src="/assets/studio-images.js?v={ASSET_VERSION}" defer></script><script src="/assets/studio.js?v={ASSET_VERSION}" defer></script>' if path=='/studio/' else '')
    social=f'{BASE}/assets/social/site-default.png'
    verification=('<meta name="google-site-verification" content="'+esc(SETTINGS['google_site_verification'])+'">') if SETTINGS.get('google_site_verification') else ''
    document=f'''<!doctype html><html lang="en"><head><meta charset="utf-8">{verification}<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} | Cricket Wicket</title><meta name="description" content="{esc(description)}"><link rel="canonical" href="{canonical}"><meta name="robots" content="{'noindex,follow' if noindex else 'index,follow,max-image-preview:large'}"><meta name="theme-color" content="#10233f"><meta property="og:type" content="website"><meta property="og:title" content="{esc(title)} | Cricket Wicket"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{canonical}"><meta property="og:site_name" content="Cricket Wicket"><meta property="og:image" content="{social}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{social}"><link rel="icon" href="/favicon.svg"><link rel="apple-touch-icon" href="/apple-touch-icon.png"><link rel="manifest" href="/site.webmanifest"><link rel="stylesheet" href="/assets/wicket.css?v={ASSET_VERSION}"><link rel="stylesheet" href="/assets/publication.css?v={ASSET_VERSION}"><link rel="stylesheet" href="/assets/portraits.css?v={ASSET_VERSION}"><link rel="stylesheet" href="/assets/profile-research.css?v={ASSET_VERSION}"><link rel="stylesheet" href="/assets/editorial-research.css?v={ASSET_VERSION}"><script src="/assets/analysis-core.js?v={ASSET_VERSION}" defer></script><script src="/assets/wicket.js?v={ASSET_VERSION}" defer></script>{home_assets}{studio_assets}<script type="application/ld+json">{ld}</script></head><body><a class="skip" href="#main">Skip to statistics</a><div class="topline"><div class="wrap">THE GAME IN NUMBERS <span>Tests · ODIs · T20Is · Men & women</span></div></div><header><div class="wrap header"><a class="brand" href="/"><img src="/logo.svg" width="36" height="36" alt="">CRICKET WICKET<span>.</span></a><button id="menu" aria-label="Open navigation" aria-expanded="false" aria-controls="nav">☰</button><nav id="nav">{''.join(f'<a href="{url}" '+('aria-current="page"' if path.startswith(url) else '')+f'>{name}</a>' for url,name in nav)}<a class="search-link" href="/search/">Search</a><a class="ipl-link" href="https://crickrida.rkjat.in/">IPL Analytics</a></nav><button id="theme" aria-label="Toggle dark theme" aria-pressed="false">◐</button></div></header><main id="main" class="wrap">{body}</main><footer><div class="wrap"><strong>CRICKET WICKET</strong><p>Official international careers. Twelve national teams. Every format.</p><div class="footer-links">{a('/about/','About')}{a('/contact/','Contact')}{a('/data-coverage/','Data coverage')}{a('/datasets/','Datasets')}{a('/methodology/','Methodology')}{a('/insights/','Statistical insights')}{a('/world-cup/','World Cup archive')}{a('/head-to-head/','Head-to-head records')}{a('/records/best-innings/','Best performances')}{a('/milestones/','Player milestones')}{a('/venue-records/','Venue records')}{a('/corrections/','Report a correction')}{a('https://crickrida.rkjat.in/','IPL on Crickrida')}</div><p class="muted">Ball-by-ball data: <a href="https://cricsheet.org/">Cricsheet</a>. Corrections: <a href="mailto:rkideas65@gmail.com">rkideas65@gmail.com</a>.</p></div></footer><div id="toast" role="status" aria-live="polite"></div></body></html>'''
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
    return f'<section class="entity-visuals" aria-label="{esc(name)} archive visuals"><div class="entity-chart"><div class="entity-chart-heading"><div><p class="eyebrow">ARCHIVE AT A GLANCE</p><h2>How this archive is shaped</h2></div><span>{len(matches):,} total matches</span></div><figure><figcaption>Matches by international format</figcaption>{format_bars}</figure></div><figure class="entity-chart entity-year-chart"><figcaption>Matches by year · each bar is an exact annual count</figcaption><div class="entity-year-scroll" tabindex="0" role="img" aria-label="{esc(name)} matches by year">{year_bars}</div></figure>{outcome}</section>'
def team_badge(team, path=None):
    mark=f'<span class="team-badge"><img src="/assets/flags/{slug(team)}.svg" width="28" height="20" alt="" loading="lazy"><span>{esc(team)}</span></span>'
    return f'<a class="team-badge-link" href="{esc(path)}">{mark}</a>' if path else mark
def stats_table(p):
    career=p.get('career',{})
    groups=[('Batting',[('matches','Matches'),('innings','Innings'),('runs','Runs'),('avg','Average'),('sr','Strike rate'),('highest_display','Highest score'),('notouts','Not outs'),('hundreds','100s'),('fifties','50s'),('ducks','Ducks'),('fours','4s'),('sixes','6s'),('balls','Balls faced')]),('Bowling',[('matches','Matches'),('bowling_innings','Innings'),('legal','Balls'),('maidens','Maidens'),('conceded','Runs conceded'),('wickets','Wickets'),('bowlAvg','Average'),('econ','Economy'),('bowlSr','Strike rate'),('best_bowling','Best innings'),('best_match','Best match'),('four_w','4 wickets'),('five_w','5 wickets'),('ten_w','10 wickets')]),('Fielding',[('matches','Matches'),('fielding_innings','Innings'),('catches','Catches'),('stumpings','Stumpings'),('dismissals','Dismissals'),('keeper_catches','Keeper catches'),('fielder_catches','Fielder catches'),('dismissals_per_innings','Dismissals / inns'),('most_dismissals','Best innings')])]
    output='<div class="format-switch" data-format-switch role="group" aria-label="Filter career records"><button class="active" data-format="" aria-pressed="true">All formats</button>'+''.join(f'<button data-format="{fmt}" aria-pressed="false">{fmt}</button>' for fmt in ('Test','ODI','T20I') if fmt in career)+'</div><div class="career-format-list">'
    for fmt in ('Test','ODI','T20I'):
        if fmt not in career: continue
        stats=career[fmt]
        disciplines=''
        for title,fields in groups:
            figures=''.join('<div class="career-stat"><dt>'+label+'</dt><dd>'+stat_value(stats,key)+'</dd></div>' for key,label in fields)
            disciplines+='<section class="career-discipline"><h4>'+title+'</h4><dl class="career-stat-grid">'+figures+'</dl></section>'
        output+='<section class="career-format" data-career-format="'+fmt+'"><div class="career-format-head"><h3>'+fmt+'</h3><span>Official international career</span></div>'+disciplines+'</section>'
    return output+'</div>'

def options(name,values,label=None):return f'<label>{esc(label or name.title())}<select name="{name}"><option value="">All</option>'+''.join(f'<option value="{esc(v)}">{esc(v)}</option>' for v in values)+'</select></label>'

def main():
    global PREVIOUS
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
    dump('/data/studio-portraits.json',{pid:{k:p[k] for k in ('path','author','license','license_url','source_url')} for pid,p in portraits.items()})
    research_ids=select_research_players(people)
    for key,n in complete_career_counts(career_scorecards(ROOT,all_cards,people),people).items():careers['meta']['enriched_fields'][key]=careers['meta']['enriched_fields'].get(key,0)+n
    for p in people.values():p['name']=p.get('full_name',p['name'])
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
    print('Building career profiles...',flush=True)
    for pid,p in people.items():
        career=p['career'];tot=aggregate(career);path=pp[pid]; rows=sorted(innings[pid],key=lambda r:r['date']);apps=appearances[pid]
        summary={'id':pid,'name':p['name'],'teams':p['teams'],'gender':p['gender'],'career':career,'url':path}
        summary['career']={fmt:{k:v for k,v in s.items() if k not in ('source','sources','enrichment_source')} for fmt,s in career.items()}
        dump(path+'summary.json',summary);dump(path+'analytics.json',{'innings':rows,'appearances':apps,'note':'Available official match scorecards within site coverage. Super overs excluded. Unknown venue setting is not inferred.'})
        identity='<div class="player-identity"><span class="gender-mark">'+esc(p['gender'])+'</span>'+''.join(team_badge(t,gp['teams'].get(t)) for t in p['teams'] if t in gp['teams'])+'<span class="career-years">'+esc(p.get('first',''))+'–'+esc(p.get('last',''))+'</span></div>'
        profile_title='<div class="player-profile-heading">'+heading(p['name'],'International career statistics, records and scorecard analysis','PLAYER CAREER')+portrait_figure(pid,p['name'],portraits)+'</div>'+identity
        body=profile_title+profile_coverage(p,rows)+actions()+'<div class="stats">'+''.join(f'<div><strong>{num(tot.get(k))}</strong><span>{label}</span></div>' for k,label in [('matches','Internationals'),('runs','Career runs'),('hundreds','Centuries'),('wickets','Wickets')])+'</div>'
        checked_dates=sorted({careers['meta']['checked_at'][:10]}|{s['checked_at'][:10] for s in career.values() if s.get('checked_at')});snapshot_label='–'.join(dict.fromkeys([checked_dates[0],checked_dates[-1]]))
        body+='<section class="panel"><h2>Career records by format</h2>'+stats_table(p)+f'<p class="note">Career records checked: {snapshot_label}. — means not recorded; N/A means the statistic does not apply. Career totals are independent of the scorecard archive.</p></section>'
        if not career:body+='<p class="note">This archive identity has no matched career record. Do not treat its archive totals as a complete career.</p>'
        body+='<section class="panel" id="analysis" data-analytics="'+path+'analytics.json"><h2>Explore this player’s available match data</h2><p>'+str(len(apps))+' match appearances in available scorecards. Filters below apply to this archive only.</p><button id="load-analysis" class="primary">Open statistical explorer</button><div id="analysis-controls" hidden></div><div id="analysis-results" aria-live="polite"></div></section>'
        body+='<section class="panel"><h2>Recent available appearances</h2>'+table(['Date','Match','Format','Result'],[[x['date'],a(x['url'],' v '.join(x['teams'])),x['format'],esc(x['result'])] for x in apps[:12]])+'</section><p>'+ ' · '.join(a(gp['teams'][t],t) for t in p['teams'] if t in gp['teams'])+'</p>'
        body += profile_research_section(p, rows, path, curated=pid in research_ids)
        page(path,p['name']+(' · '+pid if names[slug(p['name'])]>1 else '')+' career stats & records',f'{p["name"]} international cricket statistics: Test, ODI and T20I runs, wickets, averages, career records and available match analysis.',body,'ProfilePage',{'mainEntity':{'@type':'Person','name':p['name'],'identifier':pid, **(portrait_schema(pid,portraits) or {})}})
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
    coverage_page(matches,all_cards,careers,page)
    dump('/data/routes.json',{'players':pp,'matches':mp})
    dump('/data/player-index.json',[{'id':pid,'name':p['name'],'url':pp[pid],'teams':p['teams'],'gender':p['gender'],'formats':list(p['career'] or p['formats']),'byFormat':{fmt:{'runs':stats.get('runs'),'wickets':stats.get('wickets')} for fmt,stats in p['career'].items()},'runs':aggregate(p['career']).get('runs'),'wickets':aggregate(p['career']).get('wickets')} for pid,p in people.items()])
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

    # World Cup and Champions Trophy archive, grouped by the event labels in
    # the source data. Qualifier-only events remain excluded by the national
    # match scope already applied in publication_data().
    world_events=defaultdict(list)
    for m in matches:
        event=m.get('event') or ''
        if re.search(r'world cup|world twenty20|world t20|champions trophy',event,re.I):
            world_events[event].append(m)
    world_rows=[]
    for event,ms in sorted(world_events.items(),key=lambda item:(min(x['date'] for x in item[1]),item[0])):
        world_rows.append([a(gp['series'].get(event,'/series/'),event),len(ms),', '.join(sorted({m['gender'] for m in ms})),', '.join(sorted({m['format'] for m in ms})),min(m['date'] for m in ms)[:4]+'–'+max(m['date'] for m in ms)[:4]])
    world_body=heading('World Cup cricket archive','World Cup, World T20 and Champions Trophy match records, scorecards and player pathways across men’s and women’s international cricket.','WORLD CUP DATA')+actions()
    world_body+='<p class="lede">Use the tournament links to move from an event overview into every recorded match. Results are limited to the international scope published by Cricket Wicket; result-only historical matches are labelled.</p>'
    world_body+='<div class="stats">'+''.join(f'<div><strong>{num(value)}</strong><span>{label}</span></div>' for value,label in [(len(world_events),'Tournament labels'),(sum(len(v) for v in world_events.values()),'Recorded matches'),(len({m["gender"] for ms in world_events.values() for m in ms}),'Genders'),(len({m["format"] for ms in world_events.values() for m in ms}),'Formats')])+'</div>'
    if world_rows:
        world_body+='<section class="panel"><h2>Tournament archive</h2>'+table(['Tournament','Matches','Gender','Formats','Recorded span'],world_rows,caption='World Cup and Champions Trophy tournament archive')+'</section>'
        recent=sorted([m for ms in world_events.values() for m in ms],key=lambda m:(m['date'],m['id']),reverse=True)[:20]
        world_body+='<section class="panel"><h2>Recent tournament results</h2>'+match_table(recent,mp,20)+'</section>'
    world_body+='<section class="panel"><h2>Explore further</h2><div class="link-grid">'+a('/records/men/odi/most-runs/','Men’s ODI run records')+a('/records/women/odi/most-runs/','Women’s ODI run records')+a('/records/best-innings/','Best international innings')+a('/milestones/','Player milestones')+'</div><p class="note">Tournament labels come from the verified match archive. An event page may contain matches from more than one host or edition when the source uses a shared competition name.</p></section>'
    page('/world-cup/','World Cup cricket records and scorecards','World Cup, World T20 and Champions Trophy international cricket records, match results and scorecards.',world_body,'CollectionPage')

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
        if format_rows:pair_body+='<section class="panel"><h2>Results by format and gender</h2>'+table(['Format','Gender','Matches',left+' wins',right+' wins','Other'],format_rows,caption=left+' versus '+right+' results by format and gender')+'</section>'
        pair_body+='<section class="panel"><h2>Recent recorded matches</h2>'+match_table(recent,mp,25)+'</section><p class="note">Wins count the match winner recorded in the source. Draws, ties and no-results are grouped as Other; abandoned matches without an outcome remain visible.</p><p>'+a('/head-to-head/','Browse every international head-to-head')+' · '+a(gp['teams'][left],left)+' · '+a(gp['teams'][right],right)+'</p>'
        page(path,left+' vs '+right+' head-to-head records',f'{left} vs {right} international cricket head-to-head results by format, gender, wins and scorecards.',pair_body,'CollectionPage')
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

def build_collections(people,matches,pp,mp,gp,groups,careers,arc,hist,editorial=None,all_cards=None):
    ranked=sorted(people.values(),key=lambda p:aggregate(p['career']).get('runs') or 0,reverse=True)
    latest=matches[:8]
    body=homepage_hero(len(people),len(matches))
    body+='<div class="stats">'+''.join(f'<div><strong>{num(n)}</strong><span>{label}</span></div>' for n,label in [(len(people),'Player profiles'),(len(matches),'Match records'),(len(groups['teams']),'National teams'),('3','Formats covered')])+'</div>'
    body+=homepage_insights(matches,mp,people,gp)
    body+='<div class="section-heading"><h2>Start with a question</h2></div><div class="grid three">'+''.join(f'<a class="feature-card" href="{path}"><span>{category}</span><h3>{question}</h3><p>{desc}</p></a>' for path,category,question,desc in [('/records/men/odi/most-runs/','CAREER RECORDS','Who leads the run charts?','Explore qualified records across all three formats.'),('/compare/','PLAYER COMPARISON','How do their careers compare?','Choose a format and compare like-for-like figures.'),('/teams/','TEAMS & GROUNDS','Where does a team win?','Discover results, venues and international rivalries.')])+'</div><div class="section-heading"><h2>Recent recorded results</h2>'+a('/matches/','All matches →')+'</div>'+match_table(latest,mp)
    body+='<div class="section-heading"><h2>Explore the major archives</h2></div><div class="grid three">'+''.join(f'<a class="feature-card" href="{path}"><span>{category}</span><h3>{title}</h3><p>{desc}</p></a>' for path,category,title,desc in [('/world-cup/','WORLD CUP','World Cup records','Tournament results, scorecards and player pathways.'),('/head-to-head/','RIVALRIES','Head-to-head records','Compare every full-member international rivalry.'),('/records/best-innings/','PERFORMANCES','Best innings','Highest scores and bowling figures from scorecards.'),('/milestones/','MILESTONES','Player milestones','Centuries, fifties and five-wicket hauls by year.'),('/venue-records/','VENUES','Venue records','Ground volume, formats and highest team totals.')])+'</div>'
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
            listing+=f'<a class="feature-card entity-index-card" data-entity-card="{esc(name)}" href="{gp[kind][name]}"><h2>{esc(name)}</h2><p>{len(ms):,} recorded matches</p><small>{esc(ms[-1]["date"])} – {esc(ms[0]["date"])}</small></a>'
            title1=name+(' cricket results & records' if kind=='teams' else ' match records')
            body=heading(name,f'{len(ms):,} recorded matches · {ms[-1]["date"]} – {ms[0]["date"]}',kind.upper())+actions()+entity_visuals(kind,name,ms)
            if kind=='teams':
                counts=Counter('Won' if m['outcome'].get('winner')==name else 'Lost' if m['outcome'].get('winner') else 'Draw / tie / no result' for m in ms)
                body+='<div class="stats">'+''.join(f'<div><strong>{n:,}</strong><span>{esc(label)}</span></div>' for label,n in counts.items())+'</div><p class="note">Men’s and women’s results are combined in this overview. Use the linked match explorer to select a gender and format.</p>'
                rivals=defaultdict(Counter)
                for m in ms:
                    opp=next(t for t in m['teams'] if t!=name);rivals[opp]['played']+=1;rivals[opp]['wins']+=int(m['outcome'].get('winner')==name)
                body+='<section class="panel"><h2>Head-to-head results</h2>'+table(['Opponent','Matches','Wins'],[[a(gp['teams'][opp],opp),str(s['played']),str(s['wins'])] for opp,s in sorted(rivals.items(),key=lambda x:x[1]['played'],reverse=True)])+'</section>'
                squad=[p for p in ranked if name in p['teams']]
                body+='<section class="panel"><h2>Explore players</h2><p class="note">Players linked to this team; career totals can include other representative teams.</p>'+table(['Player','Gender','Career runs','Career wickets'],[[a(pp[p['id']],p['name']),p['gender'],num(aggregate(p['career']).get('runs')),num(aggregate(p['career']).get('wickets'))] for p in squad[:30]])+'</section>'
            body+='<section class="panel"><h2>Recorded matches by format</h2>'+table(['Format','Men','Women'],[[fmt,str(sum(m['format']==fmt and m['gender']=='Men' for m in ms)),str(sum(m['format']==fmt and m['gender']=='Women' for m in ms))] for fmt in ['Test','ODI','T20I']])+'</section><h2>Recent recorded matches</h2>'+entity_filter_form(kind,name,ms)+'<div id="entity-results" aria-live="polite">'+match_table(ms,mp,50)+'</div>'
            from urllib.parse import urlencode
            query={'team':name} if kind=='teams' else {'q':name}
            body+='<p>'+a('/matches/?'+urlencode(query),'Search all matching matches →')+'</p>'
            page(gp[kind][name],title1,f'{name}: international cricket results, format breakdowns and linked scorecards.',body,'CollectionPage')
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
                body=heading(f'{gender} {fmt}: {label}',qualification,'CAREER LEADERBOARD')+scope_nav+actions()+f'<form class="filters" data-records="{feed}" data-field="{field}" data-minimum-field="{minimum_field}" data-lower="{str(lower).lower()}"><label>Minimum {minimum_label}<input name="minimum" type="number" min="0" value="{minimum}"></label><label>Player or team<input name="q"></label><button class="primary">Apply</button><button type="reset">Reset</button></form><div id="record-results" aria-live="polite">'+table(['Rank','Player','Teams',label,'Matches','Bowling innings' if bowling_record else 'Batting innings','Runs conceded' if bowling_record else 'Runs','Wickets'],rows)+'</div><p class="note">Tied figures share a competition rank. The initial table lists up to 100 qualifying records; filters browse all careers in this format. Snapshot '+careers['meta']['checked_at'][:10]+'.</p>'
                if qualified:
                    top=qualified[0];body+='<section class="panel"><h2>What this table shows</h2><p>'+esc(top['name'])+' leads this snapshot. '+esc(label)+': '+num(top[field])+'. '+esc(qualification)+'. Changing the qualification can change the leader.</p><p>'+a('/methodology/','Definitions and coverage')+'</p></section>'
                page(path,f'{gender} {fmt} {label.lower()} records',f'{label} in {gender.lower()} {fmt} cricket. {qualification}. Career leaderboard with ties and player profiles.',body,'CollectionPage')
            records_body+='</div></section>'
    page('/records/','International cricket records','Test, ODI and T20I batting and bowling career records for men and women, with transparent qualification rules.',records_body,'CollectionPage')
    # Flexible comparisons use only the two selected summary files.
    choices=''.join(f'<option value="{pp[p["id"]]}">{esc(p["name"])} · {p["gender"]}</option>' for p in ranked[:80])
    compare=heading('Compare cricket careers','Search for two players and choose a format. Career records are compared independently of archive coverage.')+actions()+f'<form id="compare-form" class="filters"><label>Find another player<input id="compare-search" placeholder="Search all players"></label><label>First player<select name="a">{choices}</select></label><label>Second player<select name="b">{choices}</select></label>'+options('format',['Test','ODI','T20I'])+'<label>Data scope<select name="basis"><option value="career">Career records</option><option value="archive">Available archive</option></select></label><label>From year (archive)<input type="number" name="from" min="1877" max="2100"></label><label>To year (archive)<input type="number" name="to" min="1877" max="2100"></label><label>Opponent (archive)<input name="opponent" placeholder="e.g. Australia"></label><label>Venue setting (archive)<select name="setting"><option value="">All</option><option>Home</option><option>Away</option><option>Neutral</option><option>Unknown</option></select></label><label>Recent batting innings (archive)<select name="recent"><option value="">All</option><option>10</option><option>20</option><option>50</option></select></label><label>Minimum batting innings<input type="number" name="minimum" min="0" value="0"></label><button class="primary">Compare</button></form><div id="compare-result" aria-live="polite"><p>Select two players to compare their career records.</p></div>'
    if not editorial: compare+='<section class="panel"><h2>Featured comparisons</h2>'
    for left,right in [('Virat Kohli','Rohit Sharma'),('Sachin Tendulkar','Don Bradman'),('Joe Root','Steve Smith'),('Mithali Raj','Meg Lanning'),('Jasprit Bumrah','James Anderson')]:
        p1=next((p for p in ranked if p['name']==left),None);p2=next((p for p in ranked if p['name']==right),None)
        if not p1 or not p2:continue
        path='/compare/'+slug(left)+'-vs-'+slug(right)+'/'
        if not editorial: compare+='<p>'+a(path,left+' vs '+right)+'</p>'
        content=heading(left+' vs '+right,'Career comparison by format. Different eras and sample sizes need context.','PLAYER COMPARISON')+actions()
        for fmt in ['Test','ODI','T20I']:
            if fmt not in p1['career'] and fmt not in p2['career']:continue
            s1=p1['career'].get(fmt,{});s2=p2['career'].get(fmt,{})
            content+='<section class="panel"><h2>'+fmt+'</h2>'+table([left,'Metric',right],[[num(s1.get(k)),label,num(s2.get(k))] for k,label in [('matches','Matches'),('innings','Innings'),('runs','Runs'),('avg','Batting average'),('sr','Strike rate'),('hundreds','Centuries'),('fifties','Fifties'),('fours','Fours'),('sixes','Sixes'),('balls','Balls faced'),('wickets','Wickets'),('five_w','Five-wicket innings'),('bowlSr','Bowling strike rate'),('bowlAvg','Bowling average'),('econ','Economy')]])+'</section>'
        content+='<p>'+a(pp[p1['id']],left+' profile')+' · '+a(pp[p2['id']],right+' profile')+' · '+a('/compare/','Choose other players')+'</p>'
        page(path,left+' vs '+right+' stats comparison','Compare '+left+' and '+right+' across Test, ODI and T20I career batting and bowling statistics.',content)
    if editorial: compare += '<section class="panel"><h2>Featured comparisons</h2>'+editorial['comparison_cards']+'</section>'
    else: compare+='</section>'
    page('/compare/','Compare cricket players','Compare international cricketers by format, career runs, averages, centuries and wickets.',compare)
    entity_index=[{'name':name,'url':url,'kind':kind} for kind,g in gp.items() for name,url in g.items()];dump('/data/entity-index.json',entity_index)
    page('/studio/','International cricket content studio','Create and export publication-ready cricket visuals from verified career, match and innings data.',studio_markup(a),'SoftwareApplication',{'applicationCategory':'DesignApplication'})
    page('/embed/','Cricket Wicket player card','An embeddable international cricket career summary.','<div id="embed-result" aria-live="polite">Loading career card…</div>',noindex=True)
    page('/search/','Search cricket statistics','Find cricket players, teams, series and grounds.',heading('Find your next cricket answer','Search players, teams, series and grounds.')+'<form id="search-form" class="hero-search"><label>Search<input name="q" required></label><button class="primary">Search</button></form><div id="search-results" aria-live="polite"></div>',noindex=True)
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
