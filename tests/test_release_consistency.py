# Copyright 2026 Aaron John Schlosser, PhD.
"""Every place the app declares its version must agree, and the release must have notes."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMVER = r"\d+\.\d+\.\d+"


def read(path: str) -> str:
    """Read a repository file as UTF-8 text."""
    return (ROOT / path).read_text(encoding="utf-8")


def find_all(pattern: str, path: str) -> list[str]:
    """Return every regex capture group match in a repository file."""
    return re.findall(pattern, read(path))


def test_all_declared_versions_agree():
    """Every place that declares the app version must equal web/package.json, and the release needs notes.

    Checked: api/app/config.py, web/index.html title, and README.md "Current version".
    The FastAPI constructor, backup manifest, App.vue footer, and AuthScreen read
    APP_VERSION / the Vite-injected build stamp rather than duplicating the string.
    docs/notes/<version>.md must exist and start with "# <version> —". When cutting a
    release, bump the declared copies (see AGENTS.md). Do not hard-code the version in
    other tests.
    """
    version = json.loads(read("web/package.json"))["version"]
    assert re.fullmatch(SEMVER, version)
    declared = {
        "api/app/config.py": find_all(rf'APP_VERSION = "({SEMVER})"', "api/app/config.py"),
        "web/index.html": find_all(rf"<title>DerridAI ({SEMVER})</title>", "web/index.html"),
        "README.md": find_all(rf"Current version: \*\*({SEMVER})", "README.md"),
    }
    for path, found in declared.items():
        assert found, f"{path} does not declare a version"
        assert set(found) == {version}, f"{path} declares {found}, expected {version}"
    main = read("api/app/main.py")
    assert "version=app_version_label()" in main
    assert '"app_version": APP_VERSION' in main
    assert '"git_commit": APP_GIT_COMMIT or None' in main
    assert "appVersionLabel" in read("web/src/App.vue")
    assert "appVersionLabel" in read("web/src/components/AuthScreen.vue")
    notes = ROOT / "docs" / "notes" / f"{version}.md"
    assert notes.is_file(), f"missing {notes.relative_to(ROOT)}"
    assert notes.read_text(encoding="utf-8").lstrip().startswith(f"# {version} —")
