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

"""Process-local circuit breaking for automatic metadata provider traffic.

The circuit protects a corpus build from amplifying one provider outage into
hundreds of near-identical calls. It is deliberately operational only: no
scholarly state, prompts, response bodies, credentials, or Record values enter
this coordinator.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from .llm_failures import FailureDisposition

TRANSIENT_FAILURE_CLASSES = frozenset(
    {"rate_limit", "timeout", "transient_provider", "transport"}
)


class MetadataProviderCircuitOpen(RuntimeError):
    """Automatic metadata traffic is deferred while a provider circuit is open."""

    def __init__(self, retry_after_seconds: float) -> None:
        retry_after = max(0.0, float(retry_after_seconds))
        super().__init__("Metadata provider is temporarily unavailable; automatic work was deferred.")
        self.retry_after_seconds = retry_after
        self.retryable = True
        self.failure_code = "provider_circuit_open"
        self.failure_class = "transient_provider"
        self.failure_disposition = FailureDisposition(
            "provider_circuit_open",
            "transient_provider",
            True,
            retry_after_seconds=retry_after,
        )


@dataclass
class _ProviderHealthState:
    consecutive_failures: int = 0
    open_until: float = 0.0
    half_open_probe: bool = False


class MetadataProviderHealthCoordinator:
    """Small thread-safe circuit breaker shared by metadata calls in one process."""

    def __init__(
        self,
        *,
        failure_threshold: int = 3,
        cooldown_seconds: float = 10.0,
    ) -> None:
        self.failure_threshold = max(1, int(failure_threshold))
        self.cooldown_seconds = max(0.1, float(cooldown_seconds))
        self._lock = threading.Lock()
        self._states: dict[str, _ProviderHealthState] = {}

    def before_call(
        self,
        key: str,
        *,
        foreground: bool = False,
        now: float | None = None,
    ) -> None:
        """Admit one call or fail fast without consuming a provider attempt.

        Foreground reviewer-triggered work bypasses the automatic circuit. Once
        the cooldown expires, exactly one background caller becomes a half-open
        probe and peers continue to defer until that probe settles.
        """

        if foreground:
            return
        clock = time.monotonic() if now is None else float(now)
        with self._lock:
            state = self._states.get(key)
            if state is None or state.open_until <= 0.0:
                return
            if state.open_until > clock:
                raise MetadataProviderCircuitOpen(state.open_until - clock)
            if state.half_open_probe:
                # A peer should re-check soon after the single probe settles;
                # it does not need to wait through another full outage cooldown.
                raise MetadataProviderCircuitOpen(min(1.0, self.cooldown_seconds))
            state.half_open_probe = True

    def note_success(self, key: str) -> None:
        with self._lock:
            self._states.pop(key, None)

    def note_cancelled(self, key: str) -> None:
        """Release a half-open probe without treating cancellation as provider health."""

        with self._lock:
            state = self._states.get(key)
            if state is not None:
                state.half_open_probe = False

    def note_failure(
        self,
        key: str,
        disposition: FailureDisposition,
        *,
        now: float | None = None,
    ) -> None:
        clock = time.monotonic() if now is None else float(now)
        with self._lock:
            state = self._states.setdefault(key, _ProviderHealthState())
            if disposition.failure_class not in TRANSIENT_FAILURE_CLASSES:
                # The provider answered; a semantic/schema/auth/configuration
                # failure is not evidence that the transport is unhealthy.
                state.consecutive_failures = 0
                state.open_until = 0.0
                state.half_open_probe = False
                return

            state.consecutive_failures += 1
            reopen = state.half_open_probe or (
                state.consecutive_failures >= self.failure_threshold
            )
            if not reopen:
                return
            retry_after = max(
                self.cooldown_seconds,
                float(disposition.retry_after_seconds or 0.0),
            )
            state.open_until = clock + retry_after
            state.half_open_probe = False

    def snapshot(self, key: str, *, now: float | None = None) -> dict[str, float | int | bool]:
        """Return payload-free health telemetry for tests/operations."""

        clock = time.monotonic() if now is None else float(now)
        with self._lock:
            state = self._states.get(key)
            if state is None:
                return {
                    "consecutive_failures": 0,
                    "open": False,
                    "retry_after_seconds": 0.0,
                    "half_open_probe": False,
                }
            return {
                "consecutive_failures": state.consecutive_failures,
                "open": state.open_until > clock,
                "retry_after_seconds": max(0.0, state.open_until - clock),
                "half_open_probe": state.half_open_probe,
            }

    def reset_for_tests(self) -> None:
        with self._lock:
            self._states.clear()


metadata_provider_health = MetadataProviderHealthCoordinator()
