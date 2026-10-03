# Copyright 2026 Aaron John Schlosser, PhD.
"""Bound admission and release queued work without suppressing task errors."""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from threading import Event

import pytest
from app.concurrency import bounded_as_completed


@pytest.mark.parametrize("size", [1000, 10000])
def test_admission_is_bounded_and_refills_after_consumption(size):
    submitted = []

    def submit(item):
        future = Future()
        future.set_result(item * 2)
        submitted.append(item)
        return future

    results = bounded_as_completed(range(size), submit, max_pending=3)
    first, future = next(results)
    assert first == 0 and future.result() == 0
    assert submitted == [0, 1, 2]
    seen = [first]
    for item, future in results:
        assert future.result() == item * 2
        seen.append(item)
        assert len(submitted) - len(seen) <= 2
    assert seen == list(range(size))
    assert submitted == list(range(size))


def test_cancellation_before_admission_does_not_consume_items():
    def items():
        pytest.fail("Cancelled work must not consume input.")
        yield 1

    assert list(bounded_as_completed(items(), lambda _: Future(), max_pending=2, cancelled=lambda: True)) == []


def test_cancellation_stops_admission_and_cancels_pending_work():
    stop = Event()
    pending = []

    def submit(item):
        future = Future()
        pending.append(future)
        if item == 0:
            future.set_result(item)
        return future

    results = bounded_as_completed(range(100), submit, max_pending=3, cancelled=stop.is_set)
    assert next(results)[0] == 0
    stop.set()
    assert list(results) == []
    assert len(pending) == 3
    assert all(future.cancelled() for future in pending[1:])


def test_fast_completion_is_handled_without_waiting_for_slow_first_item():
    release = Event()
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            def task(item):
                if item == 0:
                    assert release.wait(5)
                return item

            results = bounded_as_completed(range(2), lambda item: pool.submit(task, item), max_pending=2)
            item, future = next(results)
            assert item == future.result() == 1
            release.set()
            assert [(item, future.result()) for item, future in results] == [(0, 0)]
    finally:
        release.set()


def test_consumer_failure_cancels_unhandled_tasks():
    pending = []

    def submit(item):
        future = Future()
        pending.append(future)
        if item == 0:
            future.set_exception(ValueError("provider failed"))
        return future

    results = bounded_as_completed(range(10), submit, max_pending=2)
    _, future = next(results)
    with pytest.raises(ValueError, match="provider failed"):
        future.result()
    results.close()
    assert pending[1].cancelled()
    assert len(pending) == 2


def test_submission_failure_cancels_previous_submissions():
    pending = Future()

    def submit(item):
        if item == 1:
            raise RuntimeError("executor unavailable")
        return pending

    with pytest.raises(RuntimeError, match="executor unavailable"):
        list(bounded_as_completed(range(10), submit, max_pending=2))
    assert pending.cancelled()


def test_invalid_window_fails_explicitly():
    with pytest.raises(ValueError, match="positive"):
        list(bounded_as_completed([], lambda _: Future(), max_pending=0))
