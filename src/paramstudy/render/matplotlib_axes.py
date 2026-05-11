from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np
import pandas as pd

from paramstudy.metadata import ColumnMeta, ColumnMetaRegistry
from paramstudy.options import AxesOptions, SecondaryContourOptions
from paramstudy.render._util import format_scaled_value, resolve_column_scale
from paramstudy.scale import UnitScale
from paramstudy.spec import PlotKind, PlotSpec


@dataclass(frozen=True)
class AxesDrawResult:
    mappable: Any | None = None


def draw_line_axes(
    ax: plt.Axes,
    df: pd.DataFrame,
    spec: PlotSpec,
    *,
    meta: ColumnMetaRegistry | None = None,
    options: AxesOptions | None = None,
) -> AxesDrawResult:
    """Draw one line plot on an existing Matplotlib Axes."""

    spec.validate()
    if spec.kind is not PlotKind.LINE:
        raise ValueError(f"draw_line_axes requires PlotKind.LINE, got {spec.kind!r}.")
    if spec.responses.primary is None:
        raise ValueError("Line plots require ResponseMap.primary.")

    options = options or AxesOptions()
    x_col = spec.inputs.primary
    y_col = spec.responses.primary
    group_col = spec.inputs.secondary
    _require_columns(df, [x_col, y_col, group_col])

    x_scale = _resolve_column_scale(df, x_col, meta, options)
    y_scale = _resolve_column_scale(df, y_col, meta, options)

    if group_col is None:
        xs, ys = _prepare_line_xy(df, x_col, y_col, options)
        ax.plot(_apply_scale(xs, x_scale), _apply_scale(ys, y_scale))
    else:
        group_scale = _resolve_column_scale(df, group_col, meta, options)
        group_values = _ordered_values(df[group_col])
        group_meta = _meta(meta, group_col)
        for group_value in group_values:
            subset = df.loc[df[group_col] == group_value]
            xs, ys = _prepare_line_xy(subset, x_col, y_col, options)
            label = _format_value(group_value, group_scale)
            ax.plot(_apply_scale(xs, x_scale), _apply_scale(ys, y_scale), label=label)

        if options.legend.show:
            ax.legend(
                title=options.legend.title
                or _format_label(group_col, group_meta, group_scale, options),
                loc=options.legend.loc,
                frameon=True,
            )

    ax.set_xlabel(_format_label(x_col, _meta(meta, x_col), x_scale, options))
    ax.set_ylabel(_format_label(y_col, _meta(meta, y_col), y_scale, options))
    ax.set_xscale(options.scale.x)
    ax.set_yscale(options.scale.y)
    return AxesDrawResult()


def draw_scatter_axes(
    ax: plt.Axes,
    df: pd.DataFrame,
    spec: PlotSpec,
    *,
    meta: ColumnMetaRegistry | None = None,
    options: AxesOptions | None = None,
    color_limits: tuple[float, float] | None = None,
    color_scale: UnitScale | None = None,
) -> AxesDrawResult:
    """Draw one scatter plot on an existing Matplotlib Axes."""

    spec.validate()
    if spec.kind is not PlotKind.SCATTER:
        raise ValueError(f"draw_scatter_axes requires PlotKind.SCATTER, got {spec.kind!r}.")
    if spec.inputs.secondary is None:
        raise ValueError("Scatter plots require InputMap.secondary.")

    options = options or AxesOptions()
    x_col = spec.inputs.primary
    y_col = spec.inputs.secondary
    color_col = spec.responses.color or spec.responses.primary
    size_col = spec.responses.size
    _require_columns(df, [x_col, y_col, color_col, size_col])

    subset = df.dropna(subset=[x_col, y_col])
    x_scale = _resolve_column_scale(subset, x_col, meta, options)
    y_scale = _resolve_column_scale(subset, y_col, meta, options)

    kwargs: dict[str, Any] = {}
    if color_col is not None:
        if color_scale is None:
            color_scale = _resolve_column_scale(subset, color_col, meta, options)
        kwargs["c"] = _apply_scale(subset[color_col], color_scale)
        if options.color.cmap is not None:
            kwargs["cmap"] = options.color.cmap
        _apply_color_limits(kwargs, options, color_limits)
    if size_col is not None:
        size_scale = _resolve_column_scale(subset, size_col, meta, options)
        sizes = np.asarray(_apply_scale(subset[size_col], size_scale), dtype=float)
        sizes = np.abs(sizes)
        max_size = float(np.nanmax(sizes)) if sizes.size else 1.0
        if not np.isfinite(max_size) or max_size <= 0:
            max_size = 1.0
        kwargs["s"] = 24.0 + 96.0 * sizes / max_size

    mappable = ax.scatter(
        _apply_scale(subset[x_col], x_scale),
        _apply_scale(subset[y_col], y_scale),
        **kwargs,
    )
    ax.set_xlabel(_format_label(x_col, _meta(meta, x_col), x_scale, options))
    ax.set_ylabel(_format_label(y_col, _meta(meta, y_col), y_scale, options))
    ax.set_xscale(options.scale.x)
    ax.set_yscale(options.scale.y)
    return AxesDrawResult(mappable=mappable if color_col is not None else None)


