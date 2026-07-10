# Bleed Blue

**Full-fledged Team India cricket records** — official career totals, ICC trophies & tournaments, captaincy, series browser, match centre, player profiles, global search, and ball-by-ball archive analytics.

**Live:** [https://cricket.rkjat.in](https://cricket.rkjat.in)  
**Repo:** [github.com/rkjat65/bleedblue](https://github.com/rkjat65/bleedblue)

Static site — **no backend**. Host on GitHub Pages or any static host. Design inspired by [Crickrida](https://crickrida.rkjat.in).

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
python3 -m http.server 8765
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

If Cricsheet-style match JSON files live in the **parent** folder:

```bash
python3 build_stats.py
```

Regenerates `stats.json` with match scorecards, series, quality flags (full / partial / empty).

## Data notes

| Layer | Source | Use for |
|--------|--------|---------|
| **Official** | Wikipedia / ESPNcricinfo (as-of dates in UI) | True career team totals & leaders |
| **Archive** | Ball-by-ball + recovered files in `stats.json` | Deep analytics where data exists |

Approx coverage vs official (mid-2026): Tests ~96%, ODIs ~74%, T20Is ~full.  
~1,094 matches have full ball-by-ball; many shells are empty/partial — flagged in **Coverage** and match quality badges.

Player photos: Wikipedia / Wikimedia Commons (educational display).

## Hash routes

Examples: `#view=official` · `#view=tournaments` · `#view=player&name=Virat%20Kohli` · `#view=match&id=...` · `#view=search&q=...`

## Credits

- Match data: [Cricsheet](https://cricsheet.org/) + public recoveries where noted  
- Official figures: public encyclopedic sources (see Official → Sources)  
- Design: [Crickrida](https://crickrida.rkjat.in)  
- Not affiliated with BCCI or ICC  
