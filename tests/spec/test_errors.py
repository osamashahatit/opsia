"""Readable errors: one block per dotted path, valid options, a close match (§9.6).

Every case goes through ``ChartSpec.model_validate`` with the nested dict a
theme file would give, then through ``build_spec_error``, so the tests see
the same messages a theme load will. The texts asserted in full are the
wording approved for P2.3a; a change to them is a change to the interface
(§9.6 rule 6).

The resolver's messages (§4.8, §7.2) are asserted in full at the end.
"""

import importlib
from typing import TypeAliasType

import pytest
from pydantic import ValidationError

from opsia.spec import (
    BarBorderSpec,
    ChartSpec,
    Value,
    build_spec_error,
    replace_at,
    resolve_per_item,
    resolve_per_series,
)

from .walker import leaves

ERRORS_MODULE = importlib.import_module("opsia.spec.core._errors")
TYPES_MODULE = importlib.import_module("opsia.spec.core._types")

LINE_STYLES = "'solid', 'dashed', 'dashdot', 'dotted', 'none'"
FILL_SETTINGS = "alpha, color, max_alpha, max_color, min_alpha, min_color"


def _at(path: str, value: object) -> dict[str, object]:
    """Build the nested dict a theme file would give for one dotted path."""
    keys = path.split(".")
    data: dict[str, object] = {keys[-1]: value}
    for key in reversed(keys[:-1]):
        data = {key: data}
    return data


def _message(data: object) -> str:
    """Validate data as a whole chart spec and return the readable message."""
    try:
        ChartSpec.model_validate(data)
    except ValidationError as err:
        return str(build_spec_error(err, node=ChartSpec))
    raise AssertionError(f"{data!r} was accepted.")


def _raw_error_count(data: object) -> int:
    """Return how many errors Pydantic itself reports for data."""
    try:
        ChartSpec.model_validate(data)
    except ValidationError as err:
        return err.error_count()
    return 0


# The approved messages, in full.


def test_bad_option() -> None:
    """A misspelt option lists the valid options and suggests the closest."""
    assert _message(_at("bars.border.style", "dashd")) == (
        "Invalid value for bars.border.style: 'dashd'.\n"
        f"Valid options: {LINE_STYLES}.\n"
        "Did you mean 'dashed'?"
    )


def test_wrong_kind_on_a_value_mapped_setting() -> None:
    """The wrong kind of value on a value-mapped setting also lists its forms."""
    assert _message(_at("bars.border.style", 5)) == (
        "Invalid value for bars.border.style: 5.\n"
        f"Valid options: {LINE_STYLES}.\n"
        "Give one option, a list of them (one per series), "
        "or a dict of them by series or category name."
    )


def test_bad_item_in_a_list() -> None:
    """A bad item in a per-series list is named by its position, from 1."""
    assert _message(_at("bars.border.style", ["solid", "dashd"])) == (
        "Invalid value for bars.border.style, item 2 of the list: 'dashd'.\n"
        f"Valid options: {LINE_STYLES}.\n"
        "Did you mean 'dashed'?"
    )


def test_bad_value_in_a_dict() -> None:
    """A bad value in a by-name dict is named by its key."""
    assert _message(_at("bars.fill.alpha", {"2019": "0.5"})) == (
        "Invalid value for bars.fill.alpha, key '2019': '0.5' (text).\n"
        "Expected a number, such as 0.8."
    )


def test_text_given_for_a_number() -> None:
    """Text where a number is expected is marked as text."""
    assert _message(_at("bars.layout.width", "0.8")) == (
        "Invalid value for bars.layout.width: '0.8' (text).\n"
        "Expected a number, such as 0.8."
    )


def test_dict_key_that_is_not_text() -> None:
    """An unquoted year in a theme file becomes a number key; the fix is quotes."""
    assert _message(_at("bars.fill.color", {2019: "#E24A33"})) == (
        "Invalid key for bars.fill.color: 2019 (a number).\n"
        "Names in a dict must be text. Write it in quotes: '2019'."
    )


def test_unknown_setting() -> None:
    """An unknown setting lists the node's settings and suggests the closest."""
    assert _message(_at("bars.fill.colour", "#E24A33")) == (
        "Unknown setting: bars.fill.colour.\n"
        f"Valid settings for bars.fill: {FILL_SETTINGS}.\n"
        "Did you mean 'color'?"
    )


