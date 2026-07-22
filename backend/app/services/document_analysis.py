from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class FieldRule:
    category: str
    field_name: str
    patterns: tuple[str, ...]
    confidence: float = 0.82
    preferred_page_types: tuple[str, ...] = ()
    preferred_divisions: tuple[str, ...] = ()


# v1.5 focuses on practical PEMB estimating data. Patterns intentionally allow
# broken spacing and punctuation commonly produced by PDF drawing/spec text.
FIELD_RULES: tuple[FieldRule, ...] = (
    FieldRule("Project", "Project Address", (
        r"(?:project|site)\s+address\s*[:\-]?\s*([^\n]{8,120})",
    ), 0.72, ("general_notes", "specification")),
    FieldRule("Geometry", "Building Width", (
        r"(?:overall\s+building\s+width|building\s+width|overall\s+width)\s*[:=\-]?\s*(\d+(?:\s*[-']\s*\d+(?:\s*\d+/\d+)?\s*[\"”]?)?\s*(?:ft|feet|['’])?)",
    ), 0.84, ("elevation", "roof_plan", "framing_plan", "structural_notes")),
    FieldRule("Geometry", "Building Length", (
        r"(?:overall\s+building\s+length|building\s+length|overall\s+length)\s*[:=\-]?\s*(\d+(?:\s*[-']\s*\d+(?:\s*\d+/\d+)?\s*[\"”]?)?\s*(?:ft|feet|['’])?)",
    ), 0.84, ("elevation", "roof_plan", "framing_plan", "structural_notes")),
    FieldRule("Geometry", "Eave Height", (
        r"(?:top\s+of\s+)?eave\s+(?:height|elevation)\s*[:=\-]?\s*((?:\d+\s*['’]\s*(?:\d+(?:\s+\d+/\d+)?\s*[\"”])?)|(?:\d+(?:\.\d+)?\s*(?:ft|feet)))",
        r"(?:clear\s+)?eave\s*[:=\-]?\s*(\d+(?:\s*[-']\s*\d+(?:\s*\d+/\d+)?\s*[\"”]?)?\s*(?:ft|feet|['’])?)",
    ), 0.86, ("elevation", "structural_notes")),
    FieldRule("Geometry", "Roof Slope", (
        r"roof\s+(?:slope|pitch)\s*[:=\-]?\s*([0-9.]+\s*(?::|/)\s*12)",
        r"(?:slope|pitch)\s*[:=\-]?\s*([0-9.]+\s*(?::|/)\s*12)",
        r"([0-9.]+\s*(?::|/)\s*12)\s+(?:roof\s+)?slope",
    ), 0.90, ("roof_plan", "elevation", "structural_notes")),
    FieldRule("Codes & Loads", "Building Code", (
        r"\b((?:20)?\d{2}\s+(?:IBC|International Building Code|Ohio Building Code))\b",
        r"(?:governing\s+)?building\s+code\s*[:\-]?\s*((?:(?:20)?\d{2}\s+)?(?:International|Ohio|California|Florida|Utah|North Carolina|Kentucky|Georgia|Texas)[^\n.;]{0,50}Code)",
        r"international\s+building\s+code\s*\(?IBC\)?\s*[-,:]?\s*((?:20)?\d{2})",
        r"year/version\s*[:\-]?\s*((?:20)?\d{2})",
    ), 0.91, ("structural_notes", "specification"), ("13",)),
    FieldRule("Codes & Loads", "Occupancy", (
        r"occupancy\s+(?:group|category|classification)?\s*[:\-]?\s*([^\n.;]{2,60})",
        r"use\s+group\s*[:\-]?\s*([^\n.;]{2,60})",
    ), 0.82, ("structural_notes", "specification")),
    FieldRule("Codes & Loads", "Risk Category", (
        r"risk\s+category(?:\s+of\s+building)?\s*[:\-=]?\s*(I{1,3}|IV|[1-4])\b",
        r"risk\s+category(?:\s+of\s+building)?\s*[-–—]\s*(I{1,3}|IV|[1-4])\b",
    ), 0.94, ("structural_notes", "specification"), ("13",)),
    FieldRule("Codes & Loads", "Basic Wind Speed", (
        r"(?:ultimate\s+)?(?:basic\s+)?wind\s+speed\s*[:=\-–—]?\s*(\d{2,3})\s*(?:mph)?",
        r"V\s*ult\s*[:=\-]?\s*(\d{2,3})\s*mph",
    ), 0.94, ("structural_notes", "specification"), ("13",)),
    FieldRule("Codes & Loads", "Wind Exposure", (
        r"(?:wind\s+exposure(?:\s+category)?|exposure\s+category)\s*[:=\-–—]?\s*([BCD])\b",
    ), 0.91, ("structural_notes", "specification"), ("13",)),
    FieldRule("Codes & Loads", "Ground Snow Load", (
        r"ground\s+snow\s+load\s*[:=\-–—]?\s*(\d+(?:\.\d+)?)\s*psf",
        r"\bP\s*g\s*[:=\-]?\s*(\d+(?:\.\d+)?)\s*psf",
    ), 0.94, ("structural_notes", "specification"), ("13",)),
    FieldRule("Codes & Loads", "Roof Snow Load", (
        r"roof\s+snow\s+load\s*[:=\-–—]?\s*(\d+(?:\.\d+)?)\s*psf",
        r"\bP\s*f\s*[:=\-]?\s*(\d+(?:\.\d+)?)\s*psf",
    ), 0.93, ("structural_notes", "specification"), ("13",)),
    FieldRule("Codes & Loads", "Roof Live Load", (
        r"roof\s+live\s+load\s*[:=\-–—]?\s*(\d+(?:\.\d+)?)\s*psf",
    ), 0.94, ("structural_notes", "specification"), ("13",)),
    FieldRule("Codes & Loads", "Collateral Load", (
        r"collateral\s+load\s*[:=\-–—]?\s*(\d+(?:\.\d+)?)\s*psf",
    ), 0.92, ("structural_notes", "specification"), ("13",)),
    FieldRule("Codes & Loads", "Seismic Design Category", (
        r"seismic\s+design\s+category\s*[:=\-–—]?\s*([A-F])\b",
    ), 0.95, ("structural_notes", "specification")),
    FieldRule("Codes & Loads", "Site Class", (
        r"site\s+class\s*[:=\-–—]?\s*([A-F])\b",
    ), 0.93, ("structural_notes", "specification"), ("13",)),
    FieldRule("Codes & Loads", "Ss", (
        r"(?:\bS\s*s\b|0\.2\s*s\s*\(Ss\))\s*[) ]*[:=\-–—]?\s*(0?\.\d+)",
        r"spectral\s+response[^\n]{0,80}?0\.2\s*s[^\n]{0,40}?(0?\.\d+)",
    ), 0.92, ("structural_notes", "specification"), ("13",)),
    FieldRule("Codes & Loads", "S1", (
        r"(?:\bS\s*1\b|1\s*[- ]?sec\.?\s*\(S1\))\s*[) ]*[:=\-–—]?\s*(0?\.\d+)",
        r"spectral\s+response[^\n]{0,80}?1\s*[- ]?sec[^\n]{0,40}?(0?\.\d+)",
    ), 0.92, ("structural_notes", "specification"), ("13",)),
    FieldRule("Codes & Loads", "Thermal Factor", (
        r"thermal\s+factor\s*[:=\-–—]?\s*(\d+(?:\.\d+)?)",
    ), 0.88, ("structural_notes", "specification"), ("13",)),
    FieldRule("Codes & Loads", "Snow Exposure Factor", (
        r"(?:snow\s+)?exposure\s+factor\s*[:=\-–—]?\s*(\d+(?:\.\d+)?)",
    ), 0.88, ("structural_notes", "specification"), ("13",)),
    FieldRule("Envelope", "Roof Insulation", (
        r"roof\s+insulation(?:\s+system)?[^\n]{0,120}?\b(R\s*[-]?\s*\d+(?:\.\d+)?)\b",
        r"\b(R\s*[-]?\s*\d+(?:\.\d+)?)\b[^\n]{0,80}roof\s+insulation",
    ), 0.84, ("specification",), ("07", "13")),
    FieldRule("Envelope", "Wall Insulation", (
        r"wall\s+insulation(?:\s+system)?[^\n]{0,120}?\b(R\s*[-]?\s*\d+(?:\.\d+)?)\b",
        r"\b(R\s*[-]?\s*\d+(?:\.\d+)?)\b[^\n]{0,80}wall\s+insulation",
    ), 0.84, ("specification",), ("07", "13")),
    FieldRule("Envelope", "Roof Panel Type", (
        r"(?:roof\s+panel|roofing)\s*[:\-]?\s*([^\n.;]{4,100}(?:standing\s+seam|panel)[^\n.;]{0,60})",
        r"((?:mechanically\s+seamed|vertical\s+rib|trapezoidal)[^\n.;]{0,70}standing\s+seam[^\n.;]{0,50})",
        r"(Loc\s+Seam\s+90/360\s+Roof\s+Panel)",
    ), 0.86, ("specification",), ("13",)),
    FieldRule("Envelope", "Roof Panel Gauge", (
        r"(?:roof\s+panel[^\n]{0,180}?|standing\s+seam[^\n]{0,180}?)gauge\s*[:\-]?\s*(2[246])\b",
        r"Loc\s+Seam[^\n]{0,220}?Gauge\s*[:\-]?\s*(2[246])\b",
    ), 0.91, ("specification",), ("13",)),
    FieldRule("Envelope", "Wall Panel Type", (
        r"(?:exterior\s+)?wall\s+panels?\s*[:\-]?\s*((?:R[- ]?Panel|PBR|IMP|insulated\s+metal\s+panel|concealed[- ]fastener)[^\n.;]{0,80})",
        r"(R[- ]?Panel(?:\s+Liner\s+Panel)?)",
    ), 0.80, ("specification",), ("07", "13")),
    FieldRule("Envelope", "Wall Panel Gauge", (
        r"(?:wall\s+panel[^\n]{0,180}?|liner\s+panel[^\n]{0,180}?)gauge\s*[:\-]?\s*(2[468])\b",
        r"R-Panel\s+Liner\s+Panel[^\n]{0,220}?Gauge\s*[:\-]?\s*(2[468])\b",
    ), 0.89, ("specification",), ("07", "13")),
    FieldRule("Envelope", "Roof Panel Color", (
        r"roof\s+panel[\s\S]{0,350}?color\s*[:\-]?\s*([^\n.;]{3,60})",
    ), 0.81, ("specification",), ("13",)),
    FieldRule("Envelope", "Paint System", (
        r"(70%\s*PVDF[^\n.;]{0,80})",
        r"(PVDF\s+Panel\s+Paint\s+System[^\n.;]{0,100})",
    ), 0.86, ("specification",), ("13",)),
    FieldRule("Envelope", "Finish Warranty", (
        r"(\d{1,2})\s*[- ]?year\s+finish\s+warranty",
        r"warranty\s+shall\s+be\s+for\s+a\s+period\s+of\s+(\d{1,2})\s+years?[^\n]{0,120}PVDF",
    ), 0.87, ("specification",), ("13",)),
    FieldRule("Framing", "Frame Type", (
        r"frame\s+type\s*[:\-]?\s*((?:clear[- ]?span|multi[- ]?span|single[- ]?slope|lean[- ]?to|modular)[^\n.;]{0,40})",
        r"\b(clear\s*[- ]?span)\b",
    ), 0.82, ("specification",), ("13",)),
    FieldRule("Framing", "Frame Design", (
        r"frame\s+design\s*[:\-]?\s*([^\n.;]{3,60})",
    ), 0.82, ("specification",), ("13",)),
    FieldRule("Framing", "Primary Frame Finish", (
        r"(?:primary\s+framing|rigid\s+frames?)[\s\S]{0,500}?finish\s*[:\-]?\s*([^\n.;]{3,80})",
    ), 0.75, ("specification",), ("13",)),
    FieldRule("Openings", "Overhead Door", (
        r"(?:overhead|sectional|rolling)\s+doors?[^\n]{0,140}?((?:\d+\s*['’]\s*(?:\d+\s*[\"”])?\s*)[xX]\s*(?:\d+\s*['’]\s*(?:\d+\s*[\"”])?))",
        r"((?:\d+\s*['’])\s*[xX]\s*(?:\d+\s*['’]))[^\n]{0,80}(?:overhead|sectional|rolling)\s+door",
    ), 0.80, ("door_schedule", "elevation"), ("08", "13")),
    FieldRule("Openings", "Window Size", (
        r"(?:window|fixed\s+glass)[^\n]{0,120}?size\s*[:\-]?\s*([^\n.;]{3,50})",
        r"size\s*[:\-]?\s*(\d+\s+foot\s+by\s+\d+\s+foot)",
    ), 0.78, ("door_schedule", "specification"), ("08", "13")),
    FieldRule("Accessories", "Gutters", (
        r"((?:low[- ]eave\s+)?gutter(?:s)?[^\n.;]{0,100})",
    ), 0.76, ("specification", "elevation"), ("13",)),
    FieldRule("Accessories", "Downspouts", (
        r"(downspouts?[^\n.;]{0,100})",
    ), 0.74, ("specification", "elevation"), ("13",)),
    FieldRule("Accessories", "Canopies", (
        r"(canopies?\s*[:\-]?[^\n.;]{3,140})",
    ), 0.78, ("specification", "elevation"), ("13",)),
    FieldRule("Accessories", "Framed Openings", (
        r"(framed\s+openings?\s*[:\-]?[^\n.;]{3,160})",
    ), 0.79, ("specification", "door_schedule"), ("13",)),
    FieldRule("Accessories", "Roof Curbs", (
        r"(roof\s+curbs?\s*[:\-]?[^\n.;]{3,160})",
    ), 0.78, ("specification",), ("13",)),
    FieldRule("Accessories", "Ridge Vents", (
        r"((?:gravity\s+)?ridge\s+vents?[^\n.;]{0,140})",
    ), 0.77, ("specification",), ("13",)),
)


