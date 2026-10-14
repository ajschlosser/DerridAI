# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
    "not identified", "not identifiable", "not established in source", "no value", "no author", "no speaker", "tbd", "todo", "empty", "blank", "-", "--", "—", "–", "?", "??",
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
