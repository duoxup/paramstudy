from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import paramstudy as ps
from paramstudy.options import (
    AxesOptions,
    ColorOptions,
    ColorbarMode,
    ColorbarOptions,
    ContourOptions,
    FacetLayoutMode,
    FacetLayoutOptions,
    FigureOptions,
    TripcolorOptions,
)


OUTPUT_DIR = Path(__file__).parent / "output"


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    rng = np.random.default_rng(42)
    meta = ps.make_registry(
        {
            "energy": ["Beam energy", "E", "MeV", "GeV"],
            "charge": ["Charge", "Q", "pC"],
            "power": ["Peak power", "P", "W", "MW"],
            "x": ["Horizontal offset", "x", "mm"],
            "xp": ["Horizontal angle", "x'", "mrad"],
            "beta": ["Beta setting", "beta"],
        }
    )

    line_df = _line_grid(rng)
    _save(ps.line(line_df, x="energy", y="power", group="charge", meta=meta), "gallery_line.png")

    scatter_df = _irregular_points(rng)
    scatter_results = ps.scatter(
        scatter_df,
        x="x",
        y="xp",
        color="power",
        row="beta",
        meta=meta,
        axes_options=AxesOptions(color=ColorOptions(cmap="viridis")),
        figure_options=FigureOptions(
            facets=FacetLayoutOptions(mode=FacetLayoutMode.FACET, ncols=2),
            colorbar=ColorbarOptions(mode=ColorbarMode.FIGURE),
        ),
    )
    _save(scatter_results, "gallery_scatter.png")

    grid_df = _regular_grid()
    common_figure_options = FigureOptions(colorbar=ColorbarOptions(mode=ColorbarMode.FIGURE))
    _save(
        ps.heatmap(
            grid_df,
            x="energy",
            y="charge",
            z="power",
            meta=meta,
            axes_options=AxesOptions(color=ColorOptions(cmap="plasma")),
            figure_options=common_figure_options,
        ),
        "gallery_heatmap.png",
    )
    _save(
        ps.contour(
            grid_df,
            x="energy",
            y="charge",
            z="power",
            meta=meta,
            axes_options=AxesOptions(
                color=ColorOptions(cmap="viridis"),
                contour=ContourOptions(levels=14),
            ),
            figure_options=common_figure_options,
        ),
        "gallery_contour.png",
    )
    _save(
        ps.tricontour(
            scatter_df,
            x="x",
            y="xp",
            z="power",
            meta=meta,
            axes_options=AxesOptions(
                color=ColorOptions(cmap="viridis"),
                contour=ContourOptions(levels=14),
            ),
            figure_options=common_figure_options,
        ),
        "gallery_tricontour.png",
    )
    _save(
        ps.tripcolor(
            scatter_df,
            x="x",
            y="xp",
            z="power",
            meta=meta,
            axes_options=AxesOptions(
                color=ColorOptions(cmap="viridis"),
                tripcolor=TripcolorOptions(shading="gouraud"),
            ),
            figure_options=common_figure_options,
        ),
        "gallery_tripcolor.png",
    )


def _line_grid(rng: np.random.Generator) -> pd.DataFrame:
    energy = np.tile(np.linspace(250, 2200, 9), 3)
    charge = np.repeat([50.0, 100.0, 200.0], 9)
    power = (0.35 + 0.00042 * energy + 0.0012 * charge + rng.normal(0, 0.04, energy.size)) * 1e6
    return pd.DataFrame({"energy": energy, "charge": charge, "power": power})


def _regular_grid() -> pd.DataFrame:
    rows = []
    for charge in np.linspace(40, 260, 18):
        for energy in np.linspace(250, 2200, 24):
            power = (
                0.35
                + 0.00042 * energy
                + 0.0012 * charge
                + 0.12 * np.sin(energy / 350) * np.cos(charge / 80)
            ) * 1e6
            rows.append((energy, charge, power))
    return pd.DataFrame(rows, columns=["energy", "charge", "power"])


def _irregular_points(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for beta in ["low", "high"]:
        for _ in range(70):
            x = rng.normal(0.0, 0.42)
            xp = rng.normal(0.0, 0.28)
            power = (
                1.2
                + 0.8 * np.exp(-(x**2 / 0.22 + xp**2 / 0.12))
                + 0.12 * np.sin(8 * x)
                + rng.normal(0, 0.04)
            ) * 1e6
            rows.append((x, xp, power, beta))
    return pd.DataFrame(rows, columns=["x", "xp", "power", "beta"])


def _save(results: tuple[Any, ...], filename: str) -> None:
    for index, result in enumerate(results, start=1):
        suffix = "" if len(results) == 1 else f"_{index}"
        path = OUTPUT_DIR / filename.replace(".png", f"{suffix}.png")
        result.figure.savefig(path, dpi=140)
        plt.close(result.figure)


if __name__ == "__main__":
    main()
