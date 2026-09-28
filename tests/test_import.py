"""The package imports and reports its version."""

import opsia


def test_import_exposes_version_string() -> None:
    """The package imports, and its version is a string read from package metadata."""
    assert isinstance(opsia.__version__, str)
