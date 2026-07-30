from __future__ import annotations
import gc
import logging
import os
import tempfile
import time
from datetime import datetime, timedelta

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
from app.services.document_analysis import (
    classify_page,
    extract_fields,
    normalized_compare,
    normalize_field_value,
    candidate_quality,
    page_has_rich_text_layer,
    page_is_pemb_relevant,
)
from app.services.vision_extraction import extract_from_page, vision_available
from app.services import schema_loader
from app.services.storage import get_s3
from app.core.config import settings

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("pemb-worker")
POLL_SECONDS = int(os.getenv("WORKER_POLL_SECONDS", "8"))


def _clean_text(value):
    """Remove NUL bytes and other characters Postgres text columns reject.

    Some PDF pages return text with embedded NUL (0x00) bytes via PyMuPDF. Postgres
    text/varchar columns cannot store NUL, so inserting such text raised a DataError
    mid-job, which (without a rollback) cascaded into a worker crash loop.
    """
    if value is None:
        return value
    return value.replace("\x00", "")


def event(db, job, stage: str, progress: int, message: str):
    job.stage = stage
    job.progress = progress
    job.message = message
    db.add(ProcessingEvent(project_id=job.project_id, job_id=job.id, stage=stage, progress=progress, message=message))
    db.commit()


def heartbeat(db, job, progress: int, message: str):
    """Lightweight progress update: touches the job row (so updated_at advances as a
    liveness signal) and commits, but does not add a ProcessingEvent row. Called every
    page so the UI advances smoothly and the recovery sweep can tell the worker is alive.
    """
    job.stage = "inspecting"
    job.progress = progress
    job.message = message
    db.commit()


def recover_stuck_jobs():
    """Re-queue or fail jobs left in 'processing' by a worker that died mid-job.

    An OOM kill or platform timeout terminates the process without running the
    except handler, so the job never leaves 'processing'. Without this sweep it would
    sit at its last progress (for example 18%) forever. Here, any processing job whose
    heartbeat is older than worker_stale_seconds is retried, or marked failed once it
    has exhausted worker_max_attempts.
    """
    cutoff = datetime.utcnow() - timedelta(seconds=settings.worker_stale_seconds)
    with SessionLocal() as db:
        stale = db.scalars(
            select(ProcessingJob)
            .where(ProcessingJob.status == "processing", ProcessingJob.updated_at < cutoff)
            .with_for_update(skip_locked=True)
        ).all()
        for job in stale:
            project = db.get(Project, job.project_id)
            if (job.attempts or 0) >= settings.worker_max_attempts:
                job.status = "failed"
                job.stage = "failed"
                job.error_message = (
                    "Worker stopped responding mid-analysis (likely out of memory on a "
                    "large drawing set). Try a smaller upload or a larger worker plan."
                )
                job.message = job.error_message
                if project:
                    project.status = "analysis_failed"
                db.add(ProcessingEvent(
                    project_id=job.project_id, job_id=job.id, stage="failed",
                    progress=job.progress or 0, message=job.message,
                ))
                log.warning("Job %s failed after %s attempt(s): stale/stuck", job.id, job.attempts)
            else:
                job.status = "queued"
                job.stage = "requeued"
                job.message = "Recovered a stalled analysis job; retrying"
                if project:
                    project.status = "processing"
                log.warning("Job %s re-queued after stall (attempt %s)", job.id, job.attempts)
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


# Project-identity fields that should prefer the earliest (cover/title) page, since
# later title blocks on a large set usually carry a consultant's own name and address.
_IDENTITY_PAGE_PREF = {"Customer", "Project", "Project Address"}


