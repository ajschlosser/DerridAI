# Copyright 2026 Aaron John Schlosser, PhD.
"""Researcher text policies must be written in the selected language and cover every category.

Why: asking a model once and checking the JSON is well formed let a French policy come back full of
English words, and said nothing about whether the kinds of abusive language a filter needs were
represented. Generation now names the language, audits the candidates, and retries the short
categories, and it refuses to return a policy it could not complete.
How: a scripted fake model answers the generation and the language-audit calls. Placeholder words only:
a term starting with "en" stands for a word of the wrong language, one starting with "fr" for a word
of the target language. No real forbidden term appears in this file.
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

sys.modules.setdefault("chromadb", types.SimpleNamespace())
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

import app.content_policy_generation as module  # noqa: E402
from app.content_filter import normalize_content_policy  # noqa: E402
from app.content_policy_generation import CATEGORIES, MIN_PER_CATEGORY, generate_content_policy, language_label  # noqa: E402

AUDIT = "derridai_policy_language_audit"


def _words(prefix: str, category: str, count: int, offset: int = 0) -> list[str]:
    """Distinct placeholder tokens such as "frvulgaaa"; letters only, as real terms must be."""
    letters = "abcdefghijklmnopqrstuvwxyz"
    return [prefix + category[:4] + letters[(offset + i) % 26] * 3 for i in range(count)]


class FakeModel:
    """Answers generation calls from a script and audit calls by looking at each term's prefix."""

    def __init__(self, generations, *, confirm_suspects=False, audit_replies=None):
        self.generations = list(generations)
        self.confirm_suspects = confirm_suspects
        self.audit_replies = list(audit_replies) if audit_replies is not None else None
        self.generation_prompts: list[str] = []
        self.generation_schemas: list[dict] = []
        self.audit_prompts: list[str] = []

    def __call__(self, **kwargs):
        if kwargs["schema_name"] == AUDIT:
            self.audit_prompts.append(kwargs["prompt"])
            if self.audit_replies is not None:
                return self.audit_replies.pop(0)
            verdicts = []
            for line in kwargs["prompt"].splitlines():
                if not line.startswith("- "):
                    continue
                term = line[2:].split()[0]
                suspect = line.endswith("*")
                verdicts.append({"term": term, "in_language": term.startswith("fr") or (suspect and self.confirm_suspects)})
            return json.dumps({"verdicts": verdicts})
        self.generation_prompts.append(kwargs["prompt"])
        self.generation_schemas.append(kwargs["json_schema"])
        reply = self.generations.pop(0) if self.generations else {}
        return json.dumps(reply) if not isinstance(reply, str) else reply


def _generate(model: FakeModel, monkeypatch, **overrides):
    monkeypatch.setattr(module, "chat_complete", model)
    kwargs = dict(code="fr-CA", language_name="Français", provider="ollama", model="m", base_url=None, api_key=None)
    kwargs.update(overrides)
    return generate_content_policy(**kwargs)


def _all_french():
    reply = {category: _words("fr", category, 4) for category in CATEGORIES}
    reply["contextual_terms"] = []
    return reply


def test_language_label_uses_the_installed_name_and_primary_subtag():
    """The label names the language ("Français (fr)"), not only its locale code."""
    assert language_label("fr-CA", "Français") == "Français (fr)"
    assert language_label("de-DE", None) == "de"
    assert language_label("de-DE", "de-DE") == "de"


def test_prompt_names_the_language_and_forbids_other_languages(monkeypatch):
    """The generation prompt states the target language and says not to return English terms."""
    model = FakeModel([_all_french()])
    _generate(model, monkeypatch)
    prompt = model.generation_prompts[0]
    assert "Target language: Français (fr)" in prompt
    assert "Do not return English terms" in prompt
    for category in CATEGORIES:
        assert category in prompt


