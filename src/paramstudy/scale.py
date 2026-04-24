from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from paramstudy.unit import SIPrefix, SimpleUnit, UnitLike


_DISPLAY_PREFIXES: tuple[SIPrefix, ...] = (
    SIPrefix.PICO,
    SIPrefix.NANO,
    SIPrefix.MICRO,
    SIPrefix.MILLI,
    SIPrefix.NONE,
    SIPrefix.KILO,
    SIPrefix.MEGA,
    SIPrefix.GIGA,
    SIPrefix.TERA,
)


@dataclass(frozen=True)
class UnitScale:
    """A value multiplier and the unit used after scaling."""

    multiplier: float
    unit: UnitLike

    def render_unit(self) -> str:
        return self.unit.render()


def scale_to_unit(source: UnitLike, target: UnitLike) -> UnitScale:
    """Return the multiplier needed to display ``source`` values in ``target``.

    The first implementation only supports non-ambiguous simple-unit
    conversions. Compound-unit scaling is intentionally deferred.
    """

    if source == target:
        return UnitScale(multiplier=1.0, unit=target)

    if isinstance(source, SimpleUnit) and isinstance(target, SimpleUnit):
        if source.symbol != target.symbol:
            raise ValueError(
                f"Cannot convert between different unit symbols: "
                f"{source.render()} -> {target.render()}."
            )
        if source.dimension != target.dimension:
            raise ValueError(
                f"Cannot convert between different unit dimensions: "
                f"{source.render()} -> {target.render()}."
            )
        return UnitScale(
            multiplier=source.factor_to_base / target.factor_to_base,
            unit=target,
        )

    raise ValueError(
        "Explicit unit conversion currently only supports compatible SimpleUnit objects: "
        f"{source.render()} -> {target.render()}."
    )


def resolve_unit_scale(
    values: Iterable[float],
    unit: UnitLike | None,
    *,
    preferred_unit: UnitLike | None = None,
    autoscale: bool = True,
    use_preferred: bool = True,
) -> UnitScale | None:
    """Resolve the display scale for one column of values."""

    if unit is None:
        return None
    if use_preferred and preferred_unit is not None:
        return scale_to_unit(unit, preferred_unit)
    if autoscale:
        return autoscale_unit(values, unit)
    return UnitScale(multiplier=1.0, unit=unit)


def autoscale_unit(values: Iterable[float], unit: UnitLike) -> UnitScale:
    """Return a display scale for values expressed in ``unit``.

    Only :class:`SimpleUnit` currently supports prefix changes. Compound units
    are structurally represented but intentionally not auto-scaled yet.
    """

    if isinstance(unit, SimpleUnit):
        return _autoscale_simple_unit(values, unit)
    return UnitScale(multiplier=1.0, unit=unit)


def _autoscale_simple_unit(values: Iterable[float], unit: SimpleUnit) -> UnitScale:
    array = np.asarray(values, dtype=float)
    finite = np.abs(array[np.isfinite(array)])
    if finite.size == 0 or not np.any(finite > 0):
        return UnitScale(multiplier=1.0, unit=unit)

    magnitude_in_input_unit = float(np.nanmedian(finite[finite > 0]))
    magnitude_in_base_unit = magnitude_in_input_unit * unit.factor_to_base

    best_prefix = unit.prefix
    best_score = float("inf")
    for prefix in _DISPLAY_PREFIXES:
        target_factor = prefix.factor**unit.dimension
        scaled = magnitude_in_base_unit / target_factor
        if scaled <= 0:
            continue
        score = abs(np.log10(scaled) - 1.5)
        if 0.1 <= scaled < 10000 and score < best_score:
            best_prefix = prefix
            best_score = score

    display_unit = unit.with_prefix(best_prefix)
    multiplier = unit.factor_to_base / display_unit.factor_to_base
    return UnitScale(multiplier=multiplier, unit=display_unit)
