import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from paramstudy.metadata import make_registry
from paramstudy.options import (
    ColorbarMode,
    ColorbarOptions,
    FacetLayoutMode,
    FacetLayoutOptions,
    FigureOptions,
)
from paramstudy.render.matplotlib_figure import draw_figures
from paramstudy.spec import InputMap, PlotKind, PlotSpec, ResponseMap


def test_draw_figures_dispatches_facet_scatter_and_hides_unused_axes():
    df = pd.DataFrame(
        {
            "x": range(5),
            "y": range(5),
            "z": [1e6, 2e6, 1.5e6, 2.5e6, 3e6],
            "r": ["a", "a", "b", "b", "c"],
            "c": [1, 2, 1, 2, 1],
        }
    )
    meta = make_registry(
        {
            "x": ["X", "x", "mm"],
            "y": ["Y", "y", "mrad"],
            "z": ["Power", "P", "W", "MW"],
            "r": ["Row", "r"],
            "c": ["Column", "c"],
        }
    )
    spec = PlotSpec(
        kind=PlotKind.SCATTER,
        inputs=InputMap(primary="x", secondary="y", row="r", col="c"),
        responses=ResponseMap(color="z"),
    )
    options = FigureOptions(
        facets=FacetLayoutOptions(mode=FacetLayoutMode.FACET, ncols=3),
        colorbar=ColorbarOptions(mode=ColorbarMode.FIGURE),
    )

    results = draw_figures(df, spec, meta=meta, figure_options=options)

    assert len(results) == 1
    result = results[0]
    assert result.axes.shape == (2, 3)
    assert result.plan.slots[-1].is_unused
    assert not result.axes.ravel()[-1].axison
    assert any(axes_result is not None for axes_result in result.axes_results)
    plt.close(result.figure)


def test_figure_colorbar_mode_row_adds_one_colorbar_per_row():
    df = pd.DataFrame(
        {
            "x": [1, 2, 1, 2, 1, 2, 1, 2],
            "y": [10, 10, 20, 20, 10, 10, 20, 20],
            "z": [1e6, 2e6, 1.5e6, 2.5e6, 2e6, 3e6, 2.5e6, 3.5e6],
            "row": ["a", "a", "a", "a", "b", "b", "b", "b"],
            "col": ["c1", "c1", "c1", "c1", "c2", "c2", "c2", "c2"],
        }
    )
    meta = ps_meta()
    spec = PlotSpec(
        kind=PlotKind.HEATMAP,
        inputs=InputMap(primary="x", secondary="y", row="row", col="col"),
        responses=ResponseMap(primary="z"),
    )
    options = FigureOptions(
        facets=FacetLayoutOptions(mode=FacetLayoutMode.GRID),
        colorbar=ColorbarOptions(mode=ColorbarMode.ROW),
    )

    result = draw_figures(df, spec, meta=meta, figure_options=options)[0]

    assert len(result.figure.axes) == result.axes.size + 2
    plt.close(result.figure)


def test_shared_colorbar_uses_global_color_limits():
    df = pd.DataFrame(
        {
            "x": [1, 2, 1, 2, 1, 2, 1, 2],
            "y": [10, 10, 20, 20, 10, 10, 20, 20],
            "z": [1e6, 2e6, 1.5e6, 2.5e6, 10e6, 20e6, 15e6, 25e6],
            "row": ["a", "a", "a", "a", "b", "b", "b", "b"],
        }
    )
    spec = PlotSpec(
        kind=PlotKind.HEATMAP,
        inputs=InputMap(primary="x", secondary="y", row="row"),
        responses=ResponseMap(primary="z"),
    )
    options = FigureOptions(
        facets=FacetLayoutOptions(mode=FacetLayoutMode.FACET, ncols=2),
        colorbar=ColorbarOptions(mode=ColorbarMode.FIGURE),
    )

    result = draw_figures(df, spec, meta=ps_meta(), figure_options=options)[0]
    clims = [axes_result.mappable.get_clim() for axes_result in result.axes_results if axes_result]

    assert len(set(clims)) == 1
    assert clims[0] == (1.0, 25.0)
    plt.close(result.figure)


