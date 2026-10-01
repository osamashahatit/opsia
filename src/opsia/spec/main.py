"""The Spec models: a chart's whole configuration, as frozen data.

``ChartSpec`` is the root. Its tree mirrors ``chart.format`` (§4.2), so
``chart.format.bars.fill.set(color=...)`` writes ``spec.bars.fill.color``,
the same address a theme file uses. Every leaf field defaults to None,
meaning not set (§5.4). Specs are never edited; a change builds a new one
(§3.5.2).

Every spec is a frozen Pydantic model that rejects unknown keys (§9.3.1),
so a bad value or a misspelt key is caught when a spec is built.

Three helpers work on whole specs. ``replace_at`` changes one node and
returns a new tree (§3.5.2), ``merge_layers`` lays one spec over another
(§5.4), and ``build_spec_error`` turns a Pydantic validation error into one
readable ``ValueError`` (§9.6). Recorders and the theme loader call them;
users do not.

Two more turn a value-mapped setting into one value per artist (§4.8):
``resolve_per_item`` for bars and line points, ``resolve_per_series`` for
whole lines and areas. Recorders call them to check dict keys early; the
renderer calls them to draw.
"""

from pydantic import Field

from opsia.spec.core._axis import (
    AxisGridSpec,
    AxisMarginSpec,
    AxisScaleSpec,
    AxisSpec,
    AxisSpineSpec,
    AxisTickSpec,
    AxisTitleSpec,
    DataAxisSpec,
    GridLineSpec,
    SpineSideSpec,
    TickMajorSpec,
    TickMarkerSpec,
    TickMinorSpec,
    TickTextSpec,
)
from opsia.spec.core._bars import BarBorderSpec, BarFillSpec, BarLayoutSpec, BarsSpec
from opsia.spec.core._errors import build_spec_error
from opsia.spec.core._labels import (
    BarCategoryLabelSpec,
    BarLabelSpec,
    BarStandardLabelSpec,
    LabelFrameSpec,
    LineCategoryLabelSpec,
    LineLabelSpec,
    LineStandardLabelSpec,
)
from opsia.spec.core._legend import (
    LegendFrameSpec,
    LegendLayoutSpec,
    LegendMarkerSpec,
    LegendSpec,
    LegendTextSpec,
    LegendTitleSpec,
)
from opsia.spec.core._lines import (
    LineAreaSpec,
    LineMarkerSpec,
    LinesSpec,
    LineStrokeSpec,
)
from opsia.spec.core._merge import merge_layers
from opsia.spec.core._replace import replace_at
from opsia.spec.core._resolve import resolve_per_item, resolve_per_series
from opsia.spec.core._types import (
    BaseSpec,
    ByName,
    Color,
    Flag,
    FontName,
    HorizontalAlignment,
    Integer,
    LineStyle,
    NamedValueSpec,
    Number,
    NumericSpec,
    Position,
    Value,
)

__all__ = [
    "AxisGridSpec",
    "AxisMarginSpec",
    "AxisScaleSpec",
    "AxisSpec",
    "AxisSpineSpec",
    "AxisTickSpec",
    "AxisTitleSpec",
    "BarBorderSpec",
    "BarCategoryLabelSpec",
    "BarFillSpec",
    "BarLabelSpec",
    "BarLayoutSpec",
    "BarStandardLabelSpec",
    "BarsSpec",
    "ByName",
    "ChartSpec",
    "ChartTitleSpec",
    "Color",
    "DataAxisSpec",
    "Flag",
    "FontName",
    "GridLineSpec",
    "Integer",
    "LabelFrameSpec",
    "LegendFrameSpec",
    "LegendLayoutSpec",
    "LegendMarkerSpec",
    "LegendSpec",
    "LegendTextSpec",
    "LegendTitleSpec",
    "LineAreaSpec",
    "LineCategoryLabelSpec",
    "LineLabelSpec",
    "LineMarkerSpec",
    "LineStandardLabelSpec",
    "LineStrokeSpec",
    "LineStyle",
    "LinesSpec",
    "NamedValueSpec",
    "Number",
    "NumericSpec",
    "Position",
    "SpineSideSpec",
    "TickMajorSpec",
    "TickMarkerSpec",
    "TickMinorSpec",
    "TickTextSpec",
    "Value",
    "build_spec_error",
    "merge_layers",
    "replace_at",
    "resolve_per_item",
    "resolve_per_series",
]


class ChartTitleSpec(BaseSpec):
    """The title written above the chart.

    Examples
    --------
    >>> spec = ChartTitleSpec(text="Top 5 States by Sales", size=16, position="left")
    >>> spec.text, spec.position
    ('Top 5 States by Sales', 'left')
    """

    text: str | None = Field(
        default=None,
        description="The words of the chart title.",
    )
    font: FontName | None = Field(
        default=None,
        description="The font role or family of the chart title.",
    )
    size: Number | None = Field(
        default=None,
        description="The text size of the chart title, in points.",
    )
    color: Color | None = Field(
        default=None,
        description="The text colour of the chart title.",
    )
    position: HorizontalAlignment | None = Field(
        default=None,
        description="Whether the chart title sits on the left, centre or right.",
    )
    x_offset: Number | None = Field(
        default=None,
        description="The horizontal shift of the chart title, in points.",
    )
    y_offset: Number | None = Field(
        default=None,
        description="The vertical shift of the chart title, in points.",
    )


class ChartSpec(BaseSpec):
    """A chart's whole configuration: the root of the spec tree.

    A bare ``ChartSpec()`` sets nothing: every leaf is None, and every child
    node exists, so any path can be read without None checks.

    Examples
    --------
    >>> spec = ChartSpec(
    ...     axis=AxisSpec(spine=AxisSpineSpec(top=SpineSideSpec(show=False))),
    ...     bars=BarsSpec(fill=BarFillSpec(color="#4C72B0")),
    ... )
    >>> spec.axis.spine.top.show
    False
    >>> spec.bars.fill.color
    '#4C72B0'
    >>> ChartSpec().lines.stroke.width is None
    True
    """

    axis: AxisSpec = Field(
        default_factory=AxisSpec,
        description="The axes and spines.",
    )
    legend: LegendSpec = Field(
        default_factory=LegendSpec,
        description="The legend.",
    )
    title: ChartTitleSpec = Field(
        default_factory=ChartTitleSpec,
        description="The chart title.",
    )
    bars: BarsSpec = Field(
        default_factory=BarsSpec,
        description="Styling for bar charts only.",
    )
    lines: LinesSpec = Field(
        default_factory=LinesSpec,
        description="Styling for line charts only.",
    )
