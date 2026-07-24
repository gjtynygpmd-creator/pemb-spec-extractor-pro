# v1.9.1 OCR Stability Hotfix

This release fixes analysis jobs that could appear frozen on the first large drawing sheet.

## Changes
- OCR is now a fallback for low-signal/image-only pages instead of automatically OCRing every drawing page.
- Adaptive OCR resolution defaults to 140 DPI and enforces a 12 MP render ceiling.
- Tesseract has a 35-second per-page timeout so a single page cannot stall an entire project.
- OCR renders in grayscale to reduce memory and CPU load.
- Rich born-digital drawings continue through native text + coordinate-aware extraction without OCR delay.
- `FORCE_DRAWING_OCR=true` can be set later for diagnostics, but is off by default.
- Fixed a nested `db.add()` defect in field consolidation discovered during the hotfix review.

No project files need to be uploaded again. Re-run Start Analysis after deploying the API and worker.
