"""Build compact, browser-queryable Parquet tables for Crickrida Studio."""
from __future__ import annotations
import hashlib, json, shutil
from datetime import datetime, timezone
from pathlib import Path
import duckdb, pyarrow as pa
from cricket_scope import load_cards, publication_data
from build_site import fullname
from build_ball_lake import build as build_ball

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'analytics_lake'

def write_table(name,rows):
    target=OUT/f'{name}.parquet';table=rows if isinstance(rows,pa.Table) else pa.Table.from_pylist(rows);con=duckdb.connect()
    con.register('source_rows',table);con.execute(f"COPY source_rows TO '{target.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 100000)");con.close()
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    versioned=OUT/(name+'-'+digest[:16]+'.parquet');shutil.copy2(target,versioned)
    for old in OUT.glob(name+'-*.parquet'):
        if old!=versioned:old.unlink()
    return {'file':versioned.name,'rows':table.num_rows,'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'columns':[{'name':f.name,'type':str(f.type)} for f in table.schema]}

def ipl_careers(people):
    path=ROOT/'data/leagues/ipl.json'
    if not path.exists():return []
    rows=[]
    for pid,p in json.loads(path.read_text(encoding='utf-8'))['players'].items():
        c=p['career'];seasons=[s['edition'] for s in p.get('seasons') or []]
        if not c.get('matches'):continue
        outs,balls,bb,wk=c.get('outs') or 0,c.get('balls') or 0,c.get('bowl_balls') or 0,c.get('wickets') or 0
        rate=lambda a,b,f=1:round(a*f/b,2) if b else None
        rows.append({'player_id':pid,'player':people.get(pid,{}).get('name') or p['name'],'gender':'Men','teams':' / '.join(t['team'] for t in p.get('teams') or []),'format':'IPL',
                     'first_year':seasons[0] if seasons else None,'last_year':seasons[-1] if seasons else None,'matches':c['matches'],'innings':c.get('innings'),'outs':outs,
                     'notouts':(c.get('innings') or 0)-outs,'runs':c.get('runs'),'balls':balls,'highest':c.get('hs') if c.get('innings') else None,'avg':rate(c.get('runs') or 0,outs),
                     'sr':rate(c.get('runs') or 0,balls,100),'hundreds':c.get('hundreds'),'fifties':c.get('fifties'),'ducks':c.get('ducks'),'fours':c.get('fours'),'sixes':c.get('sixes'),
                     'bowling_innings':c.get('bowl_innings'),'legal':bb,'maidens':None,'conceded':c.get('conceded'),'wickets':wk,'bowlAvg':rate(c.get('conceded') or 0,wk),
                     'econ':rate(c.get('conceded') or 0,bb,6),'bowlSr':rate(bb,wk),'four_w':c.get('four_w'),'five_w':c.get('five_w'),'ten_w':None,'catches':c.get('catches'),
                     'stumpings':c.get('stumpings'),'dismissals':(c.get('catches') or 0)+(c.get('stumpings') or 0)})
    return rows

def main():
    OUT.mkdir(exist_ok=True);archive,careers,history=publication_data(ROOT)
    people={p['id']:p for p in archive['players']}
    for p in careers['players']:people[p['id']]={**people.get(p['id'],{}),**p}
    for p in people.values():p['name']=fullname(p)
    matches=sorted(archive['matches']+history['matches'],key=lambda m:(m['date'],m['id']));cards=load_cards(ROOT,matches,people)
    match_rows=[]
    for m in matches:
        o=m.get('outcome',{});margin=o.get('by',{})
        match_rows.append({'match_id':m['id'],'date':m['date'],'year':int(m['date'][:4]),'format':m['format'],'gender':m['gender'],'team_1':m['teams'][0],'team_2':m['teams'][1],'winner':o.get('winner'),'result':o.get('result'),'margin_runs':margin.get('runs'),'margin_wickets':margin.get('wickets'),'venue':m.get('venue'),'city':m.get('city'),'series':m.get('event'),'coverage':m.get('coverage','scorecard' if m['id'] in cards else 'result-only')})
    career_rows=[]
    fields=('matches','innings','outs','notouts','runs','balls','highest','avg','sr','hundreds','fifties','ducks','fours','sixes','bowling_innings','legal','maidens','conceded','wickets','bowlAvg','econ','bowlSr','four_w','five_w','ten_w','catches','stumpings','dismissals')
    for p in careers['players']:
        for fmt,s in p.get('formats',{}).items():career_rows.append({'player_id':p['id'],'player':fullname(p),'gender':p['gender'],'teams':' / '.join(p['teams']),'format':fmt,'first_year':p.get('first'),'last_year':p.get('last'),**{k:s.get(k) for k in fields}})
    batting=[];bowling=[]
    for mid,card in cards.items():
        m=card['match']
        for n,inn in enumerate(card.get('innings',[]),1):
            if inn.get('super_over'):continue
            opp=next((t for t in m['teams'] if t!=inn['team']),None)
            for b in inn.get('bowling',[]):
                bowling.append({'match_id':mid,'date':m['date'],'year':int(m['date'][:4]),'format':m['format'],'gender':m['gender'],'innings_number':n,'player_id':b['id'],'player':people.get(b['id'],{}).get('name',b['id']),'team':opp,'opponent':inn['team'],'venue':m.get('venue'),'wickets':b.get('wickets'),'legal':b.get('balls'),'conceded':b.get('runs'),'maidens':b.get('maidens')})
            for pos,b in enumerate(inn.get('batting',[]),1):batting.append({'match_id':mid,'date':m['date'],'year':int(m['date'][:4]),'format':m['format'],'gender':m['gender'],'innings_number':n,'player_id':b['id'],'player':people.get(b['id'],{}).get('name',b['id']),'team':inn['team'],'opponent':opp,'venue':m.get('venue'),'position':pos,'runs':b.get('runs'),'balls':b.get('balls'),'fours':b.get('fours'),'sixes':b.get('sixes'),'out':b.get('out'),'dismissal':b.get('dismissal')})
    # Ball-by-ball tables for Matchups, Phases and Fantasy: every international format, the IPL and the T20 World Cup.
    routes_path=ROOT/'_site/data/routes.json'
    routes=json.loads(routes_path.read_text(encoding='utf-8')).get('players',{}) if routes_path.exists() else {}
    ball_tables,studio=build_ball(write_table,people_names={pid:p['name'] for pid,p in people.items()},routes=routes)
    # Studio gains the IPL as a fourth format: scorecards from the same ball-by-ball pass, careers from the league snapshot.
    match_rows+=studio['matches'];batting+=studio['batting'];bowling+=studio['bowling']
    career_rows+=ipl_careers(people)
    tables={'matches':write_table('matches',match_rows),'careers':write_table('careers',career_rows),'batting_innings':write_table('batting_innings',batting),'bowling_innings':write_table('bowling_innings',bowling)}
    tables.update(ball_tables)
    now=datetime.now(timezone.utc);manifest={'name':'Crickrida Analytics Lake','version':now.strftime('%Y%m%d%H%M%S'),'generated_at':now.isoformat(),'career_checked_at':careers['meta'].get('checked_at'),'match_date_from':min(m['date'] for m in matches),'match_date_to':max(m['date'] for m in matches),'scope':'Official international careers; twelve-team match archive; ball-by-ball internationals, IPL and T20 World Cup','license_note':'Cricsheet attribution applies to ball-derived records.','tables':tables}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps({k:{'rows':v['rows'],'bytes':v['bytes']} for k,v in tables.items()},indent=2))
if __name__=='__main__':main()
