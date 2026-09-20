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
        "model_version": str(request.get("model_version") or model),
        "prompt_version": prompt_version,
        "code_version": code_version,
        "temperature": generation.get("temperature"),
        "seed": generation.get("seed"),
    }
