import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'tools'))
from profile_research import aggregate_rows, value, opposition_groups, yearly_chart, milestone_events


def batting(match, runs, balls, out=True, **extra):
    return {'date':'2001-01-01','match':match,'url':'/matches/'+match+'/','format':'ODI','opponent':'Australia','runs':runs,'balls':balls,'out':out,'position':1,'innings':1,**extra}


class ProfileResearchTests(unittest.TestCase):
    def test_unknown_ball_count_invalidates_whole_sample_strike_rate(self):
        total=aggregate_rows([batting('a',100,80),batting('b',25,None)])
        self.assertEqual(total['runs'],125)
        self.assertIsNone(total['balls'])
        self.assertIsNone(total['sr'])
        self.assertEqual(total['avg'],62.5)
        self.assertIn('—',value(total,'sr'))

    def test_notouts_and_zero_wickets_are_not_applicable(self):
        total=aggregate_rows([batting('a',80,60,False),{'match':'a','wickets':0,'legal':60,'conceded':30}])
        self.assertEqual(total['matches'],1)
        self.assertEqual(total['innings'],1)
        self.assertEqual(total['bowling_innings'],1)
        self.assertEqual(total['econ'],3)
        self.assertIn('N/A',value(total,'avg'))
        self.assertIn('N/A',value(total,'bowlSr'))

    def test_unknown_dismissal_does_not_become_notout(self):
        total=aggregate_rows([batting('a',80,60,None),batting('b',0,1)])
        self.assertIsNone(total['outs'])
        self.assertIsNone(total['avg'])
        self.assertIn('—',value(total,'avg'))

    def test_unknown_runs_do_not_become_zero(self):
        total=aggregate_rows([batting('a',None,30),batting('b',100,80)])
        self.assertEqual(total['innings'],2)
        self.assertIsNone(total['runs'])
        self.assertIsNone(total['avg'])
        self.assertIsNone(total['hundreds'])

    def test_qualification_keeps_formats_and_disciplines_separate(self):
        rows=[batting(str(i),50,40,format='ODI' if i<6 else 'Test') for i in range(12)]
        self.assertEqual(opposition_groups(rows),[])
        rows.extend(batting(str(i),50,40) for i in range(20,24))
        groups=opposition_groups(rows)
        self.assertEqual(len(groups),1)
        self.assertEqual(groups[0][0],'ODI')
        self.assertEqual(groups[0][3]['innings'],10)

    def test_chart_and_timeline_use_real_rows(self):
        rows=[batting('a',100,80),batting('b',110,100,date='2002-02-02')]
        chart=yearly_chart(rows,'ODI','runs','Player')
        self.assertIn('2001: 100 runs',chart)
        self.assertIn('2002: 110 runs',chart)
        for row,label in milestone_events(rows):
            self.assertIn(row['match'],('a','b'))
            self.assertNotIn('debut',label.lower())


if __name__=='__main__':
    unittest.main()
