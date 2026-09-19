# Copyright 2026 Aaron John Schlosser, PhD.
"""Researcher-authored text policy.

Forbidden terms live on each interface locale after an administrator generates
or edits that locale's researcher text policy. This module never ships a term
list: it only matches complete lexical tokens against the policies stored with
the language configuration. Matching is deterministic and conservative so
ordinary names and scholarly vocabulary are not rejected by substring accident.
The browser mirrors hashes of ready policies for immediate feedback; the API
is the enforcement boundary.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

POLICY_VERSION = "derridai-researcher-content-policy-v1"
_TERM_RE = re.compile(r"^[^\W\d_](?:[^\W\d_]|['’\-]){0,31}$", re.UNICODE)
_WORD_RE = re.compile(r"[\w'’]+", re.UNICODE)
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})
_MAX_BLOCKED = 150
_MAX_CONTEXTUAL = 24
_MIN_BLOCKED = 8


def _normalized(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).translate(_LEET).casefold()
    # Collapse punctuation used inside a token to evade a word-level check while
    # preserving whitespace as a true token boundary.
    return re.sub(r"(?<=\w)[._*~\-]+(?=\w)", "", text)


def normalize_policy_term(value: str) -> str:
    term = _normalized(str(value or "").strip())
    if not _TERM_RE.fullmatch(term):
        raise ValueError("Policy terms must be single alphabetic tokens.")
    return term


def term_digest(value: str) -> str:
    """Stable digest used by the researcher client so term lists stay server-side.

    This is an obfuscation for the browser mirror, not a security boundary. The
    API still matches against the stored policy.
    """
    return hashlib.sha256(_normalized(value).encode("utf-8")).hexdigest()


def empty_policy() -> dict[str, Any]:
    return {
        "version": POLICY_VERSION,
        "status": "missing",
        "blocked_terms": [],
        "contextual_terms": [],
    }


def policy_is_ready(policy: Mapping[str, Any] | None) -> bool:
    if not isinstance(policy, Mapping):
        return False
    if str(policy.get("status") or "") != "ready":
        return False
    return bool(policy.get("blocked_terms") or policy.get("contextual_terms"))


def normalize_content_policy(raw: Any, *, require_ready: bool = True) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValueError("Researcher text policy must be an object.")
    blocked: list[str] = []
    seen: set[str] = set()
    for item in raw.get("blocked_terms") or []:
        term = normalize_policy_term(str(item))
        if term in seen:
            continue
        seen.add(term)
        blocked.append(term)
        if len(blocked) > _MAX_BLOCKED:
            raise ValueError(f"Researcher text policy cannot list more than {_MAX_BLOCKED} forbidden terms.")
    contextual: list[dict[str, Any]] = []
    contextual_seen: set[str] = set()
    for item in raw.get("contextual_terms") or []:
        if not isinstance(item, Mapping):
            raise ValueError("Context-sensitive policy entries must be objects.")
        term = normalize_policy_term(str(item.get("term") or ""))
        if term in contextual_seen:
            continue
        contextual_seen.add(term)
        surrounding = []
        for marker in item.get("allow_if_surrounding") or []:
            marker_text = _normalized(str(marker)).strip()
            if marker_text and marker_text not in surrounding:
                surrounding.append(marker_text)
        before = []
        for marker in item.get("allow_if_before_markers") or []:
            marker_text = _normalized(str(marker))
            if marker_text and marker_text not in before:
                before.append(marker_text)
        contextual.append({
            "term": term,
            "allow_title_case": bool(item.get("allow_title_case")),
            "allow_if_surrounding": surrounding[:12],
            "allow_if_before_markers": before[:12],
        })
        if len(contextual) > _MAX_CONTEXTUAL:
            raise ValueError(f"Researcher text policy cannot list more than {_MAX_CONTEXTUAL} context-sensitive terms.")
    if require_ready and len(blocked) < _MIN_BLOCKED:
        raise ValueError(f"Researcher text policy needs at least {_MIN_BLOCKED} forbidden terms.")
    status = "ready" if blocked or contextual else "missing"
    policy = {
        "version": POLICY_VERSION,
        "status": status,
        "blocked_terms": blocked,
        "contextual_terms": contextual,
    }
    for key in ("generated_at", "source", "provider", "model"):
        value = raw.get(key)
        if value:
            policy[key] = value
    return policy


def public_content_policy_mirror(policies: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    blocked: set[str] = set()
    contextual: list[dict[str, Any]] = []
    locales: list[str] = []
    for policy in policies:
        if not policy_is_ready(policy):
            continue
        code = str(policy.get("code") or "").strip()
        if code:
            locales.append(code)
        for term in policy.get("blocked_terms") or []:
            blocked.add(term_digest(str(term)))
        for item in policy.get("contextual_terms") or []:
            if not isinstance(item, Mapping):
                continue
            contextual.append({
                "term_hash": term_digest(str(item.get("term") or "")),
                "allow_title_case": bool(item.get("allow_title_case")),
                "allow_if_surrounding": list(item.get("allow_if_surrounding") or []),
                "allow_if_before_markers": list(item.get("allow_if_before_markers") or []),
            })
    return {
        "ready": bool(blocked or contextual),
        "locales": locales,
        "blocked_term_hashes": sorted(blocked),
        "contextual": contextual,
    }


def admin_content_policy_view(policy: Mapping[str, Any] | None, *, code: str) -> dict[str, Any]:
    if not policy_is_ready(policy):
        return {"code": code, **empty_policy()}
    return {"code": code, **dict(policy)}


def _ready_policies(policies: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    if policies is not None:
        return [dict(policy) for policy in policies if policy_is_ready(policy)]
    try:
        from .system_store import system_store
    except ImportError:
        return []
    return system_store.list_ready_content_policies()


def _title_case_name(raw: str, term: str) -> bool:
    return raw == term.title()


def _contextual_violation(original: str, policies: Sequence[Mapping[str, Any]]) -> bool:
    words = list(_WORD_RE.finditer(unicodedata.normalize("NFKC", original or "")))
    rules: dict[str, dict[str, Any]] = {}
    for policy in policies:
        for item in policy.get("contextual_terms") or []:
            if not isinstance(item, Mapping):
                continue
            term = _normalized(str(item.get("term") or ""))
            if not term:
                continue
            current = rules.setdefault(term, {
                "allow_title_case": False,
                "allow_if_surrounding": [],
                "allow_if_before_markers": [],
            })
            current["allow_title_case"] = current["allow_title_case"] or bool(item.get("allow_title_case"))
            for marker in item.get("allow_if_surrounding") or []:
                if marker not in current["allow_if_surrounding"]:
                    current["allow_if_surrounding"].append(marker)
            for marker in item.get("allow_if_before_markers") or []:
                if marker not in current["allow_if_before_markers"]:
                    current["allow_if_before_markers"].append(marker)
    if not rules:
        return False
    for index, match in enumerate(words):
        raw = match.group(0)
        token = _normalized(raw)
        rule = rules.get(token)
        if not rule:
            continue
        if rule["allow_title_case"] and _title_case_name(raw, token):
            continue
        surrounding = " ".join(_normalized(m.group(0)) for m in words[max(0, index - 3):index + 4])
        if any(marker in surrounding for marker in rule["allow_if_surrounding"]):
            continue
        before = _normalized(original[max(0, match.start() - 20):match.start()])
        if any(marker in before for marker in rule["allow_if_before_markers"]):
            continue
        return True
    return False


def contains_disallowed_language(
    value: str | None,
    *,
    policies: Sequence[Mapping[str, Any]] | None = None,
) -> bool:
    if not value:
        return False
    ready = _ready_policies(policies)
    if not ready:
        return False
    original = unicodedata.normalize("NFKC", str(value))
    normalized = _normalized(original)
    blocked: set[str] = set()
    for policy in ready:
        for term in policy.get("blocked_terms") or []:
            blocked.add(_normalized(str(term)))
    if blocked:
        pattern = re.compile(
            r"\b(?:" + "|".join(re.escape(term) for term in sorted(blocked, key=len, reverse=True)) + r")\b",
            re.IGNORECASE,
        )
        if pattern.search(normalized):
            return True
    return _contextual_violation(original, ready)


def find_disallowed_path(
    value: Any,
    *,
    path: str = "input",
    policies: Sequence[Mapping[str, Any]] | None = None,
) -> str | None:
    """Return the first nested path containing disallowed user-authored text."""
    ready = None if policies is None else _ready_policies(policies)
    if isinstance(value, str):
        return path if contains_disallowed_language(value, policies=ready) else None
    if isinstance(value, Mapping):
        for key, item in value.items():
            found = find_disallowed_path(item, path=f"{path}.{key}", policies=ready)
            if found:
                return found
        return None
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        for index, item in enumerate(value):
            found = find_disallowed_path(item, path=f"{path}[{index}]", policies=ready)
            if found:
                return found
    return None


def researcher_text_policies_ready(policies: Sequence[Mapping[str, Any]] | None = None) -> bool:
    return bool(_ready_policies(policies))


def enforce_researcher_text(value: Any, *, policies: Sequence[Mapping[str, Any]] | None = None) -> None:
    ready = _ready_policies(policies)
    if not ready:
        raise ValueError(
            "Researcher text is blocked until an administrator generates a text policy for at least one language."
        )
    if find_disallowed_path(value, policies=ready):
        raise ValueError(
            "Researcher text cannot contain profanity, obscenities, slurs, or other foul language. Please revise the text and try again."
        )
