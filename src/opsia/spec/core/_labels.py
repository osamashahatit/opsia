"""Specs for data labels: the shared frame and the bar and line label branches.

Each chart type has two label branches (§4.6): ``standard``, one label per
bar or point, and ``category``, one total per category. Whether a label sits
in a box is not a third branch; it is the ``frame`` child on every branch.
"""

from typing import Literal

from pydantic import Field

from opsia.spec.core._types import (
    BarLabelHorizontalAlignment,
    BarLabelVerticalAlignment,
    BaseSpec,
    ByName,
    CategoryLabelVerticalAlignment,
    Color,
    Flag,
    FontName,
    FrameTextVerticalAlignment,
    HorizontalAlignment,
    Integer,
    LineStyle,
    Number,
    NumericSpec,
)


class LabelFrameSpec(BaseSpec):
    """The box drawn behind a data label, shared by all four label branches.

    Examples
    --------
    >>> spec = LabelFrameSpec(show=True, face_color="#FFFFFF", width="auto")
    >>> spec.show, spec.face_color, spec.width
    (True, '#FFFFFF', 'auto')
    """

    show: Flag | None = Field(
        default=None,
        description="Whether each label is drawn inside a box.",
    )
    face_color: Color | None = Field(
        default=None,
        description="The fill colour of the label box.",
    )
    face_alpha: Number | None = Field(
        default=None,
        description="The opacity of the label box fill, from 0 to 1.",
    )
    border_color: Color | None = Field(
        default=None,
        description="The outline colour of the label box.",
    )
    border_alpha: Number | None = Field(
        default=None,
        description="The opacity of the label box outline, from 0 to 1.",
    )
    border_style: LineStyle | None = Field(
        default=None,
        description="The dash style of the label box outline.",
    )
    border_width: Number | None = Field(
        default=None,
        description="The outline width of the label box, in points.",
    )
    border_radius: Number | None = Field(
        default=None,
        description="The corner radius of the label box, in points.",
    )
    width: Number | Literal["auto"] | None = Field(
        default=None,
        description='The width of the label box, in points; "auto" fits it to the '
        "text.",
    )
    height: Number | Literal["auto"] | None = Field(
        default=None,
        description='The height of the label box, in points; "auto" fits it to the '
        "text.",
    )
    padding_left: Number | None = Field(
        default=None,
        description="The space between the text and the left edge of the box, in "
        "points.",
    )
    padding_right: Number | None = Field(
        default=None,
        description="The space between the text and the right edge of the box, in "
        "points.",
    )
    padding_top: Number | None = Field(
        default=None,
        description="The space between the text and the top edge of the box, in "
        "points.",
    )
    padding_bottom: Number | None = Field(
        default=None,
        description="The space between the text and the bottom edge of the box, in "
        "points.",
    )
    text_horizontal_alignment: HorizontalAlignment | None = Field(
        default=None,
        description="How the text is aligned horizontally inside the box.",
    )
    text_vertical_alignment: FrameTextVerticalAlignment | None = Field(
        default=None,
        description="How the text is aligned vertically inside the box.",
    )


class BarStandardLabelSpec(BaseSpec):
    """One label on each bar, showing that bar's value.

    Which alignment values are valid depends on the chart's orientation; the
    recorder checks that at ``.set()``.

    Examples
    --------
    >>> spec = BarStandardLabelSpec(show=True, vertical_alignment="outside")
    >>> spec.show, spec.vertical_alignment
    (True, 'outside')
    >>> spec.frame.show is None
    True
    """

    show: Flag | None = Field(
        default=None,
        description="Whether each bar gets a value label.",
    )
    font: FontName | None = Field(
        default=None,
        description="The font role or family of the bar labels.",
    )
    size: Number | None = Field(
        default=None,
        description="The text size of the bar labels, in points.",
    )
    color: Color | None = Field(
        default=None,
        description="The text colour of the bar labels.",
    )
    horizontal_alignment: BarLabelHorizontalAlignment | None = Field(
        default=None,
        description='Where each label sits across its bar; "outside" puts it past the '
        "bar end.",
    )
    vertical_alignment: BarLabelVerticalAlignment | None = Field(
        default=None,
        description='Where each label sits along its bar; "outside" puts it past the '
        "bar end.",
    )
    x_offset: Number | None = Field(
        default=None,
        description="The horizontal shift of each bar label, in points.",
    )
    y_offset: Number | None = Field(
        default=None,
        description="The vertical shift of each bar label, in points.",
    )
    hide_smallest: Integer | None = Field(
        default=None,
        description="The number of smallest bars whose labels are hidden.",
    )
    numeric: NumericSpec = Field(
        default_factory=NumericSpec,
        description="How the bar values are written.",
    )
    frame: LabelFrameSpec = Field(
        default_factory=LabelFrameSpec,
        description="The box behind each bar label.",
    )


