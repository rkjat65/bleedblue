"""Markup for the client-side Men's T20 World Cup analysis dashboard."""


def dashboard_markup():
    return '''
<section class="wc-dash-hero">
  <div>
    <p class="eyebrow">MEN'S T20 WORLD CUP · BALL BY BALL</p>
    <h1>The tournament, delivery by delivery</h1>
    <p>Explore every edition from 2007 to 2026: team results, innings peaks, batting, bowling and phase-by-phase patterns.</p>
  </div>
  <div class="wc-dash-controls">
    <label for="wc-edition">Edition</label>
    <select id="wc-edition"><option value="all">All editions</option></select>
    <span id="wc-status" role="status" aria-live="polite">Loading verified deliveries…</span>
  </div>
</section>

<div id="wc-dashboard" class="wc-dashboard" data-source="/data/t20wc-deliveries.json">
  <section class="wc-kpis" aria-label="Tournament totals">
    <article><span>Matches</span><strong data-kpi="matches">—</strong><small>with deliveries</small></article>
    <article><span>Runs</span><strong data-kpi="runs">—</strong><small>all innings</small></article>
    <article><span>Wickets</span><strong data-kpi="wickets">—</strong><small>team wickets</small></article>
    <article><span>Boundaries</span><strong data-kpi="boundaries">—</strong><small>fours + sixes</small></article>
    <article><span>Avg innings</span><strong data-kpi="average">—</strong><small>runs per innings</small></article>
    <article><span>Sixes</span><strong data-kpi="sixes">—</strong><small>cleared the rope</small></article>
  </section>

  <section class="wc-spotlights" aria-label="Tournament leaders">
    <article><span>Highest total</span><strong data-spot="total">—</strong><small data-spot-note="total"></small></article>
    <article><span>Most sixes</span><strong data-spot="sixes">—</strong><small data-spot-note="sixes"></small></article>
    <article><span>Most fours</span><strong data-spot="fours">—</strong><small data-spot-note="fours"></small></article>
    <article><span>Most wickets</span><strong data-spot="wickets">—</strong><small data-spot-note="wickets"></small></article>
  </section>

  <section class="wc-dashboard-grid">
    <article class="wc-card wc-chart-card">
      <div class="wc-card-head"><div><span>TEAM CONTROL</span><h2>Most match wins</h2></div><small>selected editions</small></div>
      <div id="wc-team-wins" class="wc-bars" role="img" aria-label="Match wins by team"></div>
    </article>
    <article class="wc-card wc-chart-card">
      <div class="wc-card-head"><div><span>THE TROPHY</span><h2>Titles by team</h2></div><small>official record</small></div>
      <div id="wc-titles" class="wc-bars wc-bars-gold" role="img" aria-label="Men's T20 World Cup titles by team"></div>
    </article>
  </section>

  <section class="wc-card">
    <div class="wc-card-head"><div><span>INNINGS SHAPE</span><h2>Where matches move</h2></div><small>legal balls only</small></div>
    <div id="wc-phases" class="wc-phase-grid"></div>
  </section>

  <section class="wc-dashboard-grid wc-leader-grid">
    <article class="wc-card">
      <div class="wc-card-head"><div><span>BATTERS</span><h2>Run leaders</h2></div><small>click a heading to sort</small></div>
      <div class="wc-table-scroll"><table id="wc-batting" class="wc-table"><thead><tr><th data-key="name">Batter</th><th data-key="runs">Runs</th><th data-key="average">Avg</th><th data-key="strikeRate">SR</th><th data-key="fifties">50s</th><th data-key="hundreds">100s</th><th data-key="sixes">6s</th></tr></thead><tbody></tbody></table></div>
    </article>
    <article class="wc-card">
      <div class="wc-card-head"><div><span>BOWLERS</span><h2>Wicket leaders</h2></div><small>click a heading to sort</small></div>
      <div class="wc-table-scroll"><table id="wc-bowling" class="wc-table"><thead><tr><th data-key="name">Bowler</th><th data-key="wickets">Wkts</th><th data-key="average">Avg</th><th data-key="economy">Econ</th><th data-key="strikeRate">SR</th><th data-key="fourW">4W</th><th data-key="fiveW">5W</th></tr></thead><tbody></tbody></table></div>
    </article>
  </section>

  <section class="wc-card">
    <div class="wc-card-head"><div><span>MATCH ARCHIVE</span><h2>Latest matches in this view</h2></div><small id="wc-match-count"></small></div>
    <div id="wc-matches" class="wc-match-grid"></div>
  </section>

  <section class="wc-data-note">
    <strong>Data you can audit</strong>
    <p>Cricsheet supplies the primary delivery archive. Afghanistan matches absent there are reconstructed from public ESPN play-by-play facts and accepted only when innings totals, wickets and balls reconcile with an independent scorecard. Commentary text is not stored.</p>
    <p id="wc-coverage-note"></p>
  </section>
</div>
'''
