"""World Cup pages use official history for titles, archive only for scorecards."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
from world_cup import (
    classify,
    editions,
    family_key,
    is_world_cup_match,
    load_history,
    merge_official,
    player_leaders,
    timeline_table,
)


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

    def test_official_mens_odi_history_is_complete(self):
        history = load_history()
        mens = history['families']['mens-odi']
        years = [cup['year'] for cup in mens['editions']]
        self.assertEqual(years[0], 1975)
        self.assertEqual(years[-1], 2023)
        self.assertEqual(len(years), 13)
        self.assertEqual(mens['titles']['Australia'], 6)
        self.assertEqual(mens['titles']['India'], 2)
        self.assertEqual(mens['titles']['West Indies'], 2)
        self.assertEqual(mens['editions'][0]['winner'], 'West Indies')
        self.assertEqual(mens['editions'][0]['runner_up'], 'Australia')
        self.assertEqual(set(mens['editions'][0]['losing_semi_finalists']), {'England', 'New Zealand'})
        self.assertEqual(mens['editions'][-1]['winner'], 'Australia')
        self.assertEqual(mens['editions'][-1]['runner_up'], 'India')
        self.assertEqual(set(mens['editions'][-1]['losing_semi_finalists']), {'New Zealand', 'South Africa'})
        self.assertEqual(sum(mens['titles'].values()), 13)

    def test_official_titles_ignore_incomplete_archive(self):
        matches = [
            m('2003-03-23', 'ICC Cricket World Cup', 'Australia', mid='a', teams=['Australia', 'India']),
            m('2011-04-02', 'ICC Cricket World Cup', 'India', mid='b', teams=['India', 'Sri Lanka']),
            m('2023-11-19', 'ICC Cricket World Cup', 'Australia', mid='c', teams=['Australia', 'India']),
        ]
        bundled = merge_official(matches, {}, {})
        mens = bundled['families']['mens-odi']
        self.assertEqual(mens['titles']['Australia'], 6)
        self.assertEqual(len(mens['editions']), 13)
        self.assertEqual(mens['editions'][0]['year'], '1975')
        self.assertEqual(mens['editions'][0]['archive_matches'], 0)
        self.assertEqual(mens['editions'][-1]['archive_matches'], 1)
        archive_titles = classify(matches)['mens-odi']['titles']
        self.assertEqual(archive_titles['Australia'], 2)
        self.assertNotEqual(dict(mens['titles']), dict(archive_titles))

    def test_timeline_lists_semi_finalists_and_skips_knockout_gaps(self):
        bundled = merge_official([], {}, {})
        rows = timeline_table(bundled['families']['mens-odi'], {'West Indies': '/teams/west-indies/'})
        latest = rows[0]
        self.assertEqual(latest[0], '2023')
        self.assertIn('Australia', latest[2])
        self.assertIn('India', latest[3])
        self.assertIn('New Zealand', latest[4])
        self.assertIn('South Africa', latest[4])
        first = rows[-1]
        self.assertEqual(first[0], '1975')
        self.assertIn('West Indies', first[2])
        womens_2009 = next(cup for cup in bundled['families']['womens-odi']['editions'] if cup['year'] == '2009')
        self.assertEqual(womens_2009['losing_semi_finalists'], [])
        self.assertFalse(womens_2009.get('knockout', True))

    def test_other_families_have_complete_title_counts(self):
        history = load_history()
        self.assertEqual(history['families']['womens-odi']['titles']['Australia'], 7)
        self.assertEqual(history['families']['womens-odi']['editions'][-1]['winner'], 'India')
        self.assertEqual(history['families']['womens-odi']['editions'][-1]['year'], 2025)
        self.assertEqual(history['families']['mens-t20']['titles']['India'], 3)
        self.assertEqual(history['families']['mens-t20']['editions'][-1]['year'], 2026)
        self.assertEqual(history['families']['womens-t20']['titles']['Australia'], 7)
        json.loads(Path(__file__).resolve().parent.parent.joinpath('data/world_cup_history.json').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