def test_facet_titles_format_numeric_values_with_metadata_units():
    df = pd.DataFrame(
        {
            "x": [1, 2, 1, 2],
            "y": [10, 10, 20, 20],
            "z": [1e6, 2e6, 1.5e6, 2.5e6],
            "charge": [50, 50, 100, 100],
        }
    )
    meta = ps_meta()
    spec = PlotSpec(
        kind=PlotKind.HEATMAP,
        inputs=InputMap(primary="x", secondary="y", row="charge"),
        responses=ResponseMap(primary="z"),
    )
    options = FigureOptions(facets=FacetLayoutOptions(mode=FacetLayoutMode.FACET, ncols=2))

    result = draw_figures(df, spec, meta=meta, figure_options=options)[0]
    titles = [ax.get_title() for ax in result.axes.ravel()]

    assert "Charge=50pC" in titles
    assert "Charge=100pC" in titles
    plt.close(result.figure)


def test_row_colorbar_uses_per_row_color_limits():
    df = pd.DataFrame(
        {
            "x": [1, 2, 1, 2, 1, 2, 1, 2],
            "y": [10, 10, 20, 20, 10, 10, 20, 20],
            "z": [1e6, 2e6, 3e6, 4e6, 100e6, 200e6, 300e6, 400e6],
            "row": ["a", "a", "a", "a", "b", "b", "b", "b"],
        }
    )
    spec = PlotSpec(
        kind=PlotKind.HEATMAP,
        inputs=InputMap(primary="x", secondary="y", row="row"),
        responses=ResponseMap(primary="z"),
    )
    options = FigureOptions(
        facets=FacetLayoutOptions(mode=FacetLayoutMode.GRID),
        colorbar=ColorbarOptions(mode=ColorbarMode.ROW),
    )

    result = draw_figures(df, spec, meta=ps_meta(), figure_options=options)[0]

    clims_by_row: dict[int, list[tuple[float, float]]] = {}
    for axes_result, slot in zip(result.axes_results, result.plan.slots):
        if axes_result is None or axes_result.mappable is None:
            continue
        clims_by_row.setdefault(slot.layout_row, []).append(axes_result.mappable.get_clim())

    assert set(clims_by_row.keys()) == {0, 1}
    assert clims_by_row[0][0] == pytest.approx((1.0, 4.0))
    assert clims_by_row[1][0] == pytest.approx((100.0, 400.0))
    plt.close(result.figure)


def test_col_colorbar_uses_per_col_color_limits():
    df = pd.DataFrame(
        {
            "x": [1, 2, 1, 2, 1, 2, 1, 2],
            "y": [10, 10, 20, 20, 10, 10, 20, 20],
            "z": [1e6, 2e6, 3e6, 4e6, 100e6, 200e6, 300e6, 400e6],
            "col": ["c1", "c1", "c1", "c1", "c2", "c2", "c2", "c2"],
        }
    )
    spec = PlotSpec(
        kind=PlotKind.HEATMAP,
        inputs=InputMap(primary="x", secondary="y", col="col"),
        responses=ResponseMap(primary="z"),
    )
    options = FigureOptions(
        facets=FacetLayoutOptions(mode=FacetLayoutMode.GRID),
        colorbar=ColorbarOptions(mode=ColorbarMode.COL),
    )

    result = draw_figures(df, spec, meta=ps_meta(), figure_options=options)[0]

    clims_by_col: dict[int, list[tuple[float, float]]] = {}
    for axes_result, slot in zip(result.axes_results, result.plan.slots):
        if axes_result is None or axes_result.mappable is None:
            continue
        clims_by_col.setdefault(slot.layout_col, []).append(axes_result.mappable.get_clim())

    assert set(clims_by_col.keys()) == {0, 1}
    assert clims_by_col[0][0] == pytest.approx((1.0, 4.0))
    assert clims_by_col[1][0] == pytest.approx((100.0, 400.0))
    plt.close(result.figure)


