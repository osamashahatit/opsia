"""replace_at: a new tree with one node changed, the rest shared (§3.5.2)."""

import itertools
from types import MappingProxyType

import pytest

from opsia.spec import ChartSpec, NamedValueSpec, merge_layers, replace_at

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


# Stored lists and dicts survive a later change.


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


@pytest.mark.parametrize(
    ("path", "changes", "named"),
    [
        pytest.param("bars.fil", {"color": "red"}, ("bars.fil",), id="unknown-node"),
        pytest.param(
            "bars.fill.color",
            {"value": "red"},
            ("bars.fill.color",),
            id="path-ends-at-a-setting",
        ),
        pytest.param(
            "bars..fill", {"color": "red"}, ("bars..fill",), id="empty-path-part"
        ),
        pytest.param(
            "bars",
            {"fill": ChartSpec().bars.fill},
            ("bars.fill",),
            id="node-given-as-a-change",
        ),
        pytest.param(
            "bars.fill",
            {"colour": "red"},
            ("bars.fill.colour",),
            id="unknown-setting",
        ),
        pytest.param(
            "bars.fill",
            {"colour": "red", "alfa": 0.5},
            ("bars.fill.colour", "bars.fill.alfa"),
            id="two-unknown-settings",
        ),
        pytest.param(
            "bars.border",
            {"style": "dashd"},
            ("bars.border.style",),
            id="bad-option",
        ),
        pytest.param(
            "bars.layout", {"width": "1"}, ("bars.layout.width",), id="text-for-number"
        ),
        pytest.param("bars.fill", {"color": []}, ("bars.fill.color",), id="empty-list"),
    ],
)
def test_mistake_names_the_full_path(
    path: str, changes: dict[str, object], named: tuple[str, ...]
) -> None:
    """Every kind of mistake raises a ValueError naming each wrong full path.

    The wording of each message is owned by test_errors.py.
    """
    with pytest.raises(ValueError) as caught:
        replace_at(ChartSpec(), path, **changes)
    message = str(caught.value)
    missing = [name for name in named if name not in message]
    assert not missing, f"The message does not name {missing}: {message}"


def test_original_is_unchanged_after_a_mistake() -> None:
    """A change that raises leaves the spec it was given as it was."""
    spec = replace_at(ChartSpec(), "bars.fill", color="red")
    with pytest.raises(ValueError, match=r"bars\.fill\.alpha"):
        replace_at(spec, "bars.fill", alpha="half")
    assert spec.bars.fill.color == "red"
    assert spec.bars.fill.alpha is None
