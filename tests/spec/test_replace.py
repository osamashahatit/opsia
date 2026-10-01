"""replace_at: a new tree with one node changed, the rest shared (§3.5.2)."""

import itertools
from types import MappingProxyType

import pytest
from pydantic import ValidationError

from opsia.spec import ChartSpec, NamedValueSpec, merge_layers, replace_at

FILL_SETTINGS = "alpha, color, max_alpha, max_color, min_alpha, min_color"


# Setting and reading back.


def test_setting_is_read_back_and_original_is_unchanged() -> None:
    """The new spec holds the change; the spec it came from does not."""
    spec = ChartSpec()
    new = replace_at(spec, "bars.fill", color="#E24A33")
    assert new.bars.fill.color == "#E24A33"
    assert spec.bars.fill.color is None
    assert type(new) is ChartSpec


def test_deep_node_is_changed() -> None:
    """A node several levels down is reached by its dotted path."""
    new = replace_at(ChartSpec(), "bars.label.standard.frame", show=True, width="auto")
    assert new.bars.label.standard.frame.show is True
    assert new.bars.label.standard.frame.width == "auto"


def test_top_level_node_is_changed() -> None:
    """A node directly under the root is changed too."""
    new = replace_at(ChartSpec(), "title", text="Top 5 States", size=16)
    assert new.title.text == "Top 5 States"
    assert new.title.size == 16.0


def test_number_is_stored_as_float() -> None:
    """A whole number given for a Number setting is stored as a float."""
    new = replace_at(ChartSpec(), "bars.layout", width=1)
    assert new.bars.layout.width == 1.0
    assert type(new.bars.layout.width) is float


# Sharing: only the path is rebuilt.


def test_other_branches_are_the_same_objects() -> None:
    """Every node off the changed path is shared with the original spec."""
    spec = ChartSpec()
    new = replace_at(spec, "bars.fill", color="#E24A33")
    assert new.axis is spec.axis
    assert new.legend is spec.legend
    assert new.title is spec.title
    assert new.lines is spec.lines
    assert new.bars.border is spec.bars.border
    assert new.bars.layout is spec.bars.layout
    assert new.bars.label is spec.bars.label


def test_nodes_on_the_path_are_new() -> None:
    """The root, every node along the path and the changed node are rebuilt."""
    spec = ChartSpec()
    new = replace_at(spec, "bars.fill", color="#E24A33")
    assert new is not spec
    assert new.bars is not spec.bars
    assert new.bars.fill is not spec.bars.fill


def test_children_of_the_changed_node_are_the_same_objects() -> None:
    """Changing a node that holds child nodes keeps those children as they are."""
    spec = ChartSpec()
    new = replace_at(spec, "bars.label.standard", size=10)
    assert new.bars.label.standard.size == 10.0
    assert new.bars.label.standard.numeric is spec.bars.label.standard.numeric
    assert new.bars.label.standard.frame is spec.bars.label.standard.frame
    assert new.bars.label.category is spec.bars.label.category


# None means "not set".


def test_none_does_not_erase_an_earlier_value() -> None:
    """A later call passing alpha=None keeps the alpha an earlier call set."""
    first = replace_at(ChartSpec(), "bars.fill", alpha=0.5)
    second = replace_at(first, "bars.fill", color="red", alpha=None)
    assert second.bars.fill.alpha == 0.5
    assert second.bars.fill.color == "red"


def test_all_none_returns_the_same_object() -> None:
    """When every change is None there is nothing to do, so nothing is built."""
    spec = replace_at(ChartSpec(), "bars.fill", color="red")
    assert replace_at(spec, "bars.fill", color=None, alpha=None) is spec
    assert replace_at(spec, "bars.fill") is spec


def test_all_none_still_checks_the_path_and_names() -> None:
    """A wrong path or name raises even when every value is None."""
    with pytest.raises(ValueError, match=r"Unknown node: bars\.fil\."):
        replace_at(ChartSpec(), "bars.fil", color=None)
    with pytest.raises(ValueError, match=r"Unknown setting: bars\.fill\.colour\."):
        replace_at(ChartSpec(), "bars.fill", colour=None)


