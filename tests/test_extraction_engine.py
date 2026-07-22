from app.services.document_analysis import extract_fields


def as_map(text: str) -> dict[str, str]:
    return {item["field_name"]: item["value"] for item in extract_fields(text, "unclassified", None)}


def test_universal_design_load_table():
    values = as_map("""
    DESIGN CRITERIA
    Applicable Building Code: 2024 Ohio Building Code
    Risk Category: III
    Ultimate Design Wind Speed: 114 MPH
    Wind Exposure Category: C
    Ground Snow Load: 20 PSF
    Flat Roof Snow Load: 20 PSF
    Roof Live Load: 22 PSF
    Collateral Load: 5 PSF
    Seismic Design Category: B
    """)
    assert values["Building Code"] in {"2024 Ohio Building Code", "Ohio Building Code"}
    assert values["Risk Category"] == "III"
    assert values["Basic Wind Speed"].startswith("114")
    assert values["Wind Exposure"] == "C"
    assert values["Ground Snow Load"].startswith("20")
    assert values["Roof Snow Load"].startswith("20")
    assert values["Roof Live Load"].startswith("22")
    assert values["Collateral Load"].startswith("5")
    assert values["Seismic Design Category"] == "B"


def test_rejects_definition_text_as_geometry():
    values = as_map("Building Width: Measured from outside to outside of sidewalls")
    assert "Building Width" not in values
