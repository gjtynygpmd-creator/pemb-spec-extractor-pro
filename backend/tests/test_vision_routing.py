"""Regression tests for v1.9.0 page routing and the wind-speed misread fix.

These run without any cloud infrastructure or API key. Run from backend/:
    DATABASE_URL=postgresql://unused python -m pytest tests/test_vision_routing.py
or standalone:
    DATABASE_URL=postgresql://unused python tests/test_vision_routing.py
"""

from app.services.document_analysis import (
    classify_page,
    extract_fields,
    page_has_rich_text_layer,
    count_rich_text_labels,
)

SPEC_TEXT = """SECTION 13 34 19 METAL BUILDING SYSTEMS
Governing Building Code: 2018 IBC
Risk Category: II
Basic Wind Speed: 115 mph
Wind Exposure Category: C
Ground Snow Load: 30 psf
Roof Snow Load: 24 psf
Roof Live Load: 20 psf
Collateral Load: 5 psf
Seismic Design Category: B
Roof Insulation System: R-19 fiberglass blanket, vinyl-faced
"""

# Drawing text as PyMuPDF returns it: labels and values in separate spatial runs.
DRAWING_TEXT = """S-001
STRUCTURAL NOTES
EAVE HEIGHT
BUILDING WIDTH
BASIC WIND SPEED
24'-0"
60'-0"
115 MPH
"""


def _field(fields, name):
    return [f["value"] for f in fields if f["field_name"] == name]


def test_spec_page_extracts_and_is_rich():
    pt, div, *_ = classify_page(SPEC_TEXT)
    fields = extract_fields(SPEC_TEXT, page_type=pt, division=div)
    assert page_has_rich_text_layer(SPEC_TEXT) is True
    assert _field(fields, "Basic Wind Speed") == ["115 mph"]
    assert _field(fields, "Risk Category") == ["II"]
    assert len(fields) >= 12


def test_eave_height_not_misread_as_wind_speed():
    # The core v1.9.0 bug fix: a bare dimension after the wind-speed label must not
    # be captured as the wind speed value.
    pt, div, *_ = classify_page(DRAWING_TEXT)
    fields = extract_fields(DRAWING_TEXT, page_type=pt, division=div)
    assert _field(fields, "Basic Wind Speed") != ["24 mph"]


def test_drawing_routes_to_vision_not_regex():
    # A sparse drawing page should not qualify for the regex fast path, so the worker
    # routes it to vision. It fails on length and/or label density.
    assert page_has_rich_text_layer(DRAWING_TEXT) is False
    fails_length = len(DRAWING_TEXT.strip()) < 200
    fails_labels = count_rich_text_labels(DRAWING_TEXT) < 3
    assert fails_length or fails_labels


if __name__ == "__main__":
    test_spec_page_extracts_and_is_rich()
    test_eave_height_not_misread_as_wind_speed()
    test_drawing_routes_to_vision_not_regex()
    print("All v1.9.0 routing tests passed.")
