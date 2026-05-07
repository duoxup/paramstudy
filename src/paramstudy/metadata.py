from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, IO

from paramstudy.unit import (
    CompoundUnit,
    SimpleUnit,
    UnitLike,
    Unitless,
    parse_unit,
    unit_from_dict,
    unit_to_dict,
)

PathLike = str | Path
ColumnMetaInput = Sequence[Any] | Mapping[str, Any]

_COLUMN_META_FIELDS = ("label", "symbol", "unit", "preferred_unit")
_ALLOWED_META_KEYS = frozenset(_COLUMN_META_FIELDS)


@dataclass(frozen=True)
class ColumnMeta:
    """Semantic display metadata for one DataFrame column."""

    label: str | None = None
    symbol: str | None = None
    unit: UnitLike | None = None
    preferred_unit: UnitLike | None = None

    def display_name(self, fallback: str, *, prefer_symbol: bool = False) -> str:
        if prefer_symbol:
            return self.symbol or self.label or fallback
        return self.label or self.symbol or fallback

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "symbol": self.symbol,
            "unit": unit_to_dict(self.unit),
            "preferred_unit": unit_to_dict(self.preferred_unit),
        }

    def to_csv_row(self) -> dict[str, str]:
        """Return a dict suitable for CSV writer, with column name omitted."""
        return {
            "label": self.label or "",
            "symbol": self.symbol or "",
            "unit": self.unit.render() if self.unit is not None else "",
            "preferred_unit": self.preferred_unit.render() if self.preferred_unit is not None else "",
        }

    @classmethod
    def from_csv_row(cls, row: Mapping[str, str]) -> ColumnMeta:
        """Build a ColumnMeta from a CSV row dict (column key omitted)."""
        unit = _clean_csv_unit(row.get("unit")) if row.get("unit", "").strip() else None
        preferred_unit = (
            _clean_csv_unit(row.get("preferred_unit")) if row.get("preferred_unit", "").strip() else None
        )
        if unit is None and preferred_unit is not None:
            raise ValueError("ColumnMeta.preferred_unit requires ColumnMeta.unit.")
        return cls(
            label=_clean_optional_string(row.get("label")),
            symbol=_clean_optional_string(row.get("symbol")),
            unit=unit,
            preferred_unit=preferred_unit,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ColumnMeta:
        _validate_meta_keys(payload)
        unit = _coerce_unit(payload.get("unit"))
        preferred_unit = _coerce_unit(payload.get("preferred_unit"))
        if unit is None and preferred_unit is not None:
            raise ValueError("ColumnMeta.preferred_unit requires ColumnMeta.unit.")
        return cls(
            label=_clean_optional_string(payload.get("label")),
            symbol=_clean_optional_string(payload.get("symbol")),
            unit=unit,
            preferred_unit=preferred_unit,
        )


class ColumnMetaRegistry:
    """Column-name to metadata registry with versioned JSON serialization."""

    _TYPE = "ColumnMetaRegistry"
    _VERSION = 1

    def __init__(self, metas: Mapping[str, ColumnMeta] | None = None):
        self._metas = dict(metas or {})

    def add(self, column: str, meta: ColumnMeta) -> None:
        if not column:
            raise ValueError("Column name must be non-empty.")
        self._metas[str(column)] = meta

    def get(self, column: str) -> ColumnMeta:
        return self._metas.get(column, ColumnMeta())

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self._TYPE,
            "version": self._VERSION,
            "metas": {column: meta.to_dict() for column, meta in self._metas.items()},
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ColumnMetaRegistry:
        if payload.get("type") not in (None, cls._TYPE):
            raise ValueError(f"Unexpected metadata registry type: {payload.get('type')!r}")
        version = payload.get("version", cls._VERSION)
        if version != cls._VERSION:
            raise ValueError(f"Unsupported metadata registry version: {version}")

        metas_in = payload.get("metas", {})
        if not isinstance(metas_in, Mapping):
            raise ValueError("'metas' must be a mapping.")

        registry = cls()
        for column, meta_payload in metas_in.items():
            if not isinstance(meta_payload, Mapping):
                raise TypeError(f"Metadata for column {column!r} must be a mapping.")
            registry.add(str(column), ColumnMeta.from_dict(meta_payload))
        return registry

    def to_json(
        self,
        path_or_fp: PathLike | IO[str],
        *,
        indent: int = 2,
        ensure_ascii: bool = False,
    ) -> None:
        if hasattr(path_or_fp, "write"):
            json.dump(self.to_dict(), path_or_fp, indent=indent, ensure_ascii=ensure_ascii)
            return

        path = Path(path_or_fp)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(self.to_dict(), file, indent=indent, ensure_ascii=ensure_ascii)

    @classmethod
    def from_json(cls, path_or_fp: PathLike | IO[str]) -> ColumnMetaRegistry:
        if hasattr(path_or_fp, "read"):
            return cls.from_dict(json.load(path_or_fp))

        path = Path(path_or_fp)
        with path.open("r", encoding="utf-8") as file:
            return cls.from_dict(json.load(file))

    _CSV_FIELDNAMES = ["column", "label", "symbol", "unit", "preferred_unit"]

    def to_csv(
        self,
        path_or_fp: PathLike | IO[str],
    ) -> None:
        """Write the registry as a row-per-column CSV file.

        Units are serialized as their rendered string form so the file is
        human-readable and round-trippable via from_csv.
        """
        lines = [self._CSV_FIELDNAMES] + [
            [column, row["label"], row["symbol"], row["unit"], row["preferred_unit"]]
            for column, row in sorted(self._to_csv_rows().items())
        ]

        if hasattr(path_or_fp, "write"):
            writer = csv.writer(path_or_fp, lineterminator="\n")
            writer.writerows(lines)
            return

        path = Path(path_or_fp)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file, lineterminator="\n")
            writer.writerows(lines)

    @classmethod
    def from_csv(cls, path_or_fp: PathLike | IO[str]) -> ColumnMetaRegistry:
        """Read a registry from a CSV file written by to_csv.

        Each row maps to one ColumnMeta entry. Empty cells are treated as None.
        Unit strings are parsed via parse_unit so they round-trip cleanly.
        """
        if hasattr(path_or_fp, "read"):
            reader = csv.DictReader(path_or_fp)
            return cls._from_csv_rows(list(reader))

        path = Path(path_or_fp)
        with path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            return cls._from_csv_rows(list(reader))

    def _to_csv_rows(self) -> dict[str, dict[str, str]]:
        return {column: meta.to_csv_row() for column, meta in self._metas.items()}

    @classmethod
    def _from_csv_rows(cls, rows: list[dict[str, str]]) -> ColumnMetaRegistry:
        registry = cls()
        for row in rows:
            column = row.get("column", "").strip()
            if not column:
                raise ValueError("CSV row missing non-empty 'column' field.")
            registry.add(column, ColumnMeta.from_csv_row(row))
        return registry


