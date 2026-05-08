import pytest

from paramstudy.unit import (
    CompoundUnit,
    SIPrefix,
    SimpleUnit,
    Unitless,
    parse_unit,
    unit_from_dict,
    unit_to_dict,
)


class TestSimpleUnit:
    def test_basic_rendering(self):
        assert SimpleUnit("s").render() == "s"
        assert SimpleUnit("s", SIPrefix.NANO).render() == "ns"
        assert SimpleUnit("m", SIPrefix.MICRO).render() == "um"

    def test_dimension_rendering(self):
        assert SimpleUnit("m", SIPrefix.MICRO, dimension=2).render() == "um^2"
        assert SimpleUnit("s", SIPrefix.NANO, dimension=3).render() == "ns^3"

    def test_factor_to_base(self):
        assert SimpleUnit("m", SIPrefix.MILLI).factor_to_base == pytest.approx(1e-3)
        assert SimpleUnit("m", SIPrefix.KILO).factor_to_base == pytest.approx(1e3)
        assert SimpleUnit("m", SIPrefix.MICRO, dimension=2).factor_to_base == pytest.approx(1e-12)

    def test_with_prefix(self):
        unit = SimpleUnit("s", SIPrefix.NANO)
        result = unit.with_prefix(SIPrefix.PICO)
        assert result.render() == "ps"
        assert result.symbol == "s"
        assert result.dimension == 1

    def test_with_dimension(self):
        unit = SimpleUnit("m", SIPrefix.MILLI)
        result = unit.with_dimension(2)
        assert result.render() == "mm^2"
        assert result.prefix is SIPrefix.MILLI

    def test_str_matches_render(self):
        unit = SimpleUnit("eV", SIPrefix.MEGA)
        assert str(unit) == unit.render()

    def test_empty_symbol_raises(self):
        with pytest.raises(ValueError, match="symbol must be non-empty"):
            SimpleUnit("")

    def test_zero_dimension_raises(self):
        with pytest.raises(ValueError, match="dimension must not be 0"):
            SimpleUnit("m", dimension=0)

    def test_equality(self):
        a = SimpleUnit("s", SIPrefix.NANO)
        b = SimpleUnit("s", SIPrefix.NANO)
        assert a == b
        assert a != SimpleUnit("s", SIPrefix.PICO)


class TestCompoundUnit:
    def test_render_single(self):
        unit = CompoundUnit([SimpleUnit("m", SIPrefix.MILLI)])
        assert unit.render() == "mm"

    def test_render_multiple(self):
        unit = CompoundUnit([SimpleUnit("m", SIPrefix.MILLI), SimpleUnit("rad", SIPrefix.MILLI)])
        assert unit.render() == "mm mrad"

    def test_custom_separator(self):
        unit = CompoundUnit([SimpleUnit("m"), SimpleUnit("s")], separator=".")
        assert unit.render() == "m.s"

    def test_tuple_input(self):
        unit = CompoundUnit((SimpleUnit("eV", SIPrefix.MEGA),))
        assert unit.render() == "MeV"

    def test_str_matches_render(self):
        unit = CompoundUnit([SimpleUnit("m"), SimpleUnit("rad")])
        assert str(unit) == unit.render()

    def test_empty_units_raises(self):
        with pytest.raises(ValueError, match="units must be non-empty"):
            CompoundUnit([])


class TestUnitless:
    def test_default_rendering(self):
        assert Unitless().render() == "a.u."

    def test_custom_label(self):
        assert Unitless(label="arb. units").render() == "arb. units"

    def test_str_matches_render(self):
        assert str(Unitless()) == "a.u."


