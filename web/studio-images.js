/* Card images live in memory only. No upload endpoint or persistent image store. */
(() => {
 'use strict';
 const MAX_BYTES=12*1024*1024,MAX_PIXELS=40000000;
 const allowed=new Set(['image/jpeg','image/png','image/webp']);
 function decode(blob){return new Promise((resolve,reject)=>{const url=URL.createObjectURL(blob),img=new Image();img.onload=()=>{URL.revokeObjectURL(url);resolve(img);};img.onerror=()=>{URL.revokeObjectURL(url);reject(new Error('This image could not be opened. Try a JPEG, PNG or WebP.'));};img.src=url;});}
 async function prepare(blob){
  if(!allowed.has(blob.type))throw new Error('Choose a JPEG, PNG or WebP image.');
  if(blob.size>MAX_BYTES)throw new Error('Choose an image smaller than 12 MB.');
  const img=await decode(blob);
  if(img.naturalWidth*img.naturalHeight>MAX_PIXELS)throw new Error('Choose an image under 40 megapixels.');
  const scale=Math.min(1,1200/Math.max(img.naturalWidth,img.naturalHeight)),canvas=document.createElement('canvas');
  canvas.width=Math.max(1,Math.round(img.naturalWidth*scale));canvas.height=Math.max(1,Math.round(img.naturalHeight*scale));
  canvas.getContext('2d').drawImage(img,0,0,canvas.width,canvas.height);
  return {uri:canvas.toDataURL('image/png'),width:canvas.width,height:canvas.height};
 }
 function create({change}){
  let catalogPromise;
  const slots=[0,1].map(i=>({id:'',name:'',asset:null,token:0,busy:false,mode:'auto',box:document.querySelector('#card-photo-'+i)}));
  const catalog=()=>catalogPromise||(catalogPromise=fetch('/data/studio-portraits.json').then(r=>{if(!r.ok)throw new Error();return r.json();}));
  function notify(){change();}
  function status(slot,message){slot.box.querySelector('[data-photo-status]').textContent=message;}
  function show(slot){const preview=slot.box.querySelector('img');preview.hidden=!slot.asset;if(slot.asset){preview.src=slot.asset.uri;preview.alt=slot.name?slot.name+' card photo':'Your card photo';}else preview.removeAttribute('src');
   const info=slot.box.querySelector('[data-photo-credit]');info.replaceChildren();if(slot.asset?.credit){const c=slot.asset.credit,details=document.createElement('details'),summary=document.createElement('summary');summary.textContent='ⓘ';summary.setAttribute('aria-label','Photo attribution');details.append(summary);const p=document.createElement('p');p.append(c.author+' · ');for(const [label,url] of [['Wikimedia Commons',c.source_url],[c.license,c.license_url]]){const a=document.createElement('a');a.textContent=label;a.href=url;a.target='_blank';a.rel='noopener';p.append(a,' · ');}p.append('Resized and cropped for this card.');details.append(p);info.append(details);}
   slot.box.querySelector('select').value=slot.mode;
  }
  async function automatic(slot){const token=++slot.token;slot.asset=null;slot.busy=true;status(slot,'Loading player photo…');show(slot);notify();
   try{if(!slot.id){status(slot,'Choose a player, or add your own card image.');return;}
    const records=await catalog(),credit=records[slot.id];if(token!==slot.token)return;
    if(!credit){status(slot,'No verified photo for this player. Add your own image.');return;}
    if(!/^\/assets\/(?:portraits|art\/players)\/[a-z0-9-]+\.webp$/.test(credit.path))throw new Error();
    const response=await fetch(credit.path);if(!response.ok)throw new Error();const asset=await prepare(await response.blob());if(token!==slot.token)return;
    slot.asset={...asset,credit};status(slot,'Player photo ready.');
   }catch{if(token===slot.token)status(slot,'Player photo unavailable. You can add your own image.');}
   finally{if(token===slot.token){slot.busy=false;show(slot);notify();}}
  }
  for(const slot of slots){
   const input=slot.box.querySelector('input[type=file]');
   slot.box.querySelector('select').onchange=()=>{const mode=slot.box.querySelector('select').value;slot.mode=mode;if(mode==='auto'){automatic(slot);return;}++slot.token;slot.busy=false;slot.asset=null;input.value='';show(slot);status(slot,mode==='none'?'Photo hidden.':'Choose an image below. It stays in this tab.');notify();};
   input.onchange=async()=>{const file=input.files[0];if(!file)return;const token=++slot.token;slot.mode='upload';slot.busy=true;slot.asset=null;show(slot);status(slot,'Preparing image in your browser…');notify();try{const asset=await prepare(file);if(token!==slot.token)return;slot.asset=asset;status(slot,'Local image ready. Not uploaded or saved.');}catch(e){if(token===slot.token)status(slot,e.message);}finally{if(token===slot.token){slot.busy=false;show(slot);notify();}input.value='';}};
   slot.box.querySelector('[data-photo-remove]').onclick=()=>{++slot.token;slot.mode='none';slot.busy=false;slot.asset=null;input.value='';show(slot);status(slot,'Photo removed from this card.');notify();};
  }
  return {
   async setPlayers(people){await Promise.all(slots.map(async(slot,i)=>{const person=people[i],id=person?.id||'';slot.box.hidden=i===1&&!person;if(slot.id===id)return;slot.id=id;slot.name=person?.name||'';slot.box.querySelector('[data-photo-name]').textContent=slot.name||'Card image';slot.box.querySelector('input').value='';slot.mode='auto';await automatic(slot);}));},
   visible(){return slots.filter(s=>!s.box.hidden&&s.asset).map(s=>({...s.asset,name:s.name}));},
   busy(){return slots.some(s=>!s.box.hidden&&s.busy);},
   reset(){for(const s of slots){s.mode='auto';s.box.querySelector('input').value='';automatic(s);}}
  };
 }
 window.CWStudioImages={create};
})();
