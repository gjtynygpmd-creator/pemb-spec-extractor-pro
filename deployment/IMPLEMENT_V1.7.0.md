# Implement v1.7.0 Field Test Release

1. Replace the repository contents with this package while preserving your environment variables.
2. Commit and push to the GitHub branch connected to Netlify and Render.
3. Recommended commit: `feat: release v1.7.0 geometry field test`
4. Confirm the Render API and worker both redeploy successfully.
5. Open the Netlify application and verify the `v1.7.0 Field Test` badge.
6. Create a fresh project for the live bid, upload drawings/specifications, and run analysis.
7. Export Excel and PDF after reviewing the extracted values.

No database migration is required for this release. Existing projects remain available, but re-run analysis to use the new extraction logic.