# v1.5.1 universal label/value fallback. This complements the targeted rules above
# and is intentionally limited to high-value estimating labels. It is used on every
# searchable page, including pages that cannot be classified reliably.
GENERIC_LABEL_RULES: tuple[FieldRule, ...] = (
    FieldRule("Geometry", "Building Width", (r"\b(?:bldg\.?|building)\s+(?:overall\s+)?width\s*[:=\-]?\s*([^\n|]{2,40})",), 0.78),
    FieldRule("Geometry", "Building Length", (r"\b(?:bldg\.?|building)\s+(?:overall\s+)?length\s*[:=\-]?\s*([^\n|]{2,40})",), 0.78),
    FieldRule("Geometry", "Eave Height", (r"\beave\s+(?:ht\.?|height|elev\.?|elevation)\s*[:=\-]?\s*([^\n|]{2,40})",), 0.80),
    FieldRule("Geometry", "Roof Slope", (r"\broof\s+(?:slope|pitch)\s*[:=\-]?\s*([^\n|]{2,30})",), 0.82),
    FieldRule("Codes & Loads", "Building Code", (r"\b(?:applicable|governing|design)\s+(?:building\s+)?code\s*[:=\-]?\s*([^\n|]{4,90})",), 0.83),
    FieldRule("Codes & Loads", "Risk Category", (r"\brisk\s+category\s*[:=\-]?\s*([^\n|]{1,18})",), 0.88),
    FieldRule("Codes & Loads", "Basic Wind Speed", (r"\b(?:ultimate\s+design\s+wind\s+speed|basic\s+wind\s+speed|wind\s+speed|vult)\s*[:=\-]?\s*([^\n|]{2,35})",), 0.86),
    FieldRule("Codes & Loads", "Wind Exposure", (r"\b(?:wind\s+)?exposure(?:\s+category)?\s*[:=\-]?\s*([^\n|]{1,20})",), 0.85),
    FieldRule("Codes & Loads", "Ground Snow Load", (r"\b(?:ground\s+snow\s+load|pg)\s*[:=\-]?\s*([^\n|]{1,30})",), 0.87),
    FieldRule("Codes & Loads", "Roof Snow Load", (r"\b(?:flat\s+roof\s+snow\s+load|roof\s+snow\s+load|pf)\s*[:=\-]?\s*([^\n|]{1,30})",), 0.87),
    FieldRule("Codes & Loads", "Roof Live Load", (r"\broof\s+live\s+load\s*[:=\-]?\s*([^\n|]{1,30})",), 0.87),
    FieldRule("Codes & Loads", "Collateral Load", (r"\bcollateral(?:\s+dead)?\s+load\s*[:=\-]?\s*([^\n|]{1,30})",), 0.86),
    FieldRule("Codes & Loads", "Seismic Design Category", (r"\bseismic\s+design\s+category\s*[:=\-]?\s*([^\n|]{1,20})",), 0.89),
    FieldRule("Codes & Loads", "Site Class", (r"\bsite\s+class\s*[:=\-]?\s*([^\n|]{1,20})",), 0.87),
)


