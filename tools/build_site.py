"""Build Crickrida's searchable, pre-rendered static publication."""
from __future__ import annotations
import argparse, hashlib, html, json, math, re, shutil, unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from cricket_scope import publication_data, FULL_MEMBERS, load_cards, complete_career_counts,career_scorecards
from home_visuals import homepage_hero, homepage_insights, archive_visuals, icons_rail, format_trio, records_grid
from on_this_day import publish_history, india_today
import cricket_charts as cw
from publication_assets import prepare_assets, social_image
from publication_pages import trust_pages
from portraits import load_portraits, portrait_figure
from profile_research import select_research_players, profile_research_section, opponent_pages, research_index
from editorial_research import build_editorial, entity_context
from studio_page import studio_markup
from data_health import coverage_page
from player_profile import player_seo, career_glance, career_tables, player_faq, player_person, primary_role
from profile_research import opposition_links
from profile_formats import profile_body
import league_panels as lp
import league_entities as le
import tool_pages as tp
from entity_formats import entity_switch, team_format_panel, ground_format_panel, series_format_panel, h2h_format_panel
from venues import canonicalise_matches
from compare_pages import PAIRS, find_player, compare_body, comparison_cards
from records_hub import CAREER_METRICS, INNINGS_RECORDS, MINIMUM_FIELD, MINIMUM_LABEL, CATEGORY_LABEL, innings_rows, team_rows, innings_record_table, career_table, records_table, records_index, headline_records
from player_questions import prepare_player_questions, question_page, featured_question_cards, player_question_directory, assert_clean_bundle
from entity_pages import (ground_masthead, ground_place, 
    team_totals, ground_totals, team_seo, ground_seo, team_intro, ground_intro,
    team_glance, ground_glance, team_faq, ground_faq,
    team_schema, ground_schema, h2h_path,
)
from world_cup import FAMILIES, merge_official, titles_leaderboard, timeline_table, official_record_rows, coverage_note, analysis_heading, analysis_lede
from official_public import load_team_records, load_innings_records, official_team_panel, official_innings_table, official_h2h
from broadcasts import load_broadcasts, watch_page
from tidy import tidy_copy
from arena import section_jump, match_centre, stats_band, leaders_race, result_cards, explore_bento
from t20wc_dashboard import dashboard_markup

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / '_site'
BASE = 'https://crickrida.com'
TODAY = india_today().isoformat()
PAGES = {}
PREVIOUS = {}
STUBS = set()  # redirect pages for retired URLs; never indexed, never pruned
COMPARE_CARDS = []  # curated comparison entries for the compare index
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
HERO_CAST = ('Virat Kohli','Rohit Sharma','Smriti Mandhana','Harmanpreet Kaur','MS Dhoni','Ellyse Perry','Sachin Tendulkar','Pat Cummins','Joe Root','Kane Williamson','Steve Smith')
GROUND_FACTS=json.loads((ROOT/'data/ground_facts.json').read_text(encoding='utf-8')).get('grounds',{}) if (ROOT/'data/ground_facts.json').exists() else {}
# Cricket host territories, used only for these unambiguous city labels.
HOST_CITIES = {}
for country, cities in {"India": "Mumbai|Chennai|Delhi|New Delhi|Kolkata|Bengaluru|Bangalore|Hyderabad|Ahmedabad|Pune|Nagpur|Mohali|Chandigarh|New Chandigarh|Dharamsala|Dharamshala|Ranchi|Rajkot|Indore|Lucknow|Kanpur|Visakhapatnam|Cuttack|Guwahati|Thiruvananthapuram|Raipur|Vadodara|Jaipur|Kochi|Gwalior|Jamshedpur|Margao|Faridabad|Kottayam|Vijayawada|Dehradun|Greater Noida|Mulapadu|Navi Mumbai|Surat|Tirunelveli|Bhubaneswar|Noida", "Australia": "Carrara|Kerrydale|Bowral|Bradman Oval|Sydney|Melbourne|Adelaide|Perth|Brisbane|Hobart|Canberra|Cairns|Darwin|Geelong|Townsville|Mackay|Coffs Harbour|Launceston|Alice Springs", "England": "County Ground, Hove|London|Manchester|Birmingham|Nottingham|Leeds|Southampton|Chester-le-Street|Cardiff|Bristol|Taunton|Worcester|Leicester|Derby|Hove|Chelmsford|Canterbury|Northampton|Scarborough|Cheltenham|Arundel|Beckenham|Loughborough|Wormsley|Durham", "New Zealand": "Auckland|Wellington|Christchurch|Hamilton|Dunedin|Napier|Mount Maunganui|Nelson|Queenstown|Whangarei|New Plymouth|Lincoln|Palmerston North|Tauranga|Invercargill|Rangiora", "South Africa": "Cape Town|Johannesburg|Durban|Centurion|Pretoria|Gqeberha|Port Elizabeth|Paarl|Bloemfontein|Potchefstroom|East London|Kimberley|Benoni|Pietermaritzburg|Stellenbosch|Oudtshoorn", "Pakistan": "Lahore|Karachi|Rawalpindi|Multan|Faisalabad|Peshawar|Gujranwala|Sheikhupura|Quetta|Sialkot|Sargodha|Abbottabad|Islamabad", "Sri Lanka": "Chilaw|Colombo|Galle|Kandy|Dambulla|Pallekele|Hambantota|Moratuwa|Khettarama|Katunayake|Kurunegala|Matara", "Bangladesh": "Rajshahi|Sheikh Kamal|Dhaka|Mirpur|Chattogram|Chittagong|Sylhet|Khulna|Fatullah|Bogra|Savar|Narayanganj", "Zimbabwe": "Harare|Bulawayo|Kwekwe|Mutare", "Afghanistan": "Kabul", "United Arab Emirates": "Dubai|Sharjah|Abu Dhabi|Ajman", "Ireland": "Louth|Dublin|Belfast|Bready|Malahide|Stormont|Clontarf|Comber|Waringstown|Londonderry", "West Indies": "Bridgetown|Kingston|Kingstown|Gros Islet|Port of Spain|Providence|Basseterre|North Sound|Roseau|Tarouba|Barbados|Guyana|Trinidad|Antigua|Jamaica|St Lucia|St Kitts|Grenada|Dominica|St Vincent|Arnos Vale|Georgetown|Castries|Coolidge|Cave Hill|St George's", "Namibia": "Windhoek", "Netherlands": "Amstelveen|Rotterdam|The Hague|Utrecht|Deventer|Voorburg|Schiedam", "Scotland": "Edinburgh|Aberdeen|Glasgow|Ayr|Dundee|Forfar", "Nepal": "Kirtipur|Kathmandu", "Oman": "Al Amerat|Al Amarat|Muscat", "United States of America": "Lauderhill|New York|Dallas|Grand Prairie|Morrisville|Houston|Pearland", "Canada": "Toronto|King City|Brampton", "Malaysia": "Kuala Lumpur|Bangi|Johor", "Kenya": "Nairobi|Mombasa", "Singapore": "Singapore", "Qatar": "Doha", "Hong Kong": "Hong Kong|Mong Kok", "Thailand": "Bangkok|Chiang Mai", "Papua New Guinea": "Port Moresby", "Uganda": "Entebbe|Kampala", "Rwanda": "Kigali|Kigali City", "Botswana": "Gaborone", "Nigeria": "Lagos|Abuja", "Ghana": "Accra", "Japan": "Sano", "Spain": "Almeria|Murcia|La Manga", "Italy": "Rome|Bologna", "Germany": "Krefeld", "Finland": "Kerava|Vantaa", "Czech Republic": "Prague", "Romania": "Ilfov County", "Bulgaria": "Sofia", "Malta": "Marsa", "Cyprus": "Episkopi", "Argentina": "Buenos Aires", "Indonesia": "Bali", "Vanuatu": "Port Vila", "Bhutan": "Gelephu", "Belgium": "Waterloo|Gent", "Denmark": "Brondby", "Portugal": "Albergaria", "Austria": "Seebarn|Vienna", "Jersey": "St Saviour|St Clement", "Guernsey": "St Peter Port|Castel", "Isle of Man": "Castletown", "Mexico": "Naucalpan", "Sweden": "Stockholm|Malmo", "Estonia": "Tallinn", "Serbia": "Belgrade", "Croatia": "Zagreb", "Hungary": "Budapest", "Greece": "Corfu", "Luxembourg": "Walferdange", "Slovenia": "Ljubljana", "Gibraltar": "Gibraltar", "Cayman Islands": "George Town", "Peru": "Lima", "Chile": "Santiago", "Brazil": "Sao Paulo|Brasilia", "Costa Rica": "San Jose", "Panama": "Panama City", "Belize": "Belize City", "Tanzania": "Dar es Salaam", "Mozambique": "Maputo", "Eswatini": "Mbabane", "Lesotho": "Maseru", "Malawi": "Blantyre|Lilongwe", "Zambia": "Lusaka", "Cameroon": "Yaounde", "Sierra Leone": "Freetown", "Gambia": "Banjul", "Mali": "Bamako", "Ivory Coast": "Abidjan", "Saudi Arabia": "Riyadh|Jeddah", "Bahrain": "Manama|Riffa", "Iran": "Tehran|Chabahar", "Uzbekistan": "Tashkent", "Mongolia": "Ulaanbaatar", "South Korea": "Incheon|Seoul", "China": "Guanggong|Guangzhou|Hangzhou", "Cambodia": "Phnom Penh", "Myanmar": "Yangon", "Philippines": "Manila", "Maldives": "Male", "Fiji": "Suva|Nadi", "Samoa": "Apia", "Cook Islands": "Rarotonga", "Timor-Leste": "Dili", "Suriname": "Paramaribo"}.items():
    for city in cities.split('|'):HOST_CITIES.setdefault(city,country)

REGION_HOSTS={'United Kingdom':'England','Wales':'England','Barbados':'West Indies','Jamaica':'West Indies','Trinidad and Tobago':'West Indies','Guyana':'West Indies','Saint Lucia':'West Indies','Antigua and Barbuda':'West Indies','St Kitts and Nevis':'West Indies','Dominica':'West Indies','Grenada':'West Indies','Saint Vincent and the Grenadines':'West Indies','UAE':'United Arab Emirates','USA':'United States of America'}

def host_country(m,venue_hosts=None):
    """Host country from the recorded city, the metadata, the same venue elsewhere, or the venue name."""
    host=HOST_CITIES.get(m.get('city') or '') or m.get('host_country')
    if not host and venue_hosts:host=venue_hosts.get(m.get('venue'))
    if not host:
        venue=m.get('venue') or ''
        for city,country in VENUE_KEYS:
            if city in venue:host=country;break
    return REGION_HOSTS.get(host,host)

VENUE_KEYS=sorted(((city,country) for city,country in HOST_CITIES.items() if len(city)>=5),key=lambda kv:-len(kv[0]))

def venue_host_map(matches):
    """Venue to host country when any match at that venue names its city."""
    votes=defaultdict(Counter)
    for m in matches:
        host=HOST_CITIES.get(m.get('city') or '') or m.get('host_country')
        if host and m.get('venue'):votes[m['venue']][host]+=1
    return {venue:counter.most_common(1)[0][0] for venue,counter in votes.items()}

def read(path): return json.loads((ROOT / path).read_text(encoding='utf-8'))
def esc(v): return html.escape(str(v if v is not None else ''), quote=True)
def num(v): return '-' if v is None else f'{v:,}' if isinstance(v, int) else f'{v:.2f}' if isinstance(v,float) else str(v)
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
TEXT_COLUMNS={'Player','Batter','Bowler','Team','Teams','Country','Gender','Format','Match','Result','Coverage','Dismissal','Opponent','Ground','Venue','Metric','Date','Year','First player','Second player','Champion','Runner-up','Semi-finalists','Host','Hosts','Final','Record','Holder','Detail','Span','Played','Won','Lost','Draw / tied','No result'}
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

def decimal_stat(value):return '-' if value is None else f'{value:.2f}'

def stat_value(s,key):
    v=s.get(key)
    if v is None:
        denominator={'avg':'outs','sr':'balls','bowlAvg':'wickets','bowlSr':'wickets','econ':'legal'}.get(key)
        if denominator and (s.get(denominator)==0 or (key in ('avg','sr') and 'innings' in s and not s['innings'] and s.get('runs') is None) or (key in ('bowlAvg','bowlSr','econ') and 'bowling_innings' in s and not s['bowling_innings'] and s.get('wickets') is None)):return '<span class="not-applicable" title="No applicable denominator">N/A</span>'
        return '<span class="missing" title="Not recorded in the verified source">-</span>'
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

