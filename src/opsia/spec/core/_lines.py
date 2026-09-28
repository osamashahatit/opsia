"""Specs for the lines branch: stroke, area, marker and labels."""

from pydantic import Field

from opsia.spec.core._labels import LineLabelSpec
from opsia.spec.core._types import BaseSpec, Color, LineStyle, Number, Value


class LineStrokeSpec(BaseSpec):
    """The drawn line of each series.

    Every field is value-mapped: one value for every line, a tuple assigned to
    series in order, or a mapping by name (§4.8).

    Examples
    --------
    >>> spec = LineStrokeSpec(color={"2019": "#E24A33"}, width=2)
    >>> spec.color["2019"], spec.width
    ('#E24A33', 2.0)
    """

    color: Value[Color] | None = Field(
        default=None,
        description="The colour of the lines.",
        json_schema_extra={"value_mapped": True},
    )
    alpha: Value[Number] | None = Field(
        default=None,
        description="The opacity of the lines, from 0 to 1.",
        json_schema_extra={"value_mapped": True},
    )
    style: Value[LineStyle] | None = Field(
        default=None,
        description="The dash style of the lines.",
        json_schema_extra={"value_mapped": True},
    )
    width: Value[Number] | None = Field(
        default=None,
        description="The width of the lines, in points.",
        json_schema_extra={"value_mapped": True},
    )


class LineAreaSpec(BaseSpec):
    """The filled area beneath each line.

    Whether an area is drawn is chosen with ``area=True`` on the chart call,
    not here; this node only styles it.

    Examples
    --------
    >>> spec = LineAreaSpec(alpha=0.2)
    >>> spec.alpha
    0.2
    """

    color: Value[Color] | None = Field(
        default=None,
        description="The fill colour of the area under each line.",
        json_schema_extra={"value_mapped": True},
    )
    alpha: Value[Number] | None = Field(
        default=None,
        description="The fill opacity of the area under each line, from 0 to 1.",
        json_schema_extra={"value_mapped": True},
    )


class LineMarkerSpec(BaseSpec):
    """The symbol drawn at each data point of a line.

    Every field is value-mapped (§4.8).

    Examples
    --------
    >>> spec = LineMarkerSpec(shape=("o", "s", "^"), size=6)
    >>> spec.shape, spec.size
    (('o', 's', '^'), 6.0)
    """

    shape: Value[str] | None = Field(
        default=None,
        description='The Matplotlib marker name of the point symbols; "none" hides '
        "them.",
        json_schema_extra={"value_mapped": True},
    )
    face_color: Value[Color] | None = Field(
        default=None,
        description="The fill colour of the point symbols.",
        json_schema_extra={"value_mapped": True},
    )
    face_alpha: Value[Number] | None = Field(
        default=None,
        description="The fill opacity of the point symbols, from 0 to 1.",
        json_schema_extra={"value_mapped": True},
    )
    size: Value[Number] | None = Field(
        default=None,
        description="The size of the point symbols, in points.",
        json_schema_extra={"value_mapped": True},
    )
    border_color: Value[Color] | None = Field(
        default=None,
        description="The outline colour of the point symbols.",
        json_schema_extra={"value_mapped": True},
    )
    border_alpha: Value[Number] | None = Field(
        default=None,
        description="The outline opacity of the point symbols, from 0 to 1.",
        json_schema_extra={"value_mapped": True},
    )
    border_width: Value[Number] | None = Field(
        default=None,
        description="The outline width of the point symbols, in points.",
        json_schema_extra={"value_mapped": True},
    )


class LinesSpec(BaseSpec):
    """The lines branch: styling that applies to line charts only.

    Examples
    --------
    >>> spec = LinesSpec(stroke=LineStrokeSpec(width=2))
    >>> spec.stroke.width
    2.0
    >>> spec.marker.shape is None
    True
    """

    stroke: LineStrokeSpec = Field(
        default_factory=LineStrokeSpec,
        description="The drawn lines.",
    )
    area: LineAreaSpec = Field(
        default_factory=LineAreaSpec,
        description="The area under each line.",
    )
    marker: LineMarkerSpec = Field(
        default_factory=LineMarkerSpec,
        description="The data point symbols.",
    )
    label: LineLabelSpec = Field(
        default_factory=LineLabelSpec,
        description="The data labels on the lines.",
    )
