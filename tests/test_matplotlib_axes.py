import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from paramstudy.metadata import make_registry
from paramstudy.options import AxesOptions
from paramstudy.render.matplotlib_axes import (
    draw_contour_axes,
    draw_heatmap_axes,
    draw_line_axes,
    draw_scatter_axes,
    draw_tripcolor_axes,
    draw_tricontour_axes,
)
from paramstudy.spec import InputMap, PlotKind, PlotSpec, ResponseMap


def test_draw_line_axes_with_group_and_preferred_units():
    df = pd.DataFrame(
        {
            "energy": [250, 500, 250, 500],
            "charge": [50, 50, 100, 100],
            "power": [1e6, 2e6, 1.5e6, 2.5e6],
        }
    )
    meta = make_registry(
        {
            "energy": ["Beam energy", "E", "MeV", "GeV"],
            "charge": ["Charge", "Q", "pC"],
            "power": ["Peak power", "P", "W", "MW"],
        }
    )
    spec = PlotSpec(
        kind=PlotKind.LINE,
        inputs=InputMap(primary="energy", secondary="charge"),
        responses=ResponseMap(primary="power"),
    )

    figure, ax = plt.subplots()
    draw_line_axes(ax, df, spec, meta=meta, options=AxesOptions())

    assert ax.get_xlabel() == "Beam energy [GeV]"
    assert ax.get_ylabel() == "Peak power [MW]"
    assert ax.get_legend() is not None
    assert len(ax.lines) == 2
    plt.close(figure)


def test_draw_scatter_axes_returns_mappable_for_color_response():
    df = pd.DataFrame({"x": [0.1, 0.2], "xp": [0.3, 0.4], "power": [1e6, 2e6]})
    meta = make_registry(
        {
            "x": ["Horizontal offset", "x", "mm"],
            "xp": ["Horizontal angle", "x'", "mrad"],
            "power": ["Peak power", "P", "W", "MW"],
        }
    )
    spec = PlotSpec(
        kind=PlotKind.SCATTER,
        inputs=InputMap(primary="x", secondary="xp"),
        responses=ResponseMap(color="power"),
    )

    figure, ax = plt.subplots()
    result = draw_scatter_axes(ax, df, spec, meta=meta, options=AxesOptions())

    assert result.mappable is not None
    assert ax.get_xlabel() == "Horizontal offset [um]"
    assert ax.get_ylabel() == "Horizontal angle [urad]"
    plt.close(figure)


def test_draw_heatmap_axes_returns_mappable():
    df = pd.DataFrame(
        {
            "energy": [250, 500, 250, 500],
            "charge": [50, 50, 100, 100],
            "power": [1e6, 2e6, 1.5e6, 2.5e6],
        }
    )
    meta = make_registry(
        {
            "energy": ["Beam energy", "E", "MeV", "GeV"],
            "charge": ["Charge", "Q", "pC"],
            "power": ["Peak power", "P", "W", "MW"],
        }
    )
    spec = PlotSpec(
        kind=PlotKind.HEATMAP,
        inputs=InputMap(primary="energy", secondary="charge"),
        responses=ResponseMap(primary="power"),
    )

    figure, ax = plt.subplots()
    result = draw_heatmap_axes(ax, df, spec, meta=meta, options=AxesOptions())

    assert result.mappable is not None
    assert ax.get_xlabel() == "Beam energy [GeV]"
    assert ax.get_ylabel() == "Charge [pC]"
    plt.close(figure)


def test_draw_contour_axes_returns_mappable():
    df = pd.DataFrame(
        {
            "energy": [250, 500, 750, 250, 500, 750, 250, 500, 750],
            "charge": [50, 50, 50, 100, 100, 100, 150, 150, 150],
            "power": [1e6, 2e6, 3e6, 1.5e6, 2.5e6, 3.5e6, 2e6, 3e6, 4e6],
        }
    )
    meta = make_registry(
        {
            "energy": ["Beam energy", "E", "MeV", "GeV"],
            "charge": ["Charge", "Q", "pC"],
            "power": ["Peak power", "P", "W", "MW"],
        }
    )
    spec = PlotSpec(
        kind=PlotKind.CONTOUR,
        inputs=InputMap(primary="energy", secondary="charge"),
        responses=ResponseMap(primary="power"),
    )

    figure, ax = plt.subplots()
    result = draw_contour_axes(ax, df, spec, meta=meta, options=AxesOptions())

    assert result.mappable is not None
    assert ax.get_xlabel() == "Beam energy [GeV]"
    assert ax.get_ylabel() == "Charge [pC]"
    plt.close(figure)


def test_draw_tricontour_axes_returns_mappable():
    df = pd.DataFrame(
        {
            "x": [0.0, 0.4, -0.3, 0.2, -0.2, 0.5],
            "xp": [0.0, 0.2, 0.3, -0.4, -0.1, -0.2],
            "power": [1e6, 1.5e6, 1.4e6, 1.2e6, 1.1e6, 1.3e6],
        }
    )
    meta = make_registry(
        {
            "x": ["Horizontal offset", "x", "mm"],
            "xp": ["Horizontal angle", "x'", "mrad"],
            "power": ["Peak power", "P", "W", "MW"],
        }
    )
    spec = PlotSpec(
        kind=PlotKind.TRICONTOUR,
        inputs=InputMap(primary="x", secondary="xp"),
        responses=ResponseMap(primary="power"),
    )

    figure, ax = plt.subplots()
    result = draw_tricontour_axes(ax, df, spec, meta=meta, options=AxesOptions())

    assert result.mappable is not None
    assert ax.get_xlabel() == "Horizontal offset [um]"
    assert ax.get_ylabel() == "Horizontal angle [urad]"
    plt.close(figure)


def test_draw_tripcolor_axes_returns_mappable():
    df = pd.DataFrame(
        {
            "x": [0.0, 0.4, -0.3, 0.2, -0.2, 0.5],
            "xp": [0.0, 0.2, 0.3, -0.4, -0.1, -0.2],
            "power": [1e6, 1.5e6, 1.4e6, 1.2e6, 1.1e6, 1.3e6],
        }
    )
    meta = make_registry(
        {
            "x": ["Horizontal offset", "x", "mm"],
            "xp": ["Horizontal angle", "x'", "mrad"],
            "power": ["Peak power", "P", "W", "MW"],
        }
    )
    spec = PlotSpec(
        kind=PlotKind.TRIPCOLOR,
        inputs=InputMap(primary="x", secondary="xp"),
        responses=ResponseMap(primary="power"),
    )

    figure, ax = plt.subplots()
    result = draw_tripcolor_axes(ax, df, spec, meta=meta, options=AxesOptions())

    assert result.mappable is not None
    assert ax.get_xlabel() == "Horizontal offset [um]"
    assert ax.get_ylabel() == "Horizontal angle [urad]"
    plt.close(figure)
