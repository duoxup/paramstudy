# Code Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all issues identified in the code review: dead code, import style, type accuracy, code duplication, long lines, missing `py.typed`, and a fragile colormap access on ContourSet.

**Architecture:** Six independent tasks, each touching a narrow slice of the codebase. No new public APIs. Tasks can be done in order; each leaves the test suite green before the next begins.

**Tech Stack:** Python 3.10+, pandas, numpy, matplotlib, pytest.

---

## File Map

| File | What changes |
|------|-------------|
| `src/paramstudy/scale.py` | Remove dead else, fix `list()` conversion |
| `src/paramstudy/planner.py` | Remove dead `or (None,)` guard |
| `src/paramstudy/metadata.py` | Merge split imports |
| `src/paramstudy/options.py` | Fix `AggFunc` callable signature |
| `src/paramstudy/render/_util.py` | New file — shared `_format_value` helper |
| `src/paramstudy/render/matplotlib_axes.py` | Long-line fixes, import shared helper |
| `src/paramstudy/render/matplotlib_figure.py` | Fix ContourSet `.cmap`, import shared helper |
| `src/paramstudy/py.typed` | New empty marker file |
| `pyproject.toml` | Declare `package-data` for `py.typed` |
| `tests/test_matplotlib_figure.py` | New test for shared colorbar on contour |

---

## Task 1: Dead code and import cleanup in scale.py and planner.py

**Files:**
- Modify: `src/paramstudy/scale.py:95-97` (remove dead else)
- Modify: `src/paramstudy/scale.py:101` (remove unnecessary `list()`)
- Modify: `src/paramstudy/planner.py:112` (remove dead `or (None,)`)

- [ ] **Step 1: Remove the dead `else` branch in `autoscale_unit` and the unnecessary `list()` call**

In `src/paramstudy/scale.py`, replace:

```python
def autoscale_unit(values: Iterable[float], unit: UnitLike) -> UnitScale:
    """Return a display scale for values expressed in ``unit``.

    Only :class:`SimpleUnit` currently supports prefix changes. Compound units
    are structurally represented but intentionally not auto-scaled yet.
    """

    if isinstance(unit, SimpleUnit):
        return _autoscale_simple_unit(values, unit)
    if isinstance(unit, (CompoundUnit, Unitless)):
        return UnitScale(multiplier=1.0, unit=unit)
    return UnitScale(multiplier=1.0, unit=unit)


def _autoscale_simple_unit(values: Iterable[float], unit: SimpleUnit) -> UnitScale:
    array = np.asarray(list(values), dtype=float)
```

With:

```python
def autoscale_unit(values: Iterable[float], unit: UnitLike) -> UnitScale:
    """Return a display scale for values expressed in ``unit``.

    Only :class:`SimpleUnit` currently supports prefix changes. Compound units
    are structurally represented but intentionally not auto-scaled yet.
    """

    if isinstance(unit, SimpleUnit):
        return _autoscale_simple_unit(values, unit)
    return UnitScale(multiplier=1.0, unit=unit)


def _autoscale_simple_unit(values: Iterable[float], unit: SimpleUnit) -> UnitScale:
    array = np.asarray(values, dtype=float)
```

- [ ] **Step 2: Remove the dead guard in `_build_grid_figure_plan`**

In `src/paramstudy/planner.py`, replace:

```python
    row_axis = row_values or (None,)
    col_axis = col_values or (None,)
```

With:

```python
    row_axis = row_values
    col_axis = col_values
```

- [ ] **Step 3: Run tests to verify nothing is broken**

```bash
PYTHONPATH=src MPLCONFIGDIR=/tmp/matplotlib-paramstudy python -m pytest tests/ -q
```

Expected: `28 passed`

---

## Task 2: Merge split imports in metadata.py

**Files:**
- Modify: `src/paramstudy/metadata.py:9-10`

- [ ] **Step 1: Merge the two imports from `paramstudy.unit` into one**

In `src/paramstudy/metadata.py`, replace:

```python
from paramstudy.unit import CompoundUnit, SimpleUnit, UnitLike, Unitless
from paramstudy.unit import parse_unit, unit_from_dict, unit_to_dict
```

With:

```python
from paramstudy.unit import (
    CompoundUnit,
    SimpleUnit,
    UnitLike,
    Unitless,
    parse_unit,
    unit_from_dict,
    unit_to_dict,
)
```

- [ ] **Step 2: Run tests**

```bash
PYTHONPATH=src MPLCONFIGDIR=/tmp/matplotlib-paramstudy python -m pytest tests/ -q
```

Expected: `28 passed`

---

## Task 3: Fix `AggFunc` callable type

**Files:**
- Modify: `src/paramstudy/options.py:1-9`

The current `AggFunc = str | Callable[[Any], float]` implies the callable receives a single value. In practice `grouped.apply(agg)` passes a `pd.Series` (the group) to the callable.

- [ ] **Step 1: Fix the import and type alias**

In `src/paramstudy/options.py`, replace:

```python
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


AggFunc = str | Callable[[Any], float]
```

With:

