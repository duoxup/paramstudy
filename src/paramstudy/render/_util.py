from __future__ import annotations

from typing import Any

import pandas as pd

from paramstudy.scale import UnitScale


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
