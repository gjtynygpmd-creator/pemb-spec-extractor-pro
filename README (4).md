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


def test_rejects_material_paragraph_as_accessory():
    values = as_map("Downspouts: Zinc-coated (galvanized) or aluminum-zinc alloy-coated steel sheet")
    assert "Downspouts" not in values

def test_normalizes_occupancy_group():
    values = as_map("IBC Occupancy Type: S-1")
    assert values["Occupancy"] == "S-1"

def test_separate_sidewall_geometry():
    values = as_map("BSW Eave Height: 24'-0\"\nFSW Eave Height: 30'-0\"\nRidge Offset: 18'-0\"")
    assert values["BSW Eave Height"].startswith("24")
    assert values["FSW Eave Height"].startswith("30")
    assert values["Ridge Offset"].startswith("18")


def test_detailed_roof_insulation_fields():
    text = 'Roof insulation system: fiberglass blanket insulation, R-30, 6 inch thickness, white vinyl facing.'
    fields = extract_fields(text, page_type='specification', division='07')
    found = {f['field_name']: f['value'] for f in fields}
    assert found['Roof Insulation R-Value'].replace(' ', '').upper() == 'R-30'
    assert 'fiberglass' in found['Roof Insulation Type'].lower()
    assert '6' in found['Roof Insulation Thickness']
    assert 'vinyl' in found['Roof Insulation Facing'].lower()


def test_detailed_wall_insulation_fields():
    text = 'Wall insulation: foil-faced batt insulation R-19, 4 inch thickness.'
    fields = extract_fields(text, page_type='wall_section', division='07')
    found = {f['field_name']: f['value'] for f in fields}
    assert found['Wall Insulation R-Value'].replace(' ', '').upper() == 'R-19'
    assert 'batt' in found['Wall Insulation Type'].lower()
    assert '4' in found['Wall Insulation Thickness']
    assert 'foil' in found['Wall Insulation Facing'].lower()


def test_geometry_field_test_release():
    text = """ROOF PLAN\nBuilding Width: 150'-0"\nBuilding Length: 200'-0"\nFrame Type: Clear Span\nBuilding Orientation: Gable\nRidge Offset: 75'-0"\nFront Roof Slope: 0.25:12\nBack Roof Slope: 0.25:12\nFSW Eave Height: 24'-0"\nBSW Eave Height: 24'-0"""
    values = {x["field_name"]: x["value"] for x in extract_fields(text, page_type="roof_plan", division="13")}
    assert values["Building Width"].startswith("150")
    assert values["Building Length"].startswith("200")
    assert values["Frame Type"].lower() == "clear span"
    assert values["Building Orientation"].lower() == "gable"
    assert values["Front Roof Slope"] == "0.25:12"
    assert values["Back Roof Slope"] == "0.25:12"


def test_semantic_normalization_avoids_false_conflicts():
    from app.services.document_analysis import normalize_field_value, normalized_compare
    assert normalize_field_value("Basic Wind Speed", "115") == "115 mph"
    assert normalize_field_value("Ground Snow Load", "20") == "20 psf"
    assert normalize_field_value("Wall Panel Type", "R PANEL") == "R-Panel"
    assert normalized_compare("R-30", "Roof Insulation R-Value") == normalized_compare("R 30", "Roof Insulation R-Value")


def test_accessory_scope_is_clean_value():
    text = 'Provide gutters, downspouts, gable trim, and eave trim by PEMB manufacturer.'
    fields = extract_fields(text, page_type='specification', division='13')
    found = {f['field_name']: f['value'] for f in fields}
    assert found['Gutters'] == 'Included'
    assert found['Downspouts'] == 'Included'


def test_excluded_accessory_is_normalized():
    text = 'Gutters and downspouts are excluded from the PEMB supplier scope and provided by others.'
    fields = extract_fields(text, page_type='specification', division='13')
    found = {f['field_name']: f['value'] for f in fields}
    assert found['Gutters'] == 'Excluded'
    assert found['Downspouts'] == 'Excluded'


def test_panel_values_are_estimator_ready():
    text = 'Provide 24 gauge mechanically seamed standing seam roof panels and 26 gauge PBR wall panels.'
    fields = extract_fields(text, page_type='specification', division='13')
    found = {f['field_name']: f['value'] for f in fields}
    assert found['Roof Panel Type'] == 'Standing Seam'
    assert found['Wall Panel Type'] == 'PBR Panel'
    assert found['Roof Panel Gauge'] == '24 ga'
    assert found['Wall Panel Gauge'] == '26 ga'
