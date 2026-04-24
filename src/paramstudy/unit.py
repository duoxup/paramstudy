from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class SIPrefix(Enum):
    """SI prefixes used for display and simple-unit scaling."""

    QUECTO = ("q", 1e-30)
    RONTO = ("r", 1e-27)
    YOCTO = ("y", 1e-24)
    ZEPTO = ("z", 1e-21)
    ATTO = ("a", 1e-18)
    FEMTO = ("f", 1e-15)
    PICO = ("p", 1e-12)
    NANO = ("n", 1e-9)
    MICRO = ("u", 1e-6)
    MILLI = ("m", 1e-3)
    CENTI = ("c", 1e-2)
    DECI = ("d", 1e-1)
    NONE = ("", 1.0)
    DECA = ("da", 1e1)
    HECTO = ("h", 1e2)
    KILO = ("k", 1e3)
    MEGA = ("M", 1e6)
    GIGA = ("G", 1e9)
    TERA = ("T", 1e12)
    PETA = ("P", 1e15)
    EXA = ("E", 1e18)
    ZETTA = ("Z", 1e21)
    YOTTA = ("Y", 1e24)
    RONNA = ("R", 1e27)
    QUETTA = ("Q", 1e30)

    @property
    def symbol(self) -> str:
        return self.value[0]

    @property
    def factor(self) -> float:
        return self.value[1]


@runtime_checkable
class Unit(Protocol):
    """Common rendering protocol for unit objects."""

    def render(self) -> str:
        """Return a plain-text unit string suitable for axis labels."""


@dataclass(frozen=True)
class SimpleUnit:
    """A unit with one base symbol, one SI prefix, and one dimensional power.

    Examples:
        SimpleUnit("s", SIPrefix.NANO) renders as "ns".
        SimpleUnit("m", SIPrefix.MILLI, dimension=2) renders as "mm^2".

    The dimension belongs to the complete prefixed unit expression. For example,
    ``mm^2`` is interpreted as square millimeters, not milli-square-meters.
    """

    symbol: str
    prefix: SIPrefix = SIPrefix.NONE
    dimension: int = 1

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("SimpleUnit.symbol must be non-empty.")
        if self.dimension == 0:
            raise ValueError("SimpleUnit.dimension must not be 0.")

    @property
    def factor_to_base(self) -> float:
        """Scale factor from this prefixed unit to the unprefixed base unit."""

        return self.prefix.factor**self.dimension

    def with_prefix(self, prefix: SIPrefix) -> SimpleUnit:
        return SimpleUnit(symbol=self.symbol, prefix=prefix, dimension=self.dimension)

    def with_dimension(self, dimension: int) -> SimpleUnit:
        return SimpleUnit(symbol=self.symbol, prefix=self.prefix, dimension=dimension)

    def render(self) -> str:
        text = f"{self.prefix.symbol}{self.symbol}"
        if self.dimension != 1:
            text = f"{text}^{self.dimension}"
        return text

    def __str__(self) -> str:
        return self.render()


@dataclass(frozen=True)
class CompoundUnit:
    """A compound unit represented as a sequence of simple units.

    The first version only models structure and rendering. Scaling rules for
    compound units should be added later, after deciding how to represent
    products, ratios, and mixed dimensions.
    """

    units: tuple[SimpleUnit, ...]
    separator: str = " "

    def __post_init__(self) -> None:
        if isinstance(self.units, list):
            object.__setattr__(self, "units", tuple(self.units))
        if not self.units:
            raise ValueError("CompoundUnit.units must be non-empty.")

    def render(self) -> str:
        return self.separator.join(unit.render() for unit in self.units)

    def __str__(self) -> str:
        return self.render()


@dataclass(frozen=True)
class Unitless:
    """A dimensionless marker for arbitrary or normalized quantities."""

    label: str = "a.u."

    def render(self) -> str:
        return self.label

    def __str__(self) -> str:
        return self.render()


UnitLike = SimpleUnit | CompoundUnit | Unitless

