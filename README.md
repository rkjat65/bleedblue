# Cricket Wicket

International cricket careers and scorecards at https://cricket.rkjat.in. IPL remains on Crickrida.

## Scope

Match browsing covers recognized senior Tests, ODIs and T20Is between the twelve full-member national teams, for men and women. Club, A-team, age-group and associate matches are excluded from the publication. Official player career totals retain all recognized internationals, including games against associates and recognized representative XIs. National affiliation is resolved from exact player identities and match lineups.

## Build and run

```powershell
python -m pip install -r tools/requirements.txt
python -m unittest discover -s tests -p 'test_*.py'
node tests/test_record_layers.js
node --check web/wicket.js
python tools/build_site.py
python tools/audit_site.py
python serve.py --built --port 8766
```

Open http://127.0.0.1:8766. `_site` is generated and ignored by Git. The legacy source files are retained in the repository but are not part of the publication.

## Data pipeline

Cricsheet supplies delivery data and player identity links. Independently imported career snapshots are never added to archive subtotals. Public historical scorecards fill the older innings gap. Source URLs and retrieval dates are retained internally for validation; the website's visible data credit is Cricsheet.

```powershell
python tools/backfill_free_data.py careers --workers 3
python tools/backfill_free_data.py bowling --workers 3
python tools/backfill_free_data.py scorecards --workers 3
python tools/backfill_career_fallback.py --workers 3
python tools/reconcile_careers.py
python tools/backfill_grounds.py
```

These free imports are resumable through `.data-cache/free-backfill`. Only structured cricket facts are retained. Missing fields are null. A supplemental career field requires matching identity, matches, innings and runs. Conflicting snapshots trigger a complete batting/bowling/fielding refresh. Historical innings must reconcile batter runs plus extras to team runs. Zero denominators display N/A; unrecorded fields display a dash. Partial historical balls faced must never be substituted into a full-career strike rate.

Publication scope and scorecard counts are written to `_site/coverage-report.json`. `_site/audit-report.json` records the release checks. Source import errors stay in `data/scorecard_backfill_report.json` and the career enrichment reports. Historical statistics that were never recorded cannot be reconstructed by filling zeros.

## Design and features

Pre-rendered player, match, team, ground, series and record pages provide crawlable HTML, canonical URLs, structured data and sitemaps. Existing identity URLs survive display-name changes. Search, filters, career comparisons, scorecard analysis, saved research, CSV exports and chart exports progressively enhance the static content.

Tables use left-aligned labels, compact numeric columns, consistent rate formatting, alternating rows, sticky identity columns and keyboard-accessible horizontal scrolling. Royal-blue accents and navy surfaces carry through light and dark themes, branding and charts. The old India archive and its global data payloads are retired from the published site.

## Publication and refresh

GitHub Actions validates records, builds the site, audits links/statistics/page weights and deploys GitHub Pages on pushes to `main`. Monday at 02:15 UTC, or a manual run with refresh enabled, stages fresh sources separately and preserves the current data on failure. Verified historical scorecards are reused; missing or stale summaries are imported. Successful refreshes commit the validated data before deployment.

The site is a dated statistical publication, not a live-score service. Search Console verification and indexing remain external to the build. Submit https://cricket.rkjat.in/sitemap.xml in the verified property.

## Data credit

[Cricsheet](https://cricsheet.org/).
