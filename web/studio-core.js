/* Validated query contracts shared by Studio and its regression tests.
   One query can carry several measures; the primary measure orders the rows. */
(function(root){
 'use strict';
 const metrics={runs:'Runs',wickets:'Wickets',matches:'Matches',innings:'Innings',hundreds:'Centuries',fifties:'Fifties',fours:'Fours',sixes:'Sixes',highest:'Highest score',avg:'Batting average',sr:'Batting strike rate',bowlAvg:'Bowling average',econ:'Economy',bowlSr:'Bowling strike rate',five_w:'Five-wicket innings',catches:'Catches',stumpings:'Stumpings'};
 const units={avg:'runs per dismissal',sr:'runs per 100 balls',bowlAvg:'runs conceded per wicket',econ:'runs per 6 legal balls',bowlSr:'legal balls per wicket'};
 const allowed={careers:['matches','innings','runs','highest','avg','sr','hundreds','fifties','fours','sixes','wickets','bowlAvg','econ','bowlSr','five_w','catches','stumpings'],batting:['matches','innings','runs','highest','avg','sr','hundreds','fifties','fours','sixes'],bowling:['matches','innings','wickets','bowlAvg','econ','bowlSr','five_w'],matches:['matches']};
 const dimensions={careers:['player','teams','format','gender'],batting:['player','team','opponent','venue','year','format','position','innings_number'],bowling:['player','team','opponent','venue','year','format','innings_number'],matches:['year','format','venue','winner']};
 const lower=new Set(['bowlAvg','econ','bowlSr']);
 const quote=x=>"'"+String(x).replaceAll("'","''")+"'";
 const complete=k=>`CASE WHEN count(${k})=count(*) THEN sum(${k}) END`;
 const rate=(a,b,f=1)=>`trunc((${a}) * ${f}.0 / nullif((${b}),0),2)`;
 function expression(dataset,metric){
  if(!allowed[dataset]?.includes(metric))throw new Error('Choose a metric available for this dataset.');
  const career=dataset==='careers';
  if(metric==='matches')return career?complete('matches'):'count(DISTINCT match_id)';
  if(metric==='innings')return career?complete(dataset==='bowling'?'bowling_innings':'innings'):'count(*)';
  if(metric==='highest')return career?'max(highest)':'max(runs)';
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
 function measures(s){
  const list=String(s.metrics||'').split(',').map(x=>x.trim()).filter(Boolean);
  const chosen=(list.length?list:[s.metric]).filter((m,i,a)=>m&&a.indexOf(m)===i&&allowed[s.dataset]?.includes(m)).slice(0,8);
  if(!chosen.length)throw new Error('Choose at least one measure available for this dataset.');
  const primary=chosen.includes(s.metric)?s.metric:chosen[0];
  return {list:chosen,primary};
 }
 function idList(value){return String(value||'').split(',').map(x=>x.trim()).filter(Boolean).slice(0,12);}
 function sql(s,source){
  const {dataset,group}=s;
  if(!dimensions[dataset]?.includes(group))throw new Error('Choose a valid grouping.');
  const {list,primary}=measures(s);
  const min=Math.max(0,Math.min(100000,Number(s.minimum)||0)),limit=Math.max(1,Math.min(200,Number(s.limit)||10));
  if(s.from&&s.to&&Number(s.from)>Number(s.to))throw new Error('Start year must be no later than end year.');
  let where=' WHERE 1=1';
  for(const k of ['format','gender'])if(s[k])where+=` AND ${k}=${quote(s[k])}`;
  const players=idList(s.players);
  if(dataset!=='matches'){
   if(players.length)where+=` AND player_id IN (${players.map(quote).join(',')})`;
   else if(s.player)where+=s.template==='compare'&&s.compare?` AND player_id IN (${quote(s.player)},${quote(s.compare)})`:` AND player_id=${quote(s.player)}`;
   if(s.team)where+=dataset==='careers'?` AND list_contains(string_split(teams,' / '),${quote(s.team)})`:` AND team=${quote(s.team)}`;
  }else if(s.team)where+=` AND (team_1=${quote(s.team)} OR team_2=${quote(s.team)})`;
  if(dataset!=='careers'){
   for(const k of ['from','to'])if(s[k]){const n=Number(s[k]);if(!Number.isInteger(n)||n<1877||n>2100)throw new Error('Choose a valid year.');where+=` AND year${k==='from'?'>=':'<='}${n}`;}
   if(s.venue)where+=` AND venue=${quote(s.venue)}`;
   if(s.opponent&&dataset!=='matches')where+=` AND opponent=${quote(s.opponent)}`;
   if(s.position&&dataset==='batting')where+=` AND position=${Math.max(1,Math.min(11,Number(s.position)||1))}`;
   if(s.innings_number&&dataset!=='matches')where+=` AND innings_number=${Math.max(1,Math.min(4,Number(s.innings_number)||1))}`;
  }
  const sample=dataset==='careers'?complete('matches'):'count(DISTINCT match_id)';
  const grouping=group==='player'?'player_id,player':group;
  const direction=lower.has(primary)?'ASC':'DESC';
  const columns=list.map(m=>`${expression(dataset,m)} AS "m_${m}"`).join(', ');
  return `SELECT ${group} AS label, ${columns}, "m_${primary}" AS value, ${sample} AS sample FROM ${source}${where} GROUP BY ${grouping} HAVING sample>=${min} ORDER BY ${group==='year'?'label ASC':`value ${direction} NULLS LAST, label ASC`} LIMIT ${limit}`;
 }
 function clean(s){const next={};for(const [k,v] of Object.entries(s||{}))if(typeof v==='string'&&v.length<=600)next[k]=v;return next;}
 function normalizeRow(row){return Object.fromEntries(Object.entries({...row}).map(([key,value])=>{if(value==null)return [key,null];if(key==='label')return [key,typeof value==='bigint'?String(value):value];if(typeof value==='bigint')return [key,Number(value)];if(typeof value==='string'&&value.trim()!==''&&Number.isFinite(Number(value)))return [key,Number(value)];return [key,value];}));}
 const api={metrics,units,allowed,dimensions,lower,quote,expression,measures,idList,sql,clean,normalizeRow};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.CWStudio=api;
})(typeof window==='undefined'?this:window);
