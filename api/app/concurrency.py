# Copyright 2026 Aaron John Schlosser, PhD.
"""Process-wide bounded concurrency for provider and execution resources.

DerridAI runs background work inside one API process. Feature-local semaphores let
Corpus Builder, RAG, and tool jobs each believe the same provider still has spare
capacity, so aggregate traffic can exceed a provider profile's contract. This module
is the single in-process authority for shared execution capacity.

The coordinator deliberately knows nothing about scholarly state. Callers provide a
secret-safe resource key, a limit, and an optional cancellation callback. Permits are
released by context management even when work fails.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable


Cancelled = Callable[[], bool]
WaitCallback = Callable[["CapacitySnapshot"], None]


class CapacityCancelled(InterruptedError):
    """Raised when a caller is cancelled before shared capacity becomes available."""


@dataclass(frozen=True)
class CapacitySnapshot:
    """One resource/key's operational state at an instant."""

    resource: str
    key: str
    limit: int
    active: int
    waiting: int


@dataclass
class CapacityPermit:
    """A leak-safe acquired capacity slot."""

    coordinator: "ConcurrencyCoordinator"
    resource: str
    key: str
    limit: int
    waited_seconds: float
    active_when_acquired: int
    _released: bool = False

    def release(self) -> None:
        if self._released:
            return
        self._released = True
        self.coordinator.release(self.resource, self.key)

    def __enter__(self) -> "CapacityPermit":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        self.release()


