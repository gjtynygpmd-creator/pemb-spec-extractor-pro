"""Canonical PEMB field dictionary loaded from pemb_field_schema.json.

This module is the single source of truth for which fields the app extracts and how
they are named, typed, and validated. Both extraction paths read from it:
  - the vision path builds its prompt and its accepted-field set here, and
  - the regex path's output is reconciled to these canonical names here,
so text and vision results merge under one consistent schema.

Editing the JSON (add/remove a field, change aliases or allowed values) changes the
whole pipeline; no code edits are required.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from functools import lru_cache

log = logging.getLogger("pemb-worker.schema")

_DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "pemb_field_schema.json")


@dataclass(frozen=True)
class Field:
    field_id: str
    name: str
    category: str
    type: str
    unit: str | None
    allowed_values: list[str] | None
    format: str | None
    example: str
    aliases: tuple[str, ...]
    typical_source: str
    origin: str
    required: bool
    notes: str | None


# Maps the regex engine's field names (document_analysis.CORE_ESTIMATOR_FIELDS) onto
# schema field_ids so both paths consolidate under one canonical name. Names not listed
# here are matched by exact name or alias; anything still unresolved passes through
# unchanged so no extracted data is ever dropped.
_REGEX_NAME_TO_ID = {
    "BSW Eave Height": "bsw_eave_height",
    "Back Roof Slope": "roof_slope_back",
    "Front Roof Slope": "roof_slope_front",
    "Building Code": "building_code_ibc",
    "Occupancy": "building_use",
    "Ridge Offset": "bsw_ridge_offset",
    "Site Class": "seismic_site_class",
    "Seismic Design Category": "seismic_sdc",
    "Ss": "seismic_ss",
    "S1": "seismic_s1",
    "Snow Exposure Factor": "snow_ce",
    "Thermal Factor": "snow_ct",
    "Gutters": "gutters_downspouts",
    "Downspouts": "gutters_downspouts",
    "Ridge Vents": "ventilation",
    "Overhead Doors": "overhead_doors",
    "Framed Openings": "framed_openings",
    "Roof Insulation": "roof_insulation",
    "Wall Insulation": "wall_insulation",
    # "Eave Height", "Roof Slope", "Building Orientation" have no exact schema field;
    # they pass through unchanged.
}


@lru_cache(maxsize=1)
def _load(path: str | None = None) -> dict:
    p = path or os.getenv("PEMB_SCHEMA_PATH") or _DEFAULT_PATH
    with open(p, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    fields: dict[str, Field] = {}
    by_name: dict[str, str] = {}
    by_alias: dict[str, str] = {}
    order: list[str] = []
    for item in raw.get("fields", []):
        f = Field(
            field_id=item["field_id"],
            name=item["name"],
            category=item["category"],
            type=item.get("type", "string"),
            unit=item.get("unit"),
            allowed_values=item.get("allowed_values"),
            format=item.get("format"),
            example=item.get("example", ""),
            aliases=tuple(item.get("aliases") or []),
            typical_source=item.get("typical_source", ""),
            origin=item.get("origin", "Recommended"),
            required=bool(item.get("required")),
            notes=item.get("notes"),
        )
        fields[f.field_id] = f
        order.append(f.field_id)
        by_name[f.name.strip().lower()] = f.field_id
        for a in f.aliases:
            by_alias.setdefault(a.strip().lower(), f.field_id)
    # Fold the regex-name map in via names too.
    for rname, fid in _REGEX_NAME_TO_ID.items():
        by_name.setdefault(rname.strip().lower(), fid)
    return {
        "version": raw.get("version", "?"),
        "fields": fields,
        "order": order,
        "by_name": by_name,
        "by_alias": by_alias,
        "categories": raw.get("categories", {}),
    }


def reload_schema() -> None:
    """Clear the cache so a changed JSON is picked up (useful in tests/dev)."""
    _load.cache_clear()


def version() -> str:
    return _load()["version"]


def all_fields() -> list[Field]:
    d = _load()
    return [d["fields"][fid] for fid in d["order"]]


def field_count() -> int:
    return len(_load()["fields"])


def get(field_id: str) -> Field | None:
    return _load()["fields"].get(field_id)


def resolve(name_or_id: str) -> Field | None:
    """Resolve a field_id, exact display name, regex name, or alias to a Field."""
    if not name_or_id:
        return None
    d = _load()
    key = name_or_id.strip()
    if key in d["fields"]:
        return d["fields"][key]
    low = key.lower()
    fid = d["by_name"].get(low) or d["by_alias"].get(low)
    return d["fields"].get(fid) if fid else None


def canonical_name(name_or_id: str) -> str:
    """Return the schema display name for a given name/id, or the input unchanged
    if it is not part of the schema (so nothing is silently dropped)."""
    f = resolve(name_or_id)
    return f.name if f else name_or_id


def category_for(name_or_id: str, default: str = "Other") -> str:
    f = resolve(name_or_id)
    return f.category if f else default


def coerce_value(name_or_id: str, raw_value: str) -> str:
    """Light validation/normalization. For enums, map to an allowed option
    (case-insensitive, exact or substring); otherwise return the trimmed value."""
    value = (raw_value or "").strip()
    if not value:
        return value
    f = resolve(name_or_id)
    if f and f.type == "enum" and f.allowed_values:
        low = value.lower()
        for opt in f.allowed_values:
            if opt.lower() == low:
                return opt
        for opt in f.allowed_values:
            base = opt.split("(")[0].strip().lower()
            if base and (base in low or low in base):
                return opt
    return value


def build_vision_instructions() -> str:
    """Render the schema into extraction instructions for the vision model."""
    lines: list[str] = []
    lines.append(
        "Extract the PEMB estimating fields from this sheet. Return ONLY a JSON object "
        "with a single key \"fields\" whose value is a list of objects, each with:\n"
        "  - field_id: the exact id from the list below\n"
        "  - value: the value exactly as shown on the sheet (keep units)\n"
        "  - confidence: a number from 0 to 1\n"
        "  - source_note: a short phrase describing where on the sheet it was found\n\n"
        "Rules:\n"
        "  - Use ONLY field_id values from the list. Omit any field not present. Never guess.\n"
        "  - For enum fields, choose one of the allowed values.\n"
        "  - Read schedules, load tables, title blocks, and dimension callouts.\n"
        "  - Do not confuse a dimension (e.g. an eave height like 24'-0\") with a load or a wind speed.\n\n"
        "Fields (grouped by category):"
    )
    current = None
    for f in all_fields():
        if f.category != current:
            lines.append(f"\n[{f.category}]")
            current = f.category
        parts = [f"- {f.field_id} ({f.name})", f"type={f.type}"]
        if f.unit:
            parts.append(f"unit={f.unit}")
        if f.allowed_values:
            parts.append("allowed=" + "|".join(f.allowed_values))
        if f.aliases:
            parts.append("aka=" + ", ".join(f.aliases[:5]))
        if f.notes:
            parts.append(f"note={f.notes}")
        lines.append("  " + "; ".join(parts))
    return "\n".join(lines)
