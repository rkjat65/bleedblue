"""Server-rendered homepage art and charts, using publication records only."""
import html
import json
from collections import Counter


def _metric(value):
    return '—' if value is None else f'{value:,}' if isinstance(value, int) else f'{value:.2f}' if isinstance(value, float) else str(value)


def _team_record(matches, left, right):
    selected=[m for m in matches if left in m.get('teams',[]) and right in m.get('teams',[])]
    rows=[]
    for fmt in ('Test','ODI','T20I'):
        sample=[m for m in selected if m.get('format')==fmt]
        if not sample: continue
        wins_left=sum(m.get('outcome',{}).get('winner')==left for m in sample)
        wins_right=sum(m.get('outcome',{}).get('winner')==right for m in sample)
        undecided=len(sample)-wins_left-wins_right
        rows.append((fmt,len(sample),wins_left,wins_right,undecided))
    return selected,rows


def _world_cup_groups(matches):
    """Return completed World Cup tournament groups, excluding qualifiers."""
    counts=Counter()
    for m in matches:
        event=str(m.get('event') or '')
        low=event.lower()
        if 'world cup' not in low and 'world twenty20' not in low and 'world t20' not in low:
            continue
        if any(word in low for word in ('qualifier','league','sub regional','region final','division')):
            continue
        women=m.get('gender')=='Women' or 'women' in low
        if 'twenty20' in low or 't20' in low:
            label="Women's T20 World Cup" if women else "Men's T20 World Cup"
        else:
            label="Women's ODI World Cup" if women else "Men's ODI World Cup"
        counts[label]+=1
    return counts


def homepage_insights(matches, match_routes, people, team_routes):
    """Homepage modules built from the same published international records."""
    selected,h2h=_team_record(matches,'India','Australia')
    india_route=team_routes.get('teams',{}).get('India','/teams/')
    australia_route=team_routes.get('teams',{}).get('Australia','/teams/')
    h2h_rows=''.join('<tr><th scope="row">'+fmt+'</th><td>'+str(total)+'</td><td>'+str(india)+' </td><td>'+str(australia)+'</td><td>'+str(other)+'</td></tr>' for fmt,total,india,australia,other in h2h)
    h2h_total=''.join('<span><strong>'+str(sum(row[i] for row in h2h))+'</strong> '+label+'</span>' for i,label in [(1,'matches'),(2,'India wins'),(3,'Australia wins')]) if h2h else '<span><strong>0</strong> recorded meetings</span>'
    world=_world_cup_groups(matches)
    world_rows=''.join('<tr><th scope="row">'+html.escape(name)+'</th><td>'+str(count)+'</td></tr>' for name,count in world.most_common(5))
    world_total=sum(world.values())
    def person(name): return next((p for p in people.values() if p.get('name')==name),None)
    comparisons=[]
    for left,right in [('Sachin Tendulkar','Virat Kohli'),('Mithali Raj','Meg Lanning')]:
        p1,p2=person(left),person(right)
        if not p1 or not p2: continue
        c1=p1.get('career',{});c2=p2.get('career',{})
        fmt='ODI' if 'ODI' in c1 and 'ODI' in c2 else 'Test'
        s1,s2=c1.get(fmt,{}),c2.get(fmt,{})
        comparisons.append((left,right,fmt,s1,s2))
    compare_cards=''
    for left,right,fmt,s1,s2 in comparisons:
        compare_path={'Sachin Tendulkar vs Virat Kohli':'/compare/virat-kohli-vs-sachin-tendulkar/','Mithali Raj vs Meg Lanning':'/compare/mithali-raj-vs-meg-lanning/'}.get(left+' vs '+right,'/compare/')
        compare_cards+='<article class="home-compare-card"><div class="home-compare-head"><span class="eyebrow">'+fmt+' CAREER</span><span class="home-vs">VS</span></div><h3>'+html.escape(left)+' <span>vs</span> '+html.escape(right)+'</h3><table><tbody>'
        for key,label in [('runs','Runs'),('avg','Average'),('hundreds','100s'),('fifties','50s')]:
            compare_cards+='<tr><th>'+label+'</th><td>'+_metric(s1.get(key))+'</td><td>'+_metric(s2.get(key))+'</td></tr>'
        compare_cards+='</tbody></table><a href="'+compare_path+'">Open comparison →</a></article>'
    return f'''<section class="home-insights" aria-labelledby="home-insights-title"><div class="section-heading"><div><p class="eyebrow">THE CRICKET WICKET VIEW</p><h2 id="home-insights-title">Start with the questions that define cricket.</h2><p class="muted">Use the numbers to compare teams, players and the tournaments that shaped the international game.</p></div><a href="/studio/">Build your own chart →</a></div>
      <div class="home-insight-grid"><article class="home-insight-card home-h2h"><div class="home-card-label"><span>TEAM HEAD-TO-HEAD · MEN &amp; WOMEN</span><a href="{html.escape(india_route)}">India</a><b>vs</b><a href="{html.escape(australia_route)}">Australia</a></div><div class="home-h2h-total">{h2h_total}</div><div class="table-wrap"><table><caption>India v Australia results by format</caption><thead><tr><th>Format</th><th>Matches</th><th>India wins</th><th>Australia wins</th><th>Other</th></tr></thead><tbody>{h2h_rows}</tbody></table></div><a class="home-card-link" href="/teams/">Explore every international rivalry →</a></article>
      <article class="home-insight-card home-world"><div class="home-card-label"><span>WORLD CUP ARCHIVE · MEN &amp; WOMEN</span><strong>{world_total:,}</strong><small>recorded matches</small></div><h3>Every World Cup era in one place.</h3><p>Open tournament records, follow scorecards and see how the men’s and women’s global game changed across formats.</p><div class="table-wrap"><table><caption>World Cup matches in the published archive</caption><thead><tr><th>Tournament</th><th>Matches</th></tr></thead><tbody>{world_rows or '<tr><td colspan="2">No tournament label recorded</td></tr>'}</tbody></table></div><a class="home-card-link" href="/series/">Browse World Cup tournaments →</a></article></div>
      <div class="home-comparisons"><div class="section-heading"><div><p class="eyebrow">PLAYER COMPARISONS</p><h3>Great careers, measured clearly.</h3></div><a href="/compare/">Compare any two players →</a></div><div class="grid two">{compare_cards}</div></div></section>'''


