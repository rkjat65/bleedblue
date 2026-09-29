"""Format-first profiles: coverage, splits and markup stay honest and per format."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
import cricket_charts as cw
from profile_formats import (
    bat_totals, bowl_totals, coverage, coverage_label, format_role, format_switch, innings_label,
    lean_table, profile_body, split_groups, split_section,
)


def bat(match, runs, balls, out=True, fmt='ODI', date='2020-01-01', opponent='Australia', innings=1, position=3, **extra):
    return {'date': date, 'match': match, 'url': f'/matches/{match}/', 'format': fmt, 'opponent': opponent, 'venue': 'Ground',
            'setting': 'Home', 'result': 'Won', 'innings': innings, 'position': position, 'runs': runs, 'balls': balls, 'out': out,
            'fours': 4, 'sixes': 1, 'dismissal': 'caught b X' if out else None, 'wickets': None, 'legal': None, 'conceded': None,
            'maidens': None, 'event': None, **extra}


def bowl(match, wickets, conceded, legal=60, fmt='ODI', date='2020-01-01', innings=2, **extra):
    return {'date': date, 'match': match, 'url': f'/matches/{match}/', 'format': fmt, 'opponent': 'England', 'venue': 'Ground',
            'setting': 'Away', 'result': 'Lost', 'innings': innings, 'position': None, 'runs': None, 'balls': None, 'out': None,
            'fours': None, 'sixes': None, 'dismissal': None, 'wickets': wickets, 'legal': legal, 'conceded': conceded, 'maidens': 1, 'event': None, **extra}


def stat_value(stats, key):
    value = (stats or {}).get(key)
    if value is None:
        return 'N/A'
    return f'{value:,}' if isinstance(value, int) else str(value)


class TotalsTests(unittest.TestCase):
    def test_unknown_balls_void_the_strike_rate_only(self):
        t = bat_totals([bat('a', 100, 80), bat('b', 20, None)])
        self.assertEqual(t['runs'], 120)
        self.assertIsNone(t['balls'])
        self.assertIsNone(t['sr'])
        self.assertEqual(t['avg'], 60.0)
        self.assertEqual(t['highest_display'], '100')

    def test_not_out_highest_score_carries_star_and_no_average_with_no_dismissal(self):
        t = bat_totals([bat('a', 45, 30, out=False), bat('b', 12, 10, out=False)])
        self.assertEqual(t['highest_display'], '45*')
        self.assertEqual(t['outs'], 0)
        self.assertIsNone(t['avg'])

    def test_bowling_best_and_rates(self):
        t = bowl_totals([bowl('a', 5, 27), bowl('b', 5, 20), bowl('c', 0, 40)])
        self.assertEqual(t['best_bowling'], '5/20')
        self.assertEqual(t['five_w'], 2)
        self.assertEqual(t['wickets'], 10)
        self.assertEqual(t['econ'], 2.9)
        self.assertEqual(t['bowlSr'], 18.0)


class CoverageTests(unittest.TestCase):
    def test_complete_when_official_innings_and_runs_match(self):
        rows = [bat('a', 50, 40), bat('b', 70, 60)]
        cov = coverage({'innings': 2, 'runs': 120, 'bowling_innings': 0, 'wickets': 0}, rows)
        self.assertTrue(cov['complete'])
        self.assertIn('Complete', coverage_label(cov))

    def test_partial_coverage_names_the_gap(self):
        rows = [bat('a', 50, 40)]
        cov = coverage({'innings': 302, 'runs': 14941}, rows)
        self.assertFalse(cov['complete'])
        self.assertEqual(cov['pct'], 0)
        self.assertEqual(coverage_label(cov), 'Scorecards for 1 of 302 official batting innings')

    def test_no_scorecards(self):
        cov = coverage({'innings': 10, 'runs': 100}, [])
        self.assertEqual(coverage_label(cov), 'No scorecards yet')


class SplitTests(unittest.TestCase):
    def test_limited_overs_innings_labels_distinguish_disciplines(self):
        self.assertEqual(innings_label({'innings': 1}, 'ODI', 'bat'), 'Batting first')
        self.assertEqual(innings_label({'innings': 2}, 'ODI', 'bat'), 'Chasing')
        self.assertEqual(innings_label({'innings': 1}, 'T20I', 'bowl'), 'Bowling first')
        self.assertEqual(innings_label({'innings': 3}, 'Test', 'bat'), '3rd innings of the match')

    def test_groups_are_per_discipline_and_ordered(self):
        rows = [bat('a', 10, 10, opponent='England'), bat('b', 20, 15, opponent='Australia'), bat('c', 30, 20, opponent='Australia'), bowl('d', 2, 30)]
        groups = dict((key, items) for key, _, items in split_groups(rows, 'ODI', 'bat'))
        self.assertEqual([label for label, _ in groups['opposition']], ['Australia', 'England'])
        self.assertEqual([label for label, _ in groups['position']], ['No. 3'])
        bowl_groups = dict((key, items) for key, _, items in split_groups(rows, 'ODI', 'bowl'))
        self.assertEqual([label for label, _ in bowl_groups['opposition']], ['England'])
        self.assertNotIn('position', bowl_groups)

    def test_split_section_has_tabs_and_totals_footer(self):
        rows = [bat(str(i), 40 + i, 30, opponent='Australia' if i % 2 else 'England', date=f'20{10 + i % 3}-01-01') for i in range(8)]
        markup = split_section(rows, 'ODI', 'Player', want_bowling=False)
        self.assertIn('role="tablist"', markup)
        self.assertIn('data-tab="opposition"', markup)
        self.assertIn('<tfoot>', markup)
        self.assertNotIn(' hidden', markup)
        self.assertEqual(markup.count('data-tab-panel="year"'), 1)
        self.assertNotIn('pf-bowl', markup)


class MarkupTests(unittest.TestCase):
    def test_switch_lists_only_played_formats(self):
        markup = format_switch(['Test', 'T20I'], {'Test': {'matches': 12}, 'T20I': {'matches': 3}})
        self.assertIn('href="#test"', markup)
        self.assertNotIn('href="#odi"', markup)
        self.assertIn('id=\'fmt-boot\'', markup)

    def test_lean_table_first_column_is_row_header(self):
        markup = lean_table('Caption', ['', ('Mat', 'Matches')], [['India', '3']], ['All', '3'])
        self.assertIn('<th scope="row">India</th>', markup)
        self.assertIn('title="Matches"', markup)
        self.assertIn('<tfoot><tr><th scope="row">All</th><td>3</td></tr></tfoot>', markup)

    def test_role_from_format_stats(self):
        self.assertEqual(format_role({'matches': 100, 'runs': 400, 'wickets': 150}), 'bowler')
        self.assertEqual(format_role({'matches': 100, 'runs': 3000, 'wickets': 120}), 'all-rounder')
        self.assertEqual(format_role({'matches': 100, 'runs': 4000, 'wickets': 3}), 'batter')
        self.assertEqual(format_role({'matches': 100, 'runs': 2000, 'wickets': 0, 'stumpings': 20}), 'keeper')

    def test_profile_body_renders_one_panel_per_format_and_no_dashes(self):
        career = {
            'ODI': {'matches': 10, 'innings': 10, 'notouts': 1, 'runs': 500, 'highest_display': '120*', 'avg': 55.55, 'balls': 480, 'sr': 104.16, 'hundreds': 1, 'fifties': 3, 'ducks': 0, 'fours': 40, 'sixes': 10, 'wickets': 0, 'span': '2019-2021'},
            'T20I': {'matches': 4, 'innings': 4, 'runs': 80, 'avg': 20.0, 'wickets': 0},
        }
        rows = [bat(str(i), 50, 40, date=f'2019-0{i + 1}-01') for i in range(6)] + [bat('t', 30, 20, fmt='T20I')]
        apps = [{'match': str(i), 'date': f'2019-0{i + 1}-01', 'format': 'ODI', 'teams': ['India', 'Australia'], 'venue': 'Ground', 'result': 'India won', 'url': f'/matches/{i}/'} for i in range(6)]
        blocks = {'tables': '<table></table>', 'snapshot': '2026-09-27', 'glance': '', 'faq': '', 'explorer': '', 'research': '', 'recent': ''}
        player = {'name': 'Test Player', 'teams': ['India'], 'gender': 'Men', 'first': '2019', 'last': '2021', 'career': career}
        body = profile_body(player, portrait='', badges='', rows=rows, apps=apps, career=career, totals={'matches': 14, 'runs': 580, 'hundreds': 1, 'wickets': 0, 'catches': 2},
                            blocks=blocks, charts=cw.format_lab, stat_value=stat_value, compare_path='/compare/')
        self.assertEqual(body.count('<h1>'), 1)
        self.assertIn('data-fmt-panel="overview"', body)
        self.assertIn('data-fmt-panel="odi"', body)
        self.assertIn('data-fmt-panel="t20i"', body)
        self.assertNotIn('data-fmt-panel="test"', body)
        self.assertIn('Test Player in ODIs', body)
        self.assertIn('id="career-records"', body)
        text = re.sub(r'<[^>]+>', ' ', body)
        self.assertNotIn('–', text)
        self.assertNotIn('—', text)


class ChartTests(unittest.TestCase):
    def test_career_arc_marks_milestones_and_thins_points(self):
        rows = [bat(str(i), 50, 40, date=f'20{10 + i // 20:02d}-01-{1 + i % 20:02d}') for i in range(600)]
        svg = cw.career_arc(rows, 'runs', 'Runs')
        self.assertIn('cw-mark', svg)
        self.assertIn('>5k<', svg)
        points = svg.split('<polyline')[1].split('points="')[1].split('"')[0].split()
        self.assertLess(len(points), 260)
        self.assertEqual(cw.career_arc(rows[:3], 'runs', 'Runs'), '')

    def test_histogram_conversion_note_and_year_bars(self):
        rows = [bat(str(i), v, 40) for i, v in enumerate([0, 5, 12, 30, 55, 70, 105, 130])]
        chart = cw.innings_histogram(rows, 'By score')
        self.assertIn('4 became', chart.replace('Scores of fifty or more: 4; 2 became hundreds', '4 became'))
        self.assertIn('50%', chart)
        years = [bat(str(i), 100, 80, date=f'{2015 + i}-05-01') for i in range(4)]
        bars = cw.year_bars(years, 'runs', 'Runs by year')
        self.assertEqual(bars.count('<rect'), 4)
        self.assertIn('is-best', bars)


class NavigationTests(unittest.TestCase):
    def test_format_click_handler_ignores_the_html_element(self):
        """The boot script stores the active format on <html data-fmt>; ordinary links must still navigate."""
        script = (Path(__file__).resolve().parent.parent / 'web' / 'wicket.js').read_text(encoding='utf-8')
        self.assertNotIn("closest('[data-fmt]", script)
        self.assertIn("closest('button[data-fmt],a[data-fmt],[data-fmt-link]')", script)
        self.assertIn('t===document.documentElement', script)


if __name__ == '__main__':
    unittest.main()
