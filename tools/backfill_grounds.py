"""Resolve historical venue locations from a verified international at each venue."""
import re
import json
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from backfill_free_data import ROOT,read,write,CACHE
from import_careers import fetch,CLASSES
from cricket_scope import national_match


def retrieve(m):
    file=CACHE/'grounds'/f'{m["id"]}.json'
    if file.exists():return read(file)
    url=f'https://stats.cricinfo.com/ci/engine/match/{m["id"]}.html'
    body=fetch(url);script=re.search(rb'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',body,re.S)
    d=json.loads(script.group(1))['props']['appPageProps']['data']['match']
    if str(d['objectId'])!=m['id'] or CLASSES.get(d.get('internationalClassId'))!=(m['format'],m['gender']):raise ValueError('Match identity mismatch')
    g=d['ground'];result={'venue':m['venue'],'city':g['town']['name'],'country':g['country']['name'],'source':url,'checked_at':datetime.now(timezone.utc).isoformat()}
    write(file,result);return result


def main():
    venues={}
    for m in read(ROOT/'data/historical_matches.json')['matches']:
        if national_match(m) and m['venue']:venues.setdefault(m['venue'],m)
    done={};errors=[]
    print('Resolving historical venues:',len(venues),flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(retrieve,m):v for v,m in venues.items()}
        for f in as_completed(futures):
            try:r=f.result();done[r['venue']]=r
            except Exception as e:errors.append({'venue':futures[f],'error':str(e)})
    write(ROOT/'data/ground_metadata.json',{'venues':done,'errors':errors})
    print(f'Venues: {len(done)} resolved; {len(errors)} errors',flush=True)


if __name__=='__main__':main()
