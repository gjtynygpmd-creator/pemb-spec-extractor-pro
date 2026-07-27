# Implement v1.9.2 - Stability & Memory Safety

This release fixes analysis jobs that hang mid-run (the "stuck at 18%" symptom) on
large drawing sets. It builds on v1.9.0/v1.9.1 and changes only the worker and config.

## What was happening

The whole analysis runs inside one try/except that marks a job "failed" on any Python
error. When a job instead freezes in "processing" at a fixed percentage, the worker
process was killed by the platform (out of memory, or a hard timeout) before it could
raise a catchable error. Nothing recovered a stalled job, so it stayed "processing"
forever and the UI froze at its last progress.

## What changed (code)

- `app/worker.py`
  - `recover_stuck_jobs()`: runs every poll; re-queues jobs whose heartbeat is older
    than `WORKER_STALE_SECONDS`, or fails them after `WORKER_MAX_ATTEMPTS`.
  - `heartbeat()`: updates job progress/liveness every page (smooth progress + stall
    detection).
  - Per-page try/except so one unreadable sheet is skipped, not fatal.
  - Text/blocks capped by `PAGE_TEXT_CHAR_CAP`; vision calls capped by
    `VISION_MAX_PAGES_PER_JOB`; periodic `gc.collect()` on long jobs.
- `app/services/vision_extraction.py`
  - `render_page_png()` now bounds the longest edge by `VISION_MAX_EDGE_PX`. A 34x22 in
    ARCH-D sheet dropped from ~6800x4400 px (~90 MB raw per page) to ~2200x1424 px.
- `app/core/config.py`: new stability settings (all overridable by env var).

## Required deployment steps

1. Recommended: set the worker service to a larger plan. `render.yaml` now specifies
   `plan: standard` (2 GB) for the worker. On Render's `starter` (512 MB), large drawing
   sets can still OOM even with these fixes, especially with vision on. Revert to
   `starter` only if you process small text-based specs.

2. New worker env vars (defaults shown; all optional):
   - `VISION_MAX_EDGE_PX=2200`
   - `VISION_MAX_PAGES_PER_JOB=300`
   - `PAGE_TEXT_CHAR_CAP=100000`
   - `WORKER_STALE_SECONDS=600`
   - `WORKER_MAX_ATTEMPTS=3`

3. Redeploy the worker. Start log reads
   `PEMB processing worker v1.9.2 Stable Vision started`.

## How to confirm the original root cause in your logs

Before/after deploying, open the worker logs on Render for a run that hangs:
- "Out of memory" / "Killed" / exit status 137 -> OOM. The plan bump plus bounded
  rendering address this directly.
- A Python traceback that ends the process -> a caught error path; the message now
  surfaces on the job as "failed" instead of hanging.
- No error but the process restarts -> platform timeout; recovery re-queues the job.

## Behavior after this release

- A worker that dies mid-job no longer hangs the UI: within `WORKER_STALE_SECONDS` the
  job is retried, and after `WORKER_MAX_ATTEMPTS` it is marked failed with a clear
  message ("Worker stopped responding mid-analysis (likely out of memory)...").
- Progress advances page by page rather than jumping in 10-page steps.
- Vision (when enabled) renders bounded images regardless of physical sheet size.

## First test after deploy

Re-run the same large project that was hanging. Expected: progress moves past 18%
smoothly and either completes or fails with a message. If it fails on OOM specifically,
raise the worker plan further or lower `VISION_MAX_EDGE_PX` (e.g. 1800).
