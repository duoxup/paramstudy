from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from paramstudy.unit import CompoundUnit, SIPrefix, SimpleUnit, UnitLike, parse_unit

_UNSCALABLE_SYMBOLS: frozenset[str] = frozenset({"c"})

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
    """Return a display scale for values expressed in ``unit``."""

    if isinstance(unit, SimpleUnit):
        return _autoscale_simple_unit(values, unit)
    if isinstance(unit, CompoundUnit):
        return _autoscale_compound_unit(values, unit)
    return UnitScale(multiplier=1.0, unit=unit)


def resolve_compound_scale(
    values: Iterable[float],
    unit: CompoundUnit,
    pinned: Sequence[str] | None = None,
) -> UnitScale:
    """Resolve display scale for a compound unit with optional pinned targets.

    ``pinned`` is a sequence of target unit strings (e.g. ``["mrad", "ms"]``).
    Each string is parsed and matched to a component of ``unit`` by **symbol**.
    The target string's dimension is ignored — only its prefix is used, while
    the source component's dimension (including sign) is preserved.

    Pinned components receive an exact conversion.  The remaining scaling
    (from data magnitude) is distributed across unpinned components weighted
    by ``abs(dimension)``.
    """
    if pinned:
        return _autoscale_compound_unit(values, unit, pinned=pinned)
    return _autoscale_compound_unit(values, unit)


def _autoscale_simple_unit(values: Iterable[float], unit: SimpleUnit) -> UnitScale:
    if unit.symbol in _UNSCALABLE_SYMBOLS:
        return UnitScale(multiplier=1.0, unit=unit)

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


def _best_prefix_for_multiplier(
    source: SimpleUnit,
    target_multiplier: float,
) -> SIPrefix:
    """Find the prefix whose conversion from *source* approximates *target_multiplier*."""
    if not np.isfinite(target_multiplier) or target_multiplier <= 0:
        return source.prefix

    best = source.prefix
    best_diff = float("inf")
    factor_src = source.factor_to_base
    for prefix in _DISPLAY_PREFIXES:
        factor_tgt = prefix.factor ** source.dimension
        if factor_tgt <= 0:
            continue
        diff = abs((factor_src / factor_tgt) - target_multiplier)
        if diff < best_diff:
            best_diff = diff
            best = prefix
    return best


def _autoscale_compound_unit(
    values: Iterable[float],
    unit: CompoundUnit,
    *,
    pinned: Sequence[str] | None = None,
) -> UnitScale:
    array = np.asarray(values, dtype=float)
    finite = np.abs(array[np.isfinite(array)])
    if finite.size == 0 or not np.any(finite > 0):
        return UnitScale(multiplier=1.0, unit=unit)

    magnitude = float(np.nanmedian(finite[finite > 0]))
    mag_in_base = magnitude * unit.factor_to_base

    # --- resolve pinned targets ---
    pinned_map: dict[int, SimpleUnit] = {}
    if pinned:
        used_symbols: set[str] = set()
        for pinned_str in pinned:
            target = parse_unit(pinned_str.strip())
            if not isinstance(target, SimpleUnit):
                raise ValueError(
                    f"Pinned target {pinned_str!r} must resolve to a simple unit."
                )
            matches = [
                (i, su)
                for i, su in enumerate(unit.units)
                if su.symbol == target.symbol and i not in pinned_map
            ]
            if not matches:
                raise ValueError(
                    f"Pinned target {pinned_str!r} (symbol={target.symbol!r}) "
                    f"does not match any unpinned component of {unit.render()}."
                )
            if target.symbol in used_symbols:
                raise ValueError(
                    f"Duplicate pinned target for symbol {target.symbol!r}."
                )
            if target.symbol in _UNSCALABLE_SYMBOLS:
                raise ValueError(
                    f"Cannot pin unscalable symbol {target.symbol!r}."
                )
            idx, source_su = matches[0]
            used_symbols.add(target.symbol)
            pinned_map[idx] = SimpleUnit(
                symbol=source_su.symbol,
                prefix=target.prefix,
                dimension=source_su.dimension,
            )

    # --- per-component autoscale (equal distribution, dim-weighted) ---
    n_total = sum(abs(su.dimension) for su in unit.units)
    per_dim_mag = mag_in_base ** (1.0 / n_total) if n_total > 0 else mag_in_base

    autoscaled: list[tuple[SimpleUnit, float]] = []
    for su in unit.units:
        if su.symbol in _UNSCALABLE_SYMBOLS:
            autoscaled.append((su, 1.0))
            continue
        component_mag = per_dim_mag ** abs(su.dimension)
        fake_values = [component_mag / su.factor_to_base]
        sc = _autoscale_simple_unit(fake_values, su)
        autoscaled.append((sc.unit, sc.multiplier))

    M_total = 1.0
    for _, m in autoscaled:
        M_total *= m

    # --- pinned override ---
    M_pinned = 1.0
    for i, tgt in pinned_map.items():
        source_su = unit.units[i]
        mult = source_su.factor_to_base / tgt.factor_to_base
        M_pinned *= mult

    M_left = M_total / M_pinned

    # --- distribute leftover ---
    unpinned_weight = sum(abs(unit.units[i].dimension) for i in range(len(unit.units)) if i not in pinned_map)
    result_units: list[SimpleUnit] = []
    for i, su in enumerate(unit.units):
        if i in pinned_map:
            result_units.append(pinned_map[i])
            continue
        if unpinned_weight == 0 or su.symbol in _UNSCALABLE_SYMBOLS:
            result_units.append(autoscaled[i][0])
            continue
        w = abs(su.dimension) / unpinned_weight
        target_mult = M_left**w
        best_prefix = _best_prefix_for_multiplier(su, target_mult)
        result_units.append(SimpleUnit(symbol=su.symbol, prefix=best_prefix, dimension=su.dimension))

    display_unit = CompoundUnit(tuple(result_units), separator=unit.separator)
    total_mult = unit.factor_to_base / display_unit.factor_to_base
    return UnitScale(multiplier=total_mult, unit=display_unit)
