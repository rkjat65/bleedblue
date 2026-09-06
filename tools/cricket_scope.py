"""Publication scope; official career definitions remain independent of browsing."""
FULL_MEMBERS = frozenset('Afghanistan|Australia|Bangladesh|England|India|Ireland|New Zealand|Pakistan|South Africa|Sri Lanka|West Indies|Zimbabwe'.split('|'))

def national_match(match):
    return len(match['teams']) == 2 and set(match['teams']) <= FULL_MEMBERS

def national_player(player):
    return bool(FULL_MEMBERS.intersection(player['teams']))


def complete_career_counts(cards,people):
    """Derive only when every career batting innings and dismissal reconciles."""
    from collections import defaultdict,Counter
    from decimal import Decimal,ROUND_DOWN
    rows=defaultdict(list);bowling=defaultdict(list);applied=Counter()
    for card in cards.values():
        for inn in card['innings']:
            if inn.get('super_over'):continue
            for b in inn['batting']:rows[b['id'],card['match']['format']].append(b)
            for b in inn.get('bowling',[]):bowling[b['id'],card['match']['format']].append(b)
    for pid,p in people.items():
        for fmt,s in p.get('career',{}).items():
            bowls=bowling[pid,fmt]
            if bowls and len(bowls)==s.get('bowling_innings') and all(b.get('wickets') is not None for b in bowls) and sum(b['wickets'] for b in bowls)==s.get('wickets'):
                if s.get('four_w') is None:s['four_w']=sum(b['wickets']==4 for b in bowls);applied['four_w']+=1
                if s.get('maidens') is None and all(b.get('maidens') is not None for b in bowls):s['maidens']=sum(b['maidens'] for b in bowls);applied['maidens']+=1
            batting=rows[pid,fmt]
            if not batting or len(batting)!=s.get('innings'):continue
            if any(b.get('runs') is None or b.get('out') is None for b in batting):continue
            if sum(b['runs'] for b in batting)!=s.get('runs') or sum(bool(b['out']) for b in batting)!=s.get('outs'):continue
            for key in ('balls','fours','sixes'):
                if s.get(key) is None and all(b.get(key) is not None for b in batting):
                    value=sum(b[key] for b in batting)
                    if key=='balls' and value==0 and s['runs']>0:continue
                    s[key]=value;applied[key]+=1
            if s.get('sr') is None and s.get('balls'):
                s['sr']=float((Decimal(s['runs'])*100/Decimal(s['balls'])).quantize(Decimal('.01'),rounding=ROUND_DOWN));applied['sr']+=1
    return dict(applied)


def career_scorecards(root,published,people):
    """Official careers may use available games outside the browsing scope."""
    import json
    official=json.loads((root/'data/official_match_registry.json').read_text(encoding='utf-8'))['matches']
    records={p['id']:p for p in json.loads((root/'data/careers.json').read_text(encoding='utf-8'))['players']}
    cards=dict(published)
    for file in (root/'data/scorecards').glob('*.json'):
        for mid,card in json.loads(file.read_text(encoding='utf-8')).items():
            if mid in cards or mid not in official:continue
            for inn in card['innings']:
                for kind in ('batting','bowling'):
                    team=inn['team'] if kind=='batting' else next(t for t in card['match']['teams'] if t!=inn['team'])
                    inn[kind]=[b for b in inn[kind] if b['id'] in people and b['id'] in records and records[b['id']]['gender']==card['match']['gender'] and team in records[b['id']]['teams']]
            cards[mid]=card
    return cards

