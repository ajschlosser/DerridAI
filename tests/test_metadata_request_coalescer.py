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

"""Exact in-flight reuse is bounded, isolated, revalidated and never a completed cache."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from app.metadata_request_coalescer import MetadataRequestCoalescer


def join_pair(monkeypatch, operation, *, reusable=lambda _: True):
    coalescer = MetadataRequestCoalescer()
    started, release, joined = threading.Event(), threading.Event(), threading.Event()
    calls = []

    def blocked():
        calls.append(1)
        started.set()
        assert release.wait(5)
        return operation()

    with ThreadPoolExecutor(max_workers=2) as pool:
        leader = pool.submit(coalescer.run, "same", blocked, reusable=reusable, timeout=5)
        assert started.wait(5)
        pending = coalescer._pending["same"]
        result = pending.result

        def waiting(*args, **kwargs):
            joined.set()
            return result(*args, **kwargs)

        monkeypatch.setattr(pending, "result", waiting)
        follower = pool.submit(coalescer.run, "same", blocked, reusable=reusable, timeout=5)
        try:
            assert joined.wait(5)
        finally:
            release.set()
        return coalescer, calls, leader, follower


def test_identical_call_runs_once_and_returns_independent_values(monkeypatch):
    coalescer, calls, leader, follower = join_pair(monkeypatch, lambda: {"metadata": {"topics": ["one"]}})
    first, reused_first = leader.result()
    second, reused_second = follower.result()
    assert len(calls) == 1
    assert not reused_first and reused_second
    assert first == second
    second["metadata"]["topics"].append("changed")
    assert first["metadata"]["topics"] == ["one"]
    assert not coalescer._pending
    assert coalescer.run("same", lambda: {"fresh": True}, reusable=lambda _: True, timeout=5) == ({"fresh": True}, False)


def test_failed_call_stays_failed_for_both_and_can_retry(monkeypatch):
    def failure():
        raise ValueError("validation failed")

    coalescer, calls, leader, follower = join_pair(monkeypatch, failure)
    for future in (leader, follower):
        with pytest.raises(ValueError, match="validation failed"):
            future.result()
    assert len(calls) == 1
    assert not coalescer._pending
    assert coalescer.run("same", lambda: {"repaired": True}, reusable=lambda _: True, timeout=5)[0] == {"repaired": True}


def test_semantically_inconsistent_response_is_not_reused(monkeypatch):
    coalescer, calls, leader, follower = join_pair(monkeypatch, lambda: {"contradiction": True}, reusable=lambda _: False)
    assert len(calls) == 2
    assert not leader.result()[1] and not follower.result()[1]
    assert not coalescer._pending


def test_capacity_bypasses_new_keys_without_blocking_or_eviction():
    coalescer = MetadataRequestCoalescer(capacity=1)
    started, release = threading.Event(), threading.Event()

    def blocked():
        started.set()
        assert release.wait(5)
        return {"one": True}

    with ThreadPoolExecutor(max_workers=1) as pool:
        leader = pool.submit(coalescer.run, "one", blocked, reusable=lambda _: True, timeout=5)
        assert started.wait(5)
        try:
            assert coalescer.run("two", lambda: {"two": True}, reusable=lambda _: True, timeout=5) == ({"two": True}, False)
            assert len(coalescer._pending) == 1
            with pytest.raises(TimeoutError):
                coalescer.run("one", blocked, reusable=lambda _: True, timeout=0)
            assert len(coalescer._pending) == 1
        finally:
            release.set()
        assert leader.result() == ({"one": True}, False)
    assert not coalescer._pending


def test_invalid_capacity_is_rejected():
    with pytest.raises(ValueError, match="positive"):
        MetadataRequestCoalescer(capacity=0)