def test_unknown_setting_on_a_node_with_children() -> None:
    """When the node also holds child nodes, they are listed on their own line."""
    assert _message(_at("bars.label.standard.colr", "#333333")) == (
        "Unknown setting: bars.label.standard.colr.\n"
        "Valid settings for bars.label.standard: color, font, hide_smallest, "
        "horizontal_alignment, show, size, vertical_alignment, x_offset, "
        "y_offset.\n"
        "Nodes under bars.label.standard: frame, numeric.\n"
        "Did you mean 'color'?"
    )


def test_unknown_node() -> None:
    """An unknown name under a node that holds only nodes is an unknown node."""
    assert _message({"bars": {"fil": {"color": "#E24A33"}}}) == (
        "Unknown node: bars.fil.\n"
        "Valid nodes under bars: border, fill, label, layout.\n"
        "Did you mean 'fill'?"
    )


def test_unknown_top_level_node() -> None:
    """An unknown name at the root lists the top-level nodes."""
    assert _message({"bar": {}}) == (
        "Unknown node: bar.\n"
        "Valid nodes at the top level: axis, bars, legend, lines, title.\n"
        "Did you mean 'bars'?"
    )


def test_node_given_a_value() -> None:
    """A value where a node is expected lists what the node holds."""
    assert _message(_at("bars.fill", 5)) == (
        "bars.fill is a node, not a setting.\n"
        f"Valid settings for bars.fill: {FILL_SETTINGS}."
    )


def test_two_paths_give_two_blocks() -> None:
    """Two mistakes at two paths give one error with a count and two blocks."""
    data = {
        "bars": {
            "fill": {"colour": "#E24A33"},
            "border": {"style": "dashd"},
        }
    }
    assert _message(data) == (
        "2 problems found.\n"
        "\n"
        "Unknown setting: bars.fill.colour.\n"
        f"Valid settings for bars.fill: {FILL_SETTINGS}.\n"
        "Did you mean 'color'?\n"
        "\n"
        "Invalid value for bars.border.style: 'dashd'.\n"
        f"Valid options: {LINE_STYLES}.\n"
        "Did you mean 'dashed'?"
    )


# One block per path.


def test_value_mapped_mistake_gives_one_block_not_four() -> None:
    """Pydantic reports one error per form of Value; the message has one block.

    The four forms are a scalar, a list, a dict and a NamedValueSpec (§4.8).
    """
    data = _at("bars.border.style", "dashd")
    assert _raw_error_count(data) == 4
    message = _message(data)
    assert message.count("Invalid value for") == 1
    assert "problems found" not in message


def test_every_setting_gets_one_block() -> None:
    """Every leaf in the tree, given a value it cannot accept, gets one block.

    This also proves that every annotation in the spec can be described in
    a message: an unknown kind of type would raise a TypeError here.
    """
    offenders: list[str] = []
    found = list(leaves(ChartSpec()))
    for item in found:
        message = _message(_at(item.path, object()))
        if not message.startswith(f"Invalid value for {item.path}: "):
            offenders.append(f"{item.path}: {message.splitlines()[0]}")
        elif "problems found" in message:
            offenders.append(f"{item.path}: more than one block")
    assert len(found) > 350, f"Only {len(found)} leaves were walked."
    assert not offenders, f"Leaves with a wrong message: {offenders}"


# Close matches.


@pytest.mark.parametrize(
    ("path", "given", "suggested"),
    [
        ("bars.fill.colour", "#E24A33", "color"),
        ("bars.border.style", "dashd", "dashed"),
        ("legend.layout.position", "upper rigth", "upper right"),
        ("axis.y.tick.major.text.numeric.display_units", "K", "k"),
    ],
)
def test_close_match_is_suggested(path: str, given: str, suggested: str) -> None:
    """An unknown key and a bad option both suggest the closest name, any case."""
    assert f"Did you mean {suggested!r}?" in _message(_at(path, given))


def test_no_suggestion_when_nothing_is_close() -> None:
    """With no close match, the message has no "Did you mean" line."""
    assert "Did you mean" not in _message(_at("bars.border.style", "xyz"))


