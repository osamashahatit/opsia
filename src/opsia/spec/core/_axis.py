"""Specs for the axis branch: ticks, grid, title, scale, margin and spines."""

from typing import Literal

from pydantic import Field

from opsia.spec.core._types import (
    BaseSpec,
    CapStyle,
    Color,
    FillStyle,
    Flag,
    FontName,
    HorizontalAlignment,
    Integer,
    LineStyle,
    Number,
    NumericSpec,
    VerticalAlignment,
)


class TickTextSpec(BaseSpec):
    """The text of the major or minor tick labels on one axis.

    Examples
    --------
    >>> spec = TickTextSpec(size=10, truncate=12, custom_text=("North", "South"))
    >>> spec.size, spec.truncate, spec.custom_text
    (10.0, 12, ('North', 'South'))
    >>> TickTextSpec().numeric.decimals is None
    True
    """

    show: Flag | None = Field(
        default=None,
        description="Whether the tick labels are drawn.",
    )
    font: FontName | None = Field(
        default=None,
        description="The font role or family of the tick labels.",
    )
    size: Number | None = Field(
        default=None,
        description="The text size of the tick labels, in points.",
    )
    color: Color | None = Field(
        default=None,
        description="The text colour of the tick labels.",
    )
    rotation: Number | None = Field(
        default=None,
        description="The rotation of the tick labels, in degrees.",
    )
    offset: Number | None = Field(
        default=None,
        description="The distance between the tick labels and the axis, in points.",
    )
    horizontal_alignment: HorizontalAlignment | None = Field(
        default=None,
        description="How each tick label is aligned horizontally on its anchor.",
    )
    vertical_alignment: VerticalAlignment | None = Field(
        default=None,
        description="How each tick label is aligned vertically on its anchor.",
    )
    truncate: Integer | Literal["none"] | None = Field(
        default=None,
        description='The most characters a tick label keeps; "none" keeps them all.',
    )
    custom_text: tuple[str, ...] | Literal["none"] | None = Field(
        default=None,
        description='The words that replace the tick labels, in order; "none" keeps '
        "the computed labels.",
    )
    numeric: NumericSpec = Field(
        default_factory=NumericSpec,
        description="How numbers in the tick labels are written.",
    )


class TickMarkerSpec(BaseSpec):
    """The small mark drawn at each major or minor tick on one axis.

    Examples
    --------
    >>> spec = TickMarkerSpec(shape="line_left", size=4, border_width=0.8)
    >>> spec.shape, spec.size, spec.border_width
    ('line_left', 4.0, 0.8)
    """

    show: Flag | None = Field(
        default=None,
        description="Whether the tick marks are drawn; hiding minor marks also hides "
        "the minor grid.",
    )
    shape: str | None = Field(
        default=None,
        description="The Matplotlib marker name of the tick mark, or an Opsia name "
        'such as "line_left".',
    )
    face_color: Color | None = Field(
        default=None,
        description="The fill colour of the tick mark.",
    )
    border_color: Color | None = Field(
        default=None,
        description="The outline colour of the tick mark.",
    )
    border_width: Number | None = Field(
        default=None,
        description="The outline width of the tick mark, in points.",
    )
    size: Number | None = Field(
        default=None,
        description="The size of the tick mark, in points.",
    )
    fill_style: FillStyle | None = Field(
        default=None,
        description="How much of the tick mark is filled.",
    )
    cap_style: CapStyle | None = Field(
        default=None,
        description="How the ends of the tick mark are drawn.",
    )
    x_offset: Number | None = Field(
        default=None,
        description="The horizontal shift of the tick mark, in points.",
    )
    y_offset: Number | None = Field(
        default=None,
        description="The vertical shift of the tick mark, in points.",
    )
    rotation: Number | None = Field(
        default=None,
        description="The rotation of the tick mark, in degrees.",
    )


class TickLevelSpec(BaseSpec):
    """One level of ticks on one axis, major or minor: its text and its mark.

    Examples
    --------
    >>> spec = TickLevelSpec(text=TickTextSpec(size=9))
    >>> spec.text.size
    9.0
    >>> spec.marker.show is None
    True
    """

    text: TickTextSpec = Field(
        default_factory=TickTextSpec,
        description="The tick labels at this level.",
    )
    marker: TickMarkerSpec = Field(
        default_factory=TickMarkerSpec,
        description="The tick marks at this level.",
    )


