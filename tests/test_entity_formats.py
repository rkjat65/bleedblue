"""Team, ground and series panels: records, editions and scorelines stay per format."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
from entity_formats import editions, edition_label, entity_switch, group_matches, outcome_for, record, results_table, scoreline, team_format_panel, toss_table


def match(mid, date, teams, winner=None, result=None, fmt='ODI', gender='Men', venue='Ground', setting='Home', by=None, totals=None, event='Series'):
    outcome = {'winner': winner} if winner else {'result': result or 'no result'}
    if by:
        outcome['by'] = by
    return {'id': mid, 'date': date, 'teams': teams, 'outcome': outcome, 'format': fmt, 'gender': gender, 'venue': venue, 'setting': setting, 'event': event,
            'totals': totals or [], 'player_ids': []}


class RecordTests(unittest.TestCase):
    def test_outcomes_and_record(self):
        ms = [match('1', '2020-01-01', ['India', 'Australia'], 'India'), match('2', '2020-01-03', ['India', 'Australia'], 'Australia'),
              match('3', '2020-01-05', ['India', 'Australia'], result='tie'), match('4', '2020-01-07', ['India', 'Australia'])]
        self.assertEqual([outcome_for(m, 'India') for m in ms], ['Won', 'Lost', 'Tied', 'No result'])
        rec = record(ms, 'India')
        self.assertEqual((rec['played'], rec['won'], rec['lost'], rec['tied'], rec['nr']), (4, 1, 1, 1, 1))
        self.assertEqual(rec['win_pct'], 25.0)
        self.assertEqual(rec['form'], ['Won', 'Lost', 'Tied', 'No result'])

    def test_results_table_has_totals_footer(self):
        ms = [match('1', '2020-01-01', ['India', 'Australia'], 'India'), match('2', '2021-01-03', ['India', 'England'], 'England')]
        groups = group_matches(ms, lambda m: next(x for x in m['teams'] if x != 'India'), sort_by_size=True)
        markup = results_table('By opponent', groups, 'India', first='Opponent')
        self.assertIn('<th scope="row">Australia</th>', markup)
        self.assertIn('<tfoot><tr><th scope="row">All</th><td>2</td><td>1</td><td>1</td>', markup)

    def test_toss_table_uses_scorecards(self):
        ms = [match('1', '2020-01-01', ['India', 'Australia'], 'India'), match('2', '2020-01-03', ['India', 'Australia'], 'Australia')]
        cards = {'1': {'toss': {'winner': 'India', 'decision': 'bat'}, 'innings': [{'team': 'India'}, {'team': 'Australia'}]},
                 '2': {'toss': {'winner': 'Australia', 'decision': 'field'}, 'innings': [{'team': 'India'}, {'team': 'Australia'}]}}
        markup = toss_table(ms, cards, 'India', 'ODI')
        self.assertIn('Won the toss', markup)
        self.assertIn('Batted first', markup)
        self.assertNotIn('Chased', markup)


class SeriesTests(unittest.TestCase):
    def test_editions_split_on_gaps(self):
        ms = [match('1', '2021-01-01', ['India', 'England']), match('2', '2021-01-10', ['India', 'England']), match('3', '2022-11-01', ['India', 'England']), match('4', '2022-12-10', ['India', 'England'])]
        eds = editions(ms)
        self.assertEqual([[m['id'] for m in e] for e in eds], [['1', '2'], ['3', '4']])
        self.assertEqual(edition_label(eds[0]), '2021')
        self.assertEqual(edition_label([match('a', '2021-11-01', ['A', 'B']), match('b', '2022-01-05', ['A', 'B'])]), '2021/22')

    def test_scoreline_for_bilateral_only(self):
        ms = [match('1', '2021-01-01', ['India', 'England'], 'India'), match('2', '2021-01-03', ['India', 'England'], 'India'), match('3', '2021-01-05', ['India', 'England'])]
        line = scoreline(ms)
        self.assertIn('<b>India</b> 2 <i>-</i> 0 <b>England</b>', line)
        self.assertIn('1 drawn or no result', line)
        self.assertEqual(scoreline(ms + [match('4', '2021-01-07', ['India', 'Australia'])]), '')


class PanelTests(unittest.TestCase):
    def test_team_panel_renders_men_and_women_separately(self):
        ms = [match('1', '2020-01-01', ['India', 'Australia'], 'India', totals=[{'team': 'India', 'runs': 300, 'wickets': 6}, {'team': 'Australia', 'runs': 250, 'wickets': 10}]),
              match('2', '2020-02-01', ['India', 'England'], 'India', gender='Women', totals=[{'team': 'England', 'runs': 200, 'wickets': 10}, {'team': 'India', 'runs': 201, 'wickets': 4}])]
        markup = team_format_panel('India', 'ODI', ms, {}, {}, {}, {'1': '/matches/1/', '2': '/matches/2/'}, lambda a, b: '/head-to-head/x/')
        self.assertIn('India men in ODIs', markup)
        self.assertIn('India women in ODIs', markup)
        self.assertIn('Highest ODI totals', markup)
        self.assertIn('data-fmt-panel="odi"', markup)
        self.assertNotIn('—', markup)

    def test_switch_counts(self):
        markup = entity_switch(['Test', 'ODI'], {'Test': 12, 'ODI': 40})
        self.assertIn('href="#test"', markup)
        self.assertIn('<small>40</small>', markup)


if __name__ == '__main__':
    unittest.main()