class ConcurrencyCoordinator:
    """Coordinate bounded resources across otherwise independent feature managers.

    Limits are supplied by the operation/profile contract. If callers temporarily
    disagree about a limit for the same key, each admission is evaluated against the
    requesting caller's limit; an already-running call is never killed to satisfy a
    newly lower limit. Persisted provider profiles should normally make those values
    identical.
    """

    def __init__(self) -> None:
        self._condition = threading.Condition(threading.RLock())
        self._active: dict[tuple[str, str], int] = {}
        self._waiting: dict[tuple[str, str], int] = {}
        self._limits: dict[tuple[str, str], int] = {}

    @staticmethod
    def _limit(value: int) -> int:
        return max(1, int(value))

    @staticmethod
    def _identity(resource: str, key: str) -> tuple[str, str]:
        resource = str(resource or "").strip()
        key = str(key or "").strip()
        if not resource:
            raise ValueError("Concurrency resource must be non-empty.")
        if not key:
            raise ValueError("Concurrency key must be non-empty.")
        return resource, key

    def set_limit(self, resource: str, key: str, limit: int) -> int:
        """Set a process-wide configured limit for a shared resource key."""

        identity = self._identity(resource, key)
        bounded = self._limit(limit)
        with self._condition:
            self._limits[identity] = bounded
            self._condition.notify_all()
        return bounded

    def configured_limit(
        self, resource: str, key: str, *, fallback: int = 1
    ) -> int:
        identity = self._identity(resource, key)
        with self._condition:
            return int(self._limits.get(identity, self._limit(fallback)))

    def snapshot(self, resource: str, key: str, *, limit: int = 1) -> CapacitySnapshot:
        identity = self._identity(resource, key)
        bounded = self._limit(limit)
        with self._condition:
            bounded = int(self._limits.get(identity, bounded))
            return CapacitySnapshot(
                resource=identity[0],
                key=identity[1],
                limit=bounded,
                active=int(self._active.get(identity, 0)),
                waiting=int(self._waiting.get(identity, 0)),
            )

    def snapshots(self) -> list[CapacitySnapshot]:
        """Return secret-safe operational counters for all live resource keys."""

        with self._condition:
            identities = set(self._active) | set(self._waiting)
            return [
                CapacitySnapshot(
                    resource=resource,
                    key=key,
                    limit=int(self._limits.get((resource, key), 0)),
                    active=int(self._active.get((resource, key), 0)),
                    waiting=int(self._waiting.get((resource, key), 0)),
                )
                for resource, key in sorted(identities)
            ]

    def acquire(
        self,
        resource: str,
        key: str,
        limit: int,
        *,
        cancelled: Cancelled | None = None,
        on_wait: WaitCallback | None = None,
        poll_seconds: float = 0.25,
    ) -> CapacityPermit:
        """Wait for one slot and return a context-managed permit.

        No application/repository lock is held by this class. The on_wait callback is
        called at most once and always outside the coordinator lock, so callers may
        safely update job/build progress from it.
        """

        identity = self._identity(resource, key)
        requested_limit = self._limit(limit)
        started = time.monotonic()
        notified_wait = False

        with self._condition:
            self._waiting[identity] = self._waiting.get(identity, 0) + 1

        try:
            while True:
                if cancelled is not None and cancelled():
                    raise CapacityCancelled(
                        "Cancelled while waiting for shared execution capacity."
                    )

                wait_snapshot: CapacitySnapshot | None = None
                with self._condition:
                    # A configured process-wide limit may change while this caller waits
                    # (for example when an administrator lowers the Ollama runtime cap).
                    # Re-read it for every admission decision instead of capturing a stale
                    # value when the wait began.
                    bounded = int(self._limits.get(identity, requested_limit))
                    active = int(self._active.get(identity, 0))
                    if active < bounded:
                        self._active[identity] = active + 1
                        waiting = max(0, int(self._waiting.get(identity, 1)) - 1)
                        if waiting:
                            self._waiting[identity] = waiting
                        else:
                            self._waiting.pop(identity, None)
                        return CapacityPermit(
                            coordinator=self,
                            resource=identity[0],
                            key=identity[1],
                            limit=bounded,
                            waited_seconds=max(0.0, time.monotonic() - started),
                            active_when_acquired=active + 1,
                        )
                    if on_wait is not None and not notified_wait:
                        wait_snapshot = CapacitySnapshot(
                            resource=identity[0],
                            key=identity[1],
                            limit=bounded,
                            active=active,
                            waiting=int(self._waiting.get(identity, 0)),
                        )

                if wait_snapshot is not None:
                    notified_wait = True
                    on_wait(wait_snapshot)

                with self._condition:
                    self._condition.wait(timeout=max(0.01, float(poll_seconds)))
        except BaseException:
            with self._condition:
                waiting = max(0, int(self._waiting.get(identity, 1)) - 1)
                if waiting:
                    self._waiting[identity] = waiting
                else:
                    self._waiting.pop(identity, None)
                self._condition.notify_all()
            raise

    def release(self, resource: str, key: str) -> None:
        identity = self._identity(resource, key)
        with self._condition:
            active = int(self._active.get(identity, 0))
            if active <= 1:
                self._active.pop(identity, None)
            else:
                self._active[identity] = active - 1
            self._condition.notify_all()

    def reset_for_tests(self) -> None:
        """Clear counters. Production code should never reset live permits."""

        with self._condition:
            self._active.clear()
            self._waiting.clear()
            self._limits.clear()
            self._condition.notify_all()


def provider_capacity_key(
    *,
    provider_profile_id: str | None,
    provider: str,
    base_url: str | None,
    model: str | None,
) -> str:
    """Build a stable, secret-free provider gate key.

    Named profiles are the normal authority. Direct/manual requests fall back to a
    normalized provider/endpoint/model identity so independently created jobs still
    share capacity when they address the same configured target.
    """

    profile_id = str(provider_profile_id or "").strip()
    if profile_id:
        return f"profile:{profile_id}"
    normalized_provider = str(provider or "unknown").strip().lower() or "unknown"
    normalized_url = str(base_url or "").strip().rstrip("/").lower()
    normalized_model = str(model or "").strip()
    return f"direct:{normalized_provider}|{normalized_url}|{normalized_model}"


def provider_limit(value: object, *, default: int = 1, maximum: int = 64) -> int:
    try:
        selected = value if value not in (None, "") else default
        return max(1, min(int(maximum), int(selected)))
    except (TypeError, ValueError):
        return max(1, min(int(maximum), int(default)))


capacity_coordinator = ConcurrencyCoordinator()
