# Implement v1.9.1 - Provider-Agnostic Vision

Builds on v1.9.0. The vision path now works with either OpenAI (default) or Claude,
selected by one environment variable. The regex fast path for text-layer spec manuals
is unchanged.

## Choosing a provider

Set `VISION_PROVIDER` on the worker service:

- `openai` (default): uses the OpenAI Chat Completions API with an image. Requires
  `OPENAI_API_KEY`. Set `VISION_MODEL_OPENAI` to the vision-capable model you use
  (default `gpt-4o`).
- `anthropic`: uses the Claude Messages API with an image. Requires `ANTHROPIC_API_KEY`.
  Set `VISION_MODEL_ANTHROPIC` (default `claude-opus-4-8`).

Both providers use the same prompt, JSON parsing, schema validation, and value cleaners,
so extracted fields land in the same dashboard columns regardless of provider.

## Worker environment variables (defaults shown)

```
VISION_PROVIDER=openai
VISION_EXTRACTION_ENABLED=true
OPENAI_API_KEY=            # required when provider=openai (sync:false in render.yaml)
VISION_MODEL_OPENAI=gpt-4o
ANTHROPIC_API_KEY=         # required when provider=anthropic (sync:false)
VISION_MODEL_ANTHROPIC=claude-opus-4-8
VISION_DPI=200
TEXT_LAYER_MIN_CHARS=200
TEXT_LAYER_MIN_LABELS=3
```

Only the key for the active provider is needed. The API service does not need either
key; only the worker performs extraction.

## Important: Claude API access is separate from a Claude.ai subscription

A paid Claude.ai plan (Pro, Max, Team, or Enterprise), including a company account, does
NOT include Claude API/Console access. To use `VISION_PROVIDER=anthropic` you need an API
key from the Anthropic Console (console.anthropic.com), which is a separate product with
separate, token-based billing. Access is self-serve: create/organize a Console account,
add a payment method, and generate a key. Until that exists, keep `VISION_PROVIDER=openai`.

## Behavior with no key

If the active provider has no key (or `VISION_EXTRACTION_ENABLED=false`), the job still
runs: text-layer spec pages extract normally, and drawings/scanned pages are flagged for
OCR/manual review rather than dropped. The worker log states the active provider and model.

## Local testing without cloud infrastructure

From `backend/`:

```
# Offline routing check (drawings show as needs_ocr without a key)
DATABASE_URL=postgresql://unused python -m tools.local_extract /path/to/file.pdf

# Simulate the vision path offline
DATABASE_URL=postgresql://unused python -m tools.local_extract /path/to/file.pdf --mock-vision

# Real OpenAI vision path
VISION_PROVIDER=openai OPENAI_API_KEY=sk-... DATABASE_URL=postgresql://unused \
  python -m tools.local_extract /path/to/file.pdf

# Real Claude vision path (needs an Anthropic Console key)
VISION_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-ant-... DATABASE_URL=postgresql://unused \
  python -m tools.local_extract /path/to/file.pdf
```