class TestParseUnit:
    def test_simple_base_unit(self):
        unit = parse_unit("m")
        assert isinstance(unit, SimpleUnit)
        assert unit.render() == "m"

    def test_simple_with_prefix(self):
        unit = parse_unit("ns")
        assert isinstance(unit, SimpleUnit)
        assert unit.render() == "ns"

    def test_simple_with_dimension(self):
        unit = parse_unit("mm^2")
        assert isinstance(unit, SimpleUnit)
        assert unit.render() == "mm^2"

    def test_compound(self):
        unit = parse_unit("mm mrad")
        assert isinstance(unit, CompoundUnit)
        assert unit.render() == "mm mrad"

    def test_unitless_au(self):
        unit = parse_unit("a.u.")
        assert isinstance(unit, Unitless)
        assert unit.render() == "a.u."

    def test_unitless_arb(self):
        unit = parse_unit("arb.")
        assert isinstance(unit, Unitless)
        assert unit.render() == "arb."

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            parse_unit("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            parse_unit("   ")

    def test_unrecognized_raises(self):
        with pytest.raises(ValueError, match="Cannot parse unit"):
            parse_unit("xyzzy")

    def test_strips_whitespace(self):
        assert parse_unit("  ns  ").render() == "ns"

    def test_division_simple(self):
        unit = parse_unit("m/s")
        assert isinstance(unit, CompoundUnit)
        assert unit.render() == "m/s"

    def test_division_with_prefix(self):
        unit = parse_unit("eV/c")
        assert unit.render() == "eV/c"

    def test_division_with_dimension(self):
        unit = parse_unit("W/m^2")
        assert unit.render() == "W/m^2"

    def test_division_denom_spaces(self):
        unit = parse_unit("eV/m s")
        assert unit.render() == "eV/m s"

    def test_division_no_numerator(self):
        unit = parse_unit("/s")
        assert unit.render() == "1/s"

    def test_division_with_space_around_slash(self):
        unit = parse_unit("m / s")
        assert unit.render() == "m/s"

    def test_neg_dim_simple_renders_correctly(self):
        unit = SimpleUnit("s", dimension=-1)
        assert unit.render() == "s^-1"


class TestCompoundUnitFactorToBase:
    def test_product(self):
        cu = CompoundUnit([SimpleUnit("m", SIPrefix.MILLI), SimpleUnit("rad", SIPrefix.MILLI)])
        # mm mrad: 1e-3 * 1e-3 = 1e-6
        assert cu.factor_to_base == pytest.approx(1e-6)

    def test_ratio(self):
        cu = CompoundUnit([SimpleUnit("eV", SIPrefix.MEGA), SimpleUnit("c", dimension=-1)])
        # MeV/c: 1e6 * 1 = 1e6
        assert cu.factor_to_base == pytest.approx(1e6)

    def test_neg_dim_factor(self):
        # 1/ms: factor = 1 / 1e-3 = 1e3
        cu = CompoundUnit([SimpleUnit("s", SIPrefix.MILLI, dimension=-1)])
        assert cu.factor_to_base == pytest.approx(1e3)


class TestUnitDictRoundtrip:
    def test_simple_roundtrip(self):
        original = SimpleUnit("eV", SIPrefix.GIGA)
        restored = unit_from_dict(unit_to_dict(original))
        assert restored == original
        assert restored.render() == original.render()

    def test_simple_with_dimension_roundtrip(self):
        original = SimpleUnit("m", SIPrefix.MILLI, dimension=2)
        restored = unit_from_dict(unit_to_dict(original))
        assert restored == original

    def test_compound_roundtrip(self):
        original = CompoundUnit(
            [SimpleUnit("m", SIPrefix.MILLI), SimpleUnit("rad", SIPrefix.MILLI)]
        )
        restored = unit_from_dict(unit_to_dict(original))
        assert restored.render() == original.render()

    def test_unitless_roundtrip(self):
        original = Unitless(label="custom")
        restored = unit_from_dict(unit_to_dict(original))
        assert restored.render() == original.render()

    def test_none_to_dict(self):
        assert unit_to_dict(None) is None

    def test_invalid_kind_raises(self):
        with pytest.raises(ValueError, match="Unknown unit mapping kind"):
            unit_from_dict({"kind": "bogus"})

    def test_simple_missing_symbol_raises(self):
        with pytest.raises(ValueError, match="non-empty 'symbol'"):
            unit_from_dict({"kind": "simple", "prefix": "NANO"})

    def test_simple_invalid_prefix_raises(self):
        with pytest.raises(ValueError, match="Invalid SI prefix"):
            unit_from_dict({"kind": "simple", "symbol": "m", "prefix": "BOGUS"})

    def test_compound_with_neg_dim_roundtrip(self):
        # eV/c: positive + negative dimension
        original = CompoundUnit(
            [SimpleUnit("eV", SIPrefix.MEGA), SimpleUnit("c", dimension=-1)]
        )
        restored = unit_from_dict(unit_to_dict(original))
        assert restored.render() == original.render()
        assert restored.factor_to_base == pytest.approx(original.factor_to_base)

    def test_compound_bad_units_raises(self):
        with pytest.raises(ValueError, match="sequence"):
            unit_from_dict({"kind": "compound", "units": "not-a-sequence"})


class TestSIPrefix:
    def test_none_symbol_empty(self):
        assert SIPrefix.NONE.symbol == ""

    def test_none_factor_one(self):
        assert SIPrefix.NONE.factor == pytest.approx(1.0)

    def test_known_prefix(self):
        assert SIPrefix.KILO.factor == pytest.approx(1000.0)
        assert SIPrefix.MILLI.factor == pytest.approx(0.001)
