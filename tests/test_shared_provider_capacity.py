# Copyright 2026 Aaron John Schlosser, PhD.
"""Cross-workflow provider-capacity integration tests.

These tests deliberately avoid starting manager background threads or persistence.
They exercise the managers' real provider-admission seams against one shared
ConcurrencyCoordinator so a profile limit is proven process-wide rather than merely
unit-tested inside the coordinator itself.
"""

from __future__ import annotations

import threading

from app import job_llm, job_rag
from app.concurrency import ConcurrencyCoordinator
from app.job_llm import LLMJobManager
from app.job_rag import RAGJobManager
from app.models import LLMJobCreate, RAGRunRequest


def _llm_manager() -> LLMJobManager:
    manager = LLMJobManager.__new__(LLMJobManager)
    manager._lock = threading.RLock()
    manager._jobs = {
        "llm-job": {
            "cancel_requested": False,
            "status": "queued",
            "stage_detail": "",
        }
    }
    return manager


def _rag_manager() -> RAGJobManager:
    manager = RAGJobManager.__new__(RAGJobManager)
    manager._lock = threading.RLock()
    manager._jobs = {
        "rag-job": {
            "cancel_requested": False,
            "status": "queued",
            "stage": "queued",
            "stage_detail": "",
            "scheduling": {},
        }
    }
    return manager


def test_llm_and_rag_share_one_provider_profile_limit(monkeypatch) -> None:
    coordinator = ConcurrencyCoordinator()
    monkeypatch.setattr(job_llm, "capacity_coordinator", coordinator)
    monkeypatch.setattr(job_rag, "capacity_coordinator", coordinator)

    llm = _llm_manager()
    rag = _rag_manager()
    llm_body = LLMJobCreate(
        items=[{"key": "r1", "record": {"record_id": "r1"}}],
        fields=["speaker"],
        provider="openai",
        model="test-model",
        provider_profile_id="shared-profile",
        max_concurrent_requests=1,
    )
    rag_body = RAGRunRequest(
        prompt="Question",
        provider="openai",
        model="test-model",
        provider_profile_id="shared-profile",
        max_concurrent_requests=1,
    )

    llm_permit = llm._acquire_provider_slot("llm-job", llm_body)
    assert llm_permit is not None

    rag_permits: list[object] = []
    admitted = threading.Event()

    def acquire_rag() -> None:
        permit = rag._acquire_provider_slot("rag-job", rag_body)
        rag_permits.append(permit)
        admitted.set()

    thread = threading.Thread(target=acquire_rag)
    thread.start()

    key = llm._provider_key(llm_body)
    for _ in range(100):
        if coordinator.snapshot("provider_generation", key, limit=1).waiting == 1:
            break
        threading.Event().wait(0.01)
    else:
        raise AssertionError("RAG caller did not reach the shared provider queue")

    snapshot = coordinator.snapshot("provider_generation", key, limit=1)
    assert snapshot.active == 1
    assert snapshot.waiting == 1
    assert not admitted.is_set()

    llm_permit.release()
    assert admitted.wait(timeout=1)
    assert rag_permits and rag_permits[0] is not None
    rag_permits[0].release()  # type: ignore[union-attr]
    thread.join(timeout=1)

    settled = coordinator.snapshot("provider_generation", key, limit=1)
    assert settled.active == 0
    assert settled.waiting == 0


def test_independent_provider_profiles_do_not_block_each_other(monkeypatch) -> None:
    coordinator = ConcurrencyCoordinator()
    monkeypatch.setattr(job_llm, "capacity_coordinator", coordinator)
    monkeypatch.setattr(job_rag, "capacity_coordinator", coordinator)

    llm = _llm_manager()
    rag = _rag_manager()
    llm_body = LLMJobCreate(
        items=[{"key": "r1", "record": {}}],
        fields=["speaker"],
        provider="openai",
        provider_profile_id="profile-a",
        max_concurrent_requests=1,
    )
    rag_body = RAGRunRequest(
        prompt="Question",
        provider="openai",
        provider_profile_id="profile-b",
        max_concurrent_requests=1,
    )

    llm_permit = llm._acquire_provider_slot("llm-job", llm_body)
    rag_permit = rag._acquire_provider_slot("rag-job", rag_body)
    assert llm_permit is not None
    assert rag_permit is not None

    assert coordinator.snapshot(
        "provider_generation", llm._provider_key(llm_body), limit=1
    ).active == 1
    assert coordinator.snapshot(
        "provider_generation", rag._provider_key(rag_body), limit=1
    ).active == 1

    llm_permit.release()
    rag_permit.release()


def test_research_overtakes_waiting_background_work_at_real_manager_gate(monkeypatch) -> None:
    coordinator = ConcurrencyCoordinator()
    monkeypatch.setattr(job_rag, "capacity_coordinator", coordinator)
    rag = _rag_manager()
    body = RAGRunRequest(
        prompt="Question",
        provider="openai",
        provider_profile_id="priority-profile",
        max_concurrent_requests=1,
    )
    key = rag._provider_key(body)
    held = coordinator.acquire("provider_generation", key, 1)
    background_waiting = threading.Event()
    order: list[str] = []
    failures: list[BaseException] = []

    def background() -> None:
        try:
            with coordinator.acquire(
                "provider_generation", key, 1,
                on_wait=lambda _: background_waiting.set(),
            ):
                order.append("background")
        except BaseException as exc:
            failures.append(exc)

    def research() -> None:
        try:
            permit = rag._acquire_provider_slot("rag-job", body)
            assert permit is not None
            with permit:
                order.append("research")
        except BaseException as exc:
            failures.append(exc)

    background_thread = threading.Thread(target=background)
    research_thread = threading.Thread(target=research)
    background_thread.start()
    try:
        assert background_waiting.wait(timeout=3)
        research_thread.start()
        for _ in range(300):
            if coordinator.snapshot("provider_generation", key).waiting == 2:
                break
            threading.Event().wait(0.01)
        else:
            raise AssertionError("Research did not reach the provider queue")
    finally:
        held.release()
        background_thread.join(timeout=5)
        if research_thread.ident is not None:
            research_thread.join(timeout=5)

    assert not failures
    assert not background_thread.is_alive()
    assert not research_thread.is_alive()
    assert order == ["research", "background"]
    assert coordinator.snapshot("provider_generation", key).active == 0
