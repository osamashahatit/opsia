"""Shared type aliases, the base of every spec, and the number-format spec.

Every alias here names a closed set of words or a kind of value that more
than one spec node uses. The ``Literal`` members of the Matplotlib-backed
aliases were copied from Matplotlib 3.11.2 (``matplotlib/typing.py``,
``matplotlib/text.pyi``, ``matplotlib/offsetbox.py``) and must be checked
again when the pinned Matplotlib version changes.

``Number``, ``Integer`` and ``Flag`` are strict: they reject ``"1"`` and
``True`` where a number is expected, instead of converting them silently
(§9.3.1). Strictness is set per type, not model-wide, so a YAML list still
becomes a tuple.

``Items`` is every list in the spec: one or more values, stored as a tuple.
An empty list is rejected when the spec is built, not later when a chart is
drawn (§9.6 rule 4).

``NamedValueSpec`` is the fourth form of ``Value``: a dict laid over a
scalar or a list (§4.8). Only ``merge_layers`` and ``replace_at`` build one;
validation accepts an existing instance and never builds one from a dict.

This module imports nothing from Matplotlib.
"""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    PlainValidator,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    Strict,
    WrapSerializer,
)
from pydantic.fields import FieldInfo
from pydantic.json_schema import SkipJsonSchema


def _as_dict(
    value: Mapping[str, object], handler: SerializerFunctionWrapHandler
) -> object:
    """Serialize a read-only mapping as a plain dict.

    Pydantic's serializer expects a ``dict`` and warns on a
    ``MappingProxyType``. Handing it a dict copy keeps ``model_dump()`` and
    ``model_dump_json()`` silent, and lets the inner value types still decide
    how each value is written.

    Parameters
    ----------
    value
        The stored read-only mapping.
    handler
        Pydantic's serializer for the declared mapping type.

    Returns
    -------
        The serialized form of a plain dict with the same items.

    Examples
    --------
    >>> from pydantic import BaseModel
    >>> class ExampleSpec(BaseModel):
    ...     by_name: ByName[str]
    >>> ExampleSpec(by_name={"2019": "#E24A33"}).model_dump()
    {'by_name': {'2019': '#E24A33'}}
    """
    return handler(dict(value))


def _keep_named(value: object) -> object:
    """Accept an existing NamedValueSpec as it is; reject everything else.

    This is the whole validation of the fourth form of ``Value``. A dict is
    rejected here, so it can only become the by-name form, even when its
    keys are ``names`` and ``rest`` (§4.8).

    The value is returned through ``kept``, whose declared type stays
    ``object``: the ``isinstance`` check would otherwise narrow it to a
    ``NamedValueSpec`` of unknown item type, which strict pyright rejects.

    Examples
    --------
    >>> named = NamedValueSpec(names={"2019": "#E24A33"}, rest="#CCCCCC")
    >>> _keep_named(named) is named
    True
    >>> _keep_named({"names": {}, "rest": "#CCCCCC"})
    Traceback (most recent call last):
    ...
    ValueError: Only Opsia builds a NamedValueSpec; this value is not one.
    """
    kept: object = value
    if isinstance(value, NamedValueSpec):
        return kept
    raise ValueError("Only Opsia builds a NamedValueSpec; this value is not one.")


def _dump_value(
    value: object, handler: SerializerFunctionWrapHandler, info: SerializationInfo
) -> object:
    """Serialize a value-mapped setting, writing a NamedValueSpec as a dict.

    The other three forms go to Pydantic's own serializer. A NamedValueSpec
    is written as ``{"names": ..., "rest": ...}``; read back, that becomes a
    plain by-name dict, not a NamedValueSpec.

    Examples
    --------
    >>> from opsia.spec import BarFillSpec
    >>> named = NamedValueSpec(names={"2019": "#E24A33"}, rest="#CCCCCC")
    >>> BarFillSpec(color=named).model_dump()["color"]
    {'names': {'2019': '#E24A33'}, 'rest': '#CCCCCC'}
    """
    if isinstance(value, NamedValueSpec):
        return value.model_dump(mode=info.mode)
    return handler(value)


type Number = Annotated[float, Strict()]
"""A real number. Whole numbers are accepted and stored as floats.

Strict: the text ``"1"`` and the booleans ``True`` and ``False`` are
rejected rather than converted (§9.3.1).
"""

type Integer = Annotated[int, Strict()]
"""A whole number. Strict: ``"1"``, ``1.0`` and ``True`` are rejected."""