def test_col_mode_subplots_share_group_unit_scale():
    """All subplots in a col share the col's auto-scaled unit, so drawn data
    values map onto the colorbar's vmin..vmax range correctly.
    """
    df = pd.DataFrame(
        {
            "x": [1, 2, 1, 2],
            "y": [10, 10, 20, 20],
            "z": [1e-6, 2e-6, 1e-3, 2e-3],
            "row": ["r0", "r0", "r1", "r1"],
            "col": ["A", "A", "A", "A"],
        }
    )
    meta = make_registry({"z": ["Energy", "E", "J"]})
    spec = PlotSpec(
        kind=PlotKind.HEATMAP,
        inputs=InputMap(primary="x", secondary="y", row="row", col="col"),
        responses=ResponseMap(primary="z"),
    )
    options = FigureOptions(
        facets=FacetLayoutOptions(mode=FacetLayoutMode.GRID),
        colorbar=ColorbarOptions(mode=ColorbarMode.COL),
    )

    result = draw_figures(df, spec, meta=meta, figure_options=options)[0]

    drawn_arrays = []
    clims = []
    for axes_result in result.axes_results:
        if axes_result is None or axes_result.mappable is None:
            continue
        arr = np.asarray(axes_result.mappable.get_array()).ravel()
        drawn_arrays.append(arr[np.isfinite(arr)])
        clims.append(axes_result.mappable.get_clim())

    assert len(set(clims)) == 1
    vmin, vmax = clims[0]
    overall_max = max(arr.max() for arr in drawn_arrays)
    overall_min = min(arr.min() for arr in drawn_arrays)
    assert overall_max == pytest.approx(vmax, rel=1e-6)
    assert overall_min == pytest.approx(vmin, rel=1e-6)
    plt.close(result.figure)


def test_col_mode_colorbar_label_uses_per_group_scale():
    """Each col's colorbar label reflects the col-group's auto-scaled unit."""
    df = pd.DataFrame(
        {
            "x": [1, 2, 1, 2, 1, 2, 1, 2],
            "y": [10, 10, 20, 20, 10, 10, 20, 20],
            "z": [1e-6, 2e-6, 3e-6, 4e-6, 1e-3, 2e-3, 3e-3, 4e-3],
            "row": ["r0", "r0", "r1", "r1"] * 2,
            "col": ["A"] * 4 + ["B"] * 4,
        }
    )
    meta = make_registry({"z": ["Energy", "E", "J"]})
    spec = PlotSpec(
        kind=PlotKind.HEATMAP,
        inputs=InputMap(primary="x", secondary="y", row="row", col="col"),
        responses=ResponseMap(primary="z"),
    )
    options = FigureOptions(
        facets=FacetLayoutOptions(mode=FacetLayoutMode.GRID),
        colorbar=ColorbarOptions(mode=ColorbarMode.COL),
    )

    result = draw_figures(df, spec, meta=meta, figure_options=options)[0]

    main_axes_ids = {id(ax) for ax in result.axes.ravel()}
    cb_axes = [ax for ax in result.figure.axes if id(ax) not in main_axes_ids]
    assert len(cb_axes) == 2

    labels = [ax.get_ylabel() for ax in cb_axes]
    assert any("uJ" in label for label in labels), labels
    assert any("mJ" in label for label in labels), labels
    plt.close(result.figure)


def test_shared_colorbar_with_contour_does_not_raise():
    df = pd.DataFrame(
        {
            "x": [
                250,
                500,
                750,
                250,
                500,
                750,
                250,
                500,
                750,
                250,
                500,
                750,
                250,
                500,
                750,
                250,
                500,
                750,
            ],
            "y": [
                50,
                50,
                50,
                100,
                100,
                100,
                150,
                150,
                150,
                50,
                50,
                50,
                100,
                100,
                100,
                150,
                150,
                150,
            ],
            "z": [
                1e6,
                2e6,
                3e6,
                1.5e6,
                2.5e6,
                3.5e6,
                2e6,
                3e6,
                4e6,
                2e6,
                3e6,
                4e6,
                2.5e6,
                3.5e6,
                4.5e6,
                3e6,
                4e6,
                5e6,
            ],
            "row": ["a"] * 9 + ["b"] * 9,
        }
    )
    spec = PlotSpec(
        kind=PlotKind.CONTOUR,
        inputs=InputMap(primary="x", secondary="y", row="row"),
        responses=ResponseMap(primary="z"),
    )
    options = FigureOptions(
        facets=FacetLayoutOptions(mode=FacetLayoutMode.FACET, ncols=2),
        colorbar=ColorbarOptions(mode=ColorbarMode.FIGURE),
    )

    results = draw_figures(df, spec, figure_options=options)

    assert len(results) == 1
    plt.close(results[0].figure)


def ps_meta():
    return make_registry(
        {
            "x": ["X", "x", "mm"],
            "y": ["Y", "y", "mrad"],
            "z": ["Power", "P", "W", "MW"],
            "row": ["Row", "r"],
            "col": ["Column", "c"],
            "charge": ["Charge", "Q", "pC"],
        }
    )
