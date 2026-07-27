
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_db
from app.models.project import Project, UploadedFile
from app.schemas.upload import UploadInit, UploadPartUrl, UploadComplete
from app.services.storage import get_s3

router = APIRouter(prefix="/uploads", tags=["uploads"])

@router.post("/init")
def init_upload(payload: UploadInit, db: Session = Depends(get_db)):
    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    max_bytes = settings.max_file_size_gb * 1024**3
    if payload.size > max_bytes:
        raise HTTPException(413, f"File exceeds configured {settings.max_file_size_gb} GB limit")

    safe_name = payload.filename.replace("/", "_").replace("\\", "_")
    object_key = f"projects/{project.id}/source/{uuid.uuid4()}-{safe_name}"
    result = get_s3().create_multipart_upload(
        Bucket=settings.s3_bucket,
        Key=object_key,
        ContentType=payload.content_type,
        Metadata={
            "project-id": project.id,
            "original-filename": safe_name,
        },
    )
    return {
        "upload_id": result["UploadId"],
        "object_key": object_key,
        "part_size": payload.part_size,
    }

@router.post("/part-url")
def create_part_url(payload: UploadPartUrl):
    url = get_s3().generate_presigned_url(
        "upload_part",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": payload.object_key,
            "UploadId": payload.upload_id,
            "PartNumber": payload.part_number,
        },
        ExpiresIn=settings.upload_expiration_seconds,
    )
    return {"url": url, "headers": {}}

@router.post("/complete")
def complete_upload(payload: UploadComplete, db: Session = Depends(get_db)):
    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    completed_parts = [
        {"PartNumber": int(p["part_number"]), "ETag": p["etag"]}
        for p in payload.parts
    ]
    get_s3().complete_multipart_upload(
        Bucket=settings.s3_bucket,
        Key=payload.object_key,
        UploadId=payload.upload_id,
        MultipartUpload={"Parts": completed_parts},
    )

    existing = db.query(UploadedFile).filter(
        UploadedFile.object_key == payload.object_key
    ).first()
    if not existing:
        uploaded = UploadedFile(
            project_id=payload.project_id,
            filename=payload.filename,
            object_key=payload.object_key,
            content_type=payload.content_type,
            size_bytes=payload.size,
            status="uploaded",
        )
        db.add(uploaded)
        project.status = "files_uploaded"
        db.commit()
        db.refresh(uploaded)
        return {
            "id": uploaded.id,
            "status": uploaded.status,
            "filename": uploaded.filename,
            "object_key": uploaded.object_key,
        }

    return {
        "id": existing.id,
        "status": existing.status,
        "filename": existing.filename,
        "object_key": existing.object_key,
    }
