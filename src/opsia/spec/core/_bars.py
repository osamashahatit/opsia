"""Specs for the bars branch: fill, border, layout and labels."""

from pydantic import Field

from opsia.spec.core._labels import BarLabelSpec
from opsia.spec.core._types import BaseSpec, Color, LineStyle, Number, Value


class BarFillSpec(BaseSpec):
    """The inside of the bars, plus the highlight for the highest and lowest bar.

    ``color`` and ``alpha`` take one value for every bar, a tuple assigned to
    series in order, or a mapping by series or category name (§4.8). The
    ``max_*`` and ``min_*`` fields are written by ``.extrema()`` (§4.14).

    Examples
    --------
    >>> spec = BarFillSpec(color=("#4C72B0", "#DD8452"), max_color="#E24A33")
    >>> spec.color
    ('#4C72B0', '#DD8452')
    >>> spec.max_color
    '#E24A33'
    """

    color: Value[Color] | None = Field(
        default=None,
        description="The fill colour of the bars.",
        json_schema_extra={"value_mapped": True},
    )
    alpha: Value[Number] | None = Field(
        default=None,
        description="The fill opacity of the bars, from 0 to 1.",
        json_schema_extra={"value_mapped": True},
    )
    max_color: Color | None = Field(
        default=None,
        description="The fill colour of the highest bar.",
    )
    min_color: Color | None = Field(
        default=None,
        description="The fill colour of the lowest bar.",
    )
    max_alpha: Number | None = Field(
        default=None,
        description="The fill opacity of the highest bar, from 0 to 1.",
    )
    min_alpha: Number | None = Field(
        default=None,
        description="The fill opacity of the lowest bar, from 0 to 1.",
    )


class BarBorderSpec(BaseSpec):
    """The outline of the bars, plus the highlight for the highest and lowest bar.

    ``color``, ``alpha``, ``style`` and ``width`` are value-mapped (§4.8).
    The ``max_*`` and ``min_*`` fields are written by ``.extrema()`` (§4.14).

    Examples
    --------
    >>> spec = BarBorderSpec(color="#FFFFFF", width=1, max_width=1.5)
    >>> spec.color, spec.width, spec.max_width
    ('#FFFFFF', 1.0, 1.5)
    """

    color: Value[Color] | None = Field(
        default=None,
        description="The outline colour of the bars.",
        json_schema_extra={"value_mapped": True},
    )
    alpha: Value[Number] | None = Field(
        default=None,
        description="The outline opacity of the bars, from 0 to 1.",
        json_schema_extra={"value_mapped": True},
    )
    style: Value[LineStyle] | None = Field(
        default=None,
        description="The dash style of the bar outlines.",
        json_schema_extra={"value_mapped": True},
    )
    width: Value[Number] | None = Field(
        default=None,
        description="The outline width of the bars, in points.",
        json_schema_extra={"value_mapped": True},
    )
    max_color: Color | None = Field(
        default=None,
        description="The outline colour of the highest bar.",
    )
    min_color: Color | None = Field(
        default=None,
        description="The outline colour of the lowest bar.",
    )
    max_alpha: Number | None = Field(
        default=None,
        description="The outline opacity of the highest bar, from 0 to 1.",
    )
    min_alpha: Number | None = Field(
        default=None,
        description="The outline opacity of the lowest bar, from 0 to 1.",
    )
    max_width: Number | None = Field(
        default=None,
        description="The outline width of the highest bar, in points.",
    )
    min_width: Number | None = Field(
        default=None,
        description="The outline width of the lowest bar, in points.",
    )
    max_style: LineStyle | None = Field(
        default=None,
        description="The outline dash style of the highest bar.",
    )
    min_style: LineStyle | None = Field(
        default=None,
        description="The outline dash style of the lowest bar.",
    )


class BarLayoutSpec(BaseSpec):
    """The thickness of the bars and the gaps between them (§4.7).

    Each field applies to some variants only and is ignored by the others.

    Examples
    --------
    >>> spec = BarLayoutSpec(width=0.8, cluster_width=0.7, stack_gap=0.0)
    >>> spec.width, spec.cluster_width, spec.stack_gap
    (0.8, 0.7, 0.0)
    """

    width: Number | None = Field(
        default=None,
        description="The thickness of each bar, in category units; standard and "
        "stacked only.",
    )
    cluster_width: Number | None = Field(
        default=None,
        description="The width of a whole cluster of bars, in category units; "
        "clustered only.",
    )
    cluster_gap: Number | None = Field(
        default=None,
        description="The gap between bars in one cluster, in category units; clustered "
        "only.",
    )
    stack_gap: Number | None = Field(
        default=None,
        description="The gap between stacked segments, as a fraction of the largest "
        "stack total; stacked only.",
    )


class BarsSpec(BaseSpec):
    """The bars branch: styling that applies to bar charts only.

    Examples
    --------
    >>> spec = BarsSpec(layout=BarLayoutSpec(width=0.6))
    >>> spec.layout.width
    0.6
    >>> spec.fill.color is None
    True
    """

    fill: BarFillSpec = Field(
        default_factory=BarFillSpec,
        description="The inside of the bars.",
    )
    border: BarBorderSpec = Field(
        default_factory=BarBorderSpec,
        description="The outline of the bars.",
    )
    layout: BarLayoutSpec = Field(
        default_factory=BarLayoutSpec,
        description="The bar thickness and gaps.",
    )
    label: BarLabelSpec = Field(
        default_factory=BarLabelSpec,
        description="The data labels on the bars.",
    )
