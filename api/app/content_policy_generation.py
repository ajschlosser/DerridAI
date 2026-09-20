# Copyright 2026 Aaron John Schlosser, PhD.
"""Generate a locale's researcher text policy with the selected LLM provider.

The policy must be written in the language it is for, and must cover the kinds of abusive
language a researcher filter needs to catch. Neither is guaranteed by asking a model once and
checking the JSON is well formed, so generation works in rounds:

1. Ask for terms per category, naming the language explicitly.
2. Audit the candidates with a second, narrower question ("is each of these a word of this
   language?"). Terms that also appear in another installed locale's policy are held to a
   stricter standard, since that overlap is the usual sign of English leaking into a policy.
3. Keep what passed, and ask again only for the categories that are still short, telling the
   model which terms were rejected.

Wrong-language terms are never kept. If a category is still short after the last round, the policy is
returned with that gap recorded (and refused only when almost nothing usable was produced), so an
English-contaminated policy is never saved but an otherwise good one is not thrown away.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from .content_filter import (
    POLICY_VERSION,
    normalize_content_policy,
    normalize_policy_term,
)
from .models import OllamaTouchupOptions
from .rag import _extract_json, chat_complete

# Each category is a kind of abusive language a researcher filter should represent.
CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "vulgarities": "general vulgarities and profanity",
    "sexual_insults": "sexual insults",
    "ethnic_racial_slurs": "racial and ethnic slurs actually used in the language",
    "religious_slurs": "religious slurs",
    "homophobic_transphobic_slurs": "homophobic and transphobic slurs",
    "ableist_slurs": "ableist slurs",
}
CATEGORIES = tuple(CATEGORY_DESCRIPTIONS)
MIN_PER_CATEGORY = 3
MAX_PER_CATEGORY = 30
MAX_ATTEMPTS = 3
MIN_TOTAL_TERMS = 8

_CONTEXTUAL_SCHEMA: dict[str, Any] = {
    "type": "array",
    "maxItems": 12,
    "items": {
        "type": "object",
        "additionalProperties": False,
        "required": ["term"],
        "properties": {
            "term": {"type": "string"},
            "allow_title_case": {"type": "boolean"},
            "allow_if_surrounding": {"type": "array", "items": {"type": "string"}},
            "allow_if_before_markers": {"type": "array", "items": {"type": "string"}},
        },
    },
}

_AUDIT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["verdicts"],
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["term", "in_language"],
                "properties": {"term": {"type": "string"}, "in_language": {"type": "boolean"}},
            },
        }
    },
}


def _generation_schema(categories: Sequence[str]) -> dict[str, Any]:
    properties: dict[str, Any] = {
        category: {
            "type": "array",
            "minItems": MIN_PER_CATEGORY,
            "maxItems": MAX_PER_CATEGORY,
            "items": {"type": "string"},
        }
        for category in categories
    }
    properties["contextual_terms"] = _CONTEXTUAL_SCHEMA
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [*categories, "contextual_terms"],
        "properties": properties,
    }


def language_label(code: str, name: str | None = None) -> str:
    """Human-readable identity of the target language, e.g. ``Français (fr)``.

    The code alone (``fr-CA``) is easy for a model to under-weight; the installed name and the
    primary language subtag are what say "write this in French".
    """
    primary = str(code or "").split("-")[0].lower()
    label = str(name or "").strip()
    if label and label.casefold() != str(code or "").casefold():
        return f"{label} ({primary})"
    return primary or str(code or "")


def _policy_prompt(
    label: str,
    categories: Sequence[str],
    accepted: Mapping[str, Sequence[str]],
    rejected: Sequence[str],
) -> str:
    lines = [
        "You are compiling a researcher-account text policy for DerridAI, a scholarly research tool.",
        f"Target language: {label}. Every term you return must be a lexical item of {label} as it is "
        f"actually used by its speakers. Do not return English terms, and do not return terms from any "
        f"other language, unless that exact word is also in ordinary use in {label}.",
        "Return one JSON object with these arrays of lowercase single-token terms, and nothing else:",
    ]
    for category in categories:
        lines.append(f"- {category}: {CATEGORY_DESCRIPTIONS[category]} ({MIN_PER_CATEGORY} to {MAX_PER_CATEGORY} terms)")
    lines.append(
        "- contextual_terms: tokens that are abusive in some uses and innocent in others. For each set "
        "allow_title_case when the Title Case form is a common personal name, allow_if_surrounding for nearby "
        "gloss words that mark a non-abusive sense, and allow_if_before_markers for quoted lexical discussion "
        f"such as 'word ' or 'term ' (written in {label}). Return at most 12."
    )
    lines.append(
        "Do not include ordinary scholarly vocabulary, given names, book titles, or words that are not abusive. "
        "Every term must be a single token of letters, optional apostrophes, or hyphens."
    )
    have = sorted({term for terms in accepted.values() for term in terms})
    if have:
        lines.append("Already accepted (do not repeat): " + ", ".join(have))
    if rejected:
        lines.append(f"Rejected earlier because they are not {label} words (do not repeat): " + ", ".join(sorted(set(rejected))))
    return "\n".join(lines)


def _audit_prompt(label: str, terms: Sequence[str], suspects: set[str]) -> str:
    listed = "\n".join(f"- {term}{' *' if term in suspects else ''}" for term in terms)
    return (
        f"Language audit. Target language: {label}.\n"
        f"Below is a list of words. For each one, say whether it is a real word or expression of {label} "
        "(in_language: true) or whether it belongs to a different language such as English "
        "(in_language: false). Judge only the language of the word, not whether it is offensive.\n"
        "A word marked * also appears in another language's list, so answer true only if it is genuinely "
        f"used in {label} too.\n"
        'Return {"verdicts":[{"term":"...","in_language":true}]} with one entry per word, and nothing else.\n\n'
        + listed
    )


def _clean_terms(values: Any) -> list[str]:
    """Normalize a model's list, silently dropping entries that are not valid single tokens."""
    cleaned: list[str] = []
    for value in values if isinstance(values, list) else []:
        try:
            term = normalize_policy_term(str(value))
        except ValueError:
            continue
        if term not in cleaned:
            cleaned.append(term)
    return cleaned