def _clean_generic_value(field_name: str, value: str) -> str | None:
    value = normalize_space(value)
    # Stop common table spillover and retain only the useful leading value.
    value = re.split(r"\s{3,}|\b(?:NOTES?|REMARKS?|REFERENCE)\b", value, maxsplit=1, flags=re.I)[0].strip()
    if not value or len(value) > 120:
        return None
    validators = {
        "Building Width": r"^(?:\d+(?:\.\d+)?\s*(?:ft|feet|['’])|\d+\s*[-']\s*\d+(?:\s+\d+/\d+)?\s*[\"”]?)\b",
        "Building Length": r"^(?:\d+(?:\.\d+)?\s*(?:ft|feet|['’])|\d+\s*[-']\s*\d+(?:\s+\d+/\d+)?\s*[\"”]?)\b",
        "Eave Height": r"^(?:\d+(?:\.\d+)?\s*(?:ft|feet|['’])|\d+\s*[-']\s*\d+(?:\s+\d+/\d+)?\s*[\"”]?)\b",
        "Building Code": r"^(?=.*(?:IBC|BUILDING CODE|INTERNATIONAL BUILDING CODE|OHIO BUILDING CODE|FLORIDA BUILDING CODE|CALIFORNIA BUILDING CODE)).{4,90}$",
        "Risk Category": r"^(?:I{1,3}|IV|[1-4])\b",
        "Wind Exposure": r"^[BCD]\b",
        "Seismic Design Category": r"^[A-F]\b",
        "Site Class": r"^[A-F]\b",
        "Basic Wind Speed": r"^\d{2,3}(?:\s*mph)?\b",
        "Ground Snow Load": r"^\d+(?:\.\d+)?(?:\s*psf)?\b",
        "Roof Snow Load": r"^\d+(?:\.\d+)?(?:\s*psf)?\b",
        "Roof Live Load": r"^\d+(?:\.\d+)?(?:\s*psf)?\b",
        "Collateral Load": r"^\d+(?:\.\d+)?(?:\s*psf)?\b",
        "Roof Slope": r"^(?:\d+(?:\.\d+)?\s*(?::|/)\s*12|\d+(?:\.\d+)?\s*in(?:ch)?(?:es)?\s+per\s+foot)\b",
    }
    pattern = validators.get(field_name)
    if pattern:
        m = re.search(pattern, value, re.I)
        if not m:
            return None
        value = m.group(0)
    if re.search(r"^(?:n/?a|none|not applicable|see drawings?|see plans?)$", value, re.I):
        return None
    return value


