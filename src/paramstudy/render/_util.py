from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

from paramstudy.scale import UnitScale, resolve_unit_scale

if TYPE_CHECKING:
    from paramstudy.metadata import ColumnMeta
    from paramstudy.options import AxesOptions


def format_scaled_value(value: Any, scale: UnitScale | None) -> str:
    """Format a single value with optional unit scaling for display in labels/titles."""
    if pd.isna(value):
        return "NaN"
    try:
        scaled = float(value) * (scale.multiplier if scale is not None else 1.0)
        text = f"{scaled:.6g}"
    except Exception:
        return str(value)
    if scale is not None:
        text += scale.render_unit()
    return text


def resolve_column_scale(
    df: pd.DataFrame,
    column: str,
    column_meta: "ColumnMeta",
    options: "AxesOptions",
) -> UnitScale | None:
    """Resolve the display scale for one DataFrame column.

    Returns ``None`` when the column has no unit metadata or is not numeric.
    """
    if column_meta.unit is None or not pd.api.types.is_numeric_dtype(df[column]):
        return None
    return resolve_unit_scale(
        df[column].dropna().to_numpy(),
        column_meta.unit,
        preferred_unit=column_meta.preferred_unit,
        autoscale=options.units.autoscale,
        use_preferred=options.units.use_preferred,
    )
