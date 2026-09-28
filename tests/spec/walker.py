"""Walk the spec tree, so tests never hard-code paths."""

import importlib
import inspect
import pkgutil
from collections.abc import Iterator
from typing import NamedTuple

from pydantic import BaseModel
from pydantic.fields import FieldInfo

import opsia.spec
from opsia.spec import ChartSpec


class SpecField(NamedTuple):
    """One field met while walking: where it is, what holds it, and its value."""

    path: str
    node: BaseModel
    name: str
    info: FieldInfo
    value: object


def is_node(value: object) -> bool:
    """Say whether a value is a spec node (a model instance) rather than a leaf."""
    return isinstance(value, BaseModel)


def is_value_mapped(info: FieldInfo) -> bool:
    """Say whether a field is marked as one of the value-mapped properties (§4.8)."""
    extra = info.json_schema_extra
    if extra is None or callable(extra):
        return False
    return extra.get("value_mapped") is True


def walk(node: BaseModel, prefix: str = "") -> Iterator[SpecField]:
    """Yield every field under node, depth first.

    Fields are read from the class's ``model_fields``, in declaration order.
    Child nodes are yielded before their own fields.
    """
    for name, info in type(node).model_fields.items():
        value: object = getattr(node, name)
        path = f"{prefix}{name}"
        yield SpecField(path, node, name, info, value)
        if isinstance(value, BaseModel):
            yield from walk(value, f"{path}.")


def leaves(node: BaseModel) -> Iterator[SpecField]:
    """Yield only the leaf fields under node."""
    return (item for item in walk(node) if not is_node(item.value))


def spec_classes() -> list[type]:
    """Return every class defined in any module of opsia.spec."""
    found: list[type] = []
    for info in pkgutil.walk_packages(opsia.spec.__path__, prefix="opsia.spec."):
        module = importlib.import_module(info.name)
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ == module.__name__:
                found.append(cls)
    return found


def tree() -> ChartSpec:
    """Return a bare root spec."""
    return ChartSpec()
