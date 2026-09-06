# Cricket Wicket: product, design and search strategy

The positioning: **The game in numbers.** A fast, dependable international cricket reference for fans, researchers, writers and analysts. Men's and women's cricket belong in the same product structure. IPL remains on the owner's Crickrida site.

## Implemented in the generated publication

The September 2026 release implements the first three engineering stages below: generated entity pages, career and archive analysis, qualified records, comparisons, shared filters, CSV/SVG export, saved research, embed cards, statistical explainers, a navy/green responsive theme and dark mode. The GitHub Pages workflow builds and audits the complete publication before deployment. The weekly refresh validates source completeness, count changes, scorecard totals and identity joins before replacing data.

Every available career field is exposed in batting, bowling and fielding tables. Player analysis is fetched per player; the large global career and delivery datasets are no longer profile dependencies. Career snapshots and archive splits remain separate. The original roadmap below documents the product direction.

## Remaining external and data work

Search Console verification and search/engagement reporting require the owner's account or a configured analytics property. Field Core Web Vitals are still measurement targets, not achieved claims. Corrections currently download a report; receiving reports needs an owner-selected inbox or backend. The three generated explainers are published snapshots, not a promise of human-reviewed weekly editorial coverage. Forty-three unmatched identities and missing historical delivery/scorecard records remain explicit gaps. Broader historical scorecards, localization and dependable live feeds require additional verified data access; no invented figures or third-party credentials are embedded.

## 1. Build a searchable cricket reference

Generate individual HTML pages for players, matches, teams, grounds, series and curated records. For the current static host, a Python build can generate these directly from the datasets. A framework migration is optional; pre-rendering is the requirement.

Proposed routes: `/players/virat-kohli/`, `/teams/india/`, `/grounds/lords/`, `/records/odi/most-runs/`, `/compare/virat-kohli-vs-rohit-sharma/`.

Every indexable page needs a unique title, useful description, self-referencing canonical, visible main statistics in its initial HTML, descriptive internal links and appropriate structured data that matches the visible page. Keep a stable player-ID mapping behind readable names. Generate partitioned XML sitemaps from real published pages, using actual update dates. Retain working redirects from old URLs when changing routes.

Index curated comparisons and useful record pages. Do not generate millions of empty filter combinations or near-duplicate pages. Keep arbitrary sorting and filtering out of the index through a deliberate canonical and crawl policy. Connect Search Console and inspect rendered pages and sitemap coverage. Neither schema nor sitemap submission guarantees rankings.

## 2. Make the data genuinely useful

Profiles should answer career, format, opponent, country, venue, year, home/away, innings and match-result questions. Add year-by-year trends, milestones, dismissal patterns and batting-position filters where the underlying data supports them. Show sample sizes and coverage beside every filtered calculation.

Comparison tools should offer comparable formats, periods and minimum-innings thresholds. Record tables need qualification rules, ties, clear definitions and links back to contributing matches. Never present incomplete ball-data splits as full-career analysis.

Add reliable refresh jobs, reproducible transformations, identity reconciliation, anomaly checks, visible freshness and a corrections process. Continue resolving the 43 unmatched archive identities. Full historical scorecards and licensed live feeds are distinct workstreams; the existing archive cannot supply a live service by itself. Keep technical provenance for auditability.

## 3. Design around reading and exploration

Use deep navy `#10233F`, cricket green `#087F6C`, warm white `#F7F8F5` and restrained amber `#EFB75B`. Green identifies interaction; use a consistent, accessible semantic palette for results and charts. Avoid national-flag branding for the global product.

Use a readable sans serif and tabular numerals. Put search, record shortcuts and recent results above a compact introduction. Tables need sticky headings, a pinned name column, sorting, readable row spacing, clear units and touch-friendly filters. Charts should explain a pattern and expose their underlying table. Support keyboard navigation, reduced motion, strong contrast and narrow screens. Offer dark mode once both themes are verified.

Navigation: Matches, Players, Teams, Records, Compare, Series. A consistent page template should connect each statistic to the next useful exploration. Keep promotional banners and intrusive ads away from the research flow.

## 4. Win returning visitors and useful search traffic

Build original, data-backed pages answering questions such as "most ODI runs against Australia" and "fastest to 10,000 Test runs" only when the supporting records are complete. Add short explanations written for readers, methodology, qualifications and update dates. Prioritize useful coverage of women's cricket and associate nations alongside major teams.

Offer shareable comparisons, downloadable filtered tables, saved searches and embeddable chart cards. Add editorially checked weekly record analyses. Measure search impressions, non-brand queries, engaged visits, repeat visits, successful searches and corrections—not just page counts.

## Delivery order and success checks

1. **First release:** generated player/match HTML, smaller page payloads, correct canonicals, entity sitemaps and mobile table improvements.
2. **Second release:** reliable refresh pipeline, team/ground pages, qualified record tables and useful batting/bowling splits.
3. **Third release:** curated comparisons, original statistical explainers, share/export tools and saved research.
4. **Expansion:** broader historical scorecards, localization and live services once dependable data access and operating costs are established.

Measure mobile performance in real use. Targets at the 75th percentile: LCP at most 2.5 seconds, INP at most 200 milliseconds and CLS at most 0.1. Treat these as engineering goals, not claims about the current site. Establish a baseline before promising traffic or revenue outcomes.

References: [Google JavaScript SEO guidance](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics), [Google URL guidance](https://developers.google.com/search/docs/crawling-indexing/url-structure), [Web Vitals](https://web.dev/articles/vitals).
