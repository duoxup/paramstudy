from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd

AggFunc = str | Callable[["pd.Series"], float]


class FacetLayoutMode(Enum):
    """How row/col input slots map to subplot layout."""

    GRID = "grid"
    FACET = "facet"


class MissingFacetPolicy(Enum):
    """How GRID layout handles missing row/col combinations."""

    BLANK = "blank"
    HIDE = "hide"
    ERROR = "error"


class ColorbarMode(Enum):
    NONE = "none"
    EACH = "each"
    FIGURE = "figure"
    ROW = "row"
    COL = "col"


@dataclass(frozen=True)
class UnitOptions:
    autoscale: bool = True
    use_preferred: bool = True


@dataclass(frozen=True)
class LabelOptions:
    prefer_symbol: bool = False
    show_units: bool = True


@dataclass(frozen=True)
class AxesDataOptions:
    sort_primary: bool = True
    agg: AggFunc | None = None


@dataclass(frozen=True)
class LegendOptions:
    show: bool = True
    loc: str = "best"
    title: str | None = None


@dataclass(frozen=True)
class ColorOptions:
    cmap: str | None = None
    vmin: float | None = None
    vmax: float | None = None


@dataclass(frozen=True)
class ContourOptions:
    levels: int | Sequence[float] = 10
    filled: bool = True
    labels: bool = False


@dataclass(frozen=True)
class TripcolorOptions:
    shading: str = "flat"


@dataclass(frozen=True)
class ScaleOptions:
    x: str = "linear"
    y: str = "linear"
    z: str = "linear"


@dataclass(frozen=True)
class AxesOptions:
    data: AxesDataOptions = field(default_factory=AxesDataOptions)
    labels: LabelOptions = field(default_factory=LabelOptions)
    units: UnitOptions = field(default_factory=UnitOptions)
    scale: ScaleOptions = field(default_factory=ScaleOptions)
    legend: LegendOptions = field(default_factory=LegendOptions)
    color: ColorOptions = field(default_factory=ColorOptions)
    contour: ContourOptions = field(default_factory=ContourOptions)
    tripcolor: TripcolorOptions = field(default_factory=TripcolorOptions)


@dataclass(frozen=True)
class FacetOrder:
    row: Sequence[Any] | None = None
    col: Sequence[Any] | None = None
    page: Sequence[Any] | None = None


@dataclass(frozen=True)
class FacetLayoutOptions:
    mode: FacetLayoutMode = FacetLayoutMode.GRID
    missing: MissingFacetPolicy = MissingFacetPolicy.BLANK
    order: FacetOrder = field(default_factory=FacetOrder)
    ncols: int | None = None
    sort: bool = True


@dataclass(frozen=True)
class FigureLayoutOptions:
    figsize_per_ax: tuple[float, float] = (4.8, 3.6)
    sharex: bool = False
    sharey: bool = False


@dataclass(frozen=True)
class TitleOptions:
    show: bool = True
    show_keys: bool = True
    separator: str = ", "
    prefer_symbol: bool = False


@dataclass(frozen=True)
class ColorbarOptions:
    mode: ColorbarMode = ColorbarMode.EACH


@dataclass(frozen=True)
class FigureOptions:
    layout: FigureLayoutOptions = field(default_factory=FigureLayoutOptions)
    facets: FacetLayoutOptions = field(default_factory=FacetLayoutOptions)
    titles: TitleOptions = field(default_factory=TitleOptions)
    colorbar: ColorbarOptions = field(default_factory=ColorbarOptions)
