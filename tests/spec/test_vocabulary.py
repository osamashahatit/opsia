"""No spec name is a Python keyword, soft keyword or builtin (spec §4.16).

``format`` and ``set`` are the only builtins allowed, and only because they
always follow a dot (§9.1).
"""

import builtins
import keyword

from pydantic import BaseModel

from .walker import spec_classes

ALLOWED_BUILTINS = {"format", "set"}


def _problem(name: str) -> str | None:
    """Say why a name is not allowed, or None if it is fine."""
    if name in keyword.kwlist:
        return "is a Python keyword"
    if name in keyword.softkwlist:
        return "is a Python soft keyword"
    if name in dir(builtins) and name not in ALLOWED_BUILTINS:
        return "shadows a Python builtin"
    return None


def _field_names() -> list[tuple[str, str]]:
    """Return (class name, field name) for every field of every spec model."""
    return [
        (cls.__name__, name)
        for cls in spec_classes()
        if issubclass(cls, BaseModel)
        for name in cls.model_fields
    ]


def test_spec_classes_are_found() -> None:
    """The walker finds the spec classes, so the checks below cannot pass empty."""
    names = {cls.__name__ for cls in spec_classes()}
    assert {"ChartSpec", "NumericSpec", "LabelFrameSpec"} <= names


def test_spec_fields_are_found() -> None:
    """The field list is read from model_fields and is not empty."""
    assert ("BarFillSpec", "color") in _field_names()


def test_class_names_are_not_reserved() -> None:
    """No class in opsia.spec has a reserved name."""
    offenders = [
        f"class {cls.__module__}.{cls.__name__} {why}"
        for cls in spec_classes()
        if (why := _problem(cls.__name__)) is not None
    ]
    assert not offenders, f"Rename these classes: {offenders}"


def test_field_names_are_not_reserved() -> None:
    """No field of any spec class has a reserved name."""
    offenders = [
        f"field {field_name!r} on {class_name} {why}"
        for class_name, field_name in _field_names()
        if (why := _problem(field_name)) is not None
    ]
    assert not offenders, (
        f"Rename these fields: {offenders}. "
        f"Only {sorted(ALLOWED_BUILTINS)} may shadow a builtin."
    )


def test_checker_catches_each_kind() -> None:
    """The name check itself rejects each kind of reserved name."""
    assert _problem("class") == "is a Python keyword"
    assert _problem("match") == "is a Python soft keyword"
    assert _problem("range") == "shadows a Python builtin"
    assert _problem("format") is None
    assert _problem("color") is None