def draw_heatmap_axes(
    ax: plt.Axes,
    df: pd.DataFrame,
    spec: PlotSpec,
    *,
    meta: ColumnMetaRegistry | None = None,
    options: AxesOptions | None = None,
    color_limits: tuple[float, float] | None = None,
    color_scale: UnitScale | None = None,
) -> AxesDrawResult:
    """Draw one regular-grid heatmap on an existing Matplotlib Axes."""

    spec.validate()
    if spec.kind is not PlotKind.HEATMAP:
        raise ValueError(f"draw_heatmap_axes requires PlotKind.HEATMAP, got {spec.kind!r}.")
    if spec.inputs.secondary is None or spec.responses.primary is None:
        raise ValueError("Heatmap plots require InputMap.secondary and ResponseMap.primary.")

    options = options or AxesOptions()
    x_col = spec.inputs.primary
    y_col = spec.inputs.secondary
    z_col = spec.responses.primary
    _require_columns(df, [x_col, y_col, z_col])

    subset = df[[x_col, y_col, z_col]].dropna()
    x_scale = _resolve_column_scale(subset, x_col, meta, options)
    y_scale = _resolve_column_scale(subset, y_col, meta, options)
    z_scale = color_scale if color_scale is not None else _resolve_column_scale(subset, z_col, meta, options)
    xs, ys, z_grid = _prepare_heatmap_grid(subset, x_col, y_col, z_col, options)

    kwargs: dict[str, Any] = {"shading": "auto"}
    if options.color.cmap is not None:
        kwargs["cmap"] = options.color.cmap
    _apply_color_limits(kwargs, options, color_limits)
    mappable = ax.pcolormesh(
        xs.astype(float) * (x_scale.multiplier if x_scale is not None else 1.0),
        ys.astype(float) * (y_scale.multiplier if y_scale is not None else 1.0),
        z_grid * (z_scale.multiplier if z_scale is not None else 1.0),
        **kwargs,
    )
    _draw_secondary_grid_contour(ax, df, spec, options, x_scale, y_scale)
    ax.set_xlabel(_format_label(x_col, _meta(meta, x_col), x_scale, options))
    ax.set_ylabel(_format_label(y_col, _meta(meta, y_col), y_scale, options))
    ax.set_xscale(options.scale.x)
    ax.set_yscale(options.scale.y)
    return AxesDrawResult(mappable=mappable)


