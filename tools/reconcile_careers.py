"""Refresh all disciplines together when a supplementary summary detects drift."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from backfill_free_data import ROOT, read, write, career_summary
from import_careers import fetch, CLASSES
from build_record_layers import normalize_format
from cricket_scope import publication_data


def retrieve(task):
    p,fmt=task;cls=next(k for k,v in CLASSES.items() if v==(fmt,p['gender']))
    layers={}
    for kind in ['batting','bowling','fielding']:
        url=f'https://stats.cricinfo.com/ci/engine/player/{p["espn_id"]}.html?class={cls};template=results;type={kind}'
        layers[kind]={'values':career_summary(fetch(url)),'source':url}
    stats=normalize_format(layers)
    if stats['match_count_conflict']:raise ValueError('Disciplines have different match counts')
    if (stats['matches'] or 0)<(p['formats'][fmt]['matches'] or 0):raise ValueError('Career match count decreased')
    return {'id':p['id'],'format':fmt,'layers':layers,'checked_at':datetime.now(timezone.utc).isoformat()}


def main():
    _,careers,_=publication_data(ROOT);people={p['id']:p for p in careers['players']}
    tasks={(r['id'],r['format']) for r in careers['meta']['enrichment_conflicts'] if 'stats.cricinfo.com' in r['source']}
    done=[];errors=[]
    path=ROOT/'data/career_updates.json'
    previous={(r['id'],r['format']):r for r in read(path)['records']} if path.exists() else {}
    print(f'Reconciling {len(tasks)} player formats',flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(retrieve,(people[pid],fmt)):(pid,fmt) for pid,fmt in tasks}
        for f in as_completed(futures):
            try:
                r=f.result();previous[r['id'],r['format']]=r;done.append(r)
            except Exception as e:errors.append({'record':futures[f],'error':str(e)})
    write(path,{'records':list(previous.values()),'errors':errors,'checked_at':datetime.now(timezone.utc).isoformat()})
    print(f'Reconciled {len(done)}; {len(errors)} unresolved: {errors}',flush=True)


if __name__=='__main__':main()
