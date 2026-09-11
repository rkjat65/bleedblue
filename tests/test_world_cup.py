"""World Cup pages use official history for titles, archive only for scorecards."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
from world_cup import (
    analysis_heading,
    analysis_lede,
    analysis_window,
    attach_unlabelled,
    classify,
    coverage_note,
    editions,
    family_key,
    is_world_cup_match,
    load_history,
    merge_official,
    player_leaders,
    pretty_date,
    timeline_table,
    world_cup_family,
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

    def test_pathway_events_are_not_the_world_cup(self):
        self.assertFalse(is_world_cup_match(m('2024-02-15', "ICC Men's Cricket World Cup League 2")))
        self.assertFalse(is_world_cup_match(m('2008-02-21', "ICC Women's World Cup Qualifying Series", gender='Women')))
        self.assertFalse(is_world_cup_match(m('2019-03-22', "ICC Men's T20 World Cup Europe Region Final", fmt='T20I')))
        self.assertFalse(is_world_cup_match(m('2025-06-15', "ICC Men's T20 World Cup Americas Region Final", fmt='T20I')))
        self.assertIsNone(family_key(m('2024-02-15', "ICC Men's Cricket World Cup League 2")))
        self.assertIsNone(family_key(m('2008-02-22', "ICC Women's World Cup Qualifying Series", gender='Women')))

    def test_unlabelled_afghanistan_t20_world_cup_is_attached(self):
        labelled = [
            m('2024-06-01', "ICC Men's T20 World Cup", fmt='T20I', mid='open'),
            m('2024-06-29', "ICC Men's T20 World Cup", fmt='T20I', mid='final', winner='India', teams=['India', 'South Africa']),
        ]
        afg = m('2024-06-07', '', fmt='T20I', mid='1415714', teams=['Afghanistan', 'New Zealand'])
        opener = m('2014-03-16', '', fmt='T20I', mid='682897', teams=['Afghanistan', 'Bangladesh'])
        bilateral = m('2026-01-19', '', fmt='T20I', mid='1517823', teams=['Afghanistan', 'West Indies'])
        self.assertEqual(attach_unlabelled(afg), 'mens-t20')
        self.assertEqual(attach_unlabelled(opener), 'mens-t20')
        self.assertIsNone(attach_unlabelled(bilateral))
        self.assertEqual(world_cup_family(afg), 'mens-t20')
        ids = {row['id'] for row in classify(labelled + [afg, bilateral])['mens-t20']['matches']}
        self.assertIn('1415714', ids)
        self.assertNotIn('1517823', ids)
        self.assertNotIn('2008-02-21', {row['id'] for row in classify([
            m('2008-02-21', "ICC Women's World Cup Qualifying Series", gender='Women', mid='2008-02-21'),
            m('2009-03-22', "ICC Women's World Cup", gender='Women', mid='final09', teams=['England', 'New Zealand']),
        ]).get('womens-odi', {'matches': []})['matches']})

    def test_analysis_window_starts_at_first_overs(self):
        matches = [
            m('2003-02-09', 'ICC Cricket World Cup', mid='open03'),
            m('2023-11-19', 'ICC Cricket World Cup', mid='final23', teams=['Australia', 'India']),
        ]
        cards = {
            'open03': {'innings': [{'overs': [{'over': 1, 'runs': 4}], 'batting': [{'id': 'a', 'runs': 10}]}]},
            'final23': {'innings': [{'overs': [{'over': 1, 'runs': 6}], 'batting': [{'id': 'b', 'runs': 20}]}]},
        }
        window = analysis_window(matches, cards)
        self.assertEqual(window['from_year'], '2003')
        self.assertEqual(window['from_date'], '2003-02-09')
        self.assertEqual(window['ball_by_ball'], 2)
        self.assertEqual(pretty_date('2003-02-09'), '9 February 2003')
        bundled = merge_official(matches, cards, {})
        mens = bundled['families']['mens-odi']
        self.assertEqual(mens['analysis']['from_year'], '2003')
        self.assertEqual(analysis_heading(mens), 'Ball-by-ball analysis from 2003')
        self.assertIn('Ball-by-ball data is available from 9 February 2003', analysis_lede(mens))
        self.assertIn('Ball-by-ball analysis starts in 2003', coverage_note(mens))
        self.assertNotIn('available scorecards', analysis_heading(mens).lower())
        self.assertNotIn('available scorecards', analysis_lede(mens).lower())

    def test_leaders_start_at_ball_by_ball_year(self):
        matches = [
            m('1999-06-20', 'ICC Cricket World Cup', mid='old', winner='Australia', teams=['Australia', 'Pakistan']),
            m('2003-02-09', 'ICC Cricket World Cup', mid='new'),
        ]
        people = {'a': {'name': 'Old Batter'}, 'b': {'name': 'New Batter'}}
        cards = {
            'old': {'match': {'date': '1999-06-20', 'id': 'old'}, 'innings': [{'overs': [], 'batting': [{'id': 'a', 'runs': 200, 'balls': 120}], 'bowling': []}]},
            'new': {'match': {'date': '2003-02-09', 'id': 'new'}, 'innings': [{'overs': [{'over': 1, 'runs': 4}], 'batting': [{'id': 'b', 'runs': 50, 'balls': 40}], 'bowling': []}]},
        }
        mens = merge_official(matches, cards, people)['families']['mens-odi']
        self.assertEqual(mens['analysis']['from_year'], '2003')
        self.assertEqual(mens['leaders']['runs'][0]['name'], 'New Batter')
        self.assertEqual(mens['leaders']['runs'][0]['runs'], 50)
        self.assertTrue(all(row['name'] != 'Old Batter' for row in mens['leaders']['runs']))

    def test_warmups_before_labelled_start_are_not_attached(self):
        labelled = [
            m('2019-05-30', 'ICC Cricket World Cup', mid='open19'),
            m('2019-07-14', 'ICC Cricket World Cup', mid='final19', winner='England', teams=['England', 'New Zealand']),
        ]
        warmup = m('2019-05-19', '', mid='1168515', teams=['Afghanistan', 'Ireland'])
        wc_game = m('2019-06-22', '', mid='1144510', teams=['Afghanistan', 'India'])
        ids = {row['id'] for row in classify(labelled + [warmup, wc_game])['mens-odi']['matches']}
        self.assertNotIn('1168515', ids)
        self.assertIn('1144510', ids)
        self.assertIn('open19', ids)

    def test_afghanistan_scorecard_without_overs_is_described(self):
        matches = [
            m('2024-06-01', "ICC Men's T20 World Cup", fmt='T20I', mid='labelled', teams=['India', 'Ireland']),
            m('2024-06-07', '', fmt='T20I', mid='1415714', teams=['Afghanistan', 'New Zealand']),
        ]
        cards = {
            'labelled': {'innings': [{'overs': [{'over': 1, 'runs': 8}], 'batting': []}]},
            '1415714': {'innings': [{'overs': [], 'batting': [{'id': 'gurbaz', 'runs': 80}]}]},
        }
        window = analysis_window(classify(matches)['mens-t20']['matches'], cards)
        self.assertEqual(window['from_year'], '2024')
        self.assertEqual(window['scorecard_only'], 1)
        self.assertEqual(window['afghanistan_without_balls'], 1)
        lede = analysis_lede({'analysis': window})
        self.assertIn('Afghanistan World Cup matches', lede)
        self.assertIn('Cricsheet does not publish Afghanistan', lede)

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
        self.assertEqual(mens['editions'][0]['start_date'], '1975-06-07')
        self.assertEqual(mens['editions'][-1]['start_date'], '2023-10-05')
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
