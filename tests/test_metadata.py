from io import StringIO

import pytest

from paramstudy.metadata import ColumnMetaRegistry, make_registry


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
