# Bleed Blue

**Team India cricket records dashboard** — official career totals, archive analytics, player photos, and match browser. Dark UI inspired by [Crickrida](https://crickrida.rkjat.in).

Live-friendly static site: **no backend required**. Host on [GitHub Pages](https://pages.github.com/) or any static host.

## Features

- **Official Records** — verified Test / ODI / T20I career results, ICC trophies, landmarks, and leaders (Wikipedia / ESPNcricinfo)
- **Archive analytics** — batting, bowling, fielding, head-to-head, venues, and records from local match data
- **Player gallery** — portraits for all-time icons and format leaders
- **Match browser** — search and filter the archive
- **Coverage report** — how this dataset compares to full career totals

## Quick start (local)

```bash
# from this folder
python3 -m http.server 8765
```

Open **http://127.0.0.1:8765**

> Browsers block `fetch()` of local JSON via `file://`. Always serve over HTTP.

Or open the folder with any static server (`npx serve`, VS Code Live Server, etc.).

## GitHub Pages

1. Push this repo (root = site files).
2. **Settings → Pages → Deploy from branch** → `main` → `/` (root).
3. Site URL: `https://rkjat65.github.io/bleedblue/`

No build step. `index.html` is the entry point.

## Project structure

```
.
├── index.html              # App shell + side nav
├── styles.css              # Dark theme (cyan / magenta accents)
├── app.js                  # UI logic + Chart.js
├── stats.json              # Pre-aggregated archive stats
├── official_records.json   # Official career records (web-sourced)
├── player_images.json      # Name → photo map
├── favicon.svg / .png      # Brand favicon
├── images/                 # Hero art + player portraits
├── build_stats.py          # Rebuild stats.json from match JSON (optional)
└── fetch_*.py              # Offline data recovery helpers (optional)
```

## Rebuild archive stats (optional)

If you keep Cricsheet-style match JSON files in the **parent** folder:

```bash
python3 build_stats.py
```

This regenerates `stats.json`. You do **not** need these scripts or raw match files to run or host the site.

## Data notes

| Layer | Source | Purpose |
|--------|--------|---------|
| **Official Records** | Public career totals (Wikipedia / Cricinfo) | Correct all-time figures |
| **Archive pages** | Pre-built `stats.json` from match files | Ball-by-ball style analytics |

Archive numbers can differ from full career totals when older matches are missing from the source pack. Use **Official Records** for official team W/L and career leaders.

Player photos: Wikipedia / Wikimedia Commons page images, for educational display.

## Design

- Dark graphite background
- Accents: cyan, magenta, lime, amber
- Fonts: Space Grotesk, Inter, JetBrains Mono
- Side panel navigation (mobile drawer)

## License & credits

- Match stats derived from [Cricsheet](https://cricsheet.org/) and recovered public summaries where noted
- Official figures cross-checked against public encyclopedic sources
- Design inspired by [Crickrida](https://crickrida.rkjat.in)
- Not affiliated with BCCI or ICC
