"""Build Cricket Wicket's searchable, pre-rendered static publication."""
from __future__ import annotations
import argparse, hashlib, html, json, math, re, shutil, unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / '_site'
BASE = 'https://cricket.rkjat.in'
TODAY = date.today().isoformat()
PAGES = {}
PREVIOUS = {}
ASSET_VERSION = hashlib.sha256(b''.join(p.read_bytes() for p in sorted((ROOT/'web').glob('*')) if p.is_file())).hexdigest()[:10]
ALIASES = {'SR Tendulkar':'Sachin Tendulkar','V Kohli':'Virat Kohli','RG Sharma':'Rohit Sharma','JJ Bumrah':'Jasprit Bumrah','DG Bradman':'Don Bradman','M Muralitharan':'Muttiah Muralitharan','M Muralidaran':'Muttiah Muralitharan','SK Warne':'Shane Warne','RT Ponting':'Ricky Ponting','KC Sangakkara':'Kumar Sangakkara','DPMD Jayawardene':'Mahela Jayawardene','JH Kallis':'Jacques Kallis','BC Lara':'Brian Lara','SM Gavaskar':'Sunil Gavaskar','R Dravid':'Rahul Dravid','A Kumble':'Anil Kumble','R Ashwin':'Ravichandran Ashwin','RA Jadeja':'Ravindra Jadeja','SC Ganguly':'Sourav Ganguly','V Sehwag':'Virender Sehwag','SS Mandhana':'Smriti Mandhana','H Kaur':'Harmanpreet Kaur','M Raj':'Mithali Raj','J Goswami':'Jhulan Goswami','EA Perry':'Ellyse Perry','MM Lanning':'Meg Lanning','JE Root':'Joe Root','SPD Smith':'Steve Smith','KS Williamson':'Kane Williamson','JM Anderson':'James Anderson','DA Warner':'David Warner','AC Gilchrist':'Adam Gilchrist','ST Jayasuriya':'Sanath Jayasuriya','KL Rahul':'KL Rahul','RR Pant':'Rishabh Pant','HH Pandya':'Hardik Pandya','AC Kerr':'Amelia Kerr','SCJ Broad':'Stuart Broad'}
# Cricket host territories, used only for these unambiguous city labels.
HOST_CITIES = {}
for country, cities in {'India':'Mumbai|Chennai|Delhi|New Delhi|Kolkata|Bengaluru|Bangalore|Hyderabad|Ahmedabad|Pune|Nagpur|Mohali|Dharamsala|Ranchi|Rajkot|Indore|Lucknow|Kanpur|Visakhapatnam|Cuttack|Guwahati|Thiruvananthapuram|Raipur', 'Australia':'Sydney|Melbourne|Adelaide|Perth|Brisbane|Hobart|Canberra|Cairns|Darwin', 'England':'London|Manchester|Birmingham|Nottingham|Leeds|Southampton|Chester-le-Street|Cardiff|Bristol|Taunton|Worcester|Leicester|Derby|Hove|Chelmsford', 'New Zealand':'Auckland|Wellington|Christchurch|Hamilton|Dunedin|Napier|Mount Maunganui|Nelson|Queenstown', 'South Africa':'Cape Town|Johannesburg|Durban|Centurion|Pretoria|Gqeberha|Port Elizabeth|Paarl|Bloemfontein|Potchefstroom|East London|Kimberley', 'Pakistan':'Lahore|Karachi|Rawalpindi|Multan|Faisalabad', 'Sri Lanka':'Colombo|Galle|Kandy|Dambulla|Pallekele|Hambantota', 'Bangladesh':'Dhaka|Mirpur|Chattogram|Chittagong|Sylhet', 'Zimbabwe':'Harare|Bulawayo', 'United Arab Emirates':'Dubai|Sharjah|Abu Dhabi', 'Ireland':'Dublin|Belfast|Bready|Malahide', 'West Indies':'Bridgetown|Kingston|Gros Islet|Port of Spain|Providence|Basseterre|St George\'s|North Sound|Roseau', 'Namibia':'Windhoek', 'Netherlands':'Amstelveen|Rotterdam|The Hague', 'Scotland':'Edinburgh|Aberdeen|Glasgow', 'Nepal':'Kirtipur|Kathmandu', 'Oman':'Al Amerat|Muscat'}.items():
    HOST_CITIES.update({city:country for city in cities.split('|')})

def read(path): return json.loads((ROOT / path).read_text(encoding='utf-8'))
def esc(v): return html.escape(str(v if v is not None else ''), quote=True)
def num(v): return '—' if v is None else f'{v:,}' if isinstance(v, int) else str(v)
def slug(v): return re.sub(r'[^a-z0-9]+','-',unicodedata.normalize('NFKD', str(v)).encode('ascii','ignore').decode().lower()).strip('-') or 'unknown'
def fullname(p): return ALIASES.get(p['name'],p['name'])
def dump(path, value):
    target=OUT/path.lstrip('/');target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(value,separators=(',',':'),ensure_ascii=False),encoding='utf-8')
def table(headings, rows, ident='', caption=''):
    return f'<div class="table-wrap"><table {f"id={esc(ident)}" if ident else ""}><caption>{esc(caption)}</caption><thead><tr>'+''.join(f'<th scope="col">{esc(h)}</th>' for h in headings)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<{ "th scope=\"row\"" if i==0 else "td"}>{v}</{"th" if i==0 else "td"}>' for i,v in enumerate(row))+'</tr>' for row in rows)+'</tbody></table></div>'
