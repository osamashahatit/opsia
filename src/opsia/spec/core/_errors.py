"""Turn spec validation failures into one readable ValueError (§9.6).

Pydantic reports one mistake in a ``Value[T]`` field once per union form, and
puts union tags such as ``tuple[...]`` into each error's ``loc``. This module
finds the dotted path of each error by walking its ``loc`` against
``model_fields``, groups the errors by path, and writes one block per path
(§9.3.1 rule 2).

What a field accepts is read from its type annotation, never from Pydantic's
message text, so the options a message lists are the ``Literal`` members
themselves and cannot drift from the spec. The ``NamedValueSpec`` form of
``Value`` adds nothing to a message: only Opsia builds one, so it is never
something to tell the user to give.

``build_spec_error`` handles a ``ValidationError``. The ``build_*_block``
functions write the same kinds of block for mistakes found without Pydantic,
such as a bad path given to ``replace_at``, and ``build_value_error`` joins
blocks into one error. ``get_node_class`` and ``compute_suggestion`` are
shared with ``replace_at`` and the resolver, so each rule lives in one place.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from difflib import get_close_matches
from types import NoneType, UnionType
from typing import (
    Annotated,
    Literal,
    TypeAliasType,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
)

from pydantic import ValidationError
from pydantic.fields import FieldInfo

from opsia.spec.core._types import BaseSpec, NamedValueSpec, is_value_mapped

_TYPES_MODULE = BaseSpec.__module__
"""The module whose aliases get their own wording in messages."""

_ALIAS_KINDS = {"Color": "colour", "FontName": "font"}
"""Aliases of plain ``str`` that deserve a clearer word than "text"."""

_PLAIN_KINDS: dict[type, str] = {
    bool: "flag",
    int: "whole number",
    float: "number",
    str: "text",
}
"""The kind of value each plain Python type stands for."""

_TEXT_KINDS = frozenset({"colour", "font", "text"})
"""Kinds whose values are strings."""

_ONE = {
    "number": "a number, such as 0.8",
    "whole number": "a whole number, such as 2",
    "flag": "True or False (true or false in a theme file)",
    "colour": "a colour name or hex code, such as '#4C72B0'",
    "font": "a font role or family name, such as 'body'",
    "text": "text",
}
"""How one value of each kind is described after "Expected"."""

_MANY = {
    "number": "numbers",
    "whole number": "whole numbers",
    "flag": "True or False values",
    "colour": "colours",
    "font": "font names",
    "text": "text values",
}
"""How several values of each kind are described, as in "a list of numbers"."""

_NOUN = {
    "number": "number",
    "whole number": "whole number",
    "flag": "flag",
    "colour": "colour",
    "font": "font name",
    "text": "value",
}
"""The noun for one value of each kind, as in "Give one number"."""


@dataclass(frozen=True, slots=True)
class _Accepted:
    """What a field, or one item inside it, accepts, read from its annotation.

    Examples
    --------
    >>> _read_accepted(float | None, {}).kinds
    ('number',)
    >>> _read_accepted(Literal["solid", "dashed"], {}).options
    ('solid', 'dashed')
    >>> _read_accepted(tuple[str, ...], {}).item
    _Accepted(kinds=('text',), options=(), item=None, by_name=None)
    """

    kinds: tuple[str, ...] = ()
    options: tuple[str, ...] = ()
    item: "_Accepted | None" = None
    by_name: "_Accepted | None" = None


@dataclass(frozen=True, slots=True)
class _Located:
    """Where one Pydantic error points, found by walking its loc.

    Examples
    --------
    >>> from opsia.spec import ChartSpec
    >>> located = _locate(("bars", "fill", "colour"), 1, node=ChartSpec, prefix="")
    >>> located.node_path, located.name, located.path
    ('bars.fill', 'colour', 'bars.fill.colour')
    >>> located.info is None
    True
    """

    node: type[BaseSpec]
    node_path: str
    name: str
    info: FieldInfo | None
    tail: tuple[int | str, ...]
    value: object

    @property
    def path(self) -> str:
        """The full dotted path the error points at."""
        return _join(self.node_path, self.name)


def build_spec_error(
    err: ValidationError, *, node: type[BaseSpec], prefix: str = ""
) -> ValueError:
    """Turn a Pydantic validation error into one readable ValueError.

    Every error is traced to the dotted path of the setting or node it
    concerns, and each path gets one block, however many union forms
    Pydantic tried. Raise the result with ``raise ... from err`` so the
    original error stays attached as the cause.

    Parameters
    ----------
    err
        The error raised by ``node.model_validate``.
    node
        The spec class that was validated.
    prefix
        The dotted path of ``node`` from the root, so that messages name the
        full path. Empty when ``node`` is the root.

    Returns
    -------
        The error to raise, with one block per path, or a count line
        followed by the blocks when more than one path is wrong.

    Examples
    --------
    >>> from opsia.spec import BarBorderSpec
    >>> try:
    ...     BarBorderSpec.model_validate({"style": "dashd"})
    ... except ValidationError as err:
    ...     print(build_spec_error(err, node=BarBorderSpec, prefix="bars.border"))
    Invalid value for bars.border.style: 'dashd'.
    Valid options: 'solid', 'dashed', 'dashdot', 'dotted', 'none'.
    Did you mean 'dashed'?
    """
    groups: dict[str, list[_Located]] = {}
    for error in err.errors():
        located = _locate(error["loc"], error["input"], node=node, prefix=prefix)
        groups.setdefault(located.path, []).append(located)
    return build_value_error([_build_block(items) for items in groups.values()])


def build_value_error(blocks: Sequence[str]) -> ValueError:
    """Join message blocks into one ValueError.

    Parameters
    ----------
    blocks
        One block per wrong path, in the order the paths were found.

    Returns
    -------
        The error to raise. With more than one block, a line counting the
        problems comes first and a blank line separates the blocks.

    Raises
    ------
    ValueError
        ``blocks`` is empty; there is no problem to report.

    Examples
    --------
    >>> print(build_value_error(["First problem.", "Second problem."]))
    2 problems found.
    <BLANKLINE>
    First problem.
    <BLANKLINE>
    Second problem.
    """
    if not blocks:
        raise ValueError("build_value_error needs at least one block.")
    if len(blocks) == 1:
        return ValueError(blocks[0])
    return ValueError("\n\n".join([f"{len(blocks)} problems found.", *blocks]))


def build_unknown_key_block(
    node: type[BaseSpec],
    node_path: str,
    key: str,
    *,
    expected: Literal["setting", "node"],
) -> str:
    """Write the block for a name that a spec node does not define.

    Parameters
    ----------
    node
        The spec class the name was looked up in.
    node_path
        The dotted path of ``node``; empty for the root.
    key
        The name that was not found.
    expected
        Whether the name was used as a setting or as a node, which decides
        the wording and what is listed first.

    Returns
    -------
        The block, listing the valid names and a close match when there is
        one.

    Examples
    --------
    >>> from opsia.spec import BarFillSpec, BarsSpec
    >>> print(build_unknown_key_block(BarFillSpec, "bars.fill", "colour",
    ...                               expected="setting"))
    Unknown setting: bars.fill.colour.
    Valid settings for bars.fill: alpha, color, max_alpha, max_color, min_alpha, min_color.
    Did you mean 'color'?
    >>> print(build_unknown_key_block(BarsSpec, "bars", "fil", expected="node"))
    Unknown node: bars.fil.
    Valid nodes under bars: border, fill, label, layout.
    Did you mean 'fill'?
    """
    settings, nodes = _names_of(node)
    if expected == "setting":
        lines = [
            f"Unknown setting: {_join(node_path, key)}.",
            _settings_line(node_path, settings),
        ]
        if nodes:
            lines.append(f"Nodes under {node_path}: {', '.join(nodes)}.")
    else:
        lines = [
            f"Unknown node: {_join(node_path, key)}.",
            _nodes_line(node_path, nodes),
        ]
        if not nodes:
            lines.append(_settings_line(node_path, settings))
    suggestion = compute_suggestion(key, [*settings, *nodes])
    if suggestion is not None:
        lines.append(f"Did you mean {suggestion!r}?")
    return "\n".join(lines)


def build_node_value_block(node: type[BaseSpec], path: str) -> str:
    """Write the block for a node that was given a value, as if it were a setting.

    Parameters
    ----------
    node
        The spec class of the node that was given a value.
    path
        The dotted path of that node.

    Returns
    -------
        The block, listing what the node holds instead.

    Examples
    --------
    >>> from opsia.spec import BarFillSpec
    >>> print(build_node_value_block(BarFillSpec, "bars.fill"))
    bars.fill is a node, not a setting.
    Valid settings for bars.fill: alpha, color, max_alpha, max_color, min_alpha, min_color.
    """
    settings, nodes = _names_of(node)
    listing = _settings_line(path, settings) if settings else _nodes_line(path, nodes)
    return f"{path} is a node, not a setting.\n{listing}"


def build_setting_path_block(node_path: str, name: str) -> str:
    """Write the block for a path that ends at a setting instead of a node.

    Parameters
    ----------
    node_path
        The dotted path of the node that holds the setting.
    name
        The setting the path went on to.

    Returns
    -------
        The block, showing how to pass the setting as a change instead.

    Examples
    --------
    >>> print(build_setting_path_block("bars.fill", "color"))
    bars.fill.color is a setting, not a node.
    Pass it as a change on its node: replace_at(spec, "bars.fill", color=...).
    """
    return (
        f"{_join(node_path, name)} is a setting, not a node.\n"
        f'Pass it as a change on its node: replace_at(spec, "{node_path}", '
        f"{name}=...)."
    )


def _locate(
    loc: tuple[int | str, ...], value: object, *, node: type[BaseSpec], prefix: str
) -> _Located:
    """Walk an error's loc through model_fields until it leaves the spec tree."""
    current = node
    node_path = prefix
    for position, part in enumerate(loc):
        name = str(part)
        info = current.model_fields.get(name) if isinstance(part, str) else None
        child = get_node_class(info)
        rest = loc[position + 1 :]
        if info is None or child is None or not rest:
            return _Located(current, node_path, name, info, rest, value)
        current, node_path = child, _join(node_path, name)
    return _Located(current, node_path, "", None, (), value)


