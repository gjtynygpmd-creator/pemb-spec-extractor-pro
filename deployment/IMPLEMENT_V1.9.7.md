# Implement v1.9.7 - Vision prioritization

Ensures PEMB-relevant pages get a vision read even in large, mixed documents. Backend +
one frontend label. No new env vars.

## Changes
- backend/app/services/document_analysis.py: new page_is_pemb_relevant(text).
- backend/app/worker.py:
  - PEMB-relevant pages bypass the per-job vision budget (guaranteed vision); off-topic
    pages still respect VISION_MAX_PAGES_PER_JOB.
  - Off-topic pages drop bare accessory "Specified/Included/Excluded" hits (precision).
  - "needs_ocr" page bucket renamed internally to "no_fields"; completion message says
    "N with no fields".
- frontend/project.html: the stat card label "Need OCR" is now "No Fields Found".

## Deploy
GitHub Desktop replace-and-push as usual. Worker log reads
"PEMB processing worker v1.9.7 Vision Prioritization started".

## What to expect
- On a large drawing set, the design-criteria sheet is read by vision no matter its
  position, so dimensions/loads/wind/seismic should come through if present.
- On a spec book with no design numbers, yield stays low (correctly) - the data is not
  in that document.

## Cost note
Relevant pages always get a vision call, so a set with many relevant sheets uses more
credit. VISION_MAX_PAGES_PER_JOB still caps off-topic pages.
