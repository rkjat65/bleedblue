import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from tidy import tidy_copy


class TidyCopyTest(unittest.TestCase):
    def test_drops_explanations_on_data_pages(self):
        body = '<h2>Worm</h2><p class="note">Each point is the innings total at the end of that over. Dots mark wickets.</p>'
        self.assertEqual(tidy_copy('/matches/a-b/', body), '<h2>Worm</h2>')

    def test_keeps_short_data_lines(self):
        body = '<p class="muted">India v Australia · 2023-11-19 · ODI · Men</p>'
        self.assertEqual(tidy_copy('/', body), body)

    def test_prose_pages_keep_every_word(self):
        body = '<p class="note">Averages use recorded team innings totals at this venue. Missing innings are omitted.</p>'
        self.assertEqual(tidy_copy('/methodology/', body), body)


if __name__ == '__main__':
    unittest.main()
