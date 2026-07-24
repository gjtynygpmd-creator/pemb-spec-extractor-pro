from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.project import Project, ProcessingJob, UploadedFile
from app.schemas.upload import JobCreate

router = APIRouter(prefix="/jobs", tags=["jobs"])


def serialize(j: ProcessingJob):
    return {
        "id": j.id,
        "project_id": j.project_id,
        "status": j.status,
        "progress": j.progress,
        "stage": j.stage,
        "message": j.message,
        "error_message": j.error_message,
        "attempts": j.attempts,
        "started_at": j.started_at,
        "completed_at": j.completed_at,
        "created_at": j.created_at,
        "updated_at": j.updated_at,
    }


@router.post("")
def create_job(payload: JobCreate, db: Session = Depends(get_db)):
    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    file_count = db.query(UploadedFile).filter(UploadedFile.project_id == project.id).count()
    if file_count == 0:
        raise HTTPException(400, "Upload at least one file before starting analysis")

    active = db.scalars(
        select(ProcessingJob).where(
            ProcessingJob.project_id == project.id,
            ProcessingJob.status.in_(["queued", "processing"]),
        ).order_by(ProcessingJob.created_at.desc())
    ).first()
    if active:
        return serialize(active)

    job = ProcessingJob(
        project_id=project.id,
        status="queued",
        progress=0,
        stage="queued",
        message=f"Queued {file_count} file(s) for document inspection",
    )
    db.add(job)
    project.status = "queued"
    db.commit()
    db.refresh(job)
    return serialize(job)


@router.get("/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(ProcessingJob, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return serialize(job)


@router.get("")
def list_jobs(project_id: str | None = None, db: Session = Depends(get_db)):
    query = select(ProcessingJob).order_by(ProcessingJob.created_at.desc())
    if project_id:
        query = query.where(ProcessingJob.project_id == project_id)
    jobs = db.scalars(query).all()
    return {"jobs": [serialize(j) for j in jobs]}
