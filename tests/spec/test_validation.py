"""Validation on the Pydantic specs: what a theme file or a hand-built spec meets.

Most cases go through ``ChartSpec.model_validate`` with the nested dict a
YAML theme file would give, so the tests exercise the same path a theme load
will (§5.1). The strict aliases are tested once each, on their own, and a
walk over the tree checks that every number and flag uses them. The wording
of error messages is tested in ``test_errors.py``.
"""

import json
from collections.abc import Iterator
from types import MappingProxyType
from typing import Annotated, Any, TypeAliasType, get_args, get_origin

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from opsia.spec import (
    BarFillSpec,
    ChartSpec,
    Flag,
    Integer,
    NamedValueSpec,
    Number,
    Value,
)

from .walker import leaves

# The 19 value-mapping properties, copied from claude/opsia-spec-fields.md.
VALUE_MAPPED = {
    "bars.fill.color",
    "bars.fill.alpha",
    "bars.border.color",
    "bars.border.alpha",
    "bars.border.style",
    "bars.border.width",
    "lines.stroke.color",
    "lines.stroke.alpha",
    "lines.stroke.style",
    "lines.stroke.width",
    "lines.area.color",
    "lines.area.alpha",
    "lines.marker.shape",
    "lines.marker.face_color",
    "lines.marker.face_alpha",
    "lines.marker.size",
    "lines.marker.border_color",
    "lines.marker.border_alpha",
    "lines.marker.border_width",
}

STRICT_ALIASES: tuple[TypeAliasType, ...] = (Number, Integer, Flag)
"""The aliases that every number and flag in the spec must use (§9.3.1 rule 4)."""

BARE_TYPES = (float, int, bool)
"""Types that Pydantic would convert silently if used without the aliases."""


def _at(path: str, value: object) -> dict[str, object]:
    """Build the nested dict a theme file would give for one dotted path."""
    keys = path.split(".")
    data: dict[str, object] = {keys[-1]: value}
    for key in reversed(keys[:-1]):
        data = {key: data}
    return data


def _read(spec: BaseModel, path: str) -> object:
    """Read the value at a dotted path."""
    node: object = spec
    for key in path.split("."):
        node = getattr(node, key)
    return node


def _is_read_only_mapping(value: object) -> bool:
    """Say whether a value is stored as a MappingProxyType."""
    return isinstance(value, MappingProxyType)


def _schema_fields(
    schema: dict[str, Any], node: dict[str, Any], prefix: str = ""
) -> Iterator[tuple[str, dict[str, Any], bool]]:
    """Yield (dotted path, property, is a node) for every field in a JSON Schema."""
    definitions: dict[str, Any] = schema["$defs"]
    for name, prop in node["properties"].items():
        path = f"{prefix}{name}"
        ref: str | None = prop.get("$ref")
        target: dict[str, Any] = (
            definitions.get(ref.rsplit("/", 1)[-1], {}) if ref else {}
        )
        if "properties" in target:
            yield path, prop, True
            yield from _schema_fields(schema, target, f"{path}.")
        else:
            yield path, prop, False