def a(path,label): return f'<a href="{esc(path)}">{esc(label)}</a>'
def pill(s): return f'<span class="pill">{esc(s)}</span>'
def ratios(s):
    s=dict(s)
    for key,top,bottom,factor in [('avg','runs','outs',1),('sr','runs','balls',100),('bowlAvg','conceded','wickets',1),('econ','conceded','legal',6)]:
        s[key]=round(s[top]/s[bottom]*factor,2) if s.get(top) is not None and s.get(bottom,0) and s[bottom]>0 else None
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
    canonical=BASE+path
    section=path.strip('/').split('/')[0]
    if len(path.strip('/').split('/'))>1:
        body='<nav class="breadcrumbs" aria-label="Breadcrumb">'+a('/','Home')+' / '+a('/'+section+'/',section.title())+' / <span>'+esc(title)+'</span></nav>'+body
    schema={'@context':'https://schema.org','@type':kind,'name':title,'description':description,'url':canonical,'isPartOf':{'@type':'WebSite','name':'Cricket Wicket','url':BASE+'/'}}
    if extra:schema.update(extra)
    ld=json.dumps(schema,ensure_ascii=False).replace('<','\\u003c')
    nav=[('/matches/','Matches'),('/players/','Players'),('/teams/','Teams'),('/records/','Records'),('/compare/','Compare'),('/series/','Series')]
    document=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} | Cricket Wicket</title><meta name="description" content="{esc(description)}"><link rel="canonical" href="{canonical}"><meta name="robots" content="{'noindex,follow' if noindex else 'index,follow,max-image-preview:large'}"><meta name="theme-color" content="#10233f"><meta property="og:type" content="website"><meta property="og:title" content="{esc(title)} | Cricket Wicket"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{canonical}"><meta property="og:site_name" content="Cricket Wicket"><meta property="og:image" content="{BASE}/apple-touch-icon.png"><meta name="twitter:card" content="summary"><link rel="icon" href="/favicon.svg"><link rel="apple-touch-icon" href="/apple-touch-icon.png"><link rel="manifest" href="/site.webmanifest"><link rel="stylesheet" href="/assets/wicket.css?v={ASSET_VERSION}"><script src="/assets/wicket.js?v={ASSET_VERSION}" defer></script><script type="application/ld+json">{ld}</script></head><body><a class="skip" href="#main">Skip to statistics</a><div class="topline"><div class="wrap">THE GAME IN NUMBERS <span>Tests · ODIs · T20Is · Men & women</span></div></div><header><div class="wrap header"><a class="brand" href="/"><img src="/logo.svg" width="36" height="36" alt="">CRICKET WICKET<span>.</span></a><button id="menu" aria-label="Open navigation" aria-expanded="false" aria-controls="nav">☰</button><nav id="nav">{''.join(f'<a href="{url}" '+('aria-current="page"' if path.startswith(url) else '')+f'>{name}</a>' for url,name in nav)}</nav><button id="theme" aria-label="Toggle dark theme" aria-pressed="false">◐</button><a class="search-link" href="/search/">Search</a></div></header><main id="main" class="wrap">{body}</main><footer><div class="wrap"><strong>CRICKET WICKET</strong><p>International cricket careers, match records and analysis.</p><div class="footer-links">{a('/methodology/','Coverage & methodology')}{a('/insights/','Statistical insights')}{a('/saved/','Saved research')}{a('/corrections/','Report a correction')}{a('/overview/','India archive')}{a('https://crickrida.rkjat.in','IPL on Crickrida')}</div><p class="muted">Ball-by-ball data: <a href="https://cricsheet.org/">Cricsheet</a>. Independent publication. Historical snapshots; not a live-score service.</p></div></footer><div id="toast" role="status" aria-live="polite"></div></body></html>'''
    target=OUT/path.lstrip('/')/'index.html';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(document,encoding='utf-8')
    if not noindex:PAGES[path]={'title':title,'bytes':len(document.encode()),'sha256':hashlib.sha256(document.encode()).hexdigest(),'lastmod':TODAY}
    if path in PAGES and PREVIOUS.get(path,{}).get('sha256')==PAGES[path]['sha256']:PAGES[path]['lastmod']=PREVIOUS[path].get('lastmod',TODAY)
def heading(title,subtitle='',eyebrow='INTERNATIONAL CRICKET'):
    return f'<section class="page-head"><div class="eyebrow">{esc(eyebrow)}</div><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></section>'
def actions():return '<div class="actions"><button data-save>Save page</button><button data-share>Share link</button><button data-csv>Download table CSV</button></div>'
def match_table(matches,paths,limit=40):
    return table(['Date','Match','Format','Result','Coverage'],[[esc(m['date']),a(paths[m['id']],' v '.join(m['teams'])),esc(m['format']+' · '+m['gender']),esc(result(m)),pill('Result only' if m.get('coverage')=='result-only' else 'Scorecard')] for m in matches[:limit]],caption='International match results')
