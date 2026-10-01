"""The shape of the spec tree: empty by default, frozen, and free of Matplotlib."""

import ast
import doctest
import importlib
import inspect
import pkgutil
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

import opsia.spec
from opsia.spec import (
    AxisSpec,
    AxisSpineSpec,
    AxisTickSpec,
    BarLayoutSpec,
    BarsSpec,
    ChartSpec,
    DataAxisSpec,
    LegendLayoutSpec,
    LegendSpec,
    LineMarkerSpec,
    LinesSpec,
    NumericSpec,
    SpineSideSpec,
    TickMajorSpec,
    TickMinorSpec,
    TickTextSpec,
)

from .walker import is_node, leaves, spec_classes, walk


def _spec_modules() -> list[str]:
    """Return the dotted name of opsia.spec and every module inside it."""
    names = [opsia.spec.__name__]
    for info in pkgutil.walk_packages(opsia.spec.__path__, prefix="opsia.spec."):
        names.append(info.name)
    return names


def test_schema_extra_is_only_the_value_mapped_flag() -> None:
    """A leaf's json_schema_extra is absent or exactly the value_mapped flag."""
    offenders = [
        f"{item.path}: {item.info.json_schema_extra!r}"
        for item in leaves(ChartSpec())
        if item.info.json_schema_extra not in (None, {"value_mapped": True})
    ]
    assert not offenders, f"Unexpected json_schema_extra: {offenders}"


def test_every_field_defaults_to_none_or_a_child() -> None:
    """A leaf defaults to None (not set, §5.4); a child to an empty spec."""
    offenders: list[str] = []
    for item in walk(ChartSpec()):
        has_factory = item.info.default_factory is not None
        if is_node(item.value) != has_factory:
            offenders.append(f"{item.path} (node and factory disagree)")
        elif not has_factory and item.info.default is not None:
            offenders.append(f"{item.path} (default {item.info.default!r})")
    assert not offenders, f"Fields with the wrong default: {offenders}"


def test_spines_are_stored_per_side() -> None:
    """The spine node has exactly the four screen sides (§4.12)."""
    assert list(AxisSpineSpec.model_fields) == ["top", "bottom", "left", "right"]


def test_minor_ticks_have_a_marker_only() -> None:
    """Minor ticks hold a marker and no text; major ticks hold both (§4.16 #10)."""
    assert list(TickMinorSpec.model_fields) == ["marker"]
    assert list(TickMajorSpec.model_fields) == ["text", "marker"]


def test_every_field_is_frozen() -> None:
    """Assigning to any field of any node raises a ValidationError."""
    checked = 0
    for item in walk(ChartSpec()):
        with pytest.raises(ValidationError):
            setattr(item.node, item.name, item.value)
        checked += 1
    assert checked > 400, f"Only {checked} fields were walked."


def test_hand_built_spec_reads_back_by_path() -> None:
    """Deep values set by hand are read back through their dotted paths."""
    spec = ChartSpec(
        axis=AxisSpec(
            y=DataAxisSpec(
                tick=AxisTickSpec(
                    major=TickMajorSpec(
                        text=TickTextSpec(
                            size=10,
                            numeric=NumericSpec(display_units="k", currency="$"),
                        )
                    )
                )
            ),
            spine=AxisSpineSpec(top=SpineSideSpec(show=False)),
        ),
        legend=LegendSpec(layout=LegendLayoutSpec(position="upper right")),
        bars=BarsSpec(layout=BarLayoutSpec(stack_gap=0.02)),
        lines=LinesSpec(marker=LineMarkerSpec(shape=("o", "s"))),
    )
    assert spec.axis.spine.top.show is False
    assert spec.axis.spine.right.show is None
    assert spec.bars.layout.stack_gap == 0.02
    assert spec.axis.y.tick.major.text.size == 10
    assert spec.axis.y.tick.major.text.numeric.display_units == "k"
    assert spec.axis.y.tick.major.text.numeric.currency == "$"
    assert spec.axis.x.tick.major.text.size is None
    assert spec.legend.layout.position == "upper right"
    assert spec.lines.marker.shape == ("o", "s")


def test_no_spec_module_imports_matplotlib_at_runtime() -> None:
    """Importing every spec module in a fresh interpreter loads no Matplotlib."""
    modules = ", ".join(_spec_modules())
    code = (
        f"import importlib, sys\n"
        f"for name in '{modules}'.split(', '):\n"
        f"    importlib.import_module(name)\n"
        f"loaded = sorted(m for m in sys.modules if m.split('.')[0] == 'matplotlib')\n"
        f"print(loaded)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "[]", f"Matplotlib was loaded: {result.stdout}"


def test_no_spec_source_names_matplotlib_in_an_import() -> None:
    """No import statement in any spec source file mentions matplotlib."""
    offenders: list[str] = []
    for path in Path(opsia.spec.__file__).parent.rglob("*.py"):
        for statement in ast.walk(ast.parse(path.read_text())):
            if isinstance(statement, ast.Import):
                names = [alias.name for alias in statement.names]
            elif isinstance(statement, ast.ImportFrom):
                names = [statement.module or ""]
            else:
                continue
            if any(name.split(".")[0] == "matplotlib" for name in names):
                offenders.append(f"{path.name}:{statement.lineno}")
    assert not offenders, f"Matplotlib imported under opsia.spec at: {offenders}"


@pytest.mark.parametrize("name", _spec_modules())
def test_docstring_examples_run(name: str) -> None:
    """Every Examples section in the spec modules runs and prints what it shows."""
    module = importlib.import_module(name)
    result = doctest.testmod(module, optionflags=doctest.ELLIPSIS)
    assert result.failed == 0, f"{result.failed} docstring example(s) failed in {name}"


def test_every_spec_class_has_an_examples_section() -> None:
    """Every class in opsia.spec has a NumPy Examples section (§9.4).

    The docstring is cleaned first: Python 3.13 and later strip docstring
    indentation at compile time, while 3.12 keeps it, so the raw text
    differs between the versions CI runs.
    """
    offenders = [
        cls.__name__
        for cls in spec_classes()
        if "\nExamples\n--------\n" not in inspect.cleandoc(cls.__doc__ or "")
    ]
    assert not offenders, f"Classes without an Examples section: {offenders}"
