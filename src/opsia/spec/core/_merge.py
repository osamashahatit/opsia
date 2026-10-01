"""Lay one spec over another, as themes and user calls do (§5.4).

Each layer sets some settings and leaves the rest as None, meaning "not
set". Merging takes each setting from the layer above when it is set there,
and from the layer below otherwise. "Set" means not None; Pydantic's
``model_fields_set`` is not used (§5.4).

Where the layer above sets nothing in a subtree, the result holds the lower
layer's object for that subtree, unchanged. Every node that is rebuilt is
re-validated with ``model_validate``; ``model_copy(update=...)`` and
``model_construct`` are not used (§9.3.1 rule 1).
"""

from opsia.spec.core._types import BaseSpec


def merge_layers[S: BaseSpec](*, below: S, above: S) -> S:
    """Return one spec: ``above`` where it sets a value, ``below`` elsewhere.

    Both arguments are keyword-only, so the order of the layers is always
    written out at the call site and cannot be swapped by accident.

    A value-mapped setting is taken whole: a dict or list in ``above``
    replaces the one in ``below``; the two are never combined key by key.

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
    """
    return _merge(below, above)


def _merge[N: BaseSpec](below: N, above: N) -> N:
    """Merge two nodes of the same class, rebuilding only what changes."""
    if type(below) is not type(above):
        raise TypeError(
            f"Cannot merge a {type(above).__name__} over a {type(below).__name__}."
        )
    if above is below:
        return below
    changes: dict[str, object] = {}
    for name in type(below).model_fields:
        lower: object = getattr(below, name)
        upper: object = getattr(above, name)
        if isinstance(lower, BaseSpec) and isinstance(upper, BaseSpec):
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