def load_cards(root, matches, people):
    import json,re
    selected={m['id']:m for m in matches};cards={}
    identities={p['espn_id']:pid for pid,p in people.items() if p.get('espn_id')}
    registry=root/'data/identity_registry.json'
    if registry.exists():identities.update({eid:pid for eid,pid in json.loads(registry.read_text(encoding='utf-8'))['espn_to_id'].items() if pid in people})
    def team_name(name):return re.sub(r'\s*(?:Women|Wmn|\(Women\))$','',name).strip()
    for folder in ['scorecards','historical_scorecards']:
        for file in sorted((root/'data'/folder).glob('*.json')):
            for mid,card in json.loads(file.read_text(encoding='utf-8')).items():
                if mid not in selected or mid in cards:continue
                match=selected[mid]
                if folder=='historical_scorecards':
                    def identify(row,team,played=False):
                        eid=row['espn_id'];pid=identities.get(eid,'espn-'+eid);row['id']=pid
                        if pid not in people and played:people[pid]={'id':pid,'espn_id':eid,'name':row['name'],'teams':[team],'gender':match['gender'],'career':{},'formats':{},'first':match['date'][:4],'last':match['date'][:4]}
                        if pid in people:people[pid]['full_name']=row['name']
                    card['players']={team_name(t):squad for t,squad in card['players'].items()}
                    for team,squad in card['players'].items():
                        for p in squad:identify(p,team)
                    for inn in card['innings']:
                        inn['team']=team_name(inn['team'])
                        if inn['team'] not in match['teams']:raise ValueError('Scorecard team mismatch: '+mid)
                        for b in inn['batting']:identify(b,inn['team'],True)
                        opponent=next(t for t in match['teams'] if t!=inn['team'])
                        for b in inn['bowling']:identify(b,opponent,True)
                    match['player_ids']=sorted({p['id'] for squad in card['players'].values() for p in squad if p['id'] in people}|{p['id'] for inn in card['innings'] for p in inn['batting']+inn['bowling']})
                    match['coverage']=card['coverage']
                    match['totals']=[{k:inn[k] for k in ['team','runs','wickets','balls','super_over']} for inn in card['innings']]
                card['match']=match;cards[mid]=card
    return cards

