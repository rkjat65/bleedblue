# Cricket Wicket product roadmap

Goal: the most complete international cricket reference short of live scores. Every page is format-first (Test, ODI, T20I), pre-rendered, crawlable and honest about coverage.

## Shipped (September 2026)

- **Player profiles**: masthead, sticky Overview / Test / ODI / T20I switch, per-format official line, hero tiles, career arc and by-year charts, form, score distribution, dismissals, batting position, tabbed splits (opposition, home and away, batting first or chasing, position, result, year, ground, series), milestones, best performances, latest matches.
- **Match scorecards**: overs and run rate, toss, player of the match, extras breakdown, fall of wickets, did-not-bat, super-over results, SportsEvent competitors.
- **Team, ground and series pages**: format panels with men and women separate. Teams: record tiles and form guide, results by opponent, home and away, toss and batting order, decade and year, team records, leading players, latest matches. Grounds: innings averages, bat-first and chase win rates, toss effect, totals and chases, team records and leading players at the venue. Series: editions with scorelines, results and leading players.
- **Head-to-head pages**: per-format panels with venue, ground and year splits, rivalry records and leading players.
- **Records hub**: category index; sixteen career leaderboards with spans and full columns; highest scores, strike rate, sixes, best bowling, calendar-year runs and wickets, partnerships rebuilt from the fall of wickets, team totals, chases and margins, each with team, opponent, ground and year filters.
- **Ground names**: 667 recorded spellings resolve to 402 grounds; retired ground URLs redirect to the canonical page.
- Host country resolved for every full-member match; archive rows carry maidens, series name and real result labels.

## Next

1. **Design refresh**: shared tokens for spacing and type, calmer stat tiles, consistent format colours across the home page and hubs.
2. **Compare**: three-way comparisons, year-by-year overlays, position and opposition filters.
3. **Ground metadata**: city, country and capacity on ground mastheads; the remaining ambiguous short names (Hyderabad, Wellington ODIs) once sources confirm the ground.
4. **Player pages**: captaincy and wicketkeeping splits when the source data carries them.

## Working notes

- Full build is about six minutes; `python tools/audit_site.py` another ten. Scratch harnesses render single pages from `_site` JSON in seconds.
- Budgets: 300 KB raw per player page, 2.2 GB for the publication (compressed transfer is roughly an eighth of that).
- Placeholders are a plain hyphen; N/A means there is no denominator.
