/* Validated query contracts shared by Studio and its regression tests. */
(function(root){
 'use strict';
 const metrics={runs:'Runs',wickets:'Wickets',matches:'Matches',hundreds:'Centuries',fifties:'Fifties',fours:'Fours',sixes:'Sixes',avg:'Batting average',sr:'Batting strike rate',bowlAvg:'Bowling average',econ:'Economy',bowlSr:'Bowling strike rate',five_w:'Five-wicket innings'};
 const allowed={careers:Object.keys(metrics),batting:['runs','matches','hundreds','fifties','fours','sixes','avg','sr'],bowling:['wickets','matches','bowlAvg','econ','bowlSr','five_w'],matches:['matches']};
 const dimensions={careers:['player','teams','format','gender'],batting:['player','team','opponent','venue','year','format','position'],bowling:['player','team','opponent','venue','year','format'],matches:['year','format','venue','winner']};
 const quote=x=>"'"+String(x).replaceAll("'","''")+"'";
 const complete=k=>`CASE WHEN count(${k})=count(*) THEN sum(${k}) END`;
 const rate=(a,b,f=1)=>`trunc((${a}) * ${f}.0 / nullif((${b}),0),2)`;
 function expression(dataset,metric){
  if(!allowed[dataset]?.includes(metric))throw new Error('Choose a metric available for this dataset.');
  const career=dataset==='careers';
  if(metric==='matches')return career?complete('matches'):'count(DISTINCT match_id)';
  if(metric==='avg')return rate(complete('runs'),career?complete('outs'):complete('CAST("out" AS INTEGER)'));
  if(metric==='sr')return rate(complete('runs'),complete('balls'),100);
  if(metric==='bowlAvg')return rate(complete('conceded'),complete('wickets'));
  if(metric==='econ')return rate(complete('conceded'),complete('legal'),6);
  if(metric==='bowlSr')return rate(complete('legal'),complete('wickets'));
  if(!career&&['hundreds','fifties','five_w'].includes(metric)){
   const field=metric==='five_w'?'wickets':'runs',test=metric==='hundreds'?'runs>=100':metric==='fifties'?'runs>=50 AND runs<100':'wickets>=5';
   return `CASE WHEN count(${field})=count(*) THEN sum(CASE WHEN ${test} THEN 1 ELSE 0 END) END`;
  }
  return complete(metric);
 }
 function sql(s,source){
  const {dataset,metric,group}=s;
  if(!dimensions[dataset]?.includes(group))throw new Error('Choose a valid grouping.');
  const min=Math.max(0,Math.min(100000,Number(s.minimum)||0)),limit=Math.max(1,Math.min(100,Number(s.limit)||10));
  if(s.from&&s.to&&Number(s.from)>Number(s.to))throw new Error('Start year must be no later than end year.');
  let where=' WHERE 1=1';
  for(const k of ['format','gender'])if(s[k])where+=` AND ${k}=${quote(s[k])}`;
  if(dataset!=='matches'){
   if(s.player)where+=s.template==='compare'?` AND player_id IN (${quote(s.player)},${quote(s.compare)})`:` AND player_id=${quote(s.player)}`;
   if(s.team)where+=dataset==='careers'?` AND list_contains(string_split(teams,' / '),${quote(s.team)})`:` AND team=${quote(s.team)}`;
  }else if(s.team)where+=` AND (team_1=${quote(s.team)} OR team_2=${quote(s.team)})`;
  if(dataset!=='careers'){
   for(const k of ['from','to'])if(s[k]){const n=Number(s[k]);if(!Number.isInteger(n)||n<1877||n>2100)throw new Error('Choose a valid year.');where+=` AND year${k==='from'?'>=':'<='}${n}`;}
   if(s.venue)where+=` AND venue=${quote(s.venue)}`;
   if(s.opponent&&dataset!=='matches')where+=` AND opponent=${quote(s.opponent)}`;
   if(s.position&&dataset==='batting')where+=` AND position=${Math.max(1,Math.min(11,Number(s.position)||1))}`;
  }
  const sample=dataset==='careers'?complete('matches'):'count(DISTINCT match_id)';
  const grouping=group==='player'?'player_id,player':group;
  const direction=['bowlAvg','econ','bowlSr'].includes(metric)?'ASC':'DESC';
  return `SELECT ${group} AS label, ${expression(dataset,metric)} AS value, ${sample} AS sample FROM ${source}${where} GROUP BY ${grouping} HAVING sample>=${min} ORDER BY ${group==='year'?'label ASC':`value ${direction} NULLS LAST, label ASC`} LIMIT ${limit}`;
 }
 function clean(s){const next={};for(const [k,v] of Object.entries(s||{}))if(typeof v==='string'&&v.length<=300)next[k]=v;return next;}
 function normalizeRow(row){return Object.fromEntries(Object.entries({...row}).map(([key,value])=>[key,value==null?null:['value','sample'].includes(key)?Number(value):typeof value==='bigint'?Number(value):value]));}
 const api={metrics,allowed,dimensions,quote,expression,sql,clean,normalizeRow};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.CWStudio=api;
})(typeof window==='undefined'?this:window);
