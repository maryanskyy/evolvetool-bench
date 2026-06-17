"""Documentation gates for canonical results layout."""
from __future__ import annotations

from pathlib import Path


def test_canonical_manifests_acknowledged():
    readme = Path(__file__).resolve().parents[1] / "results_canonical" / "README.md"
    assert readme.is_file(), "results_canonical/README.md must exist"
    text = readme.read_text(encoding="utf-8")
    assert "run_manifest" in text, (
        "results_canonical/README.md must document run_manifest schema"
    )