class BarCategoryLabelSpec(BaseSpec):
    """One label per category, showing the total of its bars.

    ``horizontal_alignment`` applies to vertical bars and
    ``vertical_alignment`` to horizontal bars.

    Examples
    --------
    >>> spec = BarCategoryLabelSpec(show=True, custom_values={"Texas": 0.15})
    >>> spec.custom_values["Texas"]
    0.15
    """

    show: Flag | None = Field(
        default=None,
        description="Whether each category gets a total label.",
    )
    font: FontName | None = Field(
        default=None,
        description="The font role or family of the category totals.",
    )
    size: Number | None = Field(
        default=None,
        description="The text size of the category totals, in points.",
    )
    color: Color | None = Field(
        default=None,
        description="The text colour of the category totals.",
    )
    horizontal_alignment: HorizontalAlignment | None = Field(
        default=None,
        description="How each total is aligned horizontally; vertical bars only.",
    )
    vertical_alignment: CategoryLabelVerticalAlignment | None = Field(
        default=None,
        description="How each total is aligned vertically; horizontal bars only.",
    )
    x_offset: Number | None = Field(
        default=None,
        description="The horizontal shift of each category total, in points.",
    )
    y_offset: Number | None = Field(
        default=None,
        description="The vertical shift of each category total, in points.",
    )
    custom_values: ByName[Number] | Literal["none"] | None = Field(
        default=None,
        description="The numbers shown instead of the computed totals, by category "
        'name; "none" shows the computed totals.',
    )
    numeric: NumericSpec = Field(
        default_factory=NumericSpec,
        description="How the totals are written.",
    )
    frame: LabelFrameSpec = Field(
        default_factory=LabelFrameSpec,
        description="The box behind each category total.",
    )


class BarLabelSpec(BaseSpec):
    """The two kinds of data label on a bar chart.

    Examples
    --------
    >>> spec = BarLabelSpec(standard=BarStandardLabelSpec(show=True))
    >>> spec.standard.show, spec.category.show
    (True, None)
    """

    standard: BarStandardLabelSpec = Field(
        default_factory=BarStandardLabelSpec,
        description="One value label per bar.",
    )
    category: BarCategoryLabelSpec = Field(
        default_factory=BarCategoryLabelSpec,
        description="One total label per category.",
    )


class LineStandardLabelSpec(BaseSpec):
    """One label at each point of a line, showing that point's value.

    Examples
    --------
    >>> spec = LineStandardLabelSpec(show=True, series=("2019", "2020"))
    >>> spec.series
    ('2019', '2020')
    >>> LineStandardLabelSpec(series="all").series
    'all'
    """

    show: Flag | None = Field(
        default=None,
        description="Whether each point gets a value label.",
    )
    font: FontName | None = Field(
        default=None,
        description="The font role or family of the point labels.",
    )
    size: Number | None = Field(
        default=None,
        description="The text size of the point labels, in points.",
    )
    color: Color | None = Field(
        default=None,
        description="The text colour of the point labels.",
    )
    x_offset: Number | None = Field(
        default=None,
        description="The horizontal shift of each point label, in points.",
    )
    y_offset: Number | None = Field(
        default=None,
        description="The vertical shift of each point label, in points.",
    )
    series: Literal["all"] | tuple[str, ...] | None = Field(
        default=None,
        description='The names of the lines that get labels; "all" labels every line.',
    )
    numeric: NumericSpec = Field(
        default_factory=NumericSpec,
        description="How the point values are written.",
    )
    frame: LabelFrameSpec = Field(
        default_factory=LabelFrameSpec,
        description="The box behind each point label.",
    )


class LineCategoryLabelSpec(BaseSpec):
    """One label per category, showing the total across all lines.

    Examples
    --------
    >>> spec = LineCategoryLabelSpec(show=True, custom_values="none")
    >>> spec.show, spec.custom_values
    (True, 'none')
    """

    show: Flag | None = Field(
        default=None,
        description="Whether each category gets a total label.",
    )
    font: FontName | None = Field(
        default=None,
        description="The font role or family of the category totals.",
    )
    size: Number | None = Field(
        default=None,
        description="The text size of the category totals, in points.",
    )
    color: Color | None = Field(
        default=None,
        description="The text colour of the category totals.",
    )
    x_offset: Number | None = Field(
        default=None,
        description="The horizontal shift of each category total, in points.",
    )
    y_offset: Number | None = Field(
        default=None,
        description="The vertical shift of each category total, in points.",
    )
    custom_values: ByName[Number] | Literal["none"] | None = Field(
        default=None,
        description="The numbers shown instead of the computed totals, by category "
        'name; "none" shows the computed totals.',
    )
    numeric: NumericSpec = Field(
        default_factory=NumericSpec,
        description="How the totals are written.",
    )
    frame: LabelFrameSpec = Field(
        default_factory=LabelFrameSpec,
        description="The box behind each category total.",
    )


class LineLabelSpec(BaseSpec):
    """The two kinds of data label on a line chart.

    Examples
    --------
    >>> spec = LineLabelSpec(category=LineCategoryLabelSpec(show=True))
    >>> spec.category.show, spec.standard.show
    (True, None)
    """

    standard: LineStandardLabelSpec = Field(
        default_factory=LineStandardLabelSpec,
        description="One value label per point.",
    )
    category: LineCategoryLabelSpec = Field(
        default_factory=LineCategoryLabelSpec,
        description="One total label per category.",
    )
