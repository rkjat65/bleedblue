import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from on_this_day import build_catalog, calendar_keys, content, day_path, focus_players


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.today = date(2026, 9, 15)
        self.people = {'a': {'name': 'India Batter', 'teams': ['India']}, 'b': {'name': 'Opponent', 'teams': ['Australia']}}
        self.roster = {'valid_until': '2026-09-30', 'names': ['India Batter']}
        self.match = {'id': '1', 'date': '2015-09-15', 'format': 'ODI', 'gender': 'Women', 'teams': ['India', 'Australia'], 'venue': 'Ground', 'outcome': {'winner': 'India', 'by': {'runs': 20}}, 'player_ids': ['a', 'b'], 'totals': []}
        self.card = {'innings': [{'team': 'India', 'batting': [{'id':'a','runs':105,'balls':100,'out':False}], 'bowling':[{'id':'b','wickets':5,'runs':40}]}]}

    def build(self, matches=None, card=None):
        return build_catalog(matches or [self.match], {'1': card or self.card}, self.people, {'a':'/players/a/'}, {'1':'/matches/1/'}, self.roster, self.today)

    def test_india_current_players_priority_and_notouts(self):
        entries=self.build()['09-15']
        self.assertEqual(entries[0]['metric'], '105*')
        self.assertTrue(entries[0]['current'])
        self.assertEqual(entries[0]['gender'], 'Women')
        opponent=next(x for x in entries if x['kind']=='bowling')
        self.assertFalse(opponent['india'])
        self.assertFalse(opponent['current'])

    def test_test_performance_not_assigned_to_start_day(self):
        entries=self.build([{**self.match,'format':'Test'}])['09-15']
        self.assertEqual(len(entries),1)
        self.assertEqual(entries[0]['kind'],'match')
        self.assertIn('Test began',entries[0]['title'])
        self.assertEqual(entries[0]['metric'],'TEST')

    def test_future_and_duplicate_matches_excluded(self):
        entries=self.build([self.match,self.match])['09-15']
        self.assertEqual(len(entries),len(self.build()['09-15']))
        self.assertFalse(self.build([{**self.match,'date':'2026-09-15'}])['09-15'])

    def test_no_false_figures_or_superovers(self):
        c={'innings':[{'team':'India','batting':[{'id':'a','runs':None}], 'bowling':[]}, {**self.card['innings'][0], 'super_over':True}]}
        self.assertEqual(len(self.build(card=c)['09-15']),1)

    def test_calendar_and_escaping(self):
        self.assertEqual(len(calendar_keys()),366)
        self.assertEqual(day_path('02-29'),'/on-this-day/february-29/')
        with self.assertRaises(ValueError): day_path('02-30')
        entries=self.build()['09-15']; entries[0]['title']='<script>alert(1)</script>'
        markup=content('09-15',entries,'/assets/card.png')
        self.assertNotIn('<script>',markup)
        self.assertIn('href="/matches/1/"',markup)

    def test_expired_roster_uses_recent_india_only(self):
        roster={**self.roster,'valid_until':'2025-09-30'}
        self.assertFalse(focus_players(self.people,[self.match],roster,self.today))
        self.assertEqual(focus_players(self.people,[{**self.match,'date':'2026-09-01'}],roster,self.today),{'a'})

if __name__ == '__main__': unittest.main()