type Flag = Annotated[bool, Strict()]
"""A true or false setting. Strict: ``1`` and ``"true"`` are rejected."""

type Items[T] = Annotated[tuple[T, ...], Field(min_length=1)]
"""A list of one or more values, stored as a tuple.

A list passed in is stored as a tuple, so a frozen spec holds no list
(§3.5.2). An empty list is rejected: it would give no series and no tick a
value, and the mistake would otherwise surface only when a chart is drawn.
"""

type ByName[T] = Annotated[
    Mapping[str, T], AfterValidator(MappingProxyType), WrapSerializer(_as_dict)
]
"""A mapping from a series or category name to a value, stored read-only.

A dict passed in is validated into a new dict and wrapped in a
``MappingProxyType``, so a frozen spec cannot be changed through a mapping it
holds, and later changes to the caller's dict do not reach it (§3.5.2). It
is written out as a plain dict by ``model_dump()``.
"""

type Value[T] = Annotated[
    T
    | Items[T]
    | ByName[T]
    | SkipJsonSchema[Annotated[NamedValueSpec[T], PlainValidator(_keep_named)]],
    WrapSerializer(_dump_value),
]
"""A value-mapped setting: one value, one per series in order, or by name (§4.8).

A scalar applies to every artist. A tuple is assigned to series in order and
wraps when shorter; a list passed in is stored as a tuple, and must hold at
least one value. A mapping is looked up by series name when a legend column
is set, and by category name otherwise; it is stored read-only.

The fourth form, ``NamedValueSpec``, is a mapping laid over a scalar or a
tuple. Only an existing instance is accepted, it is left out of the JSON
Schema, and ``model_dump()`` writes it as a dict.
"""

type Color = str
"""Any Matplotlib colour string, such as ``"#4C72B0"`` or ``"tab:blue"``.

``"none"`` means no colour. Colours are strings only: an RGB tuple would be
confused with the per-series tuple form of ``Value``.
"""

type FontName = str
"""A font role registered by a theme, or an installed font family (§5.7)."""

type LineStyle = Literal["solid", "dashed", "dashdot", "dotted", "none"]
"""A line dash style, by name.

The named forms of Matplotlib's ``LineStyleType`` (``matplotlib/typing.py``).
Its symbol forms (``"-"``, ``"--"``) and dash tuples are not accepted.
"""

type Position = Literal[
    "best",
    "upper right",
    "upper left",
    "lower left",
    "lower right",
    "right",
    "center left",
    "center right",
    "lower center",
    "upper center",
    "center",
]
"""A legend location name.

The Axes legend names of Matplotlib's ``LegendLocType``
(``matplotlib/typing.py``; ``Legend.codes`` in ``matplotlib/legend.py``).
The figure-only ``"outside ..."`` names are not accepted.
"""

type HorizontalAlignment = Literal["left", "center", "right"]
"""Horizontal text alignment, as in Matplotlib's ``Text`` (``text.pyi``)."""

type VerticalAlignment = Literal[
    "bottom", "baseline", "center", "center_baseline", "top"
]
"""Vertical text alignment, as in Matplotlib's ``Text`` (``text.pyi``)."""

type FillStyle = Literal["full", "left", "right", "bottom", "top", "none"]
"""How much of a marker is filled; Matplotlib's ``FillStyleType``."""

type CapStyle = Literal["butt", "round", "projecting"]
"""How the end of a stroke is drawn; the names in Matplotlib's ``CapStyleType``."""

type DisplayUnits = Literal["none", "auto", "k", "m", "b", "t"]
"""The thousands suffix for numbers. ``"none"`` shows the full number."""

type Orientation = Literal["horizontal", "vertical"]
"""The direction in which legend entries run."""

type BarLabelHorizontalAlignment = Literal["left", "center", "right", "outside"]
"""Where a bar's own label sits across the bar. An Opsia set, not Matplotlib's."""

type BarLabelVerticalAlignment = Literal["top", "center", "bottom", "outside"]
"""Where a bar's own label sits along the bar. An Opsia set, not Matplotlib's."""

type CategoryLabelVerticalAlignment = Literal["top", "center", "bottom"]
"""Where a category total sits beside a horizontal bar."""

type FrameTextVerticalAlignment = Literal["top", "center", "bottom", "center_baseline"]
"""Where label text sits vertically inside its frame."""


