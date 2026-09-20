# Copyright 2026 Aaron John Schlosser, PhD.
"""Values that are not answers: "null", "N/A", "the author of the current record".

A model asked for a speaker or position holder sometimes describes the role instead of naming the
person, or writes a placeholder where it should have returned null. Neither is metadata. They are
dropped where a model's proposal is read, so they never become a value, a suggestion, or an option in
a dropdown. The frontend applies the same test to the options it lists (web/src/domain/metadataValues.ts).
A real name that happens to resemble a pattern is not a risk: every pattern needs the whole value to
be a generic role phrase.
"""

from __future__ import annotations

import re
from typing import Any

_NOTHING = {
    "null", "none", "nil", "undefined", "nan", "n/a", "na", "n.a.", "n.a", "unknown", "unspecified", "unnamed", "untitled",
    "not specified", "not stated", "not applicable", "not available", "not provided", "not given", "not mentioned",
    "not identified", "not identifiable", "no value", "no author", "no speaker", "tbd", "todo", "empty", "blank", "-", "--", "—", "–", "?", "??",
}
_ROLES = (
    r"author|speaker|writer|narrator|person|record|text|passage|document|book|work|source|party|individual|figure|reader|interlocutor|"
    r"voice|subject|object|entity|thing|topic|concept|idea|position|claim|argument|excerpt|section|chapter|quotation|quote"
)
_WHERE = r"(?:of|in|from|for|within|at)\s+(?:the|this|that)\s+(?:current\s+|present\s+|given\s+)?(?:" + _ROLES + r")"
_GENERIC = re.compile(
    rf"^(?:(?:the|this|that|an?|current|present|same|given)\s+)+(?:(?:current|present|same|main|primary|original|unnamed|unknown|anonymous|implied|implicit|"
    rf"general|generic|specific|relevant|previous|prior|other|another|first|second)\s+)*(?:{_ROLES})(?:s)?(?:\s+{_WHERE})?$"
    rf"|^(?:unknown|unnamed|anonymous|unidentified|unspecified|generic|implied|implicit)\s+(?:{_ROLES})$"
    rf"|^(?:{_ROLES})\s+(?:unknown|unnamed|not\s+(?:specified|stated|named|identified))$"
    rf"|^(?:the\s+)?(?:{_ROLES})\s+{_WHERE}$",
    re.I,
)


def _plain(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().strip("\"'“”‘’`.,;:()[]{}<>").strip()).casefold()


def is_placeholder(value: Any) -> bool:
    """True for a value that says nothing: a null in text form, or a role described instead of named."""
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    plain = _plain(value)
    return not plain or plain in _NOTHING or bool(_GENERIC.match(plain))


def clean(value: Any) -> Any:
    """The value with placeholders removed: None for a placeholder, and list items filtered."""
    if isinstance(value, (list, tuple)):
        return [item for item in value if not is_placeholder(item)]
    return None if is_placeholder(value) else value