def make_registry(spec: Mapping[str, ColumnMetaInput]) -> ColumnMetaRegistry:
    """Build a metadata registry from compact or JSON-style specifications.

    Compact form:
        {"energy": ["Beam energy", "E", "MeV", "GeV"]}

    JSON-style form:
        {"energy": {"label": "Beam energy", "symbol": "E", "unit": "MeV"}}
    """

    registry = ColumnMetaRegistry()
    for column, meta_input in spec.items():
        registry.add(str(column), _coerce_column_meta(meta_input))
    return registry


def _coerce_column_meta(value: ColumnMetaInput) -> ColumnMeta:
    if isinstance(value, Mapping):
        return ColumnMeta.from_dict(value)

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        if len(value) > len(_COLUMN_META_FIELDS):
            raise ValueError(
                f"Compact ColumnMeta spec accepts at most {len(_COLUMN_META_FIELDS)} values: "
                f"{_COLUMN_META_FIELDS}."
            )
        payload = dict(zip(_COLUMN_META_FIELDS, value))
        return ColumnMeta.from_dict(payload)

    raise TypeError("Column metadata spec must be a compact sequence or a JSON-style mapping.")


def _validate_meta_keys(payload: Mapping[str, Any]) -> None:
    unknown = set(payload) - _ALLOWED_META_KEYS
    if unknown:
        raise ValueError(f"Unknown ColumnMeta keys: {sorted(unknown)}")


def _clean_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"Expected a string or None, got {type(value).__name__}.")
    stripped = value.strip()
    return stripped or None


def _clean_csv_unit(value: str) -> UnitLike | None:
    """Parse a unit string from CSV, falling back to Unitless on failure."""
    if not value.strip():
        return None
    try:
        return parse_unit(value.strip())
    except ValueError:
        return Unitless(label=value.strip())


def _coerce_unit(value: Any) -> UnitLike | None:
    if value is None:
        return None
    if isinstance(value, (SimpleUnit, CompoundUnit, Unitless)):
        return value
    if isinstance(value, str):
        return parse_unit(value)
    if isinstance(value, Mapping):
        return unit_from_dict(value)
    raise TypeError(
        f"Expected a unit string, UnitLike object, mapping, or None; got {type(value).__name__}."
    )
