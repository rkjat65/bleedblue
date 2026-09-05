# Bleed Blue — International Cricket

A responsive international cricket portal with a separate India records hub. IPL remains on [Crickrida](https://crickrida.rkjat.in).

## Run locally

```powershell
python serve.py
```

Open http://127.0.0.1:8765. The server binds to loopback and supports direct India player, match and series URLs. To use another port: `python serve.py --port 8766`.

## International portal

- `/`: editorial homepage, recent archive results and format summaries.
- `/international/`: match centre with team, gender, format, year and text filters, pagination and CSV export. Filter URLs can be shared and refreshed.
- `/international/?match=ID`: both teams' innings, batting and bowling cards, playing XIs, fall of wickets, runs by over and source link.
- `/international/#series`, `#teams`, `#venues`, `#records`: browse the selected archive by competition, team, ground or innings record.
- `/players/`: searchable player directory, format/gender filters, sorting and side-by-side comparison.
- `/players/?id=ID`: player profile, format statistics and recent appearances.
- `/international/#coverage`: source dates, scope and gaps.
- `/overview/`: original India archive, now with consistent navigation and styling.

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

Career and historical importers cache parsed source pages in ignored `.data-cache/careers/` and follow source pagination. Rerunning resumes cached scopes, including failed requests. Use `import_careers.py --refresh` to replace career snapshots. For a historical refresh, move the existing `matches-*.json` cache files into a backup directory before rerunning. Do not mix pages from different refreshes. Review all scope-completion flags before publishing.

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
