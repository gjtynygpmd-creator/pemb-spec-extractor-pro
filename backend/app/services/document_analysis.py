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


# v1.6 Estimator Core focuses on practical PEMB estimating data. Patterns intentionally allow
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
        r"roof\s+(?:slope|pitch)\s*[:=\-]?\s*([0-9.]+\s*(?::|/)\s*12|[0-9.]+\s*(?:in(?:ch)?(?:es)?|\")\s+per\s+(?:foot|1[\'’]-?0[\"]?))",
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
    FieldRule("Insulation", "Roof Insulation Type", (
        r"roof\s+insulation(?:\s+system)?[^\n]{0,100}?\b(fiberglass|blanket|batt|rigid(?:[- ]board)?|polyisocyanurate|polyiso|spray[- ]foam|insulated\s+metal\s+panel|IMP|liner\s+system)\b",
        r"\b(fiberglass|blanket|batt|rigid(?:[- ]board)?|polyisocyanurate|polyiso|spray[- ]foam|insulated\s+metal\s+panel|IMP)\b[^\n]{0,100}?roof",
    ), 0.86, ("specification", "roof_plan", "wall_section"), ("07", "13")),
    FieldRule("Insulation", "Roof Insulation R-Value", (
        r"roof\s+insulation(?:\s+system)?[^\n]{0,140}?\b(R\s*[-]?\s*\d+(?:\.\d+)?)\b",
        r"\b(R\s*[-]?\s*\d+(?:\.\d+)?)\b[^\n]{0,100}?(?:roof|purlin)",
    ), 0.91, ("specification", "roof_plan", "wall_section"), ("07", "13")),
    FieldRule("Insulation", "Roof Insulation Thickness", (
        r"roof\s+insulation[^\n]{0,140}?\b(\d+(?:\.\d+)?(?:-\d+/\d+)?\s*(?:inches|inch|in\.?|\"))\b",
        r"\b(\d+(?:\.\d+)?(?:-\d+/\d+)?\s*(?:inches|inch|in\.?|\"))\b[^\n]{0,80}?(?:roof\s+insulation|roof\s+batt)",
    ), 0.84, ("specification", "roof_plan", "wall_section"), ("07", "13")),
    FieldRule("Insulation", "Roof Insulation Facing", (
        r"roof\s+insulation[^\n]{0,180}?\b(white\s+vinyl|vinyl[- ]faced|foil[- ]faced|FSK|WMP[- ]?VR|VRR|vapor\s+retarder)\b",
        r"\b(white\s+vinyl|vinyl[- ]faced|foil[- ]faced|FSK|WMP[- ]?VR|VRR)\b[^\n]{0,100}?roof",
    ), 0.84, ("specification", "roof_plan", "wall_section"), ("07", "13")),
    FieldRule("Insulation", "Wall Insulation Type", (
        r"wall\s+insulation(?:\s+system)?[^\n]{0,100}?\b(fiberglass|blanket|batt|rigid(?:[- ]board)?|polyisocyanurate|polyiso|spray[- ]foam|insulated\s+metal\s+panel|IMP|liner\s+system)\b",
        r"\b(fiberglass|blanket|batt|rigid(?:[- ]board)?|polyisocyanurate|polyiso|spray[- ]foam|insulated\s+metal\s+panel|IMP)\b[^\n]{0,100}?wall",
    ), 0.86, ("specification", "elevation", "wall_section"), ("07", "13")),
    FieldRule("Insulation", "Wall Insulation R-Value", (
        r"wall\s+insulation(?:\s+system)?[^\n]{0,140}?\b(R\s*[-]?\s*\d+(?:\.\d+)?)\b",
        r"\b(R\s*[-]?\s*\d+(?:\.\d+)?)\b[^\n]{0,100}?(?:wall|girt)",
    ), 0.91, ("specification", "elevation", "wall_section"), ("07", "13")),
    FieldRule("Insulation", "Wall Insulation Thickness", (
        r"wall\s+insulation[^\n]{0,140}?\b(\d+(?:\.\d+)?(?:-\d+/\d+)?\s*(?:inches|inch|in\.?|\"))\b",
        r"\b(\d+(?:\.\d+)?(?:-\d+/\d+)?\s*(?:inches|inch|in\.?|\"))\b[^\n]{0,80}?(?:wall\s+insulation|wall\s+batt)",
    ), 0.84, ("specification", "elevation", "wall_section"), ("07", "13")),
    FieldRule("Insulation", "Wall Insulation Facing", (
        r"wall\s+insulation[^\n]{0,180}?\b(white\s+vinyl|vinyl[- ]faced|foil[- ]faced|FSK|WMP[- ]?VR|VRR|vapor\s+retarder)\b",
        r"\b(white\s+vinyl|vinyl[- ]faced|foil[- ]faced|FSK|WMP[- ]?VR|VRR)\b[^\n]{0,100}?wall",
    ), 0.84, ("specification", "elevation", "wall_section"), ("07", "13")),
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
    FieldRule("Project", "Project Name", (
        r"(?:project\s+name|project)\s*[:=\-]?\s*([^\n]{5,100})",
    ), 0.70, ("general_notes", "specification")),
    FieldRule("Project", "Bid Due", (
        r"(?:bid\s+due|bids?\s+(?:will\s+be\s+)?received(?:\s+until)?)\s*[:=\-]?\s*([^\n.;]{5,80})",
    ), 0.78, ("general_notes", "specification")),
    FieldRule("Geometry", "BSW Eave Height", (
        r"(?:back\s+sidewall|bsw)\s+(?:eave\s+)?height\s*[:=\-]?\s*((?:\d+\s*['’]\s*(?:\d+(?:\s+\d+/\d+)?\s*[\"”])?)|(?:\d+(?:\.\d+)?\s*(?:ft|feet)))",
    ), 0.90, ("elevation", "wall_section", "structural_notes")),
    FieldRule("Geometry", "FSW Eave Height", (
        r"(?:front\s+sidewall|fsw)\s+(?:eave\s+)?height\s*[:=\-]?\s*((?:\d+\s*['’]\s*(?:\d+(?:\s+\d+/\d+)?\s*[\"”])?)|(?:\d+(?:\.\d+)?\s*(?:ft|feet)))",
    ), 0.90, ("elevation", "wall_section", "structural_notes")),
    FieldRule("Geometry", "Ridge Offset", (
        r"ridge\s+offset\s*[:=\-]?\s*((?:\d+\s*['’]\s*(?:\d+(?:\s+\d+/\d+)?\s*[\"”])?)|(?:\d+(?:\.\d+)?\s*(?:ft|feet)))",
    ), 0.88, ("roof_plan", "elevation", "framing_plan")),
    FieldRule("Geometry", "Front Roof Slope", (
        r"(?:front|fsw)\s+roof\s+(?:slope|pitch)\s*[:=\-]?\s*([0-9.]+\s*(?::|/)\s*12)",
    ), 0.93, ("roof_plan", "elevation")),
    FieldRule("Geometry", "Back Roof Slope", (
        r"(?:back|bsw)\s+roof\s+(?:slope|pitch)\s*[:=\-]?\s*([0-9.]+\s*(?::|/)\s*12)",
    ), 0.93, ("roof_plan", "elevation")),
    FieldRule("Codes & Loads", "Dead Load", (
        r"(?:roof\s+)?dead\s+load\s*[:=\-–—]?\s*(\d+(?:\.\d+)?)\s*psf",
    ), 0.91, ("structural_notes", "specification"), ("13",)),
    FieldRule("Geometry", "Building Orientation", (
        r"(?:building\s+orientation|frame\s+configuration|roof\s+configuration)\s*[:=\-]?\s*(gable|single[- ]slope|double[- ]slope|lean[- ]to|multi[- ]span)",
        r"\b(gable|single[- ]slope|double[- ]slope|lean[- ]to|multi[- ]span)\s+(?:building|frame|roof)",
    ), 0.88, ("roof_plan", "elevation", "framing_plan", "structural_notes"), ("13",)),
    FieldRule("Framing", "Frame Type", (
        r"(?:frame\s+type|primary\s+framing|structural\s+system)\s*[:=\-]?\s*(clear[- ]span|multi[- ]span|modular|rigid\s+frame|single[- ]slope|lean[- ]to)",
        r"\b(clear[- ]span|multi[- ]span|modular|rigid\s+frame)\s+(?:frame|framing|building)",
    ), 0.88, ("framing_plan", "structural_notes", "specification"), ("05", "13")),
    FieldRule("Geometry", "Total Square Feet", (
        r"(?:total\s+(?:building\s+)?area|gross\s+area|building\s+area|total\s+square\s+feet)\s*[:=\-]?\s*([\d,]+(?:\.\d+)?\s*(?:s\.?f\.?|sq\.?\s*ft\.?|square\s+feet))",
    ), 0.93, ("general_notes", "roof_plan", "foundation_plan")),
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


