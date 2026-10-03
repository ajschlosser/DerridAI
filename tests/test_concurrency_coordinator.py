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

"""Shared concurrency coordinator invariants."""

from __future__ import annotations

import threading

import pytest
from app.concurrency import (
    CapacityCancelled,
    CapacityPriority,
    ConcurrencyCoordinator,
    provider_capacity_key,
)


def test_foreground_overtakes_background_without_starving_it() -> None:
    coordinator = ConcurrencyCoordinator()
    held = coordinator.acquire("provider_generation", "test", 1)
    order: list[str] = []
    failures: list[BaseException] = []
    threads: list[threading.Thread] = []

    def enqueue(name: str, priority: CapacityPriority) -> None:
        queued = threading.Event()

        def worker() -> None:
            try:
                with coordinator.acquire(
                    "provider_generation", "test", 1, priority=priority,
                    on_wait=lambda _: queued.set(),
                ):
                    order.append(name)
            except BaseException as exc:
                failures.append(exc)

        thread = threading.Thread(target=worker)
        threads.append(thread)
        thread.start()
        assert queued.wait(timeout=3)

    try:
        enqueue("background-1", "background")
        enqueue("background-2", "background")
        for index in range(5):
            enqueue(f"foreground-{index}", "foreground")
    finally:
        held.release()
        for thread in threads:
            thread.join(timeout=5)

    assert not failures
    assert not any(thread.is_alive() for thread in threads)
    assert order == [
        "foreground-0", "foreground-1", "foreground-2", "background-1",
        "foreground-3", "foreground-4", "background-2",
    ]
    assert coordinator.snapshot("provider_generation", "test").waiting == 0


def test_wait_callback_failure_removes_priority_queue_entry() -> None:
    coordinator = ConcurrencyCoordinator()
    with coordinator.acquire("provider_generation", "test", 1):
        def fail(_snapshot) -> None:
            raise RuntimeError("progress failure")

        with pytest.raises(RuntimeError, match="progress failure"):
            coordinator.acquire(
                "provider_generation", "test", 1, priority="foreground", on_wait=fail,
            )
    with coordinator.acquire("provider_generation", "test", 1):
        assert coordinator.snapshot("provider_generation", "test").active == 1


def test_provider_capacity_key_prefers_named_profile() -> None:
    assert provider_capacity_key(
        provider_profile_id="primary-local",
        provider="ollama",
        base_url="http://localhost:11434",
        model="model-a",
    ) == "profile:primary-local"


def test_provider_capacity_key_normalizes_direct_target() -> None:
    assert provider_capacity_key(
        provider_profile_id=None,
        provider="OpenAI",
        base_url="HTTPS://EXAMPLE.TEST/v1/",
        model="model-a",
    ) == "direct:openai|https://example.test/v1|model-a"


def test_coordinator_bounds_parallel_callers_and_releases_all_slots() -> None:
    coordinator = ConcurrencyCoordinator()
    admitted = threading.Barrier(3)
    release = threading.Event()
    completed: list[int] = []
    failures: list[BaseException] = []

    def worker(index: int) -> None:
        try:
            with coordinator.acquire("provider_generation", "profile:test", 2):
                if index < 2:
                    admitted.wait(timeout=2)
                release.wait(timeout=2)
                completed.append(index)
        except BaseException as exc:  # pragma: no cover - failure is asserted below
            failures.append(exc)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(4)]
    for thread in threads:
        thread.start()

    admitted.wait(timeout=2)
    snapshot = coordinator.snapshot("provider_generation", "profile:test", limit=2)
    assert snapshot.active == 2
    assert snapshot.waiting == 2

    release.set()
    for thread in threads:
        thread.join(timeout=3)

    assert not failures
    assert sorted(completed) == [0, 1, 2, 3]
    settled = coordinator.snapshot("provider_generation", "profile:test", limit=2)
    assert settled.active == 0
    assert settled.waiting == 0


@pytest.mark.parametrize("priority", ["background", "foreground"])
def test_cancelled_waiter_never_acquires_or_leaks_capacity(priority: CapacityPriority) -> None:
    coordinator = ConcurrencyCoordinator()
    held = coordinator.acquire("provider_generation", "profile:test", 1)
    cancel = threading.Event()
    waiter_started = threading.Event()
    result: list[str] = []

    def wait() -> None:
        waiter_started.set()
        try:
            coordinator.acquire(
                "provider_generation",
                "profile:test",
                1,
                cancelled=cancel.is_set,
                priority=priority,
                poll_seconds=0.01,
            )
        except CapacityCancelled:
            result.append("cancelled")

    thread = threading.Thread(target=wait)
    thread.start()
    waiter_started.wait(timeout=1)

    # Wait until the coordinator itself observes the queued caller; no timing sleep.
    deadline = threading.Event()
    for _ in range(100):
        if coordinator.snapshot("provider_generation", "profile:test", limit=1).waiting == 1:
            break
        deadline.wait(0.01)
    else:
        pytest.fail("waiter did not reach the shared capacity queue")

    cancel.set()
    thread.join(timeout=2)
    held.release()

    assert result == ["cancelled"]
    settled = coordinator.snapshot("provider_generation", "profile:test", limit=1)
    assert settled.active == 0
    assert settled.waiting == 0


def test_context_manager_releases_capacity_after_failure() -> None:
    coordinator = ConcurrencyCoordinator()

    with pytest.raises(RuntimeError):
        with coordinator.acquire("provider_generation", "profile:test", 1):
            raise RuntimeError("boom")

    assert coordinator.snapshot(
        "provider_generation", "profile:test", limit=1
    ).active == 0


def test_different_keys_have_independent_capacity() -> None:
    coordinator = ConcurrencyCoordinator()
    left = coordinator.acquire("provider_generation", "profile:left", 1)
    right = coordinator.acquire("provider_generation", "profile:right", 1)
    try:
        assert coordinator.snapshot(
            "provider_generation", "profile:left", limit=1
        ).active == 1
        assert coordinator.snapshot(
            "provider_generation", "profile:right", limit=1
        ).active == 1
    finally:
        left.release()
        right.release()


def test_waiter_observes_configured_limit_changed_while_waiting() -> None:
    coordinator = ConcurrencyCoordinator()
    coordinator.set_limit("ollama_runtime", "global", 2)
    first = coordinator.acquire("ollama_runtime", "global", 99)
    second = coordinator.acquire("ollama_runtime", "global", 99)
    acquired = threading.Event()
    release = threading.Event()

    def waiter() -> None:
        with coordinator.acquire("ollama_runtime", "global", 99, poll_seconds=0.01):
            acquired.set()
            release.wait(timeout=2)

    thread = threading.Thread(target=waiter)
    thread.start()
    for _ in range(100):
        if coordinator.snapshot("ollama_runtime", "global", limit=99).waiting == 1:
            break
        threading.Event().wait(0.01)
    else:
        pytest.fail("waiter did not reach the shared capacity queue")

    coordinator.set_limit("ollama_runtime", "global", 1)
    second.release()
    assert not acquired.wait(timeout=0.05)
    first.release()
    assert acquired.wait(timeout=1)
    release.set()
    thread.join(timeout=2)
