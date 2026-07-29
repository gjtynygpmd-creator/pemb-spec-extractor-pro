# Implement v1.9.9 - Precision

Backend only. No new env vars.

## Changes
- document_analysis.py: all three Risk Category rules require an assignment separator
  (colon/equals/dash) and reject list continuations, so C&C wind-table headers
  ("RISK CATEGORY IV", "RISK CATEGORY I, II OR III") are not mistaken for the rating.
- worker.py: Customer / Project / Project Address prefer the earliest credible page
  (cover/title sheet) so a later consultant title block does not win.

## Deploy
GitHub Desktop replace-and-push. Worker log reads
"PEMB processing worker v1.9.9 Precision started".

## Verify (re-run the combined project)
- Risk Category reads III, not IV.
- Project Address leans to the project site rather than the engineer's office.
- Identity fields still appear as conflicts for confirmation.
