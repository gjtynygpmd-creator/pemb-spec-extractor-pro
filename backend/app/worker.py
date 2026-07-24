from __future__ import annotations
import logging
import os
import tempfile
import time
from datetime import datetime

import fitz
from PIL import Image
import pytesseract
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
from app.services.document_analysis import (
    classify_page, extract_fields, extract_spatial_fields, normalized_compare,
    normalize_field_value, candidate_quality, meaningful_text_score, rich_text_layer,
)
from app.services.storage import get_s3
from app.core.config import settings

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("pemb-worker")
POLL_SECONDS = int(os.getenv("WORKER_POLL_SECONDS", "8"))
OCR_TIMEOUT_SECONDS = int(os.getenv("OCR_TIMEOUT_SECONDS", "35"))
OCR_DPI = int(os.getenv("OCR_DPI", "140"))
OCR_MAX_PIXELS = int(os.getenv("OCR_MAX_PIXELS", "12000000"))
FORCE_DRAWING_OCR = os.getenv("FORCE_DRAWING_OCR", "false").lower() in {"1", "true", "yes"}



def ocr_page_text(page: fitz.Page, dpi: int | None = None) -> str:
    """OCR a low-signal PDF page with bounded CPU and memory use.

    Large architectural sheets can become 25-40 MP images at 200+ DPI and can pin a
    small Render worker for many minutes. v1.9.1 uses adaptive DPI, grayscale, a
    pixel ceiling, and a hard Tesseract timeout so one sheet can never stall a job.
    """
    target_dpi = max(96, min(int(dpi or OCR_DPI), 180))
    rect = page.rect
    est_pixels = max(1.0, (rect.width / 72 * target_dpi) * (rect.height / 72 * target_dpi))
    if est_pixels > OCR_MAX_PIXELS:
        scale = (OCR_MAX_PIXELS / est_pixels) ** 0.5
        target_dpi = max(96, int(target_dpi * scale))

    pix = page.get_pixmap(dpi=target_dpi, colorspace=fitz.csGRAY, alpha=False)
    image = Image.frombytes("L", (pix.width, pix.height), pix.samples)
    try:
        return (pytesseract.image_to_string(
            image, config="--oem 1 --psm 11", timeout=OCR_TIMEOUT_SECONDS
        ) or "").strip()
    except RuntimeError as exc:
        # pytesseract raises RuntimeError on timeout. Treat OCR as optional and let
        # native/spatial extraction continue rather than failing the whole project.
        log.warning("OCR timed out after %ss: %s", OCR_TIMEOUT_SECONDS, exc)
        return ""


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
                        # Preserve block-level reading order for schedules, notes, and dimension callouts.
                        blocks = page.get_text("blocks") or []
                        blocks_text = "\n".join(
                            str(block[4]).strip() for block in sorted(blocks, key=lambda b: (round(b[1] / 18), b[0]))
                            if len(block) > 4 and str(block[4]).strip()
                        )
                        text_score = meaningful_text_score(text)
                        is_searchable = rich_text_layer(text)
                        initial_page_type, initial_division, initial_sheet, initial_title = classify_page(text)
                        drawing_ocr_types = {
                            "structural_notes", "roof_plan", "foundation_plan", "framing_plan",
                            "floor_plan", "elevation", "wall_section", "door_schedule",
                        }
                        # OCR is now a bounded fallback, not an automatic second pass on every
                        # drawing. Rich born-digital sheets already provide text blocks and
                        # coordinates; OCRing 22x34 sheets on a small cloud CPU was the cause of
                        # jobs appearing frozen at the first drawing page.
                        low_signal = not is_searchable
                        use_ocr_assist = low_signal or (FORCE_DRAWING_OCR and initial_page_type in drawing_ocr_types)
                        searchable_pages += int(is_searchable)
                        ocr_pages += int(use_ocr_assist)

                        # Never discard a low-signal page. OCR it and combine the result with
                        # embedded text. For drawing sheets this acts as a second reading of the page.
                        ocr_text = ""
                        if use_ocr_assist:
                            try:
                                ocr_text = ocr_page_text(page)
                            except Exception as ocr_exc:
                                log.warning("OCR failed for %s page %s: %s", source.filename, index + 1, ocr_exc)
                        analysis_text = text
                        if ocr_text:
                            analysis_text = (text + "\n--- OCR ASSIST ---\n" + ocr_text).strip()

                        page_type, division, sheet_number, sheet_title = classify_page(analysis_text)
                        if page_type == "unclassified" and initial_page_type != "unclassified":
                            page_type, division, sheet_number, sheet_title = initial_page_type, initial_division, initial_sheet, initial_title
                        db.add(DocumentPage(
                            project_id=job.project_id,
                            uploaded_file_id=source.id,
                            page_number=index + 1,
                            sheet_number=sheet_number,
                            sheet_title=sheet_title,
                            page_type=page_type,
                            spec_division=division,
                            searchable_text=is_searchable,
                            ocr_required=low_signal,
                            text_length=len(analysis_text),
                            text_excerpt=analysis_text[:4000] if analysis_text else None,
                        ))

                        # Fast text/spec path plus coordinate-aware drawing path. OCR text is
                        # routed through the same value validation pipeline instead of being skipped.
                        page_candidates = extract_fields(
                            analysis_text, page_type=page_type, division=division, blocks_text=blocks_text or analysis_text
                        )
                        page_candidates.extend(extract_spatial_fields(blocks, page_type=page_type, division=division))
                        page_seen = set()
                        for candidate in page_candidates:
                            key = (candidate.get("field_name"), normalized_compare(candidate.get("value", ""), candidate.get("field_name")))
                            if key in page_seen:
                                continue
                            page_seen.add(key)
                            candidate.update({
                                "source_file": source.filename,
                                "source_page": index + 1,
                                "source_sheet": sheet_number,
                                "page_type": page_type,
                                "division": division,
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
                ranked = sorted(
                    candidates,
                    key=lambda c: (c.get("quality_score", candidate_quality(c)), c["confidence"], -len(c.get("value") or "")),
                    reverse=True,
                )
                best = ranked[0]
                best_score = best.get("quality_score", candidate_quality(best))
                # Conflict only when two clean, materially different values have comparable authority.
                # Narrative scope statements normalize to Included/Excluded/Specified and no longer conflict.
                credible = [
                    c for c in ranked
                    if c.get("quality_score", candidate_quality(c)) >= max(0.80, best_score - 0.04)
                    and c["confidence"] >= 0.80
                ]
                unique_values = {normalized_compare(c["value"], field_name) for c in credible if c.get("value")}
                status = "conflict" if len(unique_values) > 1 else "review"
                db.add(ExtractedField(
                    project_id=job.project_id,
                    category=best["category"],
                    field_name=field_name,
                    value=best["value"],
                    normalized_value=normalize_field_value(field_name, best["value"]),
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
            conflict_count = 0
            for name, items in all_candidates.items():
                if name in manual_names or not items:
                    continue
                scores = [x.get('quality_score', candidate_quality(x)) for x in items]
                best_score = max(scores)
                values = {
                    normalized_compare(x['value'], name)
                    for x in items
                    if x.get('value')
                    and x.get('quality_score', candidate_quality(x)) >= max(0.80, best_score - 0.04)
                    and x['confidence'] >= 0.80
                }
                conflict_count += int(len(values) > 1)
            job.status = "completed"
            job.stage = "completed"
            job.progress = 100
            job.completed_at = datetime.utcnow()
            job.message = (
                f"Inspected {processed_files} PDF(s), {total_pages} page(s); "
                f"{searchable_pages} rich-text, {ocr_pages} OCR-assisted; "
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
    log.info("PEMB processing worker v1.9.1 Document Intelligence Engine started; poll interval=%ss", POLL_SECONDS)
    while True:
        job_id = claim_job()
        if job_id:
            process_job(job_id)
        else:
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
