/* Studio: real dataset queries, several measures at once, and reproducible export artwork. */
(() => {
 'use strict';
 const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)], core=window.CWStudio;
 const esc=x=>String(x??'-').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const num=x=>x==null?'-':typeof x==='string'&&!Number.isFinite(Number(x))?x:Number(x).toLocaleString('en-GB',{maximumFractionDigits:2});
 const titleCase=x=>String(x).replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());
 const lake=location.hostname==='127.0.0.1'||location.hostname==='localhost'?'/data/lake/':location.hostname==='crickrida.com'?'/lake/':'https://pub-2deb6471d5df4274810ac4497fdf3ab2.r2.dev/';
 const files={careers:'careers',batting:'batting_innings',bowling:'bowling_innings',matches:'matches'};
 const ids={dataset:'st-dataset',team:'st-team',opponent:'st-opponent',venue:'st-venue',from:'st-from',to:'st-to',position:'st-position',innings_number:'st-innings',group:'st-group',minimum:'st-minimum',limit:'st-limit',match:'st-match',metric:'st-sort',type:'design-type',size:'design-size',theme:'design-theme',accent:'design-accent',title:'design-title',subtitle:'design-subtitle',labels:'design-labels'};
 const GROUP_LABEL={player:'Player',teams:'Team',team:'Team',format:'Format',gender:'Gender',opponent:'Opponent',venue:'Ground',year:'Year',position:'Batting position',innings_number:'Innings of match',winner:'Winner'};
 const presets={
  profile:{dataset:'careers',metrics:'runs,avg,sr,hundreds,fifties',group:'format',players:['Virat Kohli'],type:'auto',limit:'12'},
  compare:{dataset:'careers',metrics:'runs,avg,sr,hundreds,fifties',group:'player',players:['Sachin Tendulkar','Virat Kohli','Ricky Ponting'],format:'ODI',type:'grouped',limit:'12'},
  leaderboard:{dataset:'careers',metrics:'runs,matches,avg,hundreds',group:'player',format:'ODI',minimum:'50',limit:'15',type:'bar'},
  timeline:{dataset:'batting',metrics:'runs,avg,sr',group:'year',players:['Virat Kohli'],format:'ODI',type:'multiples',limit:'40'},
  batting:{dataset:'batting',metrics:'runs,avg,sr,hundreds',group:'opponent',players:['Virat Kohli'],format:'ODI',type:'bar',limit:'12'},
  bowling:{dataset:'bowling',metrics:'wickets,bowlAvg,econ,bowlSr',group:'opponent',players:['Jasprit Bumrah'],format:'ODI',type:'bar',limit:'12'},
  team:{dataset:'matches',metrics:'matches',group:'winner',type:'table',limit:'12'},
  venue:{dataset:'batting',metrics:'runs,avg,sr',group:'player',format:'ODI',type:'bar',limit:'12',venue:'first'},
  year:{dataset:'batting',metrics:'runs,avg,hundreds',group:'player',format:'ODI',type:'bar',limit:'12',year:'latest'},
  match:{dataset:'matches',metrics:'matches',group:'format',type:'card',limit:'1'},
  custom:{dataset:'batting',metrics:'runs',group:'player',type:'auto',limit:'12'},
 };
 const PALETTES={wicket:{bg:'#0a0a0f',panel:'#14141d',ink:'#e8e8ed',muted:'#8888a0',line:'#26263a',series:['#00e5ff','#ffb800','#b8ff00','#ff5c7a','#8b5cf6','#4aa3ff','#f97316','#22c55e']},
  light:{bg:'#ffffff',panel:'#f3f6fb',ink:'#10233f',muted:'#5b6c76',line:'#dce4f0',series:['#1d4ed8','#d97706','#15803d','#c2264d','#7c3aed','#0e7490','#ea580c','#0f766e']},
  navy:{bg:'#0b1c36',panel:'#112a4f',ink:'#f2f6fc',muted:'#b6c7df',line:'#2c4670',series:['#79b8ff','#ffd166','#9be15d','#ff7b9c','#c4b5fd','#67e8f9','#fdba74','#86efac']},
  paper:{bg:'#faf7ef',panel:'#f1ecdf',ink:'#202a35',muted:'#626973',line:'#dcd5c5',series:['#1f4e79','#b45309','#2f6f4f','#9f1239','#5b21b6','#0f5e6b','#c2410c','#166534']}};
 let photos,db,conn,manifest,players=[],matches=[],rows=[],template='profile',generation=0,page=0,current=null,svgText='',playerChips=[];
 const source=dataset=>`read_parquet(${core.quote(new URL(lake+manifest.tables[files[dataset]].file,location.href).href)})`;
 async function query(sql){return (await conn.query(sql)).toArray().map(core.normalizeRow);}
 const seg=id=>$('#'+id+' button[aria-pressed="true"]')?.dataset.value??'';
 function setSeg(id,value){$$('#'+id+' button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.value===value)));}
 const metricsChosen=()=>$$('#st-metrics button[aria-pressed="true"]').map(b=>b.dataset.metric);
 function state(){const s={template,gender:seg('st-gender'),format:seg('st-format'),metrics:metricsChosen().join(','),players:playerChips.map(p=>p.player_id).join(','),playerNames:playerChips.map(p=>p.player).join('|')};for(const [k,id] of Object.entries(ids))s[k]=$('#'+id).value;if(!s.metric)s.metric=metricsChosen()[0]||'';return s;}
 function choices(id,values,all='All'){const el=$('#'+id);const keep=el.value;el.innerHTML=(all!=null?`<option value="">${esc(all)}</option>`:'')+values.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');el.value=keep;}
 function fields(){const dataset=$('#st-dataset').value;
  const current=new Set(metricsChosen());
  $('#st-metrics').innerHTML=core.allowed[dataset].map(m=>`<button type="button" data-metric="${m}" aria-pressed="${current.has(m)?'true':'false'}">${esc(core.metrics[m])}</button>`).join('');
  const groups=core.dimensions[dataset];const keepGroup=$('#st-group').value;$('#st-group').innerHTML=groups.map(g=>`<option value="${g}">${esc(GROUP_LABEL[g]||titleCase(g))}</option>`).join('');$('#st-group').value=groups.includes(keepGroup)?keepGroup:groups[0];
  sortOptions();
  const special=['match','team'].includes(template);
  $('#st-players-field').hidden=dataset==='matches';
  for(const [id,show] of [['st-opponent',!['careers','matches'].includes(dataset)],['st-venue',dataset!=='careers'],['st-position',dataset==='batting'],['st-innings',['batting','bowling'].includes(dataset)],['st-from',dataset!=='careers'],['st-to',dataset!=='careers'],['st-match',template==='match']])$('#'+id).closest('.st-field').hidden=!show;
  $('#st-match-field').hidden=template!=='match';
  $('#st-metrics').closest('.st-field').hidden=special;$('#st-sort').closest('.st-field').hidden=special;$('#st-group').closest('.st-field').hidden=special;$('#st-minimum').closest('.st-field').hidden=special;
  $('#st-match').innerHTML=matches.filter(m=>m.gender===seg('st-gender')&&(!seg('st-format')||m.format===seg('st-format'))).slice(0,400).map(m=>`<option value="${esc(m.match_id)}">${esc(m.date+' · '+m.team_1+' v '+m.team_2+' · '+m.format)}</option>`).join('');
  $('#studio-players').innerHTML=players.filter(p=>p.gender===seg('st-gender')).map(p=>`<option value="${esc(p.choice)}"></option>`).join('');
 }
 function sortOptions(){const chosen=metricsChosen();const keep=$('#st-sort').value;$('#st-sort').innerHTML=chosen.map(m=>`<option value="${m}">${esc(core.metrics[m])}</option>`).join('')||'<option value="">First measure</option>';$('#st-sort').value=chosen.includes(keep)?keep:(chosen[0]||'');}
 function drawChips(){$('#st-players').innerHTML=playerChips.map((p,i)=>`<span class="st-chip"><b>${esc(p.player)}</b><small>${esc(p.teams||'')}</small><button type="button" data-remove="${i}" aria-label="Remove ${esc(p.player)}">×</button></span>`).join('')||'<span class="st-chip-empty">No player filter: everyone in the dataset</span>';}
 function addPlayer(text){const name=String(text||'').trim();if(!name)return false;const gender=seg('st-gender');const p=players.find(x=>x.choice===name&&x.gender===gender)||players.find(x=>x.player===name&&x.gender===gender)||players.find(x=>x.player.toLowerCase()===name.toLowerCase()&&x.gender===gender);if(!p){$('#studio-status').textContent='Pick a player from the suggestions for the selected gender.';return false;}if(playerChips.length>=6){$('#studio-status').textContent='Six players is the limit for one canvas.';return false;}if(!playerChips.some(x=>x.player_id===p.player_id))playerChips.push(p);drawChips();return true;}
 function preset(t,run=true){template=presets[t]?t:'custom';const p=presets[template];
  $$('[data-template]').forEach(b=>{const on=b.dataset.template===template;b.classList.toggle('active',on);b.setAttribute('aria-pressed',String(on));});
  $('#design-title').value='';$('#design-subtitle').value='';$('#st-dataset').value=p.dataset;setSeg('st-format',p.format||'');
  playerChips=[];for(const name of p.players||[])addPlayer(name);drawChips();
  for(const id of ['st-team','st-opponent','st-venue','st-position','st-innings','st-from','st-to'])$('#'+id).value='';
  $('#st-minimum').value=p.minimum||'0';$('#st-limit').value=p.limit||'12';$('#design-type').value=p.type||'auto';
  fields();
  $$('#st-metrics button').forEach(b=>b.setAttribute('aria-pressed',String(p.metrics.split(',').includes(b.dataset.metric))));
  if(!metricsChosen().length)$('#st-metrics button')?.setAttribute('aria-pressed','true');
  sortOptions();$('#st-group').value=p.group;
  if(p.year==='latest')$('#st-from').value=$('#st-to').value=String(manifest.match_date_to).slice(0,4);
  if(p.venue==='first')$('#st-venue').selectedIndex=1;
  if(template==='team')$('#st-team').selectedIndex=1;
  if(run)render();
 }
 function restore(saved){saved=core.clean(saved);preset(saved.template||'profile',false);
  if(['Men','Women'].includes(saved.gender))setSeg('st-gender',saved.gender);
  if(core.allowed[saved.dataset])$('#st-dataset').value=saved.dataset;
  setSeg('st-format',['','Test','ODI','T20I'].includes(saved.format)?saved.format:'');
  fields();
  playerChips=[];for(const id of core.idList(saved.players)){const p=players.find(x=>x.player_id===id);if(p)playerChips.push(p);}drawChips();
  if(saved.metrics){const want=saved.metrics.split(',');$$('#st-metrics button').forEach(b=>b.setAttribute('aria-pressed',String(want.includes(b.dataset.metric))));}
  sortOptions();
  for(const [key,id] of Object.entries(ids))if(saved[key]!=null&&key!=='dataset')$('#'+id).value=saved[key];
 }
 const setupLink=()=>location.origin+location.pathname+'#'+encodeURIComponent(JSON.stringify(state()));
 function disableExport(on){for(const id of ['download-card','download-svg','download-data','full-preview'])$('#'+id).disabled=on||!!photos?.busy();}
 async function render(){const token=++generation;disableExport(true);$('#studio-status').textContent='Querying…';$('#story-card').setAttribute('aria-busy','true');
  try{const s=state();
   if(s.from&&s.to&&Number(s.from)>Number(s.to))throw new Error('Start year must be no later than end year.');
   let sql;
   if(s.template==='match'){sql=`SELECT date,team_1,team_2,format,gender,winner,result,venue,margin_runs,margin_wickets FROM ${source('matches')} WHERE match_id=${core.quote(s.match)}`;}
   else if(s.template==='team'){if(!s.team)throw new Error('Choose a team.');sql=`SELECT date,team_1,team_2,winner,result,format,venue FROM ${source('matches')} WHERE (team_1=${core.quote(s.team)} OR team_2=${core.quote(s.team)}) AND gender=${core.quote(s.gender)}${s.format?' AND format='+core.quote(s.format):''}${s.from?' AND year>='+Number(s.from):''}${s.to?' AND year<='+Number(s.to):''} ORDER BY date DESC LIMIT ${Math.min(200,Math.max(1,Number(s.limit)||12))}`;}
   else sql=core.sql(s,source(s.dataset));
   $('#sql').textContent=sql;const result=await query(sql);if(token!==generation)return;
   rows=result;current=s;page=0;
   await photos.setPlayers(playerChips.slice(0,2).map(p=>({id:p.player_id,name:p.player})));if(token!==generation)return;
   $('#studio-status').textContent=result.length?`${result.length} rows · ${s.gender} · ${s.format||'all formats'}${playerChips.length?' · '+playerChips.length+' player'+(playerChips.length>1?'s':''):''}`:'No records match this selection. Widen the filters.';
   paint();disableExport(!rows.length);history.replaceState(null,'',setupLink());
  }catch(e){if(token!==generation)return;rows=[];current=null;svgText='';$('#story-card').innerHTML='<p class="studio-empty">'+esc(e.message)+'</p>';$('#studio-result-table').textContent='';$('#studio-status').textContent=e.message;}
  finally{if(token===generation)$('#story-card').setAttribute('aria-busy','false');}
 }
 const measureList=()=>current?core.measures(current).list.filter(m=>rows.length&&('m_'+m) in rows[0]):[];
 function autoType(){const m=measureList();if(current.template==='match')return 'card';if(current.template==='team')return 'table';if(current.group==='year')return m.length>1?'multiples':'line';if(m.length>=3&&rows.length<=8)return 'grouped';return 'bar';}
 function baseTitle(){if(!current)return '';const names=playerChips.map(p=>p.player);const m=measureList().map(x=>core.metrics[x]);if(current.template==='match'&&rows[0])return `${rows[0].team_1} v ${rows[0].team_2}`;if(current.template==='team')return `${current.team}: recent results`;if(names.length===1)return `${names[0]}: ${m.slice(0,3).join(', ')} by ${(GROUP_LABEL[current.group]||current.group).toLowerCase()}`;if(names.length>1)return names.join(' v ');return `${m[0]||'Records'} by ${(GROUP_LABEL[current.group]||current.group).toLowerCase()}`;}
 function paint(){if(!current||!rows.length){$('#story-card').innerHTML='<p class="studio-empty">No matching records. Widen your selection.</p>';$('#studio-result-table').textContent='';return;}
  const design=state(),size={landscape:[1200,675],square:[1080,1080],portrait:[1080,1920]}[design.size]||[1200,675],W=size[0],H=size[1];
  const pal=PALETTES[design.theme]||PALETTES.wicket,{bg,panel,ink,muted,line}=pal;const accent=/^#[0-9a-f]{6}$/i.test(design.accent)?design.accent:pal.series[0];const series=[accent,...pal.series.filter(c=>c.toLowerCase()!==accent.toLowerCase())];
  const cardPhotos=photos?.visible()||[],measures=measureList(),mode=design.type==='auto'?autoType():design.type;
  const text=(x,y,str,font=20,color=ink,anchor='start',weight=400)=>`<text x="${x}" y="${y}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="${font}" font-weight="${weight}" fill="${color}" text-anchor="${anchor}">${esc(str)}</text>`;
  const wrap=(str,max)=>{const words=String(str).split(/\s+/),out=[''];for(const w of words){if(out[out.length-1].length+w.length>max)out.push(w);else if(out[out.length-1])out[out.length-1]+=' ';out[out.length-1]+=w;}return out;};
  const perPage=mode==='table'?(design.size==='portrait'?30:16):mode==='grouped'?(design.size==='portrait'?12:8):mode==='multiples'?(design.size==='portrait'?24:14):design.size==='portrait'?22:design.size==='square'?14:(cardPhotos.length?7:10);
  const data=current.template==='team'?rows.map(r=>({label:r.date+' · '+(r.team_1===current.team?r.team_2:r.team_1),value:r.winner?(r.winner===current.team?'Won':'Lost'):(r.result||'No result'),sample:1,_venue:r.venue})):rows;
  const pages=Math.max(1,Math.ceil(data.length/perPage));page=Math.max(0,Math.min(page,pages-1));const subset=data.slice(page*perPage,(page+1)*perPage);
  const title=design.title||baseTitle();
  const scope=current.dataset==='careers'?'Official career snapshot':current.dataset==='matches'?'International match archive':'Recorded innings';
  const scopeText=[scope,current.gender,current.format||'all formats',current.from||current.to?[current.from||'start',current.to||'latest'].join(' to '):'',current.opponent?'v '+current.opponent:'',current.team?'Team '+current.team:'',current.venue?current.venue:'',current.position?'No. '+current.position:'',Number(current.minimum)>0?`min ${current.minimum} matches`:'',pages>1?`page ${page+1} of ${pages}`:''].filter(Boolean).join(' · ');
  let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(title+' · '+scopeText)}"><rect width="${W}" height="${H}" fill="${bg}"/><rect width="${W}" height="6" fill="${accent}"/>`;
  svg+=text(56,58,'CRICKRIDA',15,accent,'start',800)+text(W-56,58,scope.toUpperCase(),12,muted,'end',700);
  const photoWidth=cardPhotos.length?cardPhotos.length*172:0;let top=118;
  for(const l of wrap(title,Math.min(46,Math.floor((W-140-photoWidth)/20))).slice(0,2)){svg+=text(56,top,l,38,ink,'start',800);top+=44;}
  if(design.subtitle)for(const l of wrap(design.subtitle,Math.min(90,Math.floor((W-140-photoWidth)/10))).slice(0,2)){svg+=text(56,top-6,l,18,muted);top+=24;}
  cardPhotos.forEach((photo,i)=>{const x=W-56-(cardPhotos.length-i)*172+16;svg+=`<defs><clipPath id="photo-${i}"><rect x="${x}" y="86" width="156" height="180" rx="14"/></clipPath></defs><image href="${esc(photo.uri)}" x="${x}" y="86" width="156" height="180" preserveAspectRatio="xMidYMin slice" clip-path="url(#photo-${i})"><title>${esc(photo.name||'Card photo')}</title></image>`;if(playerChips.length>1)wrap(photo.name,20).slice(0,2).forEach((l,j)=>{svg+=text(x+78,286+j*16,l,12,muted,'middle');});});
  if(cardPhotos.length)top=Math.max(top,playerChips.length>1?318:290);
  top+=12;const bottom=H-96,space=bottom-top;
  const fmtVal=(m,v)=>v==null?'-':core.units[m]?Number(v).toFixed(2):num(v);
  const scaled=(m)=>Math.max(...subset.map(r=>Number(r['m_'+m])||0),core.lower.has(m)?0:1)||1;
  if(mode==='card'){
   const r=rows[0]||{};svg+=`<rect x="56" y="${top}" width="${W-112}" height="${Math.min(space,340)}" rx="20" fill="${panel}"/>`;
   svg+=text(W/2,top+62,(r.format||'International')+' · '+(r.gender||current.gender||''),20,muted,'middle')+text(W/2,top+128,(r.team_1||'')+' v '+(r.team_2||''),44,ink,'middle',800)+text(W/2,top+172,r.date||'',20,muted,'middle')+text(W/2,top+230,r.winner?r.winner+' won'+(r.margin_runs?' by '+r.margin_runs+' runs':r.margin_wickets?' by '+r.margin_wickets+' wickets':''):(r.result||'Result unrecorded'),28,accent,'middle',800)+text(W/2,top+276,r.venue||'',18,muted,'middle');
  }else if(mode==='number'){
   const m=measures[0],r=subset[0];svg+=text(W/2,top+space*.42,fmtVal(m,r['m_'+m]),Math.min(140,W/7),accent,'middle',800)+text(W/2,top+space*.42+54,String(r.label),28,ink,'middle',700)+text(W/2,top+space*.42+88,core.metrics[m]+(core.units[m]?' · '+core.units[m]:'')+' · '+num(r.sample)+' matches',17,muted,'middle');
   const others=measures.slice(1,5);others.forEach((k,i)=>{const cx=W/2+(i-(others.length-1)/2)*(W/(others.length+1)),y=top+space*.42+150;svg+=text(cx,y,fmtVal(k,r['m_'+k]),34,ink,'middle',800)+text(cx,y+24,core.metrics[k],13,muted,'middle');});
  }else if(mode==='table'){
   const cols=current.template==='team'?['label','value']:['label',...measures.map(m=>'m_'+m),'sample'];const names=current.template==='team'?['Match','Result']:[GROUP_LABEL[current.group]||titleCase(current.group),...measures.map(m=>core.metrics[m]),'Mat'];
   const rowH=Math.min(48,space/(subset.length+1)),firstW=Math.min(W*.4,360),colW=(W-112-firstW)/Math.max(1,cols.length-1);
   names.forEach((n,i)=>svg+=text(i?56+firstW+colW*i-4:56,top+20,n,13,muted,i?'end':'start',700));svg+=`<path d="M56 ${top+30}H${W-56}" stroke="${line}"/>`;
   subset.forEach((r,i)=>{const y=top+30+rowH*(i+.72);cols.forEach((c,j)=>{const v=c==='label'?String(r[c]??'Not recorded'):c==='sample'?num(r[c]):c==='value'?String(r[c]):fmtVal(c.slice(2),r[c]);svg+=text(j?56+firstW+colW*j-4:56,y,j?v:wrap(v,34)[0],j?18:17,j===1?ink:j?muted:ink,j?'end':'start',j===1?700:400);});svg+=`<path d="M56 ${top+30+rowH*(i+1)}H${W-56}" stroke="${line}" opacity=".6"/>`;});
  }else if(mode==='grouped'){
   const k=measures.length,groupH=Math.min(34+k*22,space/subset.length),barH=Math.min(18,(groupH-24)/k),labelW=Math.min(W*.3,300),barX=56+labelW+16,barW=W-56-barX-120;
   subset.forEach((r,i)=>{const y=top+groupH*i;svg+=text(56,y+18,wrap(String(r.label??'Not recorded'),30)[0],17,ink,'start',700)+text(56,y+34,num(r.sample)+' matches',11,muted);
    measures.forEach((m,j)=>{const v=Number(r['m_'+m]);const w=r['m_'+m]==null?0:(core.lower.has(m)?(1-(v/(scaled(m)*1.15)))*barW:v/scaled(m)*barW);const yy=y+8+j*(barH+3);svg+=`<rect x="${barX}" y="${yy}" width="${Math.max(0,w).toFixed(1)}" height="${barH}" rx="3" fill="${series[j%series.length]}"/>`;if(design.labels==='on')svg+=text(barX+Math.max(0,w)+8,yy+barH*.78,fmtVal(m,r['m_'+m]),12,ink);});});
   let lx=56;measures.forEach((m,j)=>{svg+=`<rect x="${lx}" y="${bottom-14}" width="12" height="12" rx="3" fill="${series[j%series.length]}"/>`+text(lx+18,bottom-4,core.metrics[m],12,muted);lx+=30+core.metrics[m].length*7;});
  }else if(mode==='multiples'){
   const cols=measures.length>=3?(design.size==='portrait'?1:3):measures.length,rowsN=Math.ceil(measures.length/cols),cw=(W-112-(cols-1)*24)/cols,ch=(space-(rowsN-1)*24)/rowsN;
   measures.forEach((m,mi)=>{const gx=56+(mi%cols)*(cw+24),gy=top+Math.floor(mi/cols)*(ch+24);svg+=`<rect x="${gx}" y="${gy}" width="${cw}" height="${ch}" rx="14" fill="${panel}"/>`+text(gx+16,gy+26,core.metrics[m],15,ink,'start',700)+text(gx+cw-16,gy+26,core.units[m]||'',11,muted,'end');
    const max=scaled(m),n=subset.length,inner=ch-56,barW=Math.max(3,(cw-32)/n*.62),step=(cw-32)/n,base=gy+ch-18,color=series[mi%series.length];
    subset.forEach((r,i)=>{const v=Number(r['m_'+m])||0,h=r['m_'+m]==null?0:v/max*(inner-12),x=gx+16+step*i+(step-barW)/2;svg+=`<rect x="${x.toFixed(1)}" y="${(base-h).toFixed(1)}" width="${barW.toFixed(1)}" height="${h.toFixed(1)}" rx="2" fill="${color}"/>`;if(design.labels==='on'&&n<=14)svg+=text(x+barW/2,base-h-4,fmtVal(m,r['m_'+m]),10,ink,'middle');if(i%Math.max(1,Math.ceil(n/6))===0||i===n-1)svg+=text(x+barW/2,base+13,String(r.label).slice(0,12),10,muted,'middle');});});
  }else if(mode==='column'||mode==='line'){
   const m=measures[0],max=scaled(m),left=100,base=bottom-48,plotH=base-top-28,step=(W-160)/subset.length;
   for(let i=0;i<=4;i++){const y=base-plotH*i/4;svg+=`<path d="M${left} ${y}H${W-56}" stroke="${line}"/>`+text(left-10,y+5,fmtVal(m,max*i/4),13,muted,'end');}
   let prev=null;subset.forEach((r,i)=>{const x=left+step*(i+.5),v=Number(r['m_'+m])||0,y=base-v/max*plotH;if(r['m_'+m]!=null){if(mode==='column')svg+=`<rect x="${x-step*.3}" y="${y}" width="${step*.6}" height="${base-y}" rx="4" fill="${accent}"/>`;else{if(prev)svg+=`<path d="M${prev.x} ${prev.y}L${x} ${y}" stroke="${accent}" stroke-width="4" stroke-linecap="round"/>`;svg+=`<circle cx="${x}" cy="${y}" r="6" fill="${bg}" stroke="${accent}" stroke-width="3"/>`;prev={x,y};}}else prev=null;
    if(design.labels==='on'&&subset.length<=16)svg+=text(x,y-12,fmtVal(m,r['m_'+m]),15,ink,'middle',700);const label=String(r.label??'Not recorded');svg+=text(x,base+22,label.length>12?label.slice(0,11)+'…':label,13,muted,'middle');});
   svg+=text(left,top-4,core.metrics[m]+(core.units[m]?' · '+core.units[m]:''),14,muted);
  }else{
   const m=measures[0],max=scaled(m),others=measures.slice(1,4),rowH=Math.min(58,space/subset.length),labelW=Math.min(W*.3,300),valW=others.length*104+84,barX=56+labelW+16,barW=W-56-barX-valW-16;
   others.forEach((k,j)=>svg+=text(W-56-(others.length-1-j)*104,top-6,core.metrics[k],11,muted,'end',700));svg+=text(W-56-others.length*104,top-6,core.metrics[m],11,muted,'end',700);
   subset.forEach((r,i)=>{const y=top+rowH*(i+.62),v=Number(r['m_'+m])||0,w=r['m_'+m]==null?0:(core.lower.has(m)?(1-(v/(max*1.15)))*barW:v/max*barW);
    svg+=text(56,y,wrap(String(r.label??'Not recorded'),32)[0],17,ink,'start',700)+text(56,y+15,num(r.sample)+' matches',11,muted);
    svg+=`<rect x="${barX}" y="${y-13}" width="${barW}" height="18" rx="4" fill="${line}" opacity=".45"/><rect x="${barX}" y="${y-13}" width="${Math.max(0,w).toFixed(1)}" height="18" rx="4" fill="${accent}"/>`;
    svg+=text(W-56-others.length*104,y+3,fmtVal(m,r['m_'+m]),20,ink,'end',800);others.forEach((k,j)=>svg+=text(W-56-(others.length-1-j)*104,y+3,fmtVal(k,r['m_'+k]),16,muted,'end'));
    svg+=`<path d="M56 ${y+rowH*.42}H${W-56}" stroke="${line}" opacity=".5"/>`;});
  }
  const credits=cardPhotos.filter(p=>p.credit).map(p=>p.credit);if(credits.length){svg+=text(56,H-70,'Photo: '+credits.map(c=>c.author+' / '+c.license).join('; ')+' · cropped',11,muted);svg+='<metadata>'+esc(JSON.stringify(credits))+'</metadata>';}
  let foot=H-48;for(const l of wrap(scopeText,120).slice(0,1)){svg+=text(56,foot,l,13,muted);foot+=18;}
  svg+=text(56,H-22,'crickrida.com',14,muted,'start',700)+text(W-56,H-22,(current.dataset==='careers'?'Career check '+String(manifest.career_checked_at||'Unknown').slice(0,10):'Archive through '+manifest.match_date_to)+' · Cricsheet',12,muted,'end')+'</svg>';
  svgText=svg;$('#story-card').innerHTML=svg;$('#export-frame').dataset.size=design.size;
  const cols=current.template==='team'?['label','value','_venue']:Object.keys(rows[0]);const head=cols.map(k=>k==='label'?(GROUP_LABEL[current.group]||titleCase(current.group)):k==='value'?(current.template==='team'?'Result':'Sort value'):k==='sample'?'Matches':k==='_venue'?'Ground':k.startsWith('m_')?core.metrics[k.slice(2)]:titleCase(k));
  $('#studio-result-table').innerHTML=`<div class="table-wrap"><table class="score-table"><caption>${esc(scopeText)}</caption><thead><tr>${head.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${data.map(r=>`<tr>${cols.map(k=>`<td>${esc(k==='label'||k==='_venue'||typeof r[k]==='string'?r[k]:k.startsWith('m_')?fmtVal(k.slice(2),r[k]):num(r[k]))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  $('#preview-note').innerHTML=`${W} × ${H} px · ${esc(mode)} · ${esc(scopeText)}${pages>1?` <button type="button" id="visual-prev" ${page===0?'disabled':''}>Previous</button> <button type="button" id="visual-next" ${page===pages-1?'disabled':''}>Next</button>`:''}`;
  if($('#visual-prev'))$('#visual-prev').onclick=()=>{page--;paint();};if($('#visual-next'))$('#visual-next').onclick=()=>{page++;paint();};
 }
 function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);}
 async function png(){if(!svgText)return;const button=$('#download-card');button.disabled=true;try{const url=URL.createObjectURL(new Blob([svgText],{type:'image/svg+xml'})),img=new Image();try{await new Promise((resolve,reject)=>{img.onload=resolve;img.onerror=reject;img.src=url;});const canvas=document.createElement('canvas');canvas.width=img.width*2;canvas.height=img.height*2;const ctx=canvas.getContext('2d');ctx.scale(2,2);ctx.drawImage(img,0,0);const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));if(!blob)throw new Error('PNG encoding failed');download(blob,'cricket-wicket-'+template+'.png');}finally{URL.revokeObjectURL(url);}}catch(e){$('#studio-status').textContent='Could not export PNG. SVG export is available.';}finally{button.disabled=!rows.length;}}
 function csv(){if(!rows.length)return;const safe=x=>'"'+String(x??'').replace(/^[=+@-]/,"'"+'$&').replaceAll('"','""')+'"',keys=Object.keys(rows[0]);download(new Blob(['﻿'+[keys,...rows.map(r=>keys.map(k=>r[k]))].map(r=>r.map(safe).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}),'cricket-wicket-'+template+'.csv');}
 function showOut(which){$$('[data-out]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.out===which)));$$('[data-out-panel]').forEach(p=>p.hidden=p.dataset.outPanel!==which);}
 function bind(){photos=window.CWStudioImages.create({change:()=>{paint();disableExport(!rows.length);}});
  $$('[data-template]').forEach(b=>b.onclick=()=>preset(b.dataset.template));
  $('#studio-form').onsubmit=e=>{e.preventDefault();render();};
  $('#st-dataset').onchange=()=>{fields();if(!metricsChosen().length)$('#st-metrics button')?.setAttribute('aria-pressed','true');sortOptions();};
  $$('.st-seg').forEach(g=>g.addEventListener('click',e=>{const b=e.target.closest('button[data-value]');if(!b)return;$$('#'+g.id+' button').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));if(g.id==='st-gender'){playerChips=[];drawChips();}fields();}));
  $('#st-metrics').addEventListener('click',e=>{const b=e.target.closest('button[data-metric]');if(!b)return;const on=b.getAttribute('aria-pressed')==='true';if(on&&metricsChosen().length===1)return;b.setAttribute('aria-pressed',String(!on));sortOptions();});
  $('#st-player-add').onclick=()=>{if(addPlayer($('#st-player-input').value))$('#st-player-input').value='';};
  $('#st-player-input').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();if(addPlayer(e.target.value))e.target.value='';}});
  $('#st-player-input').addEventListener('change',()=>{if(addPlayer($('#st-player-input').value))$('#st-player-input').value='';});
  $('#st-players').addEventListener('click',e=>{const b=e.target.closest('[data-remove]');if(!b)return;playerChips.splice(Number(b.dataset.remove),1);drawChips();});
  Object.entries(ids).filter(([k,id])=>id.startsWith('design-')).forEach(([k,id])=>$('#'+id).oninput=()=>{paint();history.replaceState(null,'',setupLink());});
  $$('[data-out]').forEach(b=>b.onclick=()=>showOut(b.dataset.out));
  $('#full-preview').onclick=()=>{const url=URL.createObjectURL(new Blob([svgText],{type:'image/svg+xml'}));window.open(url,'_blank','noopener');setTimeout(()=>URL.revokeObjectURL(url),60000);};
  $('#download-card').onclick=png;$('#download-svg').onclick=()=>download(new Blob([svgText],{type:'image/svg+xml'}),'cricket-wicket-'+template+'.svg');$('#download-data').onclick=csv;
  $('#copy-link').onclick=async()=>{try{await navigator.clipboard.writeText(setupLink());$('#studio-status').textContent='Setup link copied.';}catch{$('#studio-status').textContent='Copy the page address to share this setup.';history.replaceState(null,'',setupLink());}};
  $('#save-design').onclick=()=>{try{localStorage.setItem('cw-studio-design',JSON.stringify(state()));$('#studio-status').textContent='Design saved on this device. Local images are not saved.';}catch{$('#studio-status').textContent='This browser could not save the design.';}};
  $('#load-design').onclick=()=>{try{const saved=JSON.parse(localStorage.getItem('cw-studio-design'));if(!saved)throw new Error();restore(saved);photos.reset();render();}catch{$('#studio-status').textContent='No valid saved design on this device.';}};
  $('#reset-design').onclick=()=>{for(const [k,v] of Object.entries({type:'auto',size:'landscape',theme:'wicket',accent:'#00e5ff',title:'',subtitle:'',labels:'on'}))$('#'+ids[k]).value=v;photos.reset();paint();};
 }
 async function boot(){try{const response=await fetch(lake+'manifest.json',{cache:'no-cache'});if(!response.ok)throw new Error('Dataset catalogue is unavailable');manifest=await response.json();if(!manifest.tables?.bowling_innings)throw new Error('The updated dataset is being published. Please retry shortly');
  const duckdb=await import('https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.33.1-dev57.0/+esm'),bundle=await duckdb.selectBundle(duckdb.getJsDelivrBundles()),worker=await duckdb.createWorker(bundle.mainWorker);db=new duckdb.AsyncDuckDB(new duckdb.ConsoleLogger(),worker);await db.instantiate(bundle.mainModule,bundle.pthreadWorker);conn=await db.connect();
  players=await query(`SELECT DISTINCT player_id,player,gender,teams FROM ${source('careers')} ORDER BY player`);players=players.map(p=>({...p,choice:p.player+' · '+p.gender+' · '+(p.teams||'')}));
  const teams=await query(`SELECT team_1 team FROM ${source('matches')} UNION SELECT team_2 FROM ${source('matches')} ORDER BY 1`),venues=await query(`SELECT venue, count(*) n FROM ${source('matches')} WHERE venue IS NOT NULL GROUP BY venue ORDER BY n DESC, venue`);
  choices('st-team',teams.map(x=>x.team),'All teams');choices('st-opponent',teams.map(x=>x.team),'All opponents');choices('st-venue',venues.map(x=>x.venue),'All grounds');
  matches=await query(`SELECT match_id,date,team_1,team_2,format,gender FROM ${source('matches')} ORDER BY date DESC`);
  $('#lake-version').textContent='Dataset '+manifest.version+' · match archive '+manifest.match_date_from+' to '+manifest.match_date_to+' · career check '+String(manifest.career_checked_at||'unrecorded').slice(0,10);
  bind();let saved;try{saved=JSON.parse(decodeURIComponent(location.hash.slice(1)));}catch{try{saved=JSON.parse(decodeURIComponent(escape(atob(location.hash.slice(1)))));}catch{}}
  if(saved)restore(saved);else preset('profile',false);
  await render();
 }catch(e){$('#studio-status').textContent='Studio could not load: '+e.message+'. Reload to retry.';}}
 addEventListener('DOMContentLoaded',boot);
})();