_UNITLESS_LABELS = frozenset({"a.u.", "a.u", "au", "arb.", "arb", "normalized", "norm."})
_BASE_UNITS = (
    "eV",
    "rad",
    "Hz",
    "mol",
    "cd",
    "sr",
    "m",
    "s",
    "g",
    "A",
    "K",
    "V",
    "W",
    "C",
    "J",
    "N",
    "Pa",
    "T",
    "F",
    "Ohm",
)
_PREFIX_BY_SYMBOL = {prefix.symbol: prefix for prefix in SIPrefix}
_PREFIX_SYMBOLS = tuple(sorted(_PREFIX_BY_SYMBOL, key=len, reverse=True))


def parse_unit(value: str) -> UnitLike:
    """Parse a unit string into a UnitLike object.

    Supported grammar is intentionally small:
    simple units like "ns", "mm", "MeV", "mm^2";
    compound units as whitespace-separated simple units, e.g. "mm mrad";
    unitless markers like "a.u.".
    """

    text = value.strip()
    if not text:
        raise ValueError("Unit string must be non-empty.")
    if text.lower() in _UNITLESS_LABELS:
        return Unitless(label=text)

    parts = text.split()
    if len(parts) > 1:
        return CompoundUnit([_parse_simple_unit(part) for part in parts])
    return _parse_simple_unit(text)


def unit_to_dict(unit: UnitLike | None) -> dict[str, Any] | None:
    if unit is None:
        return None
    if isinstance(unit, SimpleUnit):
        return {
            "kind": "simple",
            "symbol": unit.symbol,
            "prefix": unit.prefix.name,
            "dimension": unit.dimension,
        }
    if isinstance(unit, CompoundUnit):
        return {
            "kind": "compound",
            "units": [unit_to_dict(simple_unit) for simple_unit in unit.units],
            "separator": unit.separator,
        }
    if isinstance(unit, Unitless):
        return {"kind": "unitless", "label": unit.label}
    raise TypeError(f"Unsupported unit type: {type(unit).__name__}")


def unit_from_dict(payload: Mapping[str, Any]) -> UnitLike:
    kind = payload.get("kind")
    if kind == "simple":
        prefix_name = payload.get("prefix", SIPrefix.NONE.name)
        if not isinstance(prefix_name, str) or prefix_name not in SIPrefix.__members__:
            raise ValueError(f"Invalid SI prefix: {prefix_name!r}")
        symbol = payload.get("symbol")
        if not isinstance(symbol, str) or not symbol:
            raise ValueError("Simple unit mapping requires a non-empty 'symbol'.")
        return SimpleUnit(
            symbol=symbol,
            prefix=SIPrefix[prefix_name],
            dimension=int(payload.get("dimension", 1)),
        )
    if kind == "compound":
        units = payload.get("units")
        if not isinstance(units, Sequence) or isinstance(units, (str, bytes, bytearray)):
            raise ValueError("Compound unit mapping requires a sequence 'units'.")
        simple_units = [unit_from_dict(unit_payload) for unit_payload in units]
        if not all(isinstance(unit, SimpleUnit) for unit in simple_units):
            raise ValueError("Compound unit mappings may only contain simple units.")
        return CompoundUnit(simple_units, separator=str(payload.get("separator", " ")))
    if kind == "unitless":
        return Unitless(label=str(payload.get("label", "a.u.")))
    raise ValueError(f"Unknown unit mapping kind: {kind!r}")


def _parse_simple_unit(value: str) -> SimpleUnit:
    unit_text, dimension = _split_dimension(value)
    if unit_text in _BASE_UNITS:
        return SimpleUnit(unit_text, dimension=dimension)

    for prefix_symbol in _PREFIX_SYMBOLS:
        if prefix_symbol == "" or not unit_text.startswith(prefix_symbol):
            continue
        base = unit_text[len(prefix_symbol) :]
        if base in _BASE_UNITS:
            return SimpleUnit(base, prefix=_PREFIX_BY_SYMBOL[prefix_symbol], dimension=dimension)

    raise ValueError(f"Cannot parse unit: {value!r}")


def _split_dimension(value: str) -> tuple[str, int]:
    if "^" not in value:
        return value, 1
    unit_text, dim_text = value.rsplit("^", 1)
    if not unit_text:
        raise ValueError(f"Missing unit symbol in {value!r}.")
    try:
        dimension = int(dim_text)
    except ValueError as exc:
        raise ValueError(f"Invalid unit dimension in {value!r}.") from exc
    return unit_text, dimension
