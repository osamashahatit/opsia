"""Mechanical checks for the class naming convention (spec §9.1).

Every class defined inside ``opsia`` must end in one of the eight role
suffixes, be private, or be an exception or warning. Roles with a rule
that can be read off the class itself are checked here. Roles whose rule
is about behaviour ("never loops", "never mutates") are not.

Classes that Pydantic builds for a parametrized generic, such as
``NamedValueSpec[str]``, are skipped: they are not written in the source,
and their names end in a bracket, not a role suffix.
"""

import importlib
import inspect
import pkgutil
from collections import Counter
from types import ModuleType

import pytest
from pydantic import BaseModel

import opsia
from opsia.spec import NamedValueSpec

ROLE_SUFFIXES = (
    "Branch",
    "Recorder",
    "Spec",
    "Renderer",
    "Styler",
    "Yielder",
    "Helper",
    "Data",
)

SUBPACKAGES = ("spec", "format", "render", "theme", "data", "page", "measures")


def _modules() -> list[ModuleType]:
    """Import and return opsia and every module inside it."""
    found = [opsia]
    for info in pkgutil.walk_packages(opsia.__path__, prefix="opsia."):
        found.append(importlib.import_module(info.name))
    return found


def _nested(cls: type) -> list[type]:
    """Return classes defined inside cls, at any depth."""
    found: list[type] = []
    for value in vars(cls).values():
        if inspect.isclass(value) and value.__qualname__.startswith(
            f"{cls.__qualname__}."
        ):
            found.append(value)
            found.extend(_nested(value))
    return found


def _is_parametrized(cls: type) -> bool:
    """Say whether Pydantic built cls for a parametrized generic, such as X[str]."""
    if not issubclass(cls, BaseModel):
        return False
    return cls.__pydantic_generic_metadata__["origin"] is not None


def _classes() -> list[type]:
    """Return every class written in opsia's source.

    Names imported from elsewhere are skipped, and so are the classes
    Pydantic builds for a parametrized generic. Pydantic puts one of those
    into a module's namespace when the generic is parametrized at module
    level, for example by an unquoted ``NamedValueSpec[str]`` annotation.
    """
    found: list[type] = []
    for module in _modules():
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ == module.__name__ and not _is_parametrized(cls):
                found.append(cls)
                found.extend(_nested(cls))
    return found


def _where(cls: type) -> str:
    """Return the full dotted path of a class, for error messages."""
    return f"{cls.__module__}.{cls.__qualname__}"


def _lacks_role(cls: type) -> bool:
    """Say whether a class breaks the suffix rule.

    Private classes and exceptions or warnings are exempt.
    """
    if cls.__name__.startswith("_") or cls.__name__.endswith(ROLE_SUFFIXES):
        return False
    return not issubclass(cls, BaseException)


def _spec_problems(cls: type) -> list[str]:
    """List the ways a Spec class breaks its rule; empty if it follows it."""
    where = _where(cls)
    if not issubclass(cls, BaseModel):
        return [f"{where} (not a Pydantic BaseModel)"]
    problems: list[str] = []
    if cls.model_config.get("frozen") is not True:
        problems.append(f"{where} (not frozen)")
    if cls.model_config.get("extra") != "forbid":
        problems.append(f"{where} (extra keys not forbidden)")
    return problems


def test_walker_sees_every_subpackage() -> None:
    """The walker imports all seven subpackages, so no check passes by accident."""
    names = {module.__name__ for module in _modules()}
    missing = [name for name in SUBPACKAGES if f"opsia.{name}" not in names]
    assert not missing, f"The class walker did not import: {missing}"


def test_walker_skips_parametrized_generics(monkeypatch: pytest.MonkeyPatch) -> None:
    """A class Pydantic built for NamedValueSpec[int] is skipped; the generic is not.

    The parametrized class is placed in the types module the way Pydantic
    places it when ``NamedValueSpec[int]`` is written at module level.
    """
    parametrized = NamedValueSpec[int]
    module = importlib.import_module(NamedValueSpec.__module__)
    monkeypatch.setattr(module, parametrized.__name__, parametrized, raising=False)
    classes = _classes()
    assert parametrized not in classes
    assert NamedValueSpec in classes


def test_every_class_has_a_role_suffix() -> None:
    """Every public class ends in one of the eight role suffixes."""
    offenders = [_where(cls) for cls in _classes() if _lacks_role(cls)]
    assert not offenders, (
        f"Classes without a role suffix: {offenders}. "
        f"Rename each to end in one of {list(ROLE_SUFFIXES)}, "
        "make it private with a leading underscore, "
        "or make it an Exception or Warning subclass."
    )


def test_branch_classes_have_no_set() -> None:
    """A Branch hands out children and never records, so it has no set."""
    offenders = [
        _where(cls)
        for cls in _classes()
        if cls.__name__.endswith("Branch") and hasattr(cls, "set")
    ]
    assert not offenders, (
        f"Branch classes with a 'set' attribute: {offenders}. "
        "A Branch only hands out children; move 'set' to a Recorder."
    )


def test_spec_classes_are_frozen_closed_models() -> None:
    """Every Spec is a Pydantic model with frozen=True and extra="forbid"."""
    offenders = [
        problem
        for cls in _classes()
        if cls.__name__.endswith("Spec")
        for problem in _spec_problems(cls)
    ]
    assert not offenders, (
        f"Spec classes that break the rule: {offenders}. "
        "Inherit from BaseSpec in opsia.spec.core._types, which sets "
        'model_config = ConfigDict(frozen=True, extra="forbid").'
    )


def test_spec_rule_catches_each_problem() -> None:
    """The Spec check itself reports a plain class and an open, mutable model."""

    class LooseSpec(BaseModel):
        """A model with neither frozen=True nor extra="forbid"."""

    problems = _spec_problems(LooseSpec)
    assert len(problems) == 2, problems
    assert problems[0].endswith("LooseSpec (not frozen)")
    assert problems[1].endswith("LooseSpec (extra keys not forbidden)")
    assert _spec_problems(int) == ["builtins.int (not a Pydantic BaseModel)"]


def test_class_names_are_unique() -> None:
    """No two classes anywhere in opsia share a name."""
    classes = _classes()
    counts = Counter(cls.__name__ for cls in classes)
    duplicates = {
        name: [_where(cls) for cls in classes if cls.__name__ == name]
        for name, count in counts.items()
        if count > 1
    }
    assert not duplicates, (
        f"Class names used more than once: {duplicates}. "
        "Give each a more specific subject, e.g. LegendMarkerStyler "
        "and LineMarkerStyler rather than two MarkerStylers."
    )
