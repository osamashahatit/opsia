"""Validation on the Pydantic specs: what a theme file or a hand-built spec meets.

Every case goes through ``ChartSpec.model_validate`` with the nested dict a
YAML theme file would give, so the tests exercise the same path a theme load
will (§5.1). Reshaping errors into one message per path is P2.3 work; these
tests only check what Pydantic reports.
"""

from collections.abc import Iterator
from types import MappingProxyType
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from opsia.spec import BarFillSpec, ChartSpec

from .test_tree import VALUE_MAPPED
from .walker import leaves

NUMBER_PATHS = (
    "bars.layout.width",
    "axis.y.scale.min_value",
    "legend.frame.border_radius",
    "bars.border.width",
    "lines.marker.size",
)
"""Number leaves, plain and inside Value[Number]."""

INTEGER_PATHS = (
    "bars.label.standard.hide_smallest",
    "axis.y.scale.minor_divisions",
    "axis.x.tick.major.text.numeric.decimals",
)

FLAG_PATHS = (
    "legend.layout.show",
    "axis.spine.top.show",
    "bars.label.standard.numeric.separator",
)


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


def _rejects(path: str, value: object) -> bool:
    """Say whether building a spec with value at path raises a ValidationError."""
    try:
        ChartSpec.model_validate(_at(path, value))
    except ValidationError:
        return True
    return False


def _is_read_only_mapping(value: object) -> bool:
    """Say whether a value is stored as a MappingProxyType."""
    return isinstance(value, MappingProxyType)


def _schema_leaves(
    schema: dict[str, Any], node: dict[str, Any], prefix: str = ""
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield (dotted path, property) for every leaf in a model's JSON Schema."""
    definitions: dict[str, Any] = schema["$defs"]
    for name, prop in node["properties"].items():
        path = f"{prefix}{name}"
        ref: str | None = prop.get("$ref")
        target: dict[str, Any] = (
            definitions.get(ref.rsplit("/", 1)[-1], {}) if ref else {}
        )
        if "properties" in target:
            yield from _schema_leaves(schema, target, f"{path}.")
        else:
            yield path, prop


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


# Numbers and booleans are strict.


@pytest.mark.parametrize("path", NUMBER_PATHS)
@pytest.mark.parametrize("bad", ["1", True, False])
def test_number_leaf_rejects_text_and_booleans(path: str, bad: object) -> None:
    """A Number leaf rejects "1", True and False instead of converting them."""
    assert _rejects(path, bad), f"{path} accepted {bad!r}."


@pytest.mark.parametrize("path", NUMBER_PATHS)
def test_number_leaf_accepts_a_whole_number_as_float(path: str) -> None:
    """A Number leaf accepts 1 and stores it as 1.0."""
    value = _read(ChartSpec.model_validate(_at(path, 1)), path)
    assert value == 1.0
    assert type(value) is float


@pytest.mark.parametrize("path", INTEGER_PATHS)
@pytest.mark.parametrize("bad", ["1", True, 1.0])
def test_integer_leaf_rejects_text_booleans_and_floats(path: str, bad: object) -> None:
    """An Integer leaf rejects "1", True and 1.0."""
    assert _rejects(path, bad), f"{path} accepted {bad!r}."


@pytest.mark.parametrize("path", INTEGER_PATHS)
def test_integer_leaf_accepts_a_whole_number(path: str) -> None:
    """An Integer leaf accepts 1 and stores it as an int."""
    value = _read(ChartSpec.model_validate(_at(path, 1)), path)
    assert value == 1
    assert type(value) is int


@pytest.mark.parametrize("path", FLAG_PATHS)
@pytest.mark.parametrize("bad", ["1", "true", 1, 0])
def test_flag_leaf_rejects_text_and_numbers(path: str, bad: object) -> None:
    """A Flag leaf rejects "1", "true", 1 and 0 instead of converting them."""
    assert _rejects(path, bad), f"{path} accepted {bad!r}."


@pytest.mark.parametrize("path", FLAG_PATHS)
@pytest.mark.parametrize("good", [True, False])
def test_flag_leaf_accepts_booleans(path: str, good: bool) -> None:
    """A Flag leaf accepts True and False."""
    assert _read(ChartSpec.model_validate(_at(path, good)), path) is good


@pytest.mark.parametrize("bad", [["1"], [True], {"2019": "1"}, {"2019": True}])
def test_strictness_holds_inside_value_forms(bad: object) -> None:
    """Value[Number] is strict inside its tuple and mapping forms too."""
    assert _rejects("bars.border.width", bad), f"accepted {bad!r}."


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
    from_schema = {path for path, _ in _schema_leaves(schema, schema)}
    from_model = {item.path for item in leaves(ChartSpec())}
    assert from_schema == from_model, (
        f"Only in the schema: {sorted(from_schema - from_model)}. "
        f"Only in the model: {sorted(from_model - from_schema)}."
    )


def test_schema_leaf_descriptions_are_sentences() -> None:
    """Every leaf in the JSON Schema has a description ending in a full stop."""
    schema = ChartSpec.model_json_schema()
    offenders = [
        path
        for path, prop in _schema_leaves(schema, schema)
        if not str(prop.get("description", "")).endswith(".")
    ]
    assert not offenders, f"Schema leaves without a description sentence: {offenders}"


def test_schema_marks_exactly_the_nineteen_value_mapped_paths() -> None:
    """value_mapped: true appears in the JSON Schema on the 19 paths of §4.8 only."""
    schema = ChartSpec.model_json_schema()
    marked = {
        path
        for path, prop in _schema_leaves(schema, schema)
        if prop.get("value_mapped") is True
    }
    assert marked == VALUE_MAPPED, (
        f"Marked but not value-mapped: {sorted(marked - VALUE_MAPPED)}. "
        f"Value-mapped but not marked: {sorted(VALUE_MAPPED - marked)}."
    )


# Dumping, which P2.3's replace_at depends on.


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
