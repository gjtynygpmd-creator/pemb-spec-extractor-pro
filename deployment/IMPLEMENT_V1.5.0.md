# PEMB Spec Extractor Pro v1.5.0

## Purpose
v1.5.0 upgrades the core PEMB extraction engine while retaining Excel, CSV, Zoho CSV, and PDF exports.

## Improvements
- Expanded extraction from searchable specification and drawing pages.
- Searches every searchable page, including pages classified as unclassified.
- Adds core loads, codes, snow, seismic, panels, finishes, framing, openings, and accessories.
- Adds page-type and specification-division confidence weighting.
- Preserves manual estimator entries when analysis is rerun.
- Improves conflict comparison by normalizing punctuation and spacing.

## Deployment
1. Copy the package contents to the root of the existing GitHub repository.
2. Commit to `main` with `v1.5.0 core PEMB extraction`.
3. Allow Netlify, the Render API, and the Render worker to redeploy.
4. No database migration or new environment variable is required.
5. Reopen the benchmark project and click **Start Analysis** again.

## Verification
- API health/version should report `1.5.0`.
- The completed job message should report a nonzero field count on text-searchable PEMB specifications containing design criteria.
- Review extracted fields before exporting.
