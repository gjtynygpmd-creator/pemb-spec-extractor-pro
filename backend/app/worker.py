from __future__ import annotations
import logging
import os
import tempfile
import time
from datetime import datetime

import fitz
from sqlalchemy import delete, select

from app.db.session import Base, SessionLocal, engine
from app.models.project import (
    DocumentPage,
    ExtractedField,
    ProcessingEvent,
    ProcessingJob,
    Project,
    UploadedFile,
)
from app.services.document_analysis import classify_page, extract_fields, normalized_compare
from app.services.storage import get_s3
from app.core.config import settings

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("pemb-worker")
POLL_SECONDS = int(os.getenv("WORKER_POLL_SECONDS", "8"))


def event(db, job, stage: str, progress: int, message: str):
    job.stage = stage
    job.progress = progress
    job.message = message
    db.add(ProcessingEvent(project_id=job.project_id, job_id=job.id, stage=stage, progress=progress, message=message))
    db.commit()


def claim_job():
    with SessionLocal() as db:
        job = db.scalars(
            select(ProcessingJob)
            .where(ProcessingJob.status == "queued")
            .order_by(ProcessingJob.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        ).first()
        if not job:
            return None
        job.status = "processing"
        job.stage = "claiming"
        job.progress = 1
        job.attempts = (job.attempts or 0) + 1
        job.started_at = datetime.utcnow()
        job.message = "Worker claimed analysis job"
        project = db.get(Project, job.project_id)
        if project:
            project.status = "processing"
        db.commit()
        return job.id


def process_job(job_id: str):
    s3 = get_s3()
    with SessionLocal() as db:
        job = db.get(ProcessingJob, job_id)
        project = db.get(Project, job.project_id)
        files = db.scalars(select(UploadedFile).where(UploadedFile.project_id == job.project_id)).all()
        try:
            db.execute(delete(DocumentPage).where(DocumentPage.project_id == job.project_id))
            # Preserve estimator-entered values when a project is re-analyzed.
            manual_fields = db.scalars(
                select(ExtractedField).where(
                    ExtractedField.project_id == job.project_id,
                    ExtractedField.source_file == "Manual entry",
                )
            ).all()
            manual_names = {field.field_name for field in manual_fields}
            db.execute(
                delete(ExtractedField).where(
                    ExtractedField.project_id == job.project_id,
                    ExtractedField.source_file != "Manual entry",
                )
            )
            db.commit()
            event(db, job, "downloading", 5, f"Preparing {len(files)} uploaded file(s)")

            all_candidates: dict[str, list[dict]] = {}
            total_pages = 0
            searchable_pages = 0
            ocr_pages = 0
            processed_files = 0

            for file_index, source in enumerate(files):
                if (source.content_type or "").lower() != "application/pdf" and not source.filename.lower().endswith(".pdf"):
                    source.status = "skipped_unsupported"
                    db.commit()
                    continue

                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
                    event(db, job, "downloading", 8 + int(file_index / max(len(files), 1) * 10), f"Downloading {source.filename}")
                    s3.download_fileobj(settings.s3_bucket, source.object_key, tmp)
                    tmp.flush()
                    document = fitz.open(tmp.name)
                    page_count = document.page_count
                    total_pages += page_count
                    source.status = "processing"
                    db.commit()

                    for index in range(page_count):
                        page = document.load_page(index)
                        text = page.get_text("text") or ""
                        text = text.strip()
                        is_searchable = len(text) >= 40
                        needs_ocr = not is_searchable
                        searchable_pages += int(is_searchable)
                        ocr_pages += int(needs_ocr)
                        page_type, division, sheet_number, sheet_title = classify_page(text)
                        db.add(DocumentPage(
                            project_id=job.project_id,
                            uploaded_file_id=source.id,
                            page_number=index + 1,
                            sheet_number=sheet_number,
                            sheet_title=sheet_title,
                            page_type=page_type,
                            spec_division=division,
                            searchable_text=is_searchable,
                            ocr_required=needs_ocr,
                            text_length=len(text),
                            text_excerpt=text[:4000] if text else None,
                        ))

                        if is_searchable:
                            for candidate in extract_fields(text, page_type=page_type, division=division):
                                candidate.update({
                                    "source_file": source.filename,
                                    "source_page": index + 1,
                                    "source_sheet": sheet_number,
                                })
                                all_candidates.setdefault(candidate["field_name"], []).append(candidate)

                        current_page = index + 1
                        progress = 18 + int(((file_index + current_page / max(page_count, 1)) / max(len(files), 1)) * 62)
                        if current_page == 1 or current_page % 10 == 0 or current_page == page_count:
                            event(db, job, "inspecting", min(progress, 80), f"Inspecting {source.filename}: page {current_page} of {page_count}")
                        elif current_page % 4 == 0:
                            db.commit()
                    document.close()
                    source.status = "inspected"
                    processed_files += 1
                    db.commit()

            event(db, job, "extracting_fields", 84, "Consolidating source-backed PEMB fields")
            for field_name, candidates in all_candidates.items():
                if field_name in manual_names:
                    continue
                ranked = sorted(candidates, key=lambda c: (c["confidence"], len(c.get("source_excerpt") or "")), reverse=True)
                best = ranked[0]
                # Only flag a conflict when a materially different candidate is nearly as authoritative.
                # Weak keyword hits no longer force a valid high-confidence value into conflict status.
                credible = [c for c in ranked if c["confidence"] >= max(0.78, best["confidence"] - 0.06)]
                unique_values = {normalized_compare(c["value"]) for c in credible}
                status = "conflict" if len(unique_values) > 1 else "review"
                db.add(ExtractedField(
                    project_id=job.project_id,
                    category=best["category"],
                    field_name=field_name,
                    value=best["value"],
                    normalized_value=best["value"],
                    confidence=best["confidence"],
                    status=status,
                    source_file=best["source_file"],
                    source_page=best["source_page"],
                    source_sheet=best["source_sheet"],
                    source_excerpt=best["source_excerpt"],
                ))
            db.commit()

            event(db, job, "checking_conflicts", 94, "Checking duplicate values and conflicts")
            field_count = len([name for name in all_candidates if name not in manual_names]) + len(manual_names)
            conflict_count = sum(1 for name, items in all_candidates.items() if name not in manual_names and len({normalized_compare(x['value']) for x in items if x['confidence'] >= max(0.78, max(y['confidence'] for y in items)-0.06)}) > 1)
            job.status = "completed"
            job.stage = "completed"
            job.progress = 100
            job.completed_at = datetime.utcnow()
            job.message = (
                f"Inspected {processed_files} PDF(s), {total_pages} page(s); "
                f"{searchable_pages} searchable, {ocr_pages} need OCR; "
                f"{field_count} field(s), {conflict_count} conflict(s)"
            )
            project.status = "review_ready"
            db.add(ProcessingEvent(project_id=job.project_id, job_id=job.id, stage="completed", progress=100, message=job.message))
            db.commit()
            log.info("Completed job %s", job.id)
        except Exception as exc:
            log.exception("Job %s failed", job_id)
            job.status = "failed"
            job.stage = "failed"
            job.error_message = str(exc)
            job.message = f"Analysis failed: {exc}"
            project.status = "analysis_failed"
            db.add(ProcessingEvent(project_id=job.project_id, job_id=job.id, stage="failed", progress=job.progress or 0, message=job.message))
            db.commit()


def main():
    Base.metadata.create_all(bind=engine)
    log.info("PEMB processing worker v1.6.0 Estimator Core started; poll interval=%ss", POLL_SECONDS)
    while True:
        job_id = claim_job()
        if job_id:
            process_job(job_id)
        else:
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
