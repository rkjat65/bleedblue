"""Build compact, browser-queryable Parquet tables for Cricket Wicket Studio."""
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
import duckdb, pyarrow as pa
from cricket_scope import load_cards, publication_data
from build_site import fullname

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'analytics_lake'

def write_table(name,rows):
    target=OUT/f'{name}.parquet';table=pa.Table.from_pylist(rows);con=duckdb.connect()
    con.register('source_rows',table);con.execute(f"COPY source_rows TO '{target.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 100000)");con.close()
    return {'file':target.name,'rows':len(rows),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'columns':[{'name':f.name,'type':str(f.type)} for f in table.schema]}

def main():
    OUT.mkdir(exist_ok=True);archive,careers,history=publication_data(ROOT)
    people={p['id']:p for p in archive['players']}
    for p in careers['players']:people.setdefault(p['id'],p)
    matches=sorted(archive['matches']+history['matches'],key=lambda m:(m['date'],m['id']));cards=load_cards(ROOT,matches,people)
    match_rows=[]
    for m in matches:
        o=m.get('outcome',{});margin=o.get('by',{})
        match_rows.append({'match_id':m['id'],'date':m['date'],'year':int(m['date'][:4]),'format':m['format'],'gender':m['gender'],'team_1':m['teams'][0],'team_2':m['teams'][1],'winner':o.get('winner'),'result':o.get('result'),'margin_runs':margin.get('runs'),'margin_wickets':margin.get('wickets'),'venue':m.get('venue'),'city':m.get('city'),'series':m.get('event'),'coverage':m.get('coverage','scorecard' if m['id'] in cards else 'result-only')})
    career_rows=[]
    fields=('matches','innings','notouts','runs','balls','highest','avg','sr','hundreds','fifties','ducks','fours','sixes','bowling_innings','legal','maidens','conceded','wickets','bowlAvg','econ','bowlSr','four_w','five_w','ten_w','catches','stumpings','dismissals')
    for p in careers['players']:
        for fmt,s in p.get('formats',{}).items():career_rows.append({'player_id':p['id'],'player':fullname(p),'gender':p['gender'],'teams':' / '.join(p['teams']),'format':fmt,'first_year':p.get('first'),'last_year':p.get('last'),**{k:s.get(k) for k in fields}})
    batting=[]
    for mid,card in cards.items():
        m=card['match']
        for n,inn in enumerate(card.get('innings',[]),1):
            if inn.get('super_over'):continue
            opp=next((t for t in m['teams'] if t!=inn['team']),None)
            for pos,b in enumerate(inn.get('batting',[]),1):batting.append({'match_id':mid,'date':m['date'],'year':int(m['date'][:4]),'format':m['format'],'gender':m['gender'],'innings_number':n,'player_id':b['id'],'player':people.get(b['id'],{}).get('name',b['id']),'team':inn['team'],'opponent':opp,'venue':m.get('venue'),'position':pos,'runs':b.get('runs'),'balls':b.get('balls'),'fours':b.get('fours'),'sixes':b.get('sixes'),'out':b.get('out'),'dismissal':b.get('dismissal')})
    tables={'matches':write_table('matches',match_rows),'careers':write_table('careers',career_rows),'batting_innings':write_table('batting_innings',batting)}
    now=datetime.now(timezone.utc);manifest={'name':'Cricket Wicket Analytics Lake','version':now.strftime('%Y%m%d%H%M%S'),'generated_at':now.isoformat(),'scope':'Official international cricket','license_note':'Cricsheet attribution applies to ball-derived records.','tables':tables}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps({k:{'rows':v['rows'],'bytes':v['bytes']} for k,v in tables.items()},indent=2))
if __name__=='__main__':main()