def draw_contour_axes(
    ax: plt.Axes,
    df: pd.DataFrame,
    spec: PlotSpec,
    *,
    meta: ColumnMetaRegistry | None = None,
    options: AxesOptions | None = None,
    color_limits: tuple[float, float] | None = None,
    color_scale: UnitScale | None = None,
) -> AxesDrawResult:
    """Draw one regular-grid contour plot on an existing Matplotlib Axes."""

    spec.validate()
    if spec.kind is not PlotKind.CONTOUR:
        raise ValueError(f"draw_contour_axes requires PlotKind.CONTOUR, got {spec.kind!r}.")
    if spec.inputs.secondary is None or spec.responses.primary is None:
        raise ValueError("Contour plots require InputMap.secondary and ResponseMap.primary.")

    options = options or AxesOptions()
    x_col = spec.inputs.primary
    y_col = spec.inputs.secondary
    z_col = spec.responses.primary
    _require_columns(df, [x_col, y_col, z_col])

    subset = df[[x_col, y_col, z_col]].dropna()
    x_scale = _resolve_column_scale(subset, x_col, meta, options)
    y_scale = _resolve_column_scale(subset, y_col, meta, options)
    z_scale = color_scale if color_scale is not None else _resolve_column_scale(subset, z_col, meta, options)
    xs, ys, z_grid = _prepare_heatmap_grid(subset, x_col, y_col, z_col, options)

    levels = _resolve_contour_levels(options.contour.levels, color_limits)
    kwargs: dict[str, Any] = {"levels": levels}
    if options.color.cmap is not None:
        kwargs["cmap"] = options.color.cmap
    _apply_color_limits(kwargs, options, color_limits)

    x_values = xs.astype(float) * (x_scale.multiplier if x_scale is not None else 1.0)
    y_values = ys.astype(float) * (y_scale.multiplier if y_scale is not None else 1.0)
    z_values = z_grid * (z_scale.multiplier if z_scale is not None else 1.0)
    if options.contour.filled:
        mappable = ax.contourf(x_values, y_values, z_values, **kwargs)
    else:
        mappable = ax.contour(x_values, y_values, z_values, **kwargs)

    if options.contour.labels:
        ax.clabel(mappable, inline=True, fontsize=8)

    _draw_secondary_grid_contour(ax, df, spec, options, x_scale, y_scale)
    ax.set_xlabel(_format_label(x_col, _meta(meta, x_col), x_scale, options))
    ax.set_ylabel(_format_label(y_col, _meta(meta, y_col), y_scale, options))
    ax.set_xscale(options.scale.x)
    ax.set_yscale(options.scale.y)
    return AxesDrawResult(mappable=mappable)


def draw_tricontour_axes(
    ax: plt.Axes,
    df: pd.DataFrame,
    spec: PlotSpec,
    *,
    meta: ColumnMetaRegistry | None = None,
    options: AxesOptions | None = None,
    color_limits: tuple[float, float] | None = None,
    color_scale: UnitScale | None = None,
) -> AxesDrawResult:
    """Draw one irregular-grid tricontour plot on an existing Matplotlib Axes."""

    spec.validate()
    if spec.kind is not PlotKind.TRICONTOUR:
        raise ValueError(f"draw_tricontour_axes requires PlotKind.TRICONTOUR, got {spec.kind!r}.")
    if spec.inputs.secondary is None or spec.responses.primary is None:
        raise ValueError("Tricontour plots require InputMap.secondary and ResponseMap.primary.")

    options = options or AxesOptions()
    x_col = spec.inputs.primary
    y_col = spec.inputs.secondary
    z_col = spec.responses.primary
    _require_columns(df, [x_col, y_col, z_col])

    subset = df[[x_col, y_col, z_col]].dropna()
    if len(subset) < 3:
        raise ValueError("Tricontour plots require at least 3 non-NA points.")

    x_scale = _resolve_column_scale(subset, x_col, meta, options)
    y_scale = _resolve_column_scale(subset, y_col, meta, options)
    z_scale = color_scale if color_scale is not None else _resolve_column_scale(subset, z_col, meta, options)
    x_values = _apply_scale(subset[x_col], x_scale)
    y_values = _apply_scale(subset[y_col], y_scale)
    z_values = _apply_scale(subset[z_col], z_scale)

    levels = _resolve_contour_levels(options.contour.levels, color_limits)
    kwargs: dict[str, Any] = {"levels": levels}
    if options.color.cmap is not None:
        kwargs["cmap"] = options.color.cmap
    _apply_color_limits(kwargs, options, color_limits)

    if options.contour.filled:
        mappable = ax.tricontourf(x_values, y_values, z_values, **kwargs)
    else:
        mappable = ax.tricontour(x_values, y_values, z_values, **kwargs)

    if options.contour.labels:
        ax.clabel(mappable, inline=True, fontsize=8)

    _draw_secondary_tri_contour(ax, df, spec, options, x_scale, y_scale)
    ax.set_xlabel(_format_label(x_col, _meta(meta, x_col), x_scale, options))
    ax.set_ylabel(_format_label(y_col, _meta(meta, y_col), y_scale, options))
    ax.set_xscale(options.scale.x)
    ax.set_yscale(options.scale.y)
    return AxesDrawResult(mappable=mappable)


