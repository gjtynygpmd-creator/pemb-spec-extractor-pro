# v1.1 Functional MVP

## Testable workflow
1. Create a persistent project.
2. Open the project workspace.
3. Select multiple source documents.
4. Upload each file to Cloudflare R2 through multipart signed URLs.
5. Save uploaded-file records in Neon PostgreSQL.
6. Refresh/reopen the project and confirm the file list persists.
7. Start a persistent processing job.
8. Confirm the queued job remains visible after refresh.

## Not included yet
The processing job is stored but not consumed by a worker. OCR, drawing vision, extracted fields, and Excel export are the next milestone.

## Important Cloudflare R2 configuration
The R2 bucket needs a browser CORS policy allowing your Netlify origin to:
- PUT
- GET
- HEAD

and exposing the `ETag` response header.
