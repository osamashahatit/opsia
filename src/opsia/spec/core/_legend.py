"""Specs for the legend branch: title, text, frame, marker and layout."""

from pydantic import Field

from opsia.spec.core._types import (
    BaseSpec,
    Color,
    Flag,
    FontName,
    HorizontalAlignment,
    LineStyle,
    Number,
    Orientation,
    Position,
)


class LegendTitleSpec(BaseSpec):
    """The heading written above the legend entries.

    Examples
    --------
    >>> spec = LegendTitleSpec(text="Year", size=10)
    >>> spec.text, spec.size
    ('Year', 10.0)
    """

    text: str | None = Field(
        default=None,
        description="The words of the legend heading.",
    )
    font: FontName | None = Field(
        default=None,
        description="The font role or family of the legend heading.",
    )
    size: Number | None = Field(
        default=None,
        description="The text size of the legend heading, in points.",
    )
    color: Color | None = Field(
        default=None,
        description="The text colour of the legend heading.",
    )


class LegendTextSpec(BaseSpec):
    """The text of the legend entries.

    Examples
    --------
    >>> spec = LegendTextSpec(font="body", size=10)
    >>> spec.font, spec.size
    ('body', 10.0)
    """

    font: FontName | None = Field(
        default=None,
        description="The font role or family of the legend entries.",
    )
    size: Number | None = Field(
        default=None,
        description="The text size of the legend entries, in points.",
    )
    color: Color | None = Field(
        default=None,
        description="The text colour of the legend entries.",
    )


class LegendFrameSpec(BaseSpec):
    """The box drawn around the legend.

    Examples
    --------
    >>> spec = LegendFrameSpec(show=False)
    >>> spec.show
    False
    """

    show: Flag | None = Field(
        default=None,
        description="Whether the box around the legend is drawn.",
    )
    face_color: Color | None = Field(
        default=None,
        description="The fill colour of the legend box.",
    )
    face_alpha: Number | None = Field(
        default=None,
        description="The opacity of the legend box fill, from 0 to 1.",
    )
    border_color: Color | None = Field(
        default=None,
        description="The outline colour of the legend box.",
    )
    border_alpha: Number | None = Field(
        default=None,
        description="The opacity of the legend box outline, from 0 to 1.",
    )
    border_style: LineStyle | None = Field(
        default=None,
        description="The dash style of the legend box outline.",
    )
    border_width: Number | None = Field(
        default=None,
        description="The outline width of the legend box, in points.",
    )
    border_radius: Number | None = Field(
        default=None,
        description="The corner radius of the legend box, in points.",
    )


class LegendMarkerSpec(BaseSpec):
    """The colour swatches beside the legend entries.

    The swatch colour comes from the series it stands for, so it is not a
    setting here.

    Examples
    --------
    >>> spec = LegendMarkerSpec(shape="s", size=8)
    >>> spec.shape, spec.size
    ('s', 8.0)
    """

    shape: str | None = Field(
        default=None,
        description="The Matplotlib marker name of the swatches.",
    )
    size: Number | None = Field(
        default=None,
        description="The size of the swatches, in points.",
    )


class LegendLayoutSpec(BaseSpec):
    """Where the legend sits and how its entries are arranged.

    Examples
    --------
    >>> spec = LegendLayoutSpec(position="upper right", orientation="horizontal")
    >>> spec.position, spec.orientation
    ('upper right', 'horizontal')
    """

    show: Flag | None = Field(
        default=None,
        description="Whether the legend is drawn.",
    )
    position: Position | None = Field(
        default=None,
        description="The corner or edge the legend is placed at.",
    )
    x_offset: Number | None = Field(
        default=None,
        description="The horizontal shift of the legend from its position, in points.",
    )
    y_offset: Number | None = Field(
        default=None,
        description="The vertical shift of the legend from its position, in points.",
    )
    orientation: Orientation | None = Field(
        default=None,
        description="Whether the legend entries run in a row or a column.",
    )
    marker_first: Flag | None = Field(
        default=None,
        description="Whether each swatch is drawn before its text rather than after "
        "it.",
    )
    entry_spacing: Number | None = Field(
        default=None,
        description="The vertical space between legend entries; unit not yet decided "
        "(§4.13).",
    )
    column_spacing: Number | None = Field(
        default=None,
        description="The horizontal space between legend columns; unit not yet decided "
        "(§4.13).",
    )
    padding: Number | None = Field(
        default=None,
        description="The space between the legend entries and the box, in points.",
    )
    marker_spacing: Number | None = Field(
        default=None,
        description="The space between each swatch and its text; unit not yet decided "
        "(§4.13).",
    )
    horizontal_alignment: HorizontalAlignment | None = Field(
        default=None,
        description="How the legend heading and entries are aligned inside the box.",
    )


class LegendSpec(BaseSpec):
    """The legend branch: heading, entry text, box, swatches and layout.

    Examples
    --------
    >>> spec = LegendSpec(layout=LegendLayoutSpec(show=True))
    >>> spec.layout.show
    True
    >>> spec.frame.show is None
    True
    """

    title: LegendTitleSpec = Field(
        default_factory=LegendTitleSpec,
        description="The legend heading.",
    )
    text: LegendTextSpec = Field(
        default_factory=LegendTextSpec,
        description="The legend entry text.",
    )
    frame: LegendFrameSpec = Field(
        default_factory=LegendFrameSpec,
        description="The box around the legend.",
    )
    marker: LegendMarkerSpec = Field(
        default_factory=LegendMarkerSpec,
        description="The colour swatches.",
    )
    layout: LegendLayoutSpec = Field(
        default_factory=LegendLayoutSpec,
        description="The position and arrangement.",
    )
