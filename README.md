# paramstudy

`paramstudy` is a small Python package for working with and visualizing parameter
studies stored in long-form pandas DataFrames.

The intended data model is:

- each row is one sampled parameter condition or one simulation/experiment result;
- input/control columns define the parameter space;
- output/response columns define measured or simulated quantities;
- metadata provides labels, symbols, units, and preferred display units.

The package starts with point-based and series-based plots, then can grow toward
grid-based plots such as heatmaps, contours, and irregular-grid triangulation.

## Example

```python
import pandas as pd
import paramstudy as ps

from paramstudy.options import FacetLayoutMode, FacetLayoutOptions, FigureOptions

df = pd.DataFrame(
    {
        "energy": [1, 2, 3, 1, 2, 3],
        "charge": [10, 10, 10, 20, 20, 20],
        "power": [4, 8, 11, 5, 10, 13],
    }
)

meta = ps.make_registry(
    {
        "energy": ["Beam energy", "E", "MeV", "GeV"],
        "charge": ["Charge", "Q", "pC"],
        "power": ["Peak power", "P", "W", "MW"],
    }
)

results = ps.line(
    df,
    x="energy",
    y="power",
    group="charge",
    meta=meta,
    figure_options=FigureOptions(
        facets=FacetLayoutOptions(mode=FacetLayoutMode.FACET),
    ),
)
```

`line`, `scatter`, `heatmap`, `contour`, `tricontour`, and `tripcolor` all return
a tuple of figure results. A `page` input creates multiple figures.

## Plot Kinds

- `line(df, x, y, group=...)`: `x` is the primary input, `group` is the optional secondary input, and `y` is the response.
- `scatter(df, x, y, color=..., size=...)`: `x/y` are two input dimensions; `color/size` are response channels.
- `heatmap(df, x, y, z)`: regular-grid 2D input data with `z` as the response.
- `contour(df, x, y, z)`: regular-grid contour or filled contour.
- `tricontour(df, x, y, z)`: irregular 2D input data with triangular contouring.
- `tripcolor(df, x, y, z)`: irregular 2D input data with triangular color cells.

## Layout

All plot functions accept `row`, `col`, and `page`.

- `FacetLayoutMode.GRID`: `row` and `col` are interpreted as a 2D subplot grid. Missing combinations are meaningful and controlled by `MissingFacetPolicy`.
- `FacetLayoutMode.FACET`: observed `row/col` combinations are packed into a compact subplot list. Tail axes with no combination are hidden.
- `page`: each unique value becomes a separate figure; row/col layout is global across pages.

## Colorbars

`ColorbarOptions(mode=...)` supports:

- `NONE`: no colorbar.
- `EACH`: one colorbar per subplot.
- `FIGURE`: one shared colorbar per figure.
- `ROW`: one shared colorbar per subplot row.
- `COL`: one shared colorbar per subplot column.

Shared colorbar modes use a shared color scale across the relevant subplots. You can
override the automatic limits with `ColorOptions(vmin=..., vmax=...)`.

## Examples

Install the package in development mode and run the gallery script:

```bash
pip install -e ".[dev]"
python examples/demo_gallery.py
```

## Current Scope

Implemented foundation:

- column metadata and JSON serialization;
- structured unit parsing/rendering and unit-aware scaling;
- plot specification for independent variables and response variables;
- GRID/FACET page and subplot planning for long-form DataFrames;
- Matplotlib Axes-level `line` and `scatter` drawing;
- Matplotlib Axes-level regular-grid `heatmap` drawing;
- Matplotlib Axes-level regular-grid `contour` drawing;
- Matplotlib Axes-level irregular-grid `tricontour` drawing;
- Matplotlib Axes-level irregular-grid `tripcolor` drawing;
- Matplotlib Figure-level dispatch over page/row/col plans.

Planned extensions:

- interpolation helpers for irregular-to-grid visualization;
- richer plot specifications and style options.
