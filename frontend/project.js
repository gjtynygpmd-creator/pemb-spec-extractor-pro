
const API_BASE=(window.PEMB_API_BASE||localStorage.getItem('pembApiBase')||'https://pemb-spec-extractor-pro.onrender.com').replace(/\/$/,'');
const PROJECT_ID=new URLSearchParams(location.search).get('id');
const PART_SIZE=16*1024*1024;
let selected=[],workspace=null,pollTimer=null;
const $=id=>document.getElementById(id);
const formatBytes=n=>{const u=['B','KB','MB','GB','TB'];let i=0,x=n||0;while(x>=1024&&i<u.length-1){x/=1024;i++}return `${x.toFixed(i<2?1:2)} ${u[i]}`};
const escapeHtml=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
async function api(path,options={}){
 const r=await fetch(API_BASE+path,{headers:{'Content-Type':'application/json',...(options.headers||{})},...options});
 if(!r.ok)throw new Error(await r.text());return r.json()
}
async function loadWorkspace(){
 if(!PROJECT_ID){location.href='index.html';return}
 try{
  workspace=await api(`/projects/${PROJECT_ID}/workspace`);
  const p=workspace.project;
  $('projectTitle').textContent=p.name;$('projectSubtitle').textContent=[p.customer,p.address].filter(Boolean).join(' • ')||'PEMB estimating project';
  $('fileCount').textContent=p.file_count;$('fieldCount').textContent=p.field_count;$('conflictCount').textContent=p.conflict_count;$('projectState').textContent=p.status;$('pageCount').textContent=p.page_count||0;$('ocrCount').textContent=p.ocr_count||0;
  renderStored();renderJobs();renderFields();renderInspection();renderActivity();schedulePolling()
 }catch(e){$('uploadMessage').textContent='Unable to load project: '+e.message;$('uploadMessage').className='analysis-status error'}
}
function addFiles(files){
 [...files].forEach(file=>{const key=`${file.name}:${file.size}:${file.lastModified}`;if(!selected.some(x=>x.key===key))selected.push({key,file,progress:0,status:'Ready'})});
 renderPending()
}
function renderPending(){
 $('pendingFiles').innerHTML=selected.map((x,i)=>`<div class="file-row"><div class="file-head"><div><div class="file-name">${escapeHtml(x.file.name)}</div><div class="file-meta">${formatBytes(x.file.size)}</div></div><button class="secondary remove" data-i="${i}">Remove</button></div><div class="progress"><div style="width:${x.progress}%"></div></div><div class="file-status">${escapeHtml(x.status)}</div></div>`).join('');
 document.querySelectorAll('.remove').forEach(b=>b.onclick=()=>{selected.splice(+b.dataset.i,1);renderPending()})
}
function updatePending(i,progress,status){selected[i].progress=progress;selected[i].status=status;renderPending()}
async function uploadOne(item,i){
 const f=item.file;
 const init=await api('/uploads/init',{method:'POST',body:JSON.stringify({project_id:PROJECT_ID,filename:f.name,content_type:f.type||'application/octet-stream',size:f.size,part_size:PART_SIZE})});
 const count=Math.ceil(f.size/PART_SIZE),parts=[];
 for(let p=1;p<=count;p++){
  const start=(p-1)*PART_SIZE,end=Math.min(p*PART_SIZE,f.size);
  const signed=await api('/uploads/part-url',{method:'POST',body:JSON.stringify({upload_id:init.upload_id,object_key:init.object_key,part_number:p})});
  const response=await fetch(signed.url,{method:'PUT',body:f.slice(start,end),headers:signed.headers||{}});
  if(!response.ok)throw new Error(`Upload part ${p} failed`);
  const etag=(response.headers.get('etag')||'').replaceAll('"','');
  if(!etag)throw new Error('Cloud storage did not return an ETag. Check the R2 bucket CORS policy.');
  parts.push({part_number:p,etag});
  updatePending(i,Math.round(end/f.size*100),`Uploaded part ${p} of ${count}`)
 }
 await api('/uploads/complete',{method:'POST',body:JSON.stringify({upload_id:init.upload_id,object_key:init.object_key,project_id:PROJECT_ID,filename:f.name,content_type:f.type||'application/octet-stream',size:f.size,parts})});
 updatePending(i,100,'Upload complete')
}
async function uploadSelected(){
 if(!selected.length){show('uploadMessage','Select files first.','error');return}
 $('uploadBtn').disabled=true;
 try{
  for(let i=0;i<selected.length;i++)await uploadOne(selected[i],i);
  show('uploadMessage',`${selected.length} file(s) uploaded successfully.`,'success');
  selected=[];renderPending();await loadWorkspace()
 }catch(e){show('uploadMessage','Upload failed: '+e.message,'error')}
 $('uploadBtn').disabled=false
}
function renderStored(){
 $('storedFiles').innerHTML=workspace.files.length?workspace.files.map(f=>`<div class="stored-file"><div><strong>${escapeHtml(f.filename)}</strong><div class="file-meta">${formatBytes(f.size_bytes)} • ${escapeHtml(f.content_type||'unknown type')}</div></div><span class="badge">${escapeHtml(f.status)}</span></div>`).join(''):'<div class="muted">No files uploaded yet.</div>'
}
function renderJobs(){
 $('jobs').className='jobs';$('jobs').innerHTML=workspace.jobs.length?workspace.jobs.map(j=>`<div class="job-card"><div class="job-main"><div class="job-title">${escapeHtml(j.stage||j.status)}</div><div class="job-details">${escapeHtml(j.message||'')} • ${new Date(j.created_at).toLocaleString()}</div><div class="progress job-progress"><div style="width:${Math.max(0,Math.min(100,j.progress||0))}%"></div></div></div><div class="badge">${escapeHtml(j.status)} ${j.progress}%</div></div>`).join(''):'<div class="muted">No processing jobs yet.</div>'
}
function renderInspection(){const i=workspace.inspection||{};const parts=[];(i.page_types||[]).forEach(x=>parts.push(`<span class="summary-chip">${escapeHtml(x.type)}: <strong>${x.count}</strong></span>`));(i.divisions||[]).forEach(x=>parts.push(`<span class="summary-chip">Division ${escapeHtml(x.division)}: <strong>${x.count}</strong></span>`));$('inspectionSummary').innerHTML=parts.length?parts.join(''):'<span class="muted">Run analysis to index pages.</span>'}
function renderActivity(){const events=workspace.events||[];$('activityFeed').innerHTML=events.length?events.map(e=>`<div class="activity-item"><strong>${escapeHtml(e.stage)}</strong><span>${escapeHtml(e.message||'')}</span><small>${e.progress}% • ${new Date(e.created_at).toLocaleString()}</small></div>`).join(''):'<span class="muted">No activity yet.</span>'}
function schedulePolling(){clearTimeout(pollTimer);const active=(workspace.jobs||[]).some(j=>['queued','processing'].includes(j.status));if(active)pollTimer=setTimeout(loadWorkspace,4000)}
function renderFields(){
 $('fieldsBody').innerHTML=workspace.fields.length?workspace.fields.map(f=>`<tr><td>${escapeHtml(f.category)}</td><td><strong>${escapeHtml(f.field_name)}</strong></td><td>${escapeHtml(f.value||'')}</td><td>${f.confidence??''}</td><td>${escapeHtml([f.source_file,f.source_sheet,f.source_page?`p. ${f.source_page}`:''].filter(Boolean).join(' • '))}</td><td>${escapeHtml(f.status)}</td></tr>`).join(''):'<tr><td colspan="6" class="muted">No extracted fields yet.</td></tr>'
}
async function startAnalysis(){
 try{const j=await api('/jobs',{method:'POST',body:JSON.stringify({project_id:PROJECT_ID})});show('jobMessage','Analysis job queued successfully.','success');await loadWorkspace()}
 catch(e){show('jobMessage','Could not start analysis: '+e.message,'error')}
}
function show(id,text,type=''){const e=$(id);e.textContent=text;e.className=`analysis-status ${type}`}
const dz=$('dropzone'),fi=$('fileInput');
fi.onchange=e=>addFiles(e.target.files);
['dragenter','dragover'].forEach(ev=>dz.addEventListener(ev,e=>{e.preventDefault();dz.classList.add('drag')}));
['dragleave','drop'].forEach(ev=>dz.addEventListener(ev,e=>{e.preventDefault();dz.classList.remove('drag')}));
dz.addEventListener('drop',e=>addFiles(e.dataTransfer.files));
$('clearFiles').onclick=()=>{selected=[];renderPending()};$('uploadBtn').onclick=uploadSelected;$('refreshBtn').onclick=loadWorkspace;$('analyzeBtn').onclick=startAnalysis;
loadWorkspace();
