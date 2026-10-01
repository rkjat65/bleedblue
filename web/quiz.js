/* Quiz: guess the player from career numbers. Pools are static JSON in /data/quiz/. */
(function(){
  const L=window.CRLake,$=s=>document.querySelector(s);
  if(!$('#qz-out'))return;
  const p=L.params();
  const LEVEL={easy:60,medium:30,hard:12};
  const state={mode:p.mode||'ipl',level:LEVEL[p.level]?p.level:'medium',streak:0,round:null,answered:false,showTeams:false};
  const pools={};
  const status=t=>{$('#tl-status').textContent=t;$('#tl-status').hidden=!t;};
  const store=k=>{try{return localStorage.getItem(k);}catch{return null;}};
  const save=(k,v)=>{try{localStorage.setItem(k,v);}catch{}};
  const bestKey=()=>'crickrida-quiz-best-'+state.mode;
  const shuffle=a=>{for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;};
  async function pool(){
    if(!pools[state.mode]){const r=await fetch('/data/quiz/'+state.mode+'.json');if(!r.ok)throw new Error('The question pool is unavailable');pools[state.mode]=await r.json();}
    return pools[state.mode].filter(x=>x.matches>=LEVEL[state.level]);
  }
  function streakLine(){$('#qz-streak').textContent=`Streak ${state.streak} · Best ${+store(bestKey())||0}`;}
  async function next(){
    status('');state.answered=false;state.showTeams=false;
    const players=await pool();
    if(players.length<4){$('#qz-out').innerHTML='<p class="tl-empty">Not enough players at this level. Try an easier one.</p>';return;}
    const answer=players[Math.floor(Math.random()*players.length)];
    let rivals=players.filter(x=>x.id!==answer.id&&x.role===answer.role&&x.first<=answer.last&&x.last>=answer.first);
    if(rivals.length<3)rivals=players.filter(x=>x.id!==answer.id);
    const options=shuffle([answer,...shuffle(rivals).slice(0,3)]);
    state.round={answer,options};draw();
  }
  function clues(a){
    const c=[['Role',a.role],['Span',a.span],['Matches',L.num(a.matches)]];
    if((a.runs||0)>=100||a.role!=='Bowler'){
      c.push(['Runs',L.num(a.runs)],['Average',a.avg==null?'-':L.dec(a.avg)]);
      if(a.sr!=null)c.push(['Strike rate',L.dec(a.sr)]);
      c.push(['Highest',L.esc(a.hs??'-')],['100s / 50s',`${L.num(a.hundreds)} / ${L.num(a.fifties)}`]);
    }
    if((a.wickets||0)>=5){c.push(['Wickets',L.num(a.wickets)]);if(a.econ!=null)c.push(['Economy',L.dec(a.econ)]);if(a.best)c.push(['Best bowling',L.esc(a.best)]);}
    return c;
  }
  function draw(){
    const {answer,options}=state.round;
    const items=clues(answer).map(([k,v])=>`<div><dt>${k}</dt><dd>${v}</dd></div>`).join('');
    const teams=state.showTeams||state.answered?`<div class="wide"><dt>Teams</dt><dd>${L.esc(answer.teams||'-')}</dd></div>`:'';
    const buttons=options.map(o=>{const cls=state.answered?(o.id===answer.id?' is-right':o.id===state.picked?' is-wrong':''):'';return `<button type="button" class="tl-option${cls}" data-id="${L.esc(o.id)}"${state.answered?' disabled':''}>${L.esc(o.name)}</button>`;}).join('');
    let foot='';
    if(state.answered){
      const right=state.picked===answer.id;
      foot=`<p class="tl-verdict ${right?'is-right':'is-wrong'}">${right?'Correct.':'Not this time. It was '+L.esc(answer.name)+'.'}</p><div class="tl-actions"><button type="button" class="primary" id="qz-next">Next player</button><button type="button" id="qz-share">Copy result</button>${answer.path?`<a class="button" href="${L.esc(answer.path)}">${L.esc(answer.name)}'s profile</a>`:''}</div>`;
    }else foot='<div class="tl-actions"><button type="button" id="qz-teams">Show teams</button><button type="button" id="qz-skip">Skip</button></div>';
    $('#qz-out').innerHTML=`<h2>Who is this?</h2><dl class="tl-clues">${items}${teams}</dl><div class="tl-options">${buttons}</div>${foot}`;
    streakLine();
  }
  $('#qz-out').addEventListener('click',async e=>{
    const opt=e.target.closest('.tl-option');
    if(opt&&!state.answered){
      state.answered=true;state.picked=opt.dataset.id;
      if(state.picked===state.round.answer.id){state.streak++;if(state.streak>(+store(bestKey())||0))save(bestKey(),state.streak);}else state.streak=0;
      draw();$('#qz-next')?.focus();return;
    }
    if(e.target.id==='qz-next'||e.target.id==='qz-skip'){if(e.target.id==='qz-skip')state.streak=0;await next();return;}
    if(e.target.id==='qz-teams'){state.showTeams=true;draw();return;}
    if(e.target.id==='qz-share'){
      const text=`Crickrida quiz: streak ${state.streak} (best ${+store(bestKey())||0}). Can you beat it? ${location.origin}/quiz/?mode=${state.mode}`;
      try{await navigator.clipboard.writeText(text);e.target.textContent='Copied';}catch{e.target.textContent='Copy failed';}
    }
  });
  async function boot(){
    try{
      $('#qz-mode').value=state.mode;if(!$('#qz-mode').value){state.mode='ipl';$('#qz-mode').value='ipl';}
      $('#qz-mode').addEventListener('change',async e=>{state.mode=e.target.value;state.streak=0;L.setParams({mode:state.mode,level:state.level==='medium'?'':state.level});await next();});
      L.seg($('#qz-level'),state.level,async v=>{state.level=v;state.streak=0;L.setParams({mode:state.mode,level:v==='medium'?'':v});await next();});
      await next();
    }catch(e){status('The quiz could not load: '+e.message+'. Reload to retry.');}
  }
  boot();
})();
