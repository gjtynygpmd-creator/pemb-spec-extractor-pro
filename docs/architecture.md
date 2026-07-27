# Large-file processing architecture

1. **Netlify frontend**
   - Selects multiple files.
   - Splits each file into 16 MB parts.
   - Requests signed upload URLs from the API.
   - Uploads each part directly to S3-compatible storage.
   - Starts a processing job after all uploads complete.

2. **FastAPI control service**
   - Creates projects and multipart upload sessions.
   - Generates signed part URLs.
   - Completes multipart uploads.
   - Starts and reports extraction jobs.
   - Does not proxy the file bytes, keeping API memory and timeout usage low.

3. **Object storage**
   - Cloudflare R2, AWS S3, Backblaze B2 S3, or equivalent.
   - Source files under `projects/<project_id>/source/`.
   - Rendered page images, OCR JSON, extracted records, and exports in separate prefixes.

4. **Processing workers**
   - Download or stream each file from object storage.
   - Inspect each PDF page's embedded text.
   - Route each page (implemented in v1.9.0):
     - Rich, label-dense text layer -> fast regex extraction (spec manuals, structural notes).
     - Otherwise -> vision extraction: the page is rendered to an image and read by
       Claude, which returns the PEMB schema as JSON (drawings, scanned, image-only).
     - Vision unavailable or empty -> page flagged for OCR/manual review, never dropped.
   - Classify sheets by title block and content.
   - Normalize extracted values to the PEMB schema through shared cleaners so both
     paths populate the same dashboard fields.
   - Store page, sheet, excerpt, confidence, and extraction method for each value.
   - Generate Excel, Zoho CSV, conflict report, and estimator summary.

   Still on the roadmap: safe ZIP expansion, tiled rendering for very large sheets,
   and bounding-box capture for on-sheet highlighting.

5. **Production requirements**
   - Persistent database instead of the in-memory prototype store.
   - Queue service and separate workers.
   - Authentication.
   - Virus scanning.
   - ZIP-bomb and path-traversal protection.
   - Automatic file retention/deletion policy.
   - Upload retry and resume state.
