
const API_BASE = (window.PEMB_API_BASE || localStorage.getItem('pembApiBase') || 'http://localhost:8000').replace(/\/$/,'');
const PART_SIZE = 16 * 1024 * 1024;
let selectedFiles = [];
let totalUploaded = 0;
let activeJob = null;

const $ = id => document.getElementById(id);
const formatBytes = n => {
  const units=['B','KB','MB','GB','TB']; let i=0,x=n;
  while(x>=1024&&i<units.length-1){x/=1024;i++}
  return `${x.toFixed(i<2?1:2)} ${units[i]}`;
};
async function api(path, options={}){
  const res=await fetch(`${API_BASE}${path}`,{headers:{'Content-Type':'application/json',...(options.headers||{})},...options});
  if(!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}
async function checkApi(){
  try{await api('/health');$('apiStatus').textContent='Processing service online';$('apiStatus').className='api-status online'}
  catch{$('apiStatus').textContent='Backend not configured — demo mode available';$('apiStatus').className='api-status offline'}
}
function renderFiles(){
  $('fileList').innerHTML='';
  selectedFiles.forEach((f,i)=>{
    const row=document.createElement('div'); row.className='file-row'; row.dataset.index=i;
    row.innerHTML=`<div class="file-head"><div><div class="file-name">${f.file.name}</div><div class="file-meta">${formatBytes(f.file.size)} • ${f.file.type||'unknown type'}</div></div><button class="secondary remove" data-index="${i}">Remove</button></div><div class="progress"><div style="width:${f.progress||0}%"></div></div><div class="file-status">${f.status||'Ready'}</div>`;
    $('fileList').appendChild(row);
  });
  document.querySelectorAll('.remove').forEach(b=>b.onclick=()=>{selectedFiles.splice(+b.dataset.index,1);renderFiles();updateMetrics()});
}
function addFiles(files){
  [...files].forEach(file=>{
    const key=`${file.name}:${file.size}:${file.lastModified}`;
    if(!selectedFiles.some(x=>x.key===key)) selectedFiles.push({key,file,progress:0,status:'Ready'});
  });
  renderFiles(); updateMetrics();
}
function updateFile(index, progress, status){
  selectedFiles[index].progress=progress; selectedFiles[index].status=status; renderFiles();
}
function updateMetrics(){
  $('fileCount').textContent=selectedFiles.length;
  $('totalSize').textContent=formatBytes(selectedFiles.reduce((a,x)=>a+x.file.size,0));
  $('uploadedSize').textContent=formatBytes(totalUploaded);
}
async function uploadFileCloud(item,index,projectId){
  const file=item.file;
  const init=await api('/uploads/init',{method:'POST',body:JSON.stringify({
    project_id:projectId, filename:file.name, content_type:file.type||'application/octet-stream',
    size:file.size, part_size:PART_SIZE
  })});
  const totalParts=Math.ceil(file.size/PART_SIZE), completed=[];
  for(let part=1;part<=totalParts;part++){
    const start=(part-1)*PART_SIZE,end=Math.min(start+PART_SIZE,file.size);
    const signed=await api('/uploads/part-url',{method:'POST',body:JSON.stringify({
      upload_id:init.upload_id, object_key:init.object_key, part_number:part
    })});
    const chunk=file.slice(start,end);
    const put=await fetch(signed.url,{method:'PUT',body:chunk,headers:signed.headers||{}});
    if(!put.ok) throw new Error(`Part ${part} failed`);
    const etag=put.headers.get('etag')?.replaceAll('"','') || signed.mock_etag || `part-${part}`;
    completed.push({part_number:part,etag});
    totalUploaded += chunk.size;
    updateFile(index,Math.round(end/file.size*100),`Uploaded part ${part} of ${totalParts}`);
    updateMetrics();
  }
  await api('/uploads/complete',{method:'POST',body:JSON.stringify({
    upload_id:init.upload_id, object_key:init.object_key, parts:completed, project_id:projectId, filename:file.name
  })});
  updateFile(index,100,'Uploaded');
}
async function demoUpload(item,index){
  const file=item.file,totalParts=Math.ceil(file.size/PART_SIZE);
  for(let part=1;part<=totalParts;part++){
    await new Promise(r=>setTimeout(r,120));
    const end=Math.min(part*PART_SIZE,file.size),prev=Math.min((part-1)*PART_SIZE,file.size);
    totalUploaded += end-prev;
    updateFile(index,Math.round(end/file.size*100),`Demo upload part ${part} of ${totalParts}`);
    updateMetrics();
  }
  updateFile(index,100,'Uploaded in demo mode');
}
async function start(){
  if(!selectedFiles.length){showStatus('Select at least one file.','error');return}
  totalUploaded=0; updateMetrics(); $('jobState').textContent='Uploading'; setStage('upload');
  const mode=$('uploadMode').value, project={
    name:$('projectName').value||'Untitled PEMB Project',
    customer:$('customerName').value,address:$('projectAddress').value,bid_due:$('bidDue').value
  };
  try{
    let projectId='demo-project';
    if(mode==='cloud'){
      const created=await api('/projects',{method:'POST',body:JSON.stringify(project)});
      projectId=created.project_id;
    }
    for(let i=0;i<selectedFiles.length;i++){
      if(mode==='cloud') await uploadFileCloud(selectedFiles[i],i,projectId);
      else await demoUpload(selectedFiles[i],i);
    }
    if(mode==='cloud'){
      const job=await api('/jobs',{method:'POST',body:JSON.stringify({project_id:projectId})});
      activeJob=job.job_id; $('jobState').textContent='Queued'; pollJob(activeJob);
    }else{
      $('jobState').textContent='Demo Complete'; setStage('upload',true); setStage('classify');
      showStatus('Demo upload completed. Connect the backend and object storage to process the documents.','success');
    }
  }catch(e){console.error(e);$('jobState').textContent='Failed';showStatus(`Upload failed: ${e.message}`,'error')}
}
function setStage(name,done=false){
  document.querySelectorAll('.stage').forEach(x=>x.classList.remove('active'));
  const s=document.querySelector(`[data-stage="${name}"]`); if(s)s.classList.add(done?'done':'active');
}
function showStatus(text,type=''){const el=$('overallStatus');el.textContent=text;el.className=`analysis-status ${type}`}
async function pollJob(id){
  try{
    const j=await api(`/jobs/${id}`); $('jobState').textContent=j.status;
    const map={queued:'classify',classifying:'classify',ocr:'ocr',extracting:'extract',review_ready:'review',complete:'export'};
    if(map[j.status])setStage(map[j.status],j.status==='complete');
    if(['complete','review_ready','failed'].includes(j.status)){showStatus(j.message||`Job ${j.status}`,j.status==='failed'?'error':'success');refreshJobs();return}
    setTimeout(()=>pollJob(id),2500);
  }catch(e){showStatus(`Unable to read job status: ${e.message}`,'error')}
}
async function refreshJobs(){
  try{
    const data=await api('/jobs'); const box=$('jobs'); box.innerHTML=''; box.className='jobs';
    if(!data.jobs.length){box.textContent='No jobs found.';box.className='jobs empty';return}
    data.jobs.forEach(j=>{const c=document.createElement('div');c.className='job-card';c.innerHTML=`<div><div class="job-title">${j.project_name||j.project_id}</div><div class="job-details">${j.files||0} file(s) • ${j.created_at||''} • ${j.message||''}</div></div><div class="badge">${j.status}</div>`;box.appendChild(c)})
  }catch{$('jobs').textContent='Backend unavailable.';$('jobs').className='jobs empty'}
}
const dz=$('dropzone'),fi=$('fileInput');
fi.onchange=e=>addFiles(e.target.files);
['dragenter','dragover'].forEach(ev=>dz.addEventListener(ev,e=>{e.preventDefault();dz.classList.add('drag')}));
['dragleave','drop'].forEach(ev=>dz.addEventListener(ev,e=>{e.preventDefault();dz.classList.remove('drag')}));
dz.addEventListener('drop',e=>addFiles(e.dataTransfer.files));
$('clearFiles').onclick=()=>{selectedFiles=[];totalUploaded=0;renderFiles();updateMetrics();showStatus('')};
$('startUpload').onclick=start;$('refreshJobs').onclick=refreshJobs;
checkApi();updateMetrics();
