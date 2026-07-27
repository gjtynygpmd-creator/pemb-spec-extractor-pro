# Implement v1.9.4 - Hardening

Closes the last robustness gaps from the live diagnostic. Code changes are in the worker
and vision service only. For the repo cleanup and deploy steps, see
REPO_CLEANUP_AND_DEPLOY.md.

## Changes

- `app/services/vision_extraction.py`
  - OpenAI and Anthropic clients now pass `timeout=VISION_TIMEOUT_SECONDS` and
    `max_retries=0`, so a hung request fails fast and is caught.
  - `extract_from_png` / `extract_from_page` run render and the provider call under a hard
    wall-clock guard (`PAGE_TIMEOUT_SECONDS`). On timeout the page is flagged for review
    and the job continues, rather than hanging (which try/except cannot catch).
- `app/core/config.py`: adds `vision_timeout_seconds` (60) and `page_timeout_seconds` (120).
  All settings referenced in code have safe defaults.
- `render.yaml`: adds the two timeout vars and documents the confirmed Render build
  settings (Root Directory backend).
- `.gitignore` added.

## No required env vars

Defaults make the worker run correctly with your existing variables. The optional tuning
knobs are listed in REPO_CLEANUP_AND_DEPLOY.md.

## Verified here

- All test suites pass (schema loader, routing, render bounds, extraction engine).
- The wall-clock guard raises on a simulated hang; the no-key path degrades gracefully.
