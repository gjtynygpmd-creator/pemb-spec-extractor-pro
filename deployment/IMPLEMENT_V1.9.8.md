# Implement v1.9.8 - Drawing accuracy

From reviewing the real drawings export. Backend + schema; no new env vars.

## Changes
- document_analysis.py:
  - _extract_design_criteria now runs on relevant pages regardless of page type
    (structural_notes/general_notes/unclassified/specification, division 13, or any
    PEMB-relevant page). Recovers wind speed, snow loads, and snow factors from design
    blocks on sheets that classify as "specification".
  - candidate_quality prefers non-vision (validated regex) values for a set of
    deterministic code/load/seismic fields and Project Address, so a confident vision
    misread no longer beats a correct regex value.
- worker.py: Total Square Feet is computed from Building Width x Length when both exist,
  replacing implausible vision area misreads.
- schema (backend/app/data/pemb_field_schema.json + schema/): project_name note tells
  vision to use the title-block project name, not a sheet title.

## Deploy
GitHub Desktop replace-and-push. Worker log reads
"PEMB processing worker v1.9.8 Drawing Accuracy started".

## Recommended workflow
Upload the spec book and the drawings into the same project for maximum coverage.

## Verify after deploy (re-run the drawings)
- Basic Wind Speed (116 mph), Ground/Roof Snow Load, snow factors now appear.
- Risk Category reads III (not IV); Project Address reads the site (Stillwater), not the
  engineer's city.
- Total Square Feet reflects width x length, not a large misread.
- Project name is no longer a sheet title.
