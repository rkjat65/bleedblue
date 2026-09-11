"""Player profile copy, tables and pictures stay factual and crawlable."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
import cricket_charts as cw
from player_profile import (
    career_glance, career_tables, clip_meta, player_faq, player_intro, player_seo, primary_role,
)


KOHLI = {
    'name': 'Virat Kohli',
    'gender': 'Men',
    'teams': ['India'],
    'first': '2008',
    'last': '2026',
    'career': {
        'Test': {'matches': 123, 'innings': 210, 'runs': 9230, 'avg': 46.85, 'sr': 55.57, 'hundreds': 30, 'fifties': 31, 'highest_display': '254*', 'wickets': 0, 'bowlAvg': None, 'econ': 2.88, 'notouts': 13, 'balls': 16608, 'ducks': 15, 'fours': 1027, 'sixes': 30, 'bowling_innings': 11, 'legal': 175, 'maidens': 2, 'conceded': 84, 'best_bowling': '-', 'best_match': '-', 'four_w': 0, 'five_w': 0, 'ten_w': 0, 'catches': 121, 'stumpings': 0, 'fielding_innings': 236, 'dismissals': 121, 'dismissals_per_innings': 0.512, 'most_dismissals': '3 (3ct 0st)', 'span': '2011-2025'},
        'ODI': {'matches': 314, 'innings': 302, 'runs': 14941, 'avg': 58.59, 'sr': 93.95, 'hundreds': 54, 'fifties': 79, 'highest_display': '183', 'wickets': 5, 'bowlAvg': 136.0, 'econ': 6.16, 'notouts': 47, 'balls': 15903, 'ducks': 18, 'fours': 1389, 'sixes': 171, 'bowling_innings': 50, 'legal': 662, 'maidens': 1, 'conceded': 680, 'best_bowling': '1/13', 'best_match': '1/13', 'four_w': 0, 'five_w': 0, 'ten_w': None, 'catches': 169, 'stumpings': 0, 'fielding_innings': 311, 'dismissals': 169, 'dismissals_per_innings': 0.543, 'most_dismissals': '3 (3ct 0st)', 'span': '2008-2026'},
        'T20I': {'matches': 125, 'innings': 117, 'runs': 4188, 'avg': 48.69, 'sr': 137.04, 'hundreds': 1, 'fifties': 38, 'highest_display': '122*', 'wickets': 4, 'bowlAvg': 51.0, 'econ': 8.05, 'notouts': 31, 'balls': 3056, 'ducks': 7, 'fours': 369, 'sixes': 124, 'bowling_innings': 13, 'legal': 152, 'maidens': 0, 'conceded': 204, 'best_bowling': '1/13', 'best_match': '1/13', 'four_w': 0, 'five_w': 0, 'ten_w': None, 'catches': 54, 'stumpings': 0, 'fielding_innings': 124, 'dismissals': 54, 'dismissals_per_innings': 0.435, 'most_dismissals': '3 (3ct 0st)', 'span': '2010-2024'},
    },
}

BUMRAH = {
    'name': 'Jasprit Bumrah',
    'gender': 'Men',
    'teams': ['India'],
    'first': '2016',
    'last': '2025',
    'career': {
        'Test': {'matches': 40, 'innings': 20, 'runs': 200, 'avg': 8.0, 'sr': 40.0, 'hundreds': 0, 'wickets': 180, 'bowlAvg': 20.5, 'econ': 2.7, 'bowlSr': 45.0, 'best_bowling': '6/27', 'five_w': 12, 'bowling_innings': 75, 'legal': 8000, 'matches': 40},
        'ODI': {'matches': 80, 'innings': 30, 'runs': 50, 'avg': 5.0, 'sr': 70.0, 'hundreds': 0, 'wickets': 130, 'bowlAvg': 24.0, 'econ': 4.6, 'best_bowling': '6/19', 'five_w': 2, 'bowling_innings': 80, 'legal': 4000},
    },
}

MANDHANA = {
    'name': 'Smriti Mandhana',
    'gender': 'Women',
    'teams': ['India'],
    'first': '2013',
    'last': '2026',
    'career': {
        'ODI': {'matches': 90, 'innings': 90, 'runs': 4000, 'avg': 45.0, 'sr': 90.0, 'hundreds': 8, 'highest_display': '135', 'wickets': 0},
        'T20I': {'matches': 140, 'innings': 135, 'runs': 3500, 'avg': 30.0, 'sr': 120.0, 'hundreds': 0, 'highest_display': '87', 'wickets': 0},
    },
}


def stat_value(stats, key):
    value = stats.get(key)
    if value is None:
        return 'N/A'
    return f'{value:,}' if isinstance(value, int) else str(value)


def table(headings, rows, ident='', caption=''):
    head = ''.join(f'<th>{h}</th>' for h in headings)
    body = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>' for row in rows)
    return f'<table id="{ident}"><caption>{caption}</caption><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


class PlayerProfileTests(unittest.TestCase):
    def test_kohli_seo_uses_real_odi_runs(self):
        title, description = player_seo(KOHLI)
        self.assertIn('Virat Kohli stats', title)
        self.assertIn('14,941', description)
        self.assertIn('9,230', description)
        self.assertIn('4,188', description)
        self.assertNotIn("women's", title)
        self.assertLessEqual(len(description), 160)

    def test_bowler_seo_leads_with_wickets(self):
        title, description = player_seo(BUMRAH)
        self.assertIn('180 Test wickets', description)
        self.assertIn('130 ODI wickets', description)
        self.assertEqual(primary_role(BUMRAH['career']), 'bowler')

    def test_womens_player_is_labelled(self):
        title, description = player_seo(MANDHANA)
        self.assertIn("women's", title)
        self.assertIn("women's internationals", description)
        self.assertIn('4,000', description)

    def test_copy_has_no_em_or_en_dash(self):
        for player in (KOHLI, BUMRAH, MANDHANA):
            title, description = player_seo(player)
            intro = player_intro(player)
            faq_html, schema = player_faq(player)
            for text in (title, description, intro, faq_html, str(schema)):
                self.assertNotIn('\u2014', text, text)
                self.assertNotIn('\u2013', text, text)

    def test_empty_career_does_not_invent_numbers(self):
        player = {'name': 'Unknown Player', 'gender': 'Men', 'teams': ['India'], 'career': {}}
        title, description = player_seo(player)
        self.assertNotRegex(description, r'\d{3,}')
        html, _schema = player_faq(player)
        if html:
            self.assertNotRegex(html, r'\d{3,}')
        self.assertEqual(career_glance(player, stat_value), '')

    def test_tables_are_html_not_cramped_grids(self):
        markup = career_tables(KOHLI, table, stat_value)
        self.assertIn('<table', markup)
        self.assertIn('Batting career records by format', markup)
        self.assertIn('Bowling career records by format', markup)
        self.assertIn('14,941', markup)
        self.assertNotIn('career-stat-grid', markup)
        self.assertIn('ODI', markup)
        self.assertIn('Test', markup)

    def test_glance_cards_lead_with_format_heroes(self):
        markup = career_glance(KOHLI, stat_value)
        self.assertIn('id="career-glance"', markup)
        self.assertIn('14,941', markup)
        self.assertIn('format-card', markup)
        self.assertIn('Virat Kohli: Test, ODI and T20I stats', markup)

    def test_faq_answers_match_career_numbers(self):
        html, schema = player_faq(KOHLI)
        self.assertIn('How many ODI runs has Virat Kohli scored?', html)
        self.assertIn('14,941', html)
        self.assertEqual(schema['@type'], 'FAQPage')
        odi = next(q for q in schema['mainEntity'] if 'ODI runs' in q['name'])
        self.assertIn('14,941', odi['acceptedAnswer']['text'])
        self.assertLessEqual(len(schema['mainEntity']), 6)

    def test_official_charts_use_career_not_archive(self):
        chart = cw.career_lab(KOHLI['career'], 'Virat Kohli')
        self.assertIn('official career runs by format', chart)
        self.assertIn('14,941', chart)
        self.assertIn('9,230', chart)
        self.assertIn('id="official-pictures"', chart)
        self.assertNotIn('official career wickets by format', chart)
        self.assertEqual(cw.career_lab({}, 'Nobody'), '')
        bowler = cw.career_lab(BUMRAH['career'], 'Jasprit Bumrah')
        self.assertIn('official career wickets by format', bowler)

    def test_clip_meta_does_not_split_words(self):
        self.assertEqual(clip_meta('Short text'), 'Short text')
        self.assertTrue(clip_meta('word ' * 80).endswith('.'))
        self.assertLessEqual(len(clip_meta('word ' * 80)), 160)
        clipped = clip_meta('Virat Kohli has 9,230 Test runs at 46.85, 14,941 ODI runs at 58.59 and 4,188 T20I runs at 48.69. Official Test, ODI and T20I tables, career pictures and scorecard analysis on Cricket Wicket.')
        self.assertTrue(clipped.endswith('48.69.'))
        self.assertFalse(clipped.endswith(' and.'))


if __name__ == '__main__':
    unittest.main()
