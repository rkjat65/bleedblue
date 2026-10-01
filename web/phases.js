/* Phases: powerplay, middle and death from ball_phase_teams, ball_overs and ball_phase_players. */
(function(){
  const L=window.CRLake,$=s=>document.querySelector(s);
  if(!$('#ph-out'))return;
  const p=L.params();
  const state={comp:p.comp||'IPL',gender:p.gender==='Women'?'Women':'Men',from:p.from||'',to:p.to||'',team:p.team||'',venue:p.venue||'',innings:p.innings||'both',lead:p.lead||'Death',min:+p.min||0};
  let byId=new Map();
  const PHASES=['Powerplay','Middle','Death'];
  const OVERS={T20:['overs 1 to 6','overs 7 to 15','overs 16 to 20'],ODI:['overs 1 to 10','overs 11 to 40','overs 41 to 50']};
  const status=t=>{$('#tl-status').textContent=t;$('#tl-status').hidden=!t;};
  const isODI=()=>state.comp==='ODI';
  const minBalls=()=>state.min||(isODI()?300:120);
  function compWhere(alias=''){
    const a=alias?alias+'.':'';
    const w=[`${a}gender=${L.lit(state.gender)}`];
    if(state.comp==='T20WC')w.push(`${a}tournament='T20 World Cup'`);else w.push(`${a}competition=${L.lit(state.comp)}`);
    return w;
  }
  function matchWhere({venue=true}={}){
    const w=compWhere('m');
    if(+state.from)w.push(`m.season>=${+state.from}`);if(+state.to)w.push(`m.season<=${+state.to}`);
    if(venue&&state.venue)w.push(`m.venue=${L.lit(state.venue)}`);
    return w.join(' AND ');
  }
  function playerWhere(){
    const w=compWhere();
    if(+state.from)w.push(`year>=${+state.from}`);if(+state.to)w.push(`year<=${+state.to}`);
    if(state.team)w.push(`team=${L.lit(state.team)}`);
    return w.join(' AND ');
  }
  const teamClause=a=>state.team?` AND ${a}.team=${L.lit(state.team)}`:'';
  async function options(){
    const seasons=await L.query(`SELECT DISTINCT season FROM ball_matches m WHERE ${compWhere('m').join(' AND ')} AND season IS NOT NULL ORDER BY 1`);
    const ys=seasons.map(r=>r.season);
    if(state.from&&!ys.includes(+state.from))state.from='';if(state.to&&!ys.includes(+state.to))state.to='';
    $('#ph-from').innerHTML='<option value="">First</option>'+ys.map(y=>`<option${+state.from===y?' selected':''}>${y}</option>`).join('');
    $('#ph-to').innerHTML='<option value="">Latest</option>'+ys.map(y=>`<option${+state.to===y?' selected':''}>${y}</option>`).join('');
    const teams=await L.query(`SELECT t.team, count(DISTINCT t.match_id) n FROM ball_phase_teams t JOIN ball_matches m USING(match_id) WHERE ${matchWhere({venue:false})} GROUP BY 1 ORDER BY n DESC, 1`);
    if(state.team&&!teams.some(t=>t.team===state.team))state.team='';
    $('#ph-team').innerHTML='<option value="">All teams</option>'+teams.map(t=>`<option${t.team===state.team?' selected':''} value="${L.esc(t.team)}">${L.esc(t.team)}</option>`).join('');
    const venues=await L.query(`SELECT venue, count(*) n FROM ball_matches m WHERE ${matchWhere({venue:false})} AND venue IS NOT NULL GROUP BY 1 HAVING count(*)>=3 ORDER BY n DESC, 1 LIMIT 80`);
    if(state.venue&&!venues.some(v=>v.venue===state.venue))state.venue='';
    $('#ph-venue').innerHTML='<option value="">All grounds</option>'+venues.map(v=>`<option${v.venue===state.venue?' selected':''} value="${L.esc(v.venue)}">${L.esc(v.venue)} (${v.n})</option>`).join('');
  }
  function phaseCards(rows){
    const labels=OVERS[isODI()?'ODI':'T20'];
    return '<div class="tl-phases">'+PHASES.map((ph,i)=>{
      const r=rows.find(x=>x.phase===ph);if(!r)return '';
      const items=[['Run rate',L.dec(L.ratio(r.runs,r.balls,6))],['Runs per innings',L.dec(L.ratio(r.runs,r.innings),1)],['Wickets per innings',L.dec(L.ratio(r.wickets,r.innings))],['Boundary %',L.dec(L.ratio(r.fours+r.sixes,r.balls,100),1)],['Dot %',L.dec(L.ratio(r.dots,r.balls,100),1)],['Balls per wicket',L.dec(L.ratio(r.balls,r.wickets),1)]];
      return `<article class="tl-phase ph-${ph.toLowerCase()}"><div class="tl-phase-head"><h3>${ph}</h3><span>${labels[i]} · ${L.num(r.innings)} innings</span></div><dl>${items.map(([k,v])=>`<div><dt>${k}</dt><dd>${v}</dd></div>`).join('')}</dl></article>`;
    }).join('')+'</div>';
  }
  function oversChart(rows){
    if(!rows.length)return '<p class="tl-empty">No overs recorded for this selection.</p>';
    const n=isODI()?50:20,W=720,H=240,left=36,right=W-12,top=14,bottom=H-30,slot=(right-left)/n,bw=Math.max(4,slot*0.66);
    const avg=rows.map(r=>({over:r.over,runs:r.runs/r.innings,wkts:r.wickets/r.innings,innings:r.innings}));
    const peak=Math.max(...avg.map(a=>a.runs),1),wpeak=Math.max(...avg.map(a=>a.wkts),0.01);
    const cut=isODI()?[10,40]:[6,15];
    let svg='';
    for(let v=0;v<=peak;v+=peak>14?4:2){const y=bottom-v/peak*(bottom-top);svg+=`<line class="cw-grid" x1="${left}" x2="${right}" y1="${y.toFixed(1)}" y2="${y.toFixed(1)}"/><text class="cw-axis" x="${left-6}" y="${(y+3).toFixed(1)}" text-anchor="end">${v}</text>`;}
    for(const a of avg){const x=left+(a.over-1)*slot+(slot-bw)/2,h=a.runs/peak*(bottom-top),ph=a.over<=cut[0]?'powerplay':a.over<=cut[1]?'middle':'death';
      svg+=`<rect class="tl-bar ph-${ph}" x="${x.toFixed(1)}" y="${(bottom-h).toFixed(1)}" width="${bw.toFixed(1)}" height="${h.toFixed(1)}" rx="2"><title>Over ${a.over}: ${a.runs.toFixed(2)} runs, ${a.wkts.toFixed(2)} wickets per innings (${a.innings} innings)</title></rect>`;
      if(n<=20||a.over%5===0||a.over===1)svg+=`<text class="cw-axis" x="${(x+bw/2).toFixed(1)}" y="${bottom+14}" text-anchor="middle">${a.over}</text>`;}
    const pts=avg.map(a=>`${(left+(a.over-0.5)*slot).toFixed(1)},${(bottom-a.wkts/wpeak*(bottom-top)*0.9).toFixed(1)}`).join(' ');
    svg+=`<polyline class="tl-wkts" points="${pts}"/>`;
    return `<figure class="cw-figure tl-overs"><figcaption>Runs per over, per innings that reached it. The line is wickets per over.</figcaption><svg class="cw-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Average runs and wickets in each over">${svg}</svg><p class="tl-legend"><span class="ph-powerplay">Powerplay</span><span class="ph-middle">Middle</span><span class="ph-death">Death</span><span class="tl-wkt-key">Wickets</span></p></figure>`;
  }
  async function render(){
    L.setParams({comp:state.comp==='IPL'?'':state.comp,gender:state.gender==='Men'?'':state.gender,from:state.from,to:state.to,team:state.team,venue:state.venue,innings:state.innings==='both'?'':state.innings,lead:state.lead==='Death'?'':state.lead,min:state.min||''});
    status('Querying…');
    try{
      const mw=matchWhere();
      const inn=state.innings==='both'?'':` AND t.innings=${state.innings==='1'?1:2}`;
      const summary=await L.query(`SELECT t.phase, count(*) innings, sum(t.balls) balls, sum(t.runs) runs, sum(t.wickets) wickets, sum(t.dots) dots, sum(t.fours) fours, sum(t.sixes) sixes FROM ball_phase_teams t JOIN ball_matches m USING(match_id) WHERE ${mw}${teamClause('t')}${inn} GROUP BY 1`);
      const overs=await L.query(`SELECT o.over, count(*) innings, sum(o.runs) runs, sum(o.wickets) wickets FROM ball_overs o JOIN ball_matches m USING(match_id) WHERE ${mw}${teamClause('o')}${state.innings==='both'?'':` AND o.innings=${state.innings==='1'?1:2}`} GROUP BY 1 ORDER BY 1`);
      const teamMatch=state.team?` AND ${L.lit(state.team)} IN (m.team_1,m.team_2)`:'';
      const chase=(await L.query(`WITH f AS (SELECT match_id, sum(runs) total FROM ball_phase_teams WHERE innings=1 GROUP BY 1) SELECT count(*) decided, count(*) FILTER (WHERE m.winner=m.batted_first) first_won, avg(f.total) avg_first, avg(f.total) FILTER (WHERE m.winner=m.batted_first) avg_defended FROM ball_matches m JOIN f USING(match_id) WHERE ${mw}${teamMatch} AND m.result='win'`))[0];
      const toss=await L.query(`SELECT toss_decision d, count(*) n, count(*) FILTER (WHERE winner=toss_winner) won FROM ball_matches m WHERE ${mw}${teamMatch} AND result='win' AND toss_decision IS NOT NULL GROUP BY 1 ORDER BY 1`);
      const pw=playerWhere();
      const bat=await L.query(`SELECT player_id, sum(innings) innings, sum(balls) balls, sum(runs) runs, sum(outs) outs, sum(fours)+sum(sixes) bounds FROM ball_phase_players WHERE ${pw} AND role='bat' AND phase=${L.lit(state.lead)} GROUP BY 1 HAVING sum(balls)>=${minBalls()} ORDER BY runs DESC LIMIT 15`);
      const bowl=await L.query(`SELECT player_id, sum(innings) innings, sum(balls) balls, sum(runs) runs, sum(outs) wickets, sum(dots) dots FROM ball_phase_players WHERE ${pw} AND role='bowl' AND phase=${L.lit(state.lead)} GROUP BY 1 HAVING sum(balls)>=${minBalls()} ORDER BY sum(outs) DESC, sum(runs)*1.0/sum(balls) ASC LIMIT 15`);
      const venues=state.venue?[]:await L.query(`SELECT m.venue, t.phase, count(DISTINCT m.match_id) matches, sum(t.runs) runs, sum(t.balls) balls FROM ball_phase_teams t JOIN ball_matches m USING(match_id) WHERE ${matchWhere({venue:false})}${teamClause('t')} AND m.venue IS NOT NULL GROUP BY 1,2`);
      const ids=[...new Set([...bat,...bowl].map(r=>r.player_id).filter(id=>!byId.has(id)))];
      if(ids.length)for(const r of await L.query(`SELECT player_id,name,path FROM ball_players WHERE player_id IN (${ids.map(L.lit).join(',')})`))byId.set(r.player_id,r);
      const who=id=>L.link(byId.get(id)?.path,byId.get(id)?.name||id);
      let html='';
      if(!summary.length){$('#ph-out').innerHTML='<section class="panel tl-block"><p class="tl-empty">No ball-by-ball innings match these filters.</p></section>';status('');return;}
      const innSeg=`<div class="tl-chips" role="group" aria-label="Innings">${[['both','Both innings'],['1','Batting first'],['2','Chasing']].map(([k,t])=>`<button type="button" data-innings="${k}" aria-pressed="${state.innings===k}">${t}</button>`).join('')}</div>`;
      html+=`<section class="panel tl-block"><div class="tl-block-head"><h2>Phase by phase</h2>${innSeg}</div>${phaseCards(summary)}</section>`;
      html+=`<section class="panel tl-block"><h2>Over by over</h2>${oversChart(overs)}</section>`;
      const tossRows=toss.map(r=>[r.d==='field'?'Chose to field':'Chose to bat',L.num(r.n),L.num(r.won),L.dec(L.ratio(r.won,r.n,100),1)]);
      html+=`<section class="panel tl-block"><h2>Batting first or chasing</h2>`+L.tiles([[L.num(chase?.decided),'Matches with a result'],[L.dec(L.ratio(chase?.first_won,chase?.decided,100),1),'Won batting first %'],[L.dec(L.ratio((chase?.decided||0)-(chase?.first_won||0),chase?.decided,100),1),'Won chasing %'],[L.dec(chase?.avg_first,1),'First innings average'],[L.dec(chase?.avg_defended,1),'Average total defended']])+L.table('Toss decisions',['Toss decision','Matches','Toss winner won','Win %'],tossRows)+'</section>';
      const leadSeg=`<div class="tl-chips" role="group" aria-label="Phase">${PHASES.map(ph=>`<button type="button" data-lead="${ph}" aria-pressed="${state.lead===ph}">${ph}</button>`).join('')}<label class="tl-inline">Min balls <input id="ph-min" type="number" min="6" max="5000" step="6" value="${minBalls()}"></label></div>`;
      html+=`<section class="panel tl-block"><div class="tl-block-head"><h2>${state.lead} leaders</h2>${leadSeg}</div><div class="tl-two">`
        +L.table(`${state.lead} batters`,['Batter','Innings','Balls','Runs','SR','Outs','Boundary %'],bat.map(r=>[who(r.player_id),L.num(r.innings),L.num(r.balls),L.num(r.runs),L.dec(L.ratio(r.runs,r.balls,100)),L.num(r.outs),L.dec(L.ratio(r.bounds,r.balls,100),1)]),{empty:'No batter reaches the minimum balls.'})
        +L.table(`${state.lead} bowlers`,['Bowler','Innings','Balls','Wickets','Econ','SR','Dot %'],bowl.map(r=>[who(r.player_id),L.num(r.innings),L.num(r.balls),L.num(r.wickets),L.dec(L.ratio(r.runs,r.balls,6)),r.wickets?L.dec(r.balls/r.wickets,1):'-',L.dec(L.ratio(r.dots,r.balls,100),1)]),{empty:'No bowler reaches the minimum balls.'})
        +`</div>${state.venue?'<p class="tl-fine">Leaders cover every ground; the ground filter applies to the team figures above.</p>':''}</section>`;
      if(venues.length){
        const by={};for(const v of venues){const r=by[v.venue]||(by[v.venue]={venue:v.venue,matches:0});r.matches=Math.max(r.matches,v.matches);r[v.phase]=L.ratio(v.runs,v.balls,6);}
        const top=Object.values(by).sort((a,b)=>b.matches-a.matches).slice(0,15);
        html+=`<section class="panel tl-block"><h2>Grounds by phase</h2>`+L.table('Run rate by phase at the busiest grounds',['Ground','Matches',...PHASES.map(p=>p+' RR')],top.map(r=>[`<button type="button" class="tl-row-pick" data-venue="${L.esc(r.venue)}">${L.esc(r.venue)}</button>`,L.num(r.matches),...PHASES.map(p=>L.dec(r[p]))]))+'</section>';
      }
      $('#ph-out').innerHTML=html;status('');
    }catch(e){status('Phases could not load: '+e.message);}
  }
  $('#ph-out').addEventListener('click',e=>{
    const b=e.target.closest('[data-innings],[data-lead],[data-venue]');if(!b)return;
    if(b.dataset.innings)state.innings=b.dataset.innings;
    if(b.dataset.lead)state.lead=b.dataset.lead;
    if(b.dataset.venue){state.venue=b.dataset.venue;$('#ph-venue').value=state.venue;window.scrollTo({top:0});}
    render();
  });
  $('#ph-out').addEventListener('change',e=>{if(e.target.id==='ph-min'){state.min=Math.max(6,+e.target.value||0);render();}});
  async function boot(){
    try{
      await L.open(['ball_matches','ball_phase_teams','ball_overs','ball_phase_players','ball_players']);
      const refresh=async()=>{await options();await render();};
      L.seg($('#ph-comp'),state.comp,v=>{state.comp=v;state.min=0;refresh();});
      L.seg($('#ph-gender'),state.gender,v=>{state.gender=v;refresh();});
      for(const k of ['from','to','team','venue'])$('#ph-'+k).addEventListener('change',e=>{state[k]=e.target.value;k==='venue'?render():refresh();});
      await refresh();
    }catch(e){status('Phases could not load: '+e.message+'. Reload to retry.');}
  }
  boot();
})();
