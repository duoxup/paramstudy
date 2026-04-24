from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

from paramstudy.metadata import ColumnMetaRegistry
from paramstudy.options import AxesOptions, FigureOptions
from paramstudy.spec import InputMap, PlotKind, PlotSpec, ResponseMap

if TYPE_CHECKING:
    from paramstudy.render.matplotlib_figure import FigureDrawResult


def line(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    group: str | None = None,
    row: str | None = None,
    col: str | None = None,
    page: str | None = None,
    meta: ColumnMetaRegistry | None = None,
    axes_options: AxesOptions | None = None,
    figure_options: FigureOptions | None = None,
) -> tuple["FigureDrawResult", ...]:
    """Draw line figures for a parameter study DataFrame."""

    spec = PlotSpec(
        kind=PlotKind.LINE,
        inputs=InputMap(primary=x, secondary=group, row=row, col=col, page=page),
        responses=ResponseMap(primary=y),
    )
    return _draw_figures(
        df,
        spec,
        meta=meta,
        axes_options=axes_options,
        figure_options=figure_options,
    )


def scatter(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    color: str | None = None,
    size: str | None = None,
    row: str | None = None,
    col: str | None = None,
    page: str | None = None,
    meta: ColumnMetaRegistry | None = None,
    axes_options: AxesOptions | None = None,
    figure_options: FigureOptions | None = None,
) -> tuple["FigureDrawResult", ...]:
    """Draw scatter figures for a parameter study DataFrame."""

    spec = PlotSpec(
        kind=PlotKind.SCATTER,
        inputs=InputMap(primary=x, secondary=y, row=row, col=col, page=page),
        responses=ResponseMap(color=color, size=size),
    )
    return _draw_figures(
        df,
        spec,
        meta=meta,
        axes_options=axes_options,
        figure_options=figure_options,
    )


def heatmap(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    z: str,
    row: str | None = None,
    col: str | None = None,
    page: str | None = None,
    meta: ColumnMetaRegistry | None = None,
    axes_options: AxesOptions | None = None,
    figure_options: FigureOptions | None = None,
) -> tuple["FigureDrawResult", ...]:
    """Draw regular-grid heatmap figures for a parameter study DataFrame."""

    spec = PlotSpec(
        kind=PlotKind.HEATMAP,
        inputs=InputMap(primary=x, secondary=y, row=row, col=col, page=page),
        responses=ResponseMap(primary=z),
    )
    return _draw_figures(
        df,
        spec,
        meta=meta,
        axes_options=axes_options,
        figure_options=figure_options,
    )


def contour(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    z: str,
    row: str | None = None,
    col: str | None = None,
    page: str | None = None,
    meta: ColumnMetaRegistry | None = None,
    axes_options: AxesOptions | None = None,
    figure_options: FigureOptions | None = None,
) -> tuple["FigureDrawResult", ...]:
    """Draw regular-grid contour figures for a parameter study DataFrame."""

    spec = PlotSpec(
        kind=PlotKind.CONTOUR,
        inputs=InputMap(primary=x, secondary=y, row=row, col=col, page=page),
        responses=ResponseMap(primary=z),
    )
    return _draw_figures(
        df,
        spec,
        meta=meta,
        axes_options=axes_options,
        figure_options=figure_options,
    )


def tricontour(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    z: str,
    row: str | None = None,
    col: str | None = None,
    page: str | None = None,
    meta: ColumnMetaRegistry | None = None,
    axes_options: AxesOptions | None = None,
    figure_options: FigureOptions | None = None,
) -> tuple["FigureDrawResult", ...]:
    """Draw irregular-grid tricontour figures for a parameter study DataFrame."""

    spec = PlotSpec(
        kind=PlotKind.TRICONTOUR,
        inputs=InputMap(primary=x, secondary=y, row=row, col=col, page=page),
        responses=ResponseMap(primary=z),
    )
    return _draw_figures(
        df,
        spec,
        meta=meta,
        axes_options=axes_options,
        figure_options=figure_options,
    )


def tripcolor(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    z: str,
    row: str | None = None,
    col: str | None = None,
    page: str | None = None,
    meta: ColumnMetaRegistry | None = None,
    axes_options: AxesOptions | None = None,
    figure_options: FigureOptions | None = None,
) -> tuple["FigureDrawResult", ...]:
    """Draw irregular-grid tripcolor figures for a parameter study DataFrame."""

    spec = PlotSpec(
        kind=PlotKind.TRIPCOLOR,
        inputs=InputMap(primary=x, secondary=y, row=row, col=col, page=page),
        responses=ResponseMap(primary=z),
    )
    return _draw_figures(
        df,
        spec,
        meta=meta,
        axes_options=axes_options,
        figure_options=figure_options,
    )


def _draw_figures(*args: Any, **kwargs: Any) -> tuple["FigureDrawResult", ...]:
    from paramstudy.render.matplotlib_figure import draw_figures

    return draw_figures(*args, **kwargs)
