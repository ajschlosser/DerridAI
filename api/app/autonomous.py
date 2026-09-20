# Copyright 2026 Aaron John Schlosser, PhD.
"""Hands-free corpus building: decide what a build settles on its own, and say so.

In this mode nobody reviews the records, so every decision a reviewer would have made is made by a stated policy, and
none of it is dressed up as a human decision. A value the model proposed stays "LLM inferred" (method
"autonomous_policy"), a record it accepted says who accepted it, and everything it could not settle is listed with the
reason, so a person can review the exceptions afterwards without re-reading the whole corpus.

The policy is deliberately small and explicit. It is the place to add smarter rules later; the settle step below only
asks it three questions: may this proposal be taken, may this record be accepted, and what is left.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

# Statuses a person set. The policy never overrides them.
HUMAN_STATUSES = {"human_confirmed", "human_override", "human_confirmed_absent"}
# Why a field is waiting on a person, when a model proposed something for it.
PROPOSAL_REASONS = {"low_confidence", "ambiguous", "llm_disagreement", "deterministic_llm_disagreement", "evidence_failed", "confidence_missing", "no_value_returned"}


@dataclass(frozen=True)
class Policy:
    enabled: bool = False
    passes: int = 1  # extra enrichment passes before settling, so later passes can learn from earlier ones
    min_confidence: float = 0.8  # the model's stated confidence needed to take its proposal
    unresolved: str = "best_guess"  # "best_guess": take the proposal anyway; "leave": leave it for a person
    accept_records: bool = True  # accept a record once nothing on it is left waiting
    publish: bool = False  # publish when every record is accepted (never the default)

    @classmethod
    def from_request(cls, request: dict[str, Any] | None) -> Policy:
        raw = (request or {}).get("autonomous")
        if not isinstance(raw, dict):
            return cls()
        return cls(
            enabled=bool(raw.get("enabled")),
            passes=max(0, min(3, int(raw.get("passes", cls.passes)))),
            min_confidence=max(0.5, min(0.99, float(raw.get("min_confidence", cls.min_confidence)))),
            unresolved="leave" if raw.get("unresolved") == "leave" else "best_guess",
            accept_records=bool(raw.get("accept_records", True)),
            publish=bool(raw.get("publish", False)),
        )

    def public(self) -> dict[str, Any]:
        return asdict(self)


def _confidence(info: dict[str, Any]) -> float | None:
    value = info.get("confidence")
    return float(value) if isinstance(value, (int, float)) else None


def _empty(value: Any) -> bool:
    return value is None or value == "" or value == []


def settle_record(record: dict[str, Any], policy: Policy) -> dict[str, Any]:
    """Apply the policy to one record's waiting fields. Mutates the record; returns what it filled and what it left."""
    statuses = record.setdefault("metadata_field_status", {})
    filled: list[dict[str, Any]] = []
    left: list[dict[str, str]] = []
    for field, info in list(statuses.items()):
        if not isinstance(info, dict) or info.get("status") not in {"unresolved", "invalid"}:
            continue
        if info.get("status") in HUMAN_STATUSES:
            continue
        if info.get("status") == "invalid":
            left.append({"field": field, "reason": "the model returned an unusable value"})
            continue
        if info.get("reason_code") not in PROPOSAL_REASONS and info.get("method") not in {"llm", "hybrid", "deterministic+llm"}:
            left.append({"field": field, "reason": str(info.get("reason") or "needs a decision")[:160]})
            continue
        proposed = info.get("proposed_value")
        if _empty(proposed):
            proposed = record.get(field)  # a prefilled candidate already sits in the record
        if _empty(proposed):
            left.append({"field": field, "reason": "the model proposed no value"})
            continue
        confidence = _confidence(info)
        if not ((confidence is not None and confidence >= policy.min_confidence) or policy.unresolved == "best_guess"):
            left.append({"field": field, "reason": f"the model was {round((confidence or 0) * 100)}% confident, below {round(policy.min_confidence * 100)}%"})
            continue
        record[field] = proposed
        pct = f"{round(confidence * 100)}%" if confidence is not None else "unreported"
        statuses[field] = {
            "status": "llm_inferred", "method": "autonomous_policy", "autonomous": True, "confidence": confidence,
            "auto_populated": True, "proposed_value": proposed, "reason_code": "resolved",
            "reason": f"Taken automatically in hands-free mode (model confidence {pct}); no person reviewed it.",
        }
        filled.append({"field": field, "value": proposed, "confidence": confidence})
    return {"filled": filled, "left": left}


def may_accept(record: dict[str, Any]) -> tuple[bool, list[str]]:
    """Whether a settled record can be accepted, and if not, why. Call after the record's metadata state is synced."""
    reasons: list[str] = []
    if record.get("source_quality_issues"):
        reasons.append("the source text has a problem that needs a person")
    for field in list(record.get("metadata_review_fields") or []) + list(record.get("metadata_incomplete_fields") or []):
        reasons.append(f"{field} is still unresolved")
    if str(record.get("review_disposition") or "") == "rejected":
        reasons.append("a person rejected it")
    return (not reasons, list(dict.fromkeys(reasons)))