def _schema_leaves(schema: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield (dotted path, property) for every leaf in a model's JSON Schema."""
    for path, prop, is_node in _schema_fields(schema, schema):
        if not is_node:
            yield path, prop


def _bare_types(annotation: object) -> list[str]:
    """Name every float, int or bool in an annotation not wrapped in a strict alias."""
    if any(annotation is alias for alias in STRICT_ALIASES):
        return []
    if any(annotation is bare for bare in BARE_TYPES):
        return [str(getattr(annotation, "__name__", annotation))]
    if isinstance(annotation, TypeAliasType):
        return _bare_types(annotation.__value__)
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is Annotated:
        args = args[:1]
    found = _bare_types(origin) if isinstance(origin, TypeAliasType) else []
    for arg in args:
        found.extend(_bare_types(arg))
    return found


# Errors name the path.


def test_bad_value_names_the_dotted_path() -> None:
    """A misspelt option is rejected, and every error starts at its path."""
    with pytest.raises(ValidationError) as caught:
        ChartSpec.model_validate(_at("bars.border.style", "dashd"))
    locs = [error["loc"] for error in caught.value.errors()]
    assert locs, "No error was reported."
    assert all(loc[:3] == ("bars", "border", "style") for loc in locs), locs


def test_unknown_key_is_rejected() -> None:
    """A key the spec does not define, such as colour for color, is rejected."""
    with pytest.raises(ValidationError) as caught:
        ChartSpec.model_validate(_at("bars.fill.colour", "#E24A33"))
    found = [(error["loc"], error["type"]) for error in caught.value.errors()]
    assert found == [(("bars", "fill", "colour"), "extra_forbidden")]


# Lists become tuples; mappings become read-only.


@pytest.mark.parametrize(
    ("path", "given", "stored"),
    [
        ("bars.fill.color", ["#a", "#b"], ("#a", "#b")),
        ("bars.border.width", [1, 2.5], (1.0, 2.5)),
        ("axis.x.tick.major.text.custom_text", ["North", "South"], ("North", "South")),
        ("lines.label.standard.series", ["2019"], ("2019",)),
    ],
)
def test_list_is_stored_as_tuple(path: str, given: object, stored: object) -> None:
    """A YAML list is stored as a tuple, so a frozen spec holds no list."""
    value = _read(ChartSpec.model_validate(_at(path, given)), path)
    assert value == stored
    assert type(value) is tuple


@pytest.mark.parametrize(
    ("path", "item"),
    [
        ("bars.fill.color", "#E24A33"),
        ("lines.marker.size", 8.0),
        ("bars.label.category.custom_values", 0.15),
        ("lines.label.category.custom_values", 0.15),
    ],
)
def test_mapping_is_read_only(path: str, item: object) -> None:
    """A mapping is stored read-only and does not share the caller's dict."""
    source: dict[str, object] = {"Texas": item}
    stored: Any = _read(ChartSpec.model_validate(_at(path, source)), path)
    assert _is_read_only_mapping(stored), f"{path} holds a {type(stored).__name__}."
    with pytest.raises(TypeError):
        stored["Texas"] = item
    source["Texas"] = "changed after validation"
    assert dict(stored) == {"Texas": item}


# A NamedValueSpec is accepted only as an existing instance (§4.8).


def test_named_value_instance_is_kept_as_it_is() -> None:
    """An existing NamedValueSpec is stored as the same object, not rebuilt."""
    named = NamedValueSpec(names={"2019": "#E24A33"}, rest=("#4C72B0", "#DD8452"))
    assert BarFillSpec(color=named).color is named


def test_dict_with_names_and_rest_stays_a_dict() -> None:
    """A dict with the keys names and rest is a by-name dict, not a NamedValueSpec."""
    given = {"names": "#E24A33", "rest": "#CCCCCC"}
    spec = ChartSpec.model_validate(_at("bars.fill.color", given))
    stored = spec.bars.fill.color
    assert not isinstance(stored, NamedValueSpec)
    assert _is_read_only_mapping(stored)
    assert stored == given


@pytest.mark.filterwarnings("error")
def test_named_value_is_out_of_the_schema_and_dumps_as_a_dict() -> None:
    """The JSON Schema never offers a NamedValueSpec; a dump writes it as a dict.

    The dump cannot be loaded back: its "names" key reads as a series name
    holding a dict, not a colour. This is open for §8.4 (saving a chart's
    look as a theme), which must decide how to write a NamedValueSpec.
    """
    assert "NamedValueSpec" not in json.dumps(ChartSpec.model_json_schema())
    named = NamedValueSpec(names={"2019": "#E24A33"}, rest="#CCCCCC")
    spec = ChartSpec.model_validate({"bars": {"fill": {"color": named}}})
    dumped = spec.model_dump()
    assert dumped["bars"]["fill"]["color"] == {
        "names": {"2019": "#E24A33"},
        "rest": "#CCCCCC",
    }
    with pytest.raises(ValidationError):
        ChartSpec.model_validate(dumped)


# Numbers and booleans are strict.


def test_every_number_and_flag_uses_a_strict_alias() -> None:
    """No leaf holds a bare float, int or bool, which would accept "1" or True."""
    offenders = [
        f"{item.path}: {', '.join(bare)}"
        for item in leaves(ChartSpec())
        if (bare := _bare_types(item.info.annotation))
    ]
    assert not offenders, (
        f"Use Number, Integer or Flag instead of a bare type at: {offenders}"
    )


def test_bare_type_check_catches_each_kind() -> None:
    """The check itself finds bare types, also inside unions and Value."""
    assert _bare_types(float | None) == ["float"]
    assert _bare_types(Value[int] | None) == ["int"]
    assert _bare_types(bool | str) == ["bool"]
    assert _bare_types(Number | None) == []
    assert _bare_types(Value[Number] | None) == []
    assert _bare_types(Integer | Flag) == []


def test_number_alias() -> None:
    """Number accepts whole and decimal numbers as floats; rejects text and bools."""
    adapter = TypeAdapter[float](Number)
    assert adapter.validate_python(1) == 1.0
    assert type(adapter.validate_python(1)) is float
    assert adapter.validate_python(0.5) == 0.5
    for bad in ("1", True, False):
        with pytest.raises(ValidationError):
            adapter.validate_python(bad)


def test_integer_alias() -> None:
    """Integer accepts whole numbers; rejects text, booleans and floats."""
    adapter = TypeAdapter[int](Integer)
    assert adapter.validate_python(1) == 1
    assert type(adapter.validate_python(1)) is int
    for bad in ("1", True, 1.0):
        with pytest.raises(ValidationError):
            adapter.validate_python(bad)


def test_flag_alias() -> None:
    """Flag accepts True and False; rejects text and numbers."""
    adapter = TypeAdapter[bool](Flag)
    assert adapter.validate_python(True) is True
    assert adapter.validate_python(False) is False
    for bad in ("1", "true", 1, 0):
        with pytest.raises(ValidationError):
            adapter.validate_python(bad)


def test_value_alias_keeps_strictness_in_every_form() -> None:
    """Value[Number] is strict in its single, list and dict forms alike."""
    adapter = TypeAdapter[object](Value[Number])
    assert adapter.validate_python([1, 2.5]) == (1.0, 2.5)
    assert adapter.validate_python({"2019": 1}) == {"2019": 1.0}
    for bad in ("1", ["1"], [True], {"2019": "1"}, {"2019": True}):
        with pytest.raises(ValidationError):
            adapter.validate_python(bad)


# What was set, and the JSON Schema.


def test_fields_set_reports_only_what_was_given() -> None:
    """model_fields_set names only the fields given, at every level (§5.4)."""
    assert BarFillSpec(color="#E24A33").model_fields_set == {"color"}
    spec = ChartSpec.model_validate(_at("bars.fill.color", "#E24A33"))
    assert spec.model_fields_set == {"bars"}
    assert spec.bars.model_fields_set == {"fill"}
    assert spec.bars.fill.model_fields_set == {"color"}
    assert ChartSpec().model_fields_set == set()


def test_schema_lists_every_leaf() -> None:
    """The JSON Schema, walked by path, has exactly the leaves the model has."""
    schema = ChartSpec.model_json_schema()
    from_schema = {path for path, _ in _schema_leaves(schema)}
    from_model = {item.path for item in leaves(ChartSpec())}
    assert from_schema == from_model, (
        f"Only in the schema: {sorted(from_schema - from_model)}. "
        f"Only in the model: {sorted(from_model - from_schema)}."
    )


def test_schema_descriptions_are_sentences() -> None:
    """Every field in the JSON Schema, node or leaf, has a description sentence."""
    schema = ChartSpec.model_json_schema()
    found = list(_schema_fields(schema, schema))
    offenders = [
        path
        for path, prop, _ in found
        if not str(prop.get("description", "")).endswith(".")
    ]
    assert any(is_node for _, _, is_node in found), "No nodes were walked."
    assert not offenders, f"Schema fields without a description sentence: {offenders}"


def test_schema_marks_exactly_the_nineteen_value_mapped_paths() -> None:
    """value_mapped: true appears in the JSON Schema on the 19 paths of §4.8 only."""
    schema = ChartSpec.model_json_schema()
    marked = {
        path
        for path, prop in _schema_leaves(schema)
        if prop.get("value_mapped") is True
    }
    assert marked == VALUE_MAPPED, (
        f"Marked but not value-mapped: {sorted(marked - VALUE_MAPPED)}. "
        f"Value-mapped but not marked: {sorted(VALUE_MAPPED - marked)}."
    )


# Dumping a spec back to plain data.


@pytest.mark.filterwarnings("error")
def test_dump_with_mappings_is_silent_and_round_trips() -> None:
    """model_dump and model_dump_json warn about nothing and read back equal."""
    spec = ChartSpec.model_validate(
        {
            "bars": {
                "fill": {"color": {"2019": "#E24A33"}},
                "border": {"width": [1, 2]},
                "label": {"category": {"custom_values": {"Texas": 0.15}}},
            },
            "lines": {"marker": {"size": {"2019": 8}}},
        }
    )
    dumped = spec.model_dump()
    assert dumped["bars"]["fill"]["color"] == {"2019": "#E24A33"}
    assert type(dumped["bars"]["fill"]["color"]) is dict
    assert ChartSpec.model_validate(dumped) == spec
    assert ChartSpec.model_validate_json(spec.model_dump_json()) == spec
    assert ChartSpec.model_validate(spec.model_dump(exclude_unset=True)) == spec
