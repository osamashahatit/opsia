"""The resolver: one value per artist from a value-mapped setting (§4.8, §7.2).

Both functions are checked on the same forms. Error wording is owned by
``test_errors.py``; here a mistake is checked only for raising a ValueError
that names the path.
"""

import pytest

from opsia.spec import NamedValueSpec, Value, resolve_per_item, resolve_per_series

SERIES = ["2019", "2020", "2021"]
CATEGORIES = ["Texas", "Ohio"]
ONE_SERIES = ["Sales"]


def _items(
    value: Value[str] | None, *, series: list[str] = SERIES, legend: bool = True
) -> dict[tuple[str, str], str]:
    """Resolve per bar or point on bars.fill.color."""
    return resolve_per_item(
        value,
        path="bars.fill.color",
        series=series,
        categories=CATEGORIES,
        legend=legend,
    )


def _lines(
    value: Value[str] | None, *, series: list[str] = SERIES, legend: bool = True
) -> dict[str, str]:
    """Resolve per whole line on lines.stroke.color."""
    return resolve_per_series(
        value,
        path="lines.stroke.color",
        series=series,
        categories=CATEGORIES,
        legend=legend,
    )


def test_none_gives_nothing() -> None:
    """An unset setting resolves to no values; the renderer never sees None."""
    assert _items(None) == {}
    assert _lines(None) == {}


def test_scalar_goes_to_every_artist() -> None:
    """One value reaches every bar and every line."""
    items = _items("red")
    assert list(items) == [(s, c) for s in SERIES for c in CATEGORIES]
    assert set(items.values()) == {"red"}
    assert _lines("red") == dict.fromkeys(SERIES, "red")


def test_list_wraps_by_series_position() -> None:
    """Series i gets item i % len; every category of a series shares it."""
    items = _items(("red", "blue"))
    assert [items[(s, "Ohio")] for s in SERIES] == ["red", "blue", "red"]
    assert items[("2020", "Texas")] == "blue"
    assert _lines(("red", "blue")) == {"2019": "red", "2020": "blue", "2021": "red"}


def test_list_on_one_series_gives_every_bar_the_first_item() -> None:
    """A list means per series, not per bar: one series, one colour (§4.8)."""
    items = _items(("red", "blue"), series=ONE_SERIES, legend=False)
    assert set(items.values()) == {"red"}
    assert _lines(("red", "blue"), series=ONE_SERIES, legend=False) == {"Sales": "red"}


def test_dict_is_keyed_by_series_with_a_legend() -> None:
    """With a legend, dict keys are series names."""
    value = {"2019": "red", "2020": "blue", "2021": "gold"}
    assert _items(value)[("2020", "Texas")] == "blue"
    assert _lines(value) == value


def test_dict_is_keyed_by_category_without_a_legend() -> None:
    """Without a legend, dict keys are category names."""
    items = _items({"Texas": "red", "Ohio": "blue"}, series=ONE_SERIES, legend=False)
    assert items == {("Sales", "Texas"): "red", ("Sales", "Ohio"): "blue"}


def test_named_value_falls_back_to_rest() -> None:
    """A name in names wins; every other name takes the rest, by its own form."""
    named = NamedValueSpec(names={"2020": "red"}, rest=("grey", "black"))
    assert _lines(named) == {"2019": "grey", "2020": "red", "2021": "grey"}
    by_category = NamedValueSpec(names={"Ohio": "red"}, rest="grey")
    items = _items(by_category, series=ONE_SERIES, legend=False)
    assert items == {("Sales", "Texas"): "grey", ("Sales", "Ohio"): "red"}


def test_named_value_on_a_line_without_a_legend_raises() -> None:
    """Names on a whole line without a legend raise, as a plain dict does."""
    named = NamedValueSpec(names={"Ohio": "red"}, rest="grey")
    with pytest.raises(ValueError, match=r"lines\.stroke\.color"):
        _lines(named, series=ONE_SERIES, legend=False)
    unnamed = NamedValueSpec[str](names={}, rest="grey")
    assert _lines(unnamed, series=ONE_SERIES, legend=False) == {"Sales": "grey"}


def test_without_a_legend_there_must_be_one_series() -> None:
    """legend=False with two series is a caller mistake and raises."""
    with pytest.raises(ValueError, match="exactly one series"):
        _items("red", series=["a", "b"], legend=False)
    with pytest.raises(ValueError, match="exactly one series"):
        _lines("red", series=["a", "b"], legend=False)
