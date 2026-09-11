"""Named-player question URLs reuse official career figures only."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'tools'))
sys.path.insert(0, str(ROOT))
from player_profile import question_specs
from player_questions import prepare_player_questions, select_question_players, question_page
from test_player_profile import KOHLI, BUMRAH, MANDHANA


class PlayerQuestionTests(unittest.TestCase):
    def test_kohli_odi_runs_slug_and_number(self):
        specs = {s['slug']: s for s in question_specs(KOHLI, name_slug='virat-kohli')}
        spec = specs['how-many-odi-runs-has-virat-kohli-scored']
        self.assertTrue(spec['publishable'])
        self.assertIn('14,941', spec['answer'])
        self.assertIn('14,941', spec['hero'])
        self.assertEqual(spec['title'], 'How many ODI runs has Virat Kohli scored?')

    def test_kohli_average_question(self):
        specs = {s['slug']: s for s in question_specs(KOHLI, name_slug='virat-kohli')}
        spec = specs['what-is-virat-kohli-odi-batting-average']
        self.assertIn('58.59', spec['answer'])
        self.assertTrue(spec['publishable'])

    def test_thin_innings_are_not_publishable(self):
        player = {
            'name': 'Brief Batter',
            'gender': 'Men',
            'teams': ['India'],
            'career': {'ODI': {'matches': 2, 'innings': 2, 'runs': 40, 'avg': 20.0, 'wickets': 0}},
        }
        specs = question_specs(player, name_slug='brief-batter')
        runs = next(s for s in specs if s['kind'] == 'runs')
        self.assertFalse(runs['publishable'])
        people = {'x': {**player, 'id': 'x'}}
        self.assertEqual(select_question_players(people), set())

    def test_featured_name_is_selected_even_if_short(self):
        player = {
            'name': 'Smriti Mandhana',
            'gender': 'Women',
            'teams': ['India'],
            'career': {'ODI': {'matches': 10, 'innings': 10, 'runs': 400, 'avg': 40.0, 'wickets': 0, 'hundreds': 1}},
        }
        people = {'m': player}
        self.assertIn('m', select_question_players(people, featured_names={'Smriti Mandhana'}))

    def test_prepare_assigns_unique_urls_and_pages_keep_numbers(self):
        people = {
            'k': {**KOHLI, 'id': 'k'},
            'b': {**BUMRAH, 'id': 'b'},
            's': {**MANDHANA, 'id': 's'},
        }
        paths = {'k': '/players/virat-kohli/', 'b': '/players/jasprit-bumrah/', 's': '/players/s-mandhana/'}
        bundle = prepare_player_questions(people, paths, featured_names={'Virat Kohli', 'Jasprit Bumrah', 'Smriti Mandhana'})
        kohli = {s['slug']: s for s in bundle['k']['specs']}
        self.assertIn('how-many-odi-runs-has-virat-kohli-scored', kohli)
        self.assertEqual(kohli['how-many-odi-runs-has-virat-kohli-scored']['url'], '/questions/how-many-odi-runs-has-virat-kohli-scored/')
        bumrah = {s['slug']: s for s in bundle['b']['specs']}
        self.assertIn('how-many-test-wickets-has-jasprit-bumrah-taken', bumrah)
        page = question_page(kohli['how-many-odi-runs-has-virat-kohli-scored'], KOHLI, bundle['k']['specs'][1:], '2026-09-07')
        self.assertIn('14,941', page)
        self.assertIn('/players/virat-kohli/', page)
        self.assertNotIn('\u2014', page)
        self.assertNotIn('\u2013', page)
        titles = [s['title'] for pack in bundle.values() for s in pack['specs']]
        self.assertEqual(len(titles), len(set(titles)))

    def test_womens_description_mentions_women(self):
        specs = {s['kind'] + (s.get('format') or ''): s for s in question_specs(MANDHANA, name_slug='s-mandhana')}
        self.assertIn("women's", specs['runsODI']['answer'])


if __name__ == '__main__':
    unittest.main()
