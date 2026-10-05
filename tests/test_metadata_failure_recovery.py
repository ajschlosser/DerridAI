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

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.corpus_llm_helpers import StructuredOutputError
from app.llm_failures import (
    FailureDisposition,
    ProviderRequestError,
    failure_disposition,
)
from app.metadata_failure_recovery import (
    due_recovery_families,
    pending_recovery_families,
    plan_metadata_recovery,
    queue_due_recoveries,
)
from app.structured_completion import (
    StructuredCompletionError,
    complete_structured_json,
)


def test_provider_http_failures_have_stable_retry_semantics() -> None:
    upstream = ProviderRequestError(
        "router failed",
        status_code=502,
        provider_code="upstream_failed",
        provider_error_type="provider_error",
        capability_mismatch=True,
    )
    disposition = failure_disposition(upstream)
    assert disposition.code == "provider_upstream_failure"
    assert disposition.failure_class == "transient_provider"
    assert disposition.retryable is True
    assert disposition.http_status == 502
    assert disposition.provider_code == "upstream_failed"
    assert disposition.capability_mismatch is True

    throttled = failure_disposition(
        ProviderRequestError(
            "slow down",
            status_code=429,
            retry_after_seconds=17.0,
        )
    )
    assert throttled.code == "provider_rate_limited"
    assert throttled.retryable is True
    assert throttled.retry_after_seconds == 17.0

    denied = failure_disposition(
        ProviderRequestError("denied", status_code=401)
    )
    assert denied.code == "provider_authentication_failed"
    assert denied.retryable is False


def test_legacy_structured_timeout_flags_still_classify_as_retryable() -> None:
    error = StructuredOutputError(
        "timed out",
        failures=["primary timed out"],
        timed_out=True,
    )
    disposition = failure_disposition(error)
    assert disposition.failure_class == "timeout"
    assert disposition.retryable is True


def test_mixed_provider_chain_is_not_blindly_retried() -> None:
    error = StructuredOutputError(
        "mixed chain",
        failures=["primary unavailable", "review invalid"],
        failure_details=[
            FailureDisposition(
                "provider_upstream_failure",
                "transient_provider",
                True,
                502,
            ),
            FailureDisposition(
                "structured_output_invalid",
                "structured_output",
                False,
            ),
        ],
    )
    disposition = failure_disposition(error)
    assert disposition.code == "provider_chain_failed"
    assert disposition.retryable is False


def test_metadata_recovery_is_bounded_and_backed_off() -> None:
    now = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
    error = ProviderRequestError("temporary", status_code=503)

    first = plan_metadata_recovery(error, {}, now=now)
    assert first.schedule is True
    assert first.next_attempt == 1
    assert first.delay_seconds == 2.0
    assert first.not_before == (now + timedelta(seconds=2)).isoformat()

    second = plan_metadata_recovery(
        error,
        {"automatic_recovery_attempts": 1},
        now=now,
    )
    assert second.schedule is True
    assert second.next_attempt == 2
    assert second.delay_seconds == 8.0

    exhausted = plan_metadata_recovery(
        error,
        {"automatic_recovery_attempts": 2},
        now=now,
    )
    assert exhausted.schedule is False
    assert exhausted.terminal_reason == "automatic_recovery_exhausted"


def test_capability_mismatch_gets_only_one_deferred_router_chance() -> None:
    error = ProviderRequestError(
        "router backend ignored response_format",
        status_code=502,
        provider_code="upstream_failed",
        capability_mismatch=True,
    )
    assert plan_metadata_recovery(error, {}).schedule is True
    stopped = plan_metadata_recovery(
        error,
        {"automatic_recovery_attempts": 1},
    )
    assert stopped.schedule is False
    assert stopped.terminal_reason == "repeated_capability_mismatch"


def test_only_due_retry_pending_families_are_requeued() -> None:
    now = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
    record = {
        "record_id": "r1",
        "metadata_enrichment_state": "complete",
        "metadata_stage_status": {
            "discourse": "retry_pending",
            "quotation": "retry_pending",
            "indexing": "complete",
        },
        "metadata_execution_ledger": {
            "discourse": {
                "state": "retry_pending",
                "automatic_recovery_attempts": 0,
                "next_automatic_recovery_attempt": 1,
                "retry_not_before": (now - timedelta(seconds=1)).isoformat(),
            },
            "quotation": {
                "state": "retry_pending",
                "automatic_recovery_attempts": 0,
                "next_automatic_recovery_attempt": 1,
                "retry_not_before": (now + timedelta(seconds=30)).isoformat(),
            },
        },
    }

    assert pending_recovery_families(record) == ["discourse", "quotation"]
    assert due_recovery_families(record, now=now) == ["discourse"]

    promoted = queue_due_recoveries(record, now=now)
    assert promoted == ["discourse"]
    assert record["metadata_enrichment_state"] == "queued"
    assert record["metadata_stage_status"]["discourse"] == "queued"
    assert record["metadata_stage_status"]["quotation"] == "retry_pending"
    discourse = record["metadata_execution_ledger"]["discourse"]
    assert discourse["state"] == "queued"
    assert discourse["automatic_recovery_attempts"] == 0
    assert discourse["automatic_recovery_inflight_attempt"] == 1
    assert "next_automatic_recovery_attempt" not in discourse



def test_structured_completion_does_not_repeat_nonretryable_http_failure() -> None:
    calls = 0

    def request_once(_context):
        nonlocal calls
        calls += 1
        raise ProviderRequestError("bad credentials", status_code=401)

    with pytest.raises(StructuredCompletionError) as caught:
        complete_structured_json(
            request_once,
            prompt="Return JSON.",
            attempts=4,
            sleep_fn=lambda _seconds: None,
        )

    assert calls == 1
    assert caught.value.attempts == 1


def test_structured_completion_can_retry_transient_http_failure_within_budget() -> None:
    calls = 0

    def request_once(_context):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ProviderRequestError("temporary upstream", status_code=503)
        return '{"ok": true}'

    result = complete_structured_json(
        request_once,
        prompt="Return JSON.",
        attempts=2,
        sleep_fn=lambda _seconds: None,
    )
    assert result == {"ok": True}
    assert calls == 2