def _has_real_conflict(normalized_values) -> bool:
    """True only if two values genuinely disagree. Values where one contains the other
    after normalization (e.g. "clearspan" vs "clearspanrigidframe", "24ga" vs "24") are
    treated as agreement, not a conflict. This stops the regex and vision paths from
    flagging the same fact as a conflict just because one is more verbose."""
    vals = [v for v in normalized_values if v]
    for i in range(len(vals)):
        for j in range(i + 1, len(vals)):
            a, b = vals[i], vals[j]
            if a not in b and b not in a:
                return True
    return False


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
            vision_pages = 0
            vision_calls = 0
            ocr_pages = 0
            processed_files = 0
            vision_ready = vision_available()
            event(
                db, job, "downloading", 6,
                "Vision extraction is available" if vision_ready
                else "Vision extraction is off (no API key or disabled); drawings will be flagged for review",
            )

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
                        current_page = index + 1
                        try:
                            page = document.load_page(index)
                            text = _clean_text(page.get_text("text")) or ""
                            text = text.strip()
                            # Cap pathological pages so regex and memory can't spike.
                            if len(text) > settings.page_text_char_cap:
                                text = text[: settings.page_text_char_cap]
                            # Preserve block-level reading order for schedules, notes, and dimension callouts.
                            blocks = page.get_text("blocks") or []
                            blocks_text = _clean_text("\n".join(
                                str(block[4]).strip() for block in sorted(blocks, key=lambda b: (round(b[1] / 18), b[0]))
                                if len(block) > 4 and str(block[4]).strip()
                            ))
                            if len(blocks_text) > settings.page_text_char_cap:
                                blocks_text = blocks_text[: settings.page_text_char_cap]
                            page_type, division, sheet_number, sheet_title = classify_page(text)
                            has_rich_text = page_has_rich_text_layer(
                                text,
                                settings.text_layer_min_chars,
                                settings.text_layer_min_labels,
                            )

                            # Routing:
                            #   rich text layer  -> fast regex path (spec manuals, structural notes)
                            #   otherwise        -> vision path (drawings, scanned, image-only)
                            #   vision unusable  -> flag for review, never silently drop
                            # PEMB-relevant pages are guaranteed a vision read regardless of
                            # position, so a design-criteria sheet late in a large set is not
                            # starved by the per-job budget being spent on earlier pages.
                            relevant = page_is_pemb_relevant(text)
                            vision_allowed = vision_ready and (
                                relevant or vision_calls < settings.vision_max_pages_per_job
                            )
                            page_candidates: list[dict] = []
                            if has_rich_text:
                                extraction_method = "text"
                                searchable_pages += 1
                                page_candidates = extract_fields(
                                    text, page_type=page_type, division=division, blocks_text=blocks_text
                                )
                                # On off-topic pages, drop bare accessory presence hits
                                # (e.g. "gutters, downspouts" appearing in a cleaning
                                # paragraph) that would otherwise post a spurious field.
                                if not relevant:
                                    page_candidates = [
                                        c for c in page_candidates
                                        if not (c.get("category") == "Openings & Accessories"
                                                and c.get("value") in ("Specified", "Included", "Excluded"))
                                    ]
                                # Regex covers only the core fields. Supplement with vision so
                                # the many schema fields without regex rules are also captured.
                                if settings.vision_supplements_text and vision_allowed:
                                    vision_calls += 1
                                    vsup = extract_from_page(page)
                                    if vsup.used and vsup.candidates:
                                        extraction_method = "text+vision"
                                        vision_pages += 1
                                        page_candidates = page_candidates + vsup.candidates
                            elif vision_allowed:
                                vision_calls += 1
                                vision = extract_from_page(page)
                                if vision.used and vision.candidates:
                                    extraction_method = "vision"
                                    vision_pages += 1
                                    page_candidates = vision.candidates
                                else:
                                    extraction_method = "no_fields"
                                    ocr_pages += 1
                            else:
                                extraction_method = "no_fields"
                                ocr_pages += 1

                            db.add(DocumentPage(
                                project_id=job.project_id,
                                uploaded_file_id=source.id,
                                page_number=current_page,
                                sheet_number=sheet_number,
                                sheet_title=sheet_title,
                                page_type=page_type,
                                spec_division=division,
                                searchable_text=has_rich_text,
                                ocr_required=(extraction_method == "no_fields"),
                                text_length=len(text),
                                text_excerpt=_clean_text(text[:4000]) if text else None,
                            ))

                            for candidate in page_candidates:
                                # Reconcile to the canonical schema so text-path and
                                # vision-path results merge under one field name/category.
                                fld = schema_loader.resolve(candidate.get("field_name", ""))
                                if fld:
                                    candidate["field_name"] = fld.name
                                    candidate["category"] = fld.category
                                candidate.update({
                                    "source_file": source.filename,
                                    "source_page": current_page,
                                    "source_sheet": sheet_number,
                                })
                                all_candidates.setdefault(candidate["field_name"], []).append(candidate)
                        except Exception as page_exc:
                            # Isolate per-page failures: record the page and continue rather
                            # than letting one bad sheet abort the whole job.
                            log.warning("Page %s of %s failed: %s", current_page, source.filename, page_exc)
                            db.add(DocumentPage(
                                project_id=job.project_id,
                                uploaded_file_id=source.id,
                                page_number=current_page,
                                page_type="error",
                                searchable_text=False,
                                ocr_required=True,
                                text_length=0,
                                text_excerpt=None,
                            ))
                            ocr_pages += 1
                        finally:
                            page = None

                        progress = 18 + int(((file_index + current_page / max(page_count, 1)) / max(len(files), 1)) * 62)
                        # Heartbeat every page (smooth progress + liveness); full event every 10.
                        if current_page == 1 or current_page % 10 == 0 or current_page == page_count:
                            event(db, job, "inspecting", min(progress, 80), f"Inspecting {source.filename}: page {current_page} of {page_count}")
                        else:
                            heartbeat(db, job, min(progress, 80), f"Inspecting {source.filename}: page {current_page} of {page_count}")
                        if current_page % 25 == 0:
                            gc.collect()
                    document.close()
                    source.status = "inspected"
                    processed_files += 1
                    db.commit()

            event(db, job, "extracting_fields", 84, "Consolidating source-backed PEMB fields")
            # Compute Total Square Feet from width x length when both are known. Vision
            # occasionally misreads an unrelated large number as the area (e.g. 257,025 sf
            # for a 71 x 134 building); the footprint from the dimensions is authoritative.
            def _feet_val(v):
                import re as _re
                if not v:
                    return None
                m = _re.search(r"(\d+(?:\.\d+)?)\s*(?:'|ft)?\s*[-\s]?\s*(\d+(?:\.\d+)?)?\s*(?:\"|in)?", str(v))
                if not m:
                    return None
                try:
                    ft = float(m.group(1)); inch = float(m.group(2)) if m.group(2) else 0.0
                    return ft + inch / 12.0
                except ValueError:
                    return None
            try:
                w_c = (all_candidates.get("Building Width") or [None])[0]
                l_c = (all_candidates.get("Building Length") or [None])[0]
                if w_c and l_c:
                    w = _feet_val(w_c["value"]); l = _feet_val(l_c["value"])
                    if w and l and w * l > 0:
                        sf = round(w * l)
                        all_candidates["Total Square Feet"] = [{
                            "category": "Building Geometry", "field_name": "Total Square Feet",
                            "value": f"{sf:,} sf", "normalized_value": f"{sf:,} sf",
                            "confidence": 0.9, "match_method": "computed",
                            "source_excerpt": f"Computed from {w_c['value']} x {l_c['value']}",
                            "source_file": w_c.get("source_file"), "source_page": w_c.get("source_page"),
                            "source_sheet": w_c.get("source_sheet"),
                        }]
            except Exception:
                pass

            # Drop generic regex fields when the specific schema fields are present, so a
            # sheet with BSW/FSW eave heights or front/back slopes doesn't also list a
            # redundant generic "Eave Height" / "Roof Slope" row.
            if any(k in all_candidates for k in ("BSW Eave Height", "FSW Eave Height")):
                all_candidates.pop("Eave Height", None)
            if any(k in all_candidates for k in ("Roof Slope - Front", "Roof Slope - Back")):
                all_candidates.pop("Roof Slope", None)

            for field_name, candidates in all_candidates.items():
                if field_name in manual_names:
                    continue
                # Project-identity fields live on cover/title sheets near the front. On a
                # large multi-firm set the same field appears in many title blocks (often
                # a design firm's name/address). Among credible candidates, prefer the one
                # from the earliest page, which is typically the project cover rather than a
                # later consultant's stamp.
                if field_name in _IDENTITY_PAGE_PREF:
                    def _key(c):
                        q = c.get("quality_score", candidate_quality(c))
                        credible = c["confidence"] >= 0.80
                        page = c.get("source_page") or 10_000
                        # credible-first, then earliest page, then quality/confidence
                        return (1 if credible else 0, -page if credible else 0, q, c["confidence"])
                    ranked = sorted(candidates, key=_key, reverse=True)
                else:
                    ranked = sorted(
                        candidates,
                        key=lambda c: (c.get("quality_score", candidate_quality(c)), c["confidence"], -len(c.get("value") or "")),
                        reverse=True,
                    )
                best = ranked[0]
                best_score = best.get("quality_score", candidate_quality(best))
                # Conflict only when two clean values genuinely disagree (neither contains
                # the other after normalization) with comparable authority.
                credible = [
                    c for c in ranked
                    if c.get("quality_score", candidate_quality(c)) >= max(0.80, best_score - 0.04)
                    and c["confidence"] >= 0.80
                ]
                unique_values = {normalized_compare(c["value"], field_name) for c in credible if c.get("value")}
                status = "conflict" if _has_real_conflict(unique_values) else "review"
                db.add(ExtractedField(
                    project_id=job.project_id,
                    category=best["category"],
                    field_name=field_name,
                    value=_clean_text(best["value"]),
                    normalized_value=_clean_text(normalize_field_value(field_name, best["value"])),
                    confidence=best["confidence"],
                    status=status,
                    source_file=best["source_file"],
                    source_page=best["source_page"],
                    source_sheet=_clean_text(best.get("source_sheet")),
                    source_excerpt=_clean_text(best["source_excerpt"]),
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
                conflict_count += int(_has_real_conflict(values))
            job.status = "completed"
            job.stage = "completed"
            job.progress = 100
            job.completed_at = datetime.utcnow()
            job.message = (
                f"Inspected {processed_files} PDF(s), {total_pages} page(s); "
                f"{searchable_pages} via text, {vision_pages} via vision, {ocr_pages} with no fields; "
                f"{field_count} field(s), {conflict_count} conflict(s)"
            )
            project.status = "review_ready"
            db.add(ProcessingEvent(project_id=job.project_id, job_id=job.id, stage="completed", progress=100, message=job.message))
            db.commit()
            log.info("Completed job %s", job.id)
        except Exception as exc:
            log.exception("Job %s failed", job_id)
            # The failing insert (e.g. a NUL-byte DataError) leaves the session in a failed
            # transaction. Roll back before reusing it, or the failure-recording below would
            # raise PendingRollbackError and crash the worker process (status 1 -> crash loop).
            try:
                db.rollback()
                job.status = "failed"
                job.stage = "failed"
                job.error_message = str(exc)
                job.message = f"Analysis failed: {exc}"
                if project:
                    project.status = "analysis_failed"
                db.add(ProcessingEvent(project_id=job.project_id, job_id=job.id, stage="failed", progress=job.progress or 0, message=str(job.message)))
                db.commit()
            except Exception:
                # Never let recording the failure crash the worker; the stuck-job recovery
                # sweep will re-queue or fail this job on a later poll.
                log.exception("Failed to record job failure for %s", job_id)
                try:
                    db.rollback()
                except Exception:
                    pass


def main():
    Base.metadata.create_all(bind=engine)
    log.info("PEMB processing worker v1.10.1 Crash Hotfix started; poll interval=%ss", POLL_SECONDS)
    while True:
        try:
            recover_stuck_jobs()
        except Exception:
            log.exception("Stuck-job recovery sweep failed")
        job_id = claim_job()
        if job_id:
            process_job(job_id)
        else:
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
