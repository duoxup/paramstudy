from io import StringIO

import pytest

from paramstudy.metadata import ColumnMeta, ColumnMetaRegistry, make_registry
from paramstudy.unit import CompoundUnit, SIPrefix, SimpleUnit, Unitless


def test_make_registry_accepts_compact_and_json_specs():
    registry = make_registry(
        {
            "energy": ["Beam energy", "E", "MeV", "GeV"],
            "emit": {"label": "Emittance", "symbol": "eps", "unit": "mm mrad"},
            "area": ["Area", "A", "mm^2", "um^2"],
        }
    )

    assert registry.get("energy").display_name("energy") == "Beam energy"
    assert registry.get("energy").display_name("energy", prefer_symbol=True) == "E"
    assert registry.get("energy").unit.render() == "MeV"
    assert registry.get("energy").preferred_unit.render() == "GeV"
    assert registry.get("emit").unit.render() == "mm mrad"
    assert registry.get("area").preferred_unit.render() == "um^2"
    assert registry.get("missing").display_name("missing") == "missing"


def test_registry_json_roundtrip():
    registry = make_registry({"energy": ["Beam energy", "E", "MeV", "GeV"]})

    buffer = StringIO()
    registry.to_json(buffer)
    buffer.seek(0)

    restored = ColumnMetaRegistry.from_json(buffer)

    assert restored.get("energy").unit.render() == "MeV"
    assert restored.get("energy").preferred_unit.render() == "GeV"


def test_preferred_unit_requires_unit():
    with pytest.raises(ValueError, match="preferred_unit requires"):
        make_registry({"bad": [None, None, None, "ps"]})


def test_csv_roundtrip_to_file(tmp_path):
    registry = make_registry(
        {
            "energy": ["Beam energy", "E", "MeV", "GeV"],
            "charge": ["Charge", "Q", "pC"],
            "emit": {"label": "Emittance", "symbol": "eps", "unit": "mm mrad"},
        }
    )
    csv_path = tmp_path / "meta.csv"
    registry.to_csv(csv_path)

    restored = ColumnMetaRegistry.from_csv(csv_path)

    assert restored.get("energy").label == "Beam energy"
    assert restored.get("energy").symbol == "E"
    assert restored.get("energy").unit.render() == "MeV"
    assert restored.get("energy").preferred_unit.render() == "GeV"
    assert restored.get("charge").unit.render() == "pC"
    assert restored.get("charge").preferred_unit is None
    assert restored.get("emit").unit.render() == "mm mrad"


def test_csv_roundtrip_stringio():
    registry = make_registry({"energy": ["Beam energy", "E", "MeV", "GeV"]})

    buffer = StringIO()
    registry.to_csv(buffer)
    buffer.seek(0)

    restored = ColumnMetaRegistry.from_csv(buffer)

    assert restored.get("energy").label == "Beam energy"
    assert restored.get("energy").unit.render() == "MeV"


def test_csv_empty_registry(tmp_path):
    registry = ColumnMetaRegistry()
    csv_path = tmp_path / "empty.csv"
    registry.to_csv(csv_path)

    restored = ColumnMetaRegistry.from_csv(csv_path)

    assert restored.get("anything").label is None


def test_csv_missing_column_field():
    buffer = StringIO("column,label,symbol,unit,preferred_unit\n,missing column,,\n")

    with pytest.raises(ValueError, match="missing non-empty 'column'"):
        ColumnMetaRegistry.from_csv(buffer)


def test_csv_preserves_unitless():
    registry = make_registry({"norm": ["Normalized", "N", "a.u."]})
    buffer = StringIO()
    registry.to_csv(buffer)
    buffer.seek(0)

    restored = ColumnMetaRegistry.from_csv(buffer)

    assert restored.get("norm").unit.render() == "a.u."


def test_csv_partial_metadata():
    registry = make_registry({"minimal": ["Only label"]})
    buffer = StringIO()
    registry.to_csv(buffer)
    buffer.seek(0)

    restored = ColumnMetaRegistry.from_csv(buffer)

    assert restored.get("minimal").label == "Only label"
    assert restored.get("minimal").symbol is None
    assert restored.get("minimal").unit is None


def test_csv_preferred_unit_requires_unit():
    buffer = StringIO("column,label,symbol,unit,preferred_unit\nbad,,,,ps\n")

    with pytest.raises(ValueError, match="preferred_unit requires"):
        ColumnMetaRegistry.from_csv(buffer)


def test_csv_emits_warning_on_unrecognized_unit():
    buffer = StringIO("column,label,symbol,unit,preferred_unit\nbad,Bad,,Mev,\n")

    with pytest.warns(UserWarning, match="Unrecognized unit string"):
        registry = ColumnMetaRegistry.from_csv(buffer)

    # Fallback semantics preserved: parse failure becomes Unitless(label=value).
    assert isinstance(registry.get("bad").unit, Unitless)
    assert registry.get("bad").unit.render() == "Mev"


def test_csv_normalizes_compound_separator_with_warning():
    cu = CompoundUnit(
        (SimpleUnit("m", SIPrefix.MILLI), SimpleUnit("rad", SIPrefix.MILLI)),
        separator=".",
    )
    registry = ColumnMetaRegistry()
    registry.add("emit", ColumnMeta(label="Emit", unit=cu))

    buffer = StringIO()
    with pytest.warns(UserWarning, match="not CSV-roundtrippable"):
        registry.to_csv(buffer)
    buffer.seek(0)
    restored = ColumnMetaRegistry.from_csv(buffer)

    # Type preserved as CompoundUnit (no longer silently falls back to Unitless).
    restored_unit = restored.get("emit").unit
    assert isinstance(restored_unit, CompoundUnit)
    assert restored_unit.render() == "mm mrad"