def draw_tripcolor_axes(
    ax: plt.Axes,
    df: pd.DataFrame,
    spec: PlotSpec,
    *,
    meta: ColumnMetaRegistry | None = None,
    options: AxesOptions | None = None,
    color_limits: tuple[float, float] | None = None,
    color_scale: UnitScale | None = None,
) -> AxesDrawResult:
    """Draw one irregular-grid tripcolor plot on an existing Matplotlib Axes."""

    spec.validate()
    if spec.kind is not PlotKind.TRIPCOLOR:
        raise ValueError(f"draw_tripcolor_axes requires PlotKind.TRIPCOLOR, got {spec.kind!r}.")
    if spec.inputs.secondary is None or spec.responses.primary is None:
        raise ValueError("Tripcolor plots require InputMap.secondary and ResponseMap.primary.")

    options = options or AxesOptions()
    x_col = spec.inputs.primary
    y_col = spec.inputs.secondary
    z_col = spec.responses.primary
    _require_columns(df, [x_col, y_col, z_col])

    subset = df[[x_col, y_col, z_col]].dropna()
    if len(subset) < 3:
        raise ValueError("Tripcolor plots require at least 3 non-NA points.")

    x_scale = _resolve_column_scale(subset, x_col, meta, options)
    y_scale = _resolve_column_scale(subset, y_col, meta, options)
    z_scale = color_scale if color_scale is not None else _resolve_column_scale(subset, z_col, meta, options)
    kwargs: dict[str, Any] = {"shading": options.tripcolor.shading}
    if options.color.cmap is not None:
        kwargs["cmap"] = options.color.cmap
    _apply_color_limits(kwargs, options, color_limits)

    mappable = ax.tripcolor(
        _apply_scale(subset[x_col], x_scale),
        _apply_scale(subset[y_col], y_scale),
        _apply_scale(subset[z_col], z_scale),
        **kwargs,
    )
    _draw_secondary_tri_contour(ax, df, spec, options, x_scale, y_scale)
    ax.set_xlabel(_format_label(x_col, _meta(meta, x_col), x_scale, options))
    ax.set_ylabel(_format_label(y_col, _meta(meta, y_col), y_scale, options))
    ax.set_xscale(options.scale.x)
    ax.set_yscale(options.scale.y)
    return AxesDrawResult(mappable=mappable)


def _meta(registry: ColumnMetaRegistry | None, column: str) -> ColumnMeta:
    return registry.get(column) if registry is not None else ColumnMeta()


def _resolve_column_scale(
    df: pd.DataFrame,
    column: str,
    registry: ColumnMetaRegistry | None,
    options: AxesOptions,
) -> UnitScale | None:
    return resolve_column_scale(df, column, _meta(registry, column), options)


def _format_label(
    fallback: str,
    meta: ColumnMeta,
    scale: UnitScale | None,
    options: AxesOptions,
) -> str:
    text = meta.display_name(fallback, prefer_symbol=options.labels.prefer_symbol)
    if options.labels.show_units and scale is not None:
        text = f"{text} [{scale.render_unit()}]"
    return text


_format_value = format_scaled_value


def _apply_scale(values: pd.Series, scale: UnitScale | None) -> np.ndarray:
    multiplier = scale.multiplier if scale is not None else 1.0
    return values.astype(float).to_numpy() * multiplier


def _prepare_line_xy(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    options: AxesOptions,
) -> tuple[pd.Series, pd.Series]:
    subset = df[[x_col, y_col]].dropna()
    if subset.empty:
        return pd.Series(dtype=float, name=x_col), pd.Series(dtype=float, name=y_col)

    if options.data.agg is None:
        if options.data.sort_primary:
            subset = subset.sort_values(by=x_col)
        return subset[x_col], subset[y_col]

    grouped = subset.groupby(x_col, sort=options.data.sort_primary)[y_col]
    if isinstance(options.data.agg, str):
        values = getattr(grouped, options.data.agg)()
    else:
        values = grouped.apply(options.data.agg)
    return pd.Series(values.index, name=x_col), pd.Series(values.to_numpy(), name=y_col)


