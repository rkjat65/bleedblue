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

The import on 5 September 2026 contains **9,769 international matches, 8,287 player profiles and 112 team labels**, including representative XIs. It includes 6,995 men's and 2,774 women's matches: 918 Tests, 3,178 ODIs and 5,673 T20Is. Available dates run from 19 December 2001 to 1 September 2026.

```powershell
python tools/build_international.py --refresh
python -m unittest discover -s tests -v
```

The importer downloads all six public Cricsheet international JSON archives, caches ZIPs in ignored `.data-cache/`, derives both teams' scorecards and player aggregates, and writes `data/`. Run without `--refresh` to rebuild from the cached downloads. No API key, Node install or database is required. Source match files are never executed. International data does not overwrite the legacy India dataset.

`data/home.json` is a small homepage payload. `data/international.json` contains the searchable catalog and players. Scorecards are split into lazy-loaded shards under `data/scorecards/`. `data/manifest.json` records counts and source URLs.

**Coverage:** this includes all available source files, not all cricket history. Cricsheet has historical gaps and withholds Afghanistan matches. The portal is an archive, not a live-score, fixture, rankings or news feed. Player statistics cover supplied deliveries and exclude super overs. The original India career snapshots remain separately dated and have not been independently reverified by the international import. No synthetic matches or commentary were added.

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
