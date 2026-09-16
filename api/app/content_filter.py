# Copyright 2026 Aaron John Schlosser, PhD.
"""Researcher-authored text policy.

The filter is deterministic and conservative: it matches complete lexical tokens,
not substrings, and treats context-sensitive terms separately so normal names and
scholarly vocabulary are not accidentally rejected. It is enforced server-side;
the browser mirrors it only for immediate feedback.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

# Unambiguous terms are blocked as complete tokens after normalization. Keeping
# them out of a giant substring regex is important: e.g. a short blocked token
# must never reject a harmless longer word that merely begins with those letters.
_BLOCKED_TERMS = {
    "fuck", "fucking", "fucker", "motherfucker", "shit", "bullshit",
    "bitch", "bastard", "cunt", "cock", "pussy", "asshole", "arsehole",
    "whore", "slut", "goddamn",
    "nigger", "nigga", "faggot", "kike", "chink", "spic", "wetback",
    "tranny", "retard", "retarded",
}

# These words can have legitimate uses. They are handled with context/casing
# rather than being blindly rejected. "Dick" is a common personal name.
_CONTEXTUAL_TERMS = {"dick", "fag", "damn"}
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})
_WORD_RE = re.compile(r"[\w'’]+", re.UNICODE)
_BLOCKED_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(term) for term in sorted(_BLOCKED_TERMS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def _normalized(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).translate(_LEET).casefold()
    # Collapse punctuation used inside a token to evade a word-level check while
    # preserving whitespace as a true token boundary.
    return re.sub(r"(?<=\w)[._*~\-]+(?=\w)", "", text)


def _contextual_violation(original: str) -> bool:
    words = list(_WORD_RE.finditer(unicodedata.normalize("NFKC", original or "")))
    for index, match in enumerate(words):
        raw = match.group(0)
        token = _normalized(raw)
        if token not in _CONTEXTUAL_TERMS:
            continue
        if token == "dick":
            # Treat conventional title case as a name. This covers questions
            # such as "What does Dick mean here?" and "Dick Higgins" without
            # creating a substring exemption for lowercase abusive uses.
            if raw == "Dick":
                continue
            return True
        if token == "fag":
            # Avoid false positives in scholarly discussion of the British word
            # for a cigarette only when explicitly glossed/quoted as such.
            surrounding = " ".join(m.group(0).casefold() for m in words[max(0, index-3):index+4])
            if "cigarette" in surrounding or "british" in surrounding:
                continue
            return True
        if token == "damn":
            # "damn" is relatively mild but remains disallowed when used as an
            # interjection/insult. Quoted lexical discussion is permitted.
            before = original[max(0, match.start()-20):match.start()].casefold()
            if any(marker in before for marker in ("word ", "term ", "means ", "called ", "‘", '"')):
                continue
            return True
    return False


def contains_disallowed_language(value: str | None) -> bool:
    if not value:
        return False
    original = unicodedata.normalize("NFKC", str(value))
    normalized = _normalized(original)
    return bool(_BLOCKED_PATTERN.search(normalized) or _contextual_violation(original))


def find_disallowed_path(value: Any, *, path: str = "input") -> str | None:
    """Return the first nested path containing disallowed user-authored text."""
    if isinstance(value, str):
        return path if contains_disallowed_language(value) else None
    if isinstance(value, Mapping):
        for key, item in value.items():
            found = find_disallowed_path(item, path=f"{path}.{key}")
            if found:
                return found
        return None
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        for index, item in enumerate(value):
            found = find_disallowed_path(item, path=f"{path}[{index}]")
            if found:
                return found
    return None


def enforce_researcher_text(value: Any) -> None:
    if find_disallowed_path(value):
        raise ValueError(
            "Researcher text cannot contain profanity, obscenities, slurs, or other foul language. Please revise the text and try again."
        )