def normalize_field_value(field_name: str, value: str) -> str:
    """Normalize estimator values for display and reliable duplicate/conflict comparison."""
    v = normalize_space(value)
    low = v.lower()
    panel_aliases = {
        "r panel": "R-Panel", "r-panel": "R-Panel", "rpanel": "R-Panel",
        "pbr": "PBR Panel", "pbr panel": "PBR Panel",
        "imp": "Insulated Metal Panel", "insulated metal panel": "Insulated Metal Panel",
    }
    if field_name in {"Roof Panel Type", "Wall Panel Type"}:
        key = re.sub(r"[^a-z0-9]+", " ", low).strip()
        for alias, canonical in panel_aliases.items():
            if alias in key:
                return canonical
    if field_name in {"Basic Wind Speed"}:
        m = re.search(r"(\d{2,3})", v)
        return f"{m.group(1)} mph" if m else v
    if field_name in {"Ground Snow Load", "Roof Snow Load", "Roof Live Load", "Dead Load", "Collateral Load"}:
        m = re.search(r"(\d+(?:\.\d+)?)", v)
        return f"{m.group(1)} psf" if m else v
    if field_name in {"Roof Slope", "Front Roof Slope", "Back Roof Slope"}:
        m = re.search(r"([0-9.]+)\s*(?::|/)\s*12", v)
        if m:
            return f"{m.group(1)}:12"
        m = re.search(r"([0-9.]+)\s*(?:in(?:ch)?(?:es)?|\")\s+per\s+(?:foot|1[\'’]-?0)", v, re.I)
        if m:
            return f"{m.group(1)}:12"
    if field_name in {"Building Width", "Building Length", "Eave Height", "BSW Eave Height", "FSW Eave Height", "Ridge Offset"}:
        v = v.replace("feet", "ft").replace("foot", "ft")
    if field_name in {"Risk Category"}:
        roman = {"1":"I","2":"II","3":"III","4":"IV"}
        return roman.get(v.strip(), v.upper())
    if field_name in {"Wind Exposure", "Site Class", "Seismic Design Category"}:
        return v.upper()
    if field_name in {"Roof Insulation R-Value", "Wall Insulation R-Value", "Roof Insulation", "Wall Insulation"}:
        m = re.search(r"R\s*-?\s*(\d+(?:\.\d+)?)", v, re.I)
        return f"R-{m.group(1)}" if m else v
    return v


