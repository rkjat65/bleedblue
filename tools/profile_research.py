"""Crawlable player charts and selected opposition studies from verified scorecards.

These aggregates deliberately describe the publication archive, not official
career totals. A partially recorded denominator never becomes a rate.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_DOWN
import html
import re
import unicodedata

FORMATS = ('Test', 'ODI', 'T20I')


def esc(value):
    return html.escape(str(value), quote=True)


def slug(value):
    ascii_value = unicodedata.normalize('NFKD', str(value)).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', ascii_value.lower()).strip('-')


def link(path, label):
    return f'<a href="{esc(path)}">{esc(label)}</a>'


def rate(top, denominator, factor=1):
    if top is None or denominator is None or denominator <= 0:
        return None
    return float((Decimal(top) * factor / Decimal(denominator)).quantize(Decimal('.01'), rounding=ROUND_DOWN))


def complete_sum(rows, key):
    return sum(r[key] for r in rows) if all(r.get(key) is not None for r in rows) else None


def aggregate_rows(rows):
    """Keep batting and bowling samples separate, including known zero scores."""
    batting = [r for r in rows if r.get('position') is not None or r.get('runs') is not None or r.get('balls') is not None]
    bowling = [r for r in rows if any(r.get(k) is not None for k in ('wickets', 'legal', 'conceded'))]
    totals = {'matches': len({r['match'] for r in rows}), 'innings': len(batting), 'bowling_innings': len(bowling)}
    for key in ('runs', 'balls', 'fours', 'sixes'):
        totals[key] = complete_sum(batting, key)
    totals['outs'] = sum(int(r['out']) for r in batting) if all(r.get('out') is not None for r in batting) else None
    for key in ('wickets', 'legal', 'conceded'):
        totals[key] = complete_sum(bowling, key)
    totals['hundreds'] = sum(r['runs'] >= 100 for r in batting) if all(r.get('runs') is not None for r in batting) else None
    totals['fifties'] = sum(50 <= r['runs'] < 100 for r in batting) if all(r.get('runs') is not None for r in batting) else None
    totals['highest'] = max((r['runs'] for r in batting if r.get('runs') is not None), default=None)
    totals['avg'] = rate(totals['runs'], totals['outs'])
    totals['sr'] = rate(totals['runs'], totals['balls'], 100)
    totals['bowlAvg'] = rate(totals['conceded'], totals['wickets'])
    totals['econ'] = rate(totals['conceded'], totals['legal'], 6)
    totals['bowlSr'] = rate(totals['legal'], totals['wickets'])
    return totals


def value(stats, key):
    number = stats.get(key)
    if number is not None:
        return f'{number:.2f}' if isinstance(number, float) else f'{number:,}'
    denominator = {'avg': 'outs', 'sr': 'balls', 'bowlAvg': 'wickets', 'econ': 'legal', 'bowlSr': 'wickets'}.get(key)
    if denominator and stats.get(denominator) == 0:
        return '<span title="The denominator is zero; this rate does not apply">N/A</span>'
    return '<span title="Not fully recorded in the available scorecards">—</span>'


def table(headers, rows, caption):
    head = ''.join(f'<th scope="col">{esc(h)}</th>' for h in headers)
    body = ''.join('<tr>' + ''.join((f'<th scope="row">{cell}</th>' if i == 0 else f'<td>{cell}</td>') for i, cell in enumerate(row)) + '</tr>' for row in rows)
    return f'<div class="table-wrap pr-table" tabindex="0" role="region" aria-label="{esc(caption)}"><table class="score-table"><caption>{esc(caption)}</caption><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def group_years(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row['date'][:4]].append(row)
    return [(year, aggregate_rows(group)) for year, group in sorted(groups.items())]


def yearly_chart(rows, fmt, metric, context):
    """One scale and one discipline per SVG; exact values remain in the table."""
    sample = 'innings' if metric == 'runs' else 'bowling_innings'
    years = [(year, totals) for year, totals in group_years(rows) if totals[sample]]
    if not years:
        return ''
    recorded = [s[metric] for _, s in years if s[metric] is not None]
    if not recorded:
        return ''
    peak=max(recorded+[1])
    bars=''
    for year,total in years:
        number=total[metric]
        width=0 if number is None else number/peak*100
        label='Not recorded' if number is None else f'{number:,}'
        bars+=f'<li title="{year}: {label} {metric}"><span class="annual-year">{year}</span><span class="annual-track"><i class="annual-fill {metric}" style="width:{width:.3f}%"></i></span><strong>{label}</strong><span class="sr-only"> {metric}</span></li>'
    return f'<figure class="annual-chart" aria-label="{esc(context)}: {esc(fmt)} {metric} by year"><figcaption><strong>{esc(fmt)} · {metric.title()} by year</strong><span>Each bar is one calendar year · exact {metric} at right</span></figcaption><ol>{bars}</ol></figure>'


def trends(rows, context, heading='Performance by year'):
    result = '<section class="panel pr-section"><div class="pr-heading"><div><span class="eyebrow">THE SHAPE OF A CAREER</span><h2>'+esc(heading)+'</h2></div><span class="pill">Available scorecards</span></div><p class="note">Formats are shown separately. These totals cover published scorecards against the twelve national teams; they can differ from complete official career records.</p>'
    has_data = False
    for fmt in FORMATS:
        subset = [r for r in rows if r['format'] == fmt]
        if not subset:
            continue
        has_data = True
        result += '<div class="pr-format"><h3>'+esc(fmt)+'</h3><div class="pr-chart-grid">'
        result += yearly_chart(subset, fmt, 'runs', context) + yearly_chart(subset, fmt, 'wickets', context) + '</div>'
        yearly = group_years(subset)
        result += '<details class="pr-data"><summary>Exact yearly figures · '+str(len(yearly))+' seasons</summary>'
        result += table(['Year','Mat','Bat inns','Runs','HS','Avg','SR','100s','50s','4s','6s','BF','Bowl inns','Wkts','Bowl avg','Econ','Bowl SR'], [[esc(y)]+[value(s,k) for k in ('matches','innings','runs','highest','avg','sr','hundreds','fifties','fours','sixes','balls','bowling_innings','wickets','bowlAvg','econ','bowlSr')] for y,s in reversed(yearly)], fmt+' archive totals by year')+'</details></div>'
    return result+'</section>' if has_data else ''


def milestone_events(rows):
    ordered = sorted(rows, key=lambda r:(r['date'], r['match'], r.get('innings',0)))
    if not ordered:
        return []
    events = [(ordered[0], 'First available scorecard'), (ordered[-1], 'Latest available scorecard')]
    batting = [r for r in ordered if r.get('runs') is not None]
    bowling = [r for r in ordered if r.get('wickets') is not None]
    if batting:
        best = max(batting, key=lambda r:(r['runs'], r.get('out') is False))
        events.append((best, 'Highest recorded innings · '+str(best['runs'])+('*' if best.get('out') is False else '')+' runs'))
        centuries = [r for r in batting if r['runs'] >= 100]
        if centuries and centuries[0] is not best:
            events.append((centuries[0], 'First century in this archive · '+str(centuries[0]['runs'])+' runs'))
    if bowling and max(r['wickets'] for r in bowling) > 0:
        best = max(bowling, key=lambda r:(r['wickets'], -(r['conceded'] if r.get('conceded') is not None else 100000)))
        figure = str(best['wickets'])+'/'+str(best['conceded']) if best.get('conceded') is not None else str(best['wickets'])+' wickets'
        events.append((best, 'Best recorded bowling · '+figure))
        five = [r for r in bowling if r['wickets'] >= 5]
        if five and five[0] is not best:
            events.append((five[0], 'First five-wicket innings in this archive'))
    return sorted(events, key=lambda event:(event[0]['date'],event[1]))


def timeline(rows):
    events = milestone_events(rows)
    if not events:
        return ''
    body = '<section class="panel pr-section"><span class="eyebrow">MOMENTS IN THE RECORD</span><h2>Career timeline</h2><p class="note">Milestones found in available scorecards. The first recorded appearance here is not necessarily the international debut.</p><ol class="pr-timeline">'
    for row, label in events:
        detail = row['format']+' v '+row['opponent']+' · '+row.get('venue','')
        body += f'<li><time datetime="{esc(row["date"])}">{esc(row["date"])}</time><div><strong>{link(row["url"],label)}</strong><p>{esc(detail)}</p></div></li>'
    return body+'</ol></section>'


def select_research_players(people, limit_per_gender=30):
    """Balance genders and batting/bowling leaders, with broad team coverage."""
    players = list(people.values()) if isinstance(people, dict) else list(people)
    selected = set()
    def total(p, key):
        return sum(s.get(key) or 0 for s in p.get('career', {}).values())
    for gender in ('Men', 'Women'):
        candidates = [p for p in players if p.get('gender')==gender and p.get('career')]
        rankings = [sorted(candidates,key=lambda p:(-total(p,k),p['id'])) for k in ('runs','wickets')]
        chosen = set()
        # Give each national team a starting point before filling by career rank.
        teams = sorted({team for p in candidates for team in p.get('teams',[])})
        for team in teams:
            team_players = [p for p in rankings[0] if team in p.get('teams',[])]
            if team_players and len(chosen)<limit_per_gender:
                chosen.add(team_players[0]['id'])
        for batting, bowling in zip(*rankings):
            for player in (batting, bowling):
                if len(chosen)<limit_per_gender:
                    chosen.add(player['id'])
            if len(chosen)>=limit_per_gender:
                break
        selected.update(chosen)
    return selected


def opposition_groups(rows, minimum=10, per_format=4):
    groups = defaultdict(list)
    for row in rows:
        if row['format'] in FORMATS and row.get('opponent'):
            groups[(row['format'], row['opponent'])].append(row)
    chosen = []
    for fmt in FORMATS:
        qualified = [(opponent, subset, aggregate_rows(subset)) for (f,opponent),subset in groups.items() if f==fmt]
        qualified = [entry for entry in qualified if max(entry[2]['innings'],entry[2]['bowling_innings'])>=minimum]
        qualified.sort(key=lambda entry:(-entry[2]['matches'],entry[0]))
        chosen.extend((fmt, opponent, subset, stats) for opponent,subset,stats in qualified[:per_format])
    return chosen


def opposition_path(path, fmt, opponent):
    return '/research/'+path.strip('/').split('/')[-1]+'-'+slug(fmt)+'-vs-'+slug(opponent)+'/'


def opposition_links(rows, path):
    entries = opposition_groups(rows)
    if not entries:
        return ''
    body = '<section class="panel pr-section"><span class="eyebrow">A CLOSER LOOK</span><h2>Records against the opposition</h2><p>Selected studies with at least ten batting or bowling innings. Each page includes sample sizes, yearly trends and the scorecards behind the figures.</p><div class="pr-opposition-links">'
    for fmt, opponent, subset, stats in entries:
        body += '<a href="'+esc(opposition_path(path,fmt,opponent))+'"><span>'+esc(fmt)+'</span><strong>Against '+esc(opponent)+'</strong><small>'+str(stats['matches'])+' matches with recorded figures</small></a>'
    return body+'</div></section>'


def profile_research_section(p, rows, path, curated=False):
    return trends(rows,p['name'])+timeline(rows)+(opposition_links(rows,path) if curated else '')


def opponent_pages(p, rows, path):
    """Yield arguments accepted by build_site.page; no I/O or hidden imports."""
    for fmt, opponent, subset, stats in opposition_groups(rows):
        subset = sorted(subset,key=lambda r:(r['date'],r['match'],r.get('innings',0)))
        title = p['name']+' '+fmt+' record against '+opponent
        description = f'{title}: {stats["matches"]} matches with recorded figures, batting and bowling averages, yearly charts and linked scorecards from {subset[0]["date"]} to {subset[-1]["date"]}.'
        body = f'<section class="page-head"><span class="eyebrow">PLAYER RESEARCH · {esc(p["gender"])}</span><h1>{esc(title)}</h1><p>{esc(subset[0]["date"])} – {esc(subset[-1]["date"])} · Available official international scorecards</p></section>'
        body += '<p>'+link(path,p['name']+' complete career profile')+' · '+link('/research/','More player studies')+'</p>'
        body += '<section class="panel pr-section"><h2>The record at a glance</h2><p>This study covers <strong>'+str(stats['matches'])+' '+esc(fmt)+' matches</strong> against '+esc(opponent)+' with recorded batting or bowling figures: '+str(stats['innings'])+' batting innings and '+str(stats['bowling_innings'])+' bowling innings. Matches with no batting or bowling entry for this player are outside this sample.</p>'
        body += table(['Discipline','Innings','Runs','Wickets / outs','Average','Strike rate'],[
            ['Batting',value(stats,'innings'),value(stats,'runs'),value(stats,'outs'),value(stats,'avg'),value(stats,'sr')],
            ['Bowling',value(stats,'bowling_innings'),value(stats,'conceded'),value(stats,'wickets'),value(stats,'bowlAvg'),value(stats,'bowlSr')]],'Batting runs and dismissals; bowling runs conceded and wickets')
        body += '<p class="note">Batting average = runs ÷ dismissals; batting strike rate = runs per 100 balls. Bowling average = runs conceded ÷ wickets; bowling strike rate = legal balls per wicket. Rates require fully recorded inputs. — means unrecorded; N/A means a zero denominator.</p>'
        if stats['bowling_innings']:
            body += '<p>Bowling economy: <strong>'+value(stats,'econ')+'</strong> runs per six legal balls. Legal balls recorded: '+value(stats,'legal')+'.</p>'
        if stats['innings']:
            body += '<p>Batting milestones in this sample: <strong>'+value(stats,'hundreds')+' centuries</strong> and <strong>'+value(stats,'fifties')+' scores from 50 to 99</strong>. Balls faced: '+value(stats,'balls')+'.</p>'
        body += '</section>'+trends(subset,title,'How the record developed')
        body += '<section class="panel pr-section"><h2>Home, away and neutral conditions</h2><p class="note">Setting follows the recorded host country. Unknown locations are retained as unknown; venue names alone are not guessed.</p>'
        setting_rows = []
        for setting in ('Home','Away','Neutral','Unknown'):
            selected = [r for r in subset if r.get('setting','Unknown')==setting]
            if selected:
                group = aggregate_rows(selected)
                setting_rows.append([setting]+[value(group,k) for k in ('matches','innings','runs','avg','sr','bowling_innings','wickets','bowlAvg')])
        body += table(['Setting','Matches','Bat inns','Runs','Bat avg','Bat SR','Bowl inns','Wickets','Bowl avg'],setting_rows,'Opposition record by match setting')+'</section>'
        body += timeline(subset)
        recent = list(reversed(subset))[:20]
        body += '<section class="panel pr-section"><h2>Recent recorded innings</h2>'+table(['Date','Venue','Innings','Runs','Balls','Wickets','Conceded'],[[link(r['url'],r['date']),esc(r.get('venue','')),str(r.get('innings',''))]+[('—' if r.get(k) is None else str(r[k])) for k in ('runs','balls','wickets','conceded')] for r in recent],'Scorecards supporting this opposition study')+'</section>'
        body += '<p class="note">This opposition study uses available scorecards in Cricket Wicket’s twelve-team publication scope. It is a dated archive analysis, not a claim of complete career coverage. '+link('/methodology/','Read the coverage and calculation method')+'.</p>'
        yield opposition_path(path,fmt,opponent), title, description, body, 'Article'


def research_index(players, routes, selected_ids, available_rows=None):
    """A compact hub links only players with meaningful opposition samples."""
    values = list(players.values()) if isinstance(players,dict) else list(players)
    body = '<section class="page-head"><span class="eyebrow">INTERNATIONAL CRICKET RESEARCH</span><h1>Player records against the opposition</h1><p>Follow a player’s record across opponents, formats and conditions. Each study includes sample sizes, yearly charts and linked scorecards.</p></section><p class="note">Selected batting and bowling leaders from men’s and women’s cricket. Opposition studies require at least ten batting or bowling innings and cover available scorecards.</p>'
    for gender in ('Men','Women'):
        group = sorted([p for p in values if p['id'] in selected_ids and p.get('gender')==gender], key=lambda p:p['name'])
        body += '<section class="panel pr-section"><h2>'+gender+'’s cricket</h2><div class="pr-opposition-links">'
        for p in group:
            if available_rows is not None:
                studies = opposition_groups(available_rows.get(p['id'],[]))
                if not studies:
                    continue
                target = opposition_path(routes[p['id']],studies[0][0],studies[0][1])
                detail = str(len(studies))+' opposition studies on the player profile'
            else:
                target, detail = routes[p['id']]+'#research', 'Explore the available international record'
            body += '<a href="'+esc(routes[p['id']]+'#research')+'"><span>'+esc(' / '.join(p.get('teams',[])))+'</span><strong>'+esc(p['name'])+'</strong><small>'+esc(detail)+'</small></a>'
        body += '</div></section>'
    return '/research/', 'Cricket player opposition records & research', 'Explore international player records against the opposition, with separate formats, yearly charts, home and away splits and linked scorecards.', body, 'CollectionPage'
