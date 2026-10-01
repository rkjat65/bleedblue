/* Fantasy: projected XI from ball_fantasy, using the analytics app's points, form and venue rules. */
(function(){
  const L=window.CRLake,$=s=>document.querySelector(s);
  if(!$('#fa-out'))return;
  const p=L.params();
  const state={comp:['IPL','T20I-Men','T20I-Women'].includes(p.comp)?p.comp:'IPL',team1:p.team1||'',team2:p.team2||'',venue:p.venue||''};
  const RECENT=10,VENUE_WEIGHT=0.4,MAX_PER_TEAM=7;
  const status=t=>{$('#tl-status').textContent=t;$('#tl-status').hidden=!t;};
  const scope=()=>{const [comp,g]=state.comp.split('-');return `competition=${L.lit(comp)} AND gender=${L.lit(g||'Men')}`;};
  let byId=new Map();
  async function options(){
    const teams=state.comp==='IPL'
      ?await L.query(`SELECT team, max(season) last_season FROM ball_fantasy WHERE ${scope()} GROUP BY 1 HAVING max(season)=(SELECT max(season) FROM ball_fantasy WHERE ${scope()}) ORDER BY 1`)
      :await L.query(`SELECT team, count(DISTINCT match_id) n FROM ball_fantasy WHERE ${scope()} AND date>=(SELECT strftime(CAST(max(date) AS DATE)-INTERVAL 2 YEAR,'%Y-%m-%d') FROM ball_fantasy WHERE ${scope()}) GROUP BY 1 HAVING count(DISTINCT match_id)>=8 ORDER BY n DESC, 1`);
    const names=teams.map(t=>t.team);
    if(!names.includes(state.team1))state.team1=names[0]||'';
    if(!names.includes(state.team2)||state.team2===state.team1)state.team2=names.find(t=>t!==state.team1)||'';
    for(const k of ['team1','team2'])$('#fa-'+k).innerHTML=names.map(t=>`<option${t===state[k]?' selected':''} value="${L.esc(t)}">${L.esc(t)}</option>`).join('');
    const venues=await L.query(`SELECT venue, count(DISTINCT match_id) n FROM ball_fantasy WHERE ${scope()} AND venue IS NOT NULL GROUP BY 1 HAVING count(DISTINCT match_id)>=5 ORDER BY n DESC, 1 LIMIT 80`);
    if(state.venue&&!venues.some(v=>v.venue===state.venue))state.venue='';
    $('#fa-venue').innerHTML='<option value="">Any ground</option>'+venues.map(v=>`<option${v.venue===state.venue?' selected':''} value="${L.esc(v.venue)}">${L.esc(v.venue)}</option>`).join('');
  }
  function squadSql(team){
    return state.comp==='IPL'
      ?`SELECT DISTINCT player_id, ${L.lit(team)} team FROM ball_fantasy WHERE ${scope()} AND team=${L.lit(team)} AND season=(SELECT max(season) FROM ball_fantasy WHERE ${scope()} AND team=${L.lit(team)})`
      :`SELECT DISTINCT player_id, ${L.lit(team)} team FROM ball_fantasy WHERE ${scope()} AND team=${L.lit(team)} AND match_id IN (SELECT match_id FROM (SELECT DISTINCT match_id, date FROM ball_fantasy WHERE ${scope()} AND team=${L.lit(team)}) ORDER BY date DESC LIMIT 15)`;
  }
  function role(r){const w=r.recent_wkts/r.n,runs=r.recent_runs/r.n;return w>=0.8&&runs>=12?'All-rounder':w>=0.6?'Bowler':'Batter';}
  function pickXI(players){
    const sorted=[...players].sort((a,b)=>b.projected-a.projected),xi=[],per={};
    for(const pl of sorted){if(xi.length===11)break;if((per[pl.team]||0)>=MAX_PER_TEAM)continue;xi.push(pl);per[pl.team]=(per[pl.team]||0)+1;}
    const bowling=x=>x.role!=='Batter';
    let need=3-xi.filter(bowling).length;
    if(need>0){
      const spare=sorted.filter(x=>!xi.includes(x)&&bowling(x));
      while(need>0&&spare.length){
        const batters=xi.filter(x=>!bowling(x)).sort((a,b)=>a.projected-b.projected);
        const out=batters.find(b=>(per[spare[0].team]||0)<MAX_PER_TEAM||spare[0].team===b.team);if(!out)break;
        const inn=spare.shift();xi.splice(xi.indexOf(out),1,inn);per[out.team]--;per[inn.team]=(per[inn.team]||0)+1;need--;
      }
    }
    return xi.sort((a,b)=>b.projected-a.projected);
  }
  async function render(){
    L.setParams({comp:state.comp==='IPL'?'':state.comp,team1:state.team1,team2:state.team2,venue:state.venue});
    if(!state.team1||!state.team2||state.team1===state.team2){$('#fa-out').innerHTML='<section class="panel tl-block"><p class="tl-empty">Pick two different teams.</p></section>';return;}
    status('Projecting…');
    try{
      const venue=L.lit(state.venue||'');
      const rows=await L.query(`WITH squad AS (${squadSql(state.team1)} UNION ${squadSql(state.team2)}),
        hist AS (SELECT f.player_id, f.points, f.runs, f.wickets, f.venue, row_number() OVER (PARTITION BY f.player_id ORDER BY f.date DESC, f.match_id DESC) rn FROM ball_fantasy f WHERE ${scope()} AND f.player_id IN (SELECT player_id FROM squad))
        SELECT s.player_id, s.team, avg(points) FILTER (WHERE rn<=${RECENT}) recent_avg, sum(runs) FILTER (WHERE rn<=${RECENT}) recent_runs, sum(wickets) FILTER (WHERE rn<=${RECENT}) recent_wkts,
          count(*) FILTER (WHERE rn<=${RECENT}) n, avg(points) FILTER (WHERE venue=${venue}) venue_avg, count(*) FILTER (WHERE venue=${venue}) venue_n
        FROM squad s JOIN hist h USING(player_id) GROUP BY 1,2`);
      const ids=rows.map(r=>r.player_id).filter(id=>!byId.has(id));
      if(ids.length)for(const r of await L.query(`SELECT player_id,name,path FROM ball_players WHERE player_id IN (${ids.map(L.lit).join(',')})`))byId.set(r.player_id,r);
      const players=rows.map(r=>({...r,name:byId.get(r.player_id)?.name||r.player_id,path:byId.get(r.player_id)?.path,role:role(r),
        projected:state.venue&&r.venue_n>=2?(1-VENUE_WEIGHT)*r.recent_avg+VENUE_WEIGHT*r.venue_avg:r.recent_avg}));
      const xi=pickXI(players);
      const cards=xi.map((pl,i)=>`<article class="tl-pick${i<2?' is-lead':''}"><span class="tl-badge">${i===0?'C':i===1?'VC':''}</span><h3>${L.link(pl.path,pl.name)}</h3><p>${L.esc(pl.team)} · ${pl.role}</p><div class="tl-meter"><i style="width:${Math.min(100,pl.projected/(xi[0].projected||1)*100).toFixed(1)}%"></i></div><strong>${L.dec(pl.projected,1)}</strong></article>`).join('');
      const all=[...players].sort((a,b)=>b.projected-a.projected);
      let html=`<section class="panel tl-block"><h2>Suggested XI</h2><p class="tl-fine">${L.esc(state.team1)} v ${L.esc(state.team2)}${state.venue?' at '+L.esc(state.venue):''}. Captain and vice-captain are the two highest projections.</p><div class="tl-picks">${cards}</div></section>`;
      html+=`<section class="panel tl-block"><h2>Every player</h2>`+L.table('Projected fantasy points',['Player','Team','Role','Projected','Last 10 avg','Runs (last 10)','Wickets (last 10)','Ground avg'],all.map(pl=>[L.link(pl.path,pl.name),L.esc(pl.team),pl.role,L.dec(pl.projected,1),L.dec(pl.recent_avg,1),L.num(pl.recent_runs),L.num(pl.recent_wkts),pl.venue_n?`${L.dec(pl.venue_avg,1)} <small>(${pl.venue_n})</small>`:'-']),{left:[1,2]})+'</section>';
      $('#fa-out').innerHTML=html;status('');
    }catch(e){status('Fantasy could not load: '+e.message);}
  }
  async function boot(){
    try{
      await L.open(['ball_fantasy','ball_players']);
      L.seg($('#fa-comp'),state.comp,async v=>{state.comp=v;state.team1=state.team2=state.venue='';await options();render();});
      for(const k of ['team1','team2','venue'])$('#fa-'+k).addEventListener('change',e=>{state[k]=e.target.value;render();});
      await options();await render();
    }catch(e){status('Fantasy could not load: '+e.message+'. Reload to retry.');}
  }
  boot();
})();
