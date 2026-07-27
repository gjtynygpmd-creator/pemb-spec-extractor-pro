from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project, ExtractedField
from app.schemas.field import FieldUpdate, FieldCreate

router = APIRouter(prefix="/fields", tags=["fields"])


def serialize(field: ExtractedField):
    return {
        "id": field.id,
        "project_id": field.project_id,
        "category": field.category,
        "field_name": field.field_name,
        "value": field.value,
        "normalized_value": field.normalized_value,
        "confidence": field.confidence,
        "status": field.status,
        "source_file": field.source_file,
        "source_page": field.source_page,
        "source_sheet": field.source_sheet,
        "source_excerpt": field.source_excerpt,
        "created_at": field.created_at,
    }


@router.patch("/{field_id}")
def update_field(field_id: str, payload: FieldUpdate, db: Session = Depends(get_db)):
    field = db.get(ExtractedField, field_id)
    if not field:
        raise HTTPException(404, "Extracted field not found")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(field, key, value)
    db.commit()
    db.refresh(field)
    return serialize(field)


@router.post("/projects/{project_id}")
def create_manual_field(project_id: str, payload: FieldCreate, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    existing = db.scalars(
        select(ExtractedField).where(
            ExtractedField.project_id == project_id,
            ExtractedField.field_name == payload.field_name,
        )
    ).first()
    if existing:
        existing.value = payload.value
        existing.status = payload.status
        db.commit()
        db.refresh(existing)
        return serialize(existing)
    field = ExtractedField(
        project_id=project_id,
        category=payload.category,
        field_name=payload.field_name,
        value=payload.value,
        confidence=1.0,
        status=payload.status,
        source_file="Manual entry",
    )
    db.add(field)
    db.commit()
    db.refresh(field)
    return serialize(field)
