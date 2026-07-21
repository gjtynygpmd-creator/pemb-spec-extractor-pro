# PEMB Spec Extractor Pro

A Western Steel estimating application for uploading large bid packages, extracting PEMB project data, reviewing source-backed results, and exporting completed estimating records.

## Repository Structure

- `frontend/` — Netlify web interface
- `backend/` — FastAPI application and upload-control API
- `workers/` — OCR, drawing vision, and extraction workers
- `database/` — PostgreSQL migrations and schema documentation
- `docs/` — Architecture and roadmap
- `deployment/` — Netlify, Render, R2, and Neon deployment notes
- `tests/` — Automated and benchmark tests

## Infrastructure

- Netlify: frontend
- Render: FastAPI backend and workers
- Cloudflare R2: source documents and generated files
- Neon: PostgreSQL database
- OpenAI API: document and drawing interpretation

## Security

Do not commit passwords, database connection strings, API keys, or R2 credentials. Add them only as environment variables in Render and Netlify.
