# Copyright 2026 Aaron John Schlosser, PhD.
"""Every place the app declares its version must agree, and the release must have notes."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMVER = r"\d+\.\d+\.\d+"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def find_all(pattern: str, path: str) -> list[str]:
    return re.findall(pattern, read(path))


def test_all_declared_versions_agree():
    version = json.loads(read("web/package.json"))["version"]
    assert re.fullmatch(SEMVER, version)
    declared = {
        "api/app/config.py": find_all(rf'APP_VERSION = "({SEMVER})"', "api/app/config.py"),
        "api/app/main.py": find_all(rf'(?:version|"app_version"\s*:)\s*=?\s*"({SEMVER})"', "api/app/main.py"),
        "web/index.html": find_all(rf"<title>DerridAI ({SEMVER})</title>", "web/index.html"),
        "web/src/App.vue": find_all(rf"DerridAI ({SEMVER})</footer>", "web/src/App.vue"),
        "README.md": find_all(rf"Current version: \*\*({SEMVER})", "README.md"),
    }
    for path, found in declared.items():
        assert found, f"{path} does not declare a version"
        assert set(found) == {version}, f"{path} declares {found}, expected {version}"
    notes = ROOT / "docs" / "notes" / f"{version}.md"
    assert notes.is_file(), f"missing {notes.relative_to(ROOT)}"
    assert notes.read_text(encoding="utf-8").lstrip().startswith(f"# {version} —")


