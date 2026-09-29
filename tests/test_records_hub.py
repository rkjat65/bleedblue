"""Records hub: partnerships rebuild, ranking ties and team records."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
from records_hub import career_table, innings_record_table, partnerships, rank_rows, team_rows

PEOPLE = {'a': {'name': 'A One'}, 'b': {'name': 'B Two'}, 'c': {'name': 'C Three'}, 'd': {'name': 'D Four'}}
MATCH = {'id': 'm1', 'date': '2020-01-01', 'teams': ['India', 'Australia'], 'venue': 'Ground', 'gender': 'Men', 'format': 'ODI', 'outcome': {'winner': 'India', 'by': {'runs': 50}}}


class PartnershipTests(unittest.TestCase):
    def test_stands_follow_batting_order_and_fall(self):
        inn = {'team': 'India', 'runs': 200,
               'batting': [{'id': 'a', 'name': 'A One'}, {'id': 'b', 'name': 'B Two'}, {'id': 'c', 'name': 'C Three'}, {'id': 'd', 'name': 'D Four'}],
               'fall': [{'wicket': 1, 'runs': 40, 'player': 'B Two'}, {'wicket': 2, 'runs': 150, 'player': 'A One'}]}
        stands = partnerships(inn, MATCH, PEOPLE)
        self.assertEqual([(s['wicket'], s['runs'], s['pids'], s['unbroken']) for s in stands],
                         [(1, 40, ('a', 'b'), False), (2, 110, ('a', 'c'), False), (3, 50, ('c', 'd'), True)])

    def test_inconsistent_fall_is_abandoned(self):
        inn = {'team': 'India', 'runs': 100, 'batting': [{'id': 'a', 'name': 'A One'}, {'id': 'b', 'name': 'B Two'}, {'id': 'c', 'name': 'C Three'}],
               'fall': [{'wicket': 1, 'runs': 40, 'player': 'C Three'}]}
        self.assertEqual(partnerships(inn, MATCH, PEOPLE), [])


class RankingTests(unittest.TestCase):
    def test_ties_share_rank(self):
        ranked = rank_rows([{'v': 5}, {'v': 7}, {'v': 7}, {'v': 1}], lambda r: r['v'])
        self.assertEqual([rk for rk, _ in ranked], [1, 1, 3, 4])

    def test_team_rows_and_tables(self):
        m = dict(MATCH, totals=[{'team': 'India', 'runs': 300, 'wickets': 6, 'balls': 300}, {'team': 'Australia', 'runs': 250, 'wickets': 10, 'balls': 280}])
        totals, wins = team_rows([m], {}, 'Men', 'ODI')
        self.assertEqual(len(totals), 2)
        self.assertEqual(wins[0]['runs'], 50)
        head, body, feed, left = innings_record_table('lowest-team-totals', totals * 2, PEOPLE, {}, {'m1': '/matches/m1/'})
        self.assertEqual(head[1], 'Total')
        self.assertIn('250', body[0][1])
        head, body, feed, left = innings_record_table('biggest-wins-by-runs', wins * 3, PEOPLE, {}, {'m1': '/matches/m1/'})
        self.assertIn('50 runs', body[0][1])

    def test_highest_scores_table_and_feed(self):
        rows = [{'pid': 'a', 'runs': 120, 'balls': 100, 'fours': 10, 'sixes': 2, 'no': False, 'team': 'India', 'opp': 'Australia', 'venue': 'Ground', 'date': '2020-01-01', 'match': 'm1'},
                {'pid': 'b', 'runs': 120, 'balls': 90, 'fours': 10, 'sixes': 2, 'no': True, 'team': 'India', 'opp': 'Australia', 'venue': 'Ground', 'date': '2020-01-02', 'match': 'm1'},
                {'pid': 'c', 'runs': 20, 'balls': None, 'fours': None, 'sixes': None, 'no': False, 'team': 'India', 'opp': 'Australia', 'venue': 'Ground', 'date': '2020-01-03', 'match': 'm1'}]
        head, body, feed, left = innings_record_table('highest-scores', rows, PEOPLE, {'a': '/players/a/'}, {'m1': '/matches/m1/'})
        self.assertEqual(body[0][1], '<a href="/matches/m1/">120*</a>')
        self.assertEqual(body[1][0], '2')
        self.assertIn('<span class="missing">-</span>', body[2][4])
        self.assertEqual(feed[0]['v'], '120*')

    def test_career_table_columns(self):
        entries = [{'id': 'a', 'name': 'A One', 'url': '/players/a/', 'teams': ['India'], 'runs': 1000, 'innings': 30, 'matches': 30, 'avg': 40.0, 'span': '2010-2015'},
                   {'id': 'b', 'name': 'B Two', 'url': '/players/b/', 'teams': ['India'], 'runs': 900, 'innings': 10, 'matches': 12, 'avg': 90.0}]
        head, body, qualified = career_table('avg', 'Highest batting average', 'bat', entries, 20, False, {})
        self.assertEqual([p['name'] for p in qualified], ['A One'])
        self.assertEqual(head[:5], ['Rank', 'Highest batting average', 'Player', 'Team', 'Span'])
        self.assertEqual(body[0][1], '40.00')


if __name__ == '__main__':
    unittest.main()


class StandPairTests(unittest.TestCase):
    def test_chart_names_both_batters(self):
        import cricket_charts as cw
        inn = {'team': 'India', 'runs': 120,
               'batting': [{'id': 'a', 'name': 'A One'}, {'id': 'b', 'name': 'B Two'}, {'id': 'c', 'name': 'C Three'}],
               'fall': [{'wicket': 1, 'runs': 50, 'player': 'A One'}]}
        stands = cw.stand_pairs(inn)
        self.assertEqual([(s['wicket'], s['runs'], s['names'], s['unbroken']) for s in stands], [(1, 50, ('A One', 'B Two'), False), (2, 70, ('B Two', 'C Three'), True)])
        chart = cw.partnerships(inn)
        self.assertIn('A One &amp; B Two', chart)
        self.assertIn('2nd wicket (unbroken)', chart)


class HeadlineTests(unittest.TestCase):
    def test_headline_records_pick_best_per_gender_and_format(self):
        from records_hub import headline_records
        m = dict(MATCH)
        cards = {'m1': {'innings': [{'team': 'India', 'batting': [{'id': 'a', 'runs': 120, 'out': False}, {'id': 'b', 'runs': 120, 'out': True}], 'bowling': [{'id': 'c', 'wickets': 5, 'runs': 30}, {'id': 'd', 'wickets': 5, 'runs': 20}]}]}}
        heads = headline_records([m], cards, PEOPLE)
        score = heads[('Men', 'ODI')]['score']
        self.assertEqual((score[0], score[1], score[2]), (120, True, 'a'))
        bowling = heads[('Men', 'ODI')]['bowling']
        self.assertEqual((bowling[0], -bowling[1], bowling[2]), (5, 20, 'd'))