def test_english_terms_are_removed_and_the_short_categories_are_retried(monkeypatch):
    """Wrong-language terms fail the audit; the next round asks only for what is still missing.

    Round 1 returns, per category, one good term and two wrong-language ones. Round 2 must be told
    which terms were rejected and return enough good ones. The saved policy holds no wrong-language
    term, and the report shows two attempts and the removals.
    """
    first = {category: _words("fr", category, 1) + _words("en", category, 2) for category in CATEGORIES}
    first["contextual_terms"] = []
    second = {category: _words("fr", category, 3, offset=5) for category in CATEGORIES}
    second["contextual_terms"] = []
    model = FakeModel([first, second])
    policy = _generate(model, monkeypatch)

    assert not [term for term in policy["blocked_terms"] if term.startswith("en")]
    assert all(policy["generation_report"]["categories"][category] >= MIN_PER_CATEGORY for category in CATEGORIES)
    assert policy["generation_report"]["attempts"] == 2
    assert policy["generation_report"]["removed_as_wrong_language"] == 2 * len(CATEGORIES)
    assert "Rejected earlier because they are not Français (fr) words" in model.generation_prompts[1]
    assert policy["target_language"] == "Français (fr)"


def test_only_short_categories_are_requested_on_retry(monkeypatch):
    """A category that already has enough good terms is not asked for again."""
    first = _all_french()
    first["ableist_slurs"] = _words("en", "ableist_slurs", 4)  # wrong language: this one comes back empty-handed
    second = {"ableist_slurs": _words("fr", "ableist_slurs", 3, offset=9), "contextual_terms": []}
    model = FakeModel([first, second])
    policy = _generate(model, monkeypatch)

    assert model.generation_schemas[1]["required"] == ["ableist_slurs", "contextual_terms"]
    assert "ableist_slurs" in model.generation_prompts[1]
    assert "sexual_insults" not in model.generation_prompts[1]
    assert policy["generation_report"]["categories"]["ableist_slurs"] == 3


def test_a_term_also_in_another_locales_policy_must_be_confirmed(monkeypatch):
    """Overlap with another installed language is treated as probable leakage.

    "shared" terms are marked in the audit prompt and dropped unless the audit affirmatively says
    they are words of the target language; ordinary terms are kept when the audit does not object.
    """
    reply = _all_french()
    reply["vulgarities"] = _words("fr", "vulgarities", 3) + ["sharedvulg"]
    other = [{"code": "en-US", "blocked_terms": ["sharedvulg"], "contextual_terms": []}]

    unconfirmed = FakeModel([reply], confirm_suspects=False)
    policy = _generate(unconfirmed, monkeypatch, other_policies=other)
    assert "sharedvulg" not in policy["blocked_terms"]
    assert any(line.endswith("*") and "sharedvulg" in line for line in unconfirmed.audit_prompts[0].splitlines())

    confirmed = FakeModel([reply], confirm_suspects=True)
    policy = _generate(confirmed, monkeypatch, other_policies=other)
    assert "sharedvulg" in policy["blocked_terms"]


def test_the_same_locales_own_policy_is_not_treated_as_another_language(monkeypatch):
    """Regenerating a locale must not count its own previous terms as leakage."""
    reply = _all_french()
    own = [{"code": "fr-CA", "blocked_terms": reply["vulgarities"], "contextual_terms": []}]
    model = FakeModel([reply])
    _generate(model, monkeypatch, other_policies=own)
    assert not any(line.endswith("*") for line in model.audit_prompts[0].splitlines())


def test_nothing_is_returned_when_the_model_keeps_answering_in_the_wrong_language(monkeypatch):
    """After the last attempt an incomplete policy raises instead of being saved.

    The error names the language, the attempt count, the categories still short, and how many terms
    were rejected. The model is called no more than max_attempts times.
    """
    always_english = {category: _words("en", category, 4) for category in CATEGORIES}
    always_english["contextual_terms"] = []
    model = FakeModel([always_english, always_english, always_english, always_english])
    with pytest.raises(ValueError, match=r"Could not generate a usable Français \(fr\) policy after 3 attempt"):
        _generate(model, monkeypatch, max_attempts=3)
    assert len(model.generation_prompts) == 3


