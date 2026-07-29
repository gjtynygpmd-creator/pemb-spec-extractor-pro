# Implement v1.10.0 - Estimator merge

Ports the proven prompt and procurement schema from the earlier single-shot tool into
this app. Backend + schema; no new env vars, no Anthropic dependency.

## Changes
- backend/app/services/schema_loader.py: build_vision_instructions() now uses the
  estimator framing (document types, read-all-tables, ignore-boilerplate, keep-values-
  as-written, ignore "-None-", never invent).
- backend/app/data/pemb_field_schema.json (+ schema/): 90 -> 117 fields, adding
  procurement/bid context and granular geometry/finishes. All new fields are Recommended.

## Why not a second Anthropic-based version
The earlier tool ran in Claude desktop and billed the company Anthropic account, which
cannot take paid budget - that is why it ran out of credits. Its value was the prompt and
schema, both now in this app, which runs on OpenAI via Render. No parallel version needed.

## Deploy
GitHub Desktop replace-and-push. Worker log reads
"PEMB processing worker v1.10.0 Estimator Merge started".

## Verify
- Re-run the combined Synthesia project; expect more procurement fields populated from the
  spec (owner, GC, engineers, delivery method, bonds) alongside the design numbers from
  the drawings.
