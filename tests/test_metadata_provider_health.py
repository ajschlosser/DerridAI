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

import pytest
from app.llm_failures import FailureDisposition
from app.metadata_provider_health import (
    MetadataProviderCircuitOpen,
    MetadataProviderHealthCoordinator,
)

TRANSIENT = FailureDisposition(
    "provider_upstream_failure",
    "transient_provider",
    True,
    503,
)


def test_circuit_opens_after_bounded_transient_failures() -> None:
    health = MetadataProviderHealthCoordinator(
        failure_threshold=3,
        cooldown_seconds=10,
    )
    key = "profile:test"

    health.note_failure(key, TRANSIENT, now=1)
    health.note_failure(key, TRANSIENT, now=2)
    health.before_call(key, now=2.5)

    health.note_failure(key, TRANSIENT, now=3)
    state = health.snapshot(key, now=3)
    assert state["open"] is True
    assert state["consecutive_failures"] == 3

    with pytest.raises(MetadataProviderCircuitOpen) as caught:
        health.before_call(key, now=4)
    assert caught.value.retryable is True
    assert caught.value.failure_code == "provider_circuit_open"
    assert caught.value.retry_after_seconds == pytest.approx(9)


def test_half_open_allows_one_probe_and_success_closes_circuit() -> None:
    health = MetadataProviderHealthCoordinator(
        failure_threshold=1,
        cooldown_seconds=10,
    )
    key = "profile:test"
    health.note_failure(key, TRANSIENT, now=1)

    health.before_call(key, now=11)
    assert health.snapshot(key, now=11)["half_open_probe"] is True
    with pytest.raises(MetadataProviderCircuitOpen):
        health.before_call(key, now=11)

    health.note_success(key)
    health.before_call(key, now=11)
    assert health.snapshot(key, now=11)["consecutive_failures"] == 0


def test_failed_half_open_probe_reopens_circuit() -> None:
    health = MetadataProviderHealthCoordinator(
        failure_threshold=1,
        cooldown_seconds=10,
    )
    key = "profile:test"
    health.note_failure(key, TRANSIENT, now=1)
    health.before_call(key, now=11)
    health.note_failure(key, TRANSIENT, now=12)

    state = health.snapshot(key, now=12)
    assert state["open"] is True
    assert state["retry_after_seconds"] == pytest.approx(10)


def test_cancelled_half_open_probe_does_not_deadlock_provider() -> None:
    health = MetadataProviderHealthCoordinator(
        failure_threshold=1,
        cooldown_seconds=10,
    )
    key = "profile:test"
    health.note_failure(key, TRANSIENT, now=1)
    health.before_call(key, now=11)
    health.note_cancelled(key)

    health.before_call(key, now=11)
    assert health.snapshot(key, now=11)["half_open_probe"] is True


def test_retry_after_extends_cooldown_and_foreground_can_probe() -> None:
    health = MetadataProviderHealthCoordinator(
        failure_threshold=1,
        cooldown_seconds=10,
    )
    key = "profile:test"
    throttled = FailureDisposition(
        "provider_rate_limited",
        "rate_limit",
        True,
        429,
        retry_after_seconds=30,
    )
    health.note_failure(key, throttled, now=1)
    assert health.snapshot(key, now=1)["retry_after_seconds"] == pytest.approx(30)

    # Reviewer-triggered retries remain usable even while background corpus work
    # is being protected from failure amplification.
    health.before_call(key, foreground=True, now=2)
    with pytest.raises(MetadataProviderCircuitOpen):
        health.before_call(key, foreground=False, now=2)


def test_non_transient_failure_is_not_provider_outage_evidence() -> None:
    health = MetadataProviderHealthCoordinator(
        failure_threshold=1,
        cooldown_seconds=10,
    )
    key = "profile:test"
    health.note_failure(
        key,
        FailureDisposition(
            "structured_output_invalid",
            "structured_output",
            False,
        ),
        now=1,
    )
    health.before_call(key, now=1)
    assert health.snapshot(key, now=1)["open"] is False
