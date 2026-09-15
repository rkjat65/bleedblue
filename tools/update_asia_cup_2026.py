"""Add the verified 2026 Women's Asia Cup final without refreshing unrelated careers."""
import json
from datetime import datetime, timezone
from pathlib import Path
from backfill_free_data import fetch_card, read, write

ROOT=Path(__file__).resolve().parent.parent

def main():
    dest=ROOT/'data'
    history=read(dest/'historical_matches.json')
    registry=read(dest/'official_match_registry.json')
    match={'id':'1548905','date':'2026-09-13','format':'T20I','gender':'Women',
           'teams':['India','Sri Lanka'],'venue':'Dubai (DICS)','city':'Dubai',
           'event':"Women's Asia Cup 2026",'outcome':{'winner':'India'},
           'margin_text':'72 runs','totals':[],'player_ids':[], 'coverage':'result-only',
           'source':'https://stats.cricinfo.com/ci/engine/match/1548905.html',
           'source_list':'https://stats.cricinfo.com/ci/engine/stats/index.html?class=10;template=results;type=team;view=results'}
    card=fetch_card(match)
    assert [(i['runs'],i['wickets']) for i in card['innings']]==[(183,5),(111,10)]
    assert all(i['balls']==120 for i in card['innings'])
    shard=dest/'historical_scorecards/154.json'
    cards=read(shard)
    cards[match['id']]=card
    added=match['id'] not in registry['matches']
    archive_ids={m['id'] for m in read(dest/'international.json')['matches']}
    rows={m['id']:m for m in history['matches']}
    if match['id'] not in archive_ids: rows[match['id']]=match
    # Both knockout results already exist; ensure their cards are available too.
    for mid in ('1548903','1548904'):
        if mid in rows and mid not in cards: cards[mid]=fetch_card(rows[mid])
    checked=datetime.now(timezone.utc).isoformat(timespec='seconds')
    history['matches']=sorted(rows.values(),key=lambda m:(m['date'],m['id']),reverse=True)
    meta=history['meta']
    meta['added_matches']=len(rows)
    meta['last']=max(m['date'] for m in rows.values())
    meta['targeted_update']={'checked_at':checked,'match_ids':['1548903','1548904','1548905'],'event':match['event']}
    if added:
        meta['gender']['Women']+=1
        meta['format_summary']['T20I']['matches']+=1
        meta['format_summary']['T20I']['women']+=1
    registry['matches'][match['id']]=10
    registry['targeted_update']=meta['targeted_update']
    write(shard,cards)
    write(dest/'historical_matches.json',history)
    write(dest/'historical_manifest.json',meta)
    write(dest/'official_match_registry.json',registry)
    print(json.dumps({'added_final':added,'knockouts':[{'id':mid,'innings':len(cards[mid]['innings'])} for mid in ('1548903','1548904','1548905')], 'batting':card['innings'][0]['batting'],'bowling':card['innings'][1]['bowling']},ensure_ascii=False))

if __name__=='__main__':main()
