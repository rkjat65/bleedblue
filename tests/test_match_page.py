"""Match scorecard helpers: results, overs, fall of wickets and awards stay factual."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
import build_site as bs


class ResultTests(unittest.TestCase):
    def test_super_over_result_names_the_winner(self):
        m = {'outcome': {'result': 'tie', 'eliminator': 'India'}}
        self.assertEqual(bs.result(m), 'Match tied · India won the Super Over')

    def test_dls_method_is_shown(self):
        m = {'outcome': {'winner': 'England', 'by': {'runs': 12}, 'method': 'D/L'}}
        self.assertEqual(bs.result(m), 'England won by 12 runs (D/L method)')

    def test_innings_margin(self):
        m = {'outcome': {'winner': 'Australia', 'by': {'innings': 1, 'runs': 40}}}
        self.assertEqual(bs.result(m), 'Australia won by an innings and 40 runs')


class InningsTextTests(unittest.TestCase):
    def test_overs_and_run_rate_from_balls(self):
        inn = {'runs': 241, 'wickets': 4, 'balls': 258}
        self.assertEqual(bs.overs_text(inn), '43')
        self.assertEqual(bs.run_rate(inn), 5.6)
        self.assertEqual(bs.score_text(inn), '241/4')
        self.assertEqual(bs.overs_text({'runs': 10, 'balls': 20}), '3.2')

    def test_all_out_and_declared_scores(self):
        self.assertEqual(bs.score_text({'runs': 240, 'wickets': 10}), '240')
        self.assertEqual(bs.score_text({'runs': 500, 'wickets': 7, 'declared': True}), '500/7d')

    def test_fall_of_wickets_notation(self):
        inn = {'fall': [{'wicket': 2, 'runs': 76, 'player': 'RG Sharma', 'balls': 58}, {'wicket': 1, 'runs': 30, 'player': 'Shubman Gill', 'balls': 26}]}
        text = bs.fall_text(inn)
        self.assertTrue(text.startswith('<span><b>1-30</b> (Shubman Gill, 4.2 ov)</span>'))
        self.assertIn('<b>2-76</b> (RG Sharma, 9.4 ov)', text)

    def test_award_links_resolve_squad_names(self):
        card = {'awards': ['TM Head', 'Unknown Person'], 'players': {'Australia': [{'id': 'x1', 'name': 'TM Head'}]}}
        people = {'x1': {'name': 'Travis Head'}}
        pp = {'x1': '/players/travis-head/'}
        self.assertEqual(bs.award_links(card, people, pp), '<a href="/players/travis-head/">Travis Head</a>, Unknown Person')
        self.assertEqual(bs.award_links({'awards': []}, people, pp), '')


if __name__ == '__main__':
    unittest.main()
