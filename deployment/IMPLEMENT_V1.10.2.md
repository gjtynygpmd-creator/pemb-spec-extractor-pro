# Implement v1.10.2 - Throughput / rate limits

Addresses the OpenAI 429 throttling. Backend only. No schema change.

## Changes
- config.py: vision_model_openai default -> "gpt-4o-mini"; new vision_max_retries (4).
- vision_extraction.py: both provider clients use max_retries=vision_max_retries, so 429s
  back off and retry (honoring Retry-After) instead of dropping the page.
- schema_loader.py: leaner per-field prompt lines (fewer tokens per call).
- worker.py: datetime.utcnow() -> datetime.now(timezone.utc).replace(tzinfo=None)
  (removes deprecation warning; same naive-UTC value).
- render.yaml: VISION_MODEL_OPENAI=gpt-4o-mini, VISION_MAX_RETRIES=4.

## Why gpt-4o-mini
The OpenAI project in use only allows gpt-4o-mini, and that model has 200,000 TPM vs
gpt-4o's 30,000 TPM on this account. Calling gpt-4o was hitting the tight limit and being
throttled. Mini has vision and, combined with the regex-first pipeline, degrades
gracefully on dense sheets. Switch back with VISION_MODEL_OPENAI=gpt-4o if the project
allow-list and tier permit.

## Deploy
GitHub Desktop replace-and-push, OR set the env var VISION_MODEL_OPENAI=gpt-4o-mini on the
worker directly for an immediate change. Worker log reads
"PEMB processing worker v1.10.2 Throughput started".

## Verify
Re-run a job; the worker logs should show far fewer 429s and jobs should complete much
faster. Extracted values still cite their source pages.
