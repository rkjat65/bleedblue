"""Regression anchors and source completeness checks for independent record layers."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from import_careers import parse_page
from build_record_layers import normalize_format


class CareerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.careers = json.loads((ROOT / 'data/careers.json').read_text(encoding='utf-8'))
        cls.players = {p['espn_id']: p for p in cls.careers['players']}
        cls.history = json.loads((ROOT / 'data/historical_matches.json').read_text(encoding='utf-8'))
        cls.archive = json.loads((ROOT / 'data/international.json').read_text(encoding='utf-8'))

    def test_all_career_scopes_complete(self):
        self.assertEqual(len(self.careers['meta']['scopes']), 18)
        for scope in self.careers['meta']['scopes']:
            self.assertTrue(scope['complete'], scope)
            self.assertGreater(scope['rows'], 0)

    def test_retired_career_anchors(self):
        sachin = self.players['35320']['formats']
        self.assertEqual((sachin['Test']['matches'], sachin['Test']['runs'], sachin['Test']['hundreds']), (200, 15921, 51))
        self.assertEqual((sachin['ODI']['matches'], sachin['ODI']['runs'], sachin['ODI']['hundreds']), (463, 18426, 49))
        murali = next(p for p in self.players.values() if p['source_name'] == 'M Muralidaran')
        self.assertEqual(murali['formats']['Test']['wickets'], 800)
        bradman = next(p for p in self.players.values() if p['source_name'] == 'DG Bradman')
        self.assertEqual((bradman['formats']['Test']['matches'], bradman['formats']['Test']['runs'], bradman['formats']['Test']['avg']), (52, 6996, 99.94))
        mithali = next(p for p in self.players.values() if p['source_name'] == 'M Raj')
        self.assertEqual((mithali['formats']['ODI']['matches'], mithali['formats']['ODI']['runs']), (232, 7805))
        jhulan = next(p for p in self.players.values() if p['source_name'] == 'J Goswami')
        self.assertEqual(jhulan['formats']['ODI']['wickets'], 255)

    def test_identity_and_counts(self):
        ids = {p['id'] for p in self.careers['players']}
        archived = {p['id'] for p in self.archive['players']}
        meta = self.careers['meta']
        self.assertEqual(len(ids), len(self.careers['players']))
        self.assertEqual(meta['players'], len(ids))
        self.assertEqual(meta['combined_players'], len(ids | archived))
        self.assertEqual(meta['archive_players_with_career'], len(ids & archived))
        for p in self.careers['players']:
            for fmt, record in p['formats'].items():
                self.assertIn(record['source'].split('?')[0].split('/')[-1], [p['espn_id'] + '.html'])
                self.assertEqual(record['disciplines'], ['batting', 'bowling', 'fielding'])
                self.assertGreater(record['matches'], 0)

    def test_history_is_complete_and_nonduplicated(self):
        meta, matches = self.history['meta'], self.history['matches']
        self.assertTrue(meta['complete_import'])
        self.assertEqual(len(meta['scopes']), 6)
        self.assertEqual(len(matches), len({m['id'] for m in matches}))
        self.assertFalse({m['id'] for m in matches} & {m['id'] for m in self.archive['matches']})
        self.assertEqual(meta['first'], '1877-03-15')
        first = next(m for m in matches if m['date'] == meta['first'])
        self.assertEqual(first['outcome']['winner'], 'Australia')
        for m in matches:
            self.assertEqual(m['coverage'], 'result-only')
            self.assertEqual(m['totals'], [])
            self.assertEqual(m['player_ids'], [])
            self.assertEqual(len(set(m['teams'])), 2)
            self.assertTrue(m['source'].startswith('https://stats.cricinfo.com/'))

    def test_missing_fields_never_zero_filled(self):
        r = normalize_format({'batting': {'values': {'Mat': '10', 'Inns': '8', 'NO': '2', 'Runs': '1,234', 'HS': '100*', 'BF': '-'}}})
        self.assertEqual((r['runs'], r['outs'], r['highest']), (1234, 6, 100))
        self.assertIsNone(r['balls'])
        self.assertIsNone(r['wickets'])
        t20 = normalize_format({'bowling': {'values': {'Overs': '438.2'}}})
        self.assertEqual(t20['legal'], 2630)

    def test_parser_refuses_error_pages_and_preserves_columns(self):
        with self.assertRaises(ValueError):
            parse_page(b'<html>Service unavailable</html>', 'https://stats.cricinfo.com/')
        body = b'''<table class="engineTable"><caption>Overall figures</caption><thead><tr><th>Player</th><th>Mat</th><th>Runs</th></tr></thead><tbody><tr class="data1"><td><a href="/ci/engine/player/35320.html">SR Tendulkar</a> (IND)</td><td>463</td><td>18426</td></tr></tbody></table><p>Page 1 of 2 Showing 1 - 1 of 2</p><a href="?page=2">Next</a>'''
        page = parse_page(body, 'https://stats.cricinfo.com/')
        self.assertEqual(page['rows'][0]['espn_id'], '35320')
        self.assertEqual(page['rows'][0]['values']['Runs'], '18426')
        self.assertEqual(page['expected'], 2)
        self.assertEqual(page['next'], 'https://stats.cricinfo.com?page=2')


if __name__ == '__main__':
    unittest.main()
