"""Change one node of a frozen spec tree and get a new tree back (§3.5.2).

Specs are frozen, so a recorder never edits one. ``replace_at`` builds a new
tree instead: it re-validates the changed node with ``model_validate``, then
rebuilds each node above it on the way back to the root. Every branch off
that path is passed in as the existing object, so it is shared, not copied.

A dict given for a value-mapped setting fills in over the value already
stored, by the same rule ``merge_layers`` uses (``layer_value``, §4.8).

Whether a field is a child node or a setting is read from its annotation,
never from the stored value: a NamedValueSpec stored in a setting is a spec
object, but not a node.

``model_copy(update=...)`` and ``model_construct`` are not used: both skip
validation (§9.3.1 rule 1).
"""

from pydantic import ValidationError

from opsia.spec.core._errors import (
    build_node_value_block,
    build_setting_path_block,
    build_spec_error,
    build_unknown_key_block,
    build_value_error,
    get_node_class,
)
from opsia.spec.core._merge import layer_value
from opsia.spec.core._types import BaseSpec, is_value_mapped


def replace_at[S: BaseSpec](spec: S, path: str, **changes: object) -> S:
    """Return a new spec with some settings of one node changed.

    A change whose value is None is skipped, because None means "not set"
    (§5.4): a recorder passes every argument, and a later call must not erase
    what an earlier call set. When every change is None, the same spec object
    is returned. The path and every change name are checked even then.

    A dict given for a value-mapped setting fills in over the value already
    stored: the names it gives win, and every other name keeps the stored
    value (§4.8). A scalar or a list replaces the stored value whole, and so
    does any value for a setting that is not value-mapped.

    Only the nodes along ``path`` are rebuilt. Every other branch, and the
    changed node's own child nodes, are the same objects as in ``spec``, and
    ``spec`` itself is never changed.

    Parameters
    ----------
    spec
        The spec to start from, usually the root ``ChartSpec``.
    path
        The dotted path of a node from the root of ``spec``, such as
        ``"bars.fill"``.
    **changes
        New values for settings of that node, by setting name. A list is
        stored as a tuple and a dict as a read-only mapping.

    Returns
    -------
        A new spec of the same class with the changes applied, or ``spec``
        itself when every change is None.

    Raises
    ------
    ValueError
        The path names no node, a change names no setting of the node or
        names a child node, or a value is not valid for its setting. The
        message names the full dotted path and lists the valid options.

    Examples
    --------
    >>> from opsia.spec import ChartSpec
    >>> spec = ChartSpec()
    >>> new = replace_at(spec, "bars.fill", color="#E24A33", alpha=None)
    >>> new.bars.fill.color, spec.bars.fill.color
    ('#E24A33', None)
    >>> new.legend is spec.legend
    True
    >>> replace_at(new, "bars.fill", color=None) is new
    True
    >>> palette = replace_at(spec, "bars.fill", color=["#4C72B0", "#DD8452"])
    >>> color = replace_at(palette, "bars.fill", color={"2019": "#E24A33"}).bars.fill.color
    >>> color.names["2019"], color.rest
    ('#E24A33', ('#4C72B0', '#DD8452'))
    >>> replace_at(spec, "bars.fill", colour="#E24A33")
    Traceback (most recent call last):
    ...
    ValueError: Unknown setting: bars.fill.colour.
    Valid settings for bars.fill: alpha, color, max_alpha, max_color, min_alpha, min_color.
    Did you mean 'color'?
    """
    names = _split_path(path)
    chain = _walk(spec, names)
    target = chain[-1]
    _check_change_names(target, path, changes)
    given = {name: value for name, value in changes.items() if value is not None}
    if not given:
        return spec
    new: BaseSpec = _rebuild(target, given, prefix=path)
    layered = _layer_over(target, new, given)
    if layered:
        new = _rebuild(new, layered, prefix=path)
    for depth in range(len(names) - 1, 0, -1):
        prefix = ".".join(names[:depth])
        new = _rebuild(chain[depth], {names[depth]: new}, prefix=prefix)
    return _rebuild(spec, {names[0]: new}, prefix="")


def _split_path(path: str) -> list[str]:
    """Split a dotted path into node names, rejecting empty parts."""
    names = path.split(".")
    if not all(names):
        raise ValueError(
            f"Invalid path: {path!r}. A path is node names joined by dots, "
            "such as 'bars.fill'."
        )
    return names


def _walk(spec: BaseSpec, names: list[str]) -> list[BaseSpec]:
    """Return the nodes along a path, from the root to the named node."""
    chain = [spec]
    node_path = ""
    for name in names:
        current = chain[-1]
        info = type(current).model_fields.get(name)
        if info is None:
            block = build_unknown_key_block(
                type(current), node_path, name, expected="node"
            )
            raise build_value_error([block])
        child: object = getattr(current, name)
        if get_node_class(info) is None or not isinstance(child, BaseSpec):
            raise build_value_error([build_setting_path_block(node_path, name)])
        chain.append(child)
        node_path = f"{node_path}.{name}" if node_path else name
    return chain


def _check_change_names(
    target: BaseSpec, path: str, changes: dict[str, object]
) -> None:
    """Raise one error listing every change name that is not a setting."""
    fields = type(target).model_fields
    blocks: list[str] = []
    for name in changes:
        info = fields.get(name)
        if info is None:
            blocks.append(
                build_unknown_key_block(type(target), path, name, expected="setting")
            )
            continue
        node = get_node_class(info)
        if node is not None:
            blocks.append(build_node_value_block(node, f"{path}.{name}"))
    if blocks:
        raise build_value_error(blocks)


def _layer_over(
    old: BaseSpec, new: BaseSpec, given: dict[str, object]
) -> dict[str, object]:
    """Return the value-mapped changes that must fill in over the old values.

    ``new`` already holds the given values, validated on their own, so a
    mistake in them was reported exactly as it would be without layering.
    Only the settings whose layered value differs from that are returned.
    """
    fields = type(old).model_fields
    layered: dict[str, object] = {}
    for name in given:
        if not is_value_mapped(fields[name]):
            continue
        above: object = getattr(new, name)
        value = layer_value(above=above, below=getattr(old, name))
        if value is not above:
            layered[name] = value
    return layered


def _rebuild[N: BaseSpec](node: N, changes: dict[str, object], *, prefix: str) -> N:
    """Validate a new node from an existing one plus changes.

    Every field is passed in, so unchanged child nodes are handed over as the
    existing objects and kept as they are (Pydantic's default
    ``revalidate_instances="never"``).
    """
    data: dict[str, object] = {
        name: getattr(node, name) for name in type(node).model_fields
    }
    data.update(changes)
    try:
        return type(node).model_validate(data)
    except ValidationError as err:
        raise build_spec_error(err, node=type(node), prefix=prefix) from err
