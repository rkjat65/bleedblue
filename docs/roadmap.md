# Cricket Wicket product roadmap

Goal: the most complete international cricket reference short of live scores. Every page is format-first (Test, ODI, T20I), pre-rendered, crawlable and honest about coverage.

## Shipped

- **Player profiles** (September 2026): masthead, sticky Overview / Test / ODI / T20I switch, per-format official line, hero tiles, career arc and by-year charts, form, score distribution, dismissals, batting position, tabbed splits (opposition, home and away, batting first or chasing, position, result, year, ground, series), milestones, best performances, latest matches.
- **Match scorecards**: overs and run rate, toss, player of the match, extras breakdown, fall of wickets, did-not-bat, super-over results, SportsEvent competitors.
- **Team, ground and series pages**: format panels with men and women separate. Teams: record tiles and form guide, results by opponent, home and away, toss and batting order, decade and year, team records, leading players, latest matches. Grounds: innings averages, bat-first and chase win rates, toss effect, totals and chases, team records and leading players at the venue. Series: editions with scorelines, results and leading players.
- Host country resolved for every full-member match; archive rows carry maidens, series name and real result labels.

## Next

1. **Records hub**: Statsguru-style tables per format and gender with team, opposition, span and venue filters from innings data; team records, partnerships, fielding, fastest milestones, player of the match awards.
2. **Ground canonicalisation**: merge duplicate venue names behind stable redirects.
3. **Head-to-head pages**: per-format panels, venue split, leading players in the rivalry, streaks.
4. **Design refresh**: shared tokens for spacing and type, calmer stat tiles, consistent format colours across the home page and hubs.
5. **Compare**: three-way comparisons, year-by-year overlays, position and opposition filters.

## Working notes

- Full build is about six minutes; `python tools/audit_site.py` another ten. Scratch harnesses render single pages from `_site` JSON in seconds.
- Budgets: 300 KB raw per player page, 2.2 GB for the publication (compressed transfer is roughly an eighth of that).
- Placeholders are a plain hyphen; N/A means there is no denominator.
