"""The 2027 World Cup page: facts, schedule rendering and history."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
import world_cup_2027 as w
from world_cup import load_history, official_record_rows

ROOT = Path(__file__).resolve().parent.parent


class WorldCup2027Tests(unittest.TestCase):
    def setUp(self):
        self.wc = w.load(ROOT)
        self.family = load_history()['families']['mens-odi']

    def render(self, wc=None):
        return w.build(wc or self.wc, self.family, {'India': '/teams/india/'}, {'Newlands': '/grounds/newlands/'},
                       {'Newlands': [{'format': 'ODI', 'gender': 'Men', 'date': '1992-12-07', 'totals': [{'runs': 250}]}]},
                       {'runs': [], 'wickets': []}, official_record_rows(self.family), '2026-10-01')

    def test_facts_are_consistent(self):
        self.assertEqual(len(self.wc['venues']), 12)
        self.assertEqual(sum(s['matches'] for s in self.wc['format']), self.wc['matches_total'])
        self.assertLessEqual(len(self.wc['qualified']), self.wc['teams_total'])
        self.assertEqual({v['country'] for v in self.wc['venues']}, set(self.wc['hosts']))

    def test_page_with_the_announced_schedule(self):
        title, description, body, kind, extra = self.render()
        self.assertEqual(kind, 'SportsEvent')
        self.assertLessEqual(len(description), 160)
        self.assertIn('Full schedule', body)
        self.assertIn('366', body)   # days from 1 October 2026 to 2 October 2027
        self.assertEqual(body.count('<tr data-teams'), 57)
        self.assertNotIn('>Group A 1st</option>', body)
        self.assertIn('Australia', body)
        self.assertIn('<a href="/grounds/newlands/">Newlands</a>', body)
        self.assertEqual(extra['faq']['@type'], 'FAQPage')
        for text in (title, description, body):
            self.assertNotIn('—', text)
            self.assertNotIn('–', text)

    def test_schedule_rows_and_india_time(self):
        wc = dict(self.wc, fixtures=[{'match': 1, 'date': '2027-10-04', 'time': '10:00', 'stage': 'Group A', 'team1': 'India', 'team2': 'England', 'venue': 'Newlands'}])
        body = self.render(wc)[2]
        self.assertIn('data-teams="India|England"', body)
        self.assertIn('<td>13:30</td>', body)   # 10:00 local (UTC+2) is 13:30 IST
        self.assertEqual(w.ist('14:30', 120), '18:00')

    def test_editions_and_finishes(self):
        f = w.finishes(self.family['editions'])
        self.assertEqual(len(f['Australia']['titles']), 6)
        self.assertEqual(w.best_label(f.get('South Africa')), 'Semi-finals')
        self.assertEqual(w.best_label(None), 'Group stage')
        self.assertEqual(w.result_only({'winner': 'Australia', 'final_result': 'Australia won by 6 wickets'}), 'won by 6 wickets')


if __name__ == '__main__':
    unittest.main()