def stats_table(p):
    career=p.get('career',{})
    groups=[('Batting career',['matches','innings','runs','avg','sr','highest_display','notouts','hundreds','fifties','ducks','fours','sixes','balls'],['Matches','Innings','Runs','Average','SR','Highest','Not outs','100s','50s','Ducks','4s','6s','Balls faced']),('Bowling career',['matches','bowling_innings','legal','maidens','conceded','wickets','bowlAvg','econ','bowlSr','best_bowling','best_match','four_w','five_w','ten_w'],['Matches','Innings','Legal balls','Maidens','Runs conceded','Wickets','Average','Economy','Strike rate','Best innings','Best match','4 wickets','5 wickets','10 wickets']),('Fielding career',['matches','fielding_innings','catches','stumpings','dismissals','keeper_catches','fielder_catches','dismissals_per_innings','most_dismissals'],['Matches','Innings','Catches','Stumpings','Dismissals','Keeper catches','Fielder catches','Dismissals / innings','Most dismissals'])]
    output=''
    for title,keys,labels in groups:
        output+='<h3>'+title+'</h3>'+table(['Format']+labels,[[esc(fmt)]+[esc(num(stats.get(k))) for k in keys] for fmt,stats in career.items()],caption=title+' records by format')
    return output

def options(name,values,label=None):return f'<label>{esc(label or name.title())}<select name="{name}"><option value="">All</option>'+''.join(f'<option value="{esc(v)}">{esc(v)}</option>' for v in values)+'</select></label>'

