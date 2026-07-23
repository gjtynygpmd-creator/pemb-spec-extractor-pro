# Changelog

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
