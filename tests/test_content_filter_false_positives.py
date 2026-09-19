"""Researcher content filter: avoid false positives on names and words.

Why: the filter blocks abusive language in researcher input, but this is a
philosophy corpus full of authors' names and archaic words; over-blocking would
make legitimate research impossible.
How: loads content_filter.py directly by file path (no app package import) and
calls contains_disallowed_language on sample strings.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

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
    "contextual_terms": [
        {"term": "widget", "allow_title_case": True, "allow_if_surrounding": [], "allow_if_before_markers": []},
        {"term": "flint", "allow_title_case": False, "allow_if_surrounding": ["pebble"], "allow_if_before_markers": []},
        {"term": "blot", "allow_title_case": False, "allow_if_surrounding": [], "allow_if_before_markers": ["word ", "term "]},
    ],
}


def _load_content_filter():
    """Import content_filter.py by path so the test needs no ChromaDB or FastAPI setup."""
    path = ROOT / "api/app/content_filter.py"
    spec = importlib.util.spec_from_file_location("derridai_content_filter_bits", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_content_filter_avoids_name_and_substring_false_positives():
    """Names and dictionary words pass; genuine abuse and obfuscation are caught.

    Passes: "Dick Higgins", "Dickens and Dickinson", and "fag" used as the British
    word for cigarette. Blocked: "you dick", "what the damn", and the obfuscated
    "f.u.c.k".
    """
    content_filter = _load_content_filter()
    policies = [_DUMMY_POLICY]
    assert not content_filter.contains_disallowed_language("Widget Higgins discusses intermedia.", policies=policies)
    assert not content_filter.contains_disallowed_language("Widgetry and Flintstone are authors.", policies=policies)
    assert not content_filter.contains_disallowed_language("The technical term flint can mean pebble.", policies=policies)
    assert content_filter.contains_disallowed_language("you widget", policies=policies)
    assert content_filter.contains_disallowed_language("what the blot", policies=policies)
    assert not content_filter.contains_disallowed_language("the word blot", policies=policies)
    assert content_filter.contains_disallowed_language("z.z.b.l.o.c.k", policies=policies)
