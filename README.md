# PEMB Spec Extractor Pro v1.8.0 Field Test Release

## Insulation Core Release

v1.6.1 retains Excel, full CSV, Zoho CSV, and PDF exports and improves the searchable-text extraction pipeline.

### Improvements
- Searches every searchable PDF page, including `unclassified` pages.
- Adds a validated label/value fallback for design-criteria tables.
- Improves capture of building code, risk category, wind, snow, roof live load, collateral load, seismic design category, and site class.
- Rejects common definition text that can look like a building dimension.
- Retains targeted PEMB extraction for panels, insulation, framing, openings, finishes, gutters, downspouts, canopies, curbs, and vents.
- Preserves manually entered estimator values when analysis is rerun.
- Adds a worker version startup message so the deployed processing code can be verified independently of the API.

No database migration is required. See `deployment/IMPLEMENT_V1.5.1.md`.