def main():
    global PREVIOUS
    OUT.mkdir(exist_ok=True)
    if (OUT/'build-manifest.json').exists():
        PREVIOUS=json.loads((OUT/'build-manifest.json').read_text(encoding='utf-8')).get('indexable',{})
    arc=read('data/international.json');careers=read('data/careers.json');hist=read('data/historical_matches.json')
    people={p['id']:{**p,'career':{}} for p in arc['players']}
    for p in careers['players']:
        prior=people.setdefault(p['id'],{**p,'formats':{}});prior['career']=p['formats'];prior['name']=fullname(prior);prior['first']=p['first'];prior['last']=p['last']
    for p in people.values():p['name']=fullname(p)
    matches=sorted(arc['matches']+hist['matches'],key=lambda m:(m['date'],m['id']),reverse=True)
    names=Counter(slug(p['name']) for p in people.values())
    match_labels={m['id']:' v '.join(m['teams'])+' '+m['date']+' '+m['gender']+' '+m['format'] for m in matches}
    duplicate_labels=Counter(match_labels.values())
    match_labels={mid:title+(' · '+mid if duplicate_labels[title]>1 else '') for mid,title in match_labels.items()}
    pp={pid:'/players/'+slug(p['name'])+('-'+pid if names[slug(p['name'])]>1 else '')+'/' for pid,p in people.items()}
    mp={m['id']:'/matches/'+slug('-'.join(m['teams']))+'-'+m['date']+'-'+m['id']+'/' for m in matches}
    groups={kind:defaultdict(list) for kind in ['teams','grounds','series']}
    appearances=defaultdict(list);innings=defaultdict(list)
    for m in matches:
        for team in m['teams']:groups['teams'][team].append(m)
        if m['venue']:groups['grounds'][m['venue']].append(m)
        if m['event']:groups['series'][m['event']].append(m)
        for pid in m.get('player_ids',[]):appearances[pid].append({'match':m['id'],'date':m['date'],'format':m['format'],'teams':m['teams'],'venue':m['venue'],'result':result(m),'url':mp[m['id']]})
    gp={kind:{name:f'/{kind}/{slug(name)}-{hashlib.sha1(name.encode()).hexdigest()[:6]}/' for name in g} for kind,g in groups.items()}
    # Keep the old India hub and its dependencies; the new publication uses none of its global payloads.
    for folder in ['overview','official','about','coverage','batting','bowling','fielding','h2h','formats','tournaments','vendor','images']:
        shutil.copytree(ROOT/folder,OUT/folder,dirs_exist_ok=True)
    for file in ['app.js','styles.css','professional.css','enhancements.js','stats.json','official_records.json','player_images.json','logo.svg','favicon.svg','favicon-16.png','favicon-32.png','apple-touch-icon.png','site.webmanifest','404.html','CNAME']:
        shutil.copy2(ROOT/file,OUT/file)
    (OUT/'.nojekyll').touch()
    shutil.copytree(ROOT/'web',OUT/'assets',dirs_exist_ok=True)
    print('Building scorecards and player analysis...',flush=True)
    for file in sorted((ROOT/'data/scorecards').glob('*.json')):
        cards=json.loads(file.read_text(encoding='utf-8'))
        for mid,card in cards.items():
            m=card['match'];body=heading(' v '.join(m['teams']),f'{m["date"]} · {m["format"]} · {m["gender"]} · {m["venue"]}','MATCH SCORECARD')+f'<div class="result-banner">{esc(result(m))}</div>'+actions()
            body+='<p>'+ ' · '.join(a(gp['teams'][t],t) for t in m['teams'])+' · '+a(gp['grounds'][m['venue']],m['venue'])+'</p>'
            if m['event']:body+='<p>'+a(gp['series'][m['event']],m['event'])+'</p>'
            for index,inn in enumerate(card['innings'],1):
                body+=f'<section class="panel"><h2>{esc(inn["team"])} · {inn["runs"]}/{inn["wickets"]}{"d" if inn.get("declared") else ""} <small>Innings {index}{" · Super over" if inn.get("super_over") else ""}</small></h2>'
                body+=table(['Batter','Dismissal','R','B','4s','6s','SR'],[[a(pp[b['id']],people[b['id']]['name']),esc(b['dismissal']),str(b['runs'])+('' if b['out'] else '*'),str(b['balls']),str(b['fours']),str(b['sixes']),str(round(b['runs']/b['balls']*100,2)) if b['balls'] else '—'] for b in inn['batting']],caption='Batting scorecard')
                body+=f'<p>Extras {inn["extras"]} · {inn["balls"]//6}.{inn["balls"]%6} overs</p>'
                body+=table(['Bowler','Overs','Runs','Wickets','Economy'],[[a(pp[b['id']],people[b['id']]['name']),f'{b["balls"]//6}.{b["balls"]%6}',str(b['runs']),str(b['wickets']),str(round(b['runs']/b['balls']*6,2)) if b['balls'] else '—'] for b in inn['bowling']],caption='Bowling scorecard')
                peak=max([o['runs'] for o in inn['overs']]+[1]);body+='<details><summary>Runs by over and fall of wickets</summary><div class="spark" role="img" aria-label="Runs by over">'+''.join(f'<i class="{"wicket" if o["wickets"] else ""}" style="height:{max(2,o["runs"] / peak*100)}%" title="Over {o["over"]}: {o["runs"]} runs; {o["wickets"]} wickets"></i>' for o in inn['overs'])+'</div>'+table(['Over','Runs','Wickets','Total'],[[str(o[k]) for k in ['over','runs','wickets','total']] for o in inn['overs']])+ '<p>'+esc(' · '.join(f'{w["runs"]}/{w["wicket"]} ({w["player"]})' for w in inn['fall']))+'</p></details></section>'
                if inn.get('super_over'):continue
                bowl={b['id']:b for b in inn['bowling']};bat={b['id']:(pos,b) for pos,b in enumerate(inn['batting'],1)}
                for pid in set(bowl)|set(bat):
                    pos,b=bat.get(pid,(None,{}));w=bowl.get(pid,{});team=inn['team'] if b else next(t for t in m['teams'] if t!=inn['team']);opp=next(t for t in m['teams'] if t!=team);host=HOST_CITIES.get(m.get('city',''))
                    setting='Unknown' if not host else 'Home' if team==host else 'Away' if opp==host else 'Neutral'
                    outcome='Won' if m['outcome'].get('winner')==team else 'Lost' if m['outcome'].get('winner') else 'Draw / tie / no result'
                    innings[pid].append({'date':m['date'],'match':mid,'url':mp[mid],'format':m['format'],'opponent':opp,'venue':m['venue'],'setting':setting,'result':outcome,'innings':index,'position':pos,'runs':b.get('runs'),'balls':b.get('balls'),'out':b.get('out'),'fours':b.get('fours'),'sixes':b.get('sixes'),'dismissal':b.get('dismissal'),'wickets':w.get('wickets'),'legal':w.get('balls'),'conceded':w.get('runs')})
            body+='<section class="panel"><h2>Playing XIs</h2><div class="grid two">'+''.join('<div><h3>'+esc(team)+'</h3>'+''.join('<p>'+a(pp[p['id']],people[p['id']]['name'])+'</p>' for p in squad)+'</div>' for team,squad in card['players'].items())+'</div></section><p class="note">Scorecard derived from Cricsheet deliveries. Super overs are shown separately and excluded from player analysis.</p>'
            page(mp[mid],match_labels[mid]+' scorecard',f'{result(m)}. {m["format"]} scorecard at {m["venue"]}, including batting, bowling and over-by-over totals.',body,'SportsEvent',{'startDate':m['date'],'sport':'Cricket','location':{'@type':'Place','name':m['venue']}})
    for m in hist['matches']:
        body=heading(' v '.join(m['teams']),f'{m["date"]} · {m["format"]} · {m["gender"]}','HISTORICAL RESULT')+f'<div class="result-banner">{esc(result(m))}</div><p>{a(gp["grounds"][m["venue"]],m["venue"])}</p>'+actions()+'<section class="panel"><h2>Match coverage</h2><p>This record contains the result. Local innings, lineups and ball data are unavailable.</p>'+ ' · '.join(a(gp['teams'][t],t) for t in m['teams'])+'</section>'
        page(mp[m['id']],match_labels[m['id']]+' result',f'{result(m)}. Historical {m["format"]} result at {m["venue"]}.',body,'SportsEvent',{'startDate':m['date'],'sport':'Cricket'})
    print('Building career profiles...',flush=True)
    for pid,p in people.items():
        career=p['career'];tot=aggregate(career);path=pp[pid]; rows=sorted(innings[pid],key=lambda r:r['date']);apps=appearances[pid]
        summary={'id':pid,'name':p['name'],'teams':p['teams'],'gender':p['gender'],'career':career,'url':path}
        summary['career']={fmt:{k:v for k,v in s.items() if k not in ('source','sources')} for fmt,s in career.items()}
        dump(path+'summary.json',summary);dump(path+'analytics.json',{'innings':rows,'appearances':apps,'note':'Available ball-data archive only. Super overs excluded. Unknown venue setting is not inferred.'})
        body=heading(p['name'],p['gender']+' · '+' / '.join(p['teams'])+' · '+p.get('first','')+'–'+p.get('last',''),'PLAYER CAREER')+actions()+'<div class="stats">'+''.join(f'<div><strong>{num(tot.get(k))}</strong><span>{label}</span></div>' for k,label in [('matches','Internationals'),('runs','Career runs'),('hundreds','Centuries'),('wickets','Wickets')])+'</div>'
        body+='<section class="panel"><h2>Career records by format</h2>'+stats_table(p)+f'<p class="note">Career snapshot: {careers["meta"]["checked_at"][:10]}. A dash means unavailable. Career totals are independent of the scorecard archive.</p></section>'
        if not career:body+='<p class="note">This archive identity has no matched career record. Do not treat its archive totals as a complete career.</p>'
        body+='<section class="panel" id="analysis" data-analytics="'+path+'analytics.json"><h2>Explore this player’s available match data</h2><p>'+str(len(apps))+' match appearances with local ball data. Filters below apply to this archive only.</p><button id="load-analysis" class="primary">Open statistical explorer</button><div id="analysis-controls" hidden></div><div id="analysis-results" aria-live="polite"></div></section>'
        yearly=defaultdict(Counter)
        for row in rows:
            y=yearly[row['date'][:4]]
            if row['runs'] is not None:y['runs']+=row['runs'];y['innings']+=1;y['outs']+=int(row['out']);y['balls']+=row['balls']
            if row['wickets'] is not None:y['wickets']+=row['wickets']
        if yearly:
            body+='<section class="panel"><h2>Year-by-year archive trend</h2><p class="note">Available deliveries, not complete career season totals.</p>'+table(['Year','Batting innings','Runs','Average','Wickets'],[[y,str(s['innings']),str(s['runs']),num(round(s['runs']/s['outs'],2) if s['outs'] else None),str(s['wickets'])] for y,s in sorted(yearly.items(),reverse=True)])+'</section>'
        body+='<section class="panel"><h2>Recent available appearances</h2>'+table(['Date','Match','Format','Result'],[[x['date'],a(x['url'],' v '.join(x['teams'])),x['format'],esc(x['result'])] for x in apps[:12]])+'</section><p>'+ ' · '.join(a(gp['teams'][t],t) for t in p['teams'] if t in gp['teams'])+'</p>'
        page(path,p['name']+(' · '+pid if names[slug(p['name'])]>1 else '')+' career stats & records',f'{p["name"]} international cricket statistics: Test, ODI and T20I runs, wickets, averages, career records and available match analysis.',body,'ProfilePage',{'mainEntity':{'@type':'Person','name':p['name'],'identifier':pid}})
    print('Building directories, records and research pages...',flush=True)
    build_collections(people,matches,pp,mp,gp,groups,careers,arc,hist)
    dump('/data/routes.json',{'players':pp,'matches':mp})
    dump('/data/player-index.json',[{'id':pid,'name':p['name'],'url':pp[pid],'teams':p['teams'],'gender':p['gender'],'formats':list(p['career'] or p['formats']),'byFormat':{fmt:{'runs':stats.get('runs'),'wickets':stats.get('wickets')} for fmt,stats in p['career'].items()},'runs':aggregate(p['career']).get('runs'),'wickets':aggregate(p['career']).get('wickets')} for pid,p in people.items()])
    dump('/data/match-index.json',[{'id':m['id'],'date':m['date'],'url':mp[m['id']],'teams':m['teams'],'format':m['format'],'gender':m['gender'],'venue':m['venue'],'event':m['event'],'result':result(m),'coverage':'Result only' if m.get('coverage') else 'Scorecard'} for m in matches])
    sitemap_files=[]
    for index,start in enumerate(range(0,len(PAGES),10000),1):
        paths=list(PAGES)[start:start+10000];name=f'sitemap-{index}.xml';sitemap_files.append(name)
        xml='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{BASE}{esc(path)}</loc><lastmod>{PAGES[path]["lastmod"]}</lastmod></url>' for path in paths)+'</urlset>'
        (OUT/name).write_text(xml,encoding='utf-8')
    (OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<sitemap><loc>{BASE}/{x}</loc></sitemap>' for x in sitemap_files)+'</sitemapindex>',encoding='utf-8')
    (OUT/'robots.txt').write_text(f'User-agent: *\nAllow: /\nDisallow: /saved/\nDisallow: /data/\nSitemap: {BASE}/sitemap.xml\n',encoding='utf-8')
    dump('/build-manifest.json',{'built_at':TODAY,'pages':len(PAGES),'players':len(people),'matches':len(matches),'largest_html_bytes':max(x['bytes'] for x in PAGES.values()),'indexable':PAGES})
    print(f'Built {len(PAGES)} indexable pages in {OUT}',flush=True)

def build_collections(people,matches,pp,mp,gp,groups,careers,arc,hist):
    ranked=sorted(people.values(),key=lambda p:aggregate(p['career']).get('runs') or 0,reverse=True)
    latest=matches[:8]
    body=heading('Cricket. In perspective.','Explore careers, compare players and follow the records that shape the game.','CRICKET WICKET · THE GAME IN NUMBERS')
    body+='<form class="hero-search" action="/search/"><label for="home-search">Find a player, team or ground</label><div><input id="home-search" name="q" placeholder="Try Virat Kohli, India or Lord’s" required><button class="primary">Explore →</button></div></form>'
    body+='<div class="stats">'+''.join(f'<div><strong>{num(n)}</strong><span>{label}</span></div>' for n,label in [(len(people),'Player profiles'),(len(matches),'Match records'),(len(groups['teams']),'Teams & representative XIs'),('1877','History starts')])+'</div>'
    body+='<div class="section-heading"><h2>Start with a question</h2></div><div class="grid three">'+''.join(f'<a class="feature-card" href="{path}"><span>{category}</span><h3>{question}</h3><p>{desc}</p></a>' for path,category,question,desc in [('/records/men/odi/most-runs/','CAREER RECORDS','Who leads the run charts?','Explore qualified records across all three formats.'),('/compare/','PLAYER COMPARISON','How do their careers compare?','Choose a format and compare like-for-like figures.'),('/teams/','TEAMS & GROUNDS','Where does a team win?','Discover results, venues and international rivalries.')])+'</div><div class="section-heading"><h2>Recent recorded results</h2>'+a('/matches/','All matches →')+'</div>'+match_table(latest,mp)
    body+='<div class="section-heading"><h2>The run makers</h2>'+a('/players/','Player directory →')+'</div>'+table(['Player','Team','Career runs'],[[a(pp[p['id']],p['name']),esc(' / '.join(p['teams'])),num(aggregate(p['career']).get('runs'))] for p in ranked[:8]])
    body+='<p class="note">Career data updated '+careers['meta']['checked_at'][:10]+'. Historical result-only matches are labeled. '+a('/methodology/','Understand coverage →')+'</p>'
    page('/','Cricket stats, player records & scorecards','Cricket Wicket: international cricket career statistics, player comparisons, match scorecards, team records and analysis.',body,'WebSite')
    # Crawlable pagination supplies all directory entries without requiring JavaScript.
    for kind,items,size,title in [('players',ranked,100,'Cricket player directory'),('matches',matches,100,'International match results')]:
        for i in range(0,len(items),size):
            number=i//size+1;path=f'/{kind}/' if number==1 else f'/{kind}/page/{number}/'
            body=heading(title+(' · Page '+str(number) if number>1 else ''),'Search the international archive. Player figures are career snapshots; match coverage is labeled.')
            body+=f'<form class="filters" data-directory="{kind}"><label>Search<input name="q" placeholder="Search {kind}"></label>'+options('gender',['Men','Women'])+options('format',['Test','ODI','T20I'])
            if kind=='matches':body+=options('team',sorted(groups['teams']))+options('year',sorted({m['date'][:4] for m in matches},reverse=True))
            body+='<button class="primary">Apply filters</button><button type="reset">Reset</button></form>'+actions()+'<div id="directory-results" aria-live="polite">'
            if kind=='players':body+=table(['Player','Team','Gender','Career runs','Career wickets'],[[a(pp[p['id']],p['name']),esc(' / '.join(p['teams'])),p['gender'],num(aggregate(p['career']).get('runs')),num(aggregate(p['career']).get('wickets'))] for p in items[i:i+size]])
            else:body+=match_table(items[i:i+size],mp,size)
            body+='</div><nav class="pagination" aria-label="Directory pages">'+(a(f'/{kind}/' if number==2 else f'/{kind}/page/{number-1}/','← Previous') if number>1 else '')+f'<span>Page {number} / {math.ceil(len(items)/size)}</span>'+(a(f'/{kind}/page/{number+1}/','Next →') if i+size<len(items) else '')+'</nav>'
            page(path,title+(' · Page '+str(number) if number>1 else ''),f'Browse {title.lower()}, page {number}. Search by name, format and gender.',body,'CollectionPage')
    for kind,g in groups.items():
        title={'teams':'International teams','grounds':'Cricket grounds','series':'International series'}[kind]
        listing=heading(title,'Browse international results and follow the links to individual matches.')+'<div class="grid three">'
        for name,ms in sorted(g.items(),key=lambda item:len(item[1]),reverse=True):
            listing+=f'<a class="feature-card" href="{gp[kind][name]}"><h2>{esc(name)}</h2><p>{len(ms):,} recorded matches</p><small>{esc(ms[-1]["date"])} – {esc(ms[0]["date"])}</small></a>'
            title1=name+(' cricket results & records' if kind=='teams' else ' match records')
            body=heading(name,f'{len(ms):,} recorded matches · {ms[-1]["date"]} – {ms[0]["date"]}',kind.upper())+actions()
            if kind=='teams':
                counts=Counter('Won' if m['outcome'].get('winner')==name else 'Lost' if m['outcome'].get('winner') else 'Draw / tie / no result' for m in ms)
                body+='<div class="stats">'+''.join(f'<div><strong>{n:,}</strong><span>{esc(label)}</span></div>' for label,n in counts.items())+'</div><p class="note">Men’s and women’s results are combined in this overview. Use the linked match explorer to select a gender and format.</p>'
                rivals=defaultdict(Counter)
                for m in ms:
                    opp=next(t for t in m['teams'] if t!=name);rivals[opp]['played']+=1;rivals[opp]['wins']+=int(m['outcome'].get('winner')==name)
                body+='<section class="panel"><h2>Head-to-head results</h2>'+table(['Opponent','Matches','Wins'],[[a(gp['teams'][opp],opp),str(s['played']),str(s['wins'])] for opp,s in sorted(rivals.items(),key=lambda x:x[1]['played'],reverse=True)])+'</section>'
                squad=[p for p in ranked if name in p['teams']]
                body+='<section class="panel"><h2>Explore players</h2><p class="note">Players linked to this team; career totals can include other representative teams.</p>'+table(['Player','Gender','Career runs','Career wickets'],[[a(pp[p['id']],p['name']),p['gender'],num(aggregate(p['career']).get('runs')),num(aggregate(p['career']).get('wickets'))] for p in squad[:30]])+'</section>'
            body+='<section class="panel"><h2>Recorded matches by format</h2>'+table(['Format','Men','Women'],[[fmt,str(sum(m['format']==fmt and m['gender']=='Men' for m in ms)),str(sum(m['format']==fmt and m['gender']=='Women' for m in ms))] for fmt in ['Test','ODI','T20I']])+'</section><h2>Recent recorded matches</h2>'+match_table(ms,mp,50)
            from urllib.parse import urlencode
            query={'team':name} if kind=='teams' else {'q':name}
            body+='<p>'+a('/matches/?'+urlencode(query),'Search all matching matches →')+'</p>'
            page(gp[kind][name],title1,f'{name}: international cricket results, format breakdowns and linked scorecards.',body,'CollectionPage')
        page('/'+kind+'/',title,'Explore '+title.lower()+' and their international match records.',listing+'</div>','CollectionPage')
    records_body=heading('Cricket records','Qualified career leaderboards. Choose a format and gender for meaningful comparisons.')
    metrics=[('most-runs','runs','Most runs',False,0),('most-wickets','wickets','Most wickets',False,0),('most-centuries','hundreds','Most centuries',False,0),('most-matches','matches','Most appearances',False,0),('best-batting-average','avg','Highest batting average',False,20),('best-bowling-average','bowlAvg','Lowest bowling average',True,20)]
    for gender in ['Men','Women']:
        for fmt in ['Test','ODI','T20I']:
            entries=[{'id':p['id'],'name':p['name'],'url':pp[p['id']],'teams':p['teams'],**{k:v for k,v in p['career'][fmt].items() if k not in ['source','sources','disciplines']}} for p in ranked if p['gender']==gender and fmt in p['career']]
            feed=f'/data/records-{gender.lower()}-{fmt.lower()}.json';dump(feed,entries)
            records_body+=f'<section class="panel"><h2>{gender} · {fmt}</h2><div class="link-grid">'
            for key,field,label,lower,minimum in metrics:
                path=f'/records/{gender.lower()}/{fmt.lower()}/{key}/';records_body+=a(path,label)
                qualified=[p for p in entries if p.get(field) is not None and (p.get('wickets',0) or 0)>=minimum] if field=='bowlAvg' else [p for p in entries if p.get(field) is not None and (p.get('innings',0) or 0)>=minimum]
                qualified.sort(key=lambda p:(p[field] if lower else -p[field],p['name']))
                qualification=f'Minimum {minimum} '+('wickets' if field=='bowlAvg' else 'batting innings') if minimum else 'All recorded careers; no minimum qualification'
                rows=[];previous=None;rank=0
                for i,p in enumerate(qualified[:100],1):
                    if p[field]!=previous:rank=i
                    previous=p[field];rows.append([str(rank),a(p['url'],p['name']),esc(' / '.join(p['teams'])),num(p[field]),num(p.get('matches')),num(p.get('innings')),num(p.get('runs')),num(p.get('wickets'))])
                body=heading(f'{gender} {fmt}: {label}',qualification,'CAREER LEADERBOARD')+actions()+f'<form class="filters" data-records="{feed}" data-field="{field}" data-lower="{str(lower).lower()}"><label>Minimum {"wickets" if field=="bowlAvg" else "batting innings"}<input name="minimum" type="number" min="0" value="{minimum}"></label><label>Player or team<input name="q"></label><button class="primary">Apply</button><button type="reset">Reset</button></form><div id="record-results" aria-live="polite">'+table(['Rank','Player','Teams',label,'Matches','Innings','Runs','Wickets'],rows)+'</div><p class="note">Tied figures share a competition rank. The initial table lists up to 100 qualifying records; filters browse all careers in this format. Snapshot '+careers['meta']['checked_at'][:10]+'.</p>'
                if qualified:
                    top=qualified[0];body+='<section class="panel"><h2>What this table shows</h2><p>'+esc(top['name'])+' leads this snapshot. '+esc(label)+': '+num(top[field])+'. '+esc(qualification)+'. Changing the qualification can change the leader.</p><p>'+a('/methodology/','Definitions and coverage')+'</p></section>'
                page(path,f'{gender} {fmt} {label.lower()} records',f'{label} in {gender.lower()} {fmt} cricket. {qualification}. Career leaderboard with ties and player profiles.',body,'CollectionPage')
            records_body+='</div></section>'
    page('/records/','International cricket records','Test, ODI and T20I batting and bowling career records for men and women, with transparent qualification rules.',records_body,'CollectionPage')
    # Flexible comparisons use only the two selected summary files.
    choices=''.join(f'<option value="{pp[p["id"]]}">{esc(p["name"])} · {p["gender"]}</option>' for p in ranked[:80])
    compare=heading('Compare cricket careers','Search for two players and choose a format. Career records are compared independently of archive coverage.')+actions()+f'<form id="compare-form" class="filters"><label>Find another player<input id="compare-search" placeholder="Search all players"></label><label>First player<select name="a">{choices}</select></label><label>Second player<select name="b">{choices}</select></label>'+options('format',['Test','ODI','T20I'])+'<label>Data scope<select name="basis"><option value="career">Career records</option><option value="archive">Available archive</option></select></label><label>From year (archive)<input type="number" name="from" min="1877" max="2100"></label><label>To year (archive)<input type="number" name="to" min="1877" max="2100"></label><label>Opponent (archive)<input name="opponent" placeholder="e.g. Australia"></label><label>Minimum batting innings<input type="number" name="minimum" min="0" value="0"></label><button class="primary">Compare</button></form><div id="compare-result" aria-live="polite"><p>Select two players to compare their career records.</p></div>'
    compare+='<section class="panel"><h2>Featured comparisons</h2>'
    for left,right in [('Virat Kohli','Rohit Sharma'),('Sachin Tendulkar','Don Bradman'),('Joe Root','Steve Smith'),('Mithali Raj','Meg Lanning'),('Jasprit Bumrah','James Anderson')]:
        p1=next((p for p in ranked if p['name']==left),None);p2=next((p for p in ranked if p['name']==right),None)
        if not p1 or not p2:continue
        path='/compare/'+slug(left)+'-vs-'+slug(right)+'/'
        compare+='<p>'+a(path,left+' vs '+right)+'</p>'
        content=heading(left+' vs '+right,'Career comparison by format. Different eras and sample sizes need context.','PLAYER COMPARISON')+actions()
        for fmt in ['Test','ODI','T20I']:
            if fmt not in p1['career'] and fmt not in p2['career']:continue
            s1=p1['career'].get(fmt,{});s2=p2['career'].get(fmt,{})
            content+='<section class="panel"><h2>'+fmt+'</h2>'+table([left,'Metric',right],[[num(s1.get(k)),label,num(s2.get(k))] for k,label in [('matches','Matches'),('innings','Innings'),('runs','Runs'),('avg','Batting average'),('sr','Strike rate'),('hundreds','Centuries'),('wickets','Wickets'),('bowlAvg','Bowling average'),('econ','Economy')]])+'</section>'
        content+='<p>'+a(pp[p1['id']],left+' profile')+' · '+a(pp[p2['id']],right+' profile')+' · '+a('/compare/','Choose other players')+'</p>'
        page(path,left+' vs '+right+' stats comparison','Compare '+left+' and '+right+' across Test, ODI and T20I career batting and bowling statistics.',content)
    page('/compare/','Compare cricket players','Compare international cricketers by format, career runs, averages, centuries and wickets.',compare+'</section>')
    entity_index=[{'name':name,'url':url,'kind':kind} for kind,g in gp.items() for name,url in g.items()];dump('/data/entity-index.json',entity_index)
    page('/embed/','Cricket Wicket player card','An embeddable international cricket career summary.','<div id="embed-result" aria-live="polite">Loading career card…</div>',noindex=True)
    page('/search/','Search cricket statistics','Find cricket players, teams, series and grounds.',heading('Find your next cricket answer','Search players, teams, series and grounds.')+'<form id="search-form" class="hero-search"><label>Search<input name="q" required></label><button class="primary">Search</button></form><div id="search-results" aria-live="polite"></div>',noindex=True)
    page('/saved/','Saved cricket research','Your saved cricket pages and filtered searches on this device.',heading('Your cricket notebook','Saved pages and searches stay in this browser on this device.')+'<button id="clear-saved">Clear saved pages</button><div id="saved-results"></div>',noindex=True)
    page('/corrections/','Report a cricket data correction','Prepare a precise correction with the player, match, metric and supporting evidence.',heading('Help improve the record','Create a correction report to share with the site owner. This form does not send your information automatically.')+'<form id="correction-form" class="panel"><label>Page URL<input name="url" type="url" required></label><label>What needs correcting?<textarea name="issue" required></textarea></label><label>Correct value and supporting evidence<textarea name="evidence" required></textarea></label><button class="primary">Download correction report</button></form><p class="note">Review the downloaded report before sharing it. No account or personal details are required.</p>')
    methods=heading('Data coverage & methodology','Clear definitions, dates and limits for every layer of the archive.')+'<div class="stats">'+''.join(f'<div><strong>{num(v)}</strong><span>{label}</span></div>' for v,label in [(careers['meta']['players'],'Career records'),(arc['meta']['matches'],'Ball-data scorecards'),(hist['meta']['added_matches'],'Additional results'),(careers['meta']['archive_players_without_career'],'Unmatched identities')])+'</div><section class="panel"><h2>Career records</h2><p>Complete imported tables across men’s and women’s Tests, ODIs and T20Is. Snapshot '+careers['meta']['checked_at'][:10]+'. A missing field is displayed as a dash, never inferred from a partial archive. Career and delivery-derived figures are never added together.</p><h2>Match and player analysis</h2><p>Ball-by-ball data is provided by <a href="https://cricsheet.org/">Cricsheet</a>. The explorer uses only available deliveries and excludes super overs. Matches without ball data do not contribute to batting, bowling, dismissal or yearly analysis.</p><h2>Venue setting</h2><p>Home, away and neutral are assigned only for recognized host cities using the cricket team’s host territory. Other locations remain Unknown. These categories describe the venue, not which team is named first.</p><h2>Statistical definitions</h2><p>Batting average = runs / dismissals. Strike rate = 100 × runs / balls faced. Bowling average = conceded runs / wickets. Economy = 6 × conceded runs / legal balls. Combined averages are recomputed from totals, not averaged across formats. No dismissals or no wickets produces a dash.</p><h2>Record qualifications</h2><p>Average leaderboards default to 20 batting innings or 20 bowling wickets. Ties share a rank. Results by team include men and women unless filtered. Historical results may lack innings totals, lineups and deliveries.</p><h2>Corrections and freshness</h2><p>Changes pass identity, count and scorecard checks before publication. '+a('/corrections/','Prepare a correction report')+'. This publication does not supply live scores, future fixtures or official rankings.</p></section>'
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
    page('/insights/','Cricket statistical insights','Original explanations of international cricket records, with linked tables and transparent methodology.',insights+'</div>','CollectionPage')
    # The previous international URLs remain valid; the script resolves query IDs.
    page('/international/','International cricket archive','Find international match records and player profiles.',heading('International cricket archive')+'<p>'+a('/matches/','Browse match records')+' · '+a('/players/','Browse player careers')+'</p><p id="legacy-status">Opening the requested record when an ID is supplied…</p>',noindex=True)

if __name__=='__main__': main()
