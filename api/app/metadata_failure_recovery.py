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

"""Bounded automatic recovery policy for metadata-family provider failures.

One graph execution remains one graph execution. This module decides whether a
failed family should be tried again later by outer build orchestration. Recovery
state is persisted in the existing per-family execution ledger so a process
restart or build resume can continue without repeating completed siblings.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from .llm_failures import FailureDisposition, failure_disposition

DEFAULT_MAX_AUTOMATIC_RECOVERY_ATTEMPTS = 2
DEFAULT_RECOVERY_BACKOFF_SECONDS = (2.0, 8.0)
MAX_AUTOMATIC_RETRY_AFTER_SECONDS = 300.0


@dataclass(frozen=True)
class MetadataRecoveryDecision:
    schedule: bool
    disposition: FailureDisposition
    completed_attempts: int
    next_attempt: int | None
    delay_seconds: float
    not_before: str | None
    terminal_reason: str | None = None


def _completed_attempts(ledger: dict[str, Any] | None) -> int:
    try:
        return max(0, int((ledger or {}).get("automatic_recovery_attempts") or 0))
    except (TypeError, ValueError):
        return 0


def _backoff_for(next_attempt: int, delays: tuple[float, ...]) -> float:
    if not delays:
        return 0.0
    index = min(max(0, next_attempt - 1), len(delays) - 1)
    try:
        return max(0.0, float(delays[index]))
    except (TypeError, ValueError):
        return 0.0


def plan_metadata_recovery(
    error: BaseException,
    prior_ledger: dict[str, Any] | None,
    *,
    max_attempts: int = DEFAULT_MAX_AUTOMATIC_RECOVERY_ATTEMPTS,
    backoff_seconds: tuple[float, ...] = DEFAULT_RECOVERY_BACKOFF_SECONDS,
    now: datetime | None = None,
) -> MetadataRecoveryDecision:
    """Decide whether a failed family gets a later provider execution.

    Structured/schema/evidence failures are deliberately terminal here: their
    own bounded repair paths already ran. Transient provider/transport/timeout
    failures may receive up to two later executions. A capability mismatch
    nested inside an upstream router failure gets one later chance because an
    auto-router may select another backend, but it is not hammered repeatedly.
    """

    disposition = failure_disposition(error)
    completed = _completed_attempts(prior_ledger)
    limit = max(0, int(max_attempts))

    if not disposition.retryable:
        return MetadataRecoveryDecision(
            False,
            disposition,
            completed,
            None,
            0.0,
            None,
            "not_retryable",
        )
    if disposition.capability_mismatch and completed >= 1:
        return MetadataRecoveryDecision(
            False,
            disposition,
            completed,
            None,
            0.0,
            None,
            "repeated_capability_mismatch",
        )
    if completed >= limit:
        return MetadataRecoveryDecision(
            False,
            disposition,
            completed,
            None,
            0.0,
            None,
            "automatic_recovery_exhausted",
        )

    next_attempt = completed + 1
    delay = _backoff_for(next_attempt, backoff_seconds)
    if disposition.retry_after_seconds is not None:
        retry_after = max(0.0, float(disposition.retry_after_seconds))
        if retry_after > MAX_AUTOMATIC_RETRY_AFTER_SECONDS:
            return MetadataRecoveryDecision(
                False,
                disposition,
                completed,
                None,
                0.0,
                None,
                "retry_after_exceeds_automatic_window",
            )
        delay = max(delay, retry_after)

    clock = now or datetime.now(UTC)
    not_before = (clock + timedelta(seconds=delay)).isoformat()
    return MetadataRecoveryDecision(
        True,
        disposition,
        completed,
        next_attempt,
        delay,
        not_before,
        None,
    )


def retry_not_before_seconds(
    ledger: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> float:
    """Return the remaining wait for one persisted retry-pending family."""

    raw = str((ledger or {}).get("retry_not_before") or "")
    if not raw:
        return 0.0
    try:
        due = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    if due.tzinfo is None:
        due = due.replace(tzinfo=UTC)
    clock = now or datetime.now(UTC)
    return max(0.0, (due - clock).total_seconds())


def pending_recovery_families(record: dict[str, Any]) -> list[str]:
    statuses = (
        record.get("metadata_stage_status")
        if isinstance(record.get("metadata_stage_status"), dict)
        else {}
    )
    return sorted(
        str(family)
        for family, state in statuses.items()
        if str(state) == "retry_pending"
    )


def due_recovery_families(
    record: dict[str, Any],
    *,
    now: datetime | None = None,
) -> list[str]:
    ledger = (
        record.get("metadata_execution_ledger")
        if isinstance(record.get("metadata_execution_ledger"), dict)
        else {}
    )
    return [
        family
        for family in pending_recovery_families(record)
        if retry_not_before_seconds(
            ledger.get(family) if isinstance(ledger.get(family), dict) else {},
            now=now,
        )
        <= 0.0
    ]


def next_record_recovery_delay(
    record: dict[str, Any],
    *,
    now: datetime | None = None,
) -> float | None:
    families = pending_recovery_families(record)
    if not families:
        return None
    ledger = (
        record.get("metadata_execution_ledger")
        if isinstance(record.get("metadata_execution_ledger"), dict)
        else {}
    )
    return min(
        retry_not_before_seconds(
            ledger.get(family) if isinstance(ledger.get(family), dict) else {},
            now=now,
        )
        for family in families
    )


def queue_due_recoveries(
    record: dict[str, Any],
    *,
    now: datetime | None = None,
) -> list[str]:
    """Promote only due families back to queued state on the current Record."""

    due = due_recovery_families(record, now=now)
    if not due:
        return []
    statuses = record.setdefault("metadata_stage_status", {})
    ledger = record.setdefault("metadata_execution_ledger", {})
    for family in due:
        entry = dict(ledger.get(family) or {})
        completed = _completed_attempts(entry)
        try:
            next_attempt = int(
                entry.get("next_automatic_recovery_attempt") or completed + 1
            )
        except (TypeError, ValueError):
            next_attempt = completed + 1
        # Promotion reserves an ordinal but does not consume the recovery budget.
        # The family executor advances automatic_recovery_attempts only after an
        # actual provider invocation. Circuit-open deferrals therefore cannot
        # exhaust retries without doing model work.
        entry["automatic_recovery_inflight_attempt"] = max(
            completed + 1, next_attempt
        )
        entry.pop("next_automatic_recovery_attempt", None)
        entry["state"] = "queued"
        entry["queued_for_recovery_at"] = (now or datetime.now(UTC)).isoformat()
        statuses[family] = "queued"
        ledger[family] = entry
    record["metadata_enrichment_state"] = "queued"
    return due