def _prepare_heatmap_grid(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    z_col: str,
    options: AxesOptions,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xs = np.sort(df[x_col].dropna().unique())
    ys = np.sort(df[y_col].dropna().unique())
    if xs.size == 0 or ys.size == 0:
        return xs, ys, np.empty((ys.size, xs.size), dtype=float)

    agg = options.data.agg or "mean"
    grouped = df.groupby([y_col, x_col], sort=options.data.sort_primary)[z_col]
    values = getattr(grouped, agg)() if isinstance(agg, str) else grouped.apply(agg)
    pivot = values.unstack(x_col).reindex(index=ys, columns=xs)
    return xs, ys, pivot.to_numpy(dtype=float)


def _apply_color_limits(
    kwargs: dict[str, Any],
    options: AxesOptions,
    color_limits: tuple[float, float] | None,
) -> None:
    vmin = options.color.vmin
    vmax = options.color.vmax
    if color_limits is not None:
        vmin = color_limits[0] if vmin is None else vmin
        vmax = color_limits[1] if vmax is None else vmax
    if options.scale.z == "log":
        kwargs["norm"] = LogNorm(vmin=vmin, vmax=vmax)
    else:
        if vmin is not None:
            kwargs["vmin"] = vmin
        if vmax is not None:
            kwargs["vmax"] = vmax


def _resolve_contour_levels(
    levels: int | list[float] | tuple[float, ...],
    color_limits: tuple[float, float] | None,
) -> int | np.ndarray | list[float] | tuple[float, ...]:
    if isinstance(levels, int) and color_limits is not None:
        return np.linspace(color_limits[0], color_limits[1], levels + 1)
    return levels


def _ordered_values(values: pd.Series) -> list[Any]:
    ordered = list(dict.fromkeys(values.dropna().tolist()))
    try:
        return sorted(ordered)
    except TypeError:
        return ordered


def _draw_secondary_grid_contour(
    ax: plt.Axes,
    df: pd.DataFrame,
    spec: PlotSpec,
    options: AxesOptions,
    x_scale: UnitScale | None,
    y_scale: UnitScale | None,
) -> None:
    """Overlay a line-only contour for a secondary z column (heatmap / contour).

    Uses the secondary column's own dropna subset to build (xs, ys, z2_grid)
    so the overlay still aligns when the primary z and z2 columns have
    different NaN coverage.
    """
    z2_col = options.secondary_contour.column
    if z2_col is None or z2_col not in df.columns:
        return
    subset = df[[spec.inputs.primary, spec.inputs.secondary, z2_col]].dropna()
    if subset.empty:
        return
    xs, ys, z2_grid = _prepare_heatmap_grid(
        subset, spec.inputs.primary, spec.inputs.secondary, z2_col, options
    )
    if xs.size == 0 or ys.size == 0:
        return
    x_mult = x_scale.multiplier if x_scale is not None else 1.0
    y_mult = y_scale.multiplier if y_scale is not None else 1.0
    cs = ax.contour(
        xs.astype(float) * x_mult,
        ys.astype(float) * y_mult,
        z2_grid,
        levels=options.secondary_contour.levels,
        colors=options.secondary_contour.color,
        linewidths=options.secondary_contour.linewidths,
    )
    if options.secondary_contour.labels:
        _apply_secondary_contour_labels(ax, cs, options.secondary_contour)


def _draw_secondary_tri_contour(
    ax: plt.Axes,
    df: pd.DataFrame,
    spec: PlotSpec,
    options: AxesOptions,
    x_scale: UnitScale | None,
    y_scale: UnitScale | None,
) -> None:
    """Overlay a line-only tricontour for a secondary z column (tricontour / tripcolor)."""
    z2_col = options.secondary_contour.column
    if z2_col is None or z2_col not in df.columns:
        return
    tri_df = df[[spec.inputs.primary, spec.inputs.secondary, z2_col]].dropna()
    if len(tri_df) < 3:
        return
    cs = ax.tricontour(
        _apply_scale(tri_df[spec.inputs.primary], x_scale),
        _apply_scale(tri_df[spec.inputs.secondary], y_scale),
        tri_df[z2_col].astype(float).to_numpy(),
        levels=options.secondary_contour.levels,
        colors=options.secondary_contour.color,
        linewidths=options.secondary_contour.linewidths,
    )
    if options.secondary_contour.labels:
        _apply_secondary_contour_labels(ax, cs, options.secondary_contour)


def _apply_secondary_contour_labels(
    ax: plt.Axes,
    cs: Any,
    options: SecondaryContourOptions,
) -> None:
    kwargs: dict[str, Any] = {"inline": True}
    if options.label_fontsize is not None:
        kwargs["fontsize"] = options.label_fontsize
    ax.clabel(cs, **kwargs)


def _require_columns(df: pd.DataFrame, columns: list[str | None]) -> None:
    missing = [column for column in columns if column is not None and column not in df.columns]
    if missing:
        raise KeyError(f"DataFrame is missing columns: {missing}")
