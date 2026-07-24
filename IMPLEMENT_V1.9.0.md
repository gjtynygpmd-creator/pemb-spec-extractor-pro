# Implement v1.2

## 1. Commit the release
Replace the current repository contents with this package, then commit and push to the main branch.

## 2. Apply the Neon migration
Open Neon SQL Editor and run:

`database/migrations/002_processing_engine.sql`

The API also calls `create_all`, but the SQL migration is required to add new columns to the existing `processing_jobs` table.

## 3. Redeploy the Render API
Use the existing service. Confirm its Root Directory remains `backend`. After deployment, `/health` should report version `1.2.0`.

## 4. Create the Render background worker
Create a new **Background Worker** from the same GitHub repository.

- Root Directory: `backend`
- Runtime: Docker
- Dockerfile: `Dockerfile`
- Docker command: `python -m app.worker`

Copy these environment variables from the API service:

- `DATABASE_URL`
- `S3_ENDPOINT_URL`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`
- `S3_BUCKET`
- `S3_REGION`

Optional: `WORKER_POLL_SECONDS=8`

## 5. Redeploy Netlify
The existing Netlify site should deploy automatically after GitHub receives the frontend changes. Keep Base Directory set to `frontend`.

## 6. Test
1. Open an existing project with at least one PDF.
2. Click **Start Analysis**.
3. Confirm status changes from queued to processing within roughly 8–20 seconds.
4. Watch page progress update automatically.
5. Confirm the job reaches completed.
6. Verify Indexed Pages, Need OCR, Inspection Summary, Activity, and Extracted PEMB Data populate.

## Expected first-test limitations
Image-only pages will be counted as **Need OCR** but will not yet be read. The first release uses deterministic rules against searchable PDF text, providing a stable baseline before AI/OCR is added.
