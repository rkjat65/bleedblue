"""Publication boundaries and historical-denominator regressions."""
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'tools'))
from cricket_scope import publication_data,load_cards,complete_career_counts,FULL_MEMBERS
from backfill_free_data import normalize_card
from build_site import rate,stat_value
from import_careers import CLASSES,parse_page


class ScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive,cls.careers,cls.history=publication_data(ROOT)
        cls.people={p['id']:{**p,'career':{}} for p in cls.archive['players']}
        for p in cls.careers['players']:cls.people.setdefault(p['id'],{}).update(espn_id=p['espn_id'],career=p['formats'])
        cls.cards=load_cards(ROOT,cls.archive['matches']+cls.history['matches'],cls.people)

    def test_only_full_member_recognized_matches(self):
        official=json.loads((ROOT/'data/official_match_registry.json').read_text(encoding='utf8'))['matches']
        for m in self.archive['matches']+self.history['matches']:
            self.assertTrue(set(m['teams'])<=FULL_MEMBERS)
            self.assertEqual(CLASSES[official[m['id']]],(m['format'],m['gender']))

    def test_representative_team_does_not_hide_national_career(self):
        rashid=next(p for p in self.careers['players'] if p['espn_id']=='793463')
        self.assertIn('Afghanistan',rashid['teams'])
        original=next(p for p in json.loads((ROOT/'data/careers.json').read_text(encoding='utf8'))['players'] if p['id']==rashid['id'])
        self.assertEqual(original['formats']['T20I']['wickets'],rashid['formats']['T20I']['wickets'])

    def test_unrelated_register_alias_cannot_mix_gender_or_career(self):
        player=next(p for p in self.careers['players'] if p['espn_id']=='430391')
        self.assertEqual(player['gender'],'Women')
        self.assertEqual(player['formats']['ODI']['matches'],11)
        self.assertEqual(player['formats']['T20I']['runs'],3)
        self.assertEqual(player['teams'],['Sri Lanka'])

    def test_verified_career_denominators(self):
        sachin=next(p for p in self.careers['players'] if p['espn_id']=='35320')['formats']['Test']
        self.assertEqual((sachin['runs'],sachin['balls'],sachin['sr']),(15921,29437,54.08))
        kohli=next(p for p in self.careers['players'] if p['espn_id']=='253802')['formats']['Test']
        self.assertEqual((kohli['balls'],kohli['sr']),(16608,55.57))

    def test_all_recovered_innings_reconcile(self):
        for mid,card in self.cards.items():
            for inn in card['innings']:
                if inn['runs'] is not None and inn['extras'] is not None and all(b['runs'] is not None for b in inn['batting']):
                    self.assertEqual(sum(b['runs'] for b in inn['batting'])+inn['extras'],inn['runs'],mid)
                for b in inn['bowling']:
                    if b.get('maidens') is not None and b.get('balls') is not None:
                        self.assertLessEqual(b['maidens'],b['balls']//inn.get('balls_per_over',6),mid)

    def test_unknown_denominator_is_not_zero(self):
        self.assertIsNone(rate(100,None,100))
        self.assertIsNone(rate(100,0,100))
        self.assertIn('N/A',stat_value({'avg':None,'outs':0},'avg'))
        self.assertNotIn('N/A',stat_value({'sr':None,'balls':None},'sr'))

    def test_partial_innings_cannot_fill_career_balls(self):
        p={'p':{'career':{'Test':{'innings':2,'runs':30,'outs':1,'balls':None,'sr':None}}}}
        card={'m':{'match':{'format':'Test'},'innings':[{'batting':[{'id':'p','runs':30,'balls':50,'out':True}]}]}}
        complete_career_counts(card,p)
        self.assertIsNone(p['p']['career']['Test']['sr'])
        card['m']['innings'][0]['batting']=[{'id':'p','runs':20,'balls':30,'out':True},{'id':'p','runs':10,'balls':20,'out':False}]
        complete_career_counts(card,p)
        self.assertEqual(p['p']['career']['Test']['sr'],60)

    def test_structured_scorecard_rejects_unofficial_class(self):
        body=b'<script id="__NEXT_DATA__">'+json.dumps({'props':{'appPageProps':{'data':{'match':{'objectId':1,'internationalClassId':None},'content':{}}}}}).encode()+b'</script>'
        with self.assertRaisesRegex(ValueError,'official'):normalize_card(body,{'id':'1','format':'Test','gender':'Men'})

    def test_parenthesized_identity_suffix_is_not_a_country(self):
        body=b'<table class="engineTable"><caption>Overall figures</caption><thead><th>Player</th><th>Mat</th></thead><tr class="data1"><td><a href="/ci/engine/player/1059030.html">Abdul Malik (1)</a> (AFG)</td><td>2</td></tr></table>'
        self.assertEqual(parse_page(body,'https://stats.cricinfo.com/')['rows'][0]['team_codes'],['AFG'])


if __name__=='__main__':unittest.main()
