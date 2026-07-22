from __future__ import annotations
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class FieldRule:
    category: str
    field_name: str
    patterns: tuple[str, ...]
    confidence: float = 0.82


FIELD_RULES = (
    FieldRule("Geometry", "Building Width", (r"(?:building\s+)?width\s*[:=]?\s*(\d+(?:\.\d+)?\s*(?:ft|feet|['’]))",)),
    FieldRule("Geometry", "Building Length", (r"(?:building\s+)?length\s*[:=]?\s*(\d+(?:\.\d+)?\s*(?:ft|feet|['’]))",)),
    FieldRule("Geometry", "Eave Height", (r"eave\s+height\s*[:=]?\s*(\d+(?:\.\d+)?\s*(?:ft|feet|['’]))",)),
    FieldRule("Geometry", "Roof Slope", (r"roof\s+(?:slope|pitch)\s*[:=]?\s*([0-9.]+\s*(?::|/)\s*12)",)),
    FieldRule("Codes & Loads", "Building Code", (r"\b((?:20)?\d{2}\s+IBC)\b", r"international building code\s*[,\-:]?\s*((?:20)?\d{2})"), 0.90),
    FieldRule("Codes & Loads", "Risk Category", (r"risk\s+category\s*[:=]?\s*(I{1,3}|IV|[1-4])\b",), 0.90),
    FieldRule("Codes & Loads", "Basic Wind Speed", (r"(?:ultimate\s+)?(?:basic\s+)?wind\s+speed\s*[:=]?\s*(\d{2,3})\s*(?:mph)?", r"Vult\s*[:=]?\s*(\d{2,3})\s*mph"), 0.90),
    FieldRule("Codes & Loads", "Wind Exposure", (r"(?:wind\s+)?exposure(?:\s+category)?\s*[:=]?\s*([BCD])\b",), 0.88),
    FieldRule("Codes & Loads", "Ground Snow Load", (r"ground\s+snow\s+load\s*[:=]?\s*(\d+(?:\.\d+)?)\s*psf", r"Pg\s*[:=]?\s*(\d+(?:\.\d+)?)\s*psf"), 0.90),
    FieldRule("Codes & Loads", "Roof Live Load", (r"roof\s+live\s+load\s*[:=]?\s*(\d+(?:\.\d+)?)\s*psf",), 0.90),
    FieldRule("Codes & Loads", "Seismic Design Category", (r"seismic\s+design\s+category\s*[:=]?\s*([A-F])\b",), 0.92),
    FieldRule("Codes & Loads", "Site Class", (r"site\s+class\s*[:=]?\s*([A-F])\b",), 0.88),
    FieldRule("Codes & Loads", "Ss", (r"\bSs\s*[:=]\s*(0?\.\d+)",), 0.88),
    FieldRule("Codes & Loads", "S1", (r"\bS1\s*[:=]\s*(0?\.\d+)",), 0.88),
    FieldRule("Envelope", "Roof Insulation", (r"roof\s+insulation[^\n]{0,80}?\b(R-?\s*\d+)\b", r"\b(R-?\s*\d+)\b[^\n]{0,50}roof insulation"), 0.82),
    FieldRule("Envelope", "Wall Insulation", (r"wall\s+insulation[^\n]{0,80}?\b(R-?\s*\d+)\b", r"\b(R-?\s*\d+)\b[^\n]{0,50}wall insulation"), 0.82),
    FieldRule("Envelope", "Roof Panel Gauge", (r"roof\s+panels?[^\n]{0,80}?\b(2[246]\s*ga(?:uge)?)\b",), 0.82),
    FieldRule("Envelope", "Wall Panel Gauge", (r"wall\s+panels?[^\n]{0,80}?\b(2[468]\s*ga(?:uge)?)\b",), 0.82),
    FieldRule("Openings", "Overhead Door", (r"(?:overhead|sectional|rolling)\s+door[^\n]{0,100}?((?:\d+['’\-]\s*){1,2}\s*[xX]\s*(?:\d+['’\-]\s*){1,2})",), 0.76),
)


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" :;,-")


def classify_page(text: str) -> tuple[str, str | None, str | None, str | None]:
    upper = text.upper()
    division = None
    for number in ("05", "07", "08", "13"):
        if re.search(rf"\bDIVISION\s+{number}\b", upper) or re.search(rf"\b{number}\s+\d{{2}}\s+\d{{2}}\b", upper):
            division = number
            break

    categories = (
        ("structural_notes", ("STRUCTURAL GENERAL NOTES", "DESIGN CRITERIA")),
        ("general_notes", ("GENERAL NOTES",)),
        ("elevation", ("EXTERIOR ELEVATION", "BUILDING ELEVATION")),
        ("roof_plan", ("ROOF PLAN",)),
        ("foundation_plan", ("FOUNDATION PLAN",)),
        ("framing_plan", ("FRAMING PLAN",)),
        ("door_schedule", ("DOOR SCHEDULE", "OVERHEAD DOOR")),
        ("wall_section", ("WALL SECTION",)),
        ("specification", ("SECTION ", "PART 1 - GENERAL", "PART 2 - PRODUCTS")),
    )
    page_type = "unclassified"
    for candidate, needles in categories:
        if any(n in upper for n in needles):
            page_type = candidate
            break

    sheet_number = None
    sheet_title = None
    for line in [normalize_space(x) for x in text.splitlines() if x.strip()][:40]:
        match = re.fullmatch(r"([A-Z]{1,3}[-.]?\d{2,4}(?:\.\d{1,2})?)", line.upper())
        if match:
            sheet_number = match.group(1)
            break
    title_match = re.search(r"\b(GENERAL NOTES|STRUCTURAL GENERAL NOTES|ROOF PLAN|FOUNDATION PLAN|FRAMING PLAN|DOOR SCHEDULE|EXTERIOR ELEVATIONS?|WALL SECTIONS?)\b", upper)
    if title_match:
        sheet_title = title_match.group(1).title()
    return page_type, division, sheet_number, sheet_title


def extract_fields(text: str) -> list[dict]:
    found: list[dict] = []
    for rule in FIELD_RULES:
        for pattern in rule.patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
            if not match:
                continue
            value = normalize_space(match.group(1))
            excerpt_start = max(0, match.start() - 100)
            excerpt_end = min(len(text), match.end() + 140)
            found.append({
                "category": rule.category,
                "field_name": rule.field_name,
                "value": value,
                "confidence": rule.confidence,
                "source_excerpt": normalize_space(text[excerpt_start:excerpt_end]),
            })
            break
    return found
