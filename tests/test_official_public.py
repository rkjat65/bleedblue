"""Official team and innings records stay independent of the scorecard archive."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
from official_public import load_innings_records, load_team_records, official_h2h, team_formats


class OfficialPublicTests(unittest.TestCase):
    def test_india_official_tests_are_not_archive_sized(self):
        payload = load_team_records()
        india = team_formats(payload, 'India')['Test']
        self.assertGreaterEqual(india['played'], 500)
        self.assertEqual(india['won'], 186)
        australia = team_formats(payload, 'Australia')['Test']
        self.assertGreater(australia['won'], 400)

    def test_india_australia_h2h_is_complete(self):
        payload = load_team_records()
        h2h = official_h2h(payload, 'India', 'Australia')
        self.assertEqual(h2h['Test']['played'], 112)
        self.assertEqual(h2h['Test']['left_wins'], 33)
        self.assertEqual(h2h['Test']['right_wins'], 48)
        swapped = official_h2h(payload, 'Australia', 'India')
        self.assertEqual(swapped['Test']['left_wins'], 48)

    def test_official_highest_scores(self):
        records = load_innings_records()['records']
        test = next(row for row in records if row['format'] == 'Test' and 'score' in row['metric'].lower())
        odi = next(row for row in records if row['format'] == 'ODI' and row['gender'] == 'Men' and 'score' in row['metric'].lower())
        self.assertEqual(test['holder'], 'Brian Lara')
        self.assertIn('400', test['value'])
        self.assertEqual(odi['holder'], 'Rohit Sharma')
        self.assertEqual(odi['value'], '264')


if __name__ == '__main__':
    unittest.main()
