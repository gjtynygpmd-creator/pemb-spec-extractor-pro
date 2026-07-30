# Implement v1.10.1 - Crash-loop hotfix

Priority deploy. Fixes the worker crash loop (NUL-byte DataError + missing rollback).
Backend only (worker.py). No new env vars, no schema change.

## Changes (backend/app/worker.py)
- _clean_text() helper removes NUL (0x00) bytes.
- Applied at the source (page.get_text and blocks_text) and defensively at every text
  insert (DocumentPage.text_excerpt, ExtractedField value/normalized_value/
  source_excerpt/source_sheet).
- The outer except in process_job now calls db.rollback() before reusing the session, and
  the whole failure-recording block is wrapped in try/except so it cannot crash the
  process. A failed job is left for the recovery sweep to re-queue/fail.

## Deploy
GitHub Desktop replace-and-push (only backend/app/worker.py changed, plus version
strings/docs). Worker log reads "PEMB processing worker v1.10.1 Crash Hotfix started".

## Verify (from the diagnosis)
1. Redeploy the worker.
2. Re-run the stuck project (HBR_Hangars_ProjectManual.pdf); confirm it progresses past
   page 52 instead of stalling.
3. Render -> pemb-spec-extractor-worker -> Events: no more "Instance failed" crash-loop
   entries.
