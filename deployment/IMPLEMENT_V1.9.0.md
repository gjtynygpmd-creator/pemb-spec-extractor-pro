# Implement v1.9.1 — Document Intelligence Engine

1. Replace the repository contents with this release.
2. Commit: `feat: add v1.9.1 document intelligence engine`
3. Push to `main`. Netlify and Render should auto-deploy.
4. The Render Docker image now installs `tesseract-ocr`; the first build may take slightly longer.
5. Re-run **Start Analysis** on existing projects. Reprocessing is required for the new routing/OCR/spatial logic.
6. No new secrets or paid APIs are required for this release.

### What to watch during the field test
- `Need OCR` on the dashboard still means genuinely low-signal pages.
- The worker job message reports how many pages were OCR-assisted.
- Review wind, snow, risk category, roof slope, eave heights, and geometry first.
- Values that cannot be safely isolated should remain missing rather than being guessed.
