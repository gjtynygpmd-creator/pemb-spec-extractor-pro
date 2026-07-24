## v1.9.0 - Document Intelligence Engine

- Replaces the crude 40-character searchable-page threshold with a meaningful-text score.
- Never skips low-signal PDF pages: they are rendered and OCR-assisted with Tesseract.
- OCR-assists high-value drawing sheets even when an embedded text layer exists.
- Adds coordinate-aware block extraction to pair design-criteria labels with nearby values.
- Improves sheet classification for floor plans, roof plans, elevations, sections, schedules, and structural notes.
- Constrains design-load regex windows so unrelated dimensions cannot become load values.
- Prevents S1/Ss false positives from sheet numbers without seismic/spectral context.
- Correctly normalizes fractional roof slopes such as 3/8:12 to 0.375:12.
- Adds regression tests for unsafe wind matching, drawing classification, spatial extraction, and fractional roof slopes.

## v1.8.1 - Estimator Value Engine

- Separates candidate discovery from estimator-ready values.
- Converts narrative accessory scope into Included, Excluded, or Specified.
- Adds field-specific validation for panel types, gauges, openings, square footage, and addresses.
- Ranks concise validated values above long source passages.
- Reduces false conflicts by comparing normalized clean values.
- Adds regression tests for accessory scope and roof/wall panel assemblies.

# Changelog

## v1.8.0 - Real Drawing Extraction Engine
- Adds page-specific extraction passes for structural criteria, geometry, envelope systems, insulation, openings, and accessories.
- Preserves PDF text-block reading order for schedules and callouts.
- Improves sheet classification using title-block text.
- Infers overall building dimensions from plan and elevation dimensions with confidence metadata.
- Expands the estimator field registry so existing accessory and opening rules reach the dashboard.
- Adds tolerance for flattened tables and common PDF text errors such as BOOF/ROOF and $1/S1.


## v1.7.2 - Export Hotfix
- Fixed PDF export HTTP 500 caused by using the field mapping before it was initialized.
- Updated PDF and Excel release labels.
- Verified PDF generation with empty project fields.
- Retained the v1.7.1 API and R2 CORS fixes.

## v1.7.1 — CORS Hotfix
- Fixed browser preflight failures between the Netlify frontend and Render API.
- Production Netlify origin is now always allowed, even when Render has an older `CORS_ORIGINS` environment value.
- Added support for Netlify deploy-preview origins.
- Updated dashboard version badge.

## v1.7.0 - Field Test Release

- Expanded Geometry Engine: width, length, area, orientation, frame type, ridge offset, BSW/FSW eave heights, and front/back roof slopes.
- Added canonical value and unit normalization for mph, psf, R-values, roof slopes, and common metal-panel names.
- Improved conflict detection so equivalent formatting does not create false conflicts.
- Added CSI-aware source preference for core PEMB, structural steel, envelope, insulation, flashing, and roof-accessory sections.
- Added category-level estimator readiness reporting.
- Synchronized project address metadata with extracted Project Address values in PDF exports.
- Updated PDF and application release identification to v1.7.0.
- Added geometry and normalization regression tests.
