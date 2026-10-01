"""merge_layers: the layer above wins where it sets a value (§5.4).

Layers are built with ``replace_at``, the way themes and recorders will
build them, so these tests also show the two helpers working together.
Value-mapped settings fill in by name instead of being replaced (§4.8).
"""

import inspect
import itertools
from functools import reduce

import pytest

from opsia.spec import BarsSpec, ChartSpec, NamedValueSpec, merge_layers, replace_at

RED = "#E24A33"
GOLD = "#FBC15E"
GREEN = "#55A868"
GREY = "#CCCCCC"
PALETTE = ("#4C72B0", "#DD8452")


def _layer(path: str, **changes: object) -> ChartSpec:
    """Build a layer that sets only the given settings of one node."""
    return replace_at(ChartSpec(), path, **changes)


def _fold(*layers: ChartSpec) -> ChartSpec:
    """Merge layers in order, each one over the result of those before it."""
    return reduce(lambda below, above: merge_layers(below=below, above=above), layers)


# Which value wins.


def test_above_wins_where_it_sets_a_value() -> None:
    """A setting the upper layer sets replaces the lower layer's value."""
    below = _layer("bars.fill", color="#4C72B0")
    above = _layer("bars.fill", color="#E24A33")
    assert merge_layers(below=below, above=above).bars.fill.color == "#E24A33"


def test_below_shows_through_where_above_is_none() -> None:
    """A setting the upper layer leaves as None keeps the lower layer's value."""
    below = _layer("bars.fill", color="#4C72B0", alpha=0.6)
    above = _layer("bars.fill", color="#E24A33")
    merged = merge_layers(below=below, above=above)
    assert merged.bars.fill.color == "#E24A33"
    assert merged.bars.fill.alpha == 0.6


def test_settings_in_different_nodes_combine() -> None:
    """Settings the two layers make in different nodes all reach the result."""
    below = _layer("title", size=16)
    above = _layer("bars.layout", width=0.6)
    merged = merge_layers(below=below, above=above)
    assert merged.title.size == 16.0
    assert merged.bars.layout.width == 0.6


def test_three_layers_fold_in_order() -> None:
    """Default, theme and user layers, merged in that order, give each its say."""
    default = replace_at(
        _layer("bars.fill", color="#CCCCCC", alpha=1.0), "title", size=14
    )
    theme = replace_at(
        _layer("bars.fill", color=["#4C72B0", "#DD8452"]), "title", size=16
    )
    user = _layer("title", text="Top 5 States")
    merged = _fold(default, theme, user)
    assert merged.bars.fill.color == ("#4C72B0", "#DD8452")
    assert merged.bars.fill.alpha == 1.0
    assert merged.title.size == 16.0
    assert merged.title.text == "Top 5 States"


def test_swapping_the_layers_changes_the_result() -> None:
    """The order of the layers matters; keywords make it visible at the call."""
    theme = _layer("bars.fill", color="#4C72B0")
    user = _layer("bars.fill", color="#E24A33")
    assert merge_layers(below=theme, above=user).bars.fill.color == "#E24A33"
    assert merge_layers(below=user, above=theme).bars.fill.color == "#4C72B0"


def test_layers_are_keyword_only() -> None:
    """Both layers must be named, so they cannot be swapped by position."""
    parameters = inspect.signature(merge_layers).parameters.values()
    assert [parameter.name for parameter in parameters] == ["below", "above"]
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in parameters
    )


# Value-mapped settings: a dict fills in, a scalar or list replaces (§4.8).