```python
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd

AggFunc = str | Callable[["pd.Series"], float]
```

- [ ] **Step 2: Run tests**

```bash
PYTHONPATH=src MPLCONFIGDIR=/tmp/matplotlib-paramstudy python -m pytest tests/ -q
```

Expected: `28 passed`

---

## Task 4: Fix long lines in matplotlib_axes.py

**Files:**
- Modify: `src/paramstudy/render/matplotlib_axes.py:116`
- Modify: `src/paramstudy/render/matplotlib_axes.py:384`

- [ ] **Step 1: Break the long scatter call at line 116**

In `src/paramstudy/render/matplotlib_axes.py`, replace:

```python
    mappable = ax.scatter(_apply_scale(subset[x_col], x_scale), _apply_scale(subset[y_col], y_scale), **kwargs)
```

With:

```python
    mappable = ax.scatter(
        _apply_scale(subset[x_col], x_scale),
        _apply_scale(subset[y_col], y_scale),
        **kwargs,
    )
```

- [ ] **Step 2: Break the long agg dispatch at line 384**

In `src/paramstudy/render/matplotlib_axes.py`, replace:

```python
    values = getattr(grouped, options.data.agg)() if isinstance(options.data.agg, str) else grouped.apply(options.data.agg)
```

With:

```python
    if isinstance(options.data.agg, str):
        values = getattr(grouped, options.data.agg)()
    else:
        values = grouped.apply(options.data.agg)
```

- [ ] **Step 3: Run tests**

```bash
PYTHONPATH=src MPLCONFIGDIR=/tmp/matplotlib-paramstudy python -m pytest tests/ -q
```

Expected: `28 passed`

---

## Task 5: Extract shared `_format_value` helper

Both `matplotlib_axes.py` and `matplotlib_figure.py` define identical `_format_value`/`_format_title_value` functions. Extract to a shared internal utility module.

**Files:**
- Create: `src/paramstudy/render/_util.py`
- Modify: `src/paramstudy/render/matplotlib_axes.py` (remove local def, add import)
- Modify: `src/paramstudy/render/matplotlib_figure.py` (remove local def, add import)

- [ ] **Step 1: Create `src/paramstudy/render/_util.py`**

```python
from __future__ import annotations

from typing import Any

import pandas as pd

from paramstudy.scale import UnitScale


def format_scaled_value(value: Any, scale: UnitScale | None) -> str:
    """Format a single value with optional unit scaling for display in labels/titles."""
    if pd.isna(value):
        return "NaN"
    try:
        scaled = float(value) * (scale.multiplier if scale is not None else 1.0)
        text = f"{scaled:.6g}"
    except Exception:
        return str(value)
    if scale is not None:
        text += scale.render_unit()
    return text
```

- [ ] **Step 2: Run tests to confirm the new file itself doesn't break anything**

```bash
PYTHONPATH=src MPLCONFIGDIR=/tmp/matplotlib-paramstudy python -m pytest tests/ -q
```

Expected: `28 passed`

- [ ] **Step 3: Replace `_format_value` in `matplotlib_axes.py`**

Add the import near the top of the imports block in `src/paramstudy/render/matplotlib_axes.py`:

```python
from paramstudy.render._util import format_scaled_value
```

Then replace the local function definition:

```python
def _format_value(value: Any, scale: UnitScale | None) -> str:
    if pd.isna(value):
        return "NaN"
    try:
        scaled = float(value) * (scale.multiplier if scale is not None else 1.0)
        text = f"{scaled:.6g}"
    except Exception:
        return str(value)
    if scale is not None:
        text += scale.render_unit()
    return text
```

With just a one-line alias (so call sites need no change):

```python
_format_value = format_scaled_value
```

- [ ] **Step 4: Replace `_format_title_value` in `matplotlib_figure.py`**

Add the import near the top of the imports block in `src/paramstudy/render/matplotlib_figure.py`:

```python
from paramstudy.render._util import format_scaled_value
```

Then replace the local function definition:

```python
def _format_title_value(value: Any, scale: UnitScale | None) -> str:
    if pd.isna(value):
        return "NaN"
    try:
        scaled = float(value) * (scale.multiplier if scale is not None else 1.0)
        text = f"{scaled:.6g}"
    except Exception:
        return str(value)
    if scale is not None:
        text += scale.render_unit()
    return text
```

With just a one-line alias:

```python
_format_title_value = format_scaled_value
```

- [ ] **Step 5: Run tests**

```bash
PYTHONPATH=src MPLCONFIGDIR=/tmp/matplotlib-paramstudy python -m pytest tests/ -q
```

Expected: `28 passed`

---

## Task 6: Fix ContourSet colormap access and add test

`_shared_colorbar_mappable` in `matplotlib_figure.py` calls `mappable.cmap` to construct a `ScalarMappable`. For `ContourSet` objects (returned by `contourf`/`contour`), `.cmap` exists but the access pattern varies across matplotlib versions. The safe approach: use `getattr` with a fallback and avoid assuming the cmap type.

