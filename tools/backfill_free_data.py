"""Resume verified public career summaries and historical scorecards, without paid APIs."""
import argparse
import json
import re
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup
from import_careers import ROOT, CLASSES, fetch
from build_record_layers import number
from cricket_scope import national_match, national_player, publication_data,load_cards,complete_career_counts

CACHE=ROOT/'.data-cache/free-backfill'
DEST=ROOT/'data'

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8');tmp.replace(path)

def career_summary(body):
    soup=BeautifulSoup(body,'html.parser')
    table=next((t for t in soup.select('table.engineTable') if t.find('caption') and t.find('caption').get_text(strip=True)=='Career averages'),None)
    if table is None:raise ValueError('Missing career summary')
    headings=[h.get_text(' ',strip=True) for h in table.select('thead th')]
    row=next((r for r in table.select('tr') if r.find('td') and r.find('td').get_text(strip=True)=='overall'),None)
    if row is None:raise ValueError('Missing overall row')
    return {k:c.get_text(' ',strip=True) for k,c in zip(headings,row.find_all('td',recursive=False)) if k}

def fetch_career(task):
    pid,eid,fmt,cls,*anchors=task;file=CACHE/'careers'/f'{eid}-{cls}.json'
    if file.exists():
        cached=read(file)
        if not anchors or all(number(cached['values'].get(k))==v for k,v in anchors[0].items()):return cached
    url=f'https://stats.cricinfo.com/ci/engine/player/{eid}.html?class={cls};template=results;type=batting;view=innings'
    values=career_summary(fetch(url))
    result={'id':pid,'espn_id':eid,'format':fmt,'values':values,'source':url,'checked_at':datetime.now(timezone.utc).isoformat()}
    write(file,result);time.sleep(.15);return result


def fetch_bowling(task):
    pid,eid,fmt,cls,anchors=task;file=CACHE/'bowling'/f'{eid}-{cls}.json'
    if file.exists():
        cached=read(file)
        if all(number(cached['values'].get(k))==v for k,v in anchors.items()):return cached
    url=f'https://stats.cricinfo.com/ci/engine/player/{eid}.html?class={cls};template=results;type=bowling;view=innings'
    result={'id':pid,'espn_id':eid,'format':fmt,'values':career_summary(fetch(url)),'source':url,'checked_at':datetime.now(timezone.utc).isoformat()}
    write(file,result);time.sleep(.15);return result

def player(p):
    return {'espn_id':str(p['objectId']),'name':p.get('longName') or p['name']}

def normalize_card(body,expected):
    script=re.search(rb'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',body,re.S)
    if not script:raise ValueError('Missing structured scorecard')
    data=json.loads(script.group(1))['props']['appPageProps']['data'];m=data['match'];c=data['content']
    cls=m.get('internationalClassId')
    if str(m['objectId'])!=expected['id'] or cls not in CLASSES:raise ValueError('Not the expected official international')
    if CLASSES[cls]!=(expected['format'],expected['gender']):raise ValueError('International classification conflict')
    innings=[]
    for i in c.get('innings',[]):
        if not i.get('isBatted'):continue
        bat=[]
        for b in i.get('inningBatsmen',[]):
            if b.get('battedType')!='yes':continue
            bowler=(b.get('dismissalBowler') or {}).get('longName') or (b.get('dismissalBowler') or {}).get('name')
            fielders=[(x.get('player') or x).get('longName') or (x.get('player') or x).get('name') for x in (b.get('dismissalFielders') or [])]
            # Use factual dismissal components; never store commentary or third-party prose.
            dismissal={1:'caught',2:'bowled',3:'lbw',4:'run out',5:'stumped',6:'retired hurt',7:'hit wicket',8:'obstructing the field'}.get(b.get('dismissalType'),'out' if b.get('isOut') else 'not out')
            if any(fielders):dismissal+=' '+', '.join(x for x in fielders if x)
            if bowler:dismissal+=' b '+bowler
            bat.append({**player(b['player']),'runs':b.get('runs'),'balls':b.get('balls'),'minutes':b.get('minutes'),'fours':b.get('fours'),'sixes':b.get('sixes'),'sr':b.get('strikerate'),'out':b.get('isOut'),'dismissal':dismissal})
        bowl=[{**player(b['player']),'balls':b.get('balls'),'overs':b.get('overs'),'maidens':b.get('maidens'),'runs':b.get('conceded'),'wickets':b.get('wickets'),'econ':b.get('economy'),'wides':b.get('wides'),'noballs':b.get('noballs')} for b in i.get('inningBowlers',[]) if b.get('bowledType')=='yes']
        extra=i.get('extras')
        if i.get('runs') is not None and extra is not None and all(b['runs'] is not None for b in bat):
            if sum(b['runs'] for b in bat)+extra!=i['runs']:raise ValueError('Innings runs do not reconcile')
        innings.append({'team':i['team'].get('longName') or i['team']['name'],'runs':i.get('runs'),'wickets':i.get('wickets'),'balls':i.get('balls'),'overs_display':str(i.get('overs')),'balls_per_over':i.get('ballsPerOver') or m.get('ballsPerOver') or 6,'extras':extra,'super_over':False,'declared':i.get('event')==2,'batting':bat,'bowling':bowl,'overs':[],'fall':[{'player':(w.get('dismissalBatsman') or {}).get('longName') or (w.get('dismissalBatsman') or {}).get('name') or 'Batter not recorded','runs':w.get('fowRuns'),'wicket':w.get('fowWicketNum'),'balls':w.get('fowBalls'),'overs':w.get('fowOvers')} for w in i.get('inningFallOfWickets',[])]})
    if not innings and m.get('hasScorecard') and m.get('status') not in ('POSTPONED','CANCELLED','ABANDONED') and not m.get('isCancelled') and not re.search(r'abandon|no result|cancel|without a ball',str(m.get('statusText','')),re.I):raise ValueError('Advertised scorecard has no innings')
    return {'match':expected,'innings':innings,'players':{t['team'].get('longName') or t['team']['name']:[player(p['player']) for p in t.get('players',[])] for t in (c.get('matchPlayers') or {}).get('teamPlayers',[]) if t.get('type')=='PLAYING'},'international_class':cls,'coverage':'scorecard' if innings else 'no-play','source':f'https://stats.cricinfo.com/ci/engine/match/{expected["id"]}.html','checked_at':datetime.now(timezone.utc).isoformat()}