@pytest.mark.parametrize(
    ("below", "above", "expected"),
    [
        pytest.param(GREY, None, GREY, id="nothing above keeps below"),
        pytest.param({"2019": RED}, GREY, GREY, id="scalar replaces all"),
        pytest.param({"2019": RED}, list(PALETTE), PALETTE, id="list replaces all"),
        pytest.param(None, {"2019": RED}, {"2019": RED}, id="dict over nothing"),
        pytest.param(
            list(PALETTE),
            {"2019": RED},
            NamedValueSpec(names={"2019": RED}, rest=PALETTE),
            id="dict over list",
        ),
        pytest.param(
            GREY,
            {"2019": RED},
            NamedValueSpec(names={"2019": RED}, rest=GREY),
            id="dict over scalar",
        ),
        pytest.param(
            {"2019": GREEN, "2020": GOLD},
            {"2019": RED},
            {"2019": RED, "2020": GOLD},
            id="dict over dict is one dict",
        ),
        pytest.param(
            NamedValueSpec(names={"2019": GREEN}, rest=PALETTE),
            {"2019": RED, "2020": GOLD},
            NamedValueSpec(names={"2019": RED, "2020": GOLD}, rest=PALETTE),
            id="dict over named fills in names",
        ),
        pytest.param(
            {"2021": GREEN},
            NamedValueSpec(names={"2019": RED}, rest=GREY),
            NamedValueSpec(names={"2019": RED}, rest=GREY),
            id="named above wins whole",
        ),
    ],
)
def test_value_mapped_layering(below: object, above: object, expected: object) -> None:
    """Each row of the layering rule, merged on bars.fill.color."""
    merged = merge_layers(
        below=_layer("bars.fill", color=below),
        above=_layer("bars.fill", color=above),
    )
    color = merged.bars.fill.color
    assert color == expected
    assert isinstance(color, NamedValueSpec) is isinstance(expected, NamedValueSpec)


def test_grouping_does_not_matter() -> None:
    """merge(merge(a, b), c) equals merge(a, merge(b, c)) for every stack.

    Phase 5 merges theme chains, so how they are grouped must not change the
    result. Every stack of three layers drawn from nothing, a scalar, a list
    and two dicts is checked.
    """
    values: list[object] = [
        None,
        GREY,
        list(PALETTE),
        {"2019": RED},
        {"2019": GREEN, "2020": GOLD},
    ]
    layers = [_layer("bars.fill", color=value) for value in values]
    offenders: list[str] = []
    for (i, a), (j, b), (k, c) in itertools.product(enumerate(layers), repeat=3):
        left = merge_layers(below=merge_layers(below=a, above=b), above=c)
        right = merge_layers(below=a, above=merge_layers(below=b, above=c))
        if left != right:
            offenders.append(f"{values[i]!r} < {values[j]!r} < {values[k]!r}")
    assert not offenders, f"Grouping changed the result for: {offenders}"


def test_custom_values_is_replaced_whole() -> None:
    """custom_values is substitution, not value mapping: a dict above replaces."""
    below = _layer("bars.label.category", custom_values={"Texas": 0.15})
    above = _layer("bars.label.category", custom_values={"Ohio": 0.2})
    merged = merge_layers(below=below, above=above)
    assert merged.bars.label.category.custom_values == {"Ohio": 0.2}


# Sharing: what above leaves alone is below's own object.


def test_untouched_subtrees_are_the_same_objects_as_below() -> None:
    """Every subtree the upper layer sets nothing in is the lower layer's object."""
    below = _layer("bars.fill", color="#4C72B0")
    above = _layer("bars.fill", color="#E24A33")
    merged = merge_layers(below=below, above=above)
    assert merged.axis is below.axis
    assert merged.legend is below.legend
    assert merged.title is below.title
    assert merged.lines is below.lines
    assert merged.bars.border is below.bars.border
    assert merged.bars.label is below.bars.label


def test_subtree_set_only_below_is_kept() -> None:
    """A subtree only the lower layer sets is kept as the lower layer's object."""
    below = _layer("bars.label.standard", show=True, size=9)
    above = _layer("title", text="Q4")
    merged = merge_layers(below=below, above=above)
    assert merged.bars is below.bars
    assert merged.bars.label.standard.size == 9.0


def test_empty_layer_above_returns_below() -> None:
    """When the upper layer sets nothing, the result is the lower layer itself."""
    below = _layer("bars.fill", color="#4C72B0")
    assert merge_layers(below=below, above=ChartSpec()) is below


def test_same_layer_twice_returns_it() -> None:
    """Merging a layer over itself gives the same layer back."""
    layer = _layer("bars.fill", color="#4C72B0")
    assert merge_layers(below=layer, above=layer) is layer


def test_layers_are_not_changed() -> None:
    """Merging builds a new spec; neither layer is changed."""
    below = _layer("bars.fill", color="#4C72B0", alpha=0.6)
    above = _layer("bars.fill", color="#E24A33")
    merge_layers(below=below, above=above)
    assert below.bars.fill.color == "#4C72B0"
    assert above.bars.fill.alpha is None


def test_different_spec_classes_raise() -> None:
    """Only two specs of the same class can be merged."""
    with pytest.raises(TypeError, match="Cannot merge a BarsSpec over a ChartSpec"):
        merge_layers(below=ChartSpec(), above=BarsSpec())
