"""Ground facts: the Wikipedia parser stays conservative and the masthead shows only what is known."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
import fetch_ground_facts as facts  # noqa: E402
from entity_pages import ground_masthead, ground_schema, ground_seo, ground_totals  # noqa: E402


def page(title, text, extract):
    return {'title': title, 'text': text, 'extract': extract, 'qid': None, 'lat': None, 'lon': None}


CRICKET = '{{Infobox cricket ground\n| ground_name = X\n| capacity = 68,000 (Current) <br/>100,000 (Planned)<ref>x</ref>\n| established = 1864\n| end1 = High Court End\n| end2 = Pavilion End\n}}'
FOOTBALL = '{{Infobox venue\n| capacity = 75,731\n}}'


class ParserTests(unittest.TestCase):
    def test_capacity_takes_the_first_plausible_number(self):
        self.assertEqual(facts.first_int('68,000 (Current) <br/>100,000 (Planned)'), 68000)
        self.assertEqual(facts.first_int('33,100 (2011-present)<ref name="x"/>'), 33100)
        self.assertIsNone(facts.first_int('<!-- 12,000 --> unknown'))
        self.assertIsNone(facts.first_int('250'))

    def test_year_and_ends(self):
        self.assertEqual(facts.first_year('{{start date and age|1853|9|23|df=y}}'), 1853)
        self.assertIsNone(facts.first_year('<!-- {{Start date|YYYY|MM|DD|df=y}} -->'))
        fields = facts.infobox(CRICKET)
        self.assertEqual(facts.ends(fields), ['High Court End', 'Pavilion End'])
        self.assertEqual(facts.ends({'end1': "North: WACA Member's End<ref>x</ref>", 'end2': 'South: Langer Stand End'}), ["WACA Member's End", 'Langer Stand End'])
        self.assertEqual(facts.ends({'end1': 'Only one'}), [])

    def test_place_labels_that_are_not_cities_are_dropped(self):
        self.assertEqual(facts.city_from_place('Kolkata'), 'Kolkata')
        self.assertIsNone(facts.city_from_place('Ward No. 45, Kolkata Municipal Corporation'))
        self.assertIsNone(facts.city_from_place('Western Australia'))

    def test_cricket_ground_outranks_a_football_stadium_with_the_same_name(self):
        football = page('Old Trafford', FOOTBALL, 'Old Trafford is a football stadium in Greater Manchester, England. It is near the cricket ground.')
        cricket = page('Old Trafford Cricket Ground', CRICKET, 'Old Trafford is a cricket ground in Old Trafford, Greater Manchester, England.')
        district = page('Kennington', '{{Infobox UK place\n| capacity = 1\n}}', 'Kennington is a district in South London with a cricket ground.')
        self.assertLess(facts.score(football, 'Old Trafford', ['Old Trafford'], 'Manchester', 'England'), facts.score(cricket, 'Old Trafford', ['Old Trafford'], 'Manchester', 'England'))
        self.assertEqual(facts.score(district, 'Kennington Oval', ['The Oval'], 'London', 'England'), -99)
        oval = page('The Oval', CRICKET, 'The Oval is an international cricket ground in Kennington, London.')
        self.assertGreaterEqual(facts.score(oval, 'Kennington Oval', ['The Oval', 'Kennington Oval'], 'London', 'England'), 6)

    def test_a_cricket_ground_with_a_different_name_is_not_accepted(self):
        mcg = page('Melbourne Cricket Ground', CRICKET, 'The Melbourne Cricket Ground is a cricket ground in Melbourne, Australia.')
        self.assertEqual(facts.score(mcg, 'Brisbane Cricket Ground', ['Brisbane'], 'Brisbane', 'Australia'), -99)
        gabba = page('The Gabba', CRICKET, 'The Gabba is a cricket ground in Brisbane, Australia.')
        self.assertEqual(facts.score(gabba, 'Brisbane Cricket Ground', ['Brisbane'], 'Brisbane', 'Australia'), -99)
        self.assertGreaterEqual(facts.score(gabba, 'Brisbane Cricket Ground', ['Brisbane'], 'Brisbane', 'Australia', direct=True), 8)

    def test_country_check(self):
        self.assertTrue(facts.same_country('England', 'United Kingdom'))
        self.assertTrue(facts.same_country('West Indies', 'Barbados'))
        self.assertTrue(facts.same_country(None, 'Australia'))
        self.assertFalse(facts.same_country('Sri Lanka', 'Australia'))


def match(date, fmt, gender):
    return {'date': date, 'format': fmt, 'gender': gender, 'teams': ['India', 'Australia'], 'outcome': {'winner': None}}


TOTALS = ground_totals([match('2024-01-01', 'Test', 'Men'), match('2010-01-01', 'ODI', 'Men'), match('2019-01-01', 'T20I', 'Women')])
FACTS = {'city': 'Kolkata', 'country': 'India', 'capacity': 68000, 'opened': 1864, 'ends': ['High Court End', 'Pavilion End'], 'lat': 22.56444, 'lon': 88.34333, 'wikipedia': 'https://en.wikipedia.org/wiki/Eden_Gardens'}


class MastheadTests(unittest.TestCase):
    def test_masthead_lists_place_capacity_and_ends(self):
        html = ground_masthead('Eden Gardens', TOTALS, FACTS, '<div class="actions"></div>')
        self.assertIn('<p class="eyebrow">GROUND · KOLKATA · INDIA</p>', html)
        self.assertIn('<h1>Eden Gardens</h1>', html)
        self.assertIn('3 recorded internationals · 2010 to 2024 · Test, ODI and T20I', html)
        self.assertIn('<strong>68,000</strong>', html)
        self.assertIn('<strong>1864</strong>', html)
        self.assertIn('High Court End and Pavilion End', html)
        self.assertIn('openstreetmap.org/?mlat=22.56444', html)
        self.assertIn('Wikipedia', html)
        self.assertNotIn('—', html)

    def test_masthead_without_facts_stays_honest(self):
        html = ground_masthead('Somewhere Oval', TOTALS)
        self.assertIn('<p class="eyebrow">GROUND</p>', html)
        self.assertNotIn('Capacity', html)
        self.assertNotIn('gr-links', html)

    def test_seo_and_schema_carry_the_place(self):
        title, description = ground_seo('Eden Gardens', TOTALS, FACTS)
        self.assertEqual(title, 'Eden Gardens cricket records: Test, ODI and T20I')
        self.assertIn('Eden Gardens, Kolkata, India has 3 recorded', description)
        self.assertIn('Capacity 68,000.', description)
        schema = ground_schema('Eden Gardens', '/grounds/eden-gardens/', description, FACTS)
        self.assertEqual(schema['address'], {'@type': 'PostalAddress', 'addressLocality': 'Kolkata', 'addressCountry': 'India'})
        self.assertEqual(schema['geo']['latitude'], 22.56444)
        self.assertEqual(schema['maximumAttendeeCapacity'], 68000)
        self.assertNotIn('address', ground_schema('X', '/grounds/x/', 'd'))


if __name__ == '__main__':
    unittest.main()
