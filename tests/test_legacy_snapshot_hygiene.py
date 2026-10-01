# Copyright 2026 Aaron John Schlosser, PhD.
"""Keep the legacy DOM snapshot directory tied to active characterization scenarios."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "web" / "tests" / "e2e" / "legacy-dom-baseline.spec.ts"
SNAPSHOTS = Path(f"{SPEC}-snapshots")


def _scenario_names(source: str) -> tuple[set[str], set[str]]:
    literal = set(re.findall(r'name:\s*["\']([^"\']+)["\']', source))
    dynamic_prefixes = set(re.findall(r"name:\s*\`([^\`$]+)\$\{", source))
    return literal, dynamic_prefixes


def _snapshot_scenario_name(path: Path) -> str:
    name = path.stem
    return re.sub(r"-chromium-[^-]+-[^-]+$", "", name)


def test_legacy_snapshots_are_referenced_by_active_scenarios() -> None:
    source = SPEC.read_text(encoding="utf-8")
    literal, prefixes = _scenario_names(source)
    unreferenced: list[str] = []

    for path in sorted(SNAPSHOTS.iterdir()):
        if not path.is_file():
            continue
        assert path.suffix == ".html", (
            f"{path.relative_to(ROOT)} is a non-DOM legacy snapshot. "
            "Computed-style baselines are intentionally retired."
        )
        scenario = _snapshot_scenario_name(path)
        if scenario in literal or any(scenario.startswith(prefix) for prefix in prefixes):
            continue
        unreferenced.append(path.name)

    assert unreferenced == [], (
        "Legacy snapshots without an active scenario: " + ", ".join(unreferenced)
    )
