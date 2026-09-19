"""Researcher text policy wiring.

Why: the content filter must be enforced on the server (not only the browser) and
also give researchers immediate feedback in the UI.
How: unit-tests the filter directly, then checks that the backend and frontend
source still contain the enforcement hooks. The source-text checks are a
lightweight guard against the hooks being deleted, not a behavioral test.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (ROOT / "web/src/runtime/runtime.js").read_text(encoding="utf-8")
MAIN = (ROOT / "api/app/main.py").read_text(encoding="utf-8")


def _load_content_filter():
    """Import content_filter.py by path so the test needs no ChromaDB or FastAPI setup."""
    path = ROOT / "api/app/content_filter.py"
    spec = importlib.util.spec_from_file_location("derridai_content_filter_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module






















def test_researcher_text_policy_detects_nested_and_obfuscated_language():
    """Filter nested payloads and obfuscation; confirm enforcement hooks exist.

    Behavior: ordinary scholarly text ("hospitality and différance") passes; "f.u.c.k"
    and "sh1t" are blocked; find_disallowed_path reports where in a nested payload the
    offending value is ("input.tags[1]").
    Wiring: main.py must still define enforce_researcher_text, and runtime.js must keep
    the user-facing message and the capture-phase input listener.
    """
    content_filter = _load_content_filter()
    assert not content_filter.contains_disallowed_language("hospitality and différance")
    assert content_filter.contains_disallowed_language("f.u.c.k")
    assert content_filter.contains_disallowed_language("sh1t")
    assert content_filter.find_disallowed_path({"note": "clean", "tags": ["ok", "f.u.c.k"]}) == "input.tags[1]"
    assert "enforce_researcher_text" in MAIN
    assert "That language is not permitted for researcher accounts" in RUNTIME
    assert 'document.addEventListener("input",event=>filterResearcherInputElement(event.target),true)' in RUNTIME