# Lists and dicts are stored immutably.


def test_list_is_stored_as_a_tuple() -> None:
    """A list given for a per-series setting is stored as a tuple."""
    new = replace_at(ChartSpec(), "bars.fill", color=["#4C72B0", "#DD8452"])
    assert new.bars.fill.color == ("#4C72B0", "#DD8452")
    assert type(new.bars.fill.color) is tuple


def test_dict_is_stored_read_only_and_not_shared() -> None:
    """A dict is stored read-only, and later changes to the caller's dict stay out."""
    given = {"2019": "#E24A33"}
    new = replace_at(ChartSpec(), "bars.fill", color=given)
    stored = new.bars.fill.color
    assert isinstance(stored, MappingProxyType)
    given["2019"] = "changed after the call"
    assert dict(stored) == {"2019": "#E24A33"}


def test_stored_forms_survive_a_later_change_to_the_same_node() -> None:
    """Re-validating a node keeps a mapping a mapping and a tuple a tuple."""
    spec = replace_at(
        ChartSpec(), "bars.border", color={"2019": "#E24A33"}, width=[1, 2]
    )
    new = replace_at(spec, "bars.border", style="dashed")
    assert isinstance(new.bars.border.color, MappingProxyType)
    assert dict(new.bars.border.color) == {"2019": "#E24A33"}
    assert new.bars.border.width == (1.0, 2.0)


# A dict fills in over the stored value (§4.8).


def test_replace_at_uses_the_same_rule_as_merge_layers() -> None:
    """Two .set() calls in a row give what merging the two layers gives.

    Every pair drawn from nothing, a scalar, a list and two dicts is
    checked, so the six layering rows are all reached through replace_at.
    """
    values: list[object] = [
        None,
        "#CCCCCC",
        ["#4C72B0", "#DD8452"],
        {"2019": "#E24A33"},
        {"2019": "#55A868", "2020": "#FBC15E"},
    ]
    offenders: list[str] = []
    for first, second in itertools.product(values, repeat=2):
        stored = replace_at(ChartSpec(), "bars.fill", color=first)
        by_calls = replace_at(stored, "bars.fill", color=second)
        by_merge = merge_layers(
            below=stored, above=replace_at(ChartSpec(), "bars.fill", color=second)
        )
        if by_calls.bars.fill.color != by_merge.bars.fill.color:
            offenders.append(f"{first!r} then {second!r}")
    assert not offenders, f"replace_at and merge_layers differ for: {offenders}"


def test_bad_value_in_a_dict_gives_the_same_error_over_a_stored_value() -> None:
    """A bad value in a dict is reported as it would be with nothing stored."""
    bad = {"2019": "half"}
    with pytest.raises(ValueError, match=r"bars\.fill\.alpha") as alone:
        replace_at(ChartSpec(), "bars.fill", alpha=bad)
    stored = replace_at(ChartSpec(), "bars.fill", alpha=[0.5, 1.0])
    with pytest.raises(ValueError, match=r"bars\.fill\.alpha") as layered:
        replace_at(stored, "bars.fill", alpha=bad)
    assert str(layered.value) == str(alone.value)


def test_stored_named_value_is_a_setting_not_a_node() -> None:
    """A NamedValueSpec in a setting is never walked into or rebuilt as a node."""
    spec = replace_at(ChartSpec(), "bars.fill", color=["#4C72B0", "#DD8452"])
    spec = replace_at(spec, "bars.fill", color={"2019": "#E24A33"})
    named = spec.bars.fill.color
    assert isinstance(named, NamedValueSpec)
    with pytest.raises(ValueError, match="is a setting, not a node"):
        replace_at(spec, "bars.fill.color", rest="red")
    assert replace_at(spec, "bars.fill", alpha=0.5).bars.fill.color is named


