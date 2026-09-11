"""Team and ground destination copy stays factual and unique."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
from entity_pages import ground_seo, team_faq, team_glance, team_intro, team_seo, team_totals


def match(date, fmt, gender, winner=None, teams=('India', 'Australia')):
    return {'date': date, 'format': fmt, 'gender': gender, 'teams': list(teams), 'outcome': {'winner': winner}}


INDIA = [
    match('2023-11-19', 'ODI', 'Men', 'Australia'),
    match('2023-01-01', 'ODI', 'Men', 'India'),
    match('2022-06-01', 'T20I', 'Men', 'India'),
    match('2013-08-01', 'Test', 'Men', None),
    match('2022-03-01', 'ODI', 'Women', 'India'),
    match('2021-07-01', 'T20I', 'Women', 'Australia'),
]


class EntityPageTests(unittest.TestCase):
    def test_team_seo_uses_win_counts(self):
        totals = team_totals(INDIA, 'India')
        title, description = team_seo('India', totals)
        self.assertIn('India cricket records', title)
        self.assertIn('3', description)
        self.assertIn('wins', description)
        self.assertLessEqual(len(description), 160)
        self.assertNotIn('\u2014', title + description)
        self.assertNotIn('\u2013', title + description)

    def test_men_and_women_stay_separate(self):
        totals = team_totals(INDIA, 'India')
        odi_men = next(row for row in totals['rows'] if row['format'] == 'ODI' and row['gender'] == 'Men')
        odi_women = next(row for row in totals['rows'] if row['format'] == 'ODI' and row['gender'] == 'Women')
        self.assertEqual(odi_men['matches'], 2)
        self.assertEqual(odi_men['won'], 1)
        self.assertEqual(odi_women['matches'], 1)
        self.assertEqual(odi_women['won'], 1)

    def test_glance_and_faq_keep_numbers(self):
        totals = team_totals(INDIA, 'India')
        glance = team_glance('India', totals)
        self.assertIn("Men&#x27;s ODI", glance)
        self.assertIn("Women&#x27;s T20I", glance)
        html, schema = team_faq('India', totals, '/teams/india/')
        self.assertIn('How many ODIs has India won?', html)
        self.assertEqual(schema['@type'], 'FAQPage')
        self.assertIn('India', team_intro('India', totals))
        self.assertNotIn('\u2013', team_intro('India', totals))

    def test_ground_seo_mentions_match_count(self):
        from entity_pages import ground_totals
        totals = ground_totals(INDIA)
        title, description = ground_seo('Melbourne Cricket Ground', totals)
        self.assertIn('Melbourne Cricket Ground cricket records', title)
        self.assertIn('6', description)


if __name__ == '__main__':
    unittest.main()
