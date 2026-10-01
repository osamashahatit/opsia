"""merge_layers: the layer above wins where it sets a value (§5.4).

Layers are built with ``replace_at``, the way themes and recorders will
build them, so these tests also show the two helpers working together.
"""

import inspect
from functools import reduce
from types import MappingProxyType

import pytest

from opsia.spec import BarsSpec, ChartSpec, merge_layers, replace_at


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


# Value-mapped settings are taken whole.


def test_dict_above_replaces_dict_below_whole() -> None:
    """Dicts are not combined key by key: the upper dict replaces the lower one."""
    below = _layer("bars.fill", color={"2019": "#4C72B0", "2020": "#DD8452"})
    above = _layer("bars.fill", color={"2021": "#E24A33"})
    color = merge_layers(below=below, above=above).bars.fill.color
    assert isinstance(color, MappingProxyType)
    assert dict(color) == {"2021": "#E24A33"}


def test_list_above_replaces_list_below_whole() -> None:
    """A shorter list above replaces a longer list below; nothing is kept."""
    below = _layer("bars.border", width=[1, 2, 3])
    above = _layer("bars.border", width=[0.5])
    assert merge_layers(below=below, above=above).bars.border.width == (0.5,)


def test_scalar_above_replaces_dict_below() -> None:
    """A single value above replaces a dict below; the form does not matter."""
    below = _layer("bars.fill", color={"2019": "#4C72B0"})
    above = _layer("bars.fill", color="#E24A33")
    assert merge_layers(below=below, above=above).bars.fill.color == "#E24A33"


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
