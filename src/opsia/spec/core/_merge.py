"""Lay one spec over another, as themes and user calls do (§5.4).

Each layer sets some settings and leaves the rest as None, meaning "not
set". Merging takes each setting from the layer above when it is set there,
and from the layer below otherwise. "Set" means not None; Pydantic's
``model_fields_set`` is not used (§5.4).

The 19 value-mapped settings are the one exception to "above replaces
below": a dict above fills in over the value below instead (§4.8).
``layer_value`` holds that rule; ``replace_at`` uses it too, so a theme
layer and a ``.set()`` call combine the same way.

Where the layer above sets nothing in a subtree, the result holds the lower
layer's object for that subtree, unchanged. Every node that is rebuilt is
re-validated with ``model_validate``; ``model_copy(update=...)`` and
``model_construct`` are not used (§9.3.1 rule 1).
"""

from collections.abc import Mapping
from typing import cast

from opsia.spec.core._types import BaseSpec, NamedValueSpec, is_value_mapped


def merge_layers[S: BaseSpec](*, below: S, above: S) -> S:
    """Return one spec: ``above`` where it sets a value, ``below`` elsewhere.

    Both arguments are keyword-only, so the order of the layers is always
    written out at the call site and cannot be swapped by accident.

    A value-mapped setting combines by ``layer_value``: a dict above fills
    in over the value below, while a scalar or a list above replaces it.
    Every other setting, ``custom_values`` included, is replaced whole.

    Parameters
    ----------
    below
        The lower layer, such as the default theme.
    above
        The higher layer, such as a named theme or the user's own calls.

    Returns
    -------
        A spec of the same class with every setting of ``above`` that is not
        None, and the settings of ``below`` everywhere else. When ``above``
        sets nothing, ``below`` itself is returned.

    Examples
    --------
    >>> from opsia.spec import BarFillSpec, BarsSpec, ChartSpec
    >>> theme = ChartSpec(
    ...     bars=BarsSpec(fill=BarFillSpec(color="#4C72B0", alpha=0.6))
    ... )
    >>> user = ChartSpec(bars=BarsSpec(fill=BarFillSpec(color="#E24A33")))
    >>> merged = merge_layers(below=theme, above=user)
    >>> merged.bars.fill.color, merged.bars.fill.alpha
    ('#E24A33', 0.6)
    >>> merged.legend is theme.legend
    True
    >>> merge_layers(below=theme, above=ChartSpec()) is theme
    True
    >>> user = ChartSpec(bars=BarsSpec(fill=BarFillSpec(color={"2019": "#E24A33"})))
    >>> color = merge_layers(below=theme, above=user).bars.fill.color
    >>> color.names["2019"], color.rest
    ('#E24A33', '#4C72B0')
    """
    return _merge(below, above)


def layer_value(*, above: object, below: object) -> object:
    """Lay one value-mapped value over another (§4.8).

    ======================  ======================  ===========================
    above                   below                   result
    ======================  ======================  ===========================
    None                    anything                below
    scalar or list          anything                above
    NamedValueSpec          anything                above
    dict                    None                    above
    dict                    dict                    one dict, above wins a key
    dict                    NamedValueSpec          names filled in, same rest
    dict                    scalar or list          NamedValueSpec(above, below)
    ======================  ======================  ===========================

    A dict over a dict gives a plain dict, so a NamedValueSpec always has a
    rest, and grouping does not matter when three or more layers combine.

    Parameters
    ----------
    above
        The value of the higher layer, as stored in its spec.
    below
        The value of the lower layer, as stored in its spec.

    Returns
    -------
        The combined value, ready to be validated into the setting. It is
        ``below`` itself when ``above`` is None.

    Examples
    --------
    >>> layer_value(above={"2019": "red"}, below=("blue", "orange"))
    NamedValueSpec(names=mappingproxy({'2019': 'red'}), rest=('blue', 'orange'))
    >>> layer_value(above={"2020": "gold"}, below={"2019": "red"})
    {'2019': 'red', '2020': 'gold'}
    >>> layer_value(above="grey", below={"2019": "red"})
    'grey'
    """
    if above is None:
        return below
    names = _as_by_name(above)
    if names is None or below is None:
        return above
    lower_names = _as_by_name(below)
    if lower_names is not None:
        return {**lower_names, **names}
    named = _as_named(below)
    if named is not None:
        return NamedValueSpec(names={**named.names, **names}, rest=named.rest)
    return NamedValueSpec(names=names, rest=below)


def _merge[N: BaseSpec](below: N, above: N) -> N:
    """Merge two nodes of the same class, rebuilding only what changes.

    Value-mapped settings are checked first, by their field, so a
    NamedValueSpec stored in one is never mistaken for a child node.
    """
    if type(below) is not type(above):
        raise TypeError(
            f"Cannot merge a {type(above).__name__} over a {type(below).__name__}."
        )
    if above is below:
        return below
    changes: dict[str, object] = {}
    for name, info in type(below).model_fields.items():
        lower: object = getattr(below, name)
        upper: object = getattr(above, name)
        if is_value_mapped(info):
            value = layer_value(above=upper, below=lower)
            if value is not lower:
                changes[name] = value
        elif isinstance(lower, BaseSpec) and isinstance(upper, BaseSpec):
            merged = _merge(lower, upper)
            if merged is not lower:
                changes[name] = merged
        elif upper is not None:
            changes[name] = upper
    if not changes:
        return below
    data: dict[str, object] = {
        name: getattr(below, name) for name in type(below).model_fields
    }
    data.update(changes)
    return type(below).model_validate(data)


def _as_by_name(value: object) -> Mapping[str, object] | None:
    """Return a by-name value as a mapping, or None for any other form.

    Keys are text: validation has already checked every stored mapping.
    """
    if isinstance(value, Mapping):
        return cast("Mapping[str, object]", value)
    return None


def _as_named(value: object) -> "NamedValueSpec[object] | None":
    """Return a NamedValueSpec with its item type stated, or None.

    The ``isinstance`` check alone gives a NamedValueSpec of unknown item
    type, which strict pyright rejects. The return annotation is quoted:
    written plainly, ``NamedValueSpec[object]`` is evaluated when the module
    loads, and Pydantic builds a new class for it.
    """
    if isinstance(value, NamedValueSpec):
        return cast("NamedValueSpec[object]", value)
    return None
