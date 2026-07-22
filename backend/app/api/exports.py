from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import ExtractedField, Project

router = APIRouter(prefix="/exports", tags=["exports"])


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("_") or "project"


def _load(project_id: str, db: Session):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    fields = db.scalars(
        select(ExtractedField)
        .where(ExtractedField.project_id == project_id)
        .order_by(ExtractedField.category, ExtractedField.field_name, ExtractedField.created_at)
    ).all()
    return project, fields


def _field_rows(fields):
    for f in fields:
        yield [
            f.category,
            f.field_name,
            f.value or "",
            f.normalized_value or "",
            f.status,
            round((f.confidence or 0) * 100, 1) if f.confidence is not None else "",
            f.source_file or "",
            f.source_sheet or "",
            f.source_page or "",
            f.source_excerpt or "",
        ]


def _latest_field_map(fields):
    result = {}
    priority = {"accepted": 4, "review": 3, "conflict": 2, "not_applicable": 1}
    for field in fields:
        current = result.get(field.field_name)
        if current is None or priority.get(field.status, 0) >= priority.get(current.status, 0):
            result[field.field_name] = field
    return result


@router.get("/projects/{project_id}/csv")
def export_csv(project_id: str, db: Session = Depends(get_db)):
    project, fields = _load(project_id, db)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Category", "Field", "Value", "Normalized Value", "Review Status", "Confidence %", "Source File", "Source Sheet", "Source Page", "Source Excerpt"])
    writer.writerows(_field_rows(fields))
    content = output.getvalue().encode("utf-8-sig")
    filename = f"{_safe_name(project.name)}_PEMB_Data.csv"
    return StreamingResponse(io.BytesIO(content), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/projects/{project_id}/zoho-csv")
def export_zoho_csv(project_id: str, db: Session = Depends(get_db)):
    project, fields = _load(project_id, db)
    mapping = _latest_field_map(fields)
    standard_columns = [
        "Project Name", "Customer", "Project Address", "Bid Due", "Building Width", "Building Length",
        "Eave Height", "Roof Slope", "Building Code", "Risk Category", "Basic Wind Speed",
        "Wind Exposure", "Ground Snow Load", "Roof Live Load", "Seismic Design Category",
        "Roof Panel", "Roof Panel Gauge", "Wall Panel", "Wall Panel Gauge", "Roof Insulation",
        "Wall Insulation", "Overhead Door", "Gutters", "Downspouts", "Canopies", "Louvers",
        "Paint System", "Warranty", "Estimator Notes"
    ]
    values = {
        "Project Name": project.name,
        "Customer": project.customer or "",
        "Project Address": project.address or (mapping.get("Project Address").value if mapping.get("Project Address") else ""),
        "Bid Due": project.bid_due.isoformat() if project.bid_due else "",
    }
    for column in standard_columns:
        if column not in values:
            field = mapping.get(column)
            values[column] = field.value if field and field.value else ""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=standard_columns)
    writer.writeheader()
    writer.writerow(values)
    content = output.getvalue().encode("utf-8-sig")
    filename = f"{_safe_name(project.name)}_Zoho_Import.csv"
    return StreamingResponse(io.BytesIO(content), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/projects/{project_id}/xlsx")
def export_xlsx(project_id: str, db: Session = Depends(get_db)):
    project, fields = _load(project_id, db)
    wb = Workbook()
    summary = wb.active
    summary.title = "Project Summary"
    summary.append(["PEMB Spec Extractor Pro", "v1.4.0 Production Export"])
    summary.append(["Project Name", project.name])
    summary.append(["Customer", project.customer or ""])
    summary.append(["Address", project.address or ""])
    summary.append(["Bid Due", project.bid_due.isoformat() if project.bid_due else ""])
    summary.append(["Project Status", project.status])
    summary.append(["Exported UTC", datetime.now(timezone.utc).isoformat()])
    summary.append(["Extracted Field Count", len(fields)])
    summary.column_dimensions["A"].width = 24
    summary.column_dimensions["B"].width = 70
    summary["A1"].font = Font(bold=True, size=14)
    summary["B1"].font = Font(bold=True)

    data = wb.create_sheet("Extracted Data")
    headers = ["Category", "Field", "Value", "Normalized Value", "Review Status", "Confidence %", "Source File", "Source Sheet", "Source Page", "Source Excerpt"]
    data.append(headers)
    for row in _field_rows(fields):
        data.append(row)
    for cell in data[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="F4B183")
        cell.alignment = Alignment(horizontal="center")
    data.freeze_panes = "A2"
    data.auto_filter.ref = data.dimensions
    widths = [20, 30, 32, 24, 16, 14, 36, 14, 12, 70]
    for index, width in enumerate(widths, 1):
        data.column_dimensions[get_column_letter(index)].width = width
    for row in data.iter_rows(min_row=2):
        row[2].alignment = Alignment(wrap_text=True, vertical="top")
        row[9].alignment = Alignment(wrap_text=True, vertical="top")

    zoho = wb.create_sheet("Zoho Import")
    mapping = _latest_field_map(fields)
    columns = [
        "Project Name", "Customer", "Project Address", "Bid Due", "Building Width", "Building Length",
        "Eave Height", "Roof Slope", "Building Code", "Risk Category", "Basic Wind Speed", "Wind Exposure",
        "Ground Snow Load", "Roof Live Load", "Seismic Design Category", "Roof Panel", "Roof Panel Gauge",
        "Wall Panel", "Wall Panel Gauge", "Roof Insulation", "Wall Insulation", "Overhead Door", "Gutters",
        "Downspouts", "Canopies", "Louvers", "Paint System", "Warranty", "Estimator Notes"
    ]
    zoho.append(columns)
    row = []
    for column in columns:
        if column == "Project Name": value = project.name
        elif column == "Customer": value = project.customer or ""
        elif column == "Project Address": value = project.address or (mapping.get(column).value if mapping.get(column) else "")
        elif column == "Bid Due": value = project.bid_due.isoformat() if project.bid_due else ""
        else:
            field = mapping.get(column)
            value = field.value if field and field.value else ""
        row.append(value)
    zoho.append(row)
    for cell in zoho[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="F4B183")
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    zoho.freeze_panes = "A2"
    for index in range(1, len(columns) + 1):
        zoho.column_dimensions[get_column_letter(index)].width = 22

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    filename = f"{_safe_name(project.name)}_Estimator_Workbook.xlsx"
    return StreamingResponse(buffer, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
