from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import ceil
from typing import Any

import pandas as pd

from paramstudy.options import FacetLayoutMode, FacetLayoutOptions, MissingFacetPolicy
from paramstudy.spec import InputMap, PlotSpec


@dataclass(frozen=True)
class FacetKey:
    page: Any | None = None
    row: Any | None = None
    col: Any | None = None


@dataclass(frozen=True)
class AxesSlot:
    """One subplot slot in a figure plan.

    ``layout_row`` and ``layout_col`` always refer to subplot array indices.
    In GRID mode they also correspond to row/col facet-value positions.
    In FACET mode they only describe compact subplot placement.
    """

    index: int
    layout_row: int
    layout_col: int
    key: FacetKey | None
    has_data: bool
    is_unused: bool = False


@dataclass(frozen=True)
class FigurePlan:
    page_key: FacetKey
    nrows: int
    ncols: int
    slots: tuple[AxesSlot, ...]


@dataclass(frozen=True)
class PagePlan:
    figures: tuple[FigurePlan, ...]
    layout_mode: FacetLayoutMode
    row_values: tuple[Any, ...]
    col_values: tuple[Any, ...]
    page_values: tuple[Any, ...]


def build_page_plan(
    df: pd.DataFrame,
    spec: PlotSpec,
    options: FacetLayoutOptions | None = None,
) -> PagePlan:
    """Build a pure data plan for pages and axes slots.

    Row/col/page value orders are global across pages so figure layouts remain
    stable when paging through a higher-dimensional parameter study.
    """

    spec.validate()
    options = options or FacetLayoutOptions()
    _require_input_columns(df, spec.inputs)

    page_values = _ordered_values(df, spec.inputs.page, options.order.page, sort=options.sort)
    row_values = _ordered_values(df, spec.inputs.row, options.order.row, sort=options.sort)
    col_values = _ordered_values(df, spec.inputs.col, options.order.col, sort=options.sort)

    figures = tuple(
        _build_figure_plan(df, spec.inputs, page_value, row_values, col_values, options)
        for page_value in page_values
    )
    return PagePlan(
        figures=figures,
        layout_mode=options.mode,
        row_values=row_values,
        col_values=col_values,
        page_values=page_values,
    )


def _build_figure_plan(
    df: pd.DataFrame,
    inputs: InputMap,
    page_value: Any | None,
    row_values: tuple[Any, ...],
    col_values: tuple[Any, ...],
    options: FacetLayoutOptions,
) -> FigurePlan:
    page_key = FacetKey(page=page_value)
    page_df = _subset_by_value(df, inputs.page, page_value)
    if options.mode is FacetLayoutMode.GRID:
        return _build_grid_figure_plan(page_df, inputs, page_key, row_values, col_values, options)
    if options.mode is FacetLayoutMode.FACET:
        return _build_facet_figure_plan(page_df, inputs, page_key, options)
    raise ValueError(f"Unsupported facet layout mode: {options.mode!r}")


def _build_grid_figure_plan(
    df: pd.DataFrame,
    inputs: InputMap,
    page_key: FacetKey,
    row_values: tuple[Any, ...],
    col_values: tuple[Any, ...],
    options: FacetLayoutOptions,
) -> FigurePlan:
    row_axis = row_values
    col_axis = col_values
    nrows = len(row_axis)
    ncols = len(col_axis)
    observed = _observed_keys(df, inputs)

    slots: list[AxesSlot] = []
    for row_index, row_value in enumerate(row_axis):
        for col_index, col_value in enumerate(col_axis):
            key = FacetKey(page=page_key.page, row=row_value, col=col_value)
            has_data = (row_value, col_value) in observed
            if not has_data and options.missing is MissingFacetPolicy.ERROR:
                raise ValueError(
                    f"Missing GRID facet combination: row={row_value!r}, col={col_value!r}"
                )
            slots.append(
                AxesSlot(
                    index=len(slots),
                    layout_row=row_index,
                    layout_col=col_index,
                    key=key,
                    has_data=has_data,
                    is_unused=not has_data and options.missing is MissingFacetPolicy.HIDE,
                )
            )

    return FigurePlan(page_key=page_key, nrows=nrows, ncols=ncols, slots=tuple(slots))


def _build_facet_figure_plan(
    df: pd.DataFrame,
    inputs: InputMap,
    page_key: FacetKey,
    options: FacetLayoutOptions,
) -> FigurePlan:
    keys = tuple(
        FacetKey(page=page_key.page, row=row_value, col=col_value)
        for row_value, col_value in _observed_keys(df, inputs)
    )
    n_data = max(1, len(keys))
    ncols = max(1, min(options.ncols or 3, n_data))
    nrows = max(1, int(ceil(n_data / ncols)))

    slots: list[AxesSlot] = []
    for index, key in enumerate(keys):
        slots.append(
            AxesSlot(
                index=index,
                layout_row=index // ncols,
                layout_col=index % ncols,
                key=key,
                has_data=True,
            )
        )

    for index in range(len(keys), nrows * ncols):
        slots.append(
            AxesSlot(
                index=index,
                layout_row=index // ncols,
                layout_col=index % ncols,
                key=None,
                has_data=False,
                is_unused=True,
            )
        )

    return FigurePlan(page_key=page_key, nrows=nrows, ncols=ncols, slots=tuple(slots))


def _require_input_columns(df: pd.DataFrame, inputs: InputMap) -> None:
    missing = [column for column in inputs.variables() if column not in df.columns]
    if missing:
        raise KeyError(f"DataFrame is missing input columns: {missing}")


def _ordered_values(
    df: pd.DataFrame,
    column: str | None,
    explicit_order: Sequence[Any] | None,
    *,
    sort: bool,
) -> tuple[Any, ...]:
    if column is None:
        return (None,)
    if explicit_order is not None:
        return tuple(explicit_order)

    values = list(dict.fromkeys(df[column].dropna().tolist()))
    if sort:
        try:
            values = sorted(values)
        except TypeError:
            pass
    return tuple(values)


def _observed_keys(df: pd.DataFrame, inputs: InputMap) -> tuple[tuple[Any | None, Any | None], ...]:
    columns = [column for column in (inputs.row, inputs.col) if column is not None]
    if not columns:
        return ((None, None),) if not df.empty else tuple()

    unique = df.loc[:, columns].dropna().drop_duplicates()
    try:
        unique = unique.sort_values(by=columns)
    except TypeError:
        pass

    observed: list[tuple[Any | None, Any | None]] = []
    for values in unique.itertuples(index=False, name=None):
        value_map = dict(zip(columns, values))
        observed.append((value_map.get(inputs.row), value_map.get(inputs.col)))
    return tuple(observed)


def _subset_by_value(df: pd.DataFrame, column: str | None, value: Any | None) -> pd.DataFrame:
    if column is None:
        return df
    if value is None:
        return df.loc[df[column].isna()]
    return df.loc[df[column] == value]
