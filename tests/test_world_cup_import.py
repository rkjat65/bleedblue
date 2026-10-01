"""World Cup archive import: identities, over timelines and the published supplements."""
import json
import sys
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import import_world_cup_data as wc


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.exact = {('Namibia', 'D Wiese'): '221140'}
        self.loose = defaultdict(set, {('Namibia', 'wiese', 'd'): {'221140'}, ('Namibia', 'smith', 'j'): {'1', '2'}})

    def test_full_name_matches_initials_within_the_team(self):
        self.assertEqual(wc.espn_id_for('Namibia', 'D Wiese', self.exact, self.loose), '221140')
        self.assertEqual(wc.espn_id_for('Namibia', 'David Wiese', self.exact, self.loose), '221140')

    def test_ambiguous_or_unknown_names_stay_unlinked(self):
        self.assertEqual(wc.espn_id_for('Namibia', 'John Smith', self.exact, self.loose), 'unlinked:john-smith')
        self.assertTrue(wc.espn_id_for('Canada', 'David Wiese', self.exact, self.loose).startswith('unlinked:'))

    def test_timeline_totals_accumulate(self):
        rows = wc.timeline_rows([(2, 4, 1), (1, 6, 0)])
        self.assertEqual([r['total'] for r in rows], [6, 10])
        self.assertEqual(rows[1]['wickets'], 1)

    def test_published_overs_add_up_to_their_innings(self):
        overs = json.loads((ROOT / 'data/world_cup_overs.json').read_text(encoding='utf-8'))
        cards = json.loads((ROOT / 'data/world_cup_scorecards.json').read_text(encoding='utf-8'))
        for mid, card in cards.items():
            for inn in card['innings']:
                if inn['team'] in overs.get(mid, {}):
                    self.assertEqual(overs[mid][inn['team']][-1]['total'], inn['runs'], mid)


if __name__ == '__main__':
    unittest.main()