# Where a message points, and what it carries.


def test_prefix_names_the_full_path() -> None:
    """A node validated on its own is named by its full path from the root."""
    try:
        BarBorderSpec.model_validate({"style": "dashd"})
    except ValidationError as err:
        message = str(build_spec_error(err, node=BarBorderSpec, prefix="bars.border"))
    else:
        raise AssertionError("'dashd' was accepted.")
    assert message.startswith("Invalid value for bars.border.style: 'dashd'.")


def test_cause_is_the_validation_error() -> None:
    """The readable error keeps Pydantic's error as its cause (§9.6 rule 5)."""
    with pytest.raises(ValueError, match=r"bars\.border\.style") as caught:
        replace_at(ChartSpec(), "bars.border", style="dashd")
    assert isinstance(caught.value.__cause__, ValidationError)


def test_build_value_error_needs_a_block() -> None:
    """Joining no blocks is a mistake in the caller and raises."""
    build_value_error = vars(ERRORS_MODULE)["build_value_error"]
    with pytest.raises(ValueError, match="at least one block"):
        build_value_error([])


def test_alias_wording_names_real_aliases() -> None:
    """The aliases given their own wording exist and are plain text aliases."""
    alias_kinds: dict[str, str] = vars(ERRORS_MODULE)["_ALIAS_KINDS"]
    for name in alias_kinds:
        alias = getattr(TYPES_MODULE, name)
        assert isinstance(alias, TypeAliasType), f"{name} is not an alias."
        assert alias.__value__ is str, f"{name} is not an alias of str."


# The resolver's messages, in full (§4.8, §7.2).


def _item_message(value: Value[str], *, series: list[str], legend: bool) -> str:
    """Resolve per bar on bars.fill.color and return the error message."""
    with pytest.raises(ValueError) as caught:
        resolve_per_item(
            value,
            path="bars.fill.color",
            series=series,
            categories=["Texas", "Ohio"],
            legend=legend,
        )
    return str(caught.value)


def _line_message(path: str, value: Value[str]) -> str:
    """Resolve per line without a legend and return the error message."""
    with pytest.raises(ValueError) as caught:
        resolve_per_series(
            value, path=path, series=["Sales"], categories=["Jan"], legend=False
        )
    return str(caught.value)


def test_unknown_name_in_a_dict() -> None:
    """A dict key that names nothing lists the valid names and the closest."""
    assert _item_message({"Texsa": "red"}, series=["Sales"], legend=False) == (
        "Unknown name in bars.fill.color: 'Texsa'.\n"
        "Valid categories: 'Texas', 'Ohio'.\n"
        "Did you mean 'Texas'?"
    )
    assert _item_message(
        {"Utah": "red", "Iowa": "blue"}, series=["Sales"], legend=False
    ) == (
        "Unknown names in bars.fill.color: 'Utah', 'Iowa'.\n"
        "Valid categories: 'Texas', 'Ohio'."
    )


def test_names_left_without_a_value() -> None:
    """A plain dict with nothing below it names every series it leaves out."""
    assert _item_message(
        {"2019": "red"}, series=["2019", "2020", "2021"], legend=True
    ) == (
        "No value for some series in bars.fill.color: '2020', '2021'.\n"
        "Name them in the dict, or set one value or a list for every series "
        "in an earlier call or a theme."
    )


def test_dict_on_a_whole_line_without_a_legend() -> None:
    """A line cannot take a value per category; the message says what to give."""
    assert _line_message("lines.stroke.color", {"Jan": "red"}) == (
        "lines.stroke.color: a line has one colour along its whole length, "
        "so it cannot be set per category.\n"
        "This chart has no legend, so it has one line.\n"
        'Give one value, such as "red".'
    )
    assert _line_message("lines.area.alpha", {"Jan": "0.5"}) == (
        "lines.area.alpha: an area has one opacity along its whole length, "
        "so it cannot be set per category.\n"
        "This chart has no legend, so it has one line.\n"
        "Give one value, such as 0.8."
    )


def test_empty_list() -> None:
    """An empty list gives no series a value."""
    assert _item_message((), series=["2019"], legend=True) == (
        "bars.fill.color: the list is empty, so no series gets a value.\n"
        "Give at least one value."
    )
