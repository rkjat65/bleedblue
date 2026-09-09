# Cricket Wicket platform release

## Included

- Shared null-preserving calculations for archive exploration and comparisons.
- Last 10, 20 or 50 batting innings, year windows, opposition and venue-setting filters.
- Career-format coverage counts and a public coverage page with actual data dates.
- Six additional qualified leaderboard categories per gender/format.
- Crawlable dataset catalogue and Dataset/BreadcrumbList structured data.
- Filter setup links use fragments; legacy query links still restore.
- Eleven Studio workflows backed by career, match, batting and bowling Parquet tables.
- Metric, grouping, player identity, team, opponent, venue, year, batting-position and minimum-match controls.
- Editable titles/subtitles, blue brand palettes, accent colour, five visual types, three output sizes, exact labels, data table and explicit result pagination.
- PNG, SVG and CSV exports; reproducible setup links and local saved designs.
- Content-addressed R2 objects with the manifest published last.
- Card photos use available verified portraits, or JPEG/PNG/WebP files processed in the browser. User images are held in tab memory only and embedded into PNG/SVG exports; they are excluded from saved settings, links and the database. Changing player identity clears a local photo. Exported cards carry Cricket Wicket branding without the Cricsheet wordmark; existing site data attribution stays in place. Automatic Commons photos retain their individual photo credit.

## Verification

Run Python unit tests, both JavaScript calculation suites, Studio syntax checks, `build_analytics_lake.py`, `build_site.py`, `audit_site.py` and `audit_seo.py`. Browser-check profiles, recent-innings filters, women’s records, the Studio’s real SQL results, shared-link restoration, and desktop/mobile layout. Confirm deployment uses the tested commit.

Release checks on 8 September 2026: 41 Python tests and both JavaScript suites passed. Browser checks covered labelled PNG/SVG/CSV exports, DuckDB numeric conversion, women’s ODI bowling economy, visual pagination, empty results disabling export, saved setup restoration, and the last ten ODI batting innings comparison. Profile and Studio pages fit a 390 px viewport without page overflow. The publication contains 18,380 indexable pages; the full site audit and representative SEO audit must pass in the deployment workflow as well.

## External setup still required

Search Console opened signed out during this release. Actual indexing, impressions, clicks and real-user Core Web Vitals cannot be reported from a site build. Sign in to the Google account owning the property, verify `https://cricket.rkjat.in/`, and submit `https://cricket.rkjat.in/sitemap.xml`. Inspect representative player, records, research and dataset URLs. Do not submit every possible interactive filter combination.

If Google requests an HTML meta verification token, add the public token to `data/site-settings.json` under `google_site_verification` and deploy. DNS verification instead requires the exact TXT record supplied by Google; do not invent it.

Advertising is prepared editorially through the existing privacy, terms, contact, editorial and advertising pages. No ad network or tracking script is enabled. Before enabling one, obtain the approved publisher identifier, update privacy/consent handling for the chosen service, and reserve measured fixed-size placements between sections. Never put overlays over filters, charts or scorecards. Audience claims must come from measured traffic.

## Scope limits

The new bowling table is innings-level. Ball-by-ball phase, batter-versus-bowler and delivery-type studies need separate delivery tables and coverage validation before those controls can be offered honestly. Historical unrecorded data remains unavailable. Studio creator settings are local or in the shared link; no social posts are sent automatically.

## Search guidance

- https://developers.google.com/crawling/docs/faceted-navigation
- https://developers.google.com/search/docs/appearance/structured-data/dataset
- https://developers.google.com/search/docs/fundamentals/creating-helpful-content
