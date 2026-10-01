"""Series editions: splitting, labels, series scores and tournament lines."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
import series_pages as sp


def match(i, date, fmt, teams, winner, gender='Men'):
    return {'id': str(i), 'date': date, 'format': fmt, 'gender': gender, 'teams': teams, 'venue': 'Ground', 'outcome': {'winner': winner} if winner else {}}


class SeriesTests(unittest.TestCase):
    def test_a_long_gap_starts_a_new_edition(self):
        ms = [match(1, '2023-01-05', 'ODI', ['India', 'Sri Lanka'], 'India'), match(2, '2023-01-10', 'ODI', ['India', 'Sri Lanka'], 'India'),
              match(3, '2024-08-02', 'ODI', ['India', 'Sri Lanka'], 'Sri Lanka')]
        eds = sp.build_editions({'Sri Lanka v India': ms}, {'Sri Lanka v India': '/series/sl-ind/'})
        self.assertEqual([e['path'] for e in eds], ['/series/sl-ind/2024/', '/series/sl-ind/2023/'])
        self.assertEqual(sp.summary(eds[1]), 'India won 2-0')

    def test_series_score_names_draws_and_formats(self):
        ms = [match(1, '2025-06-20', 'Test', ['England', 'India'], 'England'), match(2, '2025-07-02', 'Test', ['England', 'India'], 'India'),
              match(3, '2025-07-10', 'Test', ['England', 'India'], None), match(4, '2025-07-20', 'ODI', ['England', 'India'], 'India')]
        ed = sp.build_editions({'India tour of England': ms}, {'India tour of England': '/series/x/'})[0]
        self.assertEqual(sp.summary(ed), 'Tests: Series drawn 1-1 (1 drawn or no result) · ODIs: India won 1-0')

    def test_women_edition_of_a_shared_event_is_labelled(self):
        ms = [match(1, '2009-06-10', 'T20I', ['England', 'India'], 'England'), match(2, '2009-06-11', 'T20I', ['England', 'India'], 'India', 'Women')]
        eds = sp.build_editions({'ICC World Twenty20': ms}, {'ICC World Twenty20': '/series/wt20/'})
        self.assertEqual(sorted(e['title'] for e in eds), ['ICC World Twenty20 2009', 'ICC World Twenty20 2009 (women)'])
        self.assertEqual(len({e['path'] for e in eds}), 2)

    def test_tournament_line_and_standings(self):
        ms = [match(1, '2024-06-01', 'T20I', ['India', 'Pakistan'], 'India'), match(2, '2024-06-03', 'T20I', ['India', 'USA'], 'India'),
              match(3, '2024-06-29', 'T20I', ['India', 'South Africa'], 'India')]
        ed = sp.build_editions({'T20 World Cup': ms}, {'T20 World Cup': '/series/t20wc/'})[0]
        self.assertEqual(sp.summary(ed), '4 teams · last match: India beat South Africa')
        self.assertEqual(sp.standings(ms)[0], ('India', [3, 3, 0, 0]))


if __name__ == '__main__':
    unittest.main()
