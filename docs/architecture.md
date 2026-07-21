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

4. **Processing workers — next build**
   - Download or stream each file from object storage.
   - Expand ZIP files safely.
   - Inspect PDF page text and raster content.
   - Render drawing-heavy pages in tiles.
   - OCR image-only pages.
   - Classify sheets by title block and content.
   - Run targeted drawing-vision prompts.
   - Normalize extracted values to the PEMB schema.
   - Store page, sheet, bounding box, excerpt, and confidence for each value.
   - Generate Excel, Zoho CSV, conflict report, and estimator summary.

5. **Production requirements**
   - Persistent database instead of the in-memory prototype store.
   - Queue service and separate workers.
   - Authentication.
   - Virus scanning.
   - ZIP-bomb and path-traversal protection.
   - Automatic file retention/deletion policy.
   - Upload retry and resume state.