def publication_data(root):
    import json
    from collections import Counter,defaultdict
    import re
    def read(name):return json.loads((root/'data'/name).read_text(encoding='utf-8'))
    arc,careers,hist=read('international.json'),read('careers.json'),read('historical_matches.json')
    official=read('official_match_registry.json')['matches']
    arc['matches']=[m for m in arc['matches'] if national_match(m) and m['id'] in official]
    hist['matches']=[m for m in hist['matches'] if national_match(m) and m['id'] in official]
    if (root/'data/ground_metadata.json').exists():
        venues=read('ground_metadata.json')['venues']
        for m in hist['matches']:
            if m['venue'] in venues:m['city']=venues[m['venue']]['city'];m['host_country']=venues[m['venue']]['country']
    # National affiliation is an identity fact, not a player's last listed team.
    # Some careers include representative XIs or a later change of nationality.
    selected={m['id']:m for m in arc['matches']+hist['matches']}
    countries=defaultdict(set)
    identities={p['espn_id']:p['id'] for p in careers['players']}
    if (root/'data/identity_registry.json').exists():identities.update(read('identity_registry.json')['espn_to_id'])
    for folder in ['scorecards','historical_scorecards']:
        for file in (root/'data'/folder).glob('*.json'):
            for mid,card in json.loads(file.read_text(encoding='utf-8')).items():
                if mid not in selected:continue
                for team,squad in card['players'].items():
                    team=re.sub(r'\s*(?:Women|Wmn|\(Women\))$','',team).strip()
                    if team not in FULL_MEMBERS:continue
                    for p in squad:
                        pid=p.get('id') or identities.get(p.get('espn_id'))
                        if pid:countries[pid].add(team)
    visible_ids={pid for m in arc['matches'] for pid in m['player_ids']}
    arc['players']=[p for p in arc['players'] if p['id'] in visible_ids]
    careers['players']=[p for p in careers['players'] if national_player(p) or countries[p['id']]]
    for p in careers['players']:p['teams']=sorted(set(p['teams']).intersection(FULL_MEMBERS)|countries[p['id']])
    for p in arc['players']:p['teams']=sorted(set(p['teams']).intersection(FULL_MEMBERS)|countries[p['id']])
    arc['meta'].update(matches=len(arc['matches']),players=len(arc['players']),teams=sorted(FULL_MEMBERS),formats=dict(Counter(m['format'] for m in arc['matches'])),gender=dict(Counter(m['gender'] for m in arc['matches'])))
    hist['meta']['added_matches']=len(hist['matches'])
    careers['meta']['players']=len(careers['players'])
    careers['meta']['archive_players_without_career']=len(visible_ids-{p['id'] for p in careers['players']})
    enrichment=root/'data/career_enrichment.json';applied=Counter();conflicts=[]
    by_id={p['id']:p for p in careers['players']}
    updates=root/'data/career_updates.json'
    if updates.exists():
        from build_record_layers import normalize_format
        for record in read('career_updates.json')['records']:
            p=by_id.get(record['id']);s=p['formats'].get(record['format']) if p else None
            if not s:continue
            if any('/player/'+p['espn_id']+'.html' not in r['source'] for r in record['layers'].values()):continue
            refreshed=normalize_format(record['layers'])
            # Never replace a newer bulk snapshot with an older supplemental one.
            if record['checked_at']<careers['meta']['checked_at']:continue
            for k,v in refreshed.items():
                if v is not None:s[k]=v
            s['sources']={kind:r['source'] for kind,r in record['layers'].items()}
            s['checked_at']=record['checked_at']
    mapping={'balls':'BF','sr':'SR','avg':'Ave','fours':'4s','sixes':'6s','ducks':'0','notouts':'NO'}
    enrichment_records=[]
    for file in ['career_enrichment.json','career_fallback.json']:
        if (root/'data'/file).exists():enrichment_records.extend(read(file)['records'])
    if enrichment_records:
        for record in enrichment_records:
            p=by_id.get(record['id']);s=p['formats'].get(record['format']) if p else None
            if not s:continue
            if record.get('espn_id')!=p['espn_id']:continue
            v=record['values']
            from build_record_layers import number
            if any(s.get(k)!=number(v.get(label)) for k,label in [('matches','Mat'),('innings','Inns'),('runs','Runs')]):
                conflicts.append({'id':record['id'],'format':record['format'],'source':record['source']});continue
            for key,column in mapping.items():
                value=number(v.get(column))
                # Some secondary summaries use zero for historically unknown balls.
                if key=='balls' and value==0 and (s.get('runs') or 0)>0:continue
                if s.get(key) is None and value is not None:s[key]=value;applied[key]+=1
            s['enrichment_source']=record['source']
            # Averages with no dismissals and strike rates with no balls are undefined.
            if s.get('outs') is None and s.get('innings') is not None and s.get('notouts') is not None:s['outs']=s['innings']-s['notouts']
            for key,top,bottom,factor in [('avg','runs','outs',1),('sr','runs','balls',100),('bowlAvg','conceded','wickets',1),('bowlSr','legal','wickets',1),('econ','conceded','legal',6)]:
                if s.get(key) is None and s.get(top) is not None and s.get(bottom,0) and s[bottom]>0:
                    from decimal import Decimal, ROUND_DOWN
                    s[key]=float((Decimal(s[top])*factor/Decimal(s[bottom])).quantize(Decimal('.01'),rounding=ROUND_DOWN));applied[key]+=1
    bowling=root/'data/bowling_enrichment.json'
    if bowling.exists():
        from build_record_layers import number
        for record in read('bowling_enrichment.json')['records']:
            p=by_id.get(record['id']);s=p['formats'].get(record['format']) if p else None
            if not s:continue
            if record.get('espn_id')!=p['espn_id']:continue
            v=record['values']
            if any(s.get(k)!=number(v.get(label)) for k,label in [('matches','Mat'),('bowling_innings','Inns'),('wickets','Wkts'),('conceded','Runs')]):continue
            for key,label in [('maidens','Mdns'),('four_w','4'),('five_w','5'),('ten_w','10')]:
                value=number(v.get(label))
                if s.get(key) is None and value is not None:s[key]=value;applied[key]+=1
    # Career count columns are exact. Recompute rates rather than padding a
    # source's one-decimal bowling rate with a misleading second decimal.
    from decimal import Decimal,ROUND_DOWN
    for p in careers['players']:
        for fmt,s in p['formats'].items():
            for key,top,bottom,factor in [('avg','runs','outs',1),('sr','runs','balls',100),('bowlAvg','conceded','wickets',1),('bowlSr','legal','wickets',1),('econ','conceded','legal',6)]:
                if s.get(top) is not None and s.get(bottom) and s[bottom]>0:
                    s[key]=float((Decimal(s[top])*factor/Decimal(s[bottom])).quantize(Decimal('.01'),rounding=ROUND_DOWN))
                elif s.get(bottom)==0:s[key]=None
            if fmt!='Test' and not s.get('best_match'):s['best_match']=s.get('best_bowling')
    careers['meta']['enriched_fields']=dict(applied);careers['meta']['enrichment_conflicts']=conflicts
    return arc,careers,hist
