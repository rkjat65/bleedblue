/* Real dataset queries and reproducible social artwork. */
(() => {
 'use strict';
 const $=s=>document.querySelector(s), core=window.CWStudio;
 const esc=x=>String(x??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const num=x=>x==null?'—':typeof x==='string'&&!Number.isFinite(Number(x))?x:Number(x).toLocaleString('en-GB',{maximumFractionDigits:2});
 const titleCase=x=>x.replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());
 const lake=location.hostname==='127.0.0.1'||location.hostname==='localhost'?'/data/lake/':'https://pub-2deb6471d5df4274810ac4497fdf3ab2.r2.dev/';
 const files={careers:'careers',batting:'batting_innings',bowling:'bowling_innings',matches:'matches'};
 const ids={dataset:'studio-dataset',format:'studio-format',gender:'studio-gender',team:'studio-team',opponent:'studio-opponent',venue:'studio-venue',from:'studio-from',to:'studio-to',position:'studio-position',metric:'studio-metric',group:'studio-group',minimum:'studio-minimum',limit:'studio-limit',match:'studio-match',playerText:'player-one',compareText:'player-two',type:'design-type',size:'design-size',theme:'design-theme',accent:'design-accent',title:'design-title',subtitle:'design-subtitle',labels:'design-labels'};
 let photos;
 let db,conn,manifest,players=[],matches=[],rows=[],template='player',generation=0,page=0,current=null,svgText='';
 const presets={player:['careers','runs','format'],compare:['careers','runs','player'],record:['careers','runs','player'],timeline:['batting','runs','year'],batting:['batting','runs','player'],bowling:['bowling','wickets','player'],team:['matches','matches','winner'],venue:['matches','matches','format'],year:['batting','runs','player'],match:['matches','matches','format'],custom:['batting','runs','player']};
 function source(dataset){return `read_parquet(${core.quote(new URL(lake+manifest.tables[files[dataset]].file,location.href).href)})`;}
 async function query(sql){return (await conn.query(sql)).toArray().map(core.normalizeRow);}
 function state(){return {template,...Object.fromEntries(Object.entries(ids).map(([k,id])=>[k,$('#'+id).value]))};}
 function choices(id,values,all=true){$('#'+id).innerHTML=(all?'<option value="">All</option>':'')+values.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');}
 function fields(){const dataset=$('#studio-dataset').value,metric=$('#studio-metric').value,group=$('#studio-group').value;
  $('#studio-metric').innerHTML=core.allowed[dataset].map(x=>`<option value="${x}">${core.metrics[x]}</option>`).join('');
  $('#studio-group').innerHTML=core.dimensions[dataset].map(x=>`<option value="${x}">${titleCase(x)}</option>`).join('');
  if(core.allowed[dataset].includes(metric))$('#studio-metric').value=metric;if(core.dimensions[dataset].includes(group))$('#studio-group').value=group;
  const special=['match','team'].includes(template);$('#studio-dataset').disabled=special;for(const id of ['studio-metric','studio-group','studio-minimum'])$('#'+id).closest('label').hidden=special;$('#studio-limit').closest('label').hidden=template==='match';$('#studio-team').closest('label').hidden=template==='match';
  $('#player-one-field').hidden=dataset==='matches';$('#player-two-field').hidden=template!=='compare';
  $('#year-fields').hidden=dataset==='careers'||template==='match';$('#opponent-field').hidden=['careers','matches'].includes(dataset);$('#position-field').hidden=dataset!=='batting';$('#venue-field').hidden=dataset==='careers'||special;$('#match-field').hidden=template!=='match';
  $('#studio-match').innerHTML=matches.filter(m=>m.gender===$('#studio-gender').value&&(!$('#studio-format').value||m.format===$('#studio-format').value)).map(m=>`<option value="${esc(m.match_id)}">${esc(m.date+' · '+m.team_1+' v '+m.team_2+' · '+m.gender+' '+m.format)}</option>`).join('');
  $('#studio-players').innerHTML=players.filter(p=>p.gender===$('#studio-gender').value).map(p=>`<option value="${esc(p.choice)}"></option>`).join('');
 }
 function preset(t,run=true){$('#design-title').value='';$('#design-subtitle').value='';template=presets[t]?t:'custom';const [dataset,metric,group]=presets[template];$('#studio-dataset').value=dataset;fields();$('#studio-metric').value=metric;$('#studio-group').value=group;
  document.querySelectorAll('[data-template]').forEach(b=>{b.classList.toggle('active',b.dataset.template===template);b.setAttribute('aria-pressed',String(b.dataset.template===template));});
  ['studio-team','studio-opponent','studio-venue','studio-position','studio-from','studio-to'].forEach(id=>$('#'+id).value='');
  $('#player-one').value=['player','compare','timeline'].includes(template)?players.find(p=>p.gender===$('#studio-gender').value)?.choice||'':'';
  $('#player-two').value=template==='compare'?players.filter(p=>p.gender===$('#studio-gender').value)[1]?.choice||'':'';
  if(template==='year')$('#studio-from').value=$('#studio-to').value=manifest.match_date_to.slice(0,4);
  if(template==='timeline')$('#studio-limit').value='100';else $('#studio-limit').value='10';
  if(template==='team')$('#studio-team').selectedIndex=1;
  if(template==='venue')$('#studio-venue').selectedIndex=1;
  if(run)render();
 }
 function restore(saved){saved=core.clean(saved);preset(saved.template||'player',false);for(const key of ['dataset','gender'])if(saved[key]!=null)$('#'+ids[key]).value=saved[key];if(!['Men','Women'].includes($('#studio-gender').value))$('#studio-gender').value='Men';if(!core.allowed[$('#studio-dataset').value])$('#studio-dataset').value='careers';fields();for(const [key,id] of Object.entries(ids))if(saved[key]!=null&&!['dataset','gender'].includes(key))$('#'+id).value=saved[key];}
 function setupLink(){return location.origin+location.pathname+'#'+encodeURIComponent(JSON.stringify(state()));}
 function disableExport(on){for(const id of ['download-card','download-svg','download-data','full-preview'])$('#'+id).disabled=on||!!photos?.busy();}
 async function render(){if(!conn)return;const token=++generation;disableExport(true);$('#studio-status').textContent='Querying your selection…';$('#story-card').setAttribute('aria-busy','true');
  try{const s=state();for(const [field,text] of [['player','playerText'],['compare','compareText']]){const name=s[text].trim();if(name){const p=players.find(p=>p.choice===name&&p.gender===s.gender);if(!p)throw new Error('Choose a player from the suggestions for the selected gender.');s[field]=p.player_id;}}
   if(s.from&&s.to&&Number(s.from)>Number(s.to))throw new Error('Start year must be no later than end year.');
   if(s.template==='compare'&&(!s.player||!s.compare||s.player===s.compare))throw new Error('Choose two different players.');
   let sql;
   if(s.template==='match'){sql=`SELECT date,team_1,team_2,format,gender,winner,result,venue FROM ${source('matches')} WHERE match_id=${core.quote(s.match)} AND gender=${core.quote(s.gender)}${s.format?' AND format='+core.quote(s.format):''}`;}
   else if(s.template==='team'){if(!s.team)throw new Error('Choose a team.');sql=`SELECT date,team_1,team_2,winner,result,format FROM ${source('matches')} WHERE (team_1=${core.quote(s.team)} OR team_2=${core.quote(s.team)}) AND gender=${core.quote(s.gender)}${s.format?' AND format='+core.quote(s.format):''}${s.from?' AND year>='+Number(s.from):''}${s.to?' AND year<='+Number(s.to):''} ORDER BY date DESC LIMIT ${Math.min(100,Math.max(1,Number(s.limit)||10))}`;}
   else sql=core.sql(s,source(s.dataset));
   $('#sql').textContent=sql;const result=await query(sql);if(token!==generation)return;rows=result;current=s;page=0;await photos.setPlayers([s.player?{id:s.player,name:s.playerText.split(' · ')[0]}:null,...(s.template==='compare'?[{id:s.compare,name:s.compareText.split(' · ')[0]}]:[])]);if(token!==generation)return;
   $('#studio-status').textContent=result.length?`${result.length} result rows · ${s.gender} · ${s.format||'all formats'}`:'No records match this selection. Adjust the filters.';
   paint();disableExport(!rows.length);history.replaceState(null,'',setupLink());
  }catch(e){if(token!==generation)return;rows=[];current=null;svgText='';$('#story-card').innerHTML='<p class="studio-empty">'+esc(e.message)+'</p>';$('#studio-result-table').textContent='';$('#studio-status').textContent=e.message;}
  finally{if(token===generation)$('#story-card').setAttribute('aria-busy','false');}
 }
 function dataView(){if(!current)return[];if(current.template==='match')return rows.map(r=>({label:r.team_1+' v '+r.team_2,value:r.winner?r.winner+' won':r.result||'Result unrecorded',sample:1}));if(current.template==='team')return rows.map(r=>({label:r.date+' · '+(r.team_1===current.team?r.team_2:r.team_1),value:r.winner?r.winner===current.team?'Won':'Lost':r.result||'Other',sample:1}));return rows;}
 function paint(){if(!current||!rows.length){$('#story-card').innerHTML='<p class="studio-empty">No matching records. Try widening your selection.</p>';$('#studio-result-table').textContent='';return;}
  const design=state(),size={landscape:[1200,675],square:[1080,1080],portrait:[1080,1920]}[design.size]||[1200,675],W=size[0],H=size[1];
  const theme={light:['#ffffff','#10233f','#5b6c76','#e3e9f2'],navy:['#10233f','#f2f6fc','#b6c7df','#30445f'],paper:['#faf7ef','#202a35','#626973','#dfd9cb']}[design.theme]||['#fff','#10233f','#5b6c76','#e3e9f2'];const [bg,ink,muted,line]=theme,accent=design.theme==='navy'&&design.accent==='#1d4ed8'?'#79b8ff':/^#[0-9a-f]{6}$/i.test(design.accent)?design.accent:'#1d4ed8';
  const cardPhotos=photos?.visible()||[],data=dataView(),perPage=design.size==='portrait'?24:design.size==='square'?(cardPhotos.length?10:15):(cardPhotos.length?4:8),pages=Math.ceil(data.length/perPage);page=Math.max(0,Math.min(page,pages-1));const subset=data.slice(page*perPage,(page+1)*perPage);
  const metric=core.metrics[current.metric],baseTitle=current.template==='compare'?current.playerText.split(' · ')[0]+' vs '+current.compareText.split(' · ')[0]:current.playerText?current.playerText.split(' · ')[0]:current.team||current.venue||metric+' in international cricket';const title=design.title||baseTitle;
  const scope=current.dataset==='careers'?'Official career snapshot':current.dataset==='matches'?'International match archive':'Available scorecard archive';
  const scopeText=[scope,current.gender,current.format||'all formats',current.from||current.to?[current.from||'start',current.to||'latest'].join('–'):'',current.opponent?'v '+current.opponent:'',current.team?'Team: '+current.team:'',current.venue?'Venue: '+current.venue:'',current.position?'Batting position '+current.position:'',`Minimum ${current.minimum} matches`,pages>1?`Page ${page+1}/${pages}`:''].filter(Boolean).join(' · ');
  const text=(x,y,str,font=22,color=ink,anchor='start')=>`<text x="${x}" y="${y}" font-family="Arial, sans-serif" font-size="${font}" fill="${color}" text-anchor="${anchor}">${esc(str)}</text>`;
  function wrap(str,max){const words=String(str).split(/\s+/),out=[''];for(const word of words){if(out[out.length-1].length+word.length>max)out.push(word);else if(out[out.length-1])out[out.length-1]+=' ';out[out.length-1]+=word;}return out;}
  let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(title+' · '+scopeText)}"><rect width="${W}" height="${H}" fill="${bg}"/><rect width="${W}" height="8" fill="${accent}"/>`;
  svg+=text(48,55,'CRICKET WICKET',21,accent)+text(W-48,55,'INTERNATIONAL CRICKET',15,muted,'end');
  const photoWidth=cardPhotos.length?cardPhotos.length*168:0;let top=116;for(const l of wrap(title,Math.min(48,Math.floor((W-124-photoWidth)/19))).slice(0,3)){svg+=text(48,top,l,34);top+=40;}if(design.subtitle){for(const l of wrap(design.subtitle,Math.min(78,Math.floor((W-124-photoWidth)/11))).slice(0,3)){svg+=text(48,top,l,19,muted);top+=25;}}
  cardPhotos.forEach((photo,i)=>{const x=W-48-(cardPhotos.length-i)*168+18;svg+=`<defs><clipPath id="photo-${i}"><rect x="${x}" y="88" width="150" height="172" rx="10"/></clipPath></defs><image href="${esc(photo.uri)}" x="${x}" y="88" width="150" height="172" preserveAspectRatio="xMidYMin slice" clip-path="url(#photo-${i})"><title>${esc(photo.name||'Card photo')}</title></image>`;if(current.template==='compare')wrap(photo.name,21).slice(0,2).forEach((line,j)=>{svg+=text(x+75,276+j*15,line,12,muted,'middle');});});if(cardPhotos.length)top=Math.max(top,current.template==='compare'?305:280);
  const measure=current.template==='match'?'Match picture card':current.template==='team'?'Recent team results':metric+({sr:' · runs per 100 balls',econ:' · runs per 6 legal balls',bowlSr:' · legal balls per wicket',avg:' · runs per dismissal',bowlAvg:' · runs conceded per wicket'}[current.metric]||'')+' · by '+current.group;svg+=text(48,top+5,measure,18,muted);top+=35;const bottom=H-130,space=bottom-top,numeric=subset.every(r=>r.value==null||typeof r.value==='number'),mode=current.template==='match'||design.type==='card'?'card':numeric?design.type:'table',max=Math.max(1,...subset.map(r=>Number(r.value)||0));
  if(mode==='card'){
    const r=rows[0]||{};
    svg+=`<rect x="48" y="${top}" width="${W-96}" height="${Math.min(space-10,320)}" rx="18" fill="${line}" fill-opacity=".28"/>`;
    svg+=text(W/2,top+70,(r.format||'International')+' · '+(r.gender||''),22,muted,'middle');
    svg+=text(W/2,top+130,(r.team_1||'')+' v '+(r.team_2||''),40,ink,'middle');
    svg+=text(W/2,top+180,r.date||'',22,muted,'middle');
    svg+=text(W/2,top+230,r.winner?r.winner+' won':(r.result||'Result unrecorded'),28,accent,'middle');
    svg+=text(W/2,top+270,r.venue||'',18,muted,'middle');
  }else if(mode==='number'){
   svg+=text(W/2,top+space*.45,num(subset[0].value),90,accent,'middle')+text(W/2,top+space*.45+48,subset[0].label,25,ink,'middle')+text(W/2,top+space*.45+80,metric+' · '+num(subset[0].sample)+' matches',18,muted,'middle');
  }else if(mode==='column'||mode==='line'){
   const left=85,base=bottom-45,plotH=base-top-35,step=(W-150)/subset.length;
   for(let i=0;i<=4;i++){const y=base-plotH*i/4;svg+=`<path d="M${left} ${y}H${W-50}" stroke="${line}"/>`+text(left-10,y+5,num(max*i/4),16,muted,'end');}
   let previous=null;
   subset.forEach((r,i)=>{const x=left+step*(i+.5),y=base-(Number(r.value)||0)/max*plotH;if(r.value!=null){if(mode==='column')svg+=`<rect x="${x-step*.3}" y="${y}" width="${step*.6}" height="${base-y}" fill="${accent}"/>`;else{if(previous)svg+=`<path d="M${previous.x} ${previous.y}L${x} ${y}" stroke="${accent}" stroke-width="4"/>`;svg+=`<circle cx="${x}" cy="${y}" r="5" fill="${accent}"/>`;previous={x,y};}}else previous=null;
    if(design.labels==='on')svg+=text(x,y-12,num(r.value),18,ink,'middle');const label=String(r.label??'Not recorded');svg+=text(x,base+25,label.length>12?label.slice(0,11)+'…':label,14,muted,'middle');});svg+=text(50,top-7,metric,18,muted);
  }else{
   const rowH=Math.min(70,space/subset.length),barX=W*.44,barW=W*.35;
   subset.forEach((r,i)=>{const y=top+rowH*(i+.65),label=String(r.label??'Not recorded');for(const [j,l] of wrap(label,35).slice(0,2).entries())svg+=text(48,y+j*20,l,19);
    if(mode==='bar'&&r.value!=null)svg+=`<rect x="${barX}" y="${y-16}" height="18" width="${Number(r.value)/max*barW}" rx="2" fill="${accent}"/>`;
    if(mode!=='bar'||design.labels==='on')svg+=text(W-48,y,num(r.value),22,ink,'end');svg+=`<path d="M48 ${y+rowH*.45}H${W-48}" stroke="${line}"/>`;});
  }
  const credits=cardPhotos.filter(p=>p.credit).map(p=>p.credit);if(credits.length){svg+=text(48,H-104,'Photo: '+credits.map(c=>c.author+' / '+c.license).join('; ')+' · cropped',12,muted);svg+='<metadata>'+esc(JSON.stringify(credits))+'</metadata>';}
  let foot=H-85;for(const l of wrap(scopeText,110).slice(0,2)){svg+=text(48,foot,l,15,muted);foot+=19;}
  svg+=text(48,H-25,'cricket.rkjat.in',16,muted)+text(W-48,H-25,(current.dataset==='careers'?'Career check '+String(manifest.career_checked_at||'Unknown').slice(0,10):'Archive through '+manifest.match_date_to),15,muted,'end')+'</svg>';
  svgText=svg;$('#story-card').innerHTML=svg;$('#story-card').dataset.size=design.size;
  const keys=Object.keys(rows[0]);$('#studio-result-table').innerHTML=`<div class="table-wrap"><table class="score-table"><caption>${esc(scopeText)}</caption><thead><tr>${keys.map(k=>`<th>${esc(k==='value'?metric:titleCase(k))}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${keys.map(k=>`<td>${esc(k==='label'?r[k]:num(r[k]))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  $('#preview-note').innerHTML=`${W} × ${H} px · ${esc(scopeText)}. ${pages>1?`<button id="visual-prev" ${page===0?'disabled':''}>Previous visual</button> <button id="visual-next" ${page===pages-1?'disabled':''}>Next visual</button>`:''} ${design.type==='number'?'Headline shows the first result; full selection is in the data table.':''}`;
  if($('#visual-prev'))$('#visual-prev').onclick=()=>{page--;paint();};if($('#visual-next'))$('#visual-next').onclick=()=>{page++;paint();};
 }
 function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);}
 async function png(){if(!svgText)return;const button=$('#download-card');button.disabled=true;try{const url=URL.createObjectURL(new Blob([svgText],{type:'image/svg+xml'})),img=new Image();try{await new Promise((resolve,reject)=>{img.onload=resolve;img.onerror=reject;img.src=url;});const canvas=document.createElement('canvas');canvas.width=img.width;canvas.height=img.height;canvas.getContext('2d').drawImage(img,0,0);const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));if(!blob)throw new Error('PNG encoding failed');download(blob,'cricket-wicket-'+template+'.png');}finally{URL.revokeObjectURL(url);}}catch(e){$('#studio-status').textContent='Could not export PNG. SVG export is available.';}finally{button.disabled=!rows.length;}}
 function csv(){if(!rows.length)return;const safe=x=>'"'+String(x??'').replace(/^[=+@-]/,"'"+'$&').replaceAll('"','""')+'"',keys=Object.keys(rows[0]);download(new Blob(['\ufeff'+[keys,...rows.map(r=>keys.map(k=>r[k]))].map(r=>r.map(safe).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}),'cricket-wicket-'+template+'.csv');}
 function bind(){photos=window.CWStudioImages.create({change:()=>{paint();disableExport(!rows.length);}});document.querySelectorAll('[data-template]').forEach(b=>b.onclick=()=>preset(b.dataset.template));$('#studio-form').onsubmit=e=>{e.preventDefault();render();};$('#studio-dataset').onchange=fields;$('#studio-format').onchange=fields;$('#studio-gender').onchange=()=>{fields();$('#player-one').value='';$('#player-two').value='';};
  Object.entries(ids).filter(([k,id])=>id.startsWith('design-')).forEach(([k,id])=>$('#'+id).oninput=()=>{paint();history.replaceState(null,'',setupLink());});
  $('#full-preview').onclick=()=>{const url=URL.createObjectURL(new Blob([svgText],{type:'image/svg+xml'}));window.open(url,'_blank','noopener');setTimeout(()=>URL.revokeObjectURL(url),60000);};$('#download-card').onclick=png;$('#download-svg').onclick=()=>download(new Blob([svgText],{type:'image/svg+xml'}),'cricket-wicket-'+template+'.svg');$('#download-data').onclick=csv;
  $('#copy-link').onclick=async()=>{try{await navigator.clipboard.writeText(setupLink());$('#studio-status').textContent='Setup link copied.';}catch{$('#studio-status').textContent='Copy the page address to share this setup.';history.replaceState(null,'',setupLink());}};
  $('#save-design').onclick=()=>{try{localStorage.setItem('cw-studio-design',JSON.stringify(state()));$('#studio-status').textContent='Design saved. Local images are not saved; add them again when reopening.';}catch{$('#studio-status').textContent='This browser could not save the design.';}};
  $('#load-design').onclick=()=>{try{const saved=JSON.parse(localStorage.getItem('cw-studio-design'));if(!saved)throw new Error();restore(saved);photos.reset();render();}catch{$('#studio-status').textContent='No valid saved design on this device.';}};
  $('#reset-design').onclick=()=>{for(const [k,v] of Object.entries({type:'bar',size:'landscape',theme:'light',accent:'#1d4ed8',title:'',subtitle:'',labels:'on'}))$('#'+ids[k]).value=v;photos.reset();paint();};
 }
 async function boot(){try{const response=await fetch(lake+'manifest.json',{cache:'no-cache'});if(!response.ok)throw new Error('Dataset catalogue is unavailable');manifest=await response.json();if(!manifest.tables?.bowling_innings)throw new Error('The updated dataset is being published. Please retry shortly');
  const duckdb=await import('https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.33.1-dev57.0/+esm'),bundle=await duckdb.selectBundle(duckdb.getJsDelivrBundles()),worker=await duckdb.createWorker(bundle.mainWorker);db=new duckdb.AsyncDuckDB(new duckdb.ConsoleLogger(),worker);await db.instantiate(bundle.mainModule,bundle.pthreadWorker);conn=await db.connect();
  players=await query(`SELECT DISTINCT player_id,player,gender,teams FROM ${source('careers')} ORDER BY player`);players=players.map(p=>({...p,choice:p.player+' · '+p.gender+' · '+p.player_id}));
  const teams=await query(`SELECT team_1 team FROM ${source('matches')} UNION SELECT team_2 FROM ${source('matches')} ORDER BY 1`),venues=await query(`SELECT DISTINCT venue FROM ${source('matches')} WHERE venue IS NOT NULL ORDER BY venue`);
  choices('studio-team',teams.map(x=>x.team));choices('studio-opponent',teams.map(x=>x.team));choices('studio-venue',venues.map(x=>x.venue));
  matches=await query(`SELECT match_id,date,team_1,team_2,format,gender FROM ${source('matches')} ORDER BY date DESC`);$('#studio-match').innerHTML=matches.map(m=>`<option value="${esc(m.match_id)}">${esc(m.date+' · '+m.team_1+' v '+m.team_2+' · '+m.gender+' '+m.format)}</option>`).join('');
  $('#lake-version').textContent='Dataset '+manifest.version+' · match archive '+manifest.match_date_from+' to '+manifest.match_date_to+' · career check '+String(manifest.career_checked_at||'unrecorded').slice(0,10);
  bind();let saved;try{saved=JSON.parse(decodeURIComponent(location.hash.slice(1)));}catch{try{saved=JSON.parse(decodeURIComponent(escape(atob(location.hash.slice(1)))));}catch{}}
  if(saved)restore(saved);else{preset('player',false);$('#player-one').value=players.find(p=>p.player==='Sachin Tendulkar')?.choice||$('#player-one').value;}
  await render();
 }catch(e){$('#studio-status').textContent='Studio could not load: '+e.message+'. Reload to retry.';}}
 addEventListener('DOMContentLoaded',boot);
})();
