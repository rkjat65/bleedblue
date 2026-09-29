# Cricket Wicket product roadmap

Goal: the most complete international cricket reference short of live scores. Every page is format-first (Test, ODI, T20I), pre-rendered, crawlable and honest about coverage.

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