def test_a_short_category_is_recorded_not_hidden(monkeypatch):
    """A right-language policy that is still short in one category is returned with the gap recorded.

    Wrong-language terms are never kept, but a good policy is not thrown away for one thin category;
    the report names the category so the administrator can add terms.
    """
    thin = _all_french()
    thin["religious_slurs"] = _words("fr", "religious_slurs", 1)
    policy = _generate(FakeModel([thin, thin, thin]), monkeypatch)
    assert policy["generation_report"]["short_categories"] == ["religious_slurs"]
    assert policy["generation_report"]["categories"]["religious_slurs"] == 1
    assert policy["generation_report"]["attempts"] == 3


def test_a_complete_policy_reports_no_short_categories(monkeypatch):
    """Full coverage is reported as an empty short_categories list."""
    policy = _generate(FakeModel([_all_french()]), monkeypatch)
    assert policy["generation_report"]["short_categories"] == []


def test_a_policy_with_too_few_acceptable_terms_is_refused_and_says_why(monkeypatch):
    """If fewer than 8 acceptable terms survive, nothing is returned, and the error explains the shortfall."""
    thin = {category: [] for category in CATEGORIES}
    thin["vulgarities"] = _words("fr", "vulgarities", 3)
    thin["contextual_terms"] = []
    model = FakeModel([thin, thin, thin])
    with pytest.raises(ValueError, match=r"only 3 acceptable term\(s\)"):
        _generate(model, monkeypatch)


def test_an_unusable_language_audit_raises_rather_than_accepting_unchecked_terms(monkeypatch):
    """If the audit answer cannot be parsed twice, generation fails; terms are never accepted unchecked."""
    model = FakeModel([_all_french()], audit_replies=["not json", "still not json"])
    with pytest.raises(ValueError, match="language check"):
        _generate(model, monkeypatch)


def test_malformed_generation_json_is_retried(monkeypatch):
    """A reply that is not JSON costs an attempt but does not abort generation."""
    model = FakeModel(["not json at all", _all_french()])
    policy = _generate(model, monkeypatch)
    assert policy["generation_report"]["attempts"] == 2


def test_the_generation_report_survives_being_saved(monkeypatch):
    """normalize_content_policy (used on save) keeps the language and the numeric report, and only those."""
    policy = _generate(FakeModel([_all_french()]), monkeypatch)
    saved = normalize_content_policy({**policy, "generation_report": {**policy["generation_report"], "junk": "x"}, "unexpected": 1})
    assert saved["target_language"] == "Français (fr)"
    assert saved["generation_report"]["attempts"] == 1
    assert "junk" not in saved["generation_report"] and "unexpected" not in saved


def test_installed_language_generation_uses_its_stored_name_and_other_policies(tmp_path, monkeypatch):
    """The helper used by the API looks up the language's name and the other locales' policies.

    English has a stored policy containing one word; the French generation prompt must name
    "Français" (from the stored language record), and the audit must mark that word as a suspect.
    """
    import app.system_store as store_module
    from app.persistence import SQLiteSystemRepository

    monkeypatch.setattr(store_module, "system_repository", SQLiteSystemRepository(tmp_path / "s.sqlite3"))
    store = store_module.SystemStore()
    monkeypatch.setattr(store_module, "system_store", store)
    english = [f"en{chr(97 + i) * 3}" for i in range(8)]
    store.put_content_policy("en-US", {"blocked_terms": english, "contextual_terms": []})

    reply = _all_french()
    reply["vulgarities"] = _words("fr", "vulgarities", 3) + [english[0]]
    model = FakeModel([reply])
    monkeypatch.setattr(module, "chat_complete", model)
    policy = module.generate_policy_for_installed_language(code="fr-CA", provider="ollama", model="m", base_url=None, api_key=None)

    assert "Target language: Français (fr)" in model.generation_prompts[0]
    assert any(line.endswith("*") and english[0] in line for line in model.audit_prompts[0].splitlines())
    assert english[0] not in policy["blocked_terms"]
