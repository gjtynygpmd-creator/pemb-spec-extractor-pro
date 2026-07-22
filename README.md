# PEMB Spec Extractor Pro

A proprietary estimating application for uploading large bid packages, indexing relevant construction documents, extracting source-backed PEMB project data, reviewing conflicts, and preparing downstream exports.

## Repository Structure

- `frontend/` — Netlify web interface
- `backend/` — FastAPI API and the background processing worker
- `database/` — PostgreSQL migrations
- `docs/` — architecture, roadmap, and deployment instructions
- `tests/` — benchmark and automated tests

## Current Release

**v1.2 Processing Engine MVP**

- Persistent projects and large multipart uploads
- Background worker that claims queued jobs
- PDF download and searchable-text inspection
- Page classification and Division 05/07/08/13 detection
- Initial source-backed PEMB field extraction
- Conflict flagging and project activity timeline

## Infrastructure

- Netlify: frontend
- Render: FastAPI backend and background worker
- Cloudflare R2: source documents
- Neon: PostgreSQL database

Do not commit passwords, connection strings, API keys, or R2 credentials. Store them only as environment variables.