def _build_block(items: Sequence[_Located]) -> str:
    """Write the one block for all the errors at one path."""
    first = min(items, key=lambda item: len(item.tail))
    if first.info is None and not first.name:
        return _root_value_block(first.node_path, first.value)
    if first.info is None:
        settings, _ = _names_of(first.node)
        expected: Literal["setting", "node"] = "setting" if settings else "node"
        return build_unknown_key_block(
            first.node, first.node_path, first.name, expected=expected
        )
    child = get_node_class(first.info)
    if child is not None:
        return build_node_value_block(child, first.path)
    return _leaf_block(first, first.info, items)


def _root_value_block(path: str, value: object) -> str:
    """Write the block for a whole spec given something other than a dict."""
    where = path if path else "the top level"
    return (
        f"Invalid value for {where}: {_show(value, _Accepted())}.\n"
        "Expected a dict of settings and nodes."
    )


def _leaf_block(first: _Located, info: FieldInfo, items: Sequence[_Located]) -> str:
    """Write the block for a setting, pointing at the bad item when there is one."""
    accepted = _read_accepted(info.annotation, {})
    raw = first.value
    deeper = [item for item in items if len(item.tail) > len(first.tail)]
    mapping = _as_mapping(raw)
    if mapping is not None and accepted.by_name is not None:
        for key in mapping:
            if not isinstance(key, str):
                return _key_block(first.path, key)
        for item in deeper:
            key = item.tail[-1]
            if isinstance(key, str) and key in mapping:
                label = f"{first.path}, key {key!r}"
                return _item_block(label, item.value, accepted.by_name)
    sequence = _as_sequence(raw)
    if sequence is not None and accepted.item is not None:
        if not sequence:
            return _empty_list_block(first.path, accepted.item)
        for item in deeper:
            index = item.tail[-1]
            if isinstance(index, int) and 0 <= index < len(sequence):
                label = f"{first.path}, item {index + 1} of the list"
                return _item_block(label, item.value, accepted.item)
    if is_value_mapped(info):
        return _value_mapped_block(first.path, raw, accepted)
    return _item_block(first.path, raw, accepted)


