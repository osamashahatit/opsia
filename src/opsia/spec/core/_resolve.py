"""Turn a value-mapped setting into one value per artist (§4.8, §7.2).

This is the one place where the legend decides what a dict key means: a
series name when the chart has a legend, a category name when it does not.
Everywhere else, the type of the value alone decides its meaning.

Two functions, one per kind of artist:

- ``resolve_per_item``: one artist per bar or per line point
  (``bars.*``, ``lines.marker.*``), keyed by (series, category).
- ``resolve_per_series``: one artist per whole line
  (``lines.stroke.*``, ``lines.area.*``), keyed by series.

Both are pure: they read names given as text and return a dict. They import
nothing from Matplotlib or pandas, so a recorder can call them at ``.set()``
time to check dict keys early (§9.6 rule 4), and the renderer can call them
at draw time.
"""

from collections.abc import Mapping, Sequence
from difflib import get_close_matches
from typing import cast

from opsia.spec.core._types import NamedValueSpec, Value

_WHOLE_LINE_WORDS = {
    "color": ("colour", '"red"'),
    "alpha": ("opacity", "0.8"),
    "style": ("style", '"dashed"'),
    "width": ("width", "2"),
}
"""For each per-line setting: the noun for it, and one example value."""


def resolve_per_item[T](
    value: Value[T] | None,
    *,
    path: str,
    series: Sequence[str],
    categories: Sequence[str],
    legend: bool,
) -> dict[tuple[str, str], T]:
    """Give every bar, or every point of a line, its value.

    A scalar goes to every artist. A list goes to series in order and wraps
    when shorter; with one series, every artist gets its first item. A dict
    is looked up by series name when ``legend`` is true and by category
    name otherwise. A ``NamedValueSpec`` is looked up by name first, then
    falls back to its rest.

    Parameters
    ----------
    value
        The stored setting, such as ``spec.bars.fill.color``.
    path
        The dotted path of the setting, used in error messages.
    series
        The series names, in drawing order. Exactly one when ``legend`` is
        false.
    categories
        The category names, in drawing order.
    legend
        Whether the chart has a legend column.

    Returns
    -------
        The value for each (series, category) pair, covering every pair, or
        an empty dict when ``value`` is None.

    Raises
    ------
    ValueError
        A dict names a series or category that does not exist, or leaves
        some without a value. The message names the path and lists the
        valid names.

    Examples
    --------
    >>> resolve_per_item(
    ...     ("red", "blue"),
    ...     path="bars.fill.color",
    ...     series=["2019", "2020"],
    ...     categories=["Texas", "Ohio"],
    ...     legend=True,
    ... )
    {('2019', 'Texas'): 'red', ('2019', 'Ohio'): 'red', ('2020', 'Texas'): 'blue', ('2020', 'Ohio'): 'blue'}
    >>> named = NamedValueSpec(names={"Texas": "red"}, rest="grey")
    >>> resolve_per_item(
    ...     named,
    ...     path="bars.fill.color",
    ...     series=["Sales"],
    ...     categories=["Texas", "Ohio"],
    ...     legend=False,
    ... )
    {('Sales', 'Texas'): 'red', ('Sales', 'Ohio'): 'grey'}
    """
    if value is None:
        return {}
    _check_series(series, legend=legend)
    names, rest = _split(value)
    keys = series if legend else categories
    _check_names(names, keys, path=path, legend=legend)
    spread = _spread(rest, series, path=path)
    result: dict[tuple[str, str], T] = {}
    missing: list[str] = []
    for one_series in series:
        for category in categories:
            key = one_series if legend else category
            if key in names:
                result[(one_series, category)] = names[key]
            elif one_series in spread:
                result[(one_series, category)] = spread[one_series]
            elif key not in missing:
                missing.append(key)
    if missing:
        raise ValueError(_missing_message(path, missing, legend=legend))
    return result