def render_innings(inn,index,people,pp,squad=None):
    bpo=inn.get('balls_per_over',6)
    def overs(b):return esc(str(b['overs_display'])) if b.get('overs_display') not in (None,'None') else esc(str(b['overs'])) if isinstance(b.get('overs'),(int,float,str)) else ('-' if b.get('balls') is None else str(b['balls']//bpo)+'.'+str(b['balls']%bpo))
    total=score_text(inn);ov=overs_text(inn);rr=run_rate(inn)
    sub=' · '.join(part for part in [(ov+' overs') if ov else '', ('run rate '+f'{rr:.2f}') if rr is not None else '', 'all out' if inn.get('wickets')==10 else '', 'declared' if inn.get('declared') else ''] if part)
    body='<section id="innings-'+str(index)+'" class="panel innings-panel"><div class="innings-heading"><div><span class="eyebrow">INNINGS '+str(index)+(' · SUPER OVER' if inn.get('super_over') else '')+'</span><h2>'+esc(inn['team'])+'</h2>'+(f'<small>{esc(sub)}</small>' if sub else '')+'</div><strong class="innings-total">'+esc(total)+'</strong></div>'
    body+=table(['Batter','Dismissal','R','B','4s','6s','SR'],[[a(pp[b['id']],people[b['id']]['name']),esc(dismissal_text(b,people)),esc(num(b['runs']))+('' if b['out'] else '<span class="notout">*</span>'),num(b['balls']),num(b['fours']),num(b['sixes']),decimal_stat(b.get('sr') if b.get('sr') is not None else rate(b['runs'],b['balls'],100))] for b in inn['batting']],caption='Batting scorecard')
    wides=[b.get('wides') for b in inn['bowling']];noballs=[b.get('noballs') for b in inn['bowling']]
    detail=''
    if inn.get('extras') is not None and inn['bowling'] and all(v is not None for v in wides+noballs):
        w=sum(wides);nb=sum(noballs);other=inn['extras']-w-nb
        if other>=0:detail=f' <small>(w {w}, nb {nb}, b/lb {other})</small>'
    batted={b['id'] for b in inn['batting']}
    dnb=[p for p in (squad or []) if p.get('id') not in batted]
    body+='<div class="innings-summary"><span>Extras <strong>'+num(inn['extras'])+'</strong>'+detail+'</span><span>Total <strong>'+esc(total)+'</strong>'+(f' <small>({esc(ov)} ov)</small>' if ov else '')+'</span>'+(f'<span>Run rate <strong>{rr:.2f}</strong></span>' if rr is not None else '')+'</div>'
    if dnb and not inn.get('super_over'):body+='<p class="dnb">Did not bat: '+', '.join(a(pp[p['id']],people[p['id']]['name']) if p.get('id') in pp else esc(p.get('name','')) for p in dnb)+'</p>'
    if inn['fall']:body+='<p class="fow"><span class="fow-label">Fall of wickets</span>'+fall_text(inn)+'</p>'
    body+=table(['Bowler','O','M','R','W','Econ','WD','NB'],[[a(pp[b['id']],people[b['id']]['name']),overs(b),num(b.get('maidens')),num(b['runs']),num(b['wickets']),decimal_stat(b.get('econ') if b.get('econ') is not None else rate(b['runs'],b['balls'],bpo)),num(b.get('wides')),num(b.get('noballs'))] for b in inn['bowling']],caption='Bowling scorecard')
    if inn['fall']:body+=cw.partnerships(inn)
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
        text=o['winner']+' won'+(' by '+margin if margin else '')
        if o.get('method'):text+=' ('+str(o['method'])+' method)'
        return text
    if o.get('result')=='tie' and o.get('eliminator'):return 'Match tied · '+str(o['eliminator'])+' won the Super Over'
    return {'draw':'Match drawn','tie':'Match tied','no result':'No result'}.get(o.get('result'),'Result not recorded')
def overs_text(inn):
    """Overs bowled in an innings from recorded balls, or the historical display value."""
    if inn.get('overs_display') not in (None,'None',''):return str(inn['overs_display'])
    balls=inn.get('balls');bpo=inn.get('balls_per_over') or 6
    if not isinstance(balls,int) or balls<=0:return ''
    return str(balls//bpo)+('.'+str(balls%bpo) if balls%bpo else '')
def run_rate(inn):
    balls=inn.get('balls');bpo=inn.get('balls_per_over') or 6
    return rate(inn.get('runs'),balls,bpo) if isinstance(balls,int) and balls>0 else None
def score_text(inn):
    """240 for an all-out innings, 241/4 otherwise, with a declaration mark."""
    wk=inn.get('wickets')
    return str(inn['runs'])+('/'+str(wk) if wk is not None and wk<10 else '')+('d' if inn.get('declared') else '')
def fall_text(inn):
    """Standard fall-of-wickets notation: 1-30 (Batter, 4.2 ov)."""
    bpo=inn.get('balls_per_over') or 6
    parts=[]
    for w in sorted((w for w in inn.get('fall') or [] if w.get('runs') is not None and w.get('wicket') is not None),key=lambda w:(w['wicket'],w['runs'])):
        balls=w.get('balls');over=(str(balls//bpo)+'.'+str(balls%bpo)) if isinstance(balls,int) else (str(w['overs']) if w.get('overs') not in (None,'') else '')
        parts.append(f'<span><b>{w["wicket"]}-{w["runs"]}</b> ({esc(w.get("player") or "batter not recorded")}{(", "+over+" ov") if over else ""})</span>')
    return ''.join(parts)
def award_links(card,people,pp):
    names=[n for n in (card.get('awards') or []) if n]
    if not names:return ''
    by_name={}
    for squad in (card.get('players') or {}).values():
        for p in squad:
            if p.get('id') in pp:by_name.setdefault(p.get('name'),p['id'])
    out=[]
    for name in names:
        pid=by_name.get(name)
        out.append(a(pp[pid],people[pid]['name']) if pid else esc(name))
    return ', '.join(out)
def page(path,title,description,body,kind='WebPage',extra=None,noindex=False):
    body=tidy_copy(path,body)
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
    schema={'@context':'https://schema.org','@type':kind,'name':title,'description':description,'url':canonical,'isPartOf':{'@type':'WebSite','name':'Crickrida','url':BASE+'/'}}
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
    nav=[('/matches/','Matches'),('/players/','Players'),('/teams/','Teams'),('/records/','Records'),('/compare/','Compare'),('/tools/','Tools'),('/series/','Series'),('/where-to-watch/','Watch')]
    tool_paths={'/tools/','/studio/',*tp.TOOL_PAGES}
    tools_assets=(f'<link rel="stylesheet" href="/assets/tools.css?v={ASSET_VERSION}"><script src="/assets/lake.js?v={ASSET_VERSION}" defer></script><script src="/assets/{tp.TOOL_PAGES[path]}.js?v={ASSET_VERSION}" defer></script>' if path in tp.TOOL_PAGES else f'<link rel="stylesheet" href="/assets/tools.css?v={ASSET_VERSION}">' if path=='/tools/' else '')
    home_assets=(f'<link rel="stylesheet" href="/assets/home.css?v={ASSET_VERSION}"><script src="/assets/home.js?v={ASSET_VERSION}" defer></script>' if path=='/' else '')
    studio_assets=(f'<link rel="stylesheet" href="/assets/studio.css?v={ASSET_VERSION}"><script src="/assets/studio-core.js?v={ASSET_VERSION}" defer></script><script src="/assets/studio-images.js?v={ASSET_VERSION}" defer></script><script src="/assets/studio.js?v={ASSET_VERSION}" defer></script>' if path=='/studio/' else '')
    history_assets=(f'<link rel="stylesheet" href="/assets/on-this-day.css?v={ASSET_VERSION}"><script src="/assets/on-this-day.js?v={ASSET_VERSION}" defer></script>' if path=='/' or path.startswith('/on-this-day/') else '')
    t20wc_assets=(f'<link rel="stylesheet" href="/assets/t20wc-dashboard.css?v={ASSET_VERSION}"><script src="/assets/t20wc-dashboard.js?v={ASSET_VERSION}" defer></script>' if path=='/world-cup/mens-t20/dashboard/' else '')
    og_type='profile' if kind=='ProfilePage' else 'website'
    profile_assets=(f'<link rel="stylesheet" href="/assets/profile.css?v={ASSET_VERSION}">' if kind=='ProfilePage' or path.startswith(('/records/','/compare/')) or (path.startswith(('/teams/','/grounds/','/series/','/head-to-head/')) and path.count('/')>=3) else '')
    verification=('<meta name="google-site-verification" content="'+esc(SETTINGS['google_site_verification'])+'">') if SETTINGS.get('google_site_verification') else ''
    document=f'''<!doctype html><html lang="en" data-theme="dark"><head><meta charset="utf-8"><script>if(location.hostname==='cricket.rkjat.in')location.replace('https://crickrida.com'+location.pathname+location.search+location.hash)</script>{verification}<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} | Crickrida</title><meta name="description" content="{esc(description)}"><link rel="canonical" href="{canonical}"><meta name="robots" content="{'noindex,follow' if noindex else 'index,follow,max-image-preview:large'}"><meta name="theme-color" content="#0a0a0f"><script src="/assets/theme.js?v={ASSET_VERSION}"></script><meta property="og:type" content="{og_type}"><meta property="og:title" content="{esc(title)} | Crickrida"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{canonical}"><meta property="og:site_name" content="Crickrida"><meta property="og:image" content="{social}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{social}"><link rel="icon" href="/favicon.svg"><link rel="apple-touch-icon" href="/apple-touch-icon.png"><link rel="manifest" href="/site.webmanifest"><link rel="stylesheet" href="/assets/wicket.css?v={ASSET_VERSION}"><link rel="stylesheet" href="/assets/publication.css?v={ASSET_VERSION}"><link rel="stylesheet" href="/assets/portraits.css?v={ASSET_VERSION}"><link rel="stylesheet" href="/assets/profile-research.css?v={ASSET_VERSION}"><link rel="stylesheet" href="/assets/editorial-research.css?v={ASSET_VERSION}"><link rel="stylesheet" href="/assets/analytics.css?v={ASSET_VERSION}"><script src="/assets/analysis-core.js?v={ASSET_VERSION}" defer></script><script src="/assets/wicket.js?v={ASSET_VERSION}" defer></script><script src="/assets/analytics.js?v={ASSET_VERSION}" defer></script>{home_assets}{studio_assets}{history_assets}{t20wc_assets}{tools_assets}<link rel="stylesheet" href="/assets/dark.css?v={ASSET_VERSION}"><link rel="stylesheet" href="/assets/arena.css?v={ASSET_VERSION}"><script src="/assets/arena.js?v={ASSET_VERSION}" defer></script>{profile_assets}{ld_scripts}</head><body><a class="skip" href="#main">Skip to statistics</a><div class="topline"><div class="wrap">THE GAME IN NUMBERS <span>Tests · ODIs · T20Is · Men & women</span></div></div><header><div class="wrap header"><a class="brand" href="/" aria-label="Crickrida home"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 244 240" width="30" height="30" aria-hidden="true" class="brand-mark" focusable="false"><defs><mask id="crSeamHead"><rect width="244" height="240" fill="#fff"/><path d="M103.5,137.8 L239.4,-60.0 M112.6,144.0 L248.5,-53.8" stroke="#000" stroke-width="4.5" stroke-linecap="round"/></mask></defs><path d="M0,0 L66,0 L66,98 L0,194Z" fill="currentColor"/><path d="M61.4,125.9 L95.7,76 L238.4,234.1 Q243.8,240 235.8,240 L164.4,240Z" fill="#00E5FF"/><circle cx="176" cy="42" r="39" fill="#FF2D78" mask="url(#crSeamHead)"/></svg><span class="brand-word">crickrida</span></a><button id="menu" aria-label="Open navigation" aria-expanded="false" aria-controls="nav">☰</button><nav id="nav">{''.join(f'<a href="{url}" '+('aria-current="page"' if path.startswith(url) else '')+f'>{name}</a>' for url,name in nav).replace('<a href="/tools/" >','<a href="/tools/" aria-current="page">' if path in tool_paths else '<a href="/tools/" >')}<a class="ipl-link" href="/ipl/dashboard">IPL</a><a class="ipl-link" href="/t20-world-cup/dashboard">T20 World Cup</a><a class="search-link" href="/search/">Search</a></nav><button id="theme" aria-label="Toggle dark theme" aria-pressed="false">◐</button></div></header><main id="main" class="wrap">{body}</main><footer><div class="wrap"><strong class="footer-brand"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 244 240" width="22" height="22" aria-hidden="true" class="brand-mark" focusable="false"><defs><mask id="crSeamFoot"><rect width="244" height="240" fill="#fff"/><path d="M103.5,137.8 L239.4,-60.0 M112.6,144.0 L248.5,-53.8" stroke="#000" stroke-width="4.5" stroke-linecap="round"/></mask></defs><path d="M0,0 L66,0 L66,98 L0,194Z" fill="currentColor"/><path d="M61.4,125.9 L95.7,76 L238.4,234.1 Q243.8,240 235.8,240 L164.4,240Z" fill="#00E5FF"/><circle cx="176" cy="42" r="39" fill="#FF2D78" mask="url(#crSeamFoot)"/></svg>crickrida</strong><p>International careers in every format, with ball-by-ball IPL and T20 World Cup analytics.</p><div class="footer-links">{a('/about/','About')}{a('/contact/','Contact')}{a('/data-coverage/','Data coverage')}{a('/datasets/','Datasets')}{a('/methodology/','Methodology')}{a('/insights/','Statistical insights')}{a('/questions/','Cricket questions')}{a('/blog/','Daily notes')}{a('/on-this-day/','On this day')}{a('/where-to-watch/','Where to watch')}{a('/world-cup/','World Cup archive')}{a('/head-to-head/','Head-to-head records')}{a('/records/best-innings/','Best performances')}{a('/milestones/','Player milestones')}{a('/venue-records/','Venue records')}{a('/corrections/','Report a correction')}{a('/ipl/dashboard','IPL')}{a('/t20-world-cup/dashboard','T20 World Cup')}</div><p class="muted">Ball-by-ball data: <a href="https://cricsheet.org/">Cricsheet</a>. Corrections: <a href="mailto:rkideas65@gmail.com">rkideas65@gmail.com</a>.</p></div></footer><div id="toast" role="status" aria-live="polite"></div></body></html>'''
    target=OUT/path.lstrip('/')/'index.html';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(document,encoding='utf-8')
    if not noindex:PAGES[path]={'title':title,'bytes':len(document.encode()),'sha256':hashlib.sha256(document.encode()).hexdigest(),'lastmod':TODAY}
    if path in PAGES and PREVIOUS.get(path,{}).get('sha256')==PAGES[path]['sha256']:PAGES[path]['lastmod']=PREVIOUS[path].get('lastmod',TODAY)
def heading(title,subtitle='',eyebrow='INTERNATIONAL CRICKET'):
    description=f'<p>{esc(subtitle)}</p>' if subtitle else ''
    return f'<section class="page-head"><div class="eyebrow">{esc(eyebrow)}</div><h1>{esc(title)}</h1>{description}</section>'
def actions():return '<div class="actions"><button data-save>Save page</button><button data-share>Share link</button><button data-csv>Download table CSV</button></div>'
def team_badge(team, path=None):
    mark=f'<span class="team-badge"><img src="/assets/flags/{slug(team)}.svg" width="28" height="20" alt="" loading="lazy"><span>{esc(team)}</span></span>'
    return f'<a class="team-badge-link" href="{esc(path)}">{mark}</a>' if path else mark
def matchup(match,path=None):
    label='<span class="matchup">'+team_badge(match['teams'][0])+f'<span class="match-v">v</span>'+team_badge(match['teams'][1])+'</span>'
    return f'<a class="matchup-link" href="{esc(path)}">{label}</a>' if path else label
def match_table(matches,paths,limit=40):
    return table(['Date','Match','Format','Result','Coverage'],[[esc(m['date']),matchup(m,paths[m['id']]),esc(m['format']+' · '+m['gender']),esc(result(m)),pill('Result only' if m.get('coverage')=='result-only' else 'No play' if m.get('coverage')=='no-play' else 'Scorecard')] for m in matches[:limit]],caption='International match results')
def scoreboard(m,innings,gp,card=None,people=None,pp=None):
    """Result header: each side's innings as linked scores with overs, the winner lit, toss, award, ground and series."""
    winner=(m.get('outcome') or {}).get('winner')
    rows=''
    for team in m['teams']:
        scores=' <span class="sb-and">&amp;</span> '.join(f'<a href="#innings-{i}">{score_text(inn)}'+(f'<small>{esc(overs_text(inn))} ov</small>' if overs_text(inn) else '')+'</a>' for i,inn in enumerate(innings,1) if inn['team']==team and not inn.get('super_over'))
        rows+=f'<div class="sb-team{" is-winner" if team==winner else ""}">'+team_badge(team,gp['teams'].get(team))+f'<span class="sb-scores">{scores or "-"}</span></div>'
    facts=''
    toss=(card or {}).get('toss') or {}
    if toss.get('winner'):
        decision={'bat':'chose to bat','field':'chose to field'}.get(toss.get('decision'),'')
        facts+=f'<span>Toss <b>{esc(toss["winner"])}</b>{(", "+decision) if decision else ""}</span>'
    award=award_links(card,people,pp) if card and people and pp else ''
    if award:facts+=f'<span>Player of the match <b>{award}</b></span>'
    if m.get('event'):facts+=f'<span>{esc(m["event"])}</span>'
    meta=a(gp['grounds'][m['venue']],m['venue'])+(a(gp['series'][m['event']],m['event']) if m.get('event') else '')
    return f'<section class="scoreboard" aria-label="Result">{rows}<p class="sb-result">{esc(result(m))}</p>'+(f'<p class="sb-facts">{facts}</p>' if facts else '')+f'<div class="sb-meta">{meta}</div></section>'
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
    return f'<section class="entity-visuals" aria-label="{esc(name)} archive charts"><div class="entity-chart"><div class="entity-chart-heading"><div><p class="eyebrow">MATCHES BY FORMAT</p><h2>Recorded matches</h2></div><span>{len(matches):,} total</span></div><figure><figcaption>Tests, ODIs and T20Is</figcaption>{format_bars}</figure></div><figure class="entity-chart entity-year-chart"><figcaption>Matches by year · exact annual count</figcaption><div class="entity-year-scroll" tabindex="0" role="img" aria-label="{esc(name)} matches by year">{year_bars}</div></figure>{outcome}</section>'+conditions
def stats_table(p):
    return career_tables(p, table, stat_value)

def options(name,values,label=None):return f'<label>{esc(label or name.title())}<select name="{name}"><option value="">All</option>'+''.join(f'<option value="{esc(v)}">{esc(v)}</option>' for v in values)+'</select></label>'

def render_profile(p,pid,path,rows,apps,*,gp_teams,portraits,pack,curated,checked_at,suffix='',leagues=None):
    """Title, description, body and schema for one format-first player profile."""
    career=p['career'];tot=aggregate(career)
    found=lp.player_leagues(pid,leagues or {})
    title,description=player_seo(p,suffix,lp.seo_clause(found))
    illustration=ILLUSTRATIONS.get(p['name'])
    person,og_image=player_person(p,pid,path,description,portraits,illustration=illustration,base=BASE)
    badges=''.join(team_badge(t,gp_teams.get(t)) for t in p['teams'] if t in gp_teams)
    portrait=portrait_figure(pid,p['name'],portraits,illustration=illustration)
    faq_html,faq_schema=player_faq(p, urls=pack['urls'] if pack else None, name_slug=pack['name_slug'] if pack else slug(p['name']))
    checked_dates=sorted({checked_at}|{s['checked_at'][:10] for s in career.values() if s.get('checked_at')})
    snapshot_label=' to '.join(dict.fromkeys([checked_dates[0],checked_dates[-1]])) if checked_dates else ''
    explorer=('<section class="panel pf-block" id="analysis" data-analytics="'+path+'analytics.json"><h2>Explore every recorded innings</h2><p class="pf-fine">'+str(len(apps))+' match appearances in available scorecards. Filters apply to this archive only.</p><button id="load-analysis" class="primary">Open statistical explorer</button><div id="analysis-controls" hidden></div><div id="analysis-results" aria-live="polite"></div></section>')
    research=opposition_links(rows,path) if curated else ''
    if research:research=research.replace('<section class="panel pr-section">','<section class="panel pr-section pf-block" id="research">',1)
    recent='<section class="panel pf-block" id="recent-appearances"><h2>Latest appearances</h2>'+table(['Date','Match','Format','Result'],[[x['date'],a(x['url'],' v '.join(x['teams'])),x['format'],esc(x['result'])] for x in apps[:12]],caption='Recent available appearances')+'</section><p class="pf-links">'+ ' · '.join(a(gp_teams[t],t) for t in p['teams'] if t in gp_teams)+' · '+a('/compare/#filters=a='+path,'Compare with another player')+'</p>'
    blocks={'tables':stats_table(p),'snapshot':snapshot_label,'glance':career_glance(p,stat_value),'faq':faq_html,'explorer':explorer,'research':research,'recent':recent,'leagues':lp.overview_block(found)}
    tabs={'keys':[k for k,_ in found],'chips':lp.chips(found),'switch':lp.switch_items(found),'panels':''.join(lp.league_panel(p,k,r,leagues[k].get('meta') or {}) for k,r in found)} if found else None
    body=profile_body(p,portrait=portrait,badges=badges,rows=rows,apps=apps,career=career,totals=tot,blocks=blocks,charts=cw.format_lab,stat_value=stat_value,compare_path='/compare/#filters=a='+path,extra=tabs)
    extra={'mainEntity':person,'breadcrumb_name':p['name']}
    if og_image:extra['image']=og_image
    if faq_schema:extra['faq']=faq_schema
    return title,description,body,extra

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
    renamed_venues=canonicalise_matches(matches)
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
    for old_name,new_name in renamed_venues.items():
        old_path=f'/grounds/{slug(old_name)}-{hashlib.sha1(old_name.encode()).hexdigest()[:6]}/'
        new_path=gp['grounds'].get(new_name)
        if not new_path or old_path==new_path:continue
        STUBS.add(old_path);target=OUT/old_path.lstrip('/')/'index.html';target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{esc(old_name)} has moved | Crickrida</title><link rel="canonical" href="{BASE}{new_path}"><meta name="robots" content="noindex,follow"><meta http-equiv="refresh" content="0;url={new_path}"></head><body><p>{esc(old_name)} is now published as <a href="{new_path}">{esc(new_name)}</a>.</p></body></html>',encoding='utf-8')
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
    (OUT/'data').mkdir(exist_ok=True)
    shutil.copy2(ROOT/'data/t20wc_deliveries.json',OUT/'data/t20wc-deliveries.json')
    shutil.copytree(ROOT/'data/t20wc_matches',OUT/'data/t20wc-matches',dirs_exist_ok=True)
    (OUT/'vendor').mkdir(exist_ok=True)
    shutil.copy2(ROOT/'vendor/chart.umd.min.js',OUT/'vendor/chart.umd.min.js')
    lake=ROOT/'analytics_lake'
    if lake.exists():
        lake_manifest=json.loads((lake/'manifest.json').read_text(encoding='utf-8'))
        lake_output=OUT/'data/lake';lake_output.mkdir(parents=True,exist_ok=True)
        current_tables={table_info['file'] for table_info in lake_manifest.get('tables',{}).values()}
        for stale in lake_output.iterdir():
            if stale.is_file() and stale.name!='manifest.json' and stale.name not in current_tables:
                stale.unlink()
        shutil.copy2(lake/'manifest.json',lake_output/'manifest.json')
        for table_info in lake_manifest.get('tables',{}).values():
            source=lake/table_info['file']
            if not source.is_file():raise FileNotFoundError(f'Analytics table missing: {source}')
            shutil.copy2(source,lake_output/source.name)
    prepare_assets(OUT)
    social_url=social_image(OUT, 'International cricket records, profiles & analysis')
    social_source=OUT/'assets'/social_url.split('/assets/',1)[-1]
    shutil.copy2(social_source, OUT/'assets/social/site-default.png')
    trust_pages(page, heading, a, careers['meta'].get('checked_at',''))
    print('Building scorecards and player analysis...',flush=True)
    venue_hosts=venue_host_map(matches)
    for mid,card in all_cards.items():
        m=card['match'];body=heading(' v '.join(m['teams']),f'{m["date"]} · {m["format"]} · {m["gender"]} · {m["venue"]}','MATCH SCORECARD')+scoreboard(m,card['innings'],gp,card,people,pp)+actions()
        body+=cw.match_lab(card)
        for index,inn in enumerate(card['innings'],1):
            body+=render_innings(inn,index,people,pp,(card.get('players') or {}).get(inn['team']))
            if inn.get('super_over'):continue
            bowl={b['id']:b for b in inn['bowling']};bat={b['id']:(pos,b) for pos,b in enumerate(inn['batting'],1)}
            for pid in set(bowl)|set(bat):
                pos,b=bat.get(pid,(None,{}));w=bowl.get(pid,{});team=inn['team'] if b else next(t for t in m['teams'] if t!=inn['team']);opp=next(t for t in m['teams'] if t!=team);host=host_country(m,venue_hosts)
                setting='Unknown' if not host else 'Home' if team==host else 'Away' if opp==host else 'Neutral'
                outcome='Won' if m['outcome'].get('winner')==team else 'Lost' if m['outcome'].get('winner') else {'draw':'Drawn','tie':'Tied'}.get(m['outcome'].get('result'),'No result')
                innings[pid].append({'date':m['date'],'match':mid,'url':mp[mid],'format':m['format'],'opponent':opp,'venue':m['venue'],'setting':setting,'result':outcome,'innings':index,'position':pos,'runs':b.get('runs'),'balls':b.get('balls'),'out':b.get('out'),'fours':b.get('fours'),'sixes':b.get('sixes'),'dismissal':b.get('dismissal'),'wickets':w.get('wickets'),'legal':w.get('balls'),'conceded':w.get('runs'),'maidens':w.get('maidens'),'event':m.get('event') or None})
        body+='<section class="panel"><h2>Playing XIs</h2><div class="grid two">'+''.join('<div><h3>'+team_badge(team,gp['teams'].get(team))+'</h3>'+''.join('<p>'+(a(pp[p['id']],people[p['id']]['name']) if p['id'] in pp else esc(p['name']))+'</p>' for p in squad)+'</div>' for team,squad in card['players'].items())+'</div></section><p class="note">Verified match scorecard. Super overs are excluded from player analysis. A dash means the historical scorecard did not record that field.</p>'
        if not card['innings']:body+='<section class="panel"><h2>No play</h2><p>This match has no recorded innings. Batting and bowling figures do not apply.</p></section>'
        page(mp[mid],match_labels[mid]+' scorecard',f'{result(m)}. {m["format"]} scorecard at {m["venue"]}, including batting, bowling and over-by-over totals.',body,'SportsEvent',{'startDate':m['date'],'sport':'Cricket','location':{'@type':'Place','name':m['venue']},'competitor':[{'@type':'SportsTeam','name':team,'sport':'Cricket'} for team in m['teams']]})
    for m in hist['matches']:
        if m['id'] in all_cards:continue
        body=heading(' v '.join(m['teams']),f'{m["date"]} · {m["format"]} · {m["gender"]}','HISTORICAL RESULT')+matchup(m)+f'<div class="result-banner">{esc(result(m))}</div><p>{a(gp["grounds"][m["venue"]],m["venue"])}</p>'+actions()+'<section class="panel"><h2>Match coverage</h2><p>This record contains the result. Local innings, lineups and ball data are unavailable.</p>'+ ' · '.join(a(gp['teams'][t],t) for t in m['teams'])+'</section>'
        page(mp[m['id']],match_labels[m['id']]+' result',f'{result(m)}. Historical {m["format"]} result at {m["venue"]}.',body,'SportsEvent',{'startDate':m['date'],'sport':'Cricket'})
    player_q=prepare_player_questions(people,pp,featured_names=set(ILLUSTRATIONS)|set(HERO_CAST),extra_ids=research_ids)
    print('Building career profiles...',flush=True)
    leagues=lp.load_leagues(ROOT)
    for pid,p in people.items():
        career=p['career'];path=pp[pid];rows=sorted(innings[pid],key=lambda r:(r['date'],r['match'],r.get('innings') or 0));apps=appearances[pid]
        summary={'id':pid,'name':p['name'],'teams':p['teams'],'gender':p['gender'],'career':career,'url':path}
        summary['career']={fmt:{k:v for k,v in s.items() if k not in ('source','sources','enrichment_source')} for fmt,s in career.items()}
        dump(path+'summary.json',summary);dump(path+'analytics.json',{'innings':rows,'appearances':apps,'note':'Available official match scorecards within site coverage. Super overs excluded. Unknown venue setting is not inferred.'})
        suffix=' · '+pid if names[slug(p['name'])]>1 else ''
        pack=player_q.get(pid)
        checked_at=careers['meta']['checked_at'][:10]
        title,description,body,extra=render_profile(p,pid,path,rows,apps,gp_teams=gp['teams'],portraits=portraits,pack=pack,curated=pid in research_ids,checked_at=checked_at,suffix=suffix,leagues=leagues)
        page(path,title,description,body,'ProfilePage',extra)
    print('Building comparison pages...',flush=True)
    COMPARE_CARDS.clear()
    for names in PAIRS:
        players=[find_player(people,name) for name in names]
        if any(p is None for p in players) or len({p['id'] for p in players})<len(players):continue
        path='/compare/'+'-vs-'.join(slug(p['name']) for p in players)+'/'
        body,faq,description=compare_body(players,innings,pp,portraits,ILLUSTRATIONS)
        title=' vs '.join(p['name'] for p in players)+' stats: '+', '.join(f for f in ('Test','ODI','T20I') if any(f in p['career'] for p in players))
        extra={'breadcrumb_name':' vs '.join(p['name'] for p in players)}
        if faq:extra['faq']={'@context':'https://schema.org','@type':'FAQPage','mainEntity':[{'@type':'Question','name':q,'acceptedAnswer':{'@type':'Answer','text':ans}} for q,ans in faq]}
        page(path,title,description,body,'WebPage',extra)
        lead=max(((f,sum((p['career'].get(f) or {}).get('matches') or 0 for p in players)) for f in ('Test','ODI','T20I')),key=lambda x:x[1])[0]
        COMPARE_CARDS.append((path,[p['name'] for p in players],f'{lead} careers side by side: measures, year by year and by opponent.'))
    for spec in editorial['pages']:
        if isinstance(spec, tuple):
            spec=dict(zip(('path','title','description','body'),spec))
        if spec['path'].startswith('/compare/'):continue
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
    history_home=publish_history(matches,all_cards,people,pp,mp,page,dump,OUT,ILLUSTRATIONS)
    build_collections(people,matches,pp,mp,gp,groups,careers,arc,hist,editorial,all_cards,history_home)
    build_question_hubs(people,matches,pp,mp,gp,careers,all_cards,player_q,HERO_CAST)
    build_daily_blog(people,pp,careers,all_cards,mp)
    coverage_page(matches,all_cards,careers,page)
    dump('/data/routes.json',{'players':pp,'matches':mp})
    dump('/data/player-index.json',[{'id':pid,'name':p['name'],'url':pp[pid],'teams':p['teams'],'gender':p['gender'],'formats':list(p['career'] or p['formats']),'byFormat':{fmt:{'runs':stats.get('runs'),'wickets':stats.get('wickets')} for fmt,stats in p['career'].items()},'runs':aggregate(p['career']).get('runs'),'wickets':aggregate(p['career']).get('wickets'),'art':ILLUSTRATIONS.get(p['name'])} for pid,p in people.items()])
    dump('/data/match-index.json',[{'id':m['id'],'date':m['date'],'url':mp[m['id']],'teams':m['teams'],'format':m['format'],'gender':m['gender'],'venue':m['venue'],'event':m['event'],'result':result(m),'coverage':'Result only' if m.get('coverage')=='result-only' else 'No play' if m.get('coverage')=='no-play' else 'Scorecard'} for m in matches])
    # Separate high-value hubs from large entity archives so Search Console can
    # report indexing by page type instead of one arbitrary 10,000-URL batch.
    sitemap_groups=defaultdict(list)
    for path in sorted(PAGES):
        section=path.strip('/').split('/')[0]
        group=section if section in {'matches','players','questions','research','grounds','series','on-this-day'} else 'core'
        sitemap_groups[group].append(path)
    sitemap_files=[]
    for xml in OUT.glob('sitemap-*.xml'):xml.unlink()
    for group in ['core','players','matches','questions','research','grounds','series','on-this-day']:
        items=sitemap_groups.get(group,[])
        for index,start in enumerate(range(0,len(items),10000),1):
            paths=items[start:start+10000]
            name=f'sitemap-{group}-{index}.xml'
            sitemap_files.append((name,max(PAGES[path]['lastmod'] for path in paths)))
            xml='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{BASE}{esc(path)}</loc><lastmod>{PAGES[path]["lastmod"]}</lastmod></url>' for path in paths)+'</urlset>'
            (OUT/name).write_text(xml,encoding='utf-8')
    (OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<sitemap><loc>{BASE}/{name}</loc><lastmod>{lastmod}</lastmod></sitemap>' for name,lastmod in sitemap_files)+f'<sitemap><loc>{BASE}/sitemap-ipl.xml</loc></sitemap></sitemapindex>',encoding='utf-8')
    # Public JSON indexes power the crawlable search and explorer experience;
    # only the private notebook is excluded from search.
    (OUT/'robots.txt').write_text(f'User-agent: *\nAllow: /\nDisallow: /saved/\nDisallow: /ipl/admin\nDisallow: /ipl/login\nDisallow: /t20-world-cup/admin\nDisallow: /t20-world-cup/login\nSitemap: {BASE}/sitemap.xml\n',encoding='utf-8')
    # Only prune destinations previously owned by the generator, inside this output.
    for path in set(PREVIOUS)-set(PAGES):
        target=(OUT/path.lstrip('/')).resolve()
        assert target.is_relative_to(OUT.resolve()) and target!=OUT.resolve()
        for name in ['index.html','summary.json','analytics.json','records.json']:
            (target/name).unlink(missing_ok=True)
    for index in OUT.rglob('index.html'):
        path='/'+index.parent.relative_to(OUT).as_posix().strip('./')+'/'
        if path=='//':path='/'
        if path in PAGES or path in STUBS or path in ('/embed/','/search/','/saved/','/international/'):continue
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
    official_innings=load_innings_records()

    bundled=merge_official(matches,cards,people)
    families=bundled['families']
    glance=''
    for key,label,fmt,gender in FAMILIES:
        rec=families[key]
        top=rec['titles'].most_common(1)
        champ,count=(top[0] if top else ('Not recorded',0))
        last=rec['editions'][-1]['winner'] if rec['editions'] else 'Not recorded'
        first=rec['official']['first_year']
        latest=rec['official']['latest_year']
        from_year=(rec.get('analysis') or {}).get('from_year')
        analysis_bit=f' Ball-by-ball analysis from {from_year}.' if from_year else ''
        glance+=f'<a class="format-card" href="/world-cup/{key}/"><h3>{esc(label)}</h3><div class="format-card-hero"><strong>{esc(str(count))}</strong><span>titles · {esc(champ)}</span></div><p class="format-card-note">{len(rec["editions"])} official editions, {first} to {latest}.{analysis_bit} Last champion: {esc(last or "not recorded")}.</p></a>'
    world_body=heading('World Cup cricket records','Official winners, finals, semi-finalists and landmark records for men and women. Ball-by-ball analysis starts from the first year deliveries exist.','WORLD CUP DATA')+actions()
    world_body+='<p class="player-intro">The men\'s ODI World Cup began in 1975. The latest completed edition is 2023, won by Australia, their sixth title. Women\'s ODI World Cups began in 1973. T20 World Cups began in 2007 for men and 2009 for women. Title counts and the timeline on these pages are the official tournament record. They are not inferred from the ball-by-ball archive. Player tables start at the first year with over-by-over deliveries, so granular analysis is possible from that date. Afghanistan World Cup games Cricsheet withholds are attached when the date sits inside an official edition.</p>'
    if glance: world_body+='<section class="career-glance-wrap" id="by-format"><p class="eyebrow">THE GLOBAL EVENTS</p><h2>Who has won, from the first World Cup to now</h2><div class="career-glance">'+glance+'</div></section>'
    official_editions=sum(len(rec['editions']) for rec in families.values())
    archive_matches=sum(rec['archive_match_count'] for rec in families.values())
    mens_from=(families['mens-odi'].get('analysis') or {}).get('from_year') or families['mens-odi']['official']['first_year']
    world_body+='<div class="stats"><div><strong>'+num(official_editions)+'</strong><span>Official editions</span></div><div><strong>'+num(families['mens-odi']['titles']['Australia'])+'</strong><span>Australia men\'s ODI titles</span></div><div><strong>'+num(archive_matches)+'</strong><span>Tournament matches in this archive</span></div><div><strong>'+esc(str(mens_from))+'</strong><span>Men\'s ODI ball-by-ball from</span></div></div>'
    for key,label,fmt,gender in FAMILIES:
        rec=families[key]
        path='/world-cup/'+key+'/'
        leaders=rec['leaders']
        titles=titles_leaderboard(rec,gp['teams'])
        first=rec['official']['first_year']
        latest=rec['official']['latest_year']
        body=heading(label,f'{len(rec["editions"])} official editions · {first} to {latest}','WORLD CUP')+actions()
        coverage_copy=('The delivery dashboard covers 368 played matches from 2007 to 2026, including 34 independently reconciled Afghanistan matches.' if key=='mens-t20' else coverage_note(rec))
        body+=f'<p class="player-intro">{esc(label)} from the first tournament to the latest completed edition. The timeline lists the champion, runner-up and losing semi-finalists. Landmark records are the official World Cup record, sourced independently of this site\'s scorecard archive. {esc(coverage_copy)}</p>'
        if key=='mens-t20':
            body+='<section class="panel"><p class="eyebrow">NEW · DELIVERY ANALYSIS</p><h2>Explore every men\'s T20 World Cup</h2><p>Filter the complete 2007–2026 delivery archive, compare team wins, inspect phase scoring and sort batting and bowling leaders.</p><p><a class="primary" href="/world-cup/mens-t20/dashboard/">Open the interactive dashboard</a></p></section>'
        if titles:
            body+='<section class="panel" id="winners"><h2>Most titles</h2>'+table(['Team','Titles'],titles,caption=label+' official titles')
            body+=cw.leader_bars([(team,count) for team,count in rec['titles'].most_common(8)],label+' titles',minimum=1)+'</section>'
        body+='<section class="panel" id="timeline"><h2>Official timeline</h2>'+table(['Year','Host','Champion','Runner-up','Semi-finalists','Result'],timeline_table(rec,gp['teams']),caption=label+' winners, finals and semi-finalists')+'</section>'
        record_rows=official_record_rows(rec)
        if record_rows:
            body+='<section class="panel" id="records"><h2>Official records</h2>'+table(['Record','Holder','Value','Detail'],record_rows,caption=label+' landmark records')+'</section>'
        analysis=rec.get('analysis') or {}
        if key!='mens-t20' and (leaders['runs'] or leaders['wickets'] or analysis.get('from_year')):
            body+='<section class="panel" id="analysis"><h2>'+esc(analysis_heading(rec))+'</h2><p class="muted">'+esc(analysis_lede(rec))+'</p>'
            if analysis.get('from_year'):
                body+='<div class="stats"><div><strong>'+esc(str(analysis['from_year']))+'</strong><span>Ball-by-ball from</span></div><div><strong>'+num(analysis.get('ball_by_ball'))+'</strong><span>Over-by-over matches</span></div><div><strong>'+num(analysis.get('scorecard_only'))+'</strong><span>Tables only</span></div>'
                if analysis.get('afghanistan_without_balls'):
                    body+='<div><strong>'+num(analysis['afghanistan_without_balls'])+'</strong><span>Afghanistan without deliveries</span></div>'
                body+='</div>'
            if leaders['runs']:
                body+='<h3 id="runs">Leading run scorers</h3>'+table(['Player','Runs','Inns','HS','100s'],[[a(pp.get(r['id'],'/players/'),r['name']),num(r['runs']),num(r['innings']),num(r['highest']),num(r['hundreds'])] for r in leaders['runs']],caption=label+' run scorers from recorded innings from '+str(analysis.get('from_year') or 'this window'))
            if leaders['wickets']:
                body+='<h3 id="wickets">Leading wicket takers</h3>'+table(['Player','Wickets','Inns','Best'],[[a(pp.get(r['id'],'/players/'),r['name']),num(r['wickets']),num(r['innings']),esc(r['best'] or '')] for r in leaders['wickets']],caption=label+' wicket takers from recorded innings from '+str(analysis.get('from_year') or 'this window'))
            if leaders['scores']:
                body+='<h3>Highest recorded scores</h3>'+table(['Runs','Player','Balls','Date','Team'],[[num(runs),esc(name),num(balls),esc(day),esc(team or '')] for runs,balls,name,day,mid,team in leaders['scores']],caption=label+' highest individual scores from the ball-by-ball window')
            if leaders['spells']:
                body+='<h3>Best recorded bowling</h3>'+table(['Figures','Player','Date'],[[f'{wkts}/{conceded}',esc(name),esc(day)] for wkts,conceded,name,day,mid in leaders['spells']],caption=label+' best bowling figures from the ball-by-ball window')
            body+='</section>'
        body+='<p class="note">Official titles and finals are complete even when a scorecard is missing here. Ball-by-ball tables count only innings this site holds from the analysis year onward. A missing innings is not a zero. '+a('/world-cup/','All World Cup records')+' · '+a('/records/','Career records')+'</p>'
        top_team,top_count=(rec['titles'].most_common(1)[0] if rec['titles'] else ('Not recorded',0))
        from_year=analysis.get('from_year')
        analysis_desc=f' Ball-by-ball analysis from {from_year}.' if from_year else ''
        description=f'{label}: {top_team} has {top_count} official titles. Timeline of winners, runners-up and semi-finalists from {first} to {latest}.{analysis_desc}'
        page(path,label+' winners, finals and records',description,body,'CollectionPage',{'breadcrumb_name':label})
        world_body+='<section class="panel"><h2>'+esc(label)+'</h2>'
        if titles: world_body+=table(['Team','Titles'],titles[:8],caption=label+' official titles')
        world_body+=table(['Year','Host','Champion','Runner-up','Semi-finalists','Result'],timeline_table(rec,gp['teams']),caption=label+' official timeline')
        world_body+='<p>'+a(path,'Full '+label+' records')+'</p></section>'
    all_wc=[m for rec in families.values() for m in rec['archive']['matches']]
    recent=sorted(all_wc,key=lambda m:(m['date'],m['id']),reverse=True)[:20]
    if recent: world_body+='<section class="panel"><h2>Recent World Cup scorecards in this archive</h2>'+match_table(recent,mp,20)+'</section>'
    world_body+='<p class="note">Champions Trophy and qualifying events are not mixed into these World Cup title counts. Player career tables on other pages use official international snapshots, not World Cup-only innings. '+a('/records/','Career records')+' · '+a('/questions/','Questions')+'</p>'
    page('/world-cup/','World Cup winners, finals and records','Official World Cup winners, runners-up, semi-finalists and landmark records for men and women in ODIs and T20s. The men\'s ODI World Cup runs from 1975 to 2023. Ball-by-ball analysis starts from the first year deliveries exist.',world_body,'CollectionPage')

    # Team-pair pages answer a common search intent while retaining a single
    # canonical overview page for the full rivalry directory.
    pairs=defaultdict(list)
    for m in matches:
        if len(m.get('teams',[]))!=2:continue
        pairs[tuple(sorted(m['teams']))].append(m)
    pair_rows=[]
    venue_hosts=venue_host_map(matches)
    host_of=lambda m:host_country(m,venue_hosts)
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
        counts=Counter(m['format'] for m in ms);formats=[f for f in ('Test','ODI','T20I') if counts.get(f)]
        pair_body=heading(left+' vs '+right+' head-to-head records',f'{len(ms):,} recorded international matches between {left} and {right}, with format, gender and result breakdowns.','HEAD-TO-HEAD')+actions()+entity_switch(formats,counts)+'<section class="fmt-panel fmt-overview" id="overview" data-fmt-panel="overview" aria-label="Overview">'
        pair_body+='<div class="stats">'+''.join(f'<div><strong>{num(value)}</strong><span>{label}</span></div>' for value,label in [(len(ms),'Matches'),(wins.get(left,0),left+' wins'),(wins.get(right,0),right+' wins'),(sum(not m.get('outcome',{}).get('winner') for m in ms),'Draws / ties / no result')])+'</div>'
        pair_body+=cw.win_share(left,right,wins.get(left,0),wins.get(right,0),sum(not m.get('outcome',{}).get('winner') for m in ms))
        if format_rows:pair_body+='<section class="panel"><h2>Results by format and gender</h2>'+table(['Format','Gender','Matches',left+' wins',right+' wins','Other'],format_rows,caption=left+' versus '+right+' results by format and gender')+'</section>'
        pair_body+='<section class="panel pf-block"><h2>Recent recorded matches</h2>'+match_table(recent,mp,25)+'</section><p class="pf-links">'+a('/head-to-head/','Browse every international head-to-head')+' · '+a(gp['teams'][left],left)+' · '+a(gp['teams'][right],right)+'</p></section>'
        for fmt in formats:pair_body+=h2h_format_panel(left,right,fmt,[m for m in ms if m['format']==fmt],cards,people,pp,mp,host_of)
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
        overs_display=b.get('overs_display') or ('-' if b.get('balls') is None else str((b.get('balls') or 0)//6)+'.'+str((b.get('balls') or 0)%6))
        bowl_rows.append([a(pp[b['id']],people[b['id']]['name']),m['date'],esc(team),esc(opp),m['format'],num(wickets),num(conceded),esc(overs_display),a(mp[m['id']],'Scorecard')])
    performance_body=heading('Best international cricket performances','Official landmark innings first, then the biggest batting and bowling spells in available scorecards.','PERFORMANCE RECORDS')+actions()
    performance_body+='<section class="panel" id="official-records"><h2>Official landmark records</h2><p class="muted">Complete international records, independent of whether this site holds the scorecard.</p>'+official_innings_table(official_innings,table)+'</section>'
    performance_body+='<p class="lede">The tables below rank individual innings in available scorecards. They do not replace the official landmarks above. Historical coverage varies by era. Every row links to the underlying scorecard.</p>'
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
    innings_official=load_innings_records()
    for fmt in ('Test','ODI','T20I'):
        rec=next((row for row in innings_official.get('records') or [] if row['format']==fmt and row['gender']=='Men' and 'score' in row['metric'].lower()),None)
        if rec:
            questions.append({'slug':f'highest-{fmt.lower()}-individual-score','title':f'What is the highest individual score in {fmt} cricket?','description':f'The official highest individual {fmt} international score, independent of scorecard coverage.','category':'OFFICIAL RECORDS','answer':f'{rec["holder"]} holds the official {fmt} record: {rec["value"]} for {rec["team"]}. {rec.get("detail") or ""} This is the complete international record, not a total from available scorecards.', 'links':[('/records/best-innings/','Browse official and archive innings'),('/records/', 'Career records')]})
        else:
            scores=[x for x in batting if x[2]['format']==fmt]
            if scores:
                runs,balls,m,team,opp,b=scores[0]
                questions.append({'slug':f'highest-{fmt.lower()}-individual-score','title':f'What is the highest individual score in {fmt} cricket?','description':f'Highest recorded individual {fmt} international score in the Crickrida scorecard archive.','category':'SCORECARD RECORDS','answer':f'{people[b["id"]]["name"]} has the highest recorded {fmt} score in this archive: {num(runs)} for {team} against {opp} on {m["date"]}.', 'links':[('/records/best-innings/','Browse best innings'),(mp[m['id']],'Open the scorecard')]})
        rec=next((row for row in innings_official.get('records') or [] if row['format']==fmt and row['gender']=='Men' and 'bowling' in row['metric'].lower()),None)
        if rec:
            questions.append({'slug':f'best-{fmt.lower()}-bowling-figures','title':f'What are the best bowling figures in {fmt} cricket?','description':f'The official best {fmt} bowling innings, independent of scorecard coverage.','category':'OFFICIAL RECORDS','answer':f'{rec["holder"]} holds the official {fmt} bowling record: {rec["value"]} for {rec["team"]}. {rec.get("detail") or ""}', 'links':[('/records/best-innings/','Browse official and archive innings'),('/records/', 'Career records')]})
        else:
            spells=[x for x in bowling if x[2]['format']==fmt]
            if spells:
                wickets,conceded,m,team,opp,b=spells[0]
                questions.append({'slug':f'best-{fmt.lower()}-bowling-figures','title':f'What are the best bowling figures in {fmt} cricket?','description':f'Best recorded individual {fmt} international bowling figures, ordered by wickets and runs conceded.','category':'SCORECARD RECORDS','answer':f'{people[b["id"]]["name"]} recorded the best {fmt} figures in this archive: {num(wickets)} wickets for {num(conceded)} runs for {team} against {opp} on {m["date"]}.', 'links':[('/records/best-innings/','Browse best bowling figures'),(mp[m['id']],'Open the scorecard')]})

    questions.extend([
        {'slug':'difference-between-test-odi-t20i','title':'What is the difference between Test, ODI and T20I cricket?','description':'A clear comparison of the three international formats, innings structure, time and scoring context.','category':'FORMAT GUIDE','answer':'Tests give each side two innings and can run for up to five days. ODIs give each side one innings of up to 50 overs. T20Is give each side one innings of up to 20 overs. The shorter formats make each delivery more scarce; comparing a rate or total without its format and workload can mislead.', 'links':[('/records/','Explore format records'),('/methodology/','Read the statistical definitions')]},
        {'slug':'how-is-batting-average-calculated','title':'How is a cricket batting average calculated?','description':'Learn the batting-average formula and see how not-outs and missing dismissals affect a career record.','category':'STATISTICS EXPLAINED','answer':'Batting average is runs divided by dismissals. A not-out innings adds runs and innings but does not add a dismissal. Crickrida recomputes combined averages from the published runs and dismissals; if the denominator is missing or zero, the page shows an unavailable or inapplicable value rather than inventing one.', 'links':[('/methodology/','Read the full definitions'),('/records/','Browse batting-average records')]},
        {'slug':'what-is-cricket-strike-rate','title':'What is strike rate in cricket?','description':'Understand batting strike rate, bowling strike rate and the denominators required for each.','category':'STATISTICS EXPLAINED','answer':'Batting strike rate is 100 multiplied by runs divided by balls faced. Bowling strike rate is legal balls divided by wickets. Both require a recorded denominator. A dash means the source did not record the required balls or wickets; it is not a zero.', 'links':[('/methodology/','Read the rate definitions'),('/compare/','Compare two players')]},
        {'slug':'how-do-head-to-head-records-work','title':'How do international cricket head-to-head records work?','description':'See how Crickrida counts matches, wins and other results for every full-member rivalry.','category':'RIVALRIES','answer':'A head-to-head page selects matches involving the same two national teams, then separates them by format and gender. Wins use the winner recorded in the match source. Draws, ties, no-results and matches without a winner remain visible in the Other column.', 'links':[('/head-to-head/','Browse every rivalry'),('/teams/','Explore team records')]},
        {'slug':'what-is-a-century-and-five-wicket-haul','title':'What is a century or a five-wicket haul in cricket?','description':'A scorecard guide to centuries, fifties and five-wicket bowling milestones.','category':'SCORECARD TERMS','answer':'A century is an innings of at least 100 runs. A fifty is an innings of at least 50 runs but below 100. A five-wicket haul is an innings with at least five wickets; ten-wicket match hauls are separately labelled when the scorecards support them.', 'links':[('/milestones/','Browse player milestones'),('/records/best-innings/','Browse performance records')]},
        {'slug':'are-international-career-records-complete','title':'Are Crickrida international career records complete?','description':'Understand the difference between official career snapshots and the available scorecard archive.','category':'DATA COVERAGE','answer':'Career tables are independent official international snapshots and may include recognized matches that are outside the ball-by-ball scorecard archive. Match explorers use the published international scorecards and label result-only records. Missing fields remain unavailable; they are never inferred from a partial match.', 'links':[('/methodology/','Read coverage and definitions'),('/data-coverage/','Inspect current coverage')]},
        {'slug':'how-to-compare-cricket-players','title':'How should two cricket players be compared?','description':'A practical, format-aware way to compare international careers without hiding workload or era.','category':'PLAYER COMPARISON','answer':'Choose the same format, gender and data scope first. Read runs or wickets alongside innings, dismissals, balls, average and strike rate, then inspect the playing span and opposition context. Crickrida keeps career snapshots separate from narrower available-scorecard samples so a partial archive is not presented as a full career.', 'links':[('/compare/','Open player comparison'),('/players/','Browse player profiles')]},
        {'slug':'who-has-the-most-womens-odi-runs','title':'Who has the most women’s ODI runs?','description':'The leading women’s ODI run scorer in the published official career snapshot, with a link to the qualified leaderboard.','category':'WOMEN’S RECORDS','answer':'Open the women’s ODI most-runs leaderboard for the current snapshot, qualification and the rest of the table.','links':[('/records/women/odi/most-runs/','Women’s ODI most runs'),('/records/women/t20i/most-runs/','Women’s T20I most runs')]},
        {'slug':'who-has-the-most-odi-sixes','title':'Who has hit the most ODI sixes?','description':'Find the men’s ODI sixes leader in the published career snapshot, with fours and boundary context.','category':'CAREER RECORDS','answer':'Sixes are a career counting statistic. Read them with fours, runs and balls so a sixes lead is not mistaken for a faster innings.','links':[('/records/men/odi/most-sixes/','Men’s ODI most sixes'),('/blog/2026-09-11/','Rohit vs Kohli boundary note')]},
        {'slug':'how-to-read-a-cricket-worm-chart','title':'How do you read a cricket worm chart?','description':'A short guide to worms, Manhattans and partnerships on Crickrida scorecards.','category':'SCORECARD CHARTS','answer':'A worm plots the innings total at the end of each over. Dots mark wickets. A Manhattan shows runs scored in each over. Partnerships are the runs added between recorded falls of wicket. Crickrida draws these only from recorded overs; historical result-only matches have no worm.','links':[('/matches/','Browse scorecards'),('/studio/','Export a match card')]},
        {'slug':'what-is-a-result-only-match','title':'What does result-only mean on a cricket scorecard?','description':'Why some historical international matches have a result but no innings or player figures.','category':'DATA COVERAGE','answer':'A result-only record confirms the match result, teams, date and venue, but the source does not provide a usable innings or lineup. It remains searchable as an international match while batting and bowling figures stay unavailable.', 'links':[('/matches/','Browse match records'),('/methodology/','Read the archive policy')]},
        {'slug':'which-team-has-most-international-wins','title':'Which international team has the most recorded wins?','description':'Official men\'s Test and ODI win counts, independent of the ball-by-ball archive.','category':'TEAM RECORDS','answer':'Australia hold the most official men\'s Test wins (426) and the most official men\'s ODI wins (619) in the ESPNcricinfo team summaries used on Crickrida. Open a team page for the complete played, won and lost table, then use the archive list for available scorecards.', 'links':[('/teams/','Browse team records'),('/head-to-head/','Compare rivalries')]},
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
        body=heading(q['title'],q['description'],q['category'])+actions()+'<article class="research-article"><p>'+q['answer']+'</p><h2>Explore the underlying records</h2><p>'+' · '.join(a(path,label) for path,label in q['links'])+'</p><p class="note">This answer is generated from Crickrida’s validated international dataset. Career figures and available scorecard figures are kept as separate layers; see the methodology page for definitions and coverage dates.</p></article>'
        page('/questions/'+q['slug']+'/',q['title'],q['description'],body,'Article',{'headline':q['title'],'author':{'@type':'Organization','name':'Crickrida','url':BASE+'/about/'}})
    if player_q:
        assert_clean_bundle(player_q)
        snapshot=careers['meta'].get('checked_at','')[:10]
        page('/questions/players/','International player stats questions','Dedicated pages for how many runs, wickets, centuries and sixes named international players have scored, from official career snapshots.',player_question_directory(player_q,people,pp,table),'CollectionPage')
        for pid,pack in player_q.items():
            player=people[pid]
            for spec in pack['specs']:
                related=[item for item in pack['specs'] if item['url']!=spec['url']]
                body=heading(spec['title'],spec['description'],'PLAYER STATS')+actions()+question_page(spec,player,related,snapshot)
                extra={'headline':spec['title'],'author':{'@type':'Organization','name':'Crickrida','url':BASE+'/about/'},'faq':{'@context':'https://schema.org','@type':'FAQPage','mainEntity':[{'@type':'Question','name':spec['title'],'acceptedAnswer':{'@type':'Answer','text':spec['answer']}}]},'breadcrumb_name':spec['title']}
                page(spec['url'],spec['title'],spec['description'],body,'Article',extra)

def build_daily_blog(people,pp,careers,all_cards=None,mp=None):
    """Publish a compact series of data-backed daily notes with editorial visuals."""
    left=next((p for p in people.values() if p.get('name')=='Virat Kohli'),None)
    right=next((p for p in people.values() if p.get('name')=='Rohit Sharma'),None)
    if not left or not right or 'ODI' not in left.get('career',{}) or 'ODI' not in right.get('career',{}):return
    a1,a2=left['career']['ODI'],right['career']['ODI']
    post_date='2026-09-10'; checked=esc(careers['meta'].get('checked_at',TODAY)[:10])
    posts=[]
    def publish(slug_name,title,description,visual,alt,lead,content,callout,width=1432,height=1076,*,date=post_date,data_date=checked,methodology=None,subjects=None):
        path='/blog/'+date+'/'+((slug_name.strip('/')+'/') if slug_name else '')
        article='<div class="daily-note">'+heading(title,'A small daily lesson in reading international cricket numbers.','DAILY NOTE')
        article+=f'<p class="daily-byline"><span>Crickrida</span><span>·</span><time datetime="{date}">{date}</time><span>·</span><span>Data checked {esc(data_date)}</span></p>'+actions()
        article+='<article><p>'+lead+'</p><figure class="daily-infographic"><a href="/assets/art/blog/'+visual+'" aria-label="Open full-size infographic"><img src="/assets/art/blog/'+visual+'" width="'+str(width)+'" height="'+str(height)+'" loading="eager" alt="'+esc(alt)+'"></a><figcaption>'+esc(title)+' · Crickrida · data checked '+esc(data_date)+'</figcaption></figure>'+content
        links=' · '.join(a(pp[p['id']],p['name']+' profile') for p in (subjects or [left,right]))
        article+='<div class="data-callout">'+callout+'</div><p>'+a('/compare/','Compare two international careers')+' · '+links+' · '+a('/studio/','Create your own visual')+'</p><p class="note">'+esc(methodology or 'Career figures are independent official snapshots. Batting average is runs ÷ dismissals; strike rate is 100 × runs ÷ balls faced. A missing denominator stays unavailable.')+'</p></article></div>'
        extra={'headline':title,'datePublished':date,'dateModified':date,'author':{'@type':'Organization','name':'Crickrida','url':BASE+'/about/'},'publisher':{'@type':'Organization','name':'Crickrida','url':BASE+'/'}}
        if visual.endswith(('.png','.webp','.jpg')):extra.update(image=BASE+'/assets/art/blog/'+visual,mainEntityOfPage=BASE+path)
        page(path,title,description,article,'Article',extra)
        posts.append((date,path,title,description,visual,alt,width,height))

    publish('','How to compare two international batters fairly','A practical Crickrida guide to reading runs, batting average and strike rate together, using a Virat Kohli and Rohit Sharma ODI example.','2026-09-10-compare-batters.svg','Infographic comparing Virat Kohli and Rohit Sharma in ODI runs, batting average and strike rate','When two batters are compared, one number rarely settles the question. Runs show accumulated output, average shows what a player scores per dismissal, and strike rate shows scoring pace. Read the three together, and keep the format and career scope the same.','<h2>What the example shows</h2><p>In this ODI snapshot, '+a(pp[left['id']],left['name'])+' leads the run total with <strong>'+num(a1.get('runs'))+'</strong> from '+num(a1.get('innings'))+' innings. '+a(pp[right['id']],right['name'])+' has '+num(a2.get('runs'))+' runs from '+num(a2.get('innings'))+' innings. That is the volume view.</p><p>The average comparison favours '+left['name']+' in this snapshot, while the strike-rate values are close. Era, role, opposition, venues and opportunity still matter.</p>','<div><strong>'+decimal_stat(a1.get('avg'))+'</strong><span>'+left['name']+' ODI average</span></div><div><strong>'+decimal_stat(a2.get('avg'))+'</strong><span>'+right['name']+' ODI average</span></div><div><strong>'+decimal_stat(a1.get('sr'))+' / '+decimal_stat(a2.get('sr'))+'</strong><span>ODI strike rates · '+left['name']+' / '+right['name']+'</span></div>',1200,760)
    publish('average-needs-dismissals','Why batting average needs its denominator','A Crickrida explainer on dismissals, not-outs and the denominator behind every international batting average.','2026-09-10-average-dismissals-data.svg','Data infographic comparing Virat Kohli and Rohit Sharma ODI runs, dismissals and batting average','A batting average is not runs divided by innings. It is runs divided by dismissals, which is why a not-out can lift a player’s average without adding another dismissal. The denominator carries the context.','<h2>Read the denominator first</h2><p>In the same ODI snapshot, '+a(pp[left['id']],left['name'])+' has <strong>'+num(a1.get('runs'))+'</strong> runs and '+num(a1.get('outs'))+' dismissals, producing an average of '+decimal_stat(a1.get('avg'))+'. '+a(pp[right['id']],right['name'])+' has '+num(a2.get('runs'))+' runs from '+num(a2.get('outs'))+' dismissals, producing '+decimal_stat(a2.get('avg'))+'. A not-out contributes runs but leaves the dismissal count unchanged.</p><p>That makes average useful for comparing scoring returns per opportunity, but it should sit beside innings, not-outs and the format. Crickrida keeps unavailable dismissals visible instead of filling them with an estimate.</p>','<div><strong>'+num(a1.get('outs'))+'</strong><span>'+left['name']+' ODI dismissals</span></div><div><strong>'+num(a2.get('outs'))+'</strong><span>'+right['name']+' ODI dismissals</span></div><div><strong>'+decimal_stat(a1.get('avg'))+' / '+decimal_stat(a2.get('avg'))+'</strong><span>ODI batting averages · '+left['name']+' / '+right['name']+'</span></div>',1200,760)
    publish('strike-rate-needs-balls','Why strike rate needs balls faced','A Crickrida explainer on batting strike rate and the balls-faced denominator that makes pace comparable.','2026-09-10-strike-rate-balls-data.svg','Data infographic comparing Virat Kohli and Rohit Sharma ODI runs, balls faced and batting strike rate','Strike rate describes scoring pace: runs per 100 balls faced. Without balls faced, a run total cannot tell us whether an innings was paced quickly or slowly.','<h2>Pace needs a workload</h2><p>'+a(pp[left['id']],left['name'])+' has '+num(a1.get('runs'))+' ODI runs from '+num(a1.get('balls'))+' balls, a strike rate of '+decimal_stat(a1.get('sr'))+'. '+a(pp[right['id']],right['name'])+' has '+num(a2.get('runs'))+' runs from '+num(a2.get('balls'))+' balls, a strike rate of '+decimal_stat(a2.get('sr'))+'. The formula is simple: 100 × runs ÷ balls. But the denominator keeps the comparison honest.</p><p>Strike rate should be read with role, era, opposition and format. A Test rate and a T20I rate answer different questions. If balls are not recorded, the correct result is unavailable, not zero.</p>','<div><strong>'+num(a1.get('balls'))+'</strong><span>'+left['name']+' ODI balls faced</span></div><div><strong>'+num(a2.get('balls'))+'</strong><span>'+right['name']+' ODI balls faced</span></div><div><strong>'+decimal_stat(a1.get('sr'))+' / '+decimal_stat(a2.get('sr'))+'</strong><span>ODI strike rates · '+left['name']+' / '+right['name']+'</span></div>',1200,760)
    for file in sorted((ROOT/'content/blog').glob('*.json')):
        note=json.loads(file.read_text(encoding='utf-8'))
        if note['date']>TODAY:continue
        figures=note['players']
        if note.get('kind')=='career-comparison':
            fields=note['columns']
            content=''.join('<h2>'+esc(s['heading'])+'</h2><p>'+s['html']+'</p>' for s in note['sections'])
            content+='<h2>The figures behind the infographic</h2>'+table(['Statistic']+[esc(p['name']) for p in figures],[[esc(label)]+[esc(str(p[key])) for p in figures] for key,label in fields],caption=note['scope']+' · checked '+note['data_date'])
            callout=''.join('<div><strong>'+esc(c['value'])+'</strong><span>'+esc(c['label'])+'</span></div>' for c in note['callouts'])
            publish(note['slug'],note['title'],note['description'],note['visual'],note['alt'],note['lead'],content,callout,note['width'],note['height'],date=note['date'],data_date=note['data_date'],methodology=note['methodology'],subjects=figures)
            continue
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
        description='Worm, Manhattan and partnership charts for the India v Australia 2023 ODI World Cup final, drawn from recorded overs.'
        path='/blog/2026-09-12/how-a-chase-looks/'
        article='<div class="daily-note">'+heading(title,'Read the scorecard through its over-by-over and partnership charts.','DAILY NOTE')
        article+=f'<p class="daily-byline"><span>Crickrida</span><span>·</span><time datetime="2026-09-12">2026-09-12</time></p>'+actions()
        article+='<article><p>'+esc(" v ".join(match.get("teams") or []))+' · '+esc(match.get("date"))+' · '+esc(match.get("format"))+'. A worm is the innings total at the end of each over. Dots are wickets. The dashed line is the chase target when both innings are recorded.</p>'
        article+=cw.match_lab(featured)
        article+='<p>'+a(url,'Open the full scorecard')+' · '+a('/studio/','Export a match card in Studio')+'</p><p class="note">Drawn from recorded overs only. Historical result-only matches have no worm.</p></article></div>'
        extra={'headline':title,'datePublished':'2026-09-12','dateModified':'2026-09-12','author':{'@type':'Organization','name':'Crickrida','url':BASE+'/about/'},'publisher':{'@type':'Organization','name':'Crickrida','url':BASE+'/'}}
        page(path,title,description,article,'Article',extra)
        posts.append(('2026-09-12',path,title,description,'','',1200,760))
    posts.sort(key=lambda item:item[0],reverse=True)
    cards=''
    for date,path,title,description,visual,alt,width,height in posts:
        img=f'<img src="/assets/art/blog/{visual}" width="{width}" height="{height}" loading="lazy" alt="{esc(alt)}">' if visual else ''
        cards+='<a class="feature-card daily-index-card" href="'+path+'">'+img+'<span>'+esc(date)+'</span><h2>'+esc(title)+'</h2><p>'+esc(description)+'</p><small>Read this note →</small></a>'
    index=heading('Crickrida daily notes','Small, useful lessons from international cricket records, written with the data in view.','DAILY NOTES')+actions()+'<div class="grid two daily-index-grid">'+cards+'</div><section class="panel"><h2>Keep exploring</h2><p>'+a('/questions/','Cricket questions answered with data')+' · '+a('/records/','International records')+' · '+a('/insights/','Statistical insights')+'</p></section>'
    page('/blog/','Crickrida daily cricket notes','Short, data-backed cricket lessons about international records, player statistics and scorecards.',index,'CollectionPage')

def build_collections(people,matches,pp,mp,gp,groups,careers,arc,hist,editorial=None,all_cards=None,history_home=''):
    ranked=sorted(people.values(),key=lambda p:aggregate(p['career']).get('runs') or 0,reverse=True)
    latest=matches[:8]
    faces=[];icons=[]
    for name in HERO_CAST:
        src=ILLUSTRATIONS.get(name)
        player=next((p for p in people.values() if p.get('name')==name),None)
        if not (src and player):continue
        faces.append((name,src,pp[player['id']]))
        tot=aggregate(player['career']);role=primary_role(player['career'])
        value,label=((tot.get('wickets') or 0),'international wickets') if role=='bowler' else ((tot.get('runs') or 0),'international runs')
        icons.append((name,src,pp[player['id']],f'{value:,}',label,' / '.join(player.get('teams') or [])))
    def career_leader(fmt,metric,gender):
        pool=[p for p in people.values() if p.get('gender')==gender and (p['career'].get(fmt) or {}).get(metric)]
        best=max(pool,key=lambda p:p['career'][fmt][metric],default=None)
        return (best['career'][fmt][metric],f'{fmt} {metric}',best['name'],pp[best['id']]) if best else None
    facts=[f for f in (career_leader('ODI','runs','Men'),career_leader('Test','wickets','Men'),career_leader('ODI','runs','Women')) if f]
    # Player URLs come from the stable route map; published slugs can differ from display names.
    quick=[(p['name'],pp[p['id']]) for name in ('Virat Kohli','Smriti Mandhana') for p in people.values() if p.get('name')==name and p['id'] in pp][:2]
    body=homepage_hero(len(people),len(matches),faces,facts,quick)
    body+=section_jump([('match-centre','Fixtures','calendar'),('icons','Icons','bat'),('results','Results','stumps'),('formats','Formats','ball'),('records-grid','Records','trophy'),('on-this-day','On this day','star'),('home-insights-title','Rivalries','versus'),('featured-scorecard','Scorecard','chart'),('leaders','Leaders','trophy'),('explore','Explore','book')])
    broadcast_data,broadcast_fixtures=load_broadcasts(ROOT,TODAY)
    body+=match_centre(broadcast_fixtures,TODAY)
    body+=stats_band([(len(people),'Player profiles','bat'),(len(matches),'Match records','stumps'),(len(groups['teams']),'National teams','pin'),(3,'Formats covered','ball')])
    body+=icons_rail(icons)
    body+=result_cards(latest,mp,result)
    format_counts={fmt:Counter(m['gender'] for m in matches if m['format']==fmt) for fmt in ('Test','ODI','T20I')}
    format_leaders={}
    for fmt in ('Test','ODI','T20I'):
        format_leaders[fmt]={}
        for gender in ('Men','Women'):
            rows=[]
            for metric,label in (('runs','most runs'),('wickets','most wickets')):
                lead=career_leader(fmt,metric,gender)
                if lead:rows.append((label,lead[2],lead[0],lead[3]))
            format_leaders[fmt][gender]=rows
    format_links={fmt:[('Records',f'/records/men/{fmt.lower()}/most-runs/'),('Matches',f'/matches/?format={fmt}'),('Highest scores',f'/records/men/{fmt.lower()}/highest-scores/')] for fmt in ('Test','ODI','T20I')}
    body+=format_trio(format_counts,format_leaders,format_links)
    heads=headline_records(matches,all_cards or {},people)
    tiles=[]
    for fmt in ('Test','ODI','T20I'):
        for kind,slot in (('Highest score','score'),('Best bowling','bowling')):
            entries=[]
            for gender in ('Men','Women'):
                rec=(heads.get((gender,fmt)) or {}).get(slot)
                if not rec:continue
                v1,v2,pid,team,opp,m=rec
                value=f'{v1}{"*" if slot=="score" and v2 else ""}' if slot=='score' else f'{v1}/{-v2}'
                entries.append((gender,value,people[pid]['name'],f'{team} v {opp} · {m["date"][:4]}',f'/records/{gender.lower()}/{fmt.lower()}/{"highest-scores" if slot=="score" else "best-bowling-innings"}/'))
            tiles.append((fmt,kind,entries))
    body+=records_grid(tiles)
    body+='<div id="on-this-day" class="arena-anchor">'+history_home+'</div>'
    official_teams=load_team_records();official_innings=load_innings_records()
    h2h_official=official_h2h(official_teams,'India','Australia')
    h2h_rows=[]
    if h2h_official:
        for fmt in ('Test','ODI','T20I'):
            row=h2h_official.get(fmt)
            if row:h2h_rows.append((fmt,row['played'],row['left_wins'],row['right_wins'],row['other']))
    body+=homepage_insights(matches,mp,people,gp,h2h_rows or None)
    featured=cw.showcase_card(all_cards or {})
    if featured:body+='<div id="featured-scorecard" class="arena-anchor">'+cw.homepage_lab(featured,mp.get(featured['match']['id'],'/matches/'))+'</div>'
    boards=[]
    for metric,title in [('runs','Run makers'),('wickets','Wicket takers')]:
        leaders=sorted(ranked,key=lambda p:aggregate(p['career']).get(metric) or 0,reverse=True)[:10]
        boards.append((metric,title,[(p['name'],pp[p['id']],' / '.join(p['teams']),aggregate(p['career']).get(metric) or 0) for p in leaders]))
    body+=leaders_race(boards)
    body+=explore_bento([('/records/','trophy','RECORDS','Every record, by format','Career, innings, team and partnership records.'),('/compare/','compare','PLAYER COMPARISON','Compare two careers','Pick a format and put two players side by side.'),('/teams/','pin','TEAM RECORDS','Results by team','Opponent, venue, toss and year splits.'),('/world-cup/','star','WORLD CUP','World Cup records','Winners, finals, scorecards and tournament records.'),('/head-to-head/','versus','HEAD-TO-HEAD','Team rivalries','Format-by-format results between the twelve teams.'),('/grounds/','pin','GROUNDS','Venue records','How every ground plays, format by format.'),('/studio/','chart','STUDIO','Build your own chart','Query the archive and export the visual.'),('/where-to-watch/','tv','WATCH IN INDIA','TV and streaming guide','Channels and OTT for every upcoming series.')])
    body+='<p class="note">Career data updated '+careers['meta']['checked_at'][:10]+'. Historical result-only matches are labeled. '+a('/methodology/','Understand coverage →')+'</p>'
    page('/','Cricket stats, player records & scorecards','Crickrida: international cricket career statistics, player comparisons, match scorecards, team records and analysis.',body,'WebSite')
    page('/where-to-watch/','Live cricket telecast and streaming in India','Today and upcoming international cricket matches on Indian television and official OTT streaming platforms.',watch_page(broadcast_data,broadcast_fixtures,TODAY),'CollectionPage')
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
    ipl_venues=le.load(ROOT,'ipl-venues.json');wc_teams=le.load(ROOT,'t20wc-teams.json')
    ipl_grounds=le.ground_index(ipl_venues,set(groups['grounds']))
    for kind,g in groups.items():
        title={'teams':'International teams','grounds':'Cricket grounds','series':'International series'}[kind]
        all_years=sorted({m['date'][:4] for ms in g.values() for m in ms},reverse=True)
        listing=heading(title,'Browse international results and follow the links to individual matches.')+f'<form class="filters entity-index-filter" data-entity-index-filter="{kind}"><div class="filter-intro"><strong>Filter the directory</strong><span id="entity-index-count">{len(g):,} entries</span></div>'+options('gender',['Men','Women'])+options('format',['Test','ODI','T20I'])+options('year',all_years,'Year')+f'<label>From year<input name="from" type="number" min="{all_years[-1]}" max="{all_years[0]}" inputmode="numeric"></label><label>To year<input name="to" type="number" min="{all_years[-1]}" max="{all_years[0]}" inputmode="numeric"></label><button class="primary">Apply filters</button><button type="reset">Reset</button></form><div class="grid three" id="entity-directory-results">'
        for name,ms in sorted(g.items(),key=lambda item:len(item[1]),reverse=True):
            span=f'{ms[-1]["date"][:4]} to {ms[0]["date"][:4]}'
            if kind=='grounds' and ground_place(GROUND_FACTS.get(name)):span=ground_place(GROUND_FACTS.get(name))+' · '+span
            listing+=f'<a class="feature-card entity-index-card" data-entity-card="{esc(name)}" href="{gp[kind][name]}"><h2>{esc(name)}</h2><p>{len(ms):,} recorded matches</p><small>{esc(span)}</small></a>'
            extra={'breadcrumb_name':name}
            counts=Counter(m['format'] for m in ms)
            formats=[f for f in ('Test','ODI','T20I') if counts.get(f)]
            league_tab=None
            if kind=='grounds' and name in ipl_grounds:
                venue=ipl_grounds[name];league_tab=('ipl','IPL',venue['matches'],le.ground_panel(name,venue,ipl_venues.get('meta') or {},pp))
            elif kind=='teams' and name in (wc_teams.get('teams') or {}) and any(m['gender']=='Men' and m['format']=='T20I' for m in ms):
                team=wc_teams['teams'][name];league_tab=('t20wc','T20 World Cup',team['matches'],le.team_panel(name,team,wc_teams.get('meta') or {},pp))
            switch=entity_switch(formats,counts,{'keys':[league_tab[0]],'switch':le.switch_item(*league_tab[:3])} if league_tab else None)
            from urllib.parse import urlencode
            query={'team':name} if kind=='teams' else {'q':name}
            tail='<section class="panel pf-block" id="recent-matches"><h2>Recent recorded matches</h2>'+entity_filter_form(kind,name,ms)+'<div id="entity-results" aria-live="polite">'+match_table(ms,mp,50)+'</div></section><p class="pf-links">'+a('/matches/?'+urlencode(query),'Search all matching matches →')+' · '+a('/questions/','Cricket questions')+'</p>'
            overview_open='<section class="fmt-panel fmt-overview" id="overview" data-fmt-panel="overview" aria-label="Overview">'
            if kind=='teams':
                totals=team_totals(ms,name)
                title1,description=team_seo(name,totals)
                body=heading(name,f'{totals["matches"]:,} recorded matches · {totals["first"][:4]} to {totals["last"][:4]}','TEAMS')+actions()+switch+overview_open
                body+=official_team_panel(name,official_teams,table)
                body+=team_glance(name,totals)+cw.result_decades(ms,name)
                rivals=defaultdict(Counter)
                for m in ms:
                    opp=next(t for t in m['teams'] if t!=name);rivals[opp]['played']+=1;rivals[opp]['wins']+=int(m['outcome'].get('winner')==name);rivals[opp]['losses']+=int(bool(m['outcome'].get('winner')) and m['outcome'].get('winner')!=name)
                body+='<section class="panel pf-block"><h2>Head-to-head results</h2>'+table(['Opponent','Matches','Wins','Losses','Other'],[[a(h2h_path(name,opp),opp),str(s['played']),str(s['wins']),str(s['losses']),str(s['played']-s['wins']-s['losses'])] for opp,s in sorted(rivals.items(),key=lambda x:x[1]['played'],reverse=True)],caption=name+' against each full-member opponent, all formats')+'</section>'
                squad=[p for p in ranked if name in p['teams']]
                body+='<section class="panel pf-block"><h2>Explore players</h2>'+table(['Player','Gender','Career runs','Career wickets'],[[a(pp[p['id']],p['name']),p['gender'],num(aggregate(p['career']).get('runs')),num(aggregate(p['career']).get('wickets'))] for p in squad[:30]],caption=name+' players by career runs')+'</section>'
                faq_html,faq_schema=team_faq(name,totals,gp[kind][name])
                body+=faq_html+tail+'</section>'
                for fmt in formats:body+=team_format_panel(name,fmt,[m for m in ms if m['format']==fmt],all_cards or {},people,pp,mp,h2h_path)
                if league_tab:body+=league_tab[3]
                extra.update({'mainEntity':team_schema(name,gp[kind][name],description),'faq':faq_schema})
            elif kind=='grounds':
                totals=ground_totals(ms);facts=GROUND_FACTS.get(name,{})
                title1,description=ground_seo(name,totals,facts,ipl_grounds[name]['matches'] if name in ipl_grounds else 0)
                body=ground_masthead(name,totals,facts,actions())+switch+overview_open
                body+=ground_glance(name,totals)+entity_visuals(kind,name,ms)
                body+='<section class="panel pf-block" id="career-records"><h2>Recorded matches by format</h2>'+table(['Format','Men','Women'],[[fmt,str(sum(m['format']==fmt and m['gender']=='Men' for m in ms)),str(sum(m['format']==fmt and m['gender']=='Women' for m in ms))] for fmt in ['Test','ODI','T20I']],caption=name+' matches by format and gender')+'</section>'
                faq_html,faq_schema=ground_faq(name,totals)
                body+=faq_html+tail+'</section>'
                for fmt in formats:body+=ground_format_panel(name,fmt,[m for m in ms if m['format']==fmt],all_cards or {},people,pp,mp,gp['teams'])
                if league_tab:body+=league_tab[3]
                extra.update({'mainEntity':ground_schema(name,gp[kind][name],description,facts),'faq':faq_schema})
            else:
                title1=name+' match records'
                description=f'{name}: international cricket results by edition, scorelines, leading players and linked scorecards.'
                body=heading(name,f'{len(ms):,} recorded matches · {ms[-1]["date"][:4]} to {ms[0]["date"][:4]}',kind.upper())+actions()+switch+overview_open+entity_visuals(kind,name,ms)
                body+='<section class="panel pf-block"><h2>Recorded matches by format</h2>'+table(['Format','Men','Women'],[[fmt,str(sum(m['format']==fmt and m['gender']=='Men' for m in ms)),str(sum(m['format']==fmt and m['gender']=='Women' for m in ms))] for fmt in ['Test','ODI','T20I']],caption=name+' matches by format')+'</section>'
                body+=tail+'</section>'
                for fmt in formats:body+=series_format_panel(name,fmt,[m for m in ms if m['format']==fmt],all_cards or {},people,pp,mp)
            page(gp[kind][name],title1,description,body,'CollectionPage',extra)
        page('/'+kind+'/',title,'Explore '+title.lower()+' and their international match records.',listing+'</div>','CollectionPage')
    print('Building records hub...',flush=True)
    published_records=set()
    snapshot=careers['meta']['checked_at'][:10]
    def scope_nav(key):
        return '<nav class="scope-nav" aria-label="Leaderboard scope">'+''.join(a(f'/records/{g.lower()}/{f.lower()}/{key}/',g+' · '+f) for g in ('Men','Women') for f in ('Test','ODI','T20I') if (g,f,key) in published_records)+'</nav>'
    record_pages=[]
    for gender in ['Men','Women']:
        for fmt in ['Test','ODI','T20I']:
            entries=[{'id':p['id'],'name':p['name'],'url':pp[p['id']],'teams':p['teams'],**{k:v for k,v in p['career'][fmt].items() if k not in ['source','sources','disciplines']}} for p in ranked if p['gender']==gender and fmt in p['career']]
            feed=f'/data/records-{gender.lower()}-{fmt.lower()}.json';dump(feed,entries)
            for key,field,label,lower,minimum,kind in CAREER_METRICS:
                head,body,qualified=career_table(field,label,kind,entries,minimum,lower,pp)
                if len(body)<3:continue
                path=f'/records/{gender.lower()}/{fmt.lower()}/{key}/'
                minimum_field=MINIMUM_FIELD.get(field,'innings');minimum_label=MINIMUM_LABEL[minimum_field]
                qualification=f'Minimum {minimum} '+minimum_label if minimum else 'All recorded careers, no minimum qualification'
                content=f'<form class="filters" data-records="{feed}" data-field="{field}" data-kind="{kind}" data-label="{esc(label)}" data-minimum-field="{minimum_field}" data-lower="{str(lower).lower()}"><label>Minimum {minimum_label}<input name="minimum" type="number" min="0" value="{minimum}"></label><label>Player or team<input name="q"></label><button class="primary">Apply</button><button type="reset">Reset</button></form><div id="record-results" aria-live="polite">'+records_table(head,body,f'{gender} {fmt}: {label}',left=(2,3,4))+'</div>'
                top=qualified[0] if qualified else None
                lede=(esc(top['name'])+' leads with '+(f"{top[field]:.2f}" if isinstance(top[field],float) else f"{top[field]:,}")+'. ') if top else ''
                body_html=heading(f'{gender} {fmt}: {label}',qualification+'. Official career snapshot '+snapshot+'.','CAREER RECORD')+'__SCOPE_NAV__'+key+'__'+actions()+cw.leader_bars([(p['name'],p[field]) for p in qualified[:10]],f'{label} · {gender} {fmt}')+content+'<p class="pf-fine">Tied figures share a rank. The table lists up to 100 qualifying careers; the filters search every career in this format.</p>'
                record_pages.append((path,f'{gender} {fmt} {label.lower()} records',f'{label} in {gender.lower()} {fmt} cricket. {lede}{qualification}. Career leaderboard with ties, spans and player profiles.',body_html))
                published_records.add((gender,fmt,key))
            bats,bowls,stands=innings_rows(matches,all_cards or {},people,gender,fmt)
            totals,wins=team_rows(matches,all_cards or {},gender,fmt)
            for key,label,kind in INNINGS_RECORDS:
                rows={'bat':bats,'bowl':bowls,'stand':stands,'team':totals if not key.startswith('biggest') else wins}.get(kind)
                if kind=='year':rows=bats if key=='most-runs-in-a-year' else bowls
                if not rows:continue
                head,body,feed_rows,left=innings_record_table(key,rows,people,pp,mp)
                if len(body)<3:continue
                path=f'/records/{gender.lower()}/{fmt.lower()}/{key}/'
                feed=f'/data/records/{gender.lower()}-{fmt.lower()}-{key}.json';dump(feed,{'head':[h if isinstance(h,str) else h[0] for h in head],'rows':feed_rows})
                content=f'<form class="filters" data-record-rows="{feed}"><label>Team<select name="t"><option value="">All</option></select></label><label>Opponent<select name="o"><option value="">All</option></select></label><label>Ground<select name="g"><option value="">All</option></select></label><label>Year<select name="d"><option value="">All</option></select></label><button class="primary">Apply</button><button type="reset">Reset</button></form><div id="record-results" aria-live="polite">'+records_table(head,body,f'{gender} {fmt}: {label}',left=left)+'</div>'
                first=body[0]
                body_html=heading(f'{gender} {fmt}: {label}',f'{CATEGORY_LABEL[kind]} record from available scorecards, {len(feed_rows):,} qualifying entries.',CATEGORY_LABEL[kind].upper()+' RECORD')+'__SCOPE_NAV__'+key+'__'+actions()+content+'<p class="pf-fine">Available scorecards only; the twelve-team archive is complete from 2001 and partial before. Tied figures share a rank.</p>'
                record_pages.append((path,f'{gender} {fmt} {label.lower()}',f'{label} in {gender.lower()} {fmt} cricket from verified scorecards, ranked with opponent, ground and date.',body_html))
                published_records.add((gender,fmt,key))
    for path,title,description,body_html in record_pages:
        key=path.rstrip('/').rsplit('/',1)[-1]
        page(path,title,description,body_html.replace('__SCOPE_NAV__'+key+'__',scope_nav(key),1),'CollectionPage')
    records_body=heading('Cricket records','Career, innings, team and partnership records for men and women in Tests, ODIs and T20Is.','RECORDS')+records_index(published_records)
    page('/records/','International cricket records','Test, ODI and T20I records for men and women: career leaderboards, highest scores, best bowling, team totals, partnerships and calendar-year records.',records_body,'CollectionPage')
    # The comparison tool reads only the selected players' summary and analytics files.
    choices=''.join(f'<option value="{pp[p["id"]]}">{esc(p["name"])} · {p["gender"]}</option>' for p in ranked[:80])
    compare=heading('Compare cricket careers','Two or three players, one format at a time. Official careers first; recorded innings for year-by-year and opposition views.','PLAYER COMPARISON')+actions()
    compare+=f'<form id="compare-form" class="filters cmp-form"><label>Find a player<input id="compare-search" placeholder="Type a name to add options"></label><label>Player A<select name="a">{choices}</select></label><label>Player B<select name="b">{choices}</select></label><label>Player C (optional)<select name="c"><option value="">None</option>{choices}</select></label>'+options('format',['Test','ODI','T20I'])+'<label>Data scope<select name="basis"><option value="career">Official careers</option><option value="archive">Recorded innings</option></select></label><label>From year (innings)<input type="number" name="from" min="1877" max="2100"></label><label>To year (innings)<input type="number" name="to" min="1877" max="2100"></label><label>Opponent (innings)<input name="opponent" placeholder="e.g. Australia"></label><label>Venue setting (innings)<select name="setting"><option value="">All</option><option>Home</option><option>Away</option><option>Neutral</option><option>Unknown</option></select></label><label>Last N batting innings<select name="recent"><option value="">All</option><option>10</option><option>20</option><option>50</option></select></label><label>Minimum batting innings<input type="number" name="minimum" min="0" value="0"></label><button class="primary">Compare</button></form><div id="compare-result" aria-live="polite"><p class="pf-fine">Choose players and a format, then compare.</p></div>'
    compare+='<section class="panel pf-block"><h2>Featured comparisons</h2>'+comparison_cards(COMPARE_CARDS)+'</section>'
    page('/compare/','Compare cricket players','Compare two or three international cricketers by format: runs, averages, strike rates, hundreds, wickets, year-by-year overlays and opposition splits.',compare)
    entity_index=[{'name':name,'url':url,'kind':kind} for kind,g in gp.items() for name,url in g.items()];dump('/data/entity-index.json',entity_index)
    page('/tools/','Cricket tools: matchups, phases, studio, fantasy and quiz','Free cricket tools that run in your browser: batter v bowler matchups, phase analysis, a chart studio, fantasy projections and a player quiz.',tp.tools_markup(a),'CollectionPage')
    page('/matchups/','Batter v bowler matchups','Every ball between any batter and bowler in Tests, ODIs, T20Is, the IPL and the T20 World Cup: balls, runs, strike rate, dismissals and dot balls.',tp.matchups_markup(),'WebApplication',{'applicationCategory':'SportsApplication'})
    page('/phases/','Powerplay, middle and death overs analysis','Run rate, wickets, boundaries and dot balls by phase and over for T20Is, ODIs, the IPL and the T20 World Cup, with phase leaders and grounds.',tp.phases_markup(),'WebApplication',{'applicationCategory':'SportsApplication'})
    page('/fantasy/','Fantasy cricket picks from form and ground records','Projected fantasy points and a suggested XI for any two IPL or T20I teams, from recent form and ground records.',tp.fantasy_markup(),'WebApplication',{'applicationCategory':'SportsApplication'})
    page('/quiz/','Guess the cricketer quiz','Name the player from their career numbers: IPL, T20 World Cup, Tests, ODIs and T20Is, men and women.',tp.quiz_markup(),'WebApplication',{'applicationCategory':'GameApplication'})
    for mode,rows in tp.quiz_pools(ROOT,pp,fullname).items():dump(f'/data/quiz/{mode}.json',rows)
    page('/studio/','International cricket content studio','Create and export publication-ready cricket visuals from verified career, match and innings data.',studio_markup(a),'SoftwareApplication',{'applicationCategory':'DesignApplication'})
    page('/embed/','Crickrida player card','An embeddable international cricket career summary.','<div id="embed-result" aria-live="polite">Loading career card…</div>',noindex=True)
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
    page('/world-cup/mens-t20/dashboard/','Men\'s T20 World Cup analysis dashboard','Interactive ball-by-ball analysis of every ICC Men\'s T20 World Cup edition from 2007 to 2026, including team wins, phase scoring and player leaders.',dashboard_markup(),'Dataset',{'breadcrumb_name':"Men's T20 World Cup dashboard"})

if __name__=='__main__': main()
