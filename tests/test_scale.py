import pytest

from paramstudy.scale import autoscale_unit, scale_to_unit
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


def test_autoscale_does_not_scale_compound_unit_yet():
    unit = CompoundUnit([SimpleUnit("m", SIPrefix.MILLI), SimpleUnit("rad", SIPrefix.MILLI)])

    scale = autoscale_unit([1e-6, 2e-6, 3e-6], unit)

    assert scale.multiplier == pytest.approx(1.0)
    assert scale.unit is unit
    assert scale.unit.render() == "mm mrad"


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


def test_autoscale_never_scales_unscalable_symbol():
    scale = autoscale_unit([1e-9, 1e-8, 1e-7], SimpleUnit("c"))

    assert scale.multiplier == 1.0
    assert scale.unit.render() == "c"
