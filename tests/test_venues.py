"""Ground canonicalisation merges true duplicates and never merges generic names."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
from venues import canonical_venue, canonicalise_matches, strip_suffix


class VenueTests(unittest.TestCase):
    def test_city_suffix_is_stripped_from_descriptive_names(self):
        self.assertEqual(strip_suffix('Wankhede Stadium, Mumbai'), 'Wankhede Stadium')
        self.assertEqual(strip_suffix('Kensington Oval, Bridgetown, Barbados'), 'Kensington Oval')
        self.assertEqual(strip_suffix('Sir Vivian Richards Stadium, North Sound, Antigua'), 'Sir Vivian Richards Stadium')

    def test_generic_names_keep_their_city(self):
        self.assertEqual(strip_suffix('County Ground, Bristol'), 'County Ground, Bristol')
        self.assertEqual(strip_suffix('National Stadium, Karachi'), 'National Stadium, Karachi')
        self.assertEqual(canonical_venue('National Cricket Stadium, Grenada'), "National Cricket Stadium, St George's")

    def test_historical_short_names_map_to_grounds(self):
        self.assertEqual(canonical_venue('Melbourne'), 'Melbourne Cricket Ground')
        self.assertEqual(canonical_venue('Colombo (RPS)'), 'R Premadasa Stadium')
        self.assertEqual(canonical_venue('R.Premadasa Stadium, Khettarama'), 'R Premadasa Stadium')
        self.assertEqual(canonical_venue('Colombo (SSC)'), 'Sinhalese Sports Club Ground')
        self.assertEqual(canonical_venue("Lord's, London"), "Lord's")

    def test_dated_aliases(self):
        self.assertEqual(canonical_venue('Perth', '2010-01-01'), 'WACA Ground')
        self.assertEqual(canonical_venue('Perth', '2022-12-04'), 'Perth Stadium')
        self.assertEqual(canonical_venue('Wellington', '2019-03-01', 'Test'), 'Basin Reserve')
        self.assertEqual(canonical_venue('Wellington', '2019-03-01', 'ODI'), 'Wellington')
        self.assertEqual(canonical_venue('Hyderabad', '2019-03-01'), 'Hyderabad')

    def test_unknown_names_pass_through(self):
        self.assertEqual(canonical_venue('Some New Ground'), 'Some New Ground')
        self.assertEqual(canonical_venue(''), '')

    def test_canonicalise_matches_records_changes(self):
        matches = [{'venue': 'Sydney', 'date': '1990-01-01', 'format': 'Test'}, {'venue': 'Sydney Cricket Ground', 'date': '2020-01-01', 'format': 'Test'}]
        changed = canonicalise_matches(matches)
        self.assertEqual(changed, {'Sydney': 'Sydney Cricket Ground'})
        self.assertEqual(matches[0]['venue'], 'Sydney Cricket Ground')
        self.assertEqual(matches[0]['venue_recorded'], 'Sydney')
        self.assertNotIn('venue_recorded', matches[1])


if __name__ == '__main__':
    unittest.main()
