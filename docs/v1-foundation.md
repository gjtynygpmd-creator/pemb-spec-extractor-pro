# v1 Foundation

This update replaces in-memory project storage with Neon PostgreSQL and introduces:

- persistent projects
- uploaded-file model
- processing-job model
- extracted-field model
- source page/sheet/excerpt fields
- dashboard API
- project dashboard frontend
- database-aware health check

## Deployment
1. Upload this repository update to GitHub.
2. Render will auto-deploy if automatic deployments are enabled.
3. Verify `/health` returns `database_configured: true` and version `1.0.0`.
4. Deploy `frontend/` to Netlify or reconnect the Netlify site to this GitHub repository with publish directory `frontend`.
