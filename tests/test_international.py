"""Integrity checks for imported cricket data and its generated scorecards."""
import json
import unittest
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class InternationalDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'data/international.json').read_text(encoding='utf-8'))
        cls.cards = {}
        for file in (ROOT / 'data/scorecards').glob('*.json'):
            cls.cards.update(json.loads(file.read_text(encoding='utf-8')))

    def test_unique_ids_and_source_counts(self):
        matches = self.data['matches']
        self.assertEqual(len(matches), len({m['id'] for m in matches}))
        self.assertEqual(len(matches), self.data['meta']['matches'])
        self.assertEqual(dict(Counter(m['format'] for m in matches)), self.data['meta']['formats'])
        self.assertEqual(dict(Counter(m['gender'] for m in matches)), self.data['meta']['gender'])
        self.assertEqual(len(self.data['players']), self.data['meta']['players'])

    def test_all_downloaded_international_files_are_included(self):
        archives = list((ROOT / '.data-cache').glob('*_json.zip'))
        if not archives:
            self.skipTest('Source ZIPs are locally cached; run the importer to verify original files')
        expected = set()
        for file in archives:
            with zipfile.ZipFile(file) as archive:
                expected.update(Path(name).stem for name in archive.namelist() if name.endswith('.json') and Path(name).stem.isdigit())
        self.assertEqual(expected, {m['id'] for m in self.data['matches']})

    def test_every_match_has_scorecard_and_resolved_roster(self):
        people = {p['id'] for p in self.data['players']}
        for match in self.data['matches']:
            self.assertIn(match['id'], self.cards)
            self.assertEqual(match, self.cards[match['id']]['match'])
            self.assertTrue(set(match['player_ids']).issubset(people))

    def test_innings_runs_balls_and_wickets_reconcile(self):
        for match in self.data['matches']:
            for inning in self.cards[match['id']]['innings']:
                with self.subTest(match=match['id'], team=inning['team']):
                    self.assertEqual(inning['runs'], sum(b['runs'] for b in inning['batting']) + inning['extras'])
                    self.assertEqual(inning['balls'], sum(b['balls'] for b in inning['bowling']))
                    self.assertEqual(inning['wickets'], len(inning['fall']))
                    self.assertLessEqual(sum(b['wickets'] for b in inning['bowling']), inning['wickets'])

    def test_player_aggregates_exclude_super_overs(self):
        totals = defaultdict(Counter)
        for match in self.data['matches']:
            for pid in match['player_ids']:
                totals[pid, match['format']]['matches'] += 1
            for inning in self.cards[match['id']]['innings']:
                if inning['super_over']:
                    continue
                for batter in inning['batting']:
                    totals[batter['id'], match['format']]['runs'] += batter['runs']
                for bowler in inning['bowling']:
                    totals[bowler['id'], match['format']]['wickets'] += bowler['wickets']
        for player in self.data['players']:
            for fmt, stats in player['formats'].items():
                for field in ('matches', 'runs', 'wickets'):
                    self.assertEqual(stats[field], totals[player['id'], fmt][field], (player['name'], fmt, field))

    def test_homepage_counts_use_full_archive(self):
        home = json.loads((ROOT / 'data/home.json').read_text(encoding='utf-8'))
        self.assertEqual(home['meta'], self.data['meta'])
        for fmt, summary in home['format_summary'].items():
            self.assertEqual(summary['matches'], self.data['meta']['formats'][fmt])
        self.assertLess((ROOT / 'data/home.json').stat().st_size, 100_000)


if __name__ == '__main__':
    unittest.main()
