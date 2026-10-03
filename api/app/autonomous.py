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

"""Hands-free corpus building: decide what a build settles on its own, and say so.

In this mode nobody reviews the records, so every decision a reviewer would have made is made by a stated policy, and
none of it is dressed up as a human decision. A value the model proposed keeps its original derivation and method,
while a separate autonomous-policy decision records why it was selected. A record accepted by policy says so, and
everything the policy could not settle is listed with the reason, so a person can review the exceptions afterwards
without re-reading the whole corpus.

The policy is deliberately small and explicit. It is the place to add smarter rules later; the settle step below only
asks it three questions: may this proposal be taken, may this record be accepted, and what is left.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from .field_assertions import (
    current_assertions,
    migrate_record_assertions,
    project_record_assertions,
    store_assertion,
)

# Why a field is waiting on a person, when a model proposed something for it.
PROPOSAL_REASONS = {
    "low_confidence",
    "ambiguous",
    "llm_disagreement",
    "deterministic_llm_disagreement",
    "evidence_failed",
    "confidence_missing",
    "no_value_returned",
}


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


def _empty(value: Any) -> bool:
    return value is None or value == "" or value == []


def settle_record(record: dict[str, Any], policy: Policy) -> dict[str, Any]:
    """Apply policy selection without changing an assertion's epistemic meaning.

    A policy may select a visible candidate, but selection is not a new evaluation:
    the copied assertion keeps its derivation, evaluation, authority, value state,
    confidence, evidence, model, and run identity.
    """
    migrate_record_assertions(record)
    filled: list[dict[str, Any]] = []
    left: list[dict[str, str]] = []
    decisions: list[dict[str, Any]] = []
    for assertion in list(current_assertions(record)):
        field = str(assertion.field_name or "")
        if not field or assertion.authority_status in {"human_confirmed", "human_override"}:
            continue
        if assertion.value_status not in {"unresolved", "invalid"}:
            continue
        legacy = assertion.legacy_metadata or {}
        reason_code = str(legacy.get("reason_code") or "")
        if reason_code not in PROPOSAL_REASONS and assertion.method not in {"llm", "hybrid", "deterministic+llm"}:
            left.append({"field": field, "reason": str(assertion.reason or "needs a decision")[:160]})
            continue
        proposed = legacy.get("proposed_value")
        if _empty(proposed):
            proposed = assertion.value
        if _empty(proposed):
            proposed = record.get(field)
        if _empty(proposed):
            left.append({"field": field, "reason": "the model proposed no value"})
            continue
        if assertion.value_status == "invalid" and reason_code not in {"evidence_failed", "llm_disagreement", "deterministic_llm_disagreement"}:
            left.append({"field": field, "reason": "the candidate remains invalid"})
            continue
        confidence = assertion.confidence
        if not ((confidence is not None and confidence >= policy.min_confidence) or policy.unresolved == "best_guess"):
            left.append({"field": field, "reason": f"the model was {round((confidence or 0) * 100)}% confident, below {round(policy.min_confidence * 100)}%"})
            continue
        pct = f"{round(confidence * 100)}%" if confidence is not None else "unreported"
        decision = {
            "at": datetime.now(UTC).isoformat(),
            "actor_kind": "autonomous_policy",
            "policy": policy.public(),
            "field": field,
            "assertion_id": assertion.assertion_id,
            "reason_code": reason_code or "unresolved",
            "original_status": {
                "derivation_method": assertion.derivation_method,
                "evaluation_status": assertion.evaluation_status,
                "authority_status": assertion.authority_status,
                "value_status": assertion.value_status,
                "confidence": confidence,
                "evidence": assertion.evidence,
            },
            "selected_value": proposed,
            "selection": "best_guess" if policy.unresolved == "best_guess" else "threshold",
            "confidence_threshold": policy.min_confidence,
            "confidence_reported": confidence is not None,
        }
        selected = assertion.model_copy(update={
            "assertion_id": f"{assertion.assertion_id}:policy:{len(decisions) + 1}",
            "value": proposed,
            "legacy_metadata": {**assertion.legacy_metadata, "autonomous_decision": decision},
            "reason": assertion.reason or f"Selected by autonomous policy; reported confidence {pct}.",
            "record_revision": int(record.get("record_revision") or assertion.record_revision or 1),
            "supersedes_assertion_id": assertion.assertion_id,
            "created_at": decision["at"],
        })
        store_assertion(record, selected)
        projection = record.setdefault("metadata_field_status", {}).setdefault(field, {})
        if isinstance(projection, dict):
            projection.update({
                "autonomous": True,
                "auto_populated": True,
                "proposed_value": proposed,
                "reason_code": reason_code or "unresolved",
                "autonomous_decision": decision,
            })
        filled.append({
            "field": field,
            "value": proposed,
            "confidence": confidence,
            "reason_code": reason_code or "unresolved",
            "epistemic_status": {
                "evaluation_status": selected.evaluation_status,
                "authority_status": selected.authority_status,
                "value_status": selected.value_status,
            },
        })
        decisions.append(decision)
    project_record_assertions(record)
    return {"filled": filled, "left": left, "decisions": decisions}


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
