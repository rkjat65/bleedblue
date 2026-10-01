/* Matchups: batter v bowler from ball_matchups. */
(function(){
  const L=window.CRLake,$=s=>document.querySelector(s);
  if(!$('#mu-out'))return;
  const p=L.params();
  const state={comp:p.comp||'all',gender:p.gender==='Women'?'Women':'Men',batter:p.batter||'',bowler:p.bowler||'',from:p.from||'',to:p.to||'',sort:p.sort||'balls',min:+p.min||30};
  let players=[],byId=new Map();
  const status=t=>{$('#tl-status').textContent=t;$('#tl-status').hidden=!t;};
  const COMP={all:'All cricket',Test:'Tests',ODI:'ODIs',T20I:'T20Is',IPL:'IPL',T20WC:'T20 World Cup'};
  function where(){
    const w=[`gender=${L.lit(state.gender)}`];
    if(state.comp==='T20WC')w.push(`tournament='T20 World Cup'`);else if(state.comp!=='all')w.push(`competition=${L.lit(state.comp)}`);
    if(+state.from)w.push(`year>=${+state.from}`);if(+state.to)w.push(`year<=${+state.to}`);
    return w.join(' AND ');
  }
  const name=id=>byId.get(id)?.name||id;
  const plink=id=>L.link(byId.get(id)?.path,name(id));
  function line(r){
    const sr=L.ratio(r.runs,r.balls,100),avg=r.outs?r.runs/r.outs:null;
    return {...r,sr,avg,dot:L.ratio(r.dots,r.balls,100),bound:L.ratio(r.fours+r.sixes,r.balls,100),dom:sr==null?null:sr-25*r.outs*100/r.balls};
  }
  const SUMS='sum(innings) innings,sum(balls) balls,sum(runs) runs,sum(outs) outs,sum(dots) dots,sum(fours) fours,sum(sixes) sixes';
  const ORDER={balls:'sum(balls) DESC',outs:'sum(outs) DESC, sum(balls) DESC',sr:'sum(runs)*1.0/sum(balls) DESC',bowler:'(sum(runs)*100.0-25*sum(outs)*100.0)/sum(balls) ASC'};
  const sortBar=()=>`<div class="tl-chips" role="group" aria-label="Sort">${[['balls','Most balls'],['outs','Most dismissals'],['sr','Batter on top'],['bowler','Bowler on top']].map(([k,t])=>`<button type="button" data-sort="${k}" aria-pressed="${state.sort===k}">${t}</button>`).join('')}<label class="tl-inline">Min balls <input id="mu-min" type="number" min="6" max="2000" step="6" value="${state.min}"></label></div>`;
  async function duel(){
    const rows=(await L.query(`SELECT competition,year,${SUMS} FROM ball_matchups WHERE batter_id=${L.lit(state.batter)} AND bowler_id=${L.lit(state.bowler)} AND ${where()} GROUP BY competition,year ORDER BY year DESC,competition`)).map(line);
    if(!rows.length)return `<h2>${plink(state.batter)} v ${plink(state.bowler)}</h2><p class="tl-empty">They have not met in ${COMP[state.comp]} ${state.gender==='Women'?'(women)':''} in the ball-by-ball record.</p>`;
    const total=line(rows.reduce((a,r)=>{for(const k of ['innings','balls','runs','outs','dots','fours','sixes'])a[k]=(a[k]||0)+r[k];return a;},{}));
    const byComp={};for(const r of rows){const c=byComp[r.competition]||(byComp[r.competition]={competition:r.competition,innings:0,balls:0,runs:0,outs:0,dots:0,fours:0,sixes:0});for(const k of ['innings','balls','runs','outs','dots','fours','sixes'])c[k]+=r[k];}
    const comps=Object.values(byComp).map(line);
    const head=['Innings','Balls','Runs','SR','Dismissals','Average','Dot %','4s','6s'];
    const cells=r=>[L.num(r.innings),L.num(r.balls),L.num(r.runs),L.dec(r.sr),L.num(r.outs),r.outs?L.dec(r.avg):'-',L.dec(r.dot,1),L.num(r.fours),L.num(r.sixes)];
    let html=`<h2>${plink(state.batter)} v ${plink(state.bowler)}</h2>`;
    html+=L.tiles([[L.num(total.balls),'Balls'],[L.num(total.runs),'Runs'],[L.dec(total.sr),'Strike rate'],[L.num(total.outs),'Dismissals'],[total.outs?L.dec(total.avg):'-','Average'],[L.dec(total.dot,1),'Dot %'],[L.dec(total.bound,1),'Boundary %'],[L.num(total.innings),'Innings']]);
    if(comps.length>1)html+=L.table('Duel by competition',['Competition',...head],comps.map(r=>[L.esc(r.competition),...cells(r)]));
    html+=L.table('Duel by year',['Year','Competition',...head],rows.map(r=>[String(r.year),L.esc(r.competition),...cells(r)]),{left:[1]});
    return html;
  }
  async function opponents(){
    const one=state.batter?'batter_id':'bowler_id',other=state.batter?'bowler_id':'batter_id',id=state.batter||state.bowler;
    const rows=(await L.query(`SELECT ${other} other,${SUMS} FROM ball_matchups WHERE ${one}=${L.lit(id)} AND ${where()} GROUP BY ${other} HAVING sum(balls)>=${state.min} ORDER BY ${ORDER[state.sort]} LIMIT 60`)).map(line);
    const title=state.batter?`Bowlers ${name(id)} has faced`:`Batters ${name(id)} has bowled to`;
    const head=[state.batter?'Bowler':'Batter','Innings','Balls','Runs','SR','Dismissals','Average','Dot %'];
    return `<h2>${L.esc(title)}</h2>${sortBar()}`+L.table(title,head,rows.map(r=>[`<button type="button" class="tl-row-pick" data-id="${L.esc(r.other)}">${L.esc(name(r.other))}</button>`,L.num(r.innings),L.num(r.balls),L.num(r.runs),L.dec(r.sr),L.num(r.outs),r.outs?L.dec(r.avg):'-',L.dec(r.dot,1)]),{empty:`No opponent with ${state.min} or more balls. Lower the minimum.`});
  }
  async function contested(){
    const rows=(await L.query(`SELECT batter_id,bowler_id,${SUMS} FROM ball_matchups WHERE ${where()} GROUP BY batter_id,bowler_id HAVING sum(balls)>=${state.min} ORDER BY ${ORDER[state.sort]} LIMIT 50`)).map(line);
    const head=['Batter','Bowler','Balls','Runs','SR','Dismissals','Dot %'];
    return `<h2>Most contested duels: ${L.esc(COMP[state.comp])}</h2>${sortBar()}`+L.table('Most contested duels',head,rows.map(r=>[`<button type="button" class="tl-row-pick" data-pair="${L.esc(r.batter_id)}|${L.esc(r.bowler_id)}">${L.esc(name(r.batter_id))}</button>`,L.esc(name(r.bowler_id)),L.num(r.balls),L.num(r.runs),L.dec(r.sr),L.num(r.outs),L.dec(r.dot,1)]),{left:[1]});
  }
  let run=0;
  async function render(){
    const mine=++run;
    L.setParams({comp:state.comp==='all'?'':state.comp,gender:state.gender==='Men'?'':state.gender,batter:state.batter,bowler:state.bowler,from:state.from,to:state.to,sort:state.sort==='balls'?'':state.sort,min:state.min===30?'':state.min});
    status('Querying…');
    try{
      const html=state.batter&&state.bowler?await duel():state.batter||state.bowler?await opponents():await contested();
      if(mine!==run)return;
      $('#mu-out').innerHTML=html;status('');
    }catch(e){status('Matchups could not load: '+e.message);}
  }
  $('#mu-out').addEventListener('click',e=>{
    const s=e.target.closest('[data-sort]');if(s){state.sort=s.dataset.sort;render();return;}
    const pick=e.target.closest('.tl-row-pick');if(!pick)return;
    if(pick.dataset.pair){[state.batter,state.bowler]=pick.dataset.pair.split('|');}
    else if(state.batter)state.bowler=pick.dataset.id;else state.batter=pick.dataset.id;
    $('#mu-batter').value=state.batter?name(state.batter):'';$('#mu-bowler').value=state.bowler?name(state.bowler):'';
    render();window.scrollTo({top:$('#mu-out').offsetTop-90});
  });
  $('#mu-out').addEventListener('change',e=>{if(e.target.id==='mu-min'){state.min=Math.max(6,+e.target.value||30);render();}});
  async function boot(){
    try{
      await L.open(['ball_matchups','ball_players']);
      players=(await L.query('SELECT player_id,name,teams,gender,path FROM ball_players')).map(p=>({...p,search:(p.name+' '+(p.teams||'')).toLowerCase()}));
      byId=new Map(players.map(p=>[p.player_id,p]));
      const pool=()=>players.filter(p=>(p.gender||'').includes(state.gender));
      L.picker($('#mu-batter'),pool,players,p=>{state.batter=p.player_id;render();});
      L.picker($('#mu-bowler'),pool,players,p=>{state.bowler=p.player_id;render();});
      for(const k of ['batter','bowler'])if(state[k])$('#mu-'+k).value=name(state[k]);
      for(const k of ['batter','bowler'])$('#mu-'+k).addEventListener('input',e=>{if(!e.target.value.trim()&&state[k]){state[k]='';render();}});
      L.seg($('#mu-comp'),state.comp,v=>{state.comp=v;render();});
      L.seg($('#mu-gender'),state.gender,v=>{state.gender=v;render();});
      $('#mu-from').value=state.from;$('#mu-to').value=state.to;
      for(const k of ['from','to'])$('#mu-'+k).addEventListener('change',e=>{state[k]=e.target.value;render();});
      $('#mu-swap').onclick=()=>{[state.batter,state.bowler]=[state.bowler,state.batter];$('#mu-batter').value=state.batter?name(state.batter):'';$('#mu-bowler').value=state.bowler?name(state.bowler):'';render();};
      $('#mu-clear').onclick=()=>{state.batter=state.bowler='';$('#mu-batter').value=$('#mu-bowler').value='';render();};
      await render();
    }catch(e){status('Matchups could not load: '+e.message+'. Reload to retry.');}
  }
  boot();
})();