def normalized_compare(value: str, field_name: str | None = None) -> str:
    canonical = normalize_field_value(field_name or "", value)
    return re.sub(r"[^a-z0-9.]", "", canonical.lower())


def classify_page(text: str) -> tuple[str, str | None, str | None, str | None]:
    upper = text.upper()
    division = None
    for number in ("03", "05", "07", "08", "09", "13"):
        # CSI priority: 13 34 19, 05 12 00, 05 50 00, 07 21 00, 07 41/42/62/72

        if re.search(rf"\bDIVISION\s+{number}\b", upper) or re.search(rf"\b{number}\s+\d{{2}}\s+\d{{2}}\b", upper):
            division = number
            break

    categories = (
        ("structural_notes", ("STRUCTURAL GENERAL NOTES", "DESIGN CRITERIA", "DESIGN LOADS")),
        ("general_notes", ("GENERAL NOTES",)),
        ("door_schedule", ("DOOR SCHEDULE", "OVERHEAD DOOR SCHEDULE", "WINDOW SCHEDULE")),
        ("roof_plan", ("ROOF PLAN",)),
        ("framing_plan", ("ROOF FRAMING PLAN", "MEZZANINE FRAMING PLAN", "FRAMING PLAN")),
        ("foundation_plan", ("FOUNDATION PLAN",)),
        ("elevation", ("EXTERIOR ELEVATION", "BUILDING ELEVATION", "ELEVATIONS")),
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


def _validate_targeted_value(field_name: str, value: str, excerpt: str) -> str | None:
    value = normalize_space(value)
    compact = value.lower()
    numeric_fields = {"Building Width", "Building Length", "Eave Height", "BSW Eave Height", "FSW Eave Height", "Ridge Offset"}
    if field_name in numeric_fields and not re.search(r"\d\s*(?:ft|feet|['’])|\d+\s*[-']\s*\d+", value, re.I):
        return None
    if field_name in {"Roof Slope", "Front Roof Slope", "Back Roof Slope"} and not re.fullmatch(r"[0-9.]+\s*(?::|/)\s*12", value):
        return None
    if field_name == "Building Code" and re.fullmatch(r"(?:19|20)\d{2}", value):
        value = value + " IBC"
    if field_name == "Occupancy":
        m = re.search(r"\b([A-HI-RS-U](?:-\d)?)\b", value.upper())
        if not m: return None
        value = m.group(1)
    if field_name == "Roof Panel Type":
        allowed = re.search(r"(standing\s+seam|ssr|pbr|r[- ]?panel|concealed[- ]fastener|loc\s+seam|trapezoidal)", value, re.I)
        if not allowed: return None
        value = allowed.group(1)
    if field_name == "Wall Panel Type":
        allowed = re.search(r"(pbr|r[- ]?panel|insulated\s+metal\s+panel|imp|concealed[- ]fastener|metal\s+panel\s+system)", value, re.I)
        if not allowed: return None
        value = allowed.group(1)
    if field_name in {"Gutters", "Downspouts", "Roof Curbs", "Canopies", "Framed Openings", "Ridge Vents"}:
        # Accessory results must contain an actionable quantity, size, type, or explicit scope statement.
        if not re.search(r"\d|by\s+pemb|pemb\s+(?:manufacturer|supplier)|provide|include|exclude|not\s+included|size|x\s*\d|gutter|downspout|curb|canop|framed\s+opening|ridge\s+vent", value, re.I):
            return None
        if re.search(r"zinc-coated|galvanized.*steel sheet|aluminum-zinc", value, re.I) and not re.search(r"\d|size", value, re.I):
            return None
    if len(value) > 100 and field_name not in {"Canopies", "Framed Openings"}:
        return None
    return value


CORE_ESTIMATOR_FIELDS = {
    "Project Address", "Bid Due", "Building Width", "Building Length", "Total Square Feet",
    "Frame Type", "Building Orientation", "Ridge Offset", "BSW Eave Height", "FSW Eave Height", "Eave Height",
    "Roof Panel Type", "Front Roof Slope", "Back Roof Slope", "Roof Slope", "Roof Panel Gauge",
    "Wall Panel Type", "Wall Panel Gauge", "Roof Insulation", "Wall Insulation",
    "Roof Insulation Type", "Roof Insulation R-Value", "Roof Insulation Thickness", "Roof Insulation Facing",
    "Wall Insulation Type", "Wall Insulation R-Value", "Wall Insulation Thickness", "Wall Insulation Facing", "Risk Category",
    "Building Code", "Roof Live Load", "Dead Load", "Collateral Load", "Ground Snow Load",
    "Roof Snow Load", "Basic Wind Speed", "Wind Exposure", "Site Class", "Seismic Design Category",
    "S1", "Ss", "Occupancy"
}


def extract_fields(text: str, page_type: str | None = None, division: str | None = None) -> list[dict]:
    # Search both original text and a line-normalized copy. The second form helps
    # when PDF extraction inserts line breaks between labels and values.
    variants: Iterable[str] = (text, re.sub(r"[\t\r]+", " ", text))
    found: list[dict] = []
    seen: set[tuple[str, str]] = set()
    # High-value cover-sheet values that commonly appear without explicit field labels.
    special_rules = (
        ("Project", "Project Address", r"\b(\d{2,6}\s+[A-Z0-9][A-Z0-9 .'-]{3,70}\s+(?:ROAD|RD|STREET|ST|AVENUE|AVE|DRIVE|DR|BOULEVARD|BLVD|LANE|LN|WAY|HIGHWAY|HWY),?\s+[A-Z .'-]{2,35},?\s+[A-Z]{2}(?:\s+\d{5})?)\b", 0.88),
        ("Geometry", "Total Square Feet", r"(?:total\s+(?:occupancy\s+)?area|building\s+area|total\s+square\s+feet)\s*[:=\-]?\s*([\d,]+(?:\.\d+)?\s*(?:s\.?f\.?|sq\.?\s*ft\.?|square\s+feet))", 0.92),
    )
    for category, field_name, pattern, confidence in special_rules:
        m = re.search(pattern, text, re.I | re.M)
        if m:
            value = normalize_field_value(field_name, normalize_space(m.group(1)))
            seen.add((field_name, normalized_compare(value, field_name)))
            found.append({"category": category, "field_name": field_name, "value": value, "confidence": confidence, "source_excerpt": normalize_space(text[max(0,m.start()-100):min(len(text),m.end()+140)])})
    for rule in FIELD_RULES:
        if rule.field_name not in CORE_ESTIMATOR_FIELDS:
            continue
        for variant in variants:
            matched = False
            for pattern in rule.patterns:
                match = re.search(pattern, variant, flags=re.IGNORECASE | re.MULTILINE)
                if not match:
                    continue
                value = normalize_space(match.group(1))
                excerpt_start = max(0, match.start() - 140)
                excerpt_end = min(len(variant), match.end() + 220)
                excerpt = normalize_space(variant[excerpt_start:excerpt_end])
                value = _validate_targeted_value(rule.field_name, value, excerpt)
                if value:
                    value = normalize_field_value(rule.field_name, value)
                if not value or len(value) > 220:
                    continue
                key = (rule.field_name, normalized_compare(value, rule.field_name))
                if key in seen:
                    matched = True
                    break
                seen.add(key)
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
                if value:
                    value = normalize_field_value(rule.field_name, value)
                if not value:
                    continue
                key = (rule.field_name, normalized_compare(value, rule.field_name))
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