def normalize_space(value: str) -> str:
    value = value.replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", value).strip(" :;,-")


def normalized_compare(value: str) -> str:
    return re.sub(r"[^a-z0-9.]", "", value.lower())


def classify_page(text: str) -> tuple[str, str | None, str | None, str | None]:
    upper = text.upper()
    division = None
    for number in ("03", "05", "07", "08", "09", "13"):
        if re.search(rf"\bDIVISION\s+{number}\b", upper) or re.search(rf"\b{number}\s+\d{{2}}\s+\d{{2}}\b", upper):
            division = number
            break

    categories = (
        ("structural_notes", ("STRUCTURAL GENERAL NOTES", "DESIGN CRITERIA", "DESIGN LOADS")),
        ("general_notes", ("GENERAL NOTES",)),
        ("elevation", ("EXTERIOR ELEVATION", "BUILDING ELEVATION", "ELEVATIONS")),
        ("roof_plan", ("ROOF PLAN",)),
        ("foundation_plan", ("FOUNDATION PLAN",)),
        ("framing_plan", ("FRAMING PLAN", "ROOF FRAMING PLAN")),
        ("door_schedule", ("DOOR SCHEDULE", "OVERHEAD DOOR SCHEDULE")),
        ("wall_section", ("WALL SECTION",)),
        ("specification", ("SECTION ", "PART 1 - GENERAL", "PART 1  GENERAL", "PART 2 - PRODUCTS", "PART 2 PRODUCTS")),
    )
    page_type = "unclassified"
    for candidate, needles in categories:
        if any(n in upper for n in needles):
            page_type = candidate
            break

    sheet_number = None
    sheet_title = None
    for line in [normalize_space(x) for x in text.splitlines() if x.strip()][:80]:
        match = re.fullmatch(r"([A-Z]{1,4}[-.]?\d{1,4}(?:\.\d{1,2})?[A-Z]?)", line.upper())
        if match:
            sheet_number = match.group(1)
            break
    title_match = re.search(r"\b(GENERAL NOTES|STRUCTURAL GENERAL NOTES|DESIGN CRITERIA|ROOF PLAN|FOUNDATION PLAN|FRAMING PLAN|DOOR SCHEDULE|EXTERIOR ELEVATIONS?|WALL SECTIONS?)\b", upper)
    if title_match:
        sheet_title = title_match.group(1).title()
    return page_type, division, sheet_number, sheet_title


