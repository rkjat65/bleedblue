"""Execute the browser's generated SQL with DuckDB, including hostile text and incomplete records."""
import json, subprocess, unittest
from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parents[1]
class StudioQueries(unittest.TestCase):
    def query(self,state):
        code="const c=require('./web/studio-core.js');console.log(c.sql(JSON.parse(process.argv[1]),'sample'));"
        sql=subprocess.check_output(['node','-e',code,json.dumps(state)],cwd=ROOT,text=True).strip()
        con=duckdb.connect()
        con.execute('CREATE TABLE sample (player_id VARCHAR,player VARCHAR,gender VARCHAR,format VARCHAR,match_id VARCHAR,year INTEGER,runs INTEGER,balls INTEGER,"out" BOOLEAN,wickets INTEGER,legal INTEGER,conceded INTEGER,team VARCHAR,opponent VARCHAR,venue VARCHAR,position INTEGER)')
        con.execute("INSERT INTO sample VALUES ('a','Same Name','Women','ODI','1',2020,100,80,true,2,60,30,'India','England','Ground',1),('a','Same Name','Women','ODI','2',2021,25,NULL,true,0,60,20,'India','England','Ground',1),('b','Same Name','Women','ODI','3',2021,40,20,false,1,12,10,'India','England','Ground',2)")
        try:return con.execute(sql).fetchall()
        finally:con.close()
    def state(self,**kwargs):return dict(dataset='batting',metric='runs',group='player',gender='Women',limit='10',**kwargs)
    def test_identity_grouping(self):
        self.assertEqual([r[1] for r in self.query(self.state())],[125,40])
    def test_unknown_denominator(self):
        s=self.state(player='a');s['metric']='sr';self.assertIsNone(self.query(s)[0][1])
    def test_quote_and_injection(self):
        self.assertEqual(self.query(self.state(opponent="England' OR 1=1 --")),[])
    def test_year_filter(self):
        result=self.query(self.state(player='a',from_='2021')|{'from':'2021'})
        self.assertEqual(result[0][1],25)
    def test_bowling_average(self):
        s=self.state(player='a');s.update(dataset='bowling',metric='bowlAvg');self.assertEqual(self.query(s)[0][1],25)
    def test_minimum_matches(self):
        self.assertEqual(len(self.query(self.state(minimum='2'))),1)
    def test_arrow_numeric_results(self):
        code="const c=require('./web/studio-core.js');console.log(JSON.stringify([c.normalizeRow({label:'2021',value:'18426',sample:463n}),c.normalizeRow({label:'Unknown',value:null,sample:'0'})]));"
        rows=json.loads(subprocess.check_output(['node','-e',code],cwd=ROOT,text=True))
        self.assertEqual(rows,[{'label':'2021','value':18426,'sample':463},{'label':'Unknown','value':None,'sample':0}])
if __name__=='__main__':unittest.main()
