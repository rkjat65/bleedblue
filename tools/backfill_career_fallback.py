"""Supplement missing batting counts through exact Cricsheet registry identities."""
import csv
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from backfill_free_data import ROOT, CACHE, read, write
from import_careers import fetch
from cricket_scope import national_player


def parse_batting(body):
    soup=BeautifulSoup(body,'html.parser')
    for table in soup.select('table'):
        rows=[[c.get_text(' ',strip=True) for c in r.find_all(['th','td'],recursive=False)] for r in table.select('tr')]
        if not rows or not any(r and r[0]=='Not Out' for r in rows):continue
        formats={i:{'Test':'Test','ODI':'ODI','T20':'T20I'}[v] for i,v in enumerate(rows[0]) if v in ('Test','ODI','T20')}
        fields={'Matches':'Mat','Innings':'Inns','Runs':'Runs','Balls':'BF','Not Out':'NO','Fours':'4s','Sixes':'6s','Ducks':'0'}
        return {fmt:{fields[row[0]]:row[i] for row in rows[1:] if row and row[0] in fields and i<len(row)} for i,fmt in formats.items()}
    raise ValueError('No batting summary table')


def retrieve(task):
    p,key=task;file=CACHE/'fallback'/f'{key}.json'
    if file.exists():return read(file)
    url=f'https://www.cricbuzz.com/profiles/{key}/player'
    result={'id':p['id'],'espn_id':p['espn_id'],'formats':parse_batting(fetch(url)),'source':url,'checked_at':datetime.now(timezone.utc).isoformat()}
    write(file,result);return result


def main(workers=3):
    registry={r['identifier']:r for r in csv.DictReader((ROOT/'.data-cache/careers/people.csv').open(encoding='utf-8'))}
    tasks=[]
    for p in read(ROOT/'data/careers.json')['players']:
        # This retired identity is also verified by name, country and all three
        # official career anchors; many pre-1990 summaries have partial BF totals.
        key=registry.get(p['id'],{}).get('key_cricbuzz') or {'35320':'25'}.get(p['espn_id'])
        if national_player(p) and key and any(s.get('balls') is None or s.get('fours') is None for s in p['formats'].values()):tasks.append((p,key))
    tasks.sort(key=lambda t:sum(s.get('runs') or 0 for s in t[0]['formats'].values()),reverse=True)
    records=[];errors=[]
    print(f'Career fallback: {len(tasks)} exact identities',flush=True)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(retrieve,t):t[0]['id'] for t in tasks}
        for future in as_completed(futures):
            try:
                r=future.result()
                records.extend({k:v for k,v in r.items() if k!='formats'}|{'format':fmt,'values':v} for fmt,v in r['formats'].items())
            except Exception as e:errors.append({'id':futures[future],'error':str(e)})
            n=sum(f.done() for f in futures)
            if n%100==0:print(f'Fallback: {n}/{len(tasks)}; {len(errors)} errors',flush=True)
    write(ROOT/'data/career_fallback.json',{'records':records,'errors':errors,'checked_at':datetime.now(timezone.utc).isoformat()})
    print(f'Fallback done: {len(records)} format records; {len(errors)} errors',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=3)
    main(parser.parse_args().workers)