def _parse(raw: str) -> dict[str, Any] | None:
    try:
        parsed = _extract_json(raw)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def _audit(
    *,
    label: str,
    terms: list[str],
    suspects: set[str],
    call: Callable[[str, dict[str, Any], str], str],
) -> dict[str, bool]:
    """Ask the model which of ``terms`` are words of the target language.

    Returns a verdict per term it answered about. Unparseable answers are retried once and then
    raise: accepting unaudited terms would defeat the point of the audit.
    """
    if not terms:
        return {}
    for _ in range(2):
        parsed = _parse(call(_audit_prompt(label, terms, suspects), _AUDIT_SCHEMA, "derridai_policy_language_audit"))
        if parsed is None:
            continue
        verdicts: dict[str, bool] = {}
        for item in parsed.get("verdicts") or []:
            if isinstance(item, Mapping) and isinstance(item.get("in_language"), bool):
                try:
                    verdicts[normalize_policy_term(str(item.get("term") or ""))] = bool(item["in_language"])
                except ValueError:
                    continue
        return verdicts
    raise ValueError(f"The language check for {label} did not return a usable answer.")


def _term_passes_language_audit(term: str, suspects: set[str], verdicts: Mapping[str, bool]) -> bool:
    # A suspect (also in another locale's policy) must be affirmatively confirmed; anything
    # else is dropped only when the audit says it is not a word of this language.
    if term in suspects:
        return verdicts.get(term) is True
    return verdicts.get(term, True)


