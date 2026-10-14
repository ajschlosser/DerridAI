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
