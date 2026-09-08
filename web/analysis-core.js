/* Shared cricket calculations: unknown inputs stay unknown. Works in Node and the browser. */
(function(root){
 'use strict';
 const sum=(rows,key)=>rows.every(r=>r[key]!=null)?rows.reduce((n,r)=>n+Number(r[key]),0):null;
 const rate=(a,b,f=1)=>a!=null&&b!=null&&b>0?Math.floor((a*f/b+Number.EPSILON)*100)/100:null;
 const bat=r=>r.position!=null||r.runs!=null||r.balls!=null;
 const bowl=r=>r.wickets!=null||r.legal!=null||r.conceded!=null;
 function aggregate(rows){
  const b=rows.filter(bat),w=rows.filter(bowl),s={matches:new Set(rows.map(r=>r.match)).size,innings:b.length,bowling_innings:w.length};
  for(const k of ['runs','balls','fours','sixes'])s[k]=sum(b,k);
  for(const k of ['wickets','legal','conceded'])s[k]=sum(w,k);
  s.outs=b.every(r=>r.out!=null)?b.filter(r=>r.out).length:null;
  s.notouts=s.outs==null?null:b.length-s.outs;
  for(const [key,predicate] of [['hundreds',r=>r.runs>=100],['fifties',r=>r.runs>=50&&r.runs<100],['ducks',r=>r.runs===0]])s[key]=b.every(r=>r.runs!=null)?b.filter(predicate).length:null;
  s.five_w=w.every(r=>r.wickets!=null)?w.filter(r=>r.wickets>=5).length:null;
  s.avg=rate(s.runs,s.outs);s.sr=rate(s.runs,s.balls,100);s.bowlAvg=rate(s.conceded,s.wickets);s.bowlSr=rate(s.legal,s.wickets);s.econ=rate(s.conceded,s.legal,6);
  return s;
 }
 function select(rows,f={}){
  let r=rows.filter(r=>['format','opponent','venue','setting','innings','position','result'].every(k=>!f[k]||String(r[k])===String(f[k]))&&(!f.year||r.date.slice(0,4)===f.year)&&(!f.from||Number(r.date.slice(0,4))>=Number(f.from))&&(!f.to||Number(r.date.slice(0,4))<=Number(f.to)));
  r.sort((a,b)=>a.date.localeCompare(b.date)||String(a.match).localeCompare(String(b.match))||(a.innings||0)-(b.innings||0));
  const recent=Number(f.recent)||0;
  // Last N batting innings selects the same match/innings bowling contributions.
  if(recent){const keys=new Set(r.filter(bat).slice(-recent).map(x=>x.match+':'+x.innings));r=r.filter(x=>keys.has(x.match+':'+x.innings));}
  return r;
 }
 const api={sum,rate,aggregate,select,bat,bowl};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.CWAnalysis=api;
})(typeof window==='undefined'?this:window);
