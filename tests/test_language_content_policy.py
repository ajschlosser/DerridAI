# Copyright 2026 Aaron John Schlosser, PhD.
"""Locale-generated researcher text policies (the terms live in data, not in source).

Why: the researcher content filter is driven by per-language policies that an administrator generates
with an LLM and stores in the system database. These tests cover enforcement, what the browser
sees, persistence, generation validation, and combining several languages.
How: works on small hand-written policies (`_READY` and a French one) with placeholder words, so no
real forbidden term appears in the test source. Uses temp SQLite databases and a fake LLM call.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
sys.modules.setdefault("chromadb", types.SimpleNamespace())

from app.content_filter import (
    contains_disallowed_language,
    enforce_researcher_text,
    normalize_content_policy,
    public_content_policy_mirror,
    term_digest,
)
from app.content_policy_generation import generate_content_policy
from app.persistence import SQLiteSystemRepository
from app.system_store import SystemStore


_READY = {
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


def test_enforce_researcher_text_requires_a_ready_locale_policy():
    """Text cannot be checked without a ready policy, and a ready policy blocks its terms.

    With no policies the check raises "generates a text policy" (so researcher input is not silently allowed).
    With `_READY`, ordinary text passes and a text containing a blocked term raises "cannot contain".
    """
    with pytest.raises(ValueError, match="generates a text policy"):
        enforce_researcher_text("hospitality", policies=[])
    enforce_researcher_text("hospitality", policies=[_READY])
    with pytest.raises(ValueError, match="cannot contain"):
        enforce_researcher_text("please zzblock that", policies=[_READY])


def test_public_policy_mirror_sends_digests_not_terms():
    """The mirror sent to browsers holds hashes of terms, never the terms themselves.

    Checks ready=True, the locale list, that a blocked term's digest is present, and that the raw word does
    not appear anywhere in the serialized mirror.
    """
    mirror = public_content_policy_mirror([{**_READY, "code": "en-US"}])
    assert mirror["ready"] is True
    assert mirror["locales"] == ["en-US"]
    assert term_digest("zzblock") in mirror["blocked_term_hashes"]
    dumped = json.dumps(mirror)
    assert "zzblock" not in dumped


def test_content_policy_survives_dictionary_save(tmp_path, monkeypatch):
    """Saving a language dictionary must not erase or expose its content policy.

    Stores a policy, confirms the language listing shows content_policy_ready, that get_language hides the raw
    policy, and that saving the dictionary again keeps the blocked terms. The admin snapshot still includes the policy.
    """
    import app.system_store as store_module

    repository = SQLiteSystemRepository(tmp_path / "derridai-system.sqlite3")
    monkeypatch.setattr(store_module, "system_repository", repository)
    store = SystemStore()
    saved = store.put_content_policy("en-US", _READY)
    assert saved["status"] == "ready"
    assert next(item for item in store.list_languages() if item["code"] == "en-US")["content_policy_ready"] is True
    language = store.get_language("en-US")
    assert "content_policy" not in language
    assert language["content_policy_ready"] is True
    store.put_language(
        "en-US",
        name=language["name"],
        flag=language["flag"],
        dictionary=language["dictionary"],
    )
    assert store.get_content_policy("en-US")["blocked_terms"][0] == "zzblock"
    snapshot = store.snapshot()
    assert snapshot["languages"]["en-US"]["content_policy"]["status"] == "ready"


def test_generate_content_policy_validates_model_json(monkeypatch):
    """A model's JSON reply becomes a validated policy; too-thin policies are rejected.

    A fake LLM returns 3 terms in each of the 6 categories plus one contextual term, and a language
    audit that approves everything: the result is "ready", marked llm-generated, with a report of
    how it was produced. A policy with only one blocked term must raise ValueError (it would give a
    false sense of protection).
    """
    import app.content_policy_generation as module

    def fake_chat_complete(**kwargs):
        assert kwargs["json_mode"] is True
        if kwargs["schema_name"] == "derridai_policy_language_audit":
            listed = [line[2:].split()[0] for line in kwargs["prompt"].splitlines() if line.startswith("- ")]
            return json.dumps({"verdicts": [{"term": term, "in_language": True} for term in listed]})
        reply = {category: [f"{category[:2]}{word}" for word in ("aaa", "bbb", "ccc")] for category in module.CATEGORIES}
        reply["contextual_terms"] = [
            {"term": "widget", "allow_title_case": True, "allow_if_surrounding": [], "allow_if_before_markers": []},
        ]
        return json.dumps(reply)

    monkeypatch.setattr(module, "chat_complete", fake_chat_complete)
    policy = generate_content_policy(
        code="en-US",
        provider="ollama",
        model="policy-model",
        base_url=None,
        api_key=None,
    )
    assert policy["status"] == "ready"
    assert policy["source"] == "llm-generated"
    assert "widget" in {item["term"] for item in policy["contextual_terms"]}
    assert policy["generation_report"]["attempts"] == 1
    with pytest.raises(ValueError):
        normalize_content_policy({"blocked_terms": ["too-few"], "contextual_terms": []})


def test_union_of_locale_policies_is_what_gets_enforced():
    """Terms from every ready language are enforced together.

    A French-only term is blocked when both English and French policies are supplied, while the same
    words split by a space (a different phrase) are not.
    """
    french = {
        "status": "ready",
        "code": "fr-CA",
        "blocked_terms": [
            "motinterdit",
            "termevilain",
            "aaarghword",
            "bbarghword",
            "ccarghword",
            "ddarghword",
            "eearghword",
            "ffarghword",
        ],
        "contextual_terms": [],
    }
    assert contains_disallowed_language("un motinterdit ici", policies=[_READY, french])
    assert not contains_disallowed_language("un mot interdit ici", policies=[_READY, french])
