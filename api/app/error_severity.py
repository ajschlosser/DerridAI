# Copyright 2026 Aaron John Schlosser, PhD.
"""How wrong was a value a person changed?

A correction from "Derrida" to "Derrida, J." and one from "Derrida" to "Husserl" are both
corrections, but only the second is the model being wrong. Grading them keeps a model that is
merely untidy from looking as bad as one that is mistaken.

- cleared: the person removed the value and put nothing in its place.
- cosmetic: same after ignoring case, accents, punctuation and spacing.
- near_miss: not equal, but close (string similarity of at least NEAR_MISS), or one contains the other.
- substantive: anything else.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

NEAR_MISS = 0.8


def _plain(value: Any) -> str:
    text = ", ".join(map(str, value)) if isinstance(value, (list, tuple)) else str(value if value is not None else "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[\W_]+", " ", text.casefold()).strip()


def severity(old: Any, new: Any) -> str:
    if new in (None, "", []):
        return "cleared"
    a, b = _plain(old), _plain(new)
    if a == b:
        return "cosmetic"
    if a and b and (a in b or b in a or SequenceMatcher(None, a, b).ratio() >= NEAR_MISS):
        return "near_miss"
    return "substantive"
