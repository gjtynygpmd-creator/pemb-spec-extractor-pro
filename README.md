# PEMB Spec Extractor Pro v1.4.0

Production export release for PEMB estimating projects.

## Included

- Persistent projects, uploads, processing jobs, indexed pages, and estimator review
- Editable/manual extracted fields with review status and source references
- Excel estimator workbook export
- Complete extracted-data CSV export
- Zoho-ready single-row CSV export
- No database migration required from v1.3

## Deployment

- Netlify base directory: `frontend`
- Render root directory: `backend`
- Render web command is supplied by the Dockerfile
- Render worker command: `python -m app.worker`

See `deployment/IMPLEMENT_V1.4.0.md` for update and verification steps.