**Files:**
- Modify: `src/paramstudy/render/matplotlib_figure.py:357-367`
- Modify: `tests/test_matplotlib_figure.py` (add one test)

- [ ] **Step 1: Write the failing test**

Add this test at the bottom of `tests/test_matplotlib_figure.py`:

```python
def test_shared_colorbar_with_contour_does_not_raise():
    df = pd.DataFrame(
        {
            "x": [250, 500, 750, 250, 500, 750, 250, 500, 750,
                  250, 500, 750, 250, 500, 750, 250, 500, 750],
            "y": [50, 50, 50, 100, 100, 100, 150, 150, 150,
                  50, 50, 50, 100, 100, 100, 150, 150, 150],
            "z": [1e6, 2e6, 3e6, 1.5e6, 2.5e6, 3.5e6, 2e6, 3e6, 4e6,
                  2e6, 3e6, 4e6, 2.5e6, 3.5e6, 4.5e6, 3e6, 4e6, 5e6],
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
```

- [ ] **Step 2: Run to confirm it passes (or fails for the right reason)**

```bash
PYTHONPATH=src MPLCONFIGDIR=/tmp/matplotlib-paramstudy python -m pytest tests/test_matplotlib_figure.py::test_shared_colorbar_with_contour_does_not_raise -v
```

Expected: PASS (matplotlib's ContourSet does expose `.cmap` in recent versions) — if it PASSes already, the fix below is still worthwhile as a defensive guard; if it FAILs, the fix is necessary.

- [ ] **Step 3: Fix `_shared_colorbar_mappable` to access `.cmap` safely**

In `src/paramstudy/render/matplotlib_figure.py`, replace:

```python
def _shared_colorbar_mappable(items: list[tuple[Any, plt.Axes, AxesSlot]]) -> Any:
    mappable = items[0][0]
    clim = [item[0].get_clim() for item in items if hasattr(item[0], "get_clim")]
    if not clim:
        return mappable
    vmins = [pair[0] for pair in clim if pair[0] is not None]
    vmaxs = [pair[1] for pair in clim if pair[1] is not None]
    if not vmins or not vmaxs:
        return mappable
    norm = Normalize(vmin=min(vmins), vmax=max(vmaxs))
    return ScalarMappable(norm=norm, cmap=mappable.cmap)
```

With:

```python
def _shared_colorbar_mappable(items: list[tuple[Any, plt.Axes, AxesSlot]]) -> Any:
    mappable = items[0][0]
    clim = [item[0].get_clim() for item in items if hasattr(item[0], "get_clim")]
    if not clim:
        return mappable
    vmins = [pair[0] for pair in clim if pair[0] is not None]
    vmaxs = [pair[1] for pair in clim if pair[1] is not None]
    if not vmins or not vmaxs:
        return mappable
    norm = Normalize(vmin=min(vmins), vmax=max(vmaxs))
    cmap = getattr(mappable, "cmap", None)
    return ScalarMappable(norm=norm, cmap=cmap)
```

- [ ] **Step 4: Run all tests**

```bash
PYTHONPATH=src MPLCONFIGDIR=/tmp/matplotlib-paramstudy python -m pytest tests/ -q
```

Expected: `29 passed`

---

## Task 7: Add `py.typed` PEP 561 marker

Without this file, downstream type checkers ignore the package's inline annotations.

**Files:**
- Create: `src/paramstudy/py.typed`
- Modify: `pyproject.toml`

- [ ] **Step 1: Create the empty marker file**

Create `src/paramstudy/py.typed` as an empty file.

- [ ] **Step 2: Declare it as package data in `pyproject.toml`**

Add after the `[tool.setuptools.packages.find]` section:

```toml
[tool.setuptools.package-data]
"paramstudy" = ["py.typed"]
```

- [ ] **Step 3: Run tests to confirm nothing regressed**

```bash
PYTHONPATH=src MPLCONFIGDIR=/tmp/matplotlib-paramstudy python -m pytest tests/ -q
```

Expected: `29 passed`

---

## Self-Review

**Spec coverage check:**

| Review finding | Task |
|---|---|
| Dead else in `autoscale_unit` | Task 1 |
| `list()` conversion in `_autoscale_simple_unit` | Task 1 |
| Dead `or (None,)` in `planner.py` | Task 1 |
| Split imports in `metadata.py` | Task 2 |
| `AggFunc` type mismatch | Task 3 |
| Long lines in `matplotlib_axes.py` | Task 4 |
| Duplicate `_format_value` functions | Task 5 |
| ContourSet `.cmap` fragility | Task 6 |
| Missing `py.typed` | Task 7 |

All 9 review items are covered. The two findings intentionally deferred:
- `_observed_keys` empty-df edge case: current behavior is defensible; adding a test is out of scope for this cleanup pass.
- MICRO prefix `"u"` vs `"μ"`: intentionally deferred (behavior + render change, better done as a separate feature).

**Placeholder scan:** No TBD, no vague steps. Each step has exact file paths and complete code.

**Type consistency:** `format_scaled_value` introduced in Task 5 and used consistently as `_format_value` / `_format_title_value` aliases in both render modules.
