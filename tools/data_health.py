"""Crawlable coverage summaries, independent of the build date."""
from collections import defaultdict
import json
from pathlib import Path
from profile_research import esc, table, aggregate_rows, value

TABLE_NOTES={
    'careers':'Official international career-format snapshots against all recognised opposition, plus IPL careers from ball-by-ball data.',
    'ball_matches':'Every match with ball-by-ball data: Tests, ODIs and T20Is for men and women, the IPL and the T20 World Cup.',
    'ball_players':'Cricsheet player ids with names, teams and a link to the player page where one exists.',
    'ball_matchups':'Balls faced, runs, dismissals credited to the bowler, dots and boundaries for every batter and bowler pair, by competition and year.',
    'ball_phase_players':'Batting and bowling by phase, player, team and year. T20 phases are overs 1 to 6, 7 to 15 and 16 to 20; ODI phases 1 to 10, 11 to 40 and 41 to 50.',
    'ball_phase_teams':'Every limited-overs team innings by phase: legal balls, runs including extras, wickets, dots and boundaries.',
    'ball_overs':'Every limited-overs team innings over by over.',
    'ball_fantasy':'Fantasy points for every player in every IPL and T20I match, with the batting, bowling and fielding parts.',
}


def profile_coverage(player, rows):
    if not rows: return ''
    body='<details class="profile-coverage"><summary>Scorecard coverage and data completeness</summary><p class="note">Career snapshots and available scorecards have different scopes. These counts describe recorded batting or bowling innings, not every international appearance.</p>'
    entries=[]
    for fmt in ('Test','ODI','T20I'):
        sample=[r for r in rows if r['format']==fmt]
        if not sample:continue
        s=aggregate_rows(sample);bat=[r for r in sample if r.get('position') is not None or r.get('runs') is not None]
        entries.append([fmt,str(s['matches']),str(len(bat)),str(sum(r.get('balls') is not None for r in bat)),str(sum(r.get('fours') is not None and r.get('sixes') is not None for r in bat)),min(r['date'] for r in sample),max(r['date'] for r in sample)])
    return body+table(['Format','Matches','Bat inns','Balls recorded','Boundaries recorded','First scorecard','Latest scorecard'],entries,'Player archive coverage')+'</details>'

def coverage_page(matches, cards, careers, page):
    groups=defaultdict(list)
    for m in matches:groups[m['gender'],m['format']].append(m)
    rows=[]
    for (gender,fmt),ms in sorted(groups.items()):
        n=sum(bool(cards.get(m['id'],{}).get('innings')) for m in ms)
        rows.append([gender+' · '+fmt,str(len(ms)),str(n),str(len(ms)-n),min(m['date'] for m in ms),max(m['date'] for m in ms)])
    body='<section class="page-head"><span class="eyebrow">THE RECORD BEHIND THE NUMBERS</span><h1>International cricket data coverage</h1><p>See which records are available, when they were checked and where gaps remain.</p></section>'
    body+='<p>Baseline career snapshot checked: <strong>'+esc(careers['meta'].get('checked_at','')[:10])+'</strong>. Newer checks appear on individual profiles. The latest archived match is not a guarantee that all earlier matches are complete.</p>'
    body+=table(['Scope','Match records','With innings','Without innings','First match','Latest match'],rows,'Coverage by gender and international format')
    body+='<p class="note">Records without innings include abandoned matches and unavailable scorecards. An innings record may still have missing individual fields; its presence does not establish complete coverage.</p>'
    fields=('runs','balls','avg','sr','fours','sixes','wickets','bowlAvg','econ','bowlSr')
    entries=[]
    for gender in ('Men','Women'):
        for fmt in ('Test','ODI','T20I'):
            ss=[p['formats'][fmt] for p in careers['players'] if p['gender']==gender and fmt in p['formats']]
            entries.append([gender+' · '+fmt,str(len(ss))]+[str(sum(s.get(k) is not None for s in ss)) for k in fields])
    body+='<section class="panel"><h2>Career fields recorded</h2><p>Counts of career-format records with each field present. A missing rate may be unrecorded or mathematically not applicable; these counts do not equate the two.</p>'+table(['Scope','Careers','Runs','Balls','Avg','SR','4s','6s','Wickets','Bowl avg','Econ','Bowl SR'],entries,'Non-null career fields')+'</section>'
    body+='<section class="panel"><h2>What the figures mean</h2><p>Official career totals retain all recognised internationals. Match browsing covers the twelve full-member national teams. Unknown historical balls faced and boundaries remain unrecorded; partial scorecards cannot supply complete career rates.</p><p>Every release reconciles player innings with scorecards, checks internal links and preserves stable player URLs. <a href="/methodology/">Calculation definitions</a> · <a href="/corrections/">Report a correction</a> · <a href="/studio/">Explore the datasets</a></p></section>'
    page('/data-coverage/','International cricket data coverage and freshness','Coverage by gender and format, scorecard dates and completeness of player career statistics.',body,'CollectionPage')
    manifest_path=Path(__file__).resolve().parents[1]/'analytics_lake/manifest.json'
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        catalog='<section class="page-head"><span class="eyebrow">CRICKRIDA DATA</span><h1>International cricket datasets</h1><p>Download the tables used by the analysis Studio, with their scope and field definitions.</p></section><p>Career snapshot: '+esc(str(manifest.get('career_checked_at','Unknown'))[:10])+'. Archive: '+esc(manifest.get('match_date_from',''))+' to '+esc(manifest.get('match_date_to',''))+'.</p>'
        for key,info in manifest['tables'].items():
            url='/data/lake/'+info['file']
            catalog+='<section class="panel"><h2>'+esc(key.replace('_',' ').title())+'</h2><p>'+str(info['rows'])+' rows · <a href="'+url+'" download>Download Parquet</a></p><p class="note">'+esc(TABLE_NOTES.get(key,'Available records within the twelve-team match archive, plus every IPL match from ball-by-ball data. Super overs are excluded from innings tables.'))+'</p><details><summary>Columns and types</summary>'+table(['Column','Type'],[[esc(c['name']),esc(c['type'])] for c in info['columns']],'Dataset columns')+'</details></section>'
        catalog+='<p>Ball-derived data: <a href="https://cricsheet.org/">Cricsheet</a>. Downloads retain the same coverage limits as the site. <a href="/methodology/">Definitions</a> · <a href="/studio/">Open Studio</a></p>'
        page('/datasets/','International cricket datasets for analysis','Download career, match, batting and bowling innings tables with field definitions and data coverage.',catalog,'Dataset',{'creator':{'@type':'Organization','name':'Crickrida'},'distribution':[{'@type':'DataDownload','encodingFormat':'application/vnd.apache.parquet','contentUrl':'https://crickrida.com/data/lake/'+t['file']} for t in manifest['tables'].values()]})
