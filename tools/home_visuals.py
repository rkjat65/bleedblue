"""Server-rendered homepage art and charts, using publication records only."""
import html
import json
from collections import Counter


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
