# Implement v1.9.3 - Schema-Driven Extraction

This release makes one JSON field dictionary the source of truth for extraction. It
builds on v1.9.2 and changes only the backend plus adds the schema files.

## What changed

- `backend/app/data/pemb_field_schema.json` - canonical dictionary of 90 fields in 13
  categories (type, unit, allowed values, aliases, typical source, notes).
- `backend/app/services/schema_loader.py` - loads the dictionary; builds the vision
  prompt and accepted-field set from it; reconciles the regex path's field names onto
  the same canonical names so text-path and vision-path results merge.
- `backend/app/services/vision_extraction.py` - prompt and validation now come from the
  schema; the model returns field_id values, which are enum-coerced and schema-validated.
- `backend/app/worker.py` - regex candidates are canonicalized to schema names before
  consolidation.
- `schema/PEMB_Extraction_Schema.xlsx` and `schema/pemb_field_schema.json` - human and
  machine copies for reference and editing.

## Deployment

No new required env vars. The schema ships inside the image (`COPY . .`), so nothing
else is needed. Redeploy the worker; the start log reads
`PEMB processing worker v1.9.3 Schema-Driven Extraction started`.

Optional: set `PEMB_SCHEMA_PATH` to point at a different JSON file (for example a
mounted volume) if you want to change fields without rebuilding the image.

## How to change the fields

Edit `backend/app/data/pemb_field_schema.json` (or edit the workbook and regenerate the
JSON) and redeploy. Adding, removing, or renaming a field, or changing its aliases,
allowed values, or notes, updates the vision prompt, the validation, and the dashboard
columns together. No Python changes are needed.

Each field carries:
- `field_id` - stable snake_case key (used in model output and code).
- `name` - display name shown in the app.
- `type`, `unit`, `allowed_values`, `format`, `example`.
- `aliases` - how the field appears on drawings and specs (improves recall).
- `typical_source` - where on the set it usually lives.
- `origin` - Template (from your original bid sheet) or Recommended (an addition).
- `notes` - disambiguation guidance (for example, an eave height is a dimension, not a
  wind speed).

## Testing without cloud infrastructure

From `backend/`:

```
DATABASE_URL=postgresql://unused PYTHONPATH=. python tests/test_schema_loader.py
DATABASE_URL=postgresql://unused PYTHONPATH=. python tests/test_vision_routing.py
DATABASE_URL=postgresql://unused PYTHONPATH=. python tests/test_render_bounds.py
DATABASE_URL=postgresql://unused python -m tools.local_extract /path/to/file.pdf --mock-vision
```

## Reconciliation notes

Most regex field names match the schema exactly. A few differ and are mapped in
`schema_loader._REGEX_NAME_TO_ID` (for example "Site Class" -> seismic_site_class,
"Building Code" -> building_code_ibc, "Overhead Doors" -> overhead_doors). Three
regex-only fields (Eave Height generic, Roof Slope generic, Building Orientation) are
not in the schema and pass through unchanged so nothing is lost. Add them to the JSON
if you want them treated as first-class schema fields.
