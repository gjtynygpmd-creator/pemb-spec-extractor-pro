# PEMB Spec Extractor Pro v1.7.2 — Export Hotfix

## Fix
The PDF generator referenced `mapping` while constructing project metadata before `mapping` had been initialized. This raised a Python `NameError` and caused the `/exports/projects/{project_id}/pdf` route to return HTTP 500.

The field map is now initialized before project rows are created.

## Deployment
1. Replace the repository contents with this release.
2. Commit and push to `main`.
3. Confirm the Render web service auto-deploys commit.
4. The worker does not require special configuration changes.
5. Hard-refresh the Netlify application.
6. Re-open the project and select PDF Export.

Recommended commit:

`fix: repair PDF export field mapping initialization`
