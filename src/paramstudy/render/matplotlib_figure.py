from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
import numpy as np
import pandas as pd

from paramstudy.metadata import ColumnMeta, ColumnMetaRegistry
from paramstudy.options import AxesOptions, ColorbarMode, FigureOptions
from paramstudy.planner import AxesSlot, FacetKey, FigurePlan, build_page_plan
from paramstudy.render._util import format_scaled_value
from paramstudy.render.matplotlib_axes import (
    AxesDrawResult,
    draw_contour_axes,
    draw_heatmap_axes,
    draw_line_axes,
    draw_scatter_axes,
    draw_tripcolor_axes,
    draw_tricontour_axes,
)
from paramstudy.scale import UnitScale, resolve_unit_scale
from paramstudy.spec import PlotKind, PlotSpec


@dataclass(frozen=True)
class FigureDrawResult:
    figure: plt.Figure
    axes: np.ndarray
    plan: FigurePlan
    axes_results: tuple[AxesDrawResult | None, ...]


def draw_figures(
    df: pd.DataFrame,
    spec: PlotSpec,
    *,
    meta: ColumnMetaRegistry | None = None,
    axes_options: AxesOptions | None = None,
    figure_options: FigureOptions | None = None,
) -> tuple[FigureDrawResult, ...]:
    """Draw all figures implied by a PlotSpec and FigureOptions."""

    spec.validate()
    axes_options = axes_options or AxesOptions()
    figure_options = figure_options or FigureOptions()
    page_plan = build_page_plan(df, spec, figure_options.facets)

    return tuple(
        _draw_one_figure(df, spec, figure_plan, meta, axes_options, figure_options)
        for figure_plan in page_plan.figures
    )


def _draw_one_figure(
    df: pd.DataFrame,
    spec: PlotSpec,
    plan: FigurePlan,
    meta: ColumnMetaRegistry | None,
    axes_options: AxesOptions,
    figure_options: FigureOptions,
) -> FigureDrawResult:
    figsize = (
        figure_options.layout.figsize_per_ax[0] * plan.ncols,
        figure_options.layout.figsize_per_ax[1] * plan.nrows,
    )
    figure, axes = plt.subplots(
        plan.nrows,
        plan.ncols,
        figsize=figsize,
        sharex=figure_options.layout.sharex,
        sharey=figure_options.layout.sharey,
        squeeze=False,
        layout="constrained",
    )

    axes_results: list[AxesDrawResult | None] = []
    colorbar_items: list[tuple[Any, plt.Axes, AxesSlot]] = []
    slot_color_limits = _resolve_slot_color_limits(
        df, spec, plan, meta, axes_options, figure_options
    )
    axes_flat = axes.ravel()
    for slot in plan.slots:
        ax = axes_flat[slot.index]
        if slot.is_unused:
            ax.axis("off")
            axes_results.append(None)
            continue

        subset = _subset_for_slot(df, spec, slot)
        if not slot.has_data or subset.empty:
            _draw_blank_slot(ax, slot, spec, df, meta, axes_options, figure_options)
            axes_results.append(None)
            continue

        result = _draw_axes(
            ax, subset, spec, meta, axes_options, slot_color_limits.get(slot.index)
        )
        if result.mappable is not None:
            colorbar_items.append((result.mappable, ax, slot))
        _set_slot_title(ax, slot, spec, df, meta, axes_options, figure_options)
        axes_results.append(result)

    _add_colorbars(figure, colorbar_items, df, spec, meta, axes_options, figure_options)
    _set_page_title(figure, plan.page_key, spec, df, meta, axes_options, figure_options)
    return FigureDrawResult(
        figure=figure,
        axes=axes,
        plan=plan,
        axes_results=tuple(axes_results),
    )


def _draw_axes(
    ax: plt.Axes,
    df: pd.DataFrame,
    spec: PlotSpec,
    meta: ColumnMetaRegistry | None,
    options: AxesOptions,
    color_limits: tuple[float, float] | None,
) -> AxesDrawResult:
    if spec.kind is PlotKind.LINE:
        return draw_line_axes(ax, df, spec, meta=meta, options=options)
    if spec.kind is PlotKind.SCATTER:
        return draw_scatter_axes(
            ax, df, spec, meta=meta, options=options, color_limits=color_limits
        )
    if spec.kind is PlotKind.HEATMAP:
        return draw_heatmap_axes(
            ax, df, spec, meta=meta, options=options, color_limits=color_limits
        )
    if spec.kind is PlotKind.CONTOUR:
        return draw_contour_axes(
            ax, df, spec, meta=meta, options=options, color_limits=color_limits
        )
    if spec.kind is PlotKind.TRICONTOUR:
        return draw_tricontour_axes(
            ax, df, spec, meta=meta, options=options, color_limits=color_limits
        )
    if spec.kind is PlotKind.TRIPCOLOR:
        return draw_tripcolor_axes(
            ax, df, spec, meta=meta, options=options, color_limits=color_limits
        )
    raise NotImplementedError(
        f"Matplotlib figure rendering does not support {spec.kind.value!r} yet."
    )


