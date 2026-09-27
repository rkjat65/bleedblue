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
      <div class="home-insight-grid"><article class="home-insight-card home-h2h"><div class="home-card-label"><span>TEAM HEAD-TO-HEAD · OFFICIAL</span><a href="{html.escape(india_route)}">India</a><b>vs</b><a href="{html.escape(australia_route)}">Australia</a></div><div class="home-h2h-total">{h2h_total}</div><figure class="home-chart" aria-label="India and Australia wins by format"><figcaption>Official wins by format</figcaption>{h2h_chart}</figure><a class="home-card-link" href="/teams/">Explore every international rivalry →</a></article>
      <article class="home-insight-card home-world"><div class="home-card-label"><span>WORLD CUP RECORDS</span><strong>{world_total:,}</strong><small>tournament matches in this archive</small></div><h3>World Cup results and winners</h3><figure class="home-chart home-world-chart" aria-label="World Cup matches by tournament category"><figcaption>Recorded World Cup matches by tournament</figcaption>{world_chart}</figure><a class="home-card-link" href="/world-cup/">World Cup winners and records →</a></article></div>
      <div class="home-comparisons"><div class="section-heading"><div><p class="eyebrow">PLAYER COMPARISONS</p><h3>Career records by format</h3></div><a href="/compare/">Compare any two players →</a></div><div class="grid two">{compare_cards}</div></div></section>'''


HERO_DELIVERY = '''<svg class="hero-delivery" viewBox="0 0 1280 470" preserveAspectRatio="xMaxYMid slice" aria-hidden="true" focusable="false">
        <defs><radialGradient id="hd-ball" cx="35%" cy="35%" r="70%"><stop offset="0" stop-color="#ffb4a8"/><stop offset=".45" stop-color="#e5322d"/><stop offset="1" stop-color="#7a0f12"/></radialGradient>
        <linearGradient id="hd-trail" x1="0" x2="1"><stop offset="0" stop-color="#7cc4ff" stop-opacity="0"/><stop offset="1" stop-color="#fff2c7" stop-opacity=".95"/></linearGradient>
        <filter id="hd-glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"/></filter></defs>
        <g class="hd-lights"><circle cx="820" cy="96" r="3"/><circle cx="846" cy="92" r="2.4"/><circle cx="872" cy="99" r="2.8"/><circle cx="905" cy="140" r="2.2"/><circle cx="932" cy="137" r="2.6"/><circle cx="1090" cy="118" r="2.4"/></g>
        <path id="hd-path" class="hd-path" d="M560 150 Q 820 60 1010 402 Q 1080 300 1210 318" pathLength="100"/>
        <path class="hd-trail" d="M560 150 Q 820 60 1010 402 Q 1080 300 1210 318" pathLength="100"><animate attributeName="stroke-dashoffset" values="100;0;0;-100" keyTimes="0;.62;.7;1" dur="4.2s" repeatCount="indefinite"/></path>
        <ellipse class="hd-bounce" cx="1010" cy="406" rx="4" ry="1.5"><animate attributeName="rx" values="0;0;38;52" keyTimes="0;.42;.5;1" dur="4.2s" repeatCount="indefinite"/><animate attributeName="opacity" values="0;0;.9;0" keyTimes="0;.42;.46;.8" dur="4.2s" repeatCount="indefinite"/></ellipse>
        <g class="hd-ball"><circle r="16" fill="#ff6a4d" opacity=".45" filter="url(#hd-glow)"/><circle r="9" fill="url(#hd-ball)"/><path d="M-6 -6 Q 0 0 -6 6 M6 -6 Q 0 0 6 6" stroke="#fff6" stroke-width="1.2" fill="none"><animateTransform attributeName="transform" type="rotate" from="0" to="720" dur="4.2s" repeatCount="indefinite"/></path>
          <animateMotion dur="4.2s" repeatCount="indefinite" keyPoints="0;1;1" keyTimes="0;.62;1" calcMode="linear"><mpath href="#hd-path"/></animateMotion>
          <animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;.04;.6;.66;1" dur="4.2s" repeatCount="indefinite"/></g>
        <g class="hd-impact" transform="translate(1212 318)"><circle r="10" class="hd-ring"><animate attributeName="r" values="0;0;70" keyTimes="0;.62;.9" dur="4.2s" repeatCount="indefinite"/><animate attributeName="opacity" values="0;0;1;0" keyTimes="0;.61;.63;.9" dur="4.2s" repeatCount="indefinite"/></circle>
          <g class="hd-sparks">''' + ''.join(f'<line x1="0" y1="0" x2="{x}" y2="{y}"><animate attributeName="opacity" values="0;0;1;0" keyTimes="0;.62;.64;.85" dur="4.2s" repeatCount="indefinite"/><animateTransform attributeName="transform" type="scale" values="0;0;1;1.5" keyTimes="0;.62;.7;1" dur="4.2s" repeatCount="indefinite"/></line>' for x,y in [(-40,-34),(-52,4),(-30,38),(36,-44),(50,-8),(26,40),(0,-56)]) + '''</g>
          <rect class="hd-bail" x="-22" y="-62" width="22" height="6" rx="3"><animateTransform attributeName="transform" type="translate" values="0 0;0 0;-60 -90;-110 -40" keyTimes="0;.62;.8;1" dur="4.2s" repeatCount="indefinite"/><animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;.61;.63;.9;1" dur="4.2s" repeatCount="indefinite"/></rect>
          <rect class="hd-bail" x="2" y="-62" width="22" height="6" rx="3"><animateTransform attributeName="transform" type="translate" values="0 0;0 0;50 -110;90 -60" keyTimes="0;.62;.8;1" dur="4.2s" repeatCount="indefinite"/><animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;.61;.63;.9;1" dur="4.2s" repeatCount="indefinite"/></rect></g>
      </svg>'''


def _hero_facts(facts):
    if not facts:
        return ''
    chips = ''.join(
        f'<a class="hero-fact" href="{html.escape(url, quote=True)}" style="--i:{i}"><strong data-count="{value}">{value:,}</strong>'
        f'<span>{html.escape(label)}</span><em>{html.escape(name)}</em></a>'
        for i, (value, label, name, url) in enumerate(facts[:3]))
    return f'<div class="hero-facts" aria-label="Record holders">{chips}</div>'


def homepage_hero(player_count, match_count, faces=None, facts=None, quick=None):
    cast = ''
    if faces:
        items = ''
        for index, (name, src, href) in enumerate(faces[:8]):
            load = 'eager' if index < 4 else 'lazy'
            items += (
                f'<a class="hero-face" href="{html.escape(href, quote=True)}" style="--i:{index}">'
                f'<img src="{html.escape(src, quote=True)}" width="420" height="480" alt="{html.escape(name)}" loading="{load}" decoding="async">'
                f'<span>{html.escape(name)}</span></a>'
            )
        cast = f'<div class="hero-stage" aria-hidden="true"></div><div class="hero-cast" aria-label="Featured international players">{items}</div>'
    return f'''<section class="cricket-hero" aria-labelledby="hero-title" data-cricket-hero>
      <div class="hero-art" aria-hidden="true"><picture><source type="image/webp" srcset="/assets/art/cricket-hero-640.webp 640w, /assets/art/cricket-hero-960.webp 960w, /assets/art/cricket-hero-1536.webp 1536w" sizes="(max-width:700px) 100vw, 60vw"><img src="/assets/art/cricket-hero-1536.webp" width="1536" height="1024" alt="" fetchpriority="high"></picture></div>
      <div class="hero-copy"><p class="hero-kicker"><span></span> INTERNATIONAL CRICKET</p>
        <h1 id="hero-title">Every run. Every wicket.<br><em>Every match.</em></h1>
        <p class="hero-description">Men’s and women’s Tests, ODIs and T20Is. Career records, head-to-heads and ball-by-ball scorecards with match charts.</p>
        <ul class="hero-quick" aria-label="Popular">{''.join(f'<li><a href="{html.escape(url, quote=True)}">{html.escape(label)}</a></li>' for label, url in (quick or []))}<li><a href="/head-to-head/">India v Australia</a></li><li><a href="/world-cup/">World Cups</a></li></ul>
        <div class="hero-actions"><a class="button hero-primary" href="/players/">Explore the players <span aria-hidden="true">↗</span></a><a class="hero-secondary" href="/matches/">Open a scorecard <span aria-hidden="true">→</span></a></div>
        <form class="hero-find" action="/search/" role="search"><label for="home-search">Search the archive</label><div><input id="home-search" name="q" type="search" placeholder="Search a player, team or match…" required autocomplete="off"><kbd aria-hidden="true">/</kbd><button type="submit">Search</button></div></form>
      </div>
      {cast}
      {HERO_DELIVERY}
      {_hero_facts(facts)}
      <button type="button" class="hero-motion" data-hero-motion aria-pressed="false">Pause motion</button>
      <div class="hero-bottom"><span><strong data-count="{player_count}">{player_count:,}</strong> PLAYERS <b>·</b> <strong data-count="{match_count}">{match_count:,}</strong> MATCHES <b>·</b> TEST · ODI · T20I <i>MEN &amp; WOMEN</i></span></div>
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
