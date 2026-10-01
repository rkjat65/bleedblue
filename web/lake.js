/* Shared loader for the analytics lake: DuckDB in the browser over Parquet at /lake/.
   Tools call CRLake.open() once, then CRLake.query(sql) with views named after the tables. */
(function(){
  // Same rule as Studio: R2 through Caddy on crickrida.com, the build's own copy elsewhere.
  const LAKE=location.hostname==='crickrida.com'?'/lake/':location.hostname==='localhost'||location.hostname==='127.0.0.1'?'/data/lake/':'https://pub-2deb6471d5df4274810ac4497fdf3ab2.r2.dev/';
  let ready=null,conn=null,manifest=null;
  const lit=v=>v==null?'NULL':typeof v==='number'?String(v):"'"+String(v).replace(/'/g,"''")+"'";
  async function open(tables){
    if(!ready)ready=(async()=>{
      const response=await fetch(LAKE+'manifest.json',{cache:'no-cache'});
      if(!response.ok)throw new Error('The dataset catalogue is unavailable');
      manifest=await response.json();
      const duckdb=await import('https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.33.1-dev57.0/+esm');
      const bundle=await duckdb.selectBundle(duckdb.getJsDelivrBundles());
      const worker=await duckdb.createWorker(bundle.mainWorker);
      const db=new duckdb.AsyncDuckDB(new duckdb.VoidLogger(),worker);
      await db.instantiate(bundle.mainModule,bundle.pthreadWorker);
      conn=await db.connect();
      return manifest;
    })();
    await ready;
    for(const name of tables||[]){
      const t=manifest.tables[name];
      if(!t)throw new Error('The '+name.replace(/_/g,' ')+' table is being published. Please retry shortly');
      if(!open.views.has(name)){open.views.add(name);await conn.query(`CREATE OR REPLACE VIEW ${name} AS SELECT * FROM read_parquet('${new URL(LAKE+t.file,location.href).href}')`);}
    }
    return manifest;
  }
  open.views=new Set();
  async function query(sql){
    const result=await conn.query(sql);
    // Sums arrive as 64- or 128-bit integers or decimals; the tools only need ordinary numbers.
    const numeric=result.schema.fields.filter(f=>/Int|Float|Decimal|Double/i.test(String(f.type))).map(f=>f.name);
    return result.toArray().map(row=>{const o=row.toJSON();for(const k of numeric)if(o[k]!=null)o[k]=Number(o[k]);return o;});
  }
  // Small shared helpers for the tool pages.
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num=v=>v==null||Number.isNaN(v)?'-':Number(v).toLocaleString('en-GB');
  const dec=(v,d=2)=>v==null||!Number.isFinite(v)?'-':Number(v).toFixed(d);
  const ratio=(a,b,f=1)=>b>0&&a!=null?a*f/b:null;
  function table(caption,head,rows,opts={}){
    if(!rows.length)return `<p class="tl-empty">${esc(opts.empty||'No matching records.')}</p>`;
    const th=head.map((h,i)=>`<th scope="col"${(opts.left||[]).includes(i)?' class=t':''}>${esc(h)}</th>`).join('');
    const body=rows.map(r=>'<tr>'+r.map((c,i)=>i===0?`<th scope="row">${c}</th>`:`<td${(opts.left||[]).includes(i)?' class=t':''}>${c}</td>`).join('')+'</tr>').join('');
    return `<div class="table-wrap tl-wrap" tabindex="0" role="region" aria-label="${esc(caption)}"><table class="score-table tl-table"><caption>${esc(caption)}</caption><thead><tr>${th}</tr></thead><tbody>${body}</tbody></table></div>`;
  }
  function tiles(items){const cols=items.length%4===0?4:items.length;return `<div class="tl-tiles" style="--cols:${cols}">`+items.map(([v,l],i)=>`<div${i===0?' class="lead"':''}><strong>${v}</strong><span>${esc(l)}</span></div>`).join('')+'</div>';}
  function link(path,name){return path?`<a href="${esc(path)}">${esc(name)}</a>`:esc(name);}
  // Player search box: filters a list in memory and calls onPick(player).
  function picker(input,list,players,onPick,label){
    const box=document.createElement('ul');box.className='tl-suggest';box.hidden=true;box.setAttribute('role','listbox');input.after(box);
    input.setAttribute('role','combobox');input.setAttribute('aria-autocomplete','list');input.setAttribute('aria-expanded','false');
    let items=[],active=-1;
    const close=()=>{box.hidden=true;input.setAttribute('aria-expanded','false');active=-1;};
    const show=()=>{
      const q=input.value.trim().toLowerCase();
      if(q.length<2){close();return;}
      const words=q.split(/\s+/);
      items=list().filter(p=>words.every(w=>p.search.includes(w))).slice(0,8);
      box.innerHTML=items.map((p,i)=>`<li role="option" data-i="${i}"><b>${esc(p.name)}</b><small>${esc(p.teams||'')}</small></li>`).join('')||'<li class="none">No player found</li>';
      box.hidden=false;input.setAttribute('aria-expanded','true');
    };
    input.addEventListener('input',show);
    input.addEventListener('keydown',e=>{
      if(box.hidden)return;
      const lis=[...box.querySelectorAll('li[data-i]')];
      if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();active=(active+(e.key==='ArrowDown'?1:-1)+lis.length)%lis.length;lis.forEach((li,i)=>li.classList.toggle('on',i===active));}
      else if(e.key==='Enter'){e.preventDefault();const p=items[active<0?0:active];if(p){input.value=p.name;close();onPick(p);}}
      else if(e.key==='Escape')close();
    });
    box.addEventListener('mousedown',e=>{const li=e.target.closest('li[data-i]');if(!li)return;e.preventDefault();const p=items[+li.dataset.i];input.value=p.name;close();onPick(p);});
    input.addEventListener('blur',()=>setTimeout(close,120));
  }
  function params(){return Object.fromEntries(new URLSearchParams(location.search));}
  function setParams(obj){const q=new URLSearchParams();for(const [k,v] of Object.entries(obj))if(v!==''&&v!=null)q.set(k,v);history.replaceState(null,'',location.pathname+(q.toString()?'?'+q:''));}
  function seg(el,value,onChange){
    const buttons=[...el.querySelectorAll('button[data-value]')];
    const set=v=>buttons.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.value===v)));
    set(value);
    buttons.forEach(b=>b.addEventListener('click',()=>{set(b.dataset.value);onChange(b.dataset.value);}));
    return set;
  }
  window.CRLake={open,query,lit,esc,num,dec,ratio,table,tiles,link,picker,params,setParams,seg,get manifest(){return manifest;}};
})();