def _subset_for_slot(df: pd.DataFrame, spec: PlotSpec, slot: AxesSlot) -> pd.DataFrame:
    if slot.key is None:
        return df.iloc[0:0]
    subset = df
    subset = _subset_by_value(subset, spec.inputs.page, slot.key.page)
    subset = _subset_by_value(subset, spec.inputs.row, slot.key.row)
    subset = _subset_by_value(subset, spec.inputs.col, slot.key.col)
    return subset


def _subset_by_value(df: pd.DataFrame, column: str | None, value: Any | None) -> pd.DataFrame:
    if column is None:
        return df
    if value is None:
        return df.loc[df[column].isna()]
    return df.loc[df[column] == value]


def _draw_blank_slot(
    ax: plt.Axes,
    slot: AxesSlot,
    spec: PlotSpec,
    df: pd.DataFrame,
    meta: ColumnMetaRegistry | None,
    axes_options: AxesOptions,
    options: FigureOptions,
) -> None:
    ax.set_xticks([])
    ax.set_yticks([])
    _set_slot_title(ax, slot, spec, df, meta, axes_options, options)


def _set_slot_title(
    ax: plt.Axes,
    slot: AxesSlot,
    spec: PlotSpec,
    df: pd.DataFrame,
    meta: ColumnMetaRegistry | None,
    axes_options: AxesOptions,
    options: FigureOptions,
) -> None:
    if not options.titles.show or slot.key is None:
        return
    title = _format_facet_title(
        slot.key,
        spec,
        df,
        meta,
        axes_options,
        options,
        include_page=False,
    )
    if title:
        ax.set_title(title)


def _set_page_title(
    figure: plt.Figure,
    key: FacetKey,
    spec: PlotSpec,
    df: pd.DataFrame,
    meta: ColumnMetaRegistry | None,
    axes_options: AxesOptions,
    options: FigureOptions,
) -> None:
    if not options.titles.show or key.page is None:
        return
    title = _format_facet_title(
        key,
        spec,
        df,
        meta,
        axes_options,
        options,
        include_page=True,
        page_only=True,
    )
    if title:
        figure.suptitle(title)


def _format_facet_title(
    key: FacetKey,
    spec: PlotSpec | None,
    df: pd.DataFrame,
    meta: ColumnMetaRegistry | None,
    axes_options: AxesOptions,
    options: FigureOptions,
    *,
    include_page: bool,
    page_only: bool = False,
) -> str:
    parts: list[str] = []
    if include_page and key.page is not None:
        page_column = (
            spec.inputs.page if spec is not None and spec.inputs.page is not None else "page"
        )
        parts.append(_format_facet_part(page_column, key.page, df, meta, axes_options, options))
    if not page_only:
        if key.row is not None and spec is not None and spec.inputs.row is not None:
            parts.append(
                _format_facet_part(spec.inputs.row, key.row, df, meta, axes_options, options)
            )
        if key.col is not None and spec is not None and spec.inputs.col is not None:
            parts.append(
                _format_facet_part(spec.inputs.col, key.col, df, meta, axes_options, options)
            )
    return options.titles.separator.join(parts)


def _format_facet_part(
    fallback: str,
    value: Any,
    df: pd.DataFrame,
    meta: ColumnMetaRegistry | None,
    axes_options: AxesOptions,
    options: FigureOptions,
) -> str:
    column_meta = _meta(meta, fallback)
    scale = (
        _resolve_column_scale(df, fallback, column_meta, axes_options) if fallback in df else None
    )
    value_text = _format_title_value(value, scale)
    if options.titles.show_keys:
        name = column_meta.display_name(fallback, prefer_symbol=options.titles.prefer_symbol)
        return f"{name}={value_text}"
    return value_text


def _add_colorbars(
    figure: plt.Figure,
    items: list[tuple[Any, plt.Axes, AxesSlot]],
    df: pd.DataFrame,
    spec: PlotSpec,
    meta: ColumnMetaRegistry | None,
    axes_options: AxesOptions,
    figure_options: FigureOptions,
) -> None:
    if not items or figure_options.colorbar.mode is ColorbarMode.NONE:
        return

    label = _colorbar_label(df, spec, meta, axes_options)
    if figure_options.colorbar.mode is ColorbarMode.EACH:
        for mappable, ax, _slot in items:
            colorbar = figure.colorbar(mappable, ax=ax)
            if label:
                colorbar.set_label(label)
        return

    if figure_options.colorbar.mode is ColorbarMode.FIGURE:
        mappable = _shared_colorbar_mappable(items)
        axes = [ax for _mappable, ax, _slot in items]
        colorbar = figure.colorbar(mappable, ax=axes)
        if label:
            colorbar.set_label(label)
        return

    group_index = 1 if figure_options.colorbar.mode is ColorbarMode.ROW else 2
    groups: dict[int, list[tuple[Any, plt.Axes, AxesSlot]]] = {}
    for item in items:
        slot = item[2]
        key = slot.layout_row if group_index == 1 else slot.layout_col
        groups.setdefault(key, []).append(item)
    for group_items in groups.values():
        mappable = _shared_colorbar_mappable(group_items)
        axes = [ax for _mappable, ax, _slot in group_items]
        colorbar = figure.colorbar(mappable, ax=axes)
        if label:
            colorbar.set_label(label)