# Mistakes raise a ValueError that names the full path.


def test_unknown_node_in_the_path() -> None:
    """A misspelt node in the path is named, with the valid nodes."""
    with pytest.raises(ValueError, match="Unknown node") as caught:
        replace_at(ChartSpec(), "bars.fil", color="red")
    assert str(caught.value) == (
        "Unknown node: bars.fil.\n"
        "Valid nodes under bars: border, fill, label, layout.\n"
        "Did you mean 'fill'?"
    )


def test_path_that_ends_at_a_setting() -> None:
    """A path that names a setting says how to pass it as a change instead."""
    with pytest.raises(ValueError, match="is a setting, not a node") as caught:
        replace_at(ChartSpec(), "bars.fill.color", value="red")
    assert str(caught.value) == (
        "bars.fill.color is a setting, not a node.\n"
        'Pass it as a change on its node: replace_at(spec, "bars.fill", '
        "color=...)."
    )


@pytest.mark.parametrize("path", ["", "bars.", ".bars", "bars..fill"])
def test_path_with_an_empty_part(path: str) -> None:
    """A path with an empty part is rejected before anything is looked up."""
    with pytest.raises(ValueError, match="Invalid path"):
        replace_at(ChartSpec(), path, color="red")


def test_child_node_given_as_a_change() -> None:
    """A change that names a child node raises, even with a valid spec as value."""
    spec = ChartSpec()
    with pytest.raises(ValueError, match="is a node, not a setting") as caught:
        replace_at(spec, "bars", fill=spec.bars.fill)
    assert str(caught.value) == (
        "bars.fill is a node, not a setting.\n"
        f"Valid settings for bars.fill: {FILL_SETTINGS}."
    )


def test_unknown_setting() -> None:
    """A misspelt setting is named with its full path, and the closest is offered."""
    with pytest.raises(ValueError, match="Unknown setting") as caught:
        replace_at(ChartSpec(), "bars.fill", colour="red")
    assert str(caught.value) == (
        "Unknown setting: bars.fill.colour.\n"
        f"Valid settings for bars.fill: {FILL_SETTINGS}.\n"
        "Did you mean 'color'?"
    )


def test_two_unknown_settings_give_one_error() -> None:
    """Every wrong name is reported in one error, one block each."""
    with pytest.raises(ValueError, match="2 problems found") as caught:
        replace_at(ChartSpec(), "bars.fill", colour="red", alfa=0.5)
    message = str(caught.value)
    assert message.startswith("2 problems found.\n\n")
    assert "Unknown setting: bars.fill.colour." in message
    assert "Unknown setting: bars.fill.alfa." in message


def test_bad_option() -> None:
    """A bad option is named with its full path, not the path inside the node."""
    with pytest.raises(ValueError, match="Invalid value") as caught:
        replace_at(ChartSpec(), "bars.border", style="dashd")
    assert str(caught.value) == (
        "Invalid value for bars.border.style: 'dashd'.\n"
        "Valid options: 'solid', 'dashed', 'dashdot', 'dotted', 'none'.\n"
        "Did you mean 'dashed'?"
    )
    assert isinstance(caught.value.__cause__, ValidationError)


def test_text_for_a_number() -> None:
    """The text "1" is not turned into a number; it raises, naming the path."""
    with pytest.raises(ValueError, match="Invalid value") as caught:
        replace_at(ChartSpec(), "bars.layout", width="1")
    assert str(caught.value) == (
        "Invalid value for bars.layout.width: '1' (text).\n"
        "Expected a number, such as 0.8."
    )


def test_original_is_unchanged_after_a_mistake() -> None:
    """A change that raises leaves the spec it was given as it was."""
    spec = replace_at(ChartSpec(), "bars.fill", color="red")
    with pytest.raises(ValueError, match=r"bars\.fill\.alpha"):
        replace_at(spec, "bars.fill", alpha="half")
    assert spec.bars.fill.color == "red"
    assert spec.bars.fill.alpha is None
