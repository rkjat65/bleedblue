# Cricket Wicket — International Cricket

A responsive international cricket portal with a separate India records hub. IPL remains on [Crickrida](https://crickrida.rkjat.in).

## Build and run locally

```powershell
python -m pip install -r tools/requirements.txt
python tools/build_site.py
python tools/audit_site.py
python serve.py --built
```

Open http://127.0.0.1:8765. The source-only legacy preview is still available with `python serve.py`.

## Publication

The generated `_site/` is ignored by Git. GitHub Actions validates the data, builds the site and publishes the artifact through GitHub Pages. Pushes to `main` publish the current snapshot. Monday's scheduled run (02:15 UTC) and a manual workflow run with **refresh** enabled import fresh data in an isolated temporary directory. Incomplete scopes, suspicious count decreases, regression failures or a failed publication audit prevent deployment. The existing live artifact stays available. A successful refresh commits validated data back to `main` before deployment.

Generated player, scorecard, historical-result, team, ground, series, record and curated-comparison pages contain their main statistics in HTML. Each has its own canonical URL, metadata and sitemap entry. Content hashes preserve sitemap modification dates for unchanged pages. Old player IDs and international match/hash URLs resolve to the new routes through the compatibility entry pages.

- `/players/`: paginated directory, career totals, full available batting/bowling/fielding records and player-specific archive analysis.
- `/matches/`: searchable results and scorecards, with historical result-only coverage labeled.
- `/teams/`, `/grounds/`, `/series/`: linked international entities and matching results.
- `/records/`: 36 men's/women's format-specific career leaderboards with qualifications and ties.
- `/compare/`: career or archive comparisons with format, year, opponent and minimum-innings filters.
- `/insights/`: reproducible statistical explainers linked to the record tables.
- `/saved/`: browser-local saved pages and filtered research.
- `/embed/?player=/players/virat-kohli/`: lightweight player career card; use **Embed career card** on any profile.
- `/corrections/`: download a structured correction report. No submission backend is configured.
- `/methodology/`: coverage, definitions and freshness.
- `/overview/`: original India archive.

Tables support sorting of displayed rows and CSV export. Filtered exports include all matching rows. Player charts also export to SVG. Dark mode, mobile navigation, sticky table columns and keyboard controls use the same shared shell.

## Dataset and refresh

The 5 September 2026 snapshot includes **12,411 sourced career profiles** across all 18 batting, bowling and fielding tables, and **16,958 match records** dating back to 1877. It adds 4,167 historical players and 7,189 historical results to the original archive. Another 43 archive identities have no matched career table row; they remain searchable and are listed in `data/unmatched_players.json`.

Three independent layers power the portal. Player profiles and comparisons default to ESPNcricinfo Statsguru career records, linked to Cricsheet IDs through the public player register. Historical match results extend the catalog beyond available delivery files. Cricsheet provides 9,769 local ball-data scorecards and their separately selectable player aggregates.

```powershell
python -m pip install -r tools/requirements.txt
python tools/build_international.py --refresh
python tools/import_careers.py
python tools/import_match_catalog.py
python tools/build_record_layers.py
python -m unittest discover -s tests -v
node tests/test_record_layers.js
```

Career and historical importers cache parsed source pages in ignored `.data-cache/careers/` and follow source pagination. Rerunning resumes cached scopes, including failed requests. Use `import_careers.py --refresh` to replace career snapshots. For a complete fresh import use `python tools/refresh_data.py`; it isolates the source cache and validates all scopes before copying data into the working tree. Review changes before committing outside CI.

`data/career_manifest.json` and `data/historical_manifest.json` give current counts, scope status and provenance. `data/careers.json` stores batting, bowling and fielding career records; `data/historical_matches.json` contains additional result-only matches. The original `data/international.json` and lazy-loaded `data/scorecards/` remain the ball-data layer. Small home payloads avoid downloading the full catalogs on the homepage.

Missing source values remain null. Archive figures are never substituted for or added to career totals. All-format averages use summed numerators and denominators; missing denominators produce a dash. Stable source IDs prevent name-based accidental player merges. Source tables can change between requests; conflicting match counts are flagged. A source-complete career import does not imply a complete local match-by-match history.

Historical result entries link to their source scorecard but do not invent innings totals, lineups or commentary. The site is not a live-score, future-fixture, rankings or news service. Legacy India data remains separately dated and is not combined with these career records.

## Verification

The test suite validates source counts, unique IDs, scorecard and playing-XI references, innings totals, bowling balls, wickets, player aggregates and the small homepage summary. Browser checks cover match filters, innings switching, search, player comparison and responsive layouts.

## Static hosting

Serve the repository root on a static host. The new portal uses static paths and query-string details. The existing `404.html` hands legacy India detail routes to the archive router for GitHub Pages. The production site is published from the main branch to https://cricket.rkjat.in/.

## Legacy India archive notes

## Features

| Area | What’s included |
|------|------------------|
| **Official Records** | Test / ODI / T20I career W–L, top-10 bat & bowl, landmarks, trophies |
| **Tournaments** | World Cup, T20 World Cup, Champions Trophy, WTC hubs |
| **Captaincy & fielding** | Leadership notes + keeping/fielding icons |
| **Series** | 200 series/events from the archive with drill-down |
| **Match centre** | Score summary, XI, bat/bowl cards, quality badge |
| **Player profiles** | Career by format, PoM, recent XI appearances |
| **Archive analytics** | Batting, bowling, fielding, H2H, venues, records |
| **Search** | Players, matches, series |
| **Coverage** | Full / partial / empty ball data vs official career totals |
| **About** | Methodology, sources, last generated timestamp |

## Quick start (local)

```bash
python serve.py
```

Open **http://127.0.0.1:8765** (or `#view=official`).

> Browsers block `fetch()` of local JSON via `file://`. Always serve over HTTP.

## GitHub Pages + custom domain

1. Deploy from branch `main` → `/` (root).
2. Custom domain: **`cricket.rkjat.in`** (`CNAME` file in repo).
3. DNS for `rkjat.in` (Hostinger / same as other subdomains):

   | Type | Name | Target |
   |------|------|--------|
   | `CNAME` | `cricket` | `rkjat65.github.io` |

4. Enforce HTTPS after DNS is green.

## Project structure

```
index.html / styles.css / app.js   # SPA (hash routing)
stats.json                         # Pre-aggregated archive (~3MB)
official_records.json              # Official career / tournaments
player_images.json + images/       # Portraits + hero art
build_stats.py                     # Rebuild stats from match JSON
fetch_*.py                         # Offline recovery helpers
robots.txt / sitemap.xml / favicon*
```

## Rebuild archive stats (optional)

The legacy India-only rebuild uses raw files under `.data-cache/india/`. It cannot restore recovered full-ball files that were not committed to this repository. Keep the existing `stats.json` unless deliberately rebuilding that older archive:

```bash
python3 refresh_cricsheet.py   # merge latest Cricsheet India zip
python3 build_stats.py         # rebuild stats.json (full-ball analytics only)
python3 quarantine_empty_shells.py  # move empty ESPN shells to dashboard/shells/
```

Regenerates `stats.json` with match scorecards, series, quality flags (full / partial / empty). Team W/L and player tables use **full ball-by-ball matches only**; empty ESPN shells are catalogued separately.

## Data notes

| Layer | Source | Use for |
|--------|--------|---------|
| **Official** | Wikipedia / ESPNcricinfo (as-of dates in UI) | True career team totals & leaders |
| **Archive** | Ball-by-ball + recovered files in `stats.json` | Deep analytics where data exists |

Approx coverage vs official (mid-2026): Tests ~96%, ODIs ~74%, T20Is ~full.  
~1,094 matches have full ball-by-ball; many shells are empty/partial — flagged in **Coverage** and match quality badges.

Player photos: Wikipedia / Wikimedia Commons (educational display).

## SEO & AI discovery

- Clean paths: `/`, `/tournaments`, `/batting`, `/player/Name`, `/match/id`, …
- Crawlable HTML summary + JSON-LD (SportsTeam, FAQ, WebSite SearchAction)
- `robots.txt`, `sitemap.xml`, `llms.txt`, `humans.txt`, `site.webmanifest`
- GitHub Pages SPA fallback via `404.html` for dynamic player/match URLs

### Search Console (do this once)

1. [Google Search Console](https://search.google.com/search-console) → Add property `https://cricket.rkjat.in`
2. Verify via DNS TXT or HTML file
3. Submit sitemap: `https://cricket.rkjat.in/sitemap.xml`
4. Optional: Bing Webmaster Tools → same sitemap

Indexing is not instant (days–weeks). Content quality + links help.

## Routes

Examples: `/` · `/tournaments` · `/player/Virat%20Kohli` · `/match/1496577` · `/search?q=kohli`

## Credits

- Match data: [Cricsheet](https://cricsheet.org/) + public recoveries where noted  
- Official figures: public encyclopedic sources (see Official → Sources)  
- Design: [Crickrida](https://crickrida.rkjat.in)  
- Not affiliated with BCCI or ICC  