def _empty_list_block(path: str, item: _Accepted) -> str:
    """Write the block for an empty list where at least one item is needed."""
    noun = _NOUN[item.kinds[0]] if item.kinds else "option"
    return (
        f"Invalid value for {path}: an empty list.\n"
        f"Give at least one {noun}, or leave the setting out."
    )


def _item_block(label: str, value: object, accepted: _Accepted) -> str:
    """Write the block for one wrong value: what was given and what is valid."""
    lines = [f"Invalid value for {label}: {_show(value, accepted)}."]
    lines.extend(_valid_lines(value, accepted))
    return "\n".join(lines)


def _value_mapped_block(path: str, value: object, accepted: _Accepted) -> str:
    """Write the block for one of the 19 value-mapped settings (§4.8).

    The forms line is added only when the value is the wrong kind altogether,
    such as a number where an option is expected.
    """
    one = _Accepted(kinds=accepted.kinds, options=accepted.options)
    lines = [f"Invalid value for {path}: {_show(value, one)}."]
    lines.extend(_valid_lines(value, one))
    wrong_kind = not _fits_kind(value, one)
    if wrong_kind and _as_mapping(value) is None and _as_sequence(value) is None:
        noun = _NOUN[one.kinds[0]] if one.kinds else "option"
        lines.append(
            f"Give one {noun}, a list of them (one per series), "
            "or a dict of them by series or category name."
        )
    return "\n".join(lines)