def generate_content_policy(
    *,
    code: str,
    provider: str,
    model: str,
    base_url: str | None,
    api_key: str | None,
    generation: OllamaTouchupOptions | None = None,
    cancelled: Callable[[], bool] | None = None,
    language_name: str | None = None,
    other_policies: Sequence[Mapping[str, Any]] | None = None,
    max_attempts: int = MAX_ATTEMPTS,
) -> dict[str, Any]:
    label = language_label(code, language_name)
    other_terms = {
        str(term)
        for policy in other_policies or []
        if str(policy.get("code") or "") != code
        for term in (policy.get("blocked_terms") or [])
    }

    def call(prompt: str, schema: dict[str, Any], schema_name: str) -> str:
        return chat_complete(
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
            prompt=prompt,
            options=generation,
            json_mode=True,
            json_schema=schema,
            schema_name=schema_name,
            cancelled=cancelled,
        )

    accepted: dict[str, list[str]] = {category: [] for category in CATEGORIES}
    contextual: dict[str, dict[str, Any]] = {}
    rejected: list[str] = []
    attempts = 0
    for attempt in range(1, max(1, max_attempts) + 1):
        needed = [category for category in CATEGORIES if len(accepted[category]) < MIN_PER_CATEGORY]
        if not needed:
            break
        attempts = attempt
        parsed = _parse(call(_policy_prompt(label, needed, accepted, rejected), _generation_schema(needed), "derridai_researcher_content_policy"))
        if parsed is None:
            continue
        taken = {term for terms in accepted.values() for term in terms} | set(rejected)
        candidates: dict[str, list[str]] = {}
        for category in needed:
            fresh = [term for term in _clean_terms(parsed.get(category)) if term not in taken]
            candidates[category] = fresh
            taken.update(fresh)
        new_contextual: dict[str, dict[str, Any]] = {}
        for item in parsed.get("contextual_terms") or []:
            if not isinstance(item, Mapping):
                continue
            try:
                term = normalize_policy_term(str(item.get("term") or ""))
            except ValueError:
                continue
            if term not in contextual and term not in taken:
                new_contextual[term] = dict(item, term=term)
        to_audit = [term for terms in candidates.values() for term in terms] + list(new_contextual)
        suspects = {term for term in to_audit if term in other_terms}
        verdicts = _audit(label=label, terms=to_audit, suspects=suspects, call=call)

        for category, terms in candidates.items():
            for term in terms:
                (accepted[category] if _term_passes_language_audit(term, suspects, verdicts) else rejected).append(term)
        for term, item in new_contextual.items():
            if _term_passes_language_audit(term, suspects, verdicts):
                contextual[term] = item
            else:
                rejected.append(term)

    short = [category for category in CATEGORIES if len(accepted[category]) < MIN_PER_CATEGORY]
    flat: list[str] = []
    for category in CATEGORIES:
        for term in accepted[category]:
            if term not in flat:
                flat.append(term)
    if len(flat) < MIN_TOTAL_TERMS:
        raise ValueError(
            f"Could not generate a usable {label} policy after {attempts} attempt(s): only {len(flat)} acceptable "
            f"term(s) (at least {MIN_TOTAL_TERMS} are needed). Categories still below {MIN_PER_CATEGORY} terms: "
            f"{', '.join(short) or 'none'}. {len(rejected)} candidate term(s) were rejected as not {label} words."
        )
    # Wrong-language terms are never kept. A policy that is in the right language but still short in some
    # category is returned with that gap recorded, so an administrator can see it and add terms, rather than
    # losing an otherwise good result.
    policy = normalize_content_policy(
        {"blocked_terms": flat, "contextual_terms": list(contextual.values())},
        require_ready=True,
    )
    policy["generated_at"] = datetime.now(UTC).isoformat()
    policy["source"] = "llm-generated"
    policy["provider"] = provider
    policy["model"] = model
    policy["version"] = POLICY_VERSION
    policy["target_language"] = label
    policy["generation_report"] = {
        "attempts": attempts,
        "categories": {category: len(accepted[category]) for category in CATEGORIES},
        "removed_as_wrong_language": len(rejected),
        "short_categories": short,
    }
    return policy


def generate_policy_for_installed_language(
    *,
    code: str,
    provider: str,
    model: str,
    base_url: str | None,
    api_key: str | None,
    generation: OllamaTouchupOptions | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Generate a policy for a language that is installed, using its stored name and the other
    installed locales' policies as evidence of language leakage."""
    from .system_store import system_store

    language = system_store.get_language(code) or {}
    return generate_content_policy(
        code=code,
        provider=provider,
        model=model,
        base_url=base_url,
        api_key=api_key,
        generation=generation,
        cancelled=cancelled,
        language_name=str(language.get("name") or "") or None,
        other_policies=system_store.list_ready_content_policies(),
    )


__all__ = ["CATEGORIES", "generate_content_policy", "generate_policy_for_installed_language", "language_label"]
