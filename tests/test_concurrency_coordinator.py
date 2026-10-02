# Copyright 2026 Aaron John Schlosser, PhD.
"""Shared concurrency coordinator invariants."""

from __future__ import annotations

import threading

import pytest

from app.concurrency import (
    CapacityCancelled,
    ConcurrencyCoordinator,
    provider_capacity_key,
)


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


def test_cancelled_waiter_never_acquires_or_leaks_capacity() -> None:
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