def _key_block(path: str, key: object) -> str:
    """Write the block for a dict key that is not text."""
    kind = "a number" if isinstance(key, int | float) else "not text"
    return (
        f"Invalid key for {path}: {key!r} ({kind}).\n"
        f"Names in a dict must be text. Write it in quotes: {str(key)!r}."
    )


def _valid_lines(value: object, accepted: _Accepted) -> list[str]:
    """Say what is valid, plus a close match when the value is text."""
    only_options = accepted.options and not (
        accepted.kinds or accepted.item or accepted.by_name
    )
    if only_options:
        lines = [f"Valid options: {', '.join(map(repr, accepted.options))}."]
    else:
        lines = [f"Expected {_join_or(_describe(accepted))}."]
    suggestion = compute_suggestion(value, accepted.options)
    if suggestion is not None:
        lines.append(f"Did you mean {suggestion!r}?")
    return lines


def _describe(accepted: _Accepted) -> list[str]:
    """Describe each form a value may take, one phrase per form."""
    phrases = [_ONE[kind] for kind in accepted.kinds]
    if accepted.item is not None:
        phrases.append(f"a list of {_describe_many(accepted.item)}")
    if accepted.by_name is not None:
        phrases.append(f"a dict of {_describe_many(accepted.by_name)} by name")
    phrases.extend(repr(option) for option in accepted.options)
    return phrases


def _describe_many(accepted: _Accepted) -> str:
    """Describe several values of one form, as in "a list of numbers"."""
    parts = [_MANY[kind] for kind in accepted.kinds]
    if accepted.options:
        parts.append("options")
    return " or ".join(parts)


