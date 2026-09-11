"""Small, reproducible research publication built from the site's validated data.

All functions return HTML/page specifications; this module performs no I/O and
does not import build_site. Career figures and archive analyses stay separate.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal, ROUND_DOWN
import html
import re
from urllib.parse import urlencode
from cricket_charts import pair_lab

PUBLISHED = '2026-09-07'
FORMATS = ('Test', 'ODI', 'T20I')

# Source IDs avoid fragile matching when display names gain their full spelling.
# Slugs are explicit because the first five routes have already been published.
COMPARISONS = (
    ('253802', '34102', 'Virat Kohli', 'Rohit Sharma', 'batting'),
    ('35320', '4188', 'Sachin Tendulkar', 'Don Bradman', 'batting'),
    ('303669', '267192', 'Joe Root', 'Steve Smith', 'batting'),
    ('54273', '329336', 'Mithali Raj', 'Meg Lanning', 'batting'),
    ('625383', '8608', 'Jasprit Bumrah', 'James Anderson', 'bowling'),
    ('253802', '35320', 'Virat Kohli', 'Sachin Tendulkar', 'batting'),
    ('303669', '277906', 'Joe Root', 'Kane Williamson', 'batting'),
    ('267192', '277906', 'Steve Smith', 'Kane Williamson', 'batting'),
    ('52337', '35320', 'Brian Lara', 'Sachin Tendulkar', 'batting'),
    ('8166', '49636', 'Shane Warne', 'Muttiah Muralitharan', 'bowling'),
    ('275487', '231740', 'Ellyse Perry', 'Sophie Devine', 'all-round'),
    ('597806', '372317', 'Smriti Mandhana', 'Harmanpreet Kaur', 'batting'),
    ('803971', '275487', 'Amelia Kerr', 'Ellyse Perry', 'all-round'),
    ('53932', '53422', 'Jhulan Goswami', 'Cathryn Fitzpatrick', 'bowling'),
)


def esc(value):
    return html.escape(str(value if value is not None else ''), quote=True)


def num(value):
    if value is None:
        return '—'
    return f'{value:,.2f}' if isinstance(value, float) else f'{value:,}' if isinstance(value, int) else esc(value)


def rate(numerator, denominator, factor=1):
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return float((Decimal(numerator) * factor / Decimal(denominator)).quantize(Decimal('.01'), rounding=ROUND_DOWN))


def link(path, label):
    return f'<a href="{esc(path)}">{esc(label)}</a>'


def table(headings, rows, caption):
    heads = ''.join(f'<th scope="col">{esc(v)}</th>' for v in headings)
    body = ''.join('<tr>' + ''.join(f'<{"th scope=\"row\"" if i == 0 else "td"}>{v}</{"th" if i == 0 else "td"}>' for i, v in enumerate(row)) + '</tr>' for row in rows)
    return f'<div class="table-wrap" tabindex="0" role="region" aria-label="{esc(caption)}"><table class="score-table research-table"><caption>{esc(caption)}</caption><thead><tr>{heads}</tr></thead><tbody>{body}</tbody></table></div>'


def heading(title, subtitle, category='CRICKET WICKET RESEARCH'):
    return f'<section class="page-head"><div class="eyebrow">{esc(category)}</div><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></section>'


def dates(checked):
    return f'<p class="research-byline">Cricket Wicket · Published <time datetime="{PUBLISHED}">{PUBLISHED}</time> · Data checked <time datetime="{esc(checked)}">{esc(checked)}</time></p>'


def actions():
    return '<div class="actions"><button data-save>Save page</button><button data-share>Share link</button><button data-csv>Download table CSV</button></div>'


def card(spec, category):
    return f'<a class="feature-card research-card" href="{esc(spec["path"])}"><span>{esc(category)}</span><h3>{esc(spec["title"])}</h3><p>{esc(spec["description"])}</p><small>Explore the numbers →</small></a>'


def article(path, title, description, body, checked):
    content = heading(title, description) + dates(checked) + actions() + '<div class="research-article">' + body + '</div>'
    return dict(path=path, title=title, description=description, body=content, kind='Article', extra={
        'headline': title, 'datePublished': PUBLISHED, 'dateModified': PUBLISHED,
        'author': {'@type': 'Organization', 'name': 'Cricket Wicket', 'url': 'https://cricket.rkjat.in/about/'},
        'publisher': {'@type': 'Organization', 'name': 'Cricket Wicket', 'url': 'https://cricket.rkjat.in/'},
    })


def scope_box(text, steps):
    return '<aside class="research-method"><h2>How to reproduce this</h2><p>' + text + '</p><ol>' + ''.join('<li>' + step + '</li>' for step in steps) + '</ol><p>' + link('/methodology/', 'Read the data definitions and coverage') + '</p></aside>'


def horizontal_chart(items, label, unit='', dual=False):
    """Zero-based independent bars with visible values and text equivalents."""
    values = [row[1] for row in items if row[1] is not None]
    maximum = max(values, default=0) or 1
    rows = ''
    for index, (name, value) in enumerate(items):
        width = 0 if value is None else max(0, value / maximum * 100)
        rows += f'<div class="research-bar-row"><div><span>{esc(name)}</span><strong>{num(value)}{esc(unit)}</strong></div><div class="research-bar-track"><i class="{"second" if dual and index == 1 else "first"}" style="width:{width:.3f}%"></i></div></div>'
    return f'<figure class="research-bars" aria-label="{esc(label)}"><figcaption>{esc(label)}</figcaption>{rows}</figure>'


def career_checked(people, default):
    return max([str(default)[:10]] + [s['checked_at'][:10] for p in people.values() for s in p.get('career', {}).values() if s.get('checked_at')])


def build_comparisons(people, pp, checked):
    by_source = {str(p.get('espn_id')): p for p in people.values() if p.get('espn_id')}
    pages = []
    for left_id, right_id, left, right, focus in COMPARISONS:
        p1, p2 = by_source.get(left_id), by_source.get(right_id)
        if not p1 or not p2:
            continue
        path = '/compare/' + re.sub('[^a-z0-9]+', '-', left.lower()) + '-vs-' + re.sub('[^a-z0-9]+', '-', right.lower()) + '/'
        title = left + ' vs ' + right + ' stats comparison'
        desc = f'Compare {left} and {right}: format-by-format career figures, visual comparisons, playing spans and sample sizes.'
        body = heading(left + ' vs ' + right, desc, 'PLAYER COMPARISON') + dates(checked) + actions()
        body += '<div class="comparison-identity"><a href="' + esc(pp[p1['id']]) + '"><span>FIRST PLAYER</span><strong>' + esc(left) + '</strong><small>' + esc(' / '.join(p1['teams'])) + '</small></a><b>VS</b><a href="' + esc(pp[p2['id']]) + '"><span>SECOND PLAYER</span><strong>' + esc(right) + '</strong><small>' + esc(' / '.join(p2['teams'])) + '</small></a></div>'
        body += '<nav class="research-jump" aria-label="Comparison formats">' + ''.join(link('#' + fmt.lower(), fmt) for fmt in FORMATS if fmt in p1['career'] or fmt in p2['career']) + '</nav>'
        for fmt in FORMATS:
            s1, s2 = p1['career'].get(fmt), p2['career'].get(fmt)
            if s1 is None and s2 is None:
                continue
            body += f'<section class="panel comparison-format" id="{fmt.lower()}"><h2>{fmt} career comparison</h2>'
            if s1 is None or s2 is None:
                missing = left if s1 is None else right
                present = right if s1 is None else left
                body += f'<p>{esc(missing)} has no {fmt} career in this record set, so a like-for-like {fmt} comparison is unavailable. Open {esc(present)}’s profile for the individual record.</p></section>'
                continue
            span1, span2 = s1.get('span', 'Not recorded'), s2.get('span', 'Not recorded')
            body += '<p class="comparison-context"><strong>' + esc(left) + '</strong>: ' + esc(span1) + ' · ' + num(s1.get('matches')) + ' matches. <strong>' + esc(right) + '</strong>: ' + esc(span2) + ' · ' + num(s2.get('matches')) + ' matches.</p>'
            body += '<p class="note">Full format careers at the checked date. These spans and workloads differ; the comparison does not adjust for era, opposition, venue or role. Bar lengths show the metric’s magnitude, not an overall player rating.</p>'
            metrics = [('runs', 'Career runs'), ('avg', 'Batting average'), ('sr', 'Batting strike rate')]
            if focus == 'bowling':
                metrics = [('wickets', 'Career wickets'), ('bowlAvg', 'Bowling average · lower is fewer runs per wicket'), ('bowlSr', 'Bowling strike rate · balls per wicket')]
            elif focus == 'all-round':
                metrics = [('runs', 'Career runs'), ('wickets', 'Career wickets'), ('avg', 'Batting average')]
            body += pair_lab(left, right, s1, s2, focus)
            body += '<div class="comparison-charts">' + ''.join(horizontal_chart([(left, s1.get(key)), (right, s2.get(key))], label, dual=True) for key, label in metrics) + '</div>'
            keys = [('matches', 'Matches'), ('innings', 'Batting innings'), ('runs', 'Runs'), ('outs', 'Dismissals'), ('avg', 'Batting average'), ('balls', 'Balls faced'), ('sr', 'Batting strike rate'), ('hundreds', 'Centuries'), ('fifties', 'Fifties'), ('highest_display', 'Highest score'), ('bowling_innings', 'Bowling innings'), ('wickets', 'Wickets'), ('conceded', 'Runs conceded'), ('legal', 'Legal balls bowled'), ('bowlAvg', 'Bowling average'), ('bowlSr', 'Balls per wicket'), ('econ', 'Economy'), ('five_w', 'Five-wicket innings'), ('catches', 'Catches'), ('stumpings', 'Stumpings')]
            body += table(['Metric', left, right], [[esc(label), num(s1.get(key)), num(s2.get(key))] for key, label in keys], fmt + ' full career records') + '</section>'
        body += scope_box('Both columns come from the independent official career snapshots used on player profiles. Official internationals against associates and recognized representative teams remain in those careers.', [link(pp[p1['id']], left + ' career table') + ' and ' + link(pp[p2['id']], right + ' career table') + ' contain the source figures by format.', 'Batting average divides runs by dismissals; batting strike rate divides runs by balls faced and multiplies by 100.', 'Bowling average divides runs conceded by wickets. A missing or inapplicable denominator stays unavailable; figures are never filled from a partial scorecard sample.'])
        body += '<p>' + link('/compare/', 'Choose a different pair or compare a filtered archive sample') + '</p>'
        pages.append(dict(path=path, title=title, description=desc, body=body))
    return pages


def batting_article(people, pp, gender, fmt, checked):
    candidates = [p for p in people.values() if p.get('gender') == gender and p.get('career', {}).get(fmt, {}).get('runs') is not None]
    candidates.sort(key=lambda p: (-(p['career'][fmt]['runs']), p['name']))
    top = candidates[:8]
    if not top:
        return None
    qualified = [p for p in candidates if (p['career'][fmt].get('innings') or 0) >= 20 and p['career'][fmt].get('avg') is not None]
    qualified.sort(key=lambda p: (-p['career'][fmt]['avg'], p['name']))
    leader = top[0]
    s = leader['career'][fmt]
    title = f'{gender} {fmt}: what the run leaders reveal about volume and average'
    desc = f'{gender} {fmt} run leaders compared by innings, average and scoring rate, with the qualification behind each conclusion.'
    body = '<section class="research-takeaway"><span class="eyebrow">THE FINDING</span><p>' + link(pp[leader['id']], leader['name']) + ' leads the published career snapshot with <strong>' + num(s['runs']) + '</strong> runs from <strong>' + num(s.get('innings')) + '</strong> batting innings. That answers who accumulated the most runs; average answers a different question about runs per dismissal.</p></section>'
    body += horizontal_chart([(p['name'], p['career'][fmt]['runs']) for p in top], 'Eight highest career run totals · ' + gender + ' ' + fmt)
    body += '<h2>Read opportunity alongside output</h2><p>A longer career can create more chances to add runs. The table therefore keeps matches and batting innings next to the run total. Matches include appearances without a batting innings; treating those two counts as interchangeable obscures opportunity.</p>'
    body += table(['Player', 'Span', 'Matches', 'Innings', 'Runs', 'Dismissals', 'Average', 'Strike rate'], [[link(pp[p['id']], p['name']), esc(p['career'][fmt].get('span', '—'))] + [num(p['career'][fmt].get(k)) for k in ('matches', 'innings', 'runs', 'outs', 'avg', 'sr')] for p in top], gender + ' ' + fmt + ' career run leaders with sample sizes')
    if qualified:
        q = qualified[0]
        qs = q['career'][fmt]
        body += '<h2>Changing the measure changes the question</h2><p>With a minimum of 20 batting innings, ' + link(pp[q['id']], q['name']) + ' has the highest recorded batting average in this snapshot: <strong>' + num(qs['avg']) + '</strong> from ' + num(qs['innings']) + ' innings and ' + num(qs.get('outs')) + ' dismissals. This qualification admits ' + num(len(qualified)) + ' careers. A different minimum can change the leader.</p>'
    body += '<p>Batting average uses dismissals, including the effect of not-outs. Strike rate uses balls faced. Comparing these rates helps distinguish accumulation from pace, but neither corrects for conditions, field restrictions, opposition strength or batting role. A dash in the strike-rate column means the required historical information is unavailable.</p><h2>A comparison you can take further</h2><p>Select two profiles and compare the same format. For a narrower opponent or year range, use their statistical explorers and inspect the available-scorecard coverage before treating the result as a full career split.</p>'
    body += scope_box(f'The article selects all published {gender.lower()} {fmt} careers with a known run total. The chart shows the eight largest totals, with alphabetical ordering only to resolve an equal display order. This is a career analysis, not an aggregation of the match archive.', [link(f'/records/{gender.lower()}/{fmt.lower()}/most-runs/', 'Open the career runs leaderboard') + ' and retain the same gender and format.', link(f'/records/{gender.lower()}/{fmt.lower()}/best-batting-average/', 'Open the batting-average leaderboard') + ' with a minimum of 20 innings.', 'Check the linked player tables for runs, dismissals and balls faced. No rates are averaged across players or formats.'])
    return article(f'/insights/{gender.lower()}-{fmt.lower()}-run-leaders/', title, desc, body, checked)


def bowling_article(people, pp, checked):
    eligible = [p for p in people.values() if p.get('gender') == 'Women' and (p.get('career', {}).get('ODI', {}).get('wickets') or 0) >= 100]
    eligible.sort(key=lambda p: (-p['career']['ODI']['wickets'], p['name']))
    if not eligible:
        return None
    top = eligible[:10]
    quick = sorted([p for p in eligible if p['career']['ODI'].get('bowlSr') is not None], key=lambda p: (p['career']['ODI']['bowlSr'], p['name']))
    leader = top[0]
    title = 'Women’s ODI bowling: wickets, economy and strike rate tell different stories'
    desc = 'Compare women’s ODI bowlers with at least 100 career wickets using workload, runs per wicket and balls per wicket.'
    body = '<section class="research-takeaway"><span class="eyebrow">THE FINDING</span><p>' + link(pp[leader['id']], leader['name']) + ' has the most ODI wickets in this career snapshot: <strong>' + num(leader['career']['ODI']['wickets']) + '</strong>. Across ' + num(len(eligible)) + ' bowlers with at least 100 wickets, the comparison becomes more useful when wicket volume is paired with cost and frequency.</p></section>'
    body += horizontal_chart([(p['name'], p['career']['ODI']['wickets']) for p in top], 'Women’s ODI wickets · ten largest totals among 100-wicket careers')
    body += '<h2>Three measures, three denominators</h2><p>Wickets measure accumulated output. Bowling average is runs conceded per wicket; a lower number means fewer runs conceded for each wicket taken. Bowling strike rate is legal balls per wicket, while economy is runs per six legal balls. Economy can be low without frequent wickets, and a bowler can take wickets frequently while conceding more runs.</p>'
    body += table(['Player', 'Matches', 'Bowling innings', 'Wickets', 'Legal balls', 'Runs conceded', 'Average', 'Balls/wicket', 'Economy'], [[link(pp[p['id']], p['name'])] + [num(p['career']['ODI'].get(k)) for k in ('matches', 'bowling_innings', 'wickets', 'legal', 'conceded', 'bowlAvg', 'bowlSr', 'econ')] for p in top], 'Women’s ODI career bowling: highest wicket totals with at least 100 wickets')
    if quick:
        p = quick[0]
        body += '<h2>Frequency can identify a different leader</h2><p>Among all ' + num(len(eligible)) + ' qualifying careers, ' + link(pp[p['id']], p['name']) + ' has the lowest recorded balls-per-wicket figure, <strong>' + num(p['career']['ODI']['bowlSr']) + '</strong>. The 100-wicket minimum limits small samples, but it still compares careers of different lengths and eras.</p>'
    body += '<p>These are descriptive career statistics. They do not isolate new-ball spells, death overs, opposition or venue. They also do not establish bowling style: this publication does not infer pace or spin from a player’s name. Open an individual explorer for a clearly labeled archive split.</p>'
    body += scope_box('Women’s official ODI careers only. A minimum of 100 wickets applies to the analysis; the table displays the ten largest wicket totals. Career totals include every recognized ODI in each player’s record.', [link('/records/women/odi/most-wickets/', 'Open women’s ODI wicket records') + ' and inspect the linked full careers.', 'Retain careers with at least 100 wickets; order by wickets descending for the table or bowling strike rate ascending for the frequency comparison.', 'Use conceded runs, legal balls and wickets from the same career snapshot; never average individual match rates.'])
    return article('/insights/women-odi-bowling-profiles/', title, desc, body, checked)


def scoring_periods(cards):
    """Weighted batter strike rates, only where an entire innings has known BF.

    Excludes super overs, innings without batting, missing denominators and the
    source placeholder of positive runs from zero balls. Team extras are excluded.
    """
    groups = defaultdict(Counter)
    for card_data in cards.values():
        match = card_data['match']
        if match['format'] != 'ODI':
            continue
        key = (match['gender'], match['date'][:3] + '0s')
        for innings in card_data.get('innings', []):
            if innings.get('super_over') or not innings.get('batting'):
                continue
            stats = groups[key]
            stats['available'] += 1
            batters = innings['batting']
            if any(b.get('runs') is None or b.get('balls') is None or b['balls'] < 0 or (b['balls'] == 0 and b['runs'] > 0) for b in batters):
                stats['excluded'] += 1
                continue
            balls = sum(b['balls'] for b in batters)
            if balls <= 0:
                stats['excluded'] += 1
                continue
            stats['included'] += 1
            stats['runs'] += sum(b['runs'] for b in batters)
            stats['balls'] += balls
    return dict(groups)


def scoring_article(cards, checked):
    groups = scoring_periods(cards)
    if not groups:
        return None
    title = 'ODI scoring across decades: measure pace without hiding missing balls'
    desc = 'A weighted batting strike-rate comparison across ODI decades, separating men and women and disclosing incomplete historical innings.'
    body = '<section class="research-takeaway"><span class="eyebrow">THE QUESTION</span><p>How quickly did batters score in different decades? The answer requires both runs and balls. This study sums batter runs and balls only when every listed batter in an innings has the necessary figures, then compares men’s and women’s ODIs separately.</p></section>'
    for gender in ('Men', 'Women'):
        rows = [(period, values) for (g, period), values in sorted(groups.items()) if g == gender]
        if not rows:
            continue
        body += '<h2>' + gender + ' · ODI scoring pace</h2>'
        included = [(period, rate(v['runs'], v['balls'], 100)) for period, v in rows if v['included']]
        body += horizontal_chart(included, gender + ' ODI runs per 100 balls in included innings')
        body += table(['Decade', 'Available innings', 'Included innings', 'Excluded innings', 'Batter runs', 'Balls faced', 'Runs/100 balls'], [[esc(period), num(v['available']), num(v['included']), num(v['excluded']), num(v['runs']), num(v['balls']), num(rate(v['runs'], v['balls'], 100))] for period, v in rows], gender + ' ODI scoring periods and missing-data coverage')
        usable = [(period, v) for period, v in rows if v['included'] >= 100]
        if len(usable) >= 2:
            first, last = usable[0], usable[-1]
            start, finish = rate(first[1]['runs'], first[1]['balls'], 100), rate(last[1]['runs'], last[1]['balls'], 100)
            change = round(finish - start, 2)
            body += '<p>Using periods with at least 100 included innings, the ' + esc(first[0]) + ' sample scores at <strong>' + num(start) + '</strong> runs per 100 balls and the ' + esc(last[0]) + ' sample at <strong>' + num(finish) + '</strong>, a change of ' + num(change) + ' runs per 100 balls. These are the first and last qualifying archive periods, not estimates of every ODI played in those decades.</p>'
    body += '<h2>Why the missing-data column matters</h2><p>Discarding only the batters with missing balls would keep some of an innings’ runs and remove part of its denominator. That can produce a misleading rate. Here the entire affected innings is excluded. Older scorecards can be less complete, so the surviving sample can still be selective.</p><p>Team extras do not appear in the numerator. Reduced-overs and unfinished innings remain when their batting figures are usable. The current decade is partial. Differences can reflect the mix of teams, venues, innings lengths and conditions; this table does not identify which factor caused a change.</p>'
    body += scope_box('Published senior ODI scorecards between the site’s twelve full-member countries, grouped by match-start decade and gender. These are archive samples, not the independent full career records.', ['In the match archive select ODI and one gender; group scorecards by the first three digits of the match year.', 'Ignore super overs and innings without batting. Exclude an innings if any batter lacks runs or balls, or has positive runs recorded against zero balls.', 'For retained innings, sum all batter runs and all balls faced. Calculate 100 × summed runs / summed balls. Use the coverage counts above when comparing decades.'])
    return article('/insights/odi-scoring-rates-by-decade/', title, desc, body, checked)


def outcome_counts(matches, team=None):
    counts = Counter()
    for match in matches:
        counts['matches'] += 1
        outcome = match.get('outcome', {})
        winner = outcome.get('winner')
        result = outcome.get('result')
        if winner:
            counts['decided'] += 1
            if team:
                counts['wins' if winner == team else 'losses'] += 1
        elif result == 'draw':
            counts['draws'] += 1
        elif result == 'tie':
            counts['ties'] += 1
        else:
            counts['no_result'] += 1
    counts['completed'] = counts['decided'] + counts['draws'] + counts['ties']
    return counts


def draw_article(matches, checked):
    periods = defaultdict(list)
    for match in matches:
        if match['format'] == 'Test':
            periods[(match['gender'], match['date'][:3] + '0s')].append(match)
    if not periods:
        return None
    title = 'How common is a drawn Test? Read the result mix by decade'
    desc = 'Men’s and women’s Test draw shares by decade, with completed-result denominators and sample sizes.'
    body = '<section class="research-takeaway"><span class="eyebrow">THE QUESTION</span><p>A count of draws and a draw percentage answer different questions. This analysis divides draws by Tests recorded with a winner, draw or tie in each decade, and reports incomplete or unclassified outcomes separately.</p></section>'
    for gender in ('Men', 'Women'):
        rows = [(period, outcome_counts(ms)) for (g, period), ms in sorted(periods.items()) if g == gender]
        if not rows:
            continue
        body += '<h2>' + gender + ' · Test results</h2>'
        body += horizontal_chart([(period, rate(v['draws'], v['completed'], 100)) for period, v in rows], gender + ' Test draw percentage among completed results', '%')
        body += table(['Decade', 'Recorded Tests', 'Winner', 'Draw', 'Tie', 'Other/no result', 'Draw %'], [[esc(period)] + [num(v[k]) for k in ('matches', 'decided', 'draws', 'ties', 'no_result')] + [num(rate(v['draws'], v['completed'], 100))] for period, v in rows], gender + ' Test result mix by decade')
    body += '<h2>What the comparison can establish</h2><p>The table describes the result distribution in the published archive. More scheduled matches can produce more draws even when the draw share is lower. Women’s decade samples can be much smaller, so a single result may move their percentages substantially.</p><p>A result label does not say how much play was lost or whether a pitch, tactical choice or weather determined the outcome. Those explanations need additional evidence. The current decade is unfinished; its percentage can change with each newly added result.</p>'
    body += scope_box('Published official Tests between the twelve full-member countries, separated by gender and match-start decade. No-result and unknown outcomes are displayed but excluded from the draw-percentage denominator.', [link('/matches/?format=Test', 'Open Test match results') + ' and choose a gender.', 'Count matches with a winner, drawn result or tied result. Add those counts to obtain the denominator.', 'Divide draws by that denominator and multiply by 100. A period without a completed result has no applicable draw percentage.'])
    return article('/insights/test-draws-by-decade/', title, desc, body, checked)


def rivalry_article(matches, mp, gp, checked):
    selected = [m for m in matches if set(m['teams']) == {'India', 'Australia'}]
    if not selected:
        return None
    title = 'India vs Australia: one rivalry, six separate international records'
    desc = 'India–Australia results separated into men’s and women’s Tests, ODIs and T20Is, with draws, ties and sample sizes.'
    body = '<section class="research-takeaway"><span class="eyebrow">THE FINDING</span><p>The published India–Australia archive contains <strong>' + num(len(selected)) + '</strong> match records. Combining all six format-and-gender groups into a single win figure hides their different schedules and result patterns. The table keeps each group separate.</p></section>'
    rows = []
    for gender in ('Men', 'Women'):
        for fmt in FORMATS:
            ms = [m for m in selected if m['gender'] == gender and m['format'] == fmt]
            if not ms:
                continue
            c = outcome_counts(ms, 'India')
            rows.append([esc(gender + ' · ' + fmt), num(c['matches']), num(c['wins']), num(c['losses']), num(c['draws']), num(c['ties']), num(c['no_result']), num(rate(c['wins'], c['decided'], 100))])
    body += table(['Group', 'Matches', 'India wins', 'Australia wins', 'Draws', 'Ties', 'Other/no result', 'India share of wins %'], rows, 'India–Australia international match results by format and gender')
    body += '<h2>How to read a share of wins</h2><p>India’s share of wins divides India wins by all matches with a recorded winner in that group. It excludes draws, ties and other outcomes. A Test win share can therefore differ from wins divided by all Tests. The full counts remain visible so either denominator can be reconstructed.</p><p>This record includes the available matches in the site’s published scope. It does not adjust for home advantage or identify a stronger team today. Start with a format and gender, inspect the time span, then use the linked scorecards to examine a narrower period.</p>'
    first, last = min(selected, key=lambda m: m['date']), max(selected, key=lambda m: m['date'])
    body += '<h2>Open the endpoints</h2><div class="research-endpoints"><div><span>EARLIEST PUBLISHED RECORD</span>' + link(mp[first['id']], first['date'] + ' · ' + first['gender'] + ' ' + first['format']) + '</div><div><span>LATEST PUBLISHED RECORD</span>' + link(mp[last['id']], last['date'] + ' · ' + last['gender'] + ' ' + last['format']) + '</div></div>'
    body += '<p>' + link(gp['teams']['India'], 'India team records') + ' · ' + link(gp['teams']['Australia'], 'Australia team records') + '</p>'
    body += scope_box('Official published matches whose two team names are India and Australia. A deciding tiebreak recorded as a winner contributes to that winner; tied results without a recorded winner remain ties.', ['Select India and Australia, then separate by Test, ODI and T20I and by gender.', 'Classify each match using its result winner or draw/tie label. Retain no-play, no-result and unknown outcomes in the visible totals.', 'For India’s share of wins, calculate 100 × India wins / (India wins + Australia wins).'])
    return article('/insights/india-australia-international-record/', title, desc, body, checked)


def entity_context(kind, name, matches, mp):
    """Useful, gender-separated result context for an existing team/ground page."""
    if kind not in ('teams', 'grounds') or not matches:
        return ''
    rows = []
    for gender in ('Men', 'Women'):
        for fmt in FORMATS:
            selected = [m for m in matches if m['gender'] == gender and m['format'] == fmt]
            if not selected:
                continue
            c = outcome_counts(selected, name if kind == 'teams' else None)
            if kind == 'teams':
                row = [esc(gender + ' · ' + fmt)] + [num(c[k]) for k in ('matches', 'wins', 'losses', 'draws', 'ties', 'no_result')]
            else:
                row = [esc(gender + ' · ' + fmt)] + [num(c[k]) for k in ('matches', 'decided', 'draws', 'ties', 'no_result')]
            rows.append(row)
    labels = ['Group', 'Matches', 'Wins', 'Losses', 'Draws', 'Ties', 'Other/no result'] if kind == 'teams' else ['Group', 'Matches', 'Winner recorded', 'Draws', 'Ties', 'Other/no result']
    body = '<section class="panel"><h2>Results in context</h2><p>Separate formats and genders before comparing the record. Counts below describe the published archive.</p>' + table(labels, rows, name + ' results by format and gender')
    if kind == 'grounds':
        body += '<p class="note">Result frequency alone does not establish whether a ground favours batting, bowling or chasing. Venue aliases are kept as supplied by the verified match records; differently named entries may describe the same physical ground.</p>'
    else:
        body += '<p class="note">All opponent countries shown here are in the publication’s twelve-team scope. Player career records can include additional recognized international opponents.</p>'
    earliest = min(matches, key=lambda m: (m['date'], m['id']))
    latest = max(matches, key=lambda m: (m['date'], m['id']))
    body += '<div class="research-endpoints"><div><span>EARLIEST PUBLISHED</span>' + link(mp[earliest['id']], earliest['date'] + ' · ' + ' v '.join(earliest['teams'])) + '</div><div><span>LATEST PUBLISHED</span>' + link(mp[latest['id']], latest['date'] + ' · ' + ' v '.join(latest['teams'])) + '</div></div></section>'
    return body


def build_editorial(people, matches, pp, mp, gp, all_cards, checked_at):
    checked = career_checked(people, checked_at)
    comparisons = build_comparisons(people, pp, checked)
    insights = [batting_article(people, pp, gender, fmt, checked) for gender, fmt in (('Men', 'Test'), ('Women', 'ODI'), ('Men', 'T20I'))]
    insights += [bowling_article(people, pp, checked), scoring_article(all_cards, checked), draw_article(matches, checked), rivalry_article(matches, mp, gp, checked)]
    insights = [page for page in insights if page]
    return {
        'pages': comparisons + insights,
        'comparisons': comparisons,
        'insights': insights,
        'comparison_cards': '<div class="grid three">' + ''.join(card(p, 'CAREER COMPARISON') for p in comparisons) + '</div>',
        'insight_cards': '<div class="grid three">' + ''.join(card(p, 'ORIGINAL STATISTICAL ANALYSIS') for p in insights) + '</div>',
    }