def fetch_card(match):
    file=CACHE/'scorecards'/f'{match["id"]}.json'
    if file.exists():return read(file)
    result=normalize_card(fetch(f'https://stats.cricinfo.com/ci/engine/match/{match["id"]}.html'),match)
    write(file,result);time.sleep(.15);return result

def main(mode,workers,limit):
    careers=publication_data(ROOT)[1] if mode in ('careers','bowling') else read(DEST/'careers.json');tasks=[]
    if mode=='careers':
        ranked=sorted((p for p in careers['players'] if national_player(p)),key=lambda p:sum(s.get('runs') or 0 for s in p['formats'].values()),reverse=True)
        for p in ranked:
            for fmt,s in p['formats'].items():
                if not s.get('innings'):continue
                if any(s.get(k) is None for k in ('balls','sr','avg','fours','sixes')):
                    cls=next(k for k,v in CLASSES.items() if v==(fmt,p['gender']))
                    tasks.append((p['id'],p['espn_id'],fmt,cls,{'Mat':s.get('matches'),'Inns':s.get('innings'),'Runs':s.get('runs')}))
        fn=fetch_career
    elif mode=='bowling':
        arc,_,hist=publication_data(ROOT)
        people={p['id']:{**p,'career':p['formats']} for p in careers['players']}
        complete_career_counts(load_cards(ROOT,arc['matches']+hist['matches'],people),people)
        for p in careers['players']:
            for fmt,s in p['formats'].items():
                if s.get('maidens') is None and s.get('bowling_innings'):
                    cls=next(k for k,v in CLASSES.items() if v==(fmt,p['gender']))
                    tasks.append((p['id'],p['espn_id'],fmt,cls,{'Mat':s.get('matches'),'Inns':s.get('bowling_innings'),'Wkts':s.get('wickets'),'Runs':s.get('conceded')}))
        fn=fetch_bowling
    else:
        tasks=[m for m in read(DEST/'historical_matches.json')['matches'] if national_match(m)]
        fn=fetch_card
    if limit:tasks=tasks[:limit]
    done=[];errors=[];print(f'{mode}: {len(tasks)} records',flush=True)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(fn,t):t for t in tasks}
        for f in as_completed(futures):
            try:done.append(f.result())
            except Exception as error:errors.append({'record':futures[f],'error':str(error)})
            n=len(done)+len(errors)
            if n%100==0:print(f'{mode}: {n}/{len(tasks)}; {len(errors)} errors',flush=True)
    if mode in ('careers','bowling'):
        target=DEST/('career_enrichment.json' if mode=='careers' else 'bowling_enrichment.json')
        prior=read(target)['records'] if target.exists() else []
        records={(r['id'],r['format']):r for r in prior+done}
        write(target,{'records':list(records.values()),'errors':errors,'checked_at':datetime.now(timezone.utc).isoformat()})
    else:
        shards=defaultdict(dict)
        for c in done:shards[c['match']['id'][:3]][c['match']['id']]=c
        for key,value in shards.items():write(DEST/'historical_scorecards'/f'{key}.json',value)
        write(DEST/'scorecard_backfill_report.json',{'requested':len(tasks),'imported':len(done),'with_innings':sum(bool(c['innings']) for c in done),'no_play':sum(not c['innings'] for c in done),'errors':errors,'checked_at':datetime.now(timezone.utc).isoformat()})
    print(f'{mode}: done {len(done)}; errors {len(errors)}',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['careers','bowling','scorecards']);parser.add_argument('--workers',type=int,default=4);parser.add_argument('--limit',type=int)
    args=parser.parse_args();main(args.mode,args.workers,args.limit)
