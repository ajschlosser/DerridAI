# Copyright 2026 Aaron John Schlosser, PhD.
"""What an enrichment event needs to say about the conditions it ran under.

A comparison is only as good as its record of what differed. Every ledger event carries these
columns, so an analysis can group by arm, filter to the frozen gold set, or check that two runs
used the same prompt and seed, without trusting anyone's memory.

- Ablations are real switches: naming one in a request turns that component off for the run.
- Arms randomize records to conditions by hash, so assignment is unbiased, repeatable and needs no
  stored table. The same record always lands in the same arm for a given salt.
- The gold set is a fixed hash sample of records. Gold records are scored but never learned from.
"""

from __future__ import annotations

import hashlib
from typing import Any

# Components an experiment can turn off. "autofill" off is the no-autofill baseline.
ABLATABLE = ("autofill", "blended_confidence", "rejection_memory", "reviewer_conventions", "cross_build_learning")
GOLD_RATE = 0.05


def _unit(*parts: str) -> float:
    digest = hashlib.sha256("\0".join(parts).encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def is_gold(record_id: str, rate: float = GOLD_RATE) -> bool:
    return _unit("gold", record_id) < rate


def is_blind(record_id: str, rate: float) -> bool:
    """Blind-review sample: the reviewer labels these records without seeing the model's values.

    Independent of the gold set and of arm assignment. Comparing how often people agree with the
    model when blind against how often they accept it when shown measures anchoring.
    """
    return rate > 0 and _unit("blind", record_id) < rate


RECHECK_SPACING = 8  # human decisions between a decision and its re-check, so it is not answered from memory


def is_recheck(record_id: str, field: str, rate: float) -> bool:
    """A small random share of a reviewer's decisions is asked again, blind, to measure their consistency."""
    return rate > 0 and _unit("recheck", record_id, field) < rate


def needs_second_opinion(record_id: str, field: str, rate: float) -> bool:
    """A random share of decisions is also labelled by a second reviewer, blind, to measure agreement between people."""
    return rate > 0 and _unit("second", record_id, field) < rate


def assign_arm(record_id: str, arms: list[dict[str, Any]], salt: str = "") -> dict[str, Any]:
    """Pick one arm uniformly at random for a record, the same way every time."""
    return arms[min(len(arms) - 1, int(_unit("arm", salt, record_id) * len(arms)))]


def with_arm(request: dict[str, Any], record_id: str) -> dict[str, Any]:
    """The request as it applies to one record: its arm's name and ablations, if arms are configured."""
    arms = [a for a in request.get("arms") or [] if isinstance(a, dict) and a.get("name")]
    if not arms:
        return request
    arm = assign_arm(record_id, arms, str(request.get("arm_salt") or ""))
    return {**request, "arm": str(arm["name"]), "ablations": list(arm.get("ablations") or [])}


def disabled(request: dict[str, Any] | None) -> set[str]:
    return {str(a) for a in (request or {}).get("ablations") or [] if str(a) in ABLATABLE}


def context(request: dict[str, Any] | None, *, model: str, record_id: str, code_version: str, prompt_version: str) -> dict[str, Any]:
    """Columns stamped on every ledger event."""
    request = request or {}
    generation = request.get("generation") if isinstance(request.get("generation"), dict) else {}
    return {
        "arm": str(request.get("arm") or "default"),
        "ablations": sorted(disabled(request)),
        "gold": is_gold(record_id) if record_id else False,
        "blind": is_blind(record_id, float(request.get("blind_rate") or 0)) if record_id else False,
        "model_version": str(request.get("model_version") or model),
        "prompt_version": prompt_version,
        "code_version": code_version,
        "temperature": generation.get("temperature"),
        "seed": generation.get("seed"),
    }


# Fields whose values are names or phrases that should appear in the source text; enumerated
# fields (discourse role, region type, stance) are choices, not quotations, so text support does
# not apply to them.
FREE_TEXT_FIELDS = {"speaker", "position_holder", "target"}


def supported_in_text(value: Any, text: str) -> bool | None:
    """Do the value's words appear in the text it was drawn from? None when the question does not apply."""
    import re

    items = value if isinstance(value, (list, tuple)) else [value]
    words = {w for item in items for w in re.findall(r"\w{3,}", str(item).casefold())}
    if not words:
        return None
    haystack = set(re.findall(r"\w{3,}", text.casefold()))
    return len(words & haystack) / len(words) >= 0.5
