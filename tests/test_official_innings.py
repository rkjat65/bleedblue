import unittest
from pathlib import Path
import json, sys, tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
from official_innings import apply_overlay, team_score, same_team, compatible, balls_of, near


def card():
    return {'match': {'id': 'm1', 'date': '2006-03-01', 'format': 'Test', 'teams': ['England', 'India'], 'player_ids': ['a', 'x']},
            'players': {'India': [{'id': 'a', 'name': 'A Batter'}, {'id': 'x', 'name': 'R Lim'}]},
            'innings': [{'team': 'India', 'batting': [{'id': 'x', 'name': 'R Lim', 'runs': 5, 'balls': 8, 'out': True, 'dismissal': 'bowled'}],
                         'bowling': []},
                        {'team': 'England', 'batting': [], 'bowling': [{'id': 'a', 'name': 'A Batter', 'balls': 12, 'runs': 9, 'wickets': 2}]}]}


def overlay(ops, aliases=()):
    root = Path(tempfile.mkdtemp())
    (root / 'data').mkdir()
    (root / 'data/official_innings_overlay.json').write_text(json.dumps({'ops': ops, 'aliases': list(aliases)}), encoding='utf-8')
    return root


PEOPLE = lambda: {'a': {'name': 'A Batter', 'espn_id': '1', 'career': {'Test': {}}}, 'b': {'name': 'Rohit Lim', 'espn_id': '2', 'career': {'T20I': {}}}, 'x': {'name': 'R Lim'}}


class OfficialInningsTests(unittest.TestCase):
    def test_a_batter_who_faced_no_ball_is_added_once_and_in_order(self):
        ops = [{'op': 'add_batting', 'match': 'm1', 'team': 'India', 'inn': 0, 'id': '1', 'pos': 1, 'runs': 0, 'balls': 0, 'fours': 0, 'sixes': 0, 'out': False, 'dismissal': ''}]
        cards = {'m1': card()}
        for _ in range(2):   # idempotent: a rebuild never doubles the row
            apply_overlay(overlay(ops), cards, PEOPLE())
        rows = cards['m1']['innings'][0]['batting']
        self.assertEqual([r['id'] for r in rows], ['a', 'x'])
        self.assertEqual((rows[0]['runs'], rows[0]['out'], rows[0]['dismissal']), (0, False, 'not out'))

    def test_a_credited_run_or_wicket_follows_the_official_list(self):
        cards = {'m1': card()}
        apply_overlay(overlay([{'op': 'fix_batting', 'match': 'm1', 'team': 'India', 'inn': 0, 'id': '2', 'runs': 6, 'balls': 8, 'out': True},
                               {'op': 'fix_bowling', 'match': 'm1', 'team': 'India', 'inn': 1, 'id': '1', 'wickets': 1, 'runs': 9}]), cards,
                      {**PEOPLE(), 'x': {'name': 'Rohit Lim', 'espn_id': '2', 'career': {}}})
        self.assertEqual(cards['m1']['innings'][0]['batting'][0]['runs'], 6)
        self.assertEqual(cards['m1']['innings'][1]['bowling'][0]['wickets'], 1)

    def test_one_person_under_two_ids_becomes_one(self):
        cards = {'m1': card()}
        people = PEOPLE()
        apply_overlay(overlay([], [{'from': 'x', 'espn': '2'}]), cards, people)
        self.assertEqual(cards['m1']['innings'][0]['batting'][0]['id'], 'b')
        self.assertEqual(sorted(cards['m1']['match']['player_ids']), ['a', 'b'])
        self.assertNotIn('x', people)

    def test_a_person_with_their_own_career_is_never_absorbed(self):
        cards = {'m1': card()}
        people = PEOPLE()
        people['x']['career'] = {'T20I': {}}
        apply_overlay(overlay([], [{'from': 'x', 'espn': '2'}]), cards, people)
        self.assertIn('x', people)

    def test_official_opposition_labels_find_their_team(self):
        self.assertTrue(same_team('P.N.G.', 'Papua New Guinea'))
        self.assertTrue(same_team('Czech Rep.', 'Czech Republic'))
        self.assertTrue(same_team('Brazil Women', 'Brazil'))
        self.assertEqual(team_score('U.A.E.', 'United Arab Emirates'), 3)
        self.assertFalse(same_team('U.A.E.', 'United States of America'))

    def test_names_and_dates(self):
        self.assertTrue(compatible('R Limbu', 'Rohit Limbu'))
        self.assertFalse(compatible('Hamza Nisar', 'Hamza Dar'))
        self.assertEqual(balls_of('3.2'), 20)
        self.assertEqual(near('2023-07-29'), ['2023-07-29', '2023-07-28', '2023-07-30'])


if __name__ == '__main__':
    unittest.main()
