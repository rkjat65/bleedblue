"""Server-rendered homepage modules, using publication records only."""
import html
import json
from collections import Counter

FORMAT_KEY = {'Test': 'test', 'ODI': 'odi', 'T20I': 't20i'}


def _metric(value):
    return '-' if value is None else f'{value:,}' if isinstance(value, int) else f'{value:.2f}' if isinstance(value, float) else str(value)


def _e(value):
    return html.escape(str(value if value is not None else ''), quote=True)


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
    """Count classified World Cup matches, including attached Afghanistan games."""
    from world_cup import FAMILIES, classify
    labels={key:label for key,label,*_ in FAMILIES}
    data=classify(matches)
    return Counter({labels[key]:len(rec['matches']) for key,rec in data.items()})


def homepage_insights(matches, match_routes, people, team_routes, official_h2h=None):
    """Homepage modules built from official records first, archive coverage second."""
    selected,h2h=_team_record(matches,'India','Australia')
    if official_h2h:
        h2h=official_h2h
    india_route=team_routes.get('teams',{}).get('India','/teams/')
    australia_route=team_routes.get('teams',{}).get('Australia','/teams/')
    h2h_total=''.join('<span><strong>'+str(sum(row[i] for row in h2h))+'</strong> '+label+'</span>' for i,label in [(1,'matches'),(2,'India wins'),(3,'Australia wins')]) if h2h else '<span><strong>0</strong> recorded meetings</span>'
    h2h_max=max((max(row[2],row[3],row[4]) for row in h2h),default=1)
    h2h_chart=''.join('<div class="home-format-bar"><div class="home-format-label"><strong>'+fmt+'</strong><span>India '+str(india)+' · Australia '+str(australia)+' · Other '+str(other)+'</span></div><div class="home-dual-track" aria-hidden="true"><i class="home-bar-india" style="width:'+f'{india/h2h_max*100:.1f}'+'%"></i><i class="home-bar-australia" style="width:'+f'{australia/h2h_max*100:.1f}'+'%"></i><i class="home-bar-other" style="width:'+f'{other/h2h_max*100:.1f}'+'%"></i></div></div>' for fmt,total,india,australia,other in h2h)
    world=_world_cup_groups(matches)
    world_total=sum(world.values())
    world_max=max(world.values(),default=1)
    world_chart=''.join('<div class="home-world-bar"><span>'+html.escape(name)+'</span><div class="home-world-track"><i style="width:'+f'{count/world_max*100:.1f}'+'%"></i></div><strong>'+str(count)+'</strong></div>' for name,count in world.most_common(5))
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
    return f'''<section class="home-insights" aria-labelledby="home-insights-title"><div class="section-heading"><div><p class="eyebrow">FEATURED RECORDS</p><h2 id="home-insights-title">Compare teams, players and tournaments</h2></div><a href="/studio/">Build a chart →</a></div>
      <div class="home-insight-grid"><article class="home-insight-card home-h2h"><div class="home-card-label"><span>TEAM HEAD-TO-HEAD · OFFICIAL</span><a href="{html.escape(india_route)}">India</a><b>vs</b><a href="{html.escape(australia_route)}">Australia</a></div><div class="home-h2h-total">{h2h_total}</div><figure class="home-chart" aria-label="India and Australia wins by format"><figcaption>Official wins by format</figcaption>{h2h_chart}</figure><a class="home-card-link" href="/head-to-head/">Explore every international rivalry →</a></article>
      <article class="home-insight-card home-world"><div class="home-card-label"><span>WORLD CUP RECORDS</span><strong>{world_total:,}</strong><small>tournament matches in this archive</small></div><h3>World Cup results and winners</h3><figure class="home-chart home-world-chart" aria-label="World Cup matches by tournament category"><figcaption>Recorded World Cup matches by tournament</figcaption>{world_chart}</figure><a class="home-card-link" href="/world-cup/">World Cup winners and records →</a></article></div>
      <div class="home-comparisons"><div class="section-heading"><div><p class="eyebrow">PLAYER COMPARISONS</p><h3>Career records by format</h3></div><a href="/compare/">Compare any two players →</a></div><div class="grid two">{compare_cards}</div></div></section>'''


def homepage_hero(stats, board, quick=None):
    """Headline, search and the career record holders on a plain panel, the same layout as the
    World Cup page, then the archive in numbers. No artwork and no motion: the figures lead.
    stats: [(label, value_text)]; board: [(fmt, label, value, name, url)]."""
    quick_items = ''.join(f'<li><a href="{_e(url)}">{_e(label)}</a></li>' for label, url in (quick or []))
    rows = ''.join(f'<a class="hb-row fmt-{FORMAT_KEY.get(fmt, "odi")}" href="{_e(url)}"><span>{_e(label)}</span><strong>{value:,}</strong><em>{_e(name)}</em></a>'
                   for fmt, label, value, name, url in board)
    facts = ''.join(f'<div><strong>{_e(value)}</strong><span>{_e(label)}</span></div>' for label, value in stats)
    return f'''<section class="home-hero" aria-labelledby="hero-title">
      <div class="home-hero-copy"><p class="eyebrow">INTERNATIONAL CRICKET · MEN AND WOMEN · TEST, ODI AND T20I</p>
        <h1 id="hero-title">Every run. Every wicket. <em>Every match.</em></h1>
        <p class="home-lede">Official career figures, ball-by-ball scorecards, rivalries and records, every one split by format.</p>
        <form class="hero-find" action="/search/" role="search"><label for="home-search">Search the archive</label><div><input id="home-search" name="q" type="search" placeholder="Player, team, ground or match" required autocomplete="off"><kbd aria-hidden="true">/</kbd><button type="submit">Search</button></div></form>
        <ul class="hero-quick" aria-label="Popular">{quick_items}<li><a href="/head-to-head/">India v Australia</a></li><li><a href="/records/">Records</a></li><li><a href="/world-cup/">World Cups</a></li></ul>
      </div>
      <aside class="home-board" aria-labelledby="board-title"><p class="eyebrow" id="board-title">CAREER RECORD HOLDERS</p>{rows}<a class="hb-more" href="/records/">Every record by format →</a></aside>
    </section>
    <div class="wc-facts home-facts" aria-label="The archive in numbers">{facts}</div>'''


