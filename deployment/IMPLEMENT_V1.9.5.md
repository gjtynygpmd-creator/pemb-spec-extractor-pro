# Implement v1.9.5 - Full-Schema Extraction + UI trim

Fixes the partial-data behavior on text-based specs, two wrong-value regex bugs, and
removes the Bid Readiness panel. Backend + frontend changes; no schema change.

## Backend
- app/worker.py: rich-text pages now run regex AND (when VISION_SUPPLEMENTS_TEXT is true
  and under the per-job cap) the vision model, merged. This is what fills the ~60 schema
  fields the regex rules do not cover.
- app/services/document_analysis.py:
  - Site Class / Seismic Design Category / Wind Exposure rules bind to the letter directly
    after the label instead of a greedy skip (fixes wrong-letter reads).
  - Removed "by others" as an accessory exclude trigger (fixes false "Excluded").
- app/core/config.py: adds VISION_SUPPLEMENTS_TEXT (default true).

## Frontend
- project.html / project.js: removed the Bid Readiness / Missing Information aside; the
  Project Data area now spans full width. Stat cards are unchanged; the panel's JS writes
  are null-guarded so nothing errors.

## Deploy
No new required env vars. Optional: set VISION_SUPPLEMENTS_TEXT=false on the worker to
keep text pages regex-only (lower OpenAI cost, less coverage). Redeploy; worker log reads
"PEMB processing worker v1.9.5 Full-Schema Extraction started".

## Cost note
Text/spec pages now make one vision call each (previously zero), so OpenAI usage rises.
Still cents per sheet with gpt-4o; bounded by VISION_MAX_PAGES_PER_JOB.
