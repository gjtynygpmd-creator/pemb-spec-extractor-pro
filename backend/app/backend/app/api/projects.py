from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.project import Project, UploadedFile, ExtractedField, ProcessingJob, DocumentPage, ProcessingEvent
from app.schemas.project import ProjectCreate

router = APIRouter(prefix="/projects", tags=["projects"])


def serialize_project(db: Session, p: Project):
    file_count = db.scalar(select(func.count()).select_from(UploadedFile).where(UploadedFile.project_id == p.id)) or 0
    field_count = db.scalar(select(func.count()).select_from(ExtractedField).where(ExtractedField.project_id == p.id)) or 0
    conflict_count = db.scalar(select(func.count()).select_from(ExtractedField).where(ExtractedField.project_id == p.id, ExtractedField.status == "conflict")) or 0
    page_count = db.scalar(select(func.count()).select_from(DocumentPage).where(DocumentPage.project_id == p.id)) or 0
    ocr_count = db.scalar(select(func.count()).select_from(DocumentPage).where(DocumentPage.project_id == p.id, DocumentPage.ocr_required.is_(True))) or 0
    return {
        "id": p.id, "name": p.name, "customer": p.customer, "address": p.address,
        "bid_due": p.bid_due, "status": p.status, "created_at": p.created_at,
        "updated_at": p.updated_at, "file_count": file_count,
        "field_count": field_count, "conflict_count": conflict_count,
        "page_count": page_count, "ocr_count": ocr_count,
    }


@router.post("")
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    p = Project(**payload.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return serialize_project(db, p)


@router.get("")
def list_projects(db: Session = Depends(get_db)):
    projects = db.scalars(select(Project).order_by(Project.updated_at.desc())).all()
    return {"projects": [serialize_project(db, p) for p in projects]}


@router.get("/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    return serialize_project(db, p)


@router.get("/{project_id}/workspace")
def get_project_workspace(project_id: str, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Project not found")

    files = db.scalars(select(UploadedFile).where(UploadedFile.project_id == project_id).order_by(UploadedFile.created_at.desc())).all()
    jobs = db.scalars(select(ProcessingJob).where(ProcessingJob.project_id == project_id).order_by(ProcessingJob.created_at.desc())).all()
    fields = db.scalars(select(ExtractedField).where(ExtractedField.project_id == project_id).order_by(ExtractedField.category, ExtractedField.field_name)).all()
    events = db.scalars(select(ProcessingEvent).where(ProcessingEvent.project_id == project_id).order_by(ProcessingEvent.created_at.desc()).limit(30)).all()
    page_summary = db.execute(
        select(DocumentPage.page_type, func.count(DocumentPage.id))
        .where(DocumentPage.project_id == project_id)
        .group_by(DocumentPage.page_type)
        .order_by(func.count(DocumentPage.id).desc())
    ).all()
    division_summary = db.execute(
        select(DocumentPage.spec_division, func.count(DocumentPage.id))
        .where(DocumentPage.project_id == project_id, DocumentPage.spec_division.is_not(None))
        .group_by(DocumentPage.spec_division)
        .order_by(DocumentPage.spec_division)
    ).all()

    return {
        "project": serialize_project(db, p),
        "files": [{"id": f.id, "filename": f.filename, "content_type": f.content_type, "size_bytes": f.size_bytes, "status": f.status, "created_at": f.created_at} for f in files],
        "jobs": [{"id": j.id, "status": j.status, "progress": j.progress, "stage": j.stage, "message": j.message, "error_message": j.error_message, "created_at": j.created_at, "updated_at": j.updated_at} for j in jobs],
        "fields": [{"id": f.id, "category": f.category, "field_name": f.field_name, "value": f.value, "confidence": f.confidence, "status": f.status, "source_file": f.source_file, "source_page": f.source_page, "source_sheet": f.source_sheet, "source_excerpt": f.source_excerpt} for f in fields],
        "events": [{"stage": e.stage, "progress": e.progress, "message": e.message, "created_at": e.created_at} for e in events],
        "inspection": {
            "page_types": [{"type": row[0], "count": row[1]} for row in page_summary],
            "divisions": [{"division": row[0], "count": row[1]} for row in division_summary],
        },
    }
