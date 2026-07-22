
from __future__ import annotations
import os, uuid
from datetime import datetime, timezone
from typing import Any
import boto3
from botocore.config import Config
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    s3_endpoint_url: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_bucket: str = "pemb-project-files"
    s3_region: str = "auto"
    cors_origins: str = "http://localhost:8888"
    max_file_size_gb: int = 20
    upload_expiration_seconds: int = 3600
settings=Settings()

app=FastAPI(title="PEMB Spec Extractor Pro API",version="0.4")
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(",")],
                   allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

projects: dict[str,dict[str,Any]]={}
jobs: dict[str,dict[str,Any]]={}

def s3():
    if not all([settings.s3_endpoint_url,settings.s3_access_key_id,settings.s3_secret_access_key]):
        raise HTTPException(503,"Object storage is not configured")
    return boto3.client("s3",endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region,config=Config(signature_version="s3v4"))

class ProjectIn(BaseModel):
    name:str
    customer:str|None=None
    address:str|None=None
    bid_due:str|None=None
class UploadInit(BaseModel):
    project_id:str
    filename:str
    content_type:str
    size:int
    part_size:int
class PartUrl(BaseModel):
    upload_id:str
    object_key:str
    part_number:int
class CompleteUpload(BaseModel):
    upload_id:str
    object_key:str
    parts:list[dict[str,Any]]
    project_id:str
    filename:str
class JobIn(BaseModel):
    project_id:str

@app.get("/health")
def health():
    return {"status":"ok","storage_configured":bool(settings.s3_endpoint_url)}

@app.post("/projects")
def create_project(p:ProjectIn):
    pid=str(uuid.uuid4())
    projects[pid]={"project_id":pid,**p.model_dump(),"files":[],"created_at":datetime.now(timezone.utc).isoformat()}
    return projects[pid]

@app.post("/uploads/init")
def init_upload(x:UploadInit):
    if x.size > settings.max_file_size_gb*1024**3:
        raise HTTPException(413,f"File exceeds configured {settings.max_file_size_gb} GB limit")
    if x.project_id not in projects: raise HTTPException(404,"Project not found")
    key=f"projects/{x.project_id}/source/{uuid.uuid4()}-{x.filename}"
    result=s3().create_multipart_upload(Bucket=settings.s3_bucket,Key=key,ContentType=x.content_type,
        Metadata={"project-id":x.project_id,"original-filename":x.filename})
    return {"upload_id":result["UploadId"],"object_key":key}

@app.post("/uploads/part-url")
def part_url(x:PartUrl):
    url=s3().generate_presigned_url("upload_part",Params={"Bucket":settings.s3_bucket,"Key":x.object_key,
        "UploadId":x.upload_id,"PartNumber":x.part_number},ExpiresIn=settings.upload_expiration_seconds)
    return {"url":url,"headers":{}}

@app.post("/uploads/complete")
def complete(x:CompleteUpload):
    parts=[{"PartNumber":int(p["part_number"]),"ETag":p["etag"]} for p in x.parts]
    s3().complete_multipart_upload(Bucket=settings.s3_bucket,Key=x.object_key,UploadId=x.upload_id,
        MultipartUpload={"Parts":parts})
    projects[x.project_id]["files"].append({"filename":x.filename,"object_key":x.object_key})
    return {"status":"complete","object_key":x.object_key}

@app.post("/jobs")
def create_job(x:JobIn):
    if x.project_id not in projects: raise HTTPException(404,"Project not found")
    jid=str(uuid.uuid4())
    jobs[jid]={"job_id":jid,"project_id":x.project_id,"project_name":projects[x.project_id]["name"],
        "status":"queued","files":len(projects[x.project_id]["files"]),
        "message":"Queued for page classification and extraction",
        "created_at":datetime.now(timezone.utc).isoformat()}
    # Queue integration point: Celery, Dramatiq, AWS SQS, Cloudflare Queues, etc.
    return jobs[jid]

@app.get("/jobs/{job_id}")
def get_job(job_id:str):
    if job_id not in jobs: raise HTTPException(404,"Job not found")
    return jobs[job_id]

@app.get("/jobs")
def list_jobs():
    return {"jobs":sorted(jobs.values(),key=lambda x:x["created_at"],reverse=True)}
