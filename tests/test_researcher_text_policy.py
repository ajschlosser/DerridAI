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
POLICY_ROUTES = "\n".join(
    (ROOT / path).read_text(encoding="utf-8")
    for path in (
        "api/app/routers/annotations.py",
        "api/app/routers/jobs.py",
        "api/app/routers/stores.py",
    )
)

_DUMMY_POLICY = {
    "status": "ready",
    "blocked_terms": [
        "zzblock",
        "qwvulgar",
        "aaarghword",
        "bbarghword",
        "ccarghword",
        "ddarghword",
        "eearghword",
        "ffarghword",
    ],
    "contextual_terms": [],
}


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

    Behavior (dummy placeholder policy): ordinary scholarly text ("hospitality and différance") passes; a
    dotted spelling and a leetspeak spelling ("qwvulg4r") of blocked terms are caught; find_disallowed_path
    reports where in a nested payload the bad value is ("input.tags[1]").
    Wiring (source text): server route owners still enforce researcher text, and runtime.js still has the warning
    message, the input filter, the term-digest helper, and the /api/i18n/content-policy fetch.
    """
    content_filter = _load_content_filter()
    policies = [_DUMMY_POLICY]
    assert not content_filter.contains_disallowed_language("hospitality and différance", policies=policies)
    assert content_filter.contains_disallowed_language("z.z.b.l.o.c.k", policies=policies)
    assert content_filter.contains_disallowed_language("qwvulg4r", policies=policies)
    assert content_filter.find_disallowed_path({"note": "clean", "tags": ["ok", "z.z.b.l.o.c.k"]}, policies=policies) == "input.tags[1]"
    assert "enforce_researcher_text" in POLICY_ROUTES
    assert "content_filter.warning" in RUNTIME
    assert "filterResearcherInputElement" in RUNTIME
    assert "researcherTokenDigest" in RUNTIME
    assert "/api/i18n/content-policy" in RUNTIME