def homepage_hero(players, matches):
    return f'''<section class="cricket-hero" aria-labelledby="hero-title" data-cricket-hero>
      <div class="hero-art" aria-hidden="true"><picture><source type="image/webp" srcset="/assets/art/cricket-hero-640.webp 640w, /assets/art/cricket-hero-960.webp 960w, /assets/art/cricket-hero-1536.webp 1536w" sizes="(max-width:700px) 100vw, 60vw"><img src="/assets/art/cricket-hero-1536.webp" width="1536" height="1024" alt="" fetchpriority="high"></picture></div>
      <div class="hero-copy"><p class="hero-kicker"><span></span> THE INTERNATIONAL GAME. EXPLORED.</p>
        <h1 id="hero-title">Every record.<br>Every rivalry.<br><em>A deeper game.</em></h1>
        <p class="hero-description">From the first Test to the next great innings. Discover the players, numbers and moments that make cricket extraordinary.</p>
        <div class="hero-actions"><a class="button hero-primary" href="/players/">Explore the players <span aria-hidden="true">↗</span></a><a class="hero-secondary" href="/records/">Discover records <span aria-hidden="true">→</span></a></div>
        <form class="hero-find" action="/search/"><label for="home-search">YOUR NEXT CRICKET DISCOVERY</label><div><input id="home-search" name="q" placeholder="Search a player, team or ground" required><button aria-label="Search cricket records">→</button></div></form>
      </div>
      <div class="hero-bottom"><span>TEST <b>·</b> ODI <b>·</b> T20I <i>MEN &amp; WOMEN</i></span></div>
    </section>'''


def archive_visuals(matches, routes):
    counts = Counter((m['date'][:3]+'0',m['format'],m['gender']) for m in matches)
    decades = sorted({key[0] for key in counts})
    data = [[decade, fmt, gender, n] for (decade, fmt, gender), n in sorted(counts.items())]
    totals = {decade:sum(n for (d,_,_),n in counts.items() if d==decade) for decade in decades}
    maximum = max(totals.values(), default=1)
    bars = ''.join(f'<div class="archive-column"><strong>{n:,}</strong><i style="--bar-height:{max(1,n/maximum*100):.2f}%"></i><span>{decade}s</span></div>' for decade,n in totals.items())
    rows = ''.join(f'<tr><th scope="row">{d}s</th><td>{n:,}</td></tr>' for d,n in totals.items())
    body = f'''<section class="archive-story panel" id="archive-history" data-archive-story>
      <div class="story-heading"><div><p class="eyebrow">THE SHAPE OF THE GAME</p><h2>A century is just the beginning.</h2><p class="muted">Explore how the published international archive grows through the decades.</p></div>
      <div class="story-filters"><label>Format<select data-chart-format><option value="">All formats</option><option>Test</option><option>ODI</option><option>T20I</option></select></label><label>Players<select data-chart-gender><option value="">Men &amp; women</option><option>Men</option><option>Women</option></select></label></div></div>
      <p class="chart-summary" aria-live="polite"><strong>{len(matches):,}</strong> recorded matches · all formats · men &amp; women</p>
      <div class="archive-scroll" tabindex="0" role="region" aria-label="Recorded matches by decade chart; scroll horizontally on small screens"><div class="archive-bars" aria-hidden="true">{bars}</div></div>
      <details><summary>View chart data</summary><div class="table-wrap"><table><caption>Published match records by decade</caption><thead><tr><th scope="col">Decade</th><th scope="col">Matches</th></tr></thead><tbody data-chart-rows>{rows}</tbody></table></div></details>
      <p class="note">Counts reflect this website’s published match coverage, including no-play records, for the 12 full-member countries. The current decade is incomplete. Career totals use all recognised internationals.</p>
      <script type="application/json" id="archive-chart-data">{json.dumps(data)}</script>
    </section>'''
    first = {}
    for m in sorted(matches, key=lambda m:m['date']):
        first.setdefault((m['format'],m['gender']),m)
    body += '<section class="archive-timeline"><div class="section-heading"><div><p class="eyebrow">FOLLOW THE THREAD</p><h2>Six starting points. One great game.</h2></div></div><p class="muted">The earliest match in each format and gender in our published archive. Open a moment to explore its scorecard.</p><ol class="cricket-timeline">'
    for (fmt,gender),m in sorted(first.items(), key=lambda item:item[1]['date']):
        url = routes[m['id']]
        body += f'<li><span class="timeline-year">{m["date"][:4]}</span><a href="{html.escape(url,quote=True)}"><span class="eyebrow">{gender.upper()} · {fmt}</span><h3>{html.escape(" v ".join(m["teams"]))}</h3><time datetime="{m["date"]}">{m["date"]}</time><span class="timeline-arrow" aria-hidden="true">↗</span></a></li>'
    return body + '</ol></section>'