class AxisTickSpec(BaseSpec):
    """The major and minor ticks of one axis.

    Examples
    --------
    >>> spec = AxisTickSpec(minor=TickLevelSpec(marker=TickMarkerSpec(show=False)))
    >>> spec.minor.marker.show
    False
    """

    major: TickLevelSpec = Field(
        default_factory=TickLevelSpec,
        description="The major ticks.",
    )
    minor: TickLevelSpec = Field(
        default_factory=TickLevelSpec,
        description="The minor ticks.",
    )


class GridLineSpec(BaseSpec):
    """The major or minor grid lines that extend one axis's ticks.

    Examples
    --------
    >>> spec = GridLineSpec(show=True, color="#E8E8E8", width=0.8)
    >>> spec.show, spec.color, spec.width
    (True, '#E8E8E8', 0.8)
    """

    show: Flag | None = Field(
        default=None,
        description="Whether the grid lines are drawn.",
    )
    color: Color | None = Field(
        default=None,
        description="The colour of the grid lines.",
    )
    width: Number | None = Field(
        default=None,
        description="The width of the grid lines, in points.",
    )
    style: LineStyle | None = Field(
        default=None,
        description="The dash style of the grid lines.",
    )
    alpha: Number | None = Field(
        default=None,
        description="The opacity of the grid lines, from 0 to 1.",
    )


class AxisGridSpec(BaseSpec):
    """The major and minor grid lines of one axis.

    Examples
    --------
    >>> spec = AxisGridSpec(major=GridLineSpec(show=True))
    >>> spec.major.show, spec.minor.show
    (True, None)
    """

    major: GridLineSpec = Field(
        default_factory=GridLineSpec,
        description="The grid lines at major ticks.",
    )
    minor: GridLineSpec = Field(
        default_factory=GridLineSpec,
        description="The grid lines at minor ticks.",
    )


class AxisTitleSpec(BaseSpec):
    """The title written beside one axis.

    Examples
    --------
    >>> spec = AxisTitleSpec(text="Sales", size=11)
    >>> spec.text, spec.size
    ('Sales', 11.0)
    """

    text: str | None = Field(
        default=None,
        description="The words of the axis title.",
    )
    font: FontName | None = Field(
        default=None,
        description="The font role or family of the axis title.",
    )
    size: Number | None = Field(
        default=None,
        description="The text size of the axis title, in points.",
    )
    color: Color | None = Field(
        default=None,
        description="The text colour of the axis title.",
    )
    rotation: Number | None = Field(
        default=None,
        description="The rotation of the axis title, in degrees.",
    )
    offset: Number | None = Field(
        default=None,
        description="The distance between the axis title and the tick labels, in "
        "points.",
    )


class AxisScaleSpec(BaseSpec):
    """The range of one axis and the spacing of its ticks (§4.15).

    ``step`` and ``minor_divisions`` apply to numeric axes only.

    Examples
    --------
    >>> spec = AxisScaleSpec(min_value=0, max_value=5000, step=500)
    >>> spec.min_value, spec.max_value, spec.step
    (0.0, 5000.0, 500.0)
    """

    min_value: Number | None = Field(
        default=None,
        description="Where the axis starts, in data units.",
    )
    max_value: Number | None = Field(
        default=None,
        description="Where the axis ends, in data units.",
    )
    step: Number | None = Field(
        default=None,
        description="The distance between major ticks, in data units; numeric axes "
        "only.",
    )
    minor_divisions: Integer | None = Field(
        default=None,
        description="The number of minor intervals between two major ticks; numeric "
        "axes only.",
    )


class AxisMarginSpec(BaseSpec):
    """The empty space added before and after the data along one axis.

    Examples
    --------
    >>> spec = AxisMarginSpec(lower=0.0, upper=0.05)
    >>> spec.lower, spec.upper
    (0.0, 0.05)
    """

    lower: Number | None = Field(
        default=None,
        description="The space before the lowest value, as a fraction of the data "
        "range.",
    )
    upper: Number | None = Field(
        default=None,
        description="The space after the highest value, as a fraction of the data "
        "range.",
    )


