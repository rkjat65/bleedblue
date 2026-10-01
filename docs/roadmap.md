# Crickrida product roadmap

Goal: one cricket site at crickrida.com, the most complete reference short of live scores. Every page is format-first (Test, ODI, T20I, IPL, T20 World Cup), pre-rendered where people search, crawlable and honest about coverage.

## One site (October 2026)

crickrida.com is a single site with a single brand. Caddy on the Oracle server routes by path:

- `/api`, `/app`, `/ipl`, `/t20-world-cup` go to the crickrida app container (repo IPL-Analytics). The app's pre-merge addresses 301 to their `/ipl` or `/t20-world-cup` form.
- `/lake` goes to the analytics lake on Cloudflare R2.
- Everything else is this archive, served from `/srv/crickrida/site` on the server. Each audited release is uploaded to R2 by content hash (`tools/publish_site.py`, manifest written last) and the `crickrida-site-sync` timer applies it within two minutes. Every canonical points at crickrida.com.
- cricket.rkjat.in: GitHub Pages still receives each release there as a fallback. Once its DNS A record points at the server, Caddy answers it with a plain 301 to the same path on crickrida.com.
- The Caddy config, the sync job and its timer live in IPL-Analytics `deploy/` and are applied by `.github/workflows/domain.yml`.

Merge steps:

1. Done: one domain, one brand, shared navigation, redirects from both old addresses.
   Brand: the "Play K" mark (tools/brand_mark.py) in both headers, icons and share images; the analytics section uses the site header plus a sticky section bar; the homepage hero has no player cut-out.
2. Done: one page per player, team and ground. Player profiles carry IPL and T20 World Cup tabs, IPL grounds an IPL tab, national teams a T20 World Cup tab.
   The app exports them from its ball-by-ball databases (`/api/export/careers`, `/venues`, `/teams`, keyed by Cricsheet id); `tools/fetch_league_careers.py` snapshots them into `data/leagues/` during the weekly refresh and keeps the last good copy if the app is down.
   Matches played come from stored line-ups, so players who only fielded are counted. IPL grounds map to archive grounds through `tools/venues.py`.
3. Done: the app's interactive tools run on the shared Parquet lake as one page each for every competition: `/matchups/`, `/phases/`, `/fantasy/`, `/quiz/`, and Studio gained the IPL. A `/tools/` hub replaces Studio in the site menu.
   `tools/build_ball_lake.py` builds the ball-by-ball tables (matchups, phases by player and team, overs, fantasy points, IPL scorecards) from Cricsheet's six international zips and the IPL zip, plus the reconstructed men's T20 World Cup matches; the weekly Cricsheet downloads are cached in CI and only new content-addressed files go to R2.
   The app's `/ipl` and `/t20-world-cup` tool addresses 301 to these pages with the matching competition filter (player names become Cricsheet ids); its stat-card studio goes to Studio with the IPL or T20I format.
4. Done: one host, one analytics property, one set of policies. The archive is served from the server, not proxied from GitHub Pages. Every page reports to Google Analytics property G-DXRDX6R7YY through `web/analytics.js`, with one opt-out; the app's G-4V7XW1QPZ8 is retired. `/privacy/`, `/terms/` and `/account-deletion/` cover the site and the mobile app, and the app's addresses 301 to them. cricket.rkjat.in becomes a plain 301 when its DNS moves.
5. Retire the app's front end: rebuild the remaining `/ipl` and `/t20-world-cup` pages (overview, matches and scorecards, batting and bowling, players, teams, venues, seasons, head to head, insights, pulse, records, impact ratings) as static pages here, keep the API for the mobile app, then 301 the React routes and drop the container's page rendering.

## Shipped (September 2026)

- **Player profiles**: masthead, sticky Overview / Test / ODI / T20I switch, per-format official line, hero tiles, career arc and by-year charts, form, score distribution, dismissals, batting position, tabbed splits (opposition, home and away, batting first or chasing, position, result, year, ground, series), milestones, best performances, latest matches.
- **Match scorecards**: overs and run rate, toss, player of the match, extras breakdown, fall of wickets, did-not-bat, super-over results, partnerships naming both batters, SportsEvent competitors.
- **Team, ground, series and head-to-head pages**: format panels with men and women separate; records by opponent, venue, toss, year; totals, chases and margins; leading players; series editions with scorelines.
- **Records hub**: category index; sixteen career leaderboards; highest scores, strike rate, sixes, best bowling, calendar-year runs and wickets, partnerships, team totals, chases and margins, each with team, opponent, ground and year filters.
- **Ground names**: 667 recorded spellings resolve to 402 grounds; retired ground URLs redirect to the canonical page.
- **Ground facts**: `tools/fetch_ground_facts.py` pulls city, country, capacity, opening year, bowling ends and coordinates from Cricinfo-derived metadata, Wikidata and the Wikipedia infobox into `data/ground_facts.json`; ground mastheads, index cards, meta descriptions and StadiumOrArena schema use them. Rerun with `--retry-unmatched` after improving the matcher, `--refresh` to refetch everything.
- **Homepage**: one hero figure with record tiles and search, icons rail, fixtures, results, the three formats side by side, a records grid, rivalries, featured scorecard, leaders and explore tiles. The section rail only appears when the viewport has a real gutter.
- **Compare**: curated pages for two or three players with an Overview / Test / ODI / T20I switch, best figure marked in every row, normalised measure bars, a cumulative year-by-year overlay and a batting average by opponent table; the tool at /compare/ takes up to three players with the same views.
- **Light theme**: the same tokens drive both themes; headings and numerals use the same families in light.
- **Studio**: builder rail with templates, up to six players, any number of measures on one canvas (bars with side figures, grouped bars, small multiples, columns, line, table, headline, match card), Visual / Table / SQL tabs, four themes, PNG, SVG and CSV exports, shareable setup links.
- Host country resolved for every full-member match; archive rows carry maidens, series name and real result labels; neutral stat tiles with format colours instead of the neon rainbow.

## Next

1. **Ambiguous short venue names**: Hyderabad and Wellington ODIs once sources confirm the ground.
2. **Player pages**: captaincy and wicketkeeping splits when the source data carries them; a "similar players" module from the career table.

## Working notes

- Full build is about six minutes; `python tools/audit_site.py` another ten. Scratch harnesses render single pages from `_site` JSON in seconds.
- Budgets: 300 KB raw per player page, 2.2 GB for the publication (compressed transfer is roughly an eighth of that).
- Placeholders are a plain hyphen; N/A means there is no denominator.