def resolve_per_series[T](
    value: Value[T] | None,
    *,
    path: str,
    series: Sequence[str],
    categories: Sequence[str],
    legend: bool,
) -> dict[str, T]:
    """Give every whole line, or every area under a line, its value.

    The forms mean what they mean in ``resolve_per_item``, with one
    exception: without a legend, a dict is keyed by category, and a line
    cannot take a value per category. A dict, or a ``NamedValueSpec`` that
    names anything, then raises (§4.8).

    Parameters
    ----------
    value
        The stored setting, such as ``spec.lines.stroke.color``.
    path
        The dotted path of the setting, used in error messages.
    series
        The series names, in drawing order. Exactly one when ``legend`` is
        false.
    categories
        The category names, in drawing order. Read only to keep the two
        functions' signatures the same.
    legend
        Whether the chart has a legend column.

    Returns
    -------
        The value for each series, covering every series, or an empty dict
        when ``value`` is None.

    Raises
    ------
    ValueError
        A dict is given on a chart without a legend, names a series that
        does not exist, or leaves some series without a value. The message
        names the path and says what to give instead.

    Examples
    --------
    >>> resolve_per_series(
    ...     ("red", "blue"),
    ...     path="lines.stroke.color",
    ...     series=["2019", "2020", "2021"],
    ...     categories=["Jan", "Feb"],
    ...     legend=True,
    ... )
    {'2019': 'red', '2020': 'blue', '2021': 'red'}
    >>> resolve_per_series(
    ...     {"Jan": "red"},
    ...     path="lines.stroke.color",
    ...     series=["Sales"],
    ...     categories=["Jan", "Feb"],
    ...     legend=False,
    ... )
    Traceback (most recent call last):
    ...
    ValueError: lines.stroke.color: a line has one colour along its whole length, so it cannot be set per category.
    This chart has no legend, so it has one line.
    Give one value, such as "red".
    """
    del categories
    if value is None:
        return {}
    _check_series(series, legend=legend)
    names, rest = _split(value)
    if names and not legend:
        raise ValueError(_whole_line_message(path))
    _check_names(names, series, path=path, legend=legend)
    spread = _spread(rest, series, path=path)
    result: dict[str, T] = {}
    missing: list[str] = []
    for one_series in series:
        if one_series in names:
            result[one_series] = names[one_series]
        elif one_series in spread:
            result[one_series] = spread[one_series]
        else:
            missing.append(one_series)
    if missing:
        raise ValueError(_missing_message(path, missing, legend=legend))
    return result


def _split[T](value: Value[T]) -> tuple[Mapping[str, T], "T | tuple[T, ...] | None"]:
    """Split a value into its names and what applies to every other name.

    A plain dict has names and nothing else; a scalar or a list has no
    names. Each form is checked on ``raw``, typed ``object``, and then cast:
    an ``isinstance`` check on ``value`` itself would leave item types
    unknown, which strict pyright rejects.
    """
    raw: object = value
    if isinstance(raw, NamedValueSpec):
        named = cast("NamedValueSpec[T]", raw)
        return named.names, named.rest
    if isinstance(raw, Mapping):
        return cast("Mapping[str, T]", raw), None
    return {}, cast("T | tuple[T, ...]", raw)


def _spread[T](
    rest: "T | tuple[T, ...] | None", series: Sequence[str], *, path: str
) -> dict[str, T]:
    """Give each series its value from a scalar or a list; nothing for None."""
    raw: object = rest
    if raw is None:
        return {}
    if isinstance(raw, tuple):
        items = cast("tuple[T, ...]", raw)
        if not items:
            raise ValueError(
                f"{path}: the list is empty, so no series gets a value.\n"
                "Give at least one value."
            )
        return {name: items[index % len(items)] for index, name in enumerate(series)}
    one = cast("T", raw)
    return dict.fromkeys(series, one)


def _check_series(series: Sequence[str], *, legend: bool) -> None:
    """Raise when a chart without a legend is given other than one series."""
    if not legend and len(series) != 1:
        listing = ", ".join(map(repr, series)) or "none"
        raise ValueError(
            f"A chart without a legend has exactly one series; got "
            f"{len(series)}: {listing}."
        )


def _check_names(
    names: Mapping[str, object], valid: Sequence[str], *, path: str, legend: bool
) -> None:
    """Raise when a dict names a series or category that does not exist."""
    unknown = [name for name in names if name not in valid]
    if not unknown:
        return
    kind = "series" if legend else "categories"
    listing = ", ".join(map(repr, valid))
    if len(unknown) == 1:
        lines = [f"Unknown name in {path}: {unknown[0]!r}."]
    else:
        lines = [f"Unknown names in {path}: {', '.join(map(repr, unknown))}."]
    lines.append(f"Valid {kind}: {listing}.")
    if len(unknown) == 1:
        suggestion = _suggest(unknown[0], valid)
        if suggestion is not None:
            lines.append(f"Did you mean {suggestion!r}?")
    raise ValueError("\n".join(lines))


def _missing_message(path: str, missing: Sequence[str], *, legend: bool) -> str:
    """Write the message for names a dict leaves without a value."""
    kind = "series" if legend else "categories"
    return (
        f"No value for some {kind} in {path}: {', '.join(map(repr, missing))}.\n"
        f"Name them in the dict, or set one value or a list for every {kind} "
        "in an earlier call or a theme."
    )


def _whole_line_message(path: str) -> str:
    """Write the message for a dict on a per-line setting without a legend."""
    parts = path.split(".")
    noun, example = _WHOLE_LINE_WORDS.get(parts[-1], ("value", '"red"'))
    subject = "an area" if len(parts) > 1 and parts[-2] == "area" else "a line"
    return (
        f"{path}: {subject} has one {noun} along its whole length, so it "
        "cannot be set per category.\n"
        "This chart has no legend, so it has one line.\n"
        f"Give one value, such as {example}."
    )


def _suggest(word: str, candidates: Sequence[str]) -> str | None:
    """Return the candidate closest to a word, ignoring case, or None."""
    by_folded = {candidate.casefold(): candidate for candidate in candidates}
    matches = get_close_matches(word.casefold(), list(by_folded), n=1)
    return by_folded[matches[0]] if matches else None
