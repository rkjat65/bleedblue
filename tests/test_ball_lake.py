"""Ball-by-ball lake: scorebook conventions, phases, fantasy points and tournament tags."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
import build_ball_lake as bl
import tool_pages as tp

IDS = {'A Bat': 'a', 'B Bat': 'b', 'C Bowl': 'c', 'D Field': 'd'}


def ball(batter='A Bat', bowler='C Bowl', runs=0, extras=None, wicket=None, non_striker='B Bat'):
    total = runs + sum((extras or {}).values())
    d = {'batter': batter, 'bowler': bowler, 'non_striker': non_striker, 'runs': {'batter': runs, 'extras': total - runs, 'total': total}}
    if extras:
        d['extras'] = extras
    if wicket:
        d['wickets'] = [wicket]
    return d


def match(competition='IPL', overs=None, event=None):
    info = {'dates': ['2024-04-01'], 'gender': 'male', 'teams': ['Home', 'Away'], 'venue': 'Wankhede Stadium, Mumbai',
            'outcome': {'winner': 'Home', 'by': {'runs': 10}}, 'toss': {'winner': 'Away', 'decision': 'field'},
            'event': event or {'name': 'Indian Premier League'},
            'players': {'Home': ['A Bat', 'B Bat'], 'Away': ['C Bowl', 'D Field']}}
    innings = [{'team': 'Home', 'overs': overs or []}]
    lake = bl.Lake()
    lake.add('m1', info, innings, competition, IDS)
    return lake


class BallLakeTests(unittest.TestCase):
    def test_matchups_follow_the_scorebook(self):
        overs = [{'over': 0, 'deliveries': [
            ball(runs=4), ball(extras={'wides': 1}), ball(runs=1, extras={'noballs': 1}), ball(runs=0),
            ball(wicket={'player_out': 'A Bat', 'kind': 'run out', 'fielders': [{'name': 'D Field'}]}),
        ]}, {'over': 17, 'deliveries': [ball(batter='B Bat', non_striker='A Bat', runs=6),
                                        ball(batter='B Bat', non_striker='A Bat', wicket={'player_out': 'B Bat', 'kind': 'caught', 'fielders': [{'name': 'D Field'}]})]}]
        lake = match(overs=overs)
        a = lake.matchups[('IPL', 'Men', 'IPL', 2024, 'a', 'c')]
        # balls runs outs dots fours sixes innings: the wide is not faced, the no-ball is; the run out is not the bowler's.
        self.assertEqual(a, [4, 5, 0, 2, 1, 0, 1])
        b = lake.matchups[('IPL', 'Men', 'IPL', 2024, 'b', 'c')]
        self.assertEqual(b[:3], [2, 6, 1])

    def test_phases_and_overs(self):
        overs = [{'over': 0, 'deliveries': [ball(runs=4), ball(extras={'wides': 1})]},
                 {'over': 17, 'deliveries': [ball(runs=6)]}]
        lake = match(overs=overs)
        phases = {r['phase']: r for r in lake.phase_teams}
        self.assertEqual(set(phases), {'Powerplay', 'Death'})
        self.assertEqual((phases['Powerplay']['balls'], phases['Powerplay']['runs']), (1, 5))
        bowl = lake.phase_players[('IPL', 'Men', 'IPL', 2024, 'c', 'Away', 'bowl', 'Powerplay')]
        self.assertEqual(bowl[1:3], [1, 5])   # one legal ball, charged the wide
        self.assertEqual([o['over'] for o in lake.overs], [1, 18])
        self.assertIsNone(bl.phase('Test', 3))
        self.assertEqual(bl.phase('ODI', 39), 'Middle')

    def test_fantasy_points_match_the_app(self):
        s = dict(runs=52, balls=30, fours=4, sixes=2, batted=True, out=True, wickets=3, lbw_bowled=1, catches=1, stumpings=0, run_outs=1)
        self.assertEqual(bl.fantasy_points(s), 52 + 4 + 4 + 8 + 75 + 8 + 4 + 8 + 6)
        self.assertEqual(bl.fantasy_points(dict(s, runs=0, fours=0, sixes=0, wickets=0, lbw_bowled=0, catches=0, run_outs=0)), -2)
        overs = [{'over': 0, 'deliveries': [ball(runs=4), ball(wicket={'player_out': 'A Bat', 'kind': 'caught', 'fielders': [{'name': 'D Field'}]})]}]
        rows = {r['player_id']: r for r in match(overs=overs).fantasy}
        self.assertEqual(rows['d']['catches'], 1)
        self.assertEqual(rows['c']['wickets'], 1)
        self.assertEqual(rows['a']['points'], 4 + 1)
        self.assertIn('b', rows)   # in the line-up without facing a ball

    def test_tournament_tags(self):
        self.assertEqual(bl.tournament('IPL', None), 'IPL')
        self.assertEqual(bl.tournament('T20I', {'name': "ICC Women's T20 World Cup"}, 'x', 'Women'), 'T20 World Cup')
        self.assertEqual(bl.tournament('T20I', {'name': "ICC Women's T20 World Cup Qualifier"}, 'x', 'Women'), '')
        self.assertEqual(bl.tournament('T20I', {'name': "ICC Men's T20 World Cup Europe Region Final"}, 'not-listed', 'Men'), '')
        self.assertEqual(bl.tournament('ODI', {'name': 'ICC Cricket World Cup'}), 'World Cup')

    def test_ipl_scorecards_for_studio(self):
        overs = [{'over': 0, 'deliveries': [ball(runs=4), ball(runs=0), ball(runs=0), ball(runs=0), ball(runs=0), ball(runs=0)]},
                 {'over': 1, 'deliveries': [ball(batter='B Bat', non_striker='A Bat', runs=0) for _ in range(6)]}]
        lake = match(overs=overs)
        bat = {r['player_id']: r for r in lake.studio['batting']}
        self.assertEqual((bat['a']['runs'], bat['a']['balls'], bat['a']['position']), (4, 6, 1))
        self.assertEqual(bat['b']['position'], 2)
        bowl = lake.studio['bowling'][0]
        self.assertEqual((bowl['legal'], bowl['conceded'], bowl['maidens']), (12, 4, 1))
        self.assertEqual(lake.studio['matches'][0]['format'], 'IPL')


class QuizPoolTests(unittest.TestCase):
    def test_pools_cover_every_mode_with_clues(self):
        root = Path(__file__).resolve().parent.parent
        pools = tp.quiz_pools(root, {}, lambda p: p['name'])
        self.assertEqual(set(pools), {k for k, _ in tp.QUIZ_MODES})
        for mode, rows in pools.items():
            if not rows:
                continue
            self.assertTrue(all(r['matches'] >= 12 for r in rows), mode)
            self.assertTrue(all(r['role'] in ('Batter', 'Bowler', 'All-rounder', 'Wicketkeeper') for r in rows), mode)
            self.assertTrue(all(r['first'] <= r['last'] for r in rows), mode)
        self.assertGreater(len(pools['odi']), 500)


if __name__ == '__main__':
    unittest.main()