def _read_accepted(annotation: object, bound: Mapping[object, object]) -> _Accepted:
    """Read what a type annotation accepts, following aliases and unions.

    ``bound`` maps the type parameters of an enclosing generic alias, such as
    the ``T`` of ``Value[T]``, to the types they stand for. A
    ``NamedValueSpec`` accepts nothing a user can give, so it adds nothing.
    """
    if isinstance(annotation, TypeVar):
        if annotation not in bound:
            raise TypeError(f"The type parameter {annotation!r} is not bound.")
        return _read_accepted(bound[annotation], {})
    if annotation is None or annotation is NoneType:
        return _Accepted()
    if isinstance(annotation, TypeAliasType):
        return _read_alias(annotation)
    origin = get_origin(annotation)
    args = get_args(annotation)
    if isinstance(origin, TypeAliasType):
        params = origin.__type_params__
        inner: dict[object, object] = {
            param: bound.get(arg, arg) if isinstance(arg, TypeVar) else arg
            for param, arg in zip(params, args, strict=True)
        }
        return _read_accepted(origin.__value__, inner)
    if origin is Union or origin is UnionType:
        return _combine([_read_accepted(arg, bound) for arg in args])
    if origin is Annotated:
        return _read_accepted(args[0], bound)
    if origin is Literal:
        return _Accepted(options=_literal_options(args))
    if origin is tuple:
        return _Accepted(item=_read_accepted(args[0], bound))
    if origin is Mapping:
        return _Accepted(by_name=_read_accepted(args[1], bound))
    if isinstance(annotation, type) and issubclass(annotation, NamedValueSpec):
        return _Accepted()
    if isinstance(annotation, type) and annotation in _PLAIN_KINDS:
        return _Accepted(kinds=(_PLAIN_KINDS[annotation],))
    raise TypeError(
        f"Cannot describe the type {annotation!r} in an error message. "
        f"Teach _read_accepted in {__name__} about it."
    )


def _read_alias(alias: TypeAliasType) -> _Accepted:
    """Read a non-generic alias, giving Color and FontName their own wording."""
    if alias.__module__ == _TYPES_MODULE and alias.__name__ in _ALIAS_KINDS:
        return _Accepted(kinds=(_ALIAS_KINDS[alias.__name__],))
    return _read_accepted(alias.__value__, {})


def _literal_options(args: tuple[object, ...]) -> tuple[str, ...]:
    """Return the members of a Literal, which in the spec are always strings."""
    options: list[str] = []
    for arg in args:
        if not isinstance(arg, str):
            raise TypeError(f"Literal member {arg!r} is not a string.")
        options.append(arg)
    return tuple(options)


def _combine(parts: Sequence[_Accepted]) -> _Accepted:
    """Merge what the members of a union accept."""
    kinds: list[str] = []
    options: list[str] = []
    item: _Accepted | None = None
    by_name: _Accepted | None = None
    for part in parts:
        kinds.extend(kind for kind in part.kinds if kind not in kinds)
        options.extend(option for option in part.options if option not in options)
        item = item if part.item is None else part.item
        by_name = by_name if part.by_name is None else part.by_name
    return _Accepted(tuple(kinds), tuple(options), item, by_name)


def _fits_kind(value: object, accepted: _Accepted) -> bool:
    """Say whether a value is the right kind, even if not a valid one."""
    if isinstance(value, bool):
        return "flag" in accepted.kinds
    if isinstance(value, int):
        return "whole number" in accepted.kinds or "number" in accepted.kinds
    if isinstance(value, float):
        return "number" in accepted.kinds
    if isinstance(value, str):
        return bool(accepted.options) or not _TEXT_KINDS.isdisjoint(accepted.kinds)
    return False


