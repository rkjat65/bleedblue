"""IPL and T20 World Cup tabs: exact figures, honest rates, working tab keys."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
import league_panels as lp
from player_profile import player_seo
from profile_formats import format_switch

BATTER = {
    'name': 'V Kohli',
    'cricinfo_id': '253802',
    'career': {'matches': 3, 'innings': 3, 'runs': 150, 'balls': 100, 'outs': 2, 'hs': 100, 'hs_not_out': True,
               'hundreds': 1, 'fifties': 0, 'ducks': 1, 'fours': 12, 'sixes': 5, 'bowl_innings': 0, 'bowl_balls': 0,
               'conceded': 0, 'wickets': 0, 'dots': 0, 'best': None, 'four_w': 0, 'five_w': 0, 'catches': 2,
               'stumpings': 0, 'awards': 1},
    'teams': [{'team': 'Royal Challengers Bengaluru', 'first': '2024', 'last': '2025', 'matches': 3}],
    'seasons': [],
}
BATTER['seasons'] = [
    {**BATTER['career'], 'edition': '2024', 'teams': ['Royal Challengers Bengaluru'], 'matches': 2, 'innings': 2, 'runs': 100, 'balls': 60, 'outs': 1, 'hundreds': 0, 'ducks': 1, 'hs': 100, 'hs_not_out': False},
    {**BATTER['career'], 'edition': '2025', 'teams': ['Royal Challengers Bengaluru'], 'matches': 1, 'innings': 1, 'runs': 50, 'balls': 40, 'outs': 1, 'hs': 50, 'hs_not_out': False},
]
BOWLER = {
    'name': 'JJ Bumrah',
    'career': {**BATTER['career'], 'runs': 10, 'innings': 2, 'outs': 1, 'hs': 8, 'hundreds': 0, 'balls': 12,
               'bowl_innings': 3, 'bowl_balls': 72, 'conceded': 60, 'wickets': 9, 'dots': 36, 'best': '5/10', 'five_w': 1},
    'teams': [{'team': 'Mumbai Indians', 'first': '2025', 'last': '2025', 'matches': 3}],
    'seasons': [],
}
LEAGUES = {'ipl': {'meta': {'matches': 1243, 'last': '2026-05-31'}, 'players': {'a': BATTER, 'b': BOWLER, 'z': {**BATTER, 'career': {**BATTER['career'], 'matches': 0}}}},
           't20wc': {'meta': {'matches': 378, 'last': '2026-03-08'}, 'players': {'a': BATTER}}}


class LeaguePanelTests(unittest.TestCase):
    def test_only_competitions_played_get_a_tab(self):
        self.assertEqual([k for k, _ in lp.player_leagues('a', LEAGUES)], ['ipl', 't20wc'])
        self.assertEqual([k for k, _ in lp.player_leagues('b', LEAGUES)], ['ipl'])
        self.assertEqual(lp.player_leagues('z', LEAGUES), [])
        self.assertEqual(lp.player_leagues('missing', {}), [])

    def test_rates_use_scorebook_denominators(self):
        f = lp.figures(BATTER['career'])
        self.assertEqual(f['avg'], 75.0)
        self.assertEqual(f['sr'], 150.0)
        self.assertEqual(f['notouts'], 1)
        self.assertEqual(f['highest'], '100*')
        self.assertIsNone(f['econ'])
        b = lp.figures(BOWLER['career'])
        self.assertEqual(b['econ'], 5.0)
        self.assertEqual(b['bowlSr'], 8.0)
        self.assertEqual(b['overs'], '12.0')
        self.assertEqual(lp.role(BOWLER['career']), 'bowler')
        self.assertEqual(lp.role(BATTER['career']), 'batter')

    def test_panel_has_tab_key_season_table_and_app_link(self):
        html = lp.league_panel({'name': 'Virat Kohli'}, 'ipl', BATTER, LEAGUES['ipl']['meta'])
        self.assertIn('data-fmt-panel="ipl"', html)
        self.assertIn('Virat Kohli in the IPL', html)
        self.assertIn('IPL record by season', html)
        self.assertIn('href="/ipl/batting/V%20Kohli"', html)
        table = html[html.index('IPL record by season'):]
        self.assertLess(table.index('>2025<'), table.index('>2024<'))
        self.assertNotIn('—', html)
        self.assertNotIn('–', html)
        wc = lp.league_panel({'name': 'Virat Kohli'}, 't20wc', BATTER, LEAGUES['t20wc']['meta'])
        self.assertIn('/t20-world-cup/batting/', wc)
        self.assertIn('also counted in the T20I record', wc)
        bowler = lp.league_panel({'name': 'Jasprit Bumrah'}, 'ipl', BOWLER, LEAGUES['ipl']['meta'])
        self.assertIn('/ipl/bowling/JJ%20Bumrah', bowler)
        self.assertIn('IPL bowling record', bowler)

    def test_season_chart_skips_years_without_an_edition(self):
        record = {'seasons': [{'edition': '2012', 'runs': 10}, {'edition': '2016', 'runs': 30}]}
        svg = lp.season_bars(record, 'runs', 'T20 World Cup runs by season', ['2007', '2012', '2014', '2016', '2021'])
        self.assertIn('>2014<', svg)
        self.assertNotIn('2013', svg)
        self.assertNotIn('2007', svg)
        self.assertEqual(svg.count('<rect'), 2)

    def test_switch_boot_script_accepts_competition_keys(self):
        found = lp.player_leagues('a', LEAGUES)
        nav = format_switch(['Test'], {'Test': {'matches': 5}}, {'keys': [k for k, _ in found], 'switch': lp.switch_items(found)})
        self.assertIn('ipl:1', nav)
        self.assertIn('t20wc:1', nav)
        self.assertIn('data-fmt="t20wc"', nav)

    def test_seo_adds_ipl_only_when_played(self):
        player = {'name': 'Virat Kohli', 'gender': 'Men', 'teams': ['India'], 'career': {'Test': {'matches': 1, 'runs': 500, 'avg': 50.0}}}
        title, description = player_seo(player, '', lp.seo_clause(lp.player_leagues('a', LEAGUES)))
        self.assertIn('Test and IPL career records', title)
        self.assertIn('150 IPL runs', description)
        plain_title, _ = player_seo(player)
        self.assertNotIn('IPL', plain_title)
        self.assertEqual(lp.seo_clause(lp.player_leagues('b', LEAGUES)), '3 IPL matches')


if __name__ == '__main__':
    unittest.main()
