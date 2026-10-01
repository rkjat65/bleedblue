"""IPL ground tabs and T20 World Cup team tabs."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
import league_entities as le

TOTAL = {'runs': 249, 'wickets': 4, 'balls': 112, 'team': 'Sunrisers Hyderabad', 'opponent': 'Mumbai Indians', 'edition': '2026', 'match_id': '1'}
LOW = {'runs': 67, 'wickets': 10, 'balls': 92, 'team': 'Kolkata Knight Riders', 'opponent': 'Mumbai Indians', 'edition': '2008', 'match_id': '2'}
VENUE = {
    'name': 'Wankhede Stadium, Mumbai', 'city': 'Mumbai', 'matches': 132,
    'aliases': [{'name': 'Wankhede Stadium', 'first': '2008-04-20', 'last': '2019-05-05', 'matches': 73},
                {'name': 'Wankhede Stadium, Mumbai', 'first': '2021-04-10', 'last': '2026-05-24', 'matches': 59}],
    'seasons': [{'edition': '2025', 'matches': 7}, {'edition': '2026', 'matches': 8}],
    'bat_first_won': 59, 'chase_won': 72, 'tied': 1, 'no_result': 0, 'decided': 131,
    'toss_bat': 31, 'toss_field': 101, 'toss_winner_won': 68, 'avg_first': 173.1, 'avg_second': 162.0,
    'highest_total': TOTAL, 'lowest_total': LOW,
    'top_batters': [{'player': 'Rohit Sharma', 'id': '740742ef', 'runs': 2632, 'balls': 1877, 'innings': 89}],
    'top_bowlers': [{'player': 'Lasith Malinga', 'id': 'a12e1d51', 'wickets': 68, 'balls': 1010, 'conceded': 1179, 'innings': 43}],
    'best_innings': {'player': 'AB de Villiers', 'id': 'c4487b84', 'runs': 133, 'balls': 59, 'team': 'RCB', 'opponent': 'MI', 'edition': '2015'},
    'best_bowling': None,
}
TEAM = {
    'name': 'India', 'matches': 60, 'won': 43, 'lost': 16, 'tied': 1, 'no_result': 0, 'titles': ['2007', '2024'],
    'editions': [{'edition': '2007', 'played': 6, 'won': 4, 'lost': 1, 'finish': 'Champions'},
                 {'edition': '2021', 'played': 5, 'won': 3, 'lost': 2, 'finish': None}],
    'opponents': [{'team': 'Pakistan', 'played': 9, 'won': 7, 'lost': 1}],
    'highest_total': TOTAL, 'lowest_total': LOW, 'top_batters': [], 'top_bowlers': [], 'best_innings': None, 'best_bowling': None,
}


class LeagueEntityTests(unittest.TestCase):
    def test_grounds_match_through_the_archive_canonicaliser(self):
        idx = le.ground_index({'venues': {'w': VENUE}}, {'Wankhede Stadium', 'Eden Gardens'})
        self.assertEqual(list(idx), ['Wankhede Stadium'])
        self.assertEqual(le.ground_index({'venues': {'w': VENUE}}, {'Eden Gardens'}), {})

    def test_renamed_ground_goes_to_its_current_name(self):
        pune = {**VENUE, 'name': 'Maharashtra Cricket Association Stadium, Pune', 'matches': 51,
                'aliases': [{'name': 'Subrata Roy Sahara Stadium', 'first': '2012-04-01', 'last': '2013-05-01'},
                            {'name': 'Maharashtra Cricket Association Stadium', 'first': '2016-04-01', 'last': '2023-05-01'}]}
        idx = le.ground_index({'venues': {'p': pune}}, {'Subrata Roy Sahara Stadium', 'Maharashtra Cricket Association Stadium'})
        self.assertEqual(list(idx), ['Maharashtra Cricket Association Stadium'])

    def test_ground_seo_mentions_the_ipl_only_when_hosted(self):
        from entity_pages import ground_seo
        totals = {'formats': ['Test', 'ODI', 'T20I'], 'matches': 81}
        title, description = ground_seo('Wankhede Stadium', totals, None, 132)
        self.assertEqual(title, 'Wankhede Stadium cricket records: Test, ODI, T20I and IPL')
        self.assertIn('132 IPL matches', description)
        plain, _ = ground_seo('Wankhede Stadium', totals)
        self.assertNotIn('IPL', plain)

    def test_ground_panel_shows_results_records_and_player_links(self):
        html = le.ground_panel('Wankhede Stadium', VENUE, {'last': '2026-05-31'}, {'740742ef': '/players/rohit-sharma/'})
        self.assertIn('data-fmt-panel="ipl"', html)
        self.assertIn('IPL at Wankhede Stadium', html)
        self.assertIn('<a href="/players/rohit-sharma/">Rohit Sharma</a>', html)
        self.assertIn('Lasith Malinga', html)
        self.assertIn('249/4', html)
        self.assertIn('>67<', html)
        self.assertIn('54.96', html)   # 72 of 131 decided matches won chasing
        self.assertIn('/ipl/venues/Wankhede%20Stadium%2C%20Mumbai', html)
        self.assertNotIn('—', html)

    def test_team_panel_shows_titles_finishes_and_opponents(self):
        html = le.team_panel('India', TEAM, {'last': '2026-03-08'}, {})
        self.assertIn('data-fmt-panel="t20wc"', html)
        self.assertIn('2 titles: 2007, 2024', html)
        self.assertIn('Champions', html)
        self.assertIn('Pakistan', html)
        self.assertIn('71.66', html)   # 43 of 60
        self.assertIn('also in the T20I tab', html)
        self.assertNotIn('–', html)


if __name__ == '__main__':
    unittest.main()
