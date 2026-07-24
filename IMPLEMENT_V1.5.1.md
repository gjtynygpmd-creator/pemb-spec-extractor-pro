# Implement v1.9.0 - Vision Extraction Engine

This release adds a vision-based extraction path so drawings and scanned pages are
actually read, instead of being silently skipped. The regex engine is retained as a
fast path for born-digital spec manuals.

## What changed

- New service: `backend/app/services/vision_extraction.py`
- Worker routing rewritten in `backend/app/worker.py`
- Same-line label/value binding and unit-required validation in
  `backend/app/services/document_analysis.py` (fixes the "24 mph" misread)
- New config in `backend/app/core/config.py`
- New dependency `anthropic` in `backend/requirements.txt`
- New env vars in `backend/render.yaml` (worker service)
- New local debug tool `backend/tools/local_extract.py`

## Required deployment steps

1. Set the worker's `ANTHROPIC_API_KEY` environment variable on Render (marked
   `sync: false`, so set it in the dashboard or as a secret). The API service does not
   need it; only the worker performs extraction.

2. Confirm these worker env vars (defaults shown; all optional except the key):
   - `VISION_EXTRACTION_ENABLED=true`
   - `VISION_MODEL=claude-opus-4-8`
   - `VISION_DPI=200`
   - `TEXT_LAYER_MIN_CHARS=200`
   - `TEXT_LAYER_MIN_LABELS=3`

3. Redeploy. The worker log line on start will read
   `PEMB processing worker v1.9.0 Vision Extraction Engine started`.

## Behavior without an API key

If `ANTHROPIC_API_KEY` is unset (or `VISION_EXTRACTION_ENABLED=false`), the job still
runs. Spec pages with a text layer extract normally; drawings and scanned pages are
flagged for OCR/manual review rather than dropped, and the job completes without error.

## Local testing without cloud infrastructure

From `backend/`, with dependencies installed:

```
# Offline routing check (drawings will show as needs_ocr without a key)
DATABASE_URL=postgresql://unused python -m tools.local_extract /path/to/file.pdf

# Simulate the vision path offline to verify routing and merge
DATABASE_URL=postgresql://unused python -m tools.local_extract /path/to/file.pdf --mock-vision

# Exercise the real vision path
ANTHROPIC_API_KEY=sk-... DATABASE_URL=postgresql://unused \
  python -m tools.local_extract /path/to/file.pdf
```

The tool prints, per page: detected type, text length, diagnostic label count, the
routing decision (text / vision / needs_ocr), and every field found.

## Cost and tuning notes

- Vision runs only on pages that fail the text-layer test, so clean spec manuals incur
  no model cost. A drawing-heavy set will call the model once per drawing page.
- Raise `TEXT_LAYER_MIN_LABELS` to send more borderline pages to vision (higher recall,
  higher cost); lower it to prefer the regex path.
- `VISION_DPI` trades legibility of small callout text against image size; 200 is a good
  default, 150 is cheaper, 300 helps on dense sheets.
