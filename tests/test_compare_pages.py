"""Comparison pages mark the best figure honestly and keep formats separate."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
from compare_pages import best_index, compare_body, compare_table, faq_items, opposition_table


def player(pid, name, **career):
    return {'id': pid, 'name': name, 'teams': ['India'], 'gender': 'Men', 'career': career}


def bat(pid, match, runs, opponent, out=True, year='2020'):
    return {'date': f'{year}-01-01', 'match': match, 'url': '/m/', 'format': 'ODI', 'opponent': opponent, 'venue': 'G', 'setting': 'Home', 'result': 'Won', 'innings': 1,
            'position': 3, 'runs': runs, 'balls': 40, 'out': out, 'fours': 2, 'sixes': 0, 'dismissal': None, 'wickets': None, 'legal': None, 'conceded': None}


class BestTests(unittest.TestCase):
    def test_higher_and_lower_is_better(self):
        self.assertEqual(best_index([10, 20, None], 'runs'), {1})
        self.assertEqual(best_index([25.0, 22.5, 30.0], 'bowlAvg'), {1})
        self.assertEqual(best_index([7, 7, 3], 'hundreds'), {0, 1})
        self.assertEqual(best_index([5, None], 'runs'), set())

    def test_table_marks_best_per_row(self):
        a = {'runs': 1000, 'avg': 40.0}
        b = {'runs': 900, 'avg': 55.5}
        markup = compare_table([player('a', 'A One'), player('b', 'B Two')], [a, b], [('runs', 'Runs'), ('avg', 'Average'), ('sixes', 'Sixes')], 'Caption')
        self.assertIn('<span class="cmp-best">1,000</span>', markup)
        self.assertIn('<span class="cmp-best">55.50</span>', markup)
        self.assertNotIn('Sixes', markup)


class BodyTests(unittest.TestCase):
    def test_body_has_overview_and_format_panels(self):
        a = player('a', 'A One', ODI={'matches': 10, 'innings': 10, 'runs': 500, 'avg': 50.0, 'sr': 90.0, 'hundreds': 2, 'fifties': 1, 'wickets': 0, 'span': '2019-2021'}, Test={'matches': 3, 'innings': 5, 'runs': 100, 'avg': 20.0})
        b = player('b', 'B Two', ODI={'matches': 12, 'innings': 12, 'runs': 450, 'avg': 45.0, 'sr': 100.0, 'hundreds': 1, 'fifties': 3, 'wickets': 0, 'span': '2018-2021'})
        rows = {'a': [bat('a', str(i), 50, 'Australia', year=str(2019 + i % 3)) for i in range(6)], 'b': [bat('b', 'x' + str(i), 40, 'Australia', year=str(2018 + i % 3)) for i in range(6)]}
        body, faq, description = compare_body([a, b], rows, {'a': '/players/a/', 'b': '/players/b/'}, {}, {})
        self.assertEqual(body.count('<h1'), 1)
        self.assertIn('<h1>A One vs B Two</h1>', body)
        self.assertIn('data-fmt-panel="overview"', body)
        self.assertIn('data-fmt-panel="odi"', body)
        self.assertIn('data-fmt-panel="test"', body)
        self.assertIn('B Two did not play Tests', body)
        self.assertIn('runs in each year', body)
        self.assertIn('ODI batting average by opponent', body)
        self.assertTrue(any('ODI runs' in q for q, _ in faq))
        self.assertNotIn('—', re.sub(r'<[^>]+>', '', body))
        self.assertLessEqual(len(description), 158)

    def test_body_survives_null_career_fields(self):
        a = player('a', 'A One', ODI={'matches': 10, 'innings': 10, 'runs': 500, 'avg': 50.0, 'sr': 90.0, 'hundreds': 2, 'fifties': 1, 'wickets': None})
        b = player('b', 'B Two', ODI={'matches': 12, 'innings': 12, 'runs': 450, 'avg': None, 'sr': None, 'hundreds': None, 'fifties': None, 'wickets': None, 'bowlAvg': None})
        body, faq, description = compare_body([a, b], {'a': [], 'b': []}, {'a': '/players/a/', 'b': '/players/b/'}, {}, {})
        self.assertIn('data-fmt-panel="odi"', body)
        self.assertNotIn('Wickets', body)

    def test_opposition_table_requires_three_innings(self):
        a = player('a', 'A One'); b = player('b', 'B Two')
        rows_a = [bat('a', str(i), 60, 'England') for i in range(3)] + [bat('a', 'z', 10, 'Pakistan')]
        rows_b = [bat('b', 'y' + str(i), 30, 'England') for i in range(3)]
        markup = opposition_table([a, b], [rows_a, rows_b], 'ODI')
        self.assertIn('England', markup)
        self.assertNotIn('Pakistan', markup)
        self.assertIn('cmp-best', markup)


if __name__ == '__main__':
    unittest.main()
