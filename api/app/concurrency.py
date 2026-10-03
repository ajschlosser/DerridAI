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
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import FIRST_COMPLETED, Future, wait
from dataclasses import dataclass
from typing import Literal

CapacityPriority = Literal["foreground", "background"]


@dataclass(eq=False)
class _CapacityWaiter:
    priority: CapacityPriority


def bounded_as_completed[WorkItem, WorkResult](
    items: Iterable[WorkItem],
    submit: Callable[[WorkItem], Future[WorkResult]],
    *,
    max_pending: int,
    cancelled: Callable[[], bool] | None = None,
) -> Iterator[tuple[WorkItem, Future[WorkResult]]]:
    """Admit a bounded window, refilling only after the consumer handles results.

    Cancellation stops admission and attempts to cancel submitted work. Running
    tasks retain their owning executor's normal cancellation/shutdown behavior.
    """
    if max_pending < 1:
        raise ValueError("The pending task window must be positive.")
    source = iter(items)
    pending: dict[Future[WorkResult], tuple[int, WorkItem]] = {}
    sequence = 0

    def stopped() -> bool:
        return cancelled is not None and cancelled()

    def fill() -> None:
        nonlocal sequence
        while len(pending) < max_pending and not stopped():
            try:
                item = next(source)
            except StopIteration:
                return
            pending[submit(item)] = (sequence, item)
            sequence += 1

    try:
        fill()
        while pending and not stopped():
            done, _ = wait(pending, timeout=0.25, return_when=FIRST_COMPLETED)
            for future in sorted(done, key=lambda value: pending[value][0]):
                if stopped():
                    return
                _, item = pending.pop(future)
                yield item, future
            fill()
    finally:
        for future in pending:
            future.cancel()


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


Cancelled = Callable[[], bool]
WaitCallback = Callable[[CapacitySnapshot], None]


@dataclass
class CapacityPermit:
    """A leak-safe acquired capacity slot."""

    coordinator: ConcurrencyCoordinator
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

    def __enter__(self) -> CapacityPermit:
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
        self._queues: dict[tuple[str, str], list[_CapacityWaiter]] = {}
        self._foreground_streak: dict[tuple[str, str], int] = {}

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
        priority: CapacityPriority = "background",
    ) -> CapacityPermit:
        """Wait for one slot and return a context-managed permit.

        No application/repository lock is held by this class. The on_wait callback is
        called at most once and always outside the coordinator lock, so callers may
        safely update job/build progress from it.

        Foreground work may overtake queued background work, but at most three
        foreground admissions occur while background work waits. Each class is FIFO;
        running work is never preempted and configured limits remain authoritative.
        """

        identity = self._identity(resource, key)
        if priority not in ("foreground", "background"):
            raise ValueError("Unknown execution capacity priority.")
        waiter = _CapacityWaiter(priority)
        requested_limit = self._limit(limit)
        started = time.monotonic()
        notified_wait = False

        with self._condition:
            self._waiting[identity] = self._waiting.get(identity, 0) + 1
            self._queues.setdefault(identity, []).append(waiter)

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
                    queue = self._queues[identity]
                    foreground = next((item for item in queue if item.priority == "foreground"), None)
                    background = next((item for item in queue if item.priority == "background"), None)
                    selected = (
                        background
                        if background is not None and self._foreground_streak.get(identity, 0) >= 3
                        else foreground or background
                    )
                    if active < bounded and selected is waiter:
                        queue.remove(waiter)
                        if not queue:
                            self._queues.pop(identity)
                            self._foreground_streak.pop(identity, None)
                        elif foreground is not None and background is not None:
                            self._foreground_streak[identity] = (
                                self._foreground_streak.get(identity, 0) + 1
                                if priority == "foreground" else 0
                            )
                        else:
                            self._foreground_streak.pop(identity, None)
                        self._active[identity] = active + 1
                        self._condition.notify_all()
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
                queue = self._queues.get(identity, [])
                if waiter in queue:
                    queue.remove(waiter)
                if not queue:
                    self._queues.pop(identity, None)
                    self._foreground_streak.pop(identity, None)
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
            self._queues.clear()
            self._foreground_streak.clear()
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
        parsed = (
            int(selected)
            if isinstance(selected, (int, float, str))
            else int(str(selected))
        )
        return max(1, min(int(maximum), parsed))
    except (TypeError, ValueError):
        return max(1, min(int(maximum), int(default)))


capacity_coordinator = ConcurrencyCoordinator()