class DataAxisSpec(BaseSpec):
    """One data axis: ``axis.x`` or ``axis.y``, which follow the data column.

    ``axis.x`` is always the axis of the ``x_axis=`` column and ``axis.y`` the
    axis of the ``y_axis=`` column, whatever the orientation. On a chart made
    with ``horizontal=True``, ``axis.x`` is drawn on the left of the screen and
    ``axis.y`` along the bottom (§4.11).

    Examples
    --------
    >>> spec = DataAxisSpec(scale=AxisScaleSpec(min_value=0))
    >>> spec.scale.min_value
    0.0
    >>> spec.grid.major.show is None
    True
    """

    tick: AxisTickSpec = Field(
        default_factory=AxisTickSpec,
        description="The major and minor ticks.",
    )
    grid: AxisGridSpec = Field(
        default_factory=AxisGridSpec,
        description="The major and minor grid lines.",
    )
    title: AxisTitleSpec = Field(
        default_factory=AxisTitleSpec,
        description="The axis title.",
    )
    scale: AxisScaleSpec = Field(
        default_factory=AxisScaleSpec,
        description="The range and tick spacing.",
    )
    margin: AxisMarginSpec = Field(
        default_factory=AxisMarginSpec,
        description="The space around the data.",
    )


class SpineSideSpec(BaseSpec):
    """The spine on one side of the plot: top, bottom, left or right.

    Examples
    --------
    >>> spec = SpineSideSpec(show=False)
    >>> spec.show
    False
    """

    show: Flag | None = Field(
        default=None,
        description="Whether this spine is drawn.",
    )
    color: Color | None = Field(
        default=None,
        description="The colour of this spine.",
    )
    width: Number | None = Field(
        default=None,
        description="The width of this spine, in points.",
    )
    style: LineStyle | None = Field(
        default=None,
        description="The dash style of this spine.",
    )
    position: Number | None = Field(
        default=None,
        description="Where this spine sits across the plot, as a fraction from 0 to 1.",
    )


class AxisSpineSpec(BaseSpec):
    """The four spines, stored by screen side (§4.12).

    Spines follow the screen, unlike ``axis.x`` and ``axis.y``. The recorder
    argument ``select=`` writes to several sides at once and is never stored.

    Examples
    --------
    >>> spec = AxisSpineSpec(top=SpineSideSpec(show=False))
    >>> spec.top.show, spec.left.show
    (False, None)
    """

    top: SpineSideSpec = Field(
        default_factory=SpineSideSpec,
        description="The spine along the top.",
    )
    bottom: SpineSideSpec = Field(
        default_factory=SpineSideSpec,
        description="The spine along the bottom.",
    )
    left: SpineSideSpec = Field(
        default_factory=SpineSideSpec,
        description="The spine on the left.",
    )
    right: SpineSideSpec = Field(
        default_factory=SpineSideSpec,
        description="The spine on the right.",
    )


class AxisSpec(BaseSpec):
    """The axis branch: the two data axes and the four spines.

    ``x`` is always the axis of the ``x_axis=`` column and ``y`` the axis of
    the ``y_axis=`` column; ``horizontal=True`` moves them on screen but does
    not swap their names (§4.11). Spines are the exception: they are stored by
    screen side.

    Examples
    --------
    >>> spec = AxisSpec(y=DataAxisSpec(title=AxisTitleSpec(text="Sales")))
    >>> spec.y.title.text
    'Sales'
    >>> spec.spine.top.show is None
    True
    """

    x: DataAxisSpec = Field(
        default_factory=DataAxisSpec,
        description="The axis of the x_axis= column.",
    )
    y: DataAxisSpec = Field(
        default_factory=DataAxisSpec,
        description="The axis of the y_axis= column.",
    )
    spine: AxisSpineSpec = Field(
        default_factory=AxisSpineSpec,
        description="The four spines, by screen side.",
    )
