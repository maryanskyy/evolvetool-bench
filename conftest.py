"""Pytest bootstrap: make the ``src/`` layout importable without an editable install.

The package lives under ``src/evolvetool_bench`` (see ``pyproject.toml``). Adding
``src`` to ``sys.path`` here lets ``pytest tests/`` run directly from a clean
checkout, matching the import style used across the test suite.
"""

import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