def icons_rail(icons):
    """icons: [(name, src, href, stat_value, stat_label, team)]."""
    if not icons:
        return ''
    cards = ''
    for i, (name, src, href, value, label, team) in enumerate(icons):
        cards += (f'<li style="--i:{i}"><a class="icon-card" href="{_e(href)}"><img src="{_e(src)}" width="210" height="240" alt="" loading="lazy" decoding="async">'
                  f'<span class="icon-team">{_e(team)}</span><strong>{_e(name)}</strong><span class="icon-stat"><b>{_e(value)}</b> {_e(label)}</span></a></li>')
    return f'''<section class="arena-section home-icons" id="icons" aria-labelledby="icons-title">
      <div class="section-heading"><div><p class="eyebrow">THE ICONS</p><h2 id="icons-title">Start with the greats</h2></div><a href="/players/">All players →</a></div>
      <ol class="icons-rail" tabindex="0" aria-label="Featured players">{cards}</ol>
    </section>'''


def format_trio(counts, leaders, links):
    """counts: {fmt: {'Men': n, 'Women': n}}; leaders: {fmt: {gender: [(label, name, value, url), ...]}}."""
    tiles = ''
    blurb = {'Test': 'Five days, two innings each, the original examination.', 'ODI': 'Fifty overs a side, World Cups since 1975.', 'T20I': 'Twenty overs, the fastest-growing format.'}
    for fmt in ('Test', 'ODI', 'T20I'):
        c = counts.get(fmt, {})
        rows = ''
        for gender in ('Men', 'Women'):
            for label, name, value, url in leaders.get(fmt, {}).get(gender, []):
                rows += f'<div class="ft-row"><span>{_e(gender)} · {_e(label)}</span><a href="{_e(url)}">{_e(name)}</a><b>{value:,}</b></div>'
        tiles += (f'<article class="format-tile fmt-{FORMAT_KEY[fmt]}"><div class="ft-head"><span class="ft-kicker">{_e(fmt.upper())}</span><strong>{c.get("Men", 0) + c.get("Women", 0):,}</strong><small>matches recorded · {c.get("Men", 0):,} men · {c.get("Women", 0):,} women</small></div>'
                  f'<p>{_e(blurb[fmt])}</p><div class="ft-rows">{rows}</div><div class="ft-links">' + ''.join(f'<a href="{_e(url)}">{_e(label)}</a>' for label, url in links.get(fmt, [])) + '</div></article>')
    return f'''<section class="arena-section home-formats" id="formats" aria-labelledby="formats-title">
      <div class="section-heading"><div><p class="eyebrow">THREE FORMATS</p><h2 id="formats-title">Test, ODI and T20I, side by side</h2></div><a href="/records/">All records →</a></div>
      <div class="format-trio">{tiles}</div>
    </section>'''


def records_grid(tiles):
    """tiles: [(fmt, kind_label, [(gender, value_text, name, detail, url), ...])]."""
    if not tiles:
        return ''
    cells = ''
    for fmt, kind, entries in tiles:
        if not entries:
            continue
        lead = entries[0]
        rest = ''.join(f'<span class="rg-alt"><em>{_e(g)}</em> <b>{_e(v)}</b> {_e(n)}<small>{_e(d)}</small></span>' for g, v, n, d, u in entries[1:])
        cells += (f'<a class="rg-tile fmt-{FORMAT_KEY[fmt]}" href="{_e(lead[4])}"><span class="rg-kicker">{_e(fmt.upper())} · {_e(kind.upper())}</span>'
                  f'<strong>{_e(lead[1])}</strong><span class="rg-name">{_e(lead[2])}</span><small>{_e(lead[3])}</small>{rest}<span class="rg-go">Full list →</span></a>')
    return f'''<section class="arena-section home-records" id="records-grid" aria-labelledby="records-grid-title">
      <div class="section-heading"><div><p class="eyebrow">RECORDS THAT MATTER</p><h2 id="records-grid-title">The numbers every fan asks for</h2></div><a href="/records/">Records hub →</a></div>
      <div class="records-tiles">{cells}</div>
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
      <div class="story-heading"><div><p class="eyebrow">MATCH COVERAGE</p><h2>Matches by decade</h2><p class="muted">Published international match records by format and gender.</p></div>
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
    body += '<section class="archive-timeline"><div class="section-heading"><div><p class="eyebrow">EARLIEST MATCHES</p><h2>First available scorecard by format</h2></div></div><p class="muted">The earliest published men’s and women’s match in each format.</p><ol class="cricket-timeline">'
    for (fmt,gender),m in sorted(first.items(), key=lambda item:item[1]['date']):
        url = routes[m['id']]
        body += f'<li><span class="timeline-year">{m["date"][:4]}</span><a href="{html.escape(url,quote=True)}"><span class="eyebrow">{gender.upper()} · {fmt}</span><h3>{html.escape(" v ".join(m["teams"]))}</h3><time datetime="{m["date"]}">{m["date"]}</time><span class="timeline-arrow" aria-hidden="true">↗</span></a></li>'
    return body + '</ol></section>'
