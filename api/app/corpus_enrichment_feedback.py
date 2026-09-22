# Copyright 2026 Aaron John Schlosser, PhD.
"""Provenance helpers for model feedback that does not change review state."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def enrichment_informational_event(
    kind: str,
    field: str,
    *,
    run_id: str,
    pass_number: int,
    model: str | None = None,
    authoritative: Any = None,
    proposed: Any = None,
    confidence: Any = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Build an auditable no-change or protected-value model event."""
    event: dict[str, Any] = {
        "kind": kind,
        "field": field,
        "run_id": run_id,
        "pass": pass_number,
        "model": model or None,
        "at": datetime.now(UTC).isoformat(),
    }
    if authoritative is not None:
        event["authoritative_value"] = authoritative
    if proposed is not None:
        event["proposed_value"] = proposed
    if isinstance(confidence, (int, float)):
        event["confidence"] = confidence
    if reason:
        event["reason"] = reason
    return event
