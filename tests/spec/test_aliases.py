"""The type aliases read correctly at runtime through ``.__value__``.

A ``type`` statement makes a ``TypeAliasType``, so anything that reads an
alias at runtime (these tests, the future reference generator of §10.3)
must go through ``.__value__``. The expected members are copied from
``claude/opsia-spec-fields.md``; ``Position`` is the one alias the fields
file does not list, so its members come from Matplotlib 3.11.2
(``LegendLocType`` in ``matplotlib/typing.py``, Axes names only).

How the strict and mapping aliases behave on real input is tested in
``test_validation.py``; this file checks only how they are built.
"""

import importlib
import typing
from collections.abc import Mapping
from types import MappingProxyType
from typing import TypeAliasType

import pytest
from pydantic import AfterValidator, PlainValidator, Strict, WrapSerializer
from pydantic.fields import FieldInfo

from opsia.spec import NamedValueSpec

TYPES_MODULE = importlib.import_module("opsia.spec.core._types")

LITERAL_ALIASES: dict[str, tuple[str, ...]] = {
    "LineStyle": ("solid", "dashed", "dashdot", "dotted", "none"),
    "Position": (
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
    ),
    "HorizontalAlignment": ("left", "center", "right"),
    "VerticalAlignment": ("bottom", "baseline", "center", "center_baseline", "top"),
    "FillStyle": ("full", "left", "right", "bottom", "top", "none"),
    "CapStyle": ("butt", "round", "projecting"),
    "DisplayUnits": ("none", "auto", "k", "m", "b", "t"),
    "Orientation": ("horizontal", "vertical"),
    "BarLabelHorizontalAlignment": ("left", "center", "right", "outside"),
    "BarLabelVerticalAlignment": ("top", "center", "bottom", "outside"),
    "CategoryLabelVerticalAlignment": ("top", "center", "bottom"),
    "FrameTextVerticalAlignment": ("top", "center", "bottom", "center_baseline"),
}

STRING_ALIASES = ("Color", "FontName")

STRICT_ALIASES: dict[str, type] = {"Number": float, "Integer": int, "Flag": bool}

GENERIC_ALIASES = ("ByName", "Items", "Value")


def _alias(name: str) -> TypeAliasType:
    """Return the alias of that name from the types module, checking its kind."""
    value = getattr(TYPES_MODULE, name)
    assert isinstance(value, TypeAliasType), (
        f"{name} is a {type(value).__name__}, not a `type` alias."
    )
    return value


def test_every_alias_is_checked() -> None:
    """Each alias in the types module appears in exactly one table here."""
    found = {
        name
        for name, value in vars(TYPES_MODULE).items()
        if isinstance(value, TypeAliasType)
    }
    expected = (
        set(LITERAL_ALIASES)
        | set(STRING_ALIASES)
        | set(STRICT_ALIASES)
        | set(GENERIC_ALIASES)
    )
    assert found == expected, (
        f"Aliases with no test: {sorted(found - expected)}. "
        f"Tested but missing from the module: {sorted(expected - found)}."
    )


@pytest.mark.parametrize("name", sorted(LITERAL_ALIASES))
def test_literal_members_match_the_fields_file(name: str) -> None:
    """Each Literal alias holds exactly the members the fields file lists."""
    value = _alias(name).__value__
    assert typing.get_origin(value) is typing.Literal, (
        f"{name} should be a Literal, got {value!r}."
    )
    members = typing.get_args(value)
    expected = LITERAL_ALIASES[name]
    assert set(members) == set(expected), (
        f"{name} members differ. Extra: {sorted(set(members) - set(expected))}. "
        f"Missing: {sorted(set(expected) - set(members))}."
    )
    assert len(members) == len(expected), f"{name} lists a member twice."


@pytest.mark.parametrize("name", STRING_ALIASES)
def test_string_aliases_are_plain_str(name: str) -> None:
    """Color and FontName are plain strings, so a tuple always means per series."""
    assert _alias(name).__value__ is str


@pytest.mark.parametrize("name", sorted(STRICT_ALIASES))
def test_strict_aliases_are_annotated_strict(name: str) -> None:
    """Number, Integer and Flag are their base type marked Strict, and nothing more."""
    value = _alias(name).__value__
    assert typing.get_origin(value) is typing.Annotated, (
        f"{name} should be Annotated, got {value!r}."
    )
    base, *metadata = typing.get_args(value)
    assert base is STRICT_ALIASES[name], f"{name} wraps {base!r}."
    assert len(metadata) == 1, f"{name} carries {metadata!r}."
    assert isinstance(metadata[0], Strict), f"{name} carries {metadata[0]!r}."
    assert metadata[0].strict is True


def test_by_name_is_a_read_only_mapping() -> None:
    """ByName[T] is Mapping[str, T], wrapped read-only and dumped as a dict."""
    alias = _alias("ByName")
    (param,) = alias.__type_params__
    value = alias.__value__
    assert typing.get_origin(value) is typing.Annotated
    mapping, *metadata = typing.get_args(value)
    assert typing.get_origin(mapping) is Mapping
    assert typing.get_args(mapping) == (str, param)
    validators = [item for item in metadata if isinstance(item, AfterValidator)]
    serializers = [item for item in metadata if isinstance(item, WrapSerializer)]
    assert [validator.func for validator in validators] == [MappingProxyType]
    assert len(serializers) == 1
    assert len(metadata) == 2, f"ByName carries extra metadata: {metadata!r}."


def test_items_is_a_tuple_of_at_least_one() -> None:
    """Items[T] is tuple[T, ...] with a minimum length of one, and nothing more."""
    alias = _alias("Items")
    (param,) = alias.__type_params__
    value = alias.__value__
    assert typing.get_origin(value) is typing.Annotated
    sequence, *metadata = typing.get_args(value)
    assert typing.get_origin(sequence) is tuple
    assert typing.get_args(sequence) == (param, ...)
    assert len(metadata) == 1, f"Items carries {metadata!r}."
    field = metadata[0]
    assert isinstance(field, FieldInfo), f"Items carries {field!r}."
    lengths = [getattr(item, "min_length", None) for item in field.metadata]
    assert lengths == [1], f"Items has the constraints {field.metadata!r}."


def test_value_is_four_forms_under_one_serializer() -> None:
    """Value[T] is T, Items[T], ByName[T] and NamedValueSpec[T] (§4.8).

    The four forms sit under one serializer, which writes a NamedValueSpec
    as a dict. The fourth form is checked by ``_keep_named`` alone, so only
    an existing instance is accepted.
    """
    alias = _alias("Value")
    (param,) = alias.__type_params__
    value = alias.__value__
    assert typing.get_origin(value) is typing.Annotated
    union, *metadata = typing.get_args(value)
    assert len(metadata) == 1, f"Value carries {metadata!r}."
    assert isinstance(metadata[0], WrapSerializer)

    scalar, per_series, by_name, named = typing.get_args(union)
    assert scalar is param
    assert typing.get_origin(per_series) is _alias("Items")
    assert typing.get_args(per_series) == (param,)
    assert typing.get_origin(by_name) is _alias("ByName")
    assert typing.get_args(by_name) == (param,)

    assert typing.get_origin(named) is typing.Annotated
    named_type, *named_metadata = typing.get_args(named)
    assert issubclass(named_type, NamedValueSpec)
    validators = [item for item in named_metadata if isinstance(item, PlainValidator)]
    keep_named = vars(TYPES_MODULE)["_keep_named"]
    assert [validator.func for validator in validators] == [keep_named]
