# Implement v1.9.6 - Polish pass

Fixes found while reviewing the sample-sheet export. No new env vars; deploy as usual.

## Changes
- backend/app/data/pemb_field_schema.json (+ schema/ copies): ASCE 7 allowed-values now
  carry the full "ASCE 7-NN" prefix on every option (fixes the "16-Jul" date artifact),
  and the Jurisdiction field label is corrected to "AHJ".
- backend/app/worker.py:
  - Drops redundant generic "Eave Height" / "Roof Slope" when the specific BSW/FSW eave
    heights or front/back slopes are present.
  - New _has_real_conflict(): two values only conflict if neither contains the other
    after normalization, so regex-vs-vision verbosity differences stop creating false
    conflicts.

## Deploy
GitHub Desktop replace-and-push as before, or drop the two changed files
(backend/app/worker.py and backend/app/data/pemb_field_schema.json) plus the schema/
copies into place and commit. Worker log reads
"PEMB processing worker v1.9.6 Polish started".

## Verify after deploy
Re-run the sample sheet. Expected: ASCE 7 Edition reads "ASCE 7-16" (not 16-Jul),
Jurisdiction field labeled AHJ, no duplicate generic Eave Height / Roof Slope rows,
and the Frame Type / Roof Panel Gauge conflicts gone.