def _rule_confidence(rule: FieldRule, page_type: str | None, division: str | None, match_text: str) -> float:
    score = rule.confidence
    if page_type and page_type in rule.preferred_page_types:
        score += 0.05
    if division and division in rule.preferred_divisions:
        score += 0.05
    if re.search(r"(?:not\s+used|not\s+applicable|optional|example)", match_text, re.I):
        score -= 0.12
    return max(0.40, min(0.99, score))


def extract_fields(text: str, page_type: str | None = None, division: str | None = None) -> list[dict]:
    # Search both original text and a line-normalized copy. The second form helps
    # when PDF extraction inserts line breaks between labels and values.
    variants: Iterable[str] = (text, re.sub(r"[\t\r]+", " ", text))
    found: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for rule in FIELD_RULES:
        for variant in variants:
            matched = False
            for pattern in rule.patterns:
                match = re.search(pattern, variant, flags=re.IGNORECASE | re.MULTILINE)
                if not match:
                    continue
                value = normalize_space(match.group(1))
                if not value or len(value) > 220:
                    continue
                key = (rule.field_name, normalized_compare(value))
                if key in seen:
                    matched = True
                    break
                seen.add(key)
                excerpt_start = max(0, match.start() - 140)
                excerpt_end = min(len(variant), match.end() + 220)
                excerpt = normalize_space(variant[excerpt_start:excerpt_end])
                found.append({
                    "category": rule.category,
                    "field_name": rule.field_name,
                    "value": value,
                    "confidence": _rule_confidence(rule, page_type, division, excerpt),
                    "source_excerpt": excerpt,
                })
                matched = True
                break
            if matched:
                break

    # Universal field finder: examine label/value pairs regardless of page type.
    # Targeted matches remain preferred because their base confidence is higher.
    compact = re.sub(r"[\t\r]+", " ", text)
    for rule in GENERIC_LABEL_RULES:
        for pattern in rule.patterns:
            for match in re.finditer(pattern, compact, flags=re.IGNORECASE | re.MULTILINE):
                value = _clean_generic_value(rule.field_name, match.group(1))
                if not value:
                    continue
                key = (rule.field_name, normalized_compare(value))
                if key in seen:
                    continue
                seen.add(key)
                excerpt_start = max(0, match.start() - 120)
                excerpt_end = min(len(compact), match.end() + 180)
                excerpt = normalize_space(compact[excerpt_start:excerpt_end])
                found.append({
                    "category": rule.category,
                    "field_name": rule.field_name,
                    "value": value,
                    "confidence": _rule_confidence(rule, page_type, division, excerpt),
                    "source_excerpt": excerpt,
                    "match_method": "universal_label",
                })
    return found
