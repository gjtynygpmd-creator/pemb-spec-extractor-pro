
const API_BASE=(window.PEMB_API_BASE||localStorage.getItem('pembApiBase')||'https://pemb-spec-extractor-pro.onrender.com').replace(/\/$/,'');
const $=id=>document.getElementById(id);
async function api(path,options={}){
 const r=await fetch(API_BASE+path,{headers:{'Content-Type':'application/json',...(options.headers||{})},...options});
 if(!r.ok)throw new Error(await r.text());return r.json()
}
function card(p){
 return `<article class="project-card"><div class="project-card-head"><div><h3>${p.name}</h3><p>${p.customer||'No customer entered'}</p></div><span class="badge">${p.status}</span></div>
 <div class="project-stats"><span><b>${p.file_count}</b> Files</span><span><b>${p.field_count}</b> Fields</span><span><b>${p.conflict_count}</b> Conflicts</span></div>
 <div class="project-meta">${p.address||'No address'}${p.bid_due?` • Bid due ${new Date(p.bid_due).toLocaleString()}`:''}</div></article>`
}
async function load(){
 try{const d=await api('/projects');$('projectGrid').innerHTML=d.projects.length?d.projects.map(card).join(''):'<div class="muted">No projects yet.</div>'}
 catch(e){$('dashboardMessage').textContent='Could not load projects: '+e.message;$('dashboardMessage').className='analysis-status error'}
}
$('newProjectBtn').onclick=()=>$('projectForm').classList.remove('hidden');
$('cancelProject').onclick=()=>$('projectForm').classList.add('hidden');
$('saveProject').onclick=async()=>{
 try{
   await api('/projects',{method:'POST',body:JSON.stringify({
     name:$('name').value,customer:$('customer').value||null,address:$('address').value||null,
     bid_due:$('bidDue').value?new Date($('bidDue').value).toISOString():null
   })});
   $('projectForm').classList.add('hidden');$('dashboardMessage').textContent='Project created.';$('dashboardMessage').className='analysis-status success';load()
 }catch(e){$('dashboardMessage').textContent='Create failed: '+e.message;$('dashboardMessage').className='analysis-status error'}
};
load();
