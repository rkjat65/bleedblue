"""Chart geometry uses recorded cricket values; missing inputs stay missing."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
import cricket_charts as cw


def over(n, runs, wickets=0, total=None):
    return {'over': n, 'runs': runs, 'wickets': wickets, 'total': total if total is not None else runs}


class CricketChartTests(unittest.TestCase):
    def test_worm_follows_cumulative_totals(self):
        inn = {'team': 'India', 'overs': [over(1, 8, 0, 8), over(2, 12, 1, 20), over(3, 6, 0, 26)]}
        chart = cw.worm([inn])
        self.assertIn('Worm', chart)
        self.assertIn('India', chart)
        self.assertIn('cw-wicket', chart)
        self.assertNotIn('em-dash', chart)

    def test_manhattan_marks_wicket_overs(self):
        inn = {'team': 'Australia', 'overs': [over(1, 4), over(2, 16, 2), over(3, 1)]}
        chart = cw.manhattan(inn)
        self.assertIn('Manhattan', chart)
        self.assertIn('cw-man-w', chart)
        self.assertIn('Australia', chart)

    def test_partnerships_use_fall_differences(self):
        inn = {'team': 'England', 'runs': 250, 'fall': [
            {'player': 'A', 'runs': 40, 'wicket': 1},
            {'player': 'B', 'runs': 130, 'wicket': 2},
        ]}
        chart = cw.partnerships(inn)
        self.assertIn('40', chart)
        self.assertIn('90', chart)
        self.assertIn('Unbroken stand', chart)
        self.assertIn('120', chart)

    def test_inconsistent_fall_is_not_drawn(self):
        inn = {'runs': 80, 'fall': [{'player': 'A', 'runs': 50, 'wicket': 1}, {'player': 'B', 'runs': 40, 'wicket': 2}]}
        self.assertEqual(cw.partnerships(inn), '')

    def test_scoring_mix_rejects_unknown_boundaries(self):
        self.assertEqual(cw.scoring_mix([{'runs': 50, 'fours': 4, 'sixes': None}]), '')
        mix = cw.scoring_mix([{'runs': 50, 'fours': 4, 'sixes': 2}, {'runs': 20, 'fours': 1, 'sixes': 0}])
        self.assertIn('20', mix)
        self.assertIn('12', mix)
        self.assertIn('38', mix)

    def test_scoring_mix_rejects_boundaries_above_runs(self):
        self.assertEqual(cw.scoring_mix([{'runs': 10, 'fours': 4, 'sixes': 0}]), '')

    def test_phases_split_t20_powerplay(self):
        inn = {'team': 'India', 'overs': [over(n, 10 if n <= 6 else 6) for n in range(1, 21)]}
        chart = cw.phases(inn, 'T20I')
        self.assertIn('Powerplay', chart)
        self.assertIn('60 runs', chart)
        self.assertIn('Death overs', chart)

    def test_empty_overs_skip_match_lab(self):
        self.assertEqual(cw.match_lab({'match': {'format': 'Test'}, 'innings': [{'overs': [], 'fall': []}]}), '')

    def test_form_strip_needs_three_innings(self):
        rows = [{'date': '2020-01-01', 'opponent': 'Australia', 'runs': 10, 'out': True}]
        self.assertEqual(cw.form_strip(rows), '')
        rows += [{'date': '2020-01-02', 'opponent': 'England', 'runs': 100, 'out': False},
                 {'date': '2020-01-03', 'opponent': 'Pakistan', 'runs': 0, 'out': True}]
        chart = cw.form_strip(rows)
        self.assertIn('hundred', chart)
        self.assertIn('duck', chart)
        self.assertIn('notout', chart)

    def test_butterfly_scales_each_row(self):
        chart = cw.pair_lab('A', 'B', {'runs': 100, 'avg': 50, 'sr': 90, 'hundreds': 2, 'sixes': 10},
                            {'runs': 200, 'avg': 25, 'sr': 120, 'hundreds': 1, 'sixes': 20})
        self.assertIn('A', chart)
        self.assertIn('200', chart)
        self.assertIn('width:50.00%', chart)

    def test_unknown_runs_do_not_become_zero_in_player_lab(self):
        rows = [{'date': '2020-01-01', 'format': 'ODI', 'runs': None, 'position': 1, 'opponent': 'Australia'}]
        self.assertEqual(cw.player_lab(rows, 'Tester'), '')

    def test_result_decades_use_pixel_heights(self):
        matches = []
        for year, winner in [('1990', 'India'), ('1991', 'Australia'), ('2000', 'India'), ('2001', 'India'), ('2010', None)]:
            matches.append({'date': year+'-01-01', 'outcome': {'winner': winner}})
        chart = cw.result_decades(matches, 'India')
        self.assertIn('height:', chart)
        self.assertIn('px', chart)
        self.assertNotIn('height:0px', chart)

    def test_zero_wickets_do_not_divide_by_zero(self):
        rows = [{'date': f'2020-01-0{i}', 'format': 'ODI', 'wickets': 0, 'legal': 24, 'conceded': 20, 'opponent': 'Australia'} for i in range(1, 6)]
        self.assertNotIn('Error', cw.player_lab(rows, 'Bowler'))
        self.assertEqual(cw.trajectory(rows, 'wickets'), '')


if __name__ == '__main__':
    unittest.main()
