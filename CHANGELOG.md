## v1.9.4 - Hardening (timeouts, hang guard) + clean repo

Closes the remaining robustness gaps from the live diagnostic and ships as a clean tree.

- Vision clients now use an explicit network timeout with retries disabled
  (VISION_TIMEOUT_SECONDS, default 60), so a hung provider request fails fast and is
  caught, instead of stalling the worker.
- Added a hard per-page wall-clock guard (PAGE_TIMEOUT_SECONDS, default 120) around the
  render+vision step. A hang, as opposed to an exception, is not caught by try/except;
  this bounds it so the job continues and the page is flagged for review.
- render_page_png already caps the longest edge (VISION_MAX_EDGE_PX) and drops the alpha
  channel; confirmed and retained.
- Verified every setting referenced in code has a safe default, so the worker runs
  correctly even when optional env vars are unset.
- Added .gitignore (caches, archives, env files, web-upload duplicates).
- render.yaml annotated with the confirmed Render build settings (Root Directory backend,
  Dockerfile backend/Dockerfile). Dashboard settings remain the source of truth.
- Packaged as a clean repo tree (contents at root, no wrapper folder, no __pycache__,
  no .pytest_cache, no committed archives, no duplicate files) for a single clean commit.

Note: deploying this version also clears any stuck "processing" job automatically via the
v1.9.2 recovery sweep (after WORKER_STALE_SECONDS); no database surgery is required.

## v1.9.3 - Schema-Driven Extraction

Makes a single JSON field dictionary the source of truth for what gets extracted.

- Adds backend/app/data/pemb_field_schema.json (90 fields across 13 categories), derived from the reorganized bid template, with per-field type, unit, allowed values, drawing/spec aliases, typical source location, and disambiguation notes.
- Adds app/services/schema_loader.py: loads the dictionary and reconciles both extraction paths to one set of canonical names. The vision prompt and its accepted-field set are now generated from the schema; the regex path's output names are mapped onto the same canonical fields so text and vision results merge cleanly.
- Vision model now returns field_id values with enum coercion and schema validation, so drawings yield exact, normalized specifications instead of free-form guesses.
- Added roof/wall insulation thickness fields so the schema fully covers the regex engine's fields; nothing extracted is dropped.
- Editing the JSON (or the companion schema/PEMB_Extraction_Schema.xlsx) changes the whole pipeline with no code edits.
- Optional PEMB_SCHEMA_PATH env var overrides the packaged dictionary location.

## v1.9.2 - Stability & Memory Safety

Fixes analysis jobs hanging mid-run (the "stuck at 18%" symptom) on large drawing sets.

- Root cause: on a large multi-page PDF the worker was being killed by the platform (out of memory, or a hard timeout) before it could raise a catchable error. The job stayed in "processing" forever because nothing recovered a stalled job, so the UI froze at its last progress.
- Stuck-job recovery: the worker now sweeps every poll for jobs stuck in "processing" past a heartbeat timeout and either re-queues them (up to WORKER_MAX_ATTEMPTS) or marks them failed with a clear message, instead of leaving them hung.
- Per-page heartbeat: job progress and liveness are updated every page, so progress advances smoothly and a stall is detectable.
- Memory-safe rendering: vision renders are now bounded by longest edge (VISION_MAX_EDGE_PX), so a full-size ARCH-D/E sheet no longer produces a ~90 MB bitmap per page. This removes the main out-of-memory trigger introduced by the vision path.
- Per-page error isolation: a single unreadable sheet is recorded and skipped rather than aborting the whole job.
- Guard rails: per-page text is capped (PAGE_TEXT_CHAR_CAP), vision calls per job are capped (VISION_MAX_PAGES_PER_JOB), and memory is reclaimed periodically during long jobs.
- Deployment: render.yaml worker plan recommended at 'standard' (2 GB) for large sets; new stability settings added as env vars.

## v1.9.1 - Provider-Agnostic Vision

- Makes the vision extraction path provider-agnostic behind a single switch (VISION_PROVIDER).
- Defaults to OpenAI (Chat Completions with an image, JSON response) so existing OpenAI deployments work with no code change; set OPENAI_API_KEY and VISION_MODEL_OPENAI.
- Adds a one-variable switch to Claude (set VISION_PROVIDER=anthropic plus ANTHROPIC_API_KEY). Note: the Claude API is a separate product from a Claude.ai subscription and requires an Anthropic Console API key (separate billing).
- Both providers share the same prompt, JSON parsing, schema validation, and value cleaners, so results populate identical dashboard fields.
- Adds the openai dependency and provider/model configuration to config and render.yaml.
- Graceful degradation now reports the active provider and model in logs and the local tool.

## v1.9.0 - Vision Extraction Engine

- Adds a vision-based extraction path: pages without a rich text layer (drawings, scanned sheets, image-only pages) are rendered and read by Claude, which returns the PEMB estimator schema as JSON.
- Rewires the worker to route each page: a rich, label-dense text layer goes to the fast regex path; everything else goes to the vision path; pages the vision path cannot use are flagged for OCR/manual review instead of being silently dropped.
- Fixes a wrong-value bug where a label such as "Basic Wind Speed" on a drawing could bind across a line break to the next bare number on the sheet (for example an eave height of 24'-0" reported as "24 mph"). Label/value matching for the affected rules now binds on the same line and requires the expected unit.
- Adds a page-routing helper (rich-text-layer detection by length and label density) and configurable thresholds.
- Adds graceful degradation when no API key is present: the job still runs, drawings are flagged for review, and nothing crashes.
- Adds a standalone local extraction tool (tools/local_extract.py) to debug routing and extraction on a PDF without S3, Postgres, or the worker queue, including a --mock-vision mode for offline testing.
- Adds the anthropic dependency and vision configuration (model, DPI, thresholds) to config and render.yaml.

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
