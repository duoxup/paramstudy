import pytest

from paramstudy.scale import autoscale_unit, resolve_compound_scale, scale_to_unit
from paramstudy.unit import CompoundUnit, SIPrefix, SimpleUnit, Unitless


def test_autoscale_simple_unit_ns_to_ps():
    scale = autoscale_unit([0.1, 0.2, 0.3], SimpleUnit("s", SIPrefix.NANO))

    assert scale.multiplier == pytest.approx(1000.0)
    assert scale.unit.render() == "ps"


def test_autoscale_simple_unit_keeps_reasonable_prefix():
    scale = autoscale_unit([1.0, 2.0, 3.0], SimpleUnit("m", SIPrefix.MILLI))

    assert scale.multiplier == pytest.approx(1.0)
    assert scale.unit.render() == "mm"


def test_autoscale_simple_unit_with_dimension():
    scale = autoscale_unit([1e-6, 2e-6, 3e-6], SimpleUnit("m", SIPrefix.MILLI, dimension=2))

    assert scale.multiplier == pytest.approx(1e6)
    assert scale.unit.render() == "um^2"


def test_autoscale_compound_unit_equal_distribution():
    unit = CompoundUnit([SimpleUnit("m", SIPrefix.MILLI), SimpleUnit("rad", SIPrefix.MILLI)])

    scale = autoscale_unit([1e-6, 2e-6, 3e-6], unit)

    assert scale.multiplier == pytest.approx(1e6)
    assert scale.unit.render() == "um urad"


def test_autoscale_does_not_scale_unitless():
    unit = Unitless()

    scale = autoscale_unit([1e-9, 2e-9, 3e-9], unit)

    assert scale.multiplier == pytest.approx(1.0)
    assert scale.unit is unit
    assert scale.unit.render() == "a.u."


def test_scale_to_preferred_simple_unit():
    scale = scale_to_unit(SimpleUnit("s", SIPrefix.NANO), SimpleUnit("s", SIPrefix.PICO))

    assert scale.multiplier == pytest.approx(1000.0)
    assert scale.unit.render() == "ps"


def test_resolve_compound_scale_pinned():
    # m^2 rad / s  ~1e6, pin rad→urad
    unit = CompoundUnit(
        [
            SimpleUnit("m", SIPrefix.MILLI, dimension=2),
            SimpleUnit("rad", SIPrefix.MILLI),
            SimpleUnit("s", dimension=-1),
        ]
    )
    scale = resolve_compound_scale([1e6, 2e6, 3e6], unit, pinned=["urad"])

    # rad component should be urad (pinned)
    for su in scale.unit.units:
        if su.symbol == "rad":
            assert su.prefix is SIPrefix.MICRO


def test_resolve_compound_scale_all_pinned():
    # MeV/c, pin both
    unit = CompoundUnit(
        [SimpleUnit("eV", SIPrefix.MEGA), SimpleUnit("c", dimension=-1)]
    )
    scale = resolve_compound_scale([1e6, 2e6], unit, pinned=["GeV"])

    # eV should be GIGA (pinned), c stays NONE (unscalable)
    for su in scale.unit.units:
        if su.symbol == "eV":
            assert su.prefix is SIPrefix.GIGA
        if su.symbol == "c":
            assert su.prefix is SIPrefix.NONE


def test_resolve_compound_scale_dimension_weighted():
    # mm^2 with dim=2 gets more weight
    unit = CompoundUnit([SimpleUnit("m", SIPrefix.MILLI, dimension=2)])
    scale = resolve_compound_scale([1e-6, 2e-6, 3e-6], unit)

    # mm^2 ~1e-6 → should scale to um^2
    assert scale.unit.render() == "um^2"


def test_resolve_compound_scale_c_stays_fixed():
    # MeV/c with MeV values → c should not scale
    unit = CompoundUnit(
        [SimpleUnit("eV", SIPrefix.MEGA), SimpleUnit("c", dimension=-1)]
    )
    scale = resolve_compound_scale([1e6, 2e6], unit)

    # c component should stay at NONE prefix
    for su in scale.unit.units:
        if su.symbol == "c":
            assert su.prefix is SIPrefix.NONE
    scale = autoscale_unit([1e-9, 1e-8, 1e-7], SimpleUnit("c"))

    assert scale.multiplier == 1.0
    assert scale.unit.render() == "c"
