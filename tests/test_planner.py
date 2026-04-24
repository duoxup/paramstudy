import pandas as pd
import pytest

from paramstudy.options import FacetLayoutMode, FacetLayoutOptions, MissingFacetPolicy
from paramstudy.planner import build_page_plan
from paramstudy.spec import InputMap, PlotKind, PlotSpec, ResponseMap


def _spec():
    return PlotSpec(
        kind=PlotKind.HEATMAP,
        inputs=InputMap(primary="x", secondary="y", row="r", col="c", page="p"),
        responses=ResponseMap(primary="z"),
    )


def _df():
    return pd.DataFrame(
        {
            "x": [1, 1, 1, 1, 1],
            "y": [1, 1, 1, 1, 1],
            "z": [1, 2, 3, 4, 5],
            "r": ["a", "a", "b", "a", "b"],
            "c": [1, 2, 1, 1, 2],
            "p": ["P1", "P1", "P1", "P2", "P2"],
        }
    )


def test_grid_plan_uses_global_row_col_layout():
    plan = build_page_plan(_df(), _spec(), FacetLayoutOptions(mode=FacetLayoutMode.GRID))

    assert len(plan.figures) == 2
    assert plan.row_values == ("a", "b")
    assert plan.col_values == (1, 2)
    assert all((figure.nrows, figure.ncols) == (2, 2) for figure in plan.figures)
    assert any(not slot.has_data for slot in plan.figures[0].slots)


def test_grid_missing_error_policy():
    with pytest.raises(ValueError, match="Missing GRID facet combination"):
        build_page_plan(
            _df(),
            _spec(),
            FacetLayoutOptions(mode=FacetLayoutMode.GRID, missing=MissingFacetPolicy.ERROR),
        )


def test_facet_plan_marks_tail_slots_unused():
    df = pd.DataFrame(
        {
            "x": range(5),
            "y": range(5),
            "z": range(5),
            "r": ["a", "a", "b", "b", "c"],
            "c": [1, 2, 1, 2, 1],
        }
    )
    spec = PlotSpec(
        kind=PlotKind.SCATTER,
        inputs=InputMap(primary="x", secondary="y", row="r", col="c"),
        responses=ResponseMap(color="z"),
    )

    plan = build_page_plan(df, spec, FacetLayoutOptions(mode=FacetLayoutMode.FACET, ncols=3))
    figure = plan.figures[0]

    assert (figure.nrows, figure.ncols) == (2, 3)
    assert len(figure.slots) == 6
    assert figure.slots[-1].is_unused
    assert figure.slots[-1].key is None
