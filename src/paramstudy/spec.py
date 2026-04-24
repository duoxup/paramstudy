from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PlotKind(Enum):
    LINE = "line"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    CONTOUR = "contour"
    TRICONTOUR = "tricontour"
    TRIPCOLOR = "tripcolor"


@dataclass(frozen=True)
class InputMap:
    """Mapping from independent variables to plot-dimension slots.

    ``primary`` is the first within-axes input variable.
    ``secondary`` is the second within-axes input variable when the plot kind
    needs one. For line plots, it represents the optional group/legend variable.
    For scatter/grid plots, it represents the y-axis input variable.
    """

    primary: str
    secondary: str | None = None
    row: str | None = None
    col: str | None = None
    page: str | None = None

    def variables(self) -> tuple[str, ...]:
        return tuple(
            variable
            for variable in (self.primary, self.secondary, self.row, self.col, self.page)
            if variable is not None
        )


@dataclass(frozen=True)
class ResponseMap:
    """Mapping from dependent variables to visual response channels."""

    primary: str | None = None
    color: str | None = None
    size: str | None = None

    def variables(self) -> tuple[str, ...]:
        return tuple(
            variable for variable in (self.primary, self.color, self.size) if variable is not None
        )


@dataclass(frozen=True)
class PlotSpec:
    kind: PlotKind
    inputs: InputMap
    responses: ResponseMap

    def validate(self) -> None:
        _validate_input_slots(self.inputs)

        if self.kind is PlotKind.LINE:
            if self.responses.primary is None:
                raise ValueError("Line plots require ResponseMap.primary as the y-axis response.")
            return

        if self.kind is PlotKind.SCATTER:
            if self.inputs.secondary is None:
                raise ValueError("Scatter plots require InputMap.secondary as the y-axis input.")
            return

        if self.kind in {
            PlotKind.HEATMAP,
            PlotKind.CONTOUR,
            PlotKind.TRICONTOUR,
            PlotKind.TRIPCOLOR,
        }:
            if self.inputs.secondary is None:
                raise ValueError(f"{self.kind.value} plots require InputMap.secondary.")
            if self.responses.primary is None:
                raise ValueError(f"{self.kind.value} plots require ResponseMap.primary.")
            return

        raise ValueError(f"Unsupported plot kind: {self.kind!r}")

    def input_variables(self) -> tuple[str, ...]:
        return self.inputs.variables()

    def response_variables(self) -> tuple[str, ...]:
        return self.responses.variables()

    def all_variables(self) -> tuple[str, ...]:
        return (*self.input_variables(), *self.response_variables())


def _validate_input_slots(inputs: InputMap) -> None:
    variables = inputs.variables()
    if not inputs.primary:
        raise ValueError("InputMap.primary must be non-empty.")
    if len(variables) > 5:
        raise ValueError(
            "A plot can display at most 5 independent variables: "
            "primary, secondary, row, col, page."
        )
    duplicates = sorted({variable for variable in variables if variables.count(variable) > 1})
    if duplicates:
        raise ValueError(f"Input variables cannot occupy multiple slots: {duplicates}")
