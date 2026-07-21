
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.project import Project, UploadedFile, ExtractedField
from app.schemas.project import ProjectCreate

router = APIRouter(prefix="/projects", tags=["projects"])

def serialize_project(db: Session, p: Project):
    file_count = db.scalar(select(func.count()).select_from(UploadedFile).where(UploadedFile.project_id == p.id)) or 0
    field_count = db.scalar(select(func.count()).select_from(ExtractedField).where(ExtractedField.project_id == p.id)) or 0
    conflict_count = db.scalar(select(func.count()).select_from(ExtractedField).where(
        ExtractedField.project_id == p.id,
        ExtractedField.status == "conflict"
    )) or 0
    return {
        "id": p.id, "name": p.name, "customer": p.customer, "address": p.address,
        "bid_due": p.bid_due, "status": p.status, "created_at": p.created_at,
        "updated_at": p.updated_at, "file_count": file_count,
        "field_count": field_count, "conflict_count": conflict_count
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
