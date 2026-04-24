import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

import paramstudy as ps
from paramstudy.options import FacetLayoutMode, FacetLayoutOptions, FigureOptions


def test_line_api_draws_grouped_line():
    df = pd.DataFrame(
        {
            "energy": [250, 500, 250, 500],
            "charge": [50, 50, 100, 100],
            "power": [1e6, 2e6, 1.5e6, 2.5e6],
        }
    )
    meta = ps.make_registry(
        {
            "energy": ["Beam energy", "E", "MeV", "GeV"],
            "charge": ["Charge", "Q", "pC"],
            "power": ["Peak power", "P", "W", "MW"],
        }
    )

    results = ps.line(df, x="energy", y="power", group="charge", meta=meta)

    assert len(results) == 1
    ax = results[0].axes[0, 0]
    assert ax.get_xlabel() == "Beam energy [GeV]"
    assert len(ax.lines) == 2
    plt.close(results[0].figure)


def test_scatter_api_draws_faceted_scatter():
    df = pd.DataFrame(
        {
            "x": [0.1, 0.2, 0.3, 0.4],
            "y": [0.2, 0.1, 0.4, 0.3],
            "z": [1e6, 2e6, 3e6, 4e6],
            "row": ["a", "a", "b", "b"],
        }
    )
    meta = ps.make_registry(
        {
            "x": ["X", "x", "mm"],
            "y": ["Y", "y", "mrad"],
            "z": ["Power", "P", "W", "MW"],
            "row": ["Row", "r"],
        }
    )

    results = ps.scatter(
        df,
        x="x",
        y="y",
        color="z",
        row="row",
        meta=meta,
        figure_options=FigureOptions(
            facets=FacetLayoutOptions(mode=FacetLayoutMode.FACET, ncols=2),
        ),
    )

    assert len(results) == 1
    assert results[0].axes.shape == (1, 2)
    plt.close(results[0].figure)


def test_heatmap_api_draws_regular_grid():
    df = pd.DataFrame(
        {
            "energy": [250, 500, 250, 500],
            "charge": [50, 50, 100, 100],
            "power": [1e6, 2e6, 1.5e6, 2.5e6],
        }
    )
    meta = ps.make_registry(
        {
            "energy": ["Beam energy", "E", "MeV", "GeV"],
            "charge": ["Charge", "Q", "pC"],
            "power": ["Peak power", "P", "W", "MW"],
        }
    )

    results = ps.heatmap(df, x="energy", y="charge", z="power", meta=meta)

    assert len(results) == 1
    assert results[0].axes.shape == (1, 1)
    assert any(axes_result is not None for axes_result in results[0].axes_results)
    plt.close(results[0].figure)


def test_contour_api_draws_regular_grid():
    df = pd.DataFrame(
        {
            "energy": [250, 500, 750, 250, 500, 750, 250, 500, 750],
            "charge": [50, 50, 50, 100, 100, 100, 150, 150, 150],
            "power": [1e6, 2e6, 3e6, 1.5e6, 2.5e6, 3.5e6, 2e6, 3e6, 4e6],
        }
    )
    meta = ps.make_registry(
        {
            "energy": ["Beam energy", "E", "MeV", "GeV"],
            "charge": ["Charge", "Q", "pC"],
            "power": ["Peak power", "P", "W", "MW"],
        }
    )

    results = ps.contour(df, x="energy", y="charge", z="power", meta=meta)

    assert len(results) == 1
    assert results[0].axes.shape == (1, 1)
    assert any(axes_result is not None for axes_result in results[0].axes_results)
    plt.close(results[0].figure)


def test_tricontour_api_draws_irregular_grid():
    df = pd.DataFrame(
        {
            "x": [0.0, 0.4, -0.3, 0.2, -0.2, 0.5],
            "y": [0.0, 0.2, 0.3, -0.4, -0.1, -0.2],
            "z": [1e6, 1.5e6, 1.4e6, 1.2e6, 1.1e6, 1.3e6],
        }
    )
    meta = ps.make_registry(
        {
            "x": ["X", "x", "mm"],
            "y": ["Y", "y", "mrad"],
            "z": ["Power", "P", "W", "MW"],
        }
    )

    results = ps.tricontour(df, x="x", y="y", z="z", meta=meta)

    assert len(results) == 1
    assert results[0].axes.shape == (1, 1)
    assert any(axes_result is not None for axes_result in results[0].axes_results)
    plt.close(results[0].figure)


def test_tripcolor_api_draws_irregular_grid():
    df = pd.DataFrame(
        {
            "x": [0.0, 0.4, -0.3, 0.2, -0.2, 0.5],
            "y": [0.0, 0.2, 0.3, -0.4, -0.1, -0.2],
            "z": [1e6, 1.5e6, 1.4e6, 1.2e6, 1.1e6, 1.3e6],
        }
    )
    meta = ps.make_registry(
        {
            "x": ["X", "x", "mm"],
            "y": ["Y", "y", "mrad"],
            "z": ["Power", "P", "W", "MW"],
        }
    )

    results = ps.tripcolor(df, x="x", y="y", z="z", meta=meta)

    assert len(results) == 1
    assert results[0].axes.shape == (1, 1)
    assert any(axes_result is not None for axes_result in results[0].axes_results)
    plt.close(results[0].figure)
