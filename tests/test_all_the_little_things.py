from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (ROOT / "web/src/runtime/runtime.js").read_text(encoding="utf-8")
MAIN = (ROOT / "api/app/main.py").read_text(encoding="utf-8")

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
    path = ROOT / "api/app/content_filter.py"
    spec = importlib.util.spec_from_file_location("derridai_content_filter_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_researcher_text_policy_detects_nested_and_obfuscated_language():
    content_filter = _load_content_filter()
    policies = [_DUMMY_POLICY]
    assert not content_filter.contains_disallowed_language("hospitality and différance", policies=policies)
    assert content_filter.contains_disallowed_language("z.z.b.l.o.c.k", policies=policies)
    assert content_filter.contains_disallowed_language("qwvulg4r", policies=policies)
    assert content_filter.find_disallowed_path({"note": "clean", "tags": ["ok", "z.z.b.l.o.c.k"]}, policies=policies) == "input.tags[1]"
    assert "enforce_researcher_text" in MAIN
    assert "content_filter.warning" in RUNTIME
    assert "filterResearcherInputElement" in RUNTIME
    assert "researcherTokenDigest" in RUNTIME
    assert "/api/i18n/content-policy" in RUNTIME
