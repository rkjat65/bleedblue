"""World Cup editions use recorded finals, not invented all-time history."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
from world_cup import classify, editions, family_key, is_world_cup_match, player_leaders


def m(date, event, winner=None, fmt='ODI', gender='Men', mid=None, teams=None):
    return {
        'id': mid or date,
        'date': date,
        'event': event,
        'format': fmt,
        'gender': gender,
        'teams': teams or ['India', 'Australia'],
        'outcome': {'winner': winner} if winner else {},
    }


class WorldCupTests(unittest.TestCase):
    def test_qualifiers_are_excluded(self):
        self.assertFalse(is_world_cup_match(m('2018-01-01', 'ICC Cricket World Cup Qualifier')))
        self.assertTrue(is_world_cup_match(m('2023-11-19', 'ICC Cricket World Cup')))
        self.assertEqual(family_key(m('2024-06-29', "ICC Men's T20 World Cup", fmt='T20I')), 'mens-t20')
        self.assertEqual(family_key(m('2022-04-03', "ICC Women's World Cup", gender='Women')), 'womens-odi')

    def test_editions_split_on_calendar_gaps(self):
        matches = [
            m('2015-02-14', 'ICC Cricket World Cup', 'Australia', mid='a'),
            m('2015-03-29', 'ICC Cricket World Cup', 'Australia', mid='b', teams=['Australia', 'New Zealand']),
            m('2019-05-30', 'ICC Cricket World Cup', 'England', mid='c'),
            m('2019-07-14', 'ICC Cricket World Cup', 'England', mid='d', teams=['England', 'New Zealand']),
        ]
        groups = editions(matches)
        self.assertEqual(len(groups), 2)
        data = classify(matches)['mens-odi']
        self.assertEqual(data['editions'][0]['winner'], 'Australia')
        self.assertEqual(data['editions'][1]['winner'], 'England')
        self.assertEqual(data['titles']['Australia'], 1)
        self.assertEqual(data['titles']['England'], 1)

    def test_player_leaders_skip_super_overs_and_unknown_runs(self):
        cards = {
            'm1': {'match': {'date': '2023-11-19', 'id': 'm1'}, 'innings': [
                {'super_over': False, 'team': 'India', 'batting': [
                    {'id': 'kohli', 'runs': 54, 'balls': 63, 'fours': 4, 'sixes': 0},
                    {'id': 'missing', 'runs': None, 'balls': 10},
                ], 'bowling': [{'id': 'starc', 'wickets': 3, 'runs': 55, 'balls': 60}]},
                {'super_over': True, 'batting': [{'id': 'kohli', 'runs': 20, 'balls': 8}], 'bowling': []},
            ]}
        }
        people = {'kohli': {'name': 'Virat Kohli'}, 'starc': {'name': 'Mitchell Starc'}, 'missing': {'name': 'Unknown'}}
        leaders = player_leaders(['m1'], cards, people)
        self.assertEqual(leaders['runs'][0]['runs'], 54)
        self.assertEqual(leaders['wickets'][0]['wickets'], 3)
        self.assertEqual(leaders['scores'][0][0], 54)


if __name__ == '__main__':
    unittest.main()