def _show(value: object, accepted: _Accepted) -> str:
    """Show a value as the user wrote it, marking text where no text is expected."""
    mapping = _as_mapping(value)
    shown = repr(dict(mapping)) if mapping is not None else repr(value)
    expects_other_kind = bool(accepted.kinds) or not accepted.options
    if (
        isinstance(value, str)
        and _TEXT_KINDS.isdisjoint(accepted.kinds)
        and expects_other_kind
    ):
        return f"{shown} (text)"
    return shown


def compute_suggestion(word: object, candidates: Iterable[str]) -> str | None:
    """Return the candidate closest to a text value, ignoring case, or None.

    Parameters
    ----------
    word
        The value the user gave. Anything other than text has no suggestion.
    candidates
        The valid names or options.

    Returns
    -------
        The closest candidate, spelt as in ``candidates``, or None when no
        candidate is close enough.

    Examples
    --------
    >>> compute_suggestion("colour", ["alpha", "color"])
    'color'
    >>> compute_suggestion("K", ["k", "m"])
    'k'
    >>> compute_suggestion(5, ["solid"]) is None
    True
    """
    if not isinstance(word, str):
        return None
    by_folded = {candidate.casefold(): candidate for candidate in candidates}
    matches = get_close_matches(word.casefold(), list(by_folded), n=1)
    return by_folded[matches[0]] if matches else None


def _names_of(node: type[BaseSpec]) -> tuple[list[str], list[str]]:
    """Return a node's setting names and child node names, each sorted."""
    settings: list[str] = []
    nodes: list[str] = []
    for name, info in node.model_fields.items():
        (settings if get_node_class(info) is None else nodes).append(name)
    return sorted(settings), sorted(nodes)


def _settings_line(node_path: str, settings: Sequence[str]) -> str:
    """List a node's settings."""
    listing = ", ".join(settings) if settings else "none"
    return f"Valid settings for {node_path or 'the top level'}: {listing}."


def _nodes_line(node_path: str, nodes: Sequence[str]) -> str:
    """List a node's child nodes."""
    listing = ", ".join(nodes) if nodes else "none"
    if not node_path:
        return f"Valid nodes at the top level: {listing}."
    return f"Valid nodes under {node_path}: {listing}."


def get_node_class(info: FieldInfo | None) -> type[BaseSpec] | None:
    """Return the spec class of a child node field, or None for a setting.

    The answer is read from the field's annotation, never from a stored
    value: a NamedValueSpec stored in a setting is a spec object, but the
    field holding it is a setting.

    Parameters
    ----------
    info
        The field's entry in a spec class's ``model_fields``, or None when
        the name was not found.

    Returns
    -------
        The spec class of the child node, or None when the field is a
        setting or ``info`` is None.

    Examples
    --------
    >>> from opsia.spec import BarFillSpec, BarsSpec
    >>> get_node_class(BarsSpec.model_fields["fill"]) is BarFillSpec
    True
    >>> get_node_class(BarFillSpec.model_fields["color"]) is None
    True
    """
    if info is None:
        return None
    annotation = info.annotation
    if isinstance(annotation, type) and issubclass(annotation, BaseSpec):
        return annotation
    return None


def _as_mapping(value: object) -> Mapping[object, object] | None:
    """Return the value as a mapping, or None when it is not one."""
    if isinstance(value, Mapping):
        return cast("Mapping[object, object]", value)
    return None


def _as_sequence(value: object) -> Sequence[object] | None:
    """Return the value as a list or tuple, or None when it is neither."""
    if isinstance(value, list | tuple):
        return cast("Sequence[object]", value)
    return None


def _join(*parts: str) -> str:
    """Join path parts with dots, skipping empty ones."""
    return ".".join(part for part in parts if part)


def _join_or(phrases: Sequence[str]) -> str:
    """Join phrases as "a", "a, or b" or "a, b, or c"."""
    if len(phrases) <= 1:
        return "".join(phrases)
    return f"{', '.join(phrases[:-1])}, or {phrases[-1]}"