def _colorbar_label(
    df: pd.DataFrame,
    spec: PlotSpec,
    meta: ColumnMetaRegistry | None,
    options: AxesOptions,
) -> str | None:
    column = spec.responses.color or spec.responses.primary
    if column is None:
        return None
    column_meta = _meta(meta, column)
    scale = _resolve_column_scale(df, column, column_meta, options)
    label = column_meta.display_name(column, prefer_symbol=options.labels.prefer_symbol)
    if options.labels.show_units and scale is not None:
        label = f"{label} [{scale.render_unit()}]"
    return label


def _resolve_column_scale(
    df: pd.DataFrame,
    column: str,
    column_meta: ColumnMeta,
    options: AxesOptions,
) -> UnitScale | None:
    if column_meta.unit is None or not pd.api.types.is_numeric_dtype(df[column]):
        return None
    return resolve_unit_scale(
        df[column].dropna().to_numpy(),
        column_meta.unit,
        preferred_unit=column_meta.preferred_unit,
        autoscale=options.units.autoscale,
        use_preferred=options.units.use_preferred,
    )


def _resolve_slot_color_limits(
    df: pd.DataFrame,
    spec: PlotSpec,
    plan: FigurePlan,
    meta: ColumnMetaRegistry | None,
    axes_options: AxesOptions,
    figure_options: FigureOptions,
) -> dict[int, tuple[float, float] | None]:
    """Per-slot color limits scoped by the active colorbar mode."""
    column = spec.responses.color or spec.responses.primary
    if column is None or column not in df or not pd.api.types.is_numeric_dtype(df[column]):
        return {}

    mode = figure_options.colorbar.mode
    user_override = (
        axes_options.color.vmin is not None or axes_options.color.vmax is not None
    )

    if mode in (ColorbarMode.NONE, ColorbarMode.EACH) and not user_override:
        return {}

    if mode in (ColorbarMode.NONE, ColorbarMode.EACH, ColorbarMode.FIGURE):
        limits = _column_limits(df, column, meta, axes_options)
        return {slot.index: limits for slot in plan.slots}

    group_attr = "layout_row" if mode is ColorbarMode.ROW else "layout_col"
    by_group: dict[int, list[AxesSlot]] = {}
    for slot in plan.slots:
        if not slot.has_data or slot.is_unused:
            continue
        by_group.setdefault(getattr(slot, group_attr), []).append(slot)

    result: dict[int, tuple[float, float] | None] = {}
    for group_slots in by_group.values():
        frames = [_subset_for_slot(df, spec, s) for s in group_slots]
        group_df = pd.concat(frames) if frames else df.iloc[0:0]
        limits = _column_limits(group_df, column, meta, axes_options)
        for slot in group_slots:
            result[slot.index] = limits
    return result


def _column_limits(
    df: pd.DataFrame,
    column: str,
    meta: ColumnMetaRegistry | None,
    axes_options: AxesOptions,
) -> tuple[float, float] | None:
    if column not in df or not pd.api.types.is_numeric_dtype(df[column]):
        return None
    column_meta = _meta(meta, column)
    scale = _resolve_column_scale(df, column, column_meta, axes_options)
    multiplier = scale.multiplier if scale is not None else 1.0
    values = df[column].dropna().astype(float).to_numpy() * multiplier
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return None
    vmin = float(np.nanmin(finite)) if axes_options.color.vmin is None else axes_options.color.vmin
    vmax = float(np.nanmax(finite)) if axes_options.color.vmax is None else axes_options.color.vmax
    return vmin, vmax


def _shared_colorbar_mappable(items: list[tuple[Any, plt.Axes, AxesSlot]]) -> Any:
    mappable = items[0][0]
    clim = [item[0].get_clim() for item in items if isinstance(item[0], ScalarMappable)]
    if not clim:
        return mappable
    vmins = [pair[0] for pair in clim if pair[0] is not None]
    vmaxs = [pair[1] for pair in clim if pair[1] is not None]
    if not vmins or not vmaxs:
        return mappable
    norm = Normalize(vmin=min(vmins), vmax=max(vmaxs))
    cmap = getattr(mappable, "cmap", None)
    return ScalarMappable(norm=norm, cmap=cmap)


_format_title_value = format_scaled_value


def _meta(registry: ColumnMetaRegistry | None, column: str) -> ColumnMeta:
    return registry.get(column) if registry is not None else ColumnMeta()