def is_value_mapped(info: FieldInfo) -> bool:
    """Say whether a field is one of the 19 value-mapped properties (§4.8).

    A value-mapped field carries ``json_schema_extra={"value_mapped": True}``.
    Only these fields are layered by name when one layer is laid over
    another; every other field is replaced whole.

    Parameters
    ----------
    info
        The field's entry in a spec class's ``model_fields``.

    Returns
    -------
        True when the field is marked value-mapped.

    Examples
    --------
    >>> from opsia.spec import BarCategoryLabelSpec, BarFillSpec
    >>> is_value_mapped(BarFillSpec.model_fields["color"])
    True
    >>> is_value_mapped(BarCategoryLabelSpec.model_fields["custom_values"])
    False
    """
    extra = info.json_schema_extra
    if extra is None or callable(extra):
        return False
    return extra.get("value_mapped") is True


class BaseSpec(BaseModel):
    """The base of every Spec: frozen, and closed to unknown keys.

    Private by module rather than by name: it lives in the private ``_types``
    module and is not exported from ``opsia.spec``. A leading underscore would
    make strict pyright reject every spec module that inherits from it.

    ``frozen=True`` makes assignment to a field raise, so a spec is changed
    only by building a new one (§3.5.2). ``extra="forbid"`` rejects a key the
    spec does not define, such as ``colour`` for ``color`` in a theme file.

    Leaves are declared as ``Field(default=None, description=...)``, where
    None means not set (§5.4). The keyword form matters: mypy and pyright do
    not read a positional ``Field(None, ...)`` as a default.

    Examples
    --------
    >>> class ExampleSpec(BaseSpec):
    ...     size: Number | None = Field(
    ...         default=None,
    ...         description="The text size, in points.",
    ...     )
    >>> ExampleSpec(size=10).size
    10.0
    >>> ExampleSpec().size is None
    True
    >>> ExampleSpec.model_config["frozen"], ExampleSpec.model_config["extra"]
    (True, 'forbid')
    """

    model_config = ConfigDict(frozen=True, extra="forbid")


class NamedValueSpec[T](BaseSpec):
    """A by-name mapping laid over a scalar or a list (§4.8).

    The resolver looks a series or category name up in ``names`` first and
    falls back to ``rest``. Built only by ``merge_layers`` and
    ``replace_at``, when a dict is laid over a scalar or a list; a dict from
    code or a theme file never becomes one. A dict laid over a dict gives a
    plain dict, so ``rest`` is never None.

    It is a value, not a node of the spec tree: it is stored in a
    value-mapped setting such as ``bars.fill.color``.

    Examples
    --------
    >>> named = NamedValueSpec(
    ...     names={"2019": "#E24A33"}, rest=("#4C72B0", "#DD8452")
    ... )
    >>> named.names["2019"], named.rest
    ('#E24A33', ('#4C72B0', '#DD8452'))
    """

    names: ByName[T] = Field(
        description="The values given by series or category name.",
    )
    rest: T | Items[T] = Field(
        description="The value or per-series values for every other name.",
    )


class NumericSpec(BaseSpec):
    """How numbers are written, on tick text and on every data label.

    Every field is None until a theme or a ``.numeric()`` call sets it.
    ``as_percent`` cannot be combined with ``currency`` or ``display_units``;
    that check belongs to the recorder, not to this class.

    Examples
    --------
    >>> spec = NumericSpec(display_units="k", currency="$", decimals=0)
    >>> spec.display_units, spec.currency, spec.decimals
    ('k', '$', 0)
    >>> NumericSpec().separator is None
    True
    """

    display_units: DisplayUnits | None = Field(
        default=None,
        description='The suffix for large numbers; "none" shows the full number '
        'and "auto" picks one.',
    )
    as_percent: Flag | None = Field(
        default=None,
        description="Whether to multiply by 100 and append a percent sign.",
    )
    decimals: Integer | None = Field(
        default=None,
        description="The number of digits after the decimal point.",
    )
    separator: Flag | None = Field(
        default=None,
        description="Whether to group thousands with a separator.",
    )
    currency: str | Literal["none"] | None = Field(
        default=None,
        description='The currency symbol put before the number, such as "$"; '
        '"none" for no symbol.',
    )
    infinity: str | None = Field(
        default=None,
        description="The text shown in place of positive infinity.",
    )
    negative_infinity: str | None = Field(
        default=None,
        description="The text shown in place of negative infinity.",
    )
    missing: str | None = Field(
        default=None,
        description="The text shown in place of a missing value.",
    )
