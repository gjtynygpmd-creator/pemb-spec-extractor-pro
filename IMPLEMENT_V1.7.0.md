"""Tests for the schema loader that reconciles both extraction paths.

Run from backend/:
    DATABASE_URL=postgresql://unused PYTHONPATH=. python tests/test_schema_loader.py
"""

from app.services import schema_loader as S


def test_loads_all_fields():
    assert S.field_count() >= 90
    assert S.version()


def test_resolve_by_id_name_alias_and_regex_name():
    # by field_id
    assert S.resolve("basic_wind_speed").name == "Basic Wind Speed"
    # by exact display name
    assert S.resolve("FSW Eave Height").field_id == "fsw_eave_height"
    # by alias
    assert S.resolve("Vult").field_id == "basic_wind_speed"
    # by regex engine name that differs from the schema display name
    assert S.resolve("Site Class").field_id == "seismic_site_class"
    assert S.resolve("Building Code").field_id == "building_code_ibc"
    assert S.resolve("Overhead Doors").field_id == "overhead_doors"
    assert S.resolve("Roof Insulation").field_id == "roof_insulation"
    assert S.resolve("Ss").field_id == "seismic_ss"


def test_unknown_passes_through():
    # A regex-only field not in the schema keeps its name and is not force-categorized.
    assert S.resolve("Building Orientation") is None
    assert S.canonical_name("Building Orientation") == "Building Orientation"


def test_enum_coercion():
    assert S.coerce_value("wind_exposure", "c") == "C"
    assert S.coerce_value("risk_category", "II") == "II"
    # non-enum returns trimmed value unchanged
    assert S.coerce_value("basic_wind_speed", " 115 mph ") == "115 mph"


def test_vision_instructions_are_schema_driven():
    text = S.build_vision_instructions()
    assert "basic_wind_speed" in text
    assert "[Design Criteria - Wind]" in text
    assert "field_id" in text


if __name__ == "__main__":
    test_loads_all_fields()
    test_resolve_by_id_name_alias_and_regex_name()
    test_unknown_passes_through()
    test_enum_coercion()
    test_vision_instructions_are_schema_driven()
    print("All schema loader tests passed.")
