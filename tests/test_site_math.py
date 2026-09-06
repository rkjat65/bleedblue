"""Check combined career ratios and missing denominators independently of rendering."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
from build_site import aggregate, slug, stable_routes


class SiteMathTests(unittest.TestCase):
    def test_weighted_average_uses_total_dismissals(self):
        stats = aggregate({'Test': {'runs': 100, 'outs': 2}, 'ODI': {'runs': 200, 'outs': 10}})
        self.assertEqual(stats['avg'], 25)
        self.assertIsNone(stats['sr'])

    def test_missing_denominator_does_not_become_zero(self):
        stats = aggregate({'Test': {'runs': 100, 'outs': None}, 'ODI': {'runs': 200, 'outs': 10}})
        self.assertIsNone(stats['outs'])
        self.assertIsNone(stats['avg'])

    def test_zero_dismissals_is_not_infinite_average(self):
        stats = aggregate({'Test': {'runs': 100, 'outs': 0}, 'ODI': {'runs': 200, 'outs': 0}})
        self.assertIsNone(stats['avg'])

    def test_url_names_are_ascii_and_safe(self):
        self.assertEqual(slug("Lord’s Cricket Ground"), 'lords-cricket-ground')
        self.assertEqual(slug('Québec / ../'), 'quebec')

    def test_published_identity_urls_survive_renaming(self):
        self.assertEqual(stable_routes({'a':'/players/full-name/'},{'a':'/players/old-name/'},'players'), {'a':'/players/old-name/'})
        self.assertEqual(stable_routes({'42':'/matches/india-england-42/'},{'42':'/matches/england-india-42/'},'matches'), {'42':'/matches/england-india-42/'})

    def test_new_identity_cannot_take_published_url(self):
        self.assertEqual(stable_routes({'a':'/players/new-name/','b':'/players/old-name/'},{'a':'/players/old-name/'},'players'), {'a':'/players/old-name/','b':'/players/old-name-b/'})

    def test_invalid_previous_routes_are_not_reused(self):
        self.assertEqual(stable_routes({'a':'/players/alice/'},{'a':'//other.example/'},'players'), {'a':'/players/alice/'})


if __name__ == '__main__':
    unittest.main()
