"""Opsia: presentation-grade charts in Python.

The public API is not built yet. This package currently exposes only its
version.

Examples
--------
>>> import opsia as op
>>> isinstance(op.__version__, str)
True
"""

from importlib.metadata import version

__all__: list[str] = []

__version__: str = version("opsia")
