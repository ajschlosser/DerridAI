# Copyright 2026 Aaron John Schlosser, PhD.
"""The WebSocket realtime operations plane: authentication, authorization, backpressure and replay.

Why: the socket carries live job and corpus-build notifications. It must authenticate from the
session cookie, authorize every topic, never leak another user's job, stay bounded when a browser
falls behind, and let a reconnecting client either replay or resynchronize from REST. Losing the
socket or failing to publish must never affect the underlying job.
How: drives the real ASGI app with Starlette's TestClient WebSocket support and a stubbed session
lookup, and exercises the broker, queue and observer directly with in-memory fakes.
"""
from __future__ import annotations

import sys
import threading
import types
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.modules.setdefault("chromadb", types.SimpleNamespace())
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import main, operation_events  # noqa: E402
from app.auth import auth_store  # noqa: E402
from app.job_llm import LLMJobManager  # noqa: E402
from app.job_rag import RAGJobManager  # noqa: E402
from app.job_tools import LLMToolJobManager  # noqa: E402
from app.job_upsert import UpsertJobManager  # noqa: E402
from app.realtime import router as realtime_router  # noqa: E402
from app.realtime import subscriptions  # noqa: E402
from app.realtime.broker import EventBroker, Subscriber  # noqa: E402
from app.realtime.coalescing import OutgoingQueue  # noqa: E402
from app.realtime.events import RealtimeObserver, job_event_types  # noqa: E402
from app.realtime.protocol import (  # noqa: E402
    PROTOCOL_VERSION,
    Audience,
    Event,
    ProtocolError,
    parse_client_message,
)
from starlette.testclient import TestClient  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402

USERS = {
    "admin-cookie": SimpleNamespace(id=1, username="root", role="admin", active=True),
    "ann-cookie": SimpleNamespace(id=3, username="ann", role="researcher", active=True),
    "bob-cookie": SimpleNamespace(id=4, username="bob", role="researcher", active=True),
}
RAG_JOBS = {
    "rag-ann": {"id": "rag-ann", "type": "rag", "owner": "ann", "status": "running"},
    "rag-bob": {"id": "rag-bob", "type": "rag", "owner": "bob", "status": "running"},
}


@pytest.fixture()
def test_broker(monkeypatch):
    fresh = EventBroker(replay_events=8)
    monkeypatch.setattr(realtime_router, "broker", fresh)
    monkeypatch.setattr(auth_store, "user_for_session", lambda cookie: USERS.get(cookie or ""))
    monkeypatch.setattr(subscriptions, "find_job_summary", lambda job_id: RAG_JOBS.get(job_id))
    monkeypatch.setattr(subscriptions, "corpus_build_exists", lambda build_id: build_id == "build-1")
    return fresh


def _client(cookie: str | None) -> TestClient:
    client = TestClient(main.app)
    if cookie:
        client.cookies.set("derridai_session", cookie)
    return client


def _ready(ws) -> dict:
    frame = ws.receive_json()
    assert frame["type"] == "connection.ready"
    return frame


def _subscribe(ws, *topics: str, last_event_id: int | None = None) -> dict:
    message: dict = {"type": "subscribe", "topics": list(topics)}
    if last_event_id is not None:
        message["last_event_id"] = last_event_id
    ws.send_json(message)
    frame = ws.receive_json()
    assert frame["type"] == "subscription.updated"
    return frame["payload"]


def _publish(broker: EventBroker, job_id: str, *, owner: str | None, rag: bool, event_type: str = "job.progress"):
    audience = Audience(owner=owner, admin_only=not rag, capability="rag.jobs.own" if rag else None)
    return broker.publish(
        event_type, resource_type="job", resource_id=job_id,
        payload={"job": {"id": job_id}}, topics=("jobs", f"job:{job_id}"), audience=audience,
    )


def _close_code(ws) -> int:
    with pytest.raises(WebSocketDisconnect) as info:
        for _ in range(10):
            ws.receive_json()
    return info.value.code


# -- handshake ----------------------------------------------------------------------------------


def test_unauthenticated_sockets_are_closed_with_4401(test_broker):
    with _client(None).websocket_connect("/api/ws/events") as ws:
        assert _close_code(ws) == 4401


def test_authenticated_socket_receives_ready_with_protocol_version(test_broker):
    with _client("admin-cookie").websocket_connect("/api/ws/events") as ws:
        ready = _ready(ws)
        assert ready["payload"]["protocol_version"] == PROTOCOL_VERSION
        assert ready["payload"]["last_event_id"] == 0


def test_cross_origin_browsers_are_refused(test_broker):
    with _client("admin-cookie").websocket_connect("/api/ws/events", headers={"origin": "https://evil.example"}) as ws:
        assert _close_code(ws) == 4403


def test_a_role_with_no_realtime_topic_is_refused(test_broker, monkeypatch):
    monkeypatch.setattr(realtime_router, "capabilities_for", lambda user: frozenset({"corpus.read"}))
    with _client("ann-cookie").websocket_connect("/api/ws/events") as ws:
        assert _close_code(ws) == 4403


# -- subscriptions and isolation ------------------------------------------------------------------


def test_researchers_may_follow_only_their_own_research_jobs(test_broker):
    with _client("ann-cookie").websocket_connect("/api/ws/events") as ws:
        _ready(ws)
        result = _subscribe(ws, "jobs", "job:rag-ann", "job:rag-bob", "job:missing", "corpus-builds")
        assert result["topics"] == ["job:rag-ann", "jobs"]
        rejected = {item["topic"]: item["code"] for item in result["rejected"]}
        # Another user's job is indistinguishable from a missing one.
        assert rejected == {"job:rag-bob": 4404, "job:missing": 4404, "corpus-builds": 4403}


def test_events_never_cross_users(test_broker):
    with _client("ann-cookie").websocket_connect("/api/ws/events") as ws:
        _ready(ws)
        _subscribe(ws, "jobs")
        _publish(test_broker, "upsert-1", owner="root", rag=False)
        _publish(test_broker, "rag-bob", owner="bob", rag=True)
        mine = _publish(test_broker, "rag-ann", owner="ann", rag=True)
        frame = ws.receive_json()
        assert frame["resource_id"] == "rag-ann" and frame["event_id"] == mine.event_id
        assert set(frame) == {"type", "event_id", "resource_type", "resource_id", "revision", "timestamp", "payload"}


def test_admin_receives_every_subscribed_job_and_unsubscribe_stops_delivery(test_broker):
    with _client("admin-cookie").websocket_connect("/api/ws/events") as ws:
        _ready(ws)
        _subscribe(ws, "jobs", "corpus-build:build-1")
        _publish(test_broker, "upsert-1", owner="root", rag=False)
        assert ws.receive_json()["resource_id"] == "upsert-1"
        ws.send_json({"type": "unsubscribe", "topics": ["jobs"]})
        assert ws.receive_json()["payload"]["topics"] == ["corpus-build:build-1"]
        _publish(test_broker, "upsert-2", owner="root", rag=False)
        ws.send_json({"type": "ping"})
        assert ws.receive_json()["type"] == "pong"


def test_duplicate_subscriptions_are_idempotent(test_broker):
    with _client("admin-cookie").websocket_connect("/api/ws/events") as ws:
        _ready(ws)
        _subscribe(ws, "jobs")
        assert _subscribe(ws, "jobs", "jobs")["topics"] == ["jobs"]


# -- protocol enforcement ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("frame", "code"),
    [("not json", 4400), ('{"type": "launch_missiles"}', 4400), ('{"type": "subscribe", "topics": "jobs"}', 4400)],
)
def test_malformed_and_unknown_messages_close_with_4400(test_broker, frame, code):
    with _client("admin-cookie").websocket_connect("/api/ws/events") as ws:
        _ready(ws)
        ws.send_text(frame)
        assert _close_code(ws) == code


def test_oversized_messages_close_with_4408(test_broker, monkeypatch):
    monkeypatch.setattr(realtime_router, "settings", replace(realtime_router.settings, realtime_max_client_message_bytes=64))
    with _client("admin-cookie").websocket_connect("/api/ws/events") as ws:
        _ready(ws)
        ws.send_json({"type": "subscribe", "topics": ["jobs"] * 1, "padding": "x" * 200})
        assert _close_code(ws) == 4408


def test_message_floods_close_with_4408(test_broker):
    with _client("admin-cookie").websocket_connect("/api/ws/events") as ws:
        _ready(ws)
        for _ in range(60):
            ws.send_json({"type": "ping"})
        codes = []
        with pytest.raises(WebSocketDisconnect) as info:
            for _ in range(80):
                codes.append(ws.receive_json()["type"])
        assert info.value.code == 4408


def test_parse_client_message_validates_last_event_id():
    assert parse_client_message('{"type":"resync","last_event_id":4}', max_bytes=100).last_event_id == 4
    with pytest.raises(ProtocolError):
        parse_client_message('{"type":"resync","last_event_id":-1}', max_bytes=100)


# -- replay and resync -------------------------------------------------------------------------


def test_reconnect_replays_missed_events_or_requires_resync(test_broker):
    first = _publish(test_broker, "upsert-1", owner="root", rag=False)
    second = _publish(test_broker, "upsert-1", owner="root", rag=False)
    with _client("admin-cookie").websocket_connect("/api/ws/events") as ws:
        _ready(ws)
        _subscribe(ws, "jobs", last_event_id=first.event_id)
        replayed = ws.receive_json()
        assert replayed["event_id"] == second.event_id and replayed["revision"] == 2

    for _ in range(12):  # overflow the eight-event replay ring
        _publish(test_broker, "upsert-2", owner="root", rag=False)
    with _client("admin-cookie").websocket_connect("/api/ws/events") as ws:
        _ready(ws)
        _subscribe(ws, "jobs", last_event_id=first.event_id)
        assert ws.receive_json()["type"] == "connection.resync_required"


def test_replay_never_includes_other_users_events():
    broker = EventBroker(replay_events=16)
    _publish(broker, "rag-bob", owner="bob", rag=True)
    mine = _publish(broker, "rag-ann", owner="ann", rag=True)
    ann = Subscriber(username="ann", role="researcher", capabilities=frozenset({"rag.jobs.own"}), topics={"jobs"})
    assert [event.event_id for event in broker.replay_since(ann, 0)] == [mine.event_id]


# -- heartbeat and session lifecycle -------------------------------------------------------------


def test_session_expiry_closes_the_socket_with_4401(test_broker, monkeypatch):
    monkeypatch.setattr(realtime_router, "settings", replace(realtime_router.settings, realtime_heartbeat_seconds=1.0))
    with _client("admin-cookie").websocket_connect("/api/ws/events") as ws:
        _ready(ws)
        heartbeat = ws.receive_json()
        assert heartbeat["type"] == "connection.heartbeat"
        monkeypatch.setattr(auth_store, "user_for_session", lambda cookie: None)
        assert _close_code(ws) == 4401


def test_disconnect_unregisters_the_subscriber(test_broker):
    with _client("admin-cookie").websocket_connect("/api/ws/events") as ws:
        _ready(ws)
        _subscribe(ws, "jobs")
        assert len(test_broker.subscribers()) == 1
    assert test_broker.subscribers() == []


# -- queue, coalescing and backpressure ------------------------------------------------------------


def _event(event_id: int, event_type: str = "job.progress", resource_id: str = "j1") -> Event:
    return Event(event_type, event_id, "job", resource_id, event_id, "t", {}, ("jobs",))


def test_progress_is_coalesced_to_the_newest_and_order_follows_event_id():
    queue = OutgoingQueue(max_events=8)
    queue.put(_event(1))
    queue.put(_event(2, "job.completed"))
    queue.put(_event(3))
    events, overflowed = queue.drain()
    assert [event.event_id for event in events] == [2, 3] and not overflowed
    assert queue.coalesced == 1


def test_a_full_queue_drops_superseded_progress_but_never_terminal_events():
    queue = OutgoingQueue(max_events=4)
    queue.put(_event(1, resource_id="a"))
    queue.put(_event(2, "job.completed", "b"))
    queue.put(_event(3, "job.warning", "c"))
    queue.put(_event(4, "job.failed", "d"))
    queue.put(_event(5, "job.cancelled", "e"))
    events, overflowed = queue.drain()
    assert [event.event_id for event in events] == [2, 3, 4, 5] and not overflowed


def test_a_queue_of_only_essential_events_overflows_into_resync():
    queue = OutgoingQueue(max_events=4)
    for index in range(1, 6):
        queue.put(_event(index, "job.completed", f"r{index}"))
    events, overflowed = queue.drain()
    assert overflowed and [event.event_id for event in events] == [5]
    assert len(queue) == 0


def test_a_slow_client_stays_bounded():
    queue = OutgoingQueue(max_events=16)
    for index in range(1, 5000):
        queue.put(_event(index, resource_id=f"job-{index % 50}"))
    assert len(queue) <= 16


def test_broker_failures_never_reach_the_publisher(monkeypatch):
    broker = EventBroker()
    bad = Subscriber(username="root", role="admin", topics={"jobs"})
    monkeypatch.setattr(bad.queue, "put", lambda event: (_ for _ in ()).throw(RuntimeError("boom")))
    broker.register(bad)
    assert _publish(broker, "j", owner=None, rag=False) is None
    assert broker.publish_failures == 1


def test_revisions_are_monotonic_per_resource():
    broker = EventBroker()
    revisions = [_publish(broker, "j", owner=None, rag=False).revision for _ in range(3)]
    other = _publish(broker, "k", owner=None, rag=False).revision
    assert revisions == [1, 2, 3] and other == 1


# -- observer: shared job state -> normalized events -----------------------------------------------


@pytest.fixture(autouse=True)
def no_stale_operation_notes():
    """Corpus tests in the same worker leave build notes behind; each test starts clean."""
    operation_events.drain()
    yield
    operation_events.drain()



class FakeManager:
    def __init__(self):
        self.jobs: dict[str, dict] = {}

    def realtime_job_summaries(self):
        return [dict(job) for job in self.jobs.values()]


def _collect(broker: EventBroker) -> list[Event]:
    seen: list[Event] = []
    original = broker.publish

    def publish(*args, **kwargs):
        event = original(*args, **kwargs)
        if event is not None:
            seen.append(event)
        return event

    broker.publish = publish  # type: ignore[method-assign]
    return seen


def test_observer_emits_lifecycle_events_from_shared_job_state():
    broker = EventBroker()
    seen = _collect(broker)
    manager = FakeManager()
    manager.jobs["j1"] = {"id": "j1", "type": "llm", "status": "queued", "completed": 0, "total": 3, "warnings_count": 0}
    observer = RealtimeObserver(broker, managers=lambda: [manager], interval=0.01)
    observer.tick()
    assert seen == []  # existing state is the REST bootstrap, not a burst of events

    manager.jobs["j2"] = {"id": "j2", "type": "rag", "owner": "ann", "status": "queued", "warnings_count": 0}
    manager.jobs["j1"].update(status="running", stage="review")
    observer.tick()
    manager.jobs["j1"].update(completed=1)
    observer.tick()
    manager.jobs["j1"].update(completed=3, status="completed", warnings_count=1)
    del manager.jobs["j2"]
    observer.tick()

    by_job = {job_id: [event.type for event in seen if event.resource_id == job_id] for job_id in ("j1", "j2")}
    assert by_job == {
        "j1": ["job.stage_changed", "job.started", "job.progress", "job.warning", "job.completed"],
        "j2": ["job.created", "job.removed"],
    }
    assert [event.event_id for event in seen] == sorted(event.event_id for event in seen)
    created = next(event for event in seen if event.type == "job.created")
    assert "owner" not in created.payload["job"]
    assert created.audience == Audience(owner="ann", admin_only=False, capability="rag.jobs.own")
    assert next(event for event in seen if event.resource_id == "j1").audience.admin_only is True
    assert [event.revision for event in seen if event.resource_id == "j1"] == [1, 2, 3, 4, 5]


def test_observer_survives_a_failing_manager():
    broker = EventBroker()
    seen = _collect(broker)

    class Broken:
        def realtime_job_summaries(self):
            raise RuntimeError("manager lock poisoned")

    good = FakeManager()
    observer = RealtimeObserver(broker, managers=lambda: [Broken(), good], interval=0.01)
    observer.tick()
    good.jobs["j"] = {"id": "j", "type": "upsert", "status": "running"}
    observer.tick()
    assert [event.type for event in seen] == ["job.created"]


def test_every_job_manager_exposes_the_shared_realtime_summary():
    job = {
        "id": "x", "type": "rag", "owner": "ann", "status": "running", "stage": "retrieval",
        "stage_detail": "Retrieving " + "evidence " * 100, "completed": 1, "total": 4,
        "request": {"prompt": "full private prompt"}, "result": {"answer": "full answer"},
        "warnings": ["w"], "results": [{"proposal": {"changes": {}}}],
    }
    for manager_type in (LLMJobManager, RAGJobManager, LLMToolJobManager, UpsertJobManager):
        manager = manager_type.__new__(manager_type)
        manager._lock = threading.RLock()
        manager._jobs = {"x": dict(job)}
        summary = manager.realtime_job_summary("x")
        assert summary["status"] == "running" and summary["warnings_count"] == 1
        assert "request" not in summary and "result" not in summary and "results" not in summary
        assert len(summary["stage_detail"]) <= 240
        assert manager.realtime_job_summaries() == [summary]


def test_real_llm_job_events_converge_on_the_rest_snapshot(monkeypatch):
    from app.models import LLMJobCreate

    manager = LLMJobManager.__new__(LLMJobManager)
    manager._lock = threading.RLock()
    manager._jobs = {}
    monkeypatch.setattr(manager, "_persist_job", lambda job_id: None, raising=False)
    manager._executor = SimpleNamespace(submit=lambda *args, **kwargs: None)
    broker = EventBroker()
    seen = _collect(broker)
    observer = RealtimeObserver(broker, managers=lambda: [manager], interval=0.01)
    observer.tick()
    body = LLMJobCreate(items=[{"key": "k", "record": {"record_id": "r1"}}], fields=["speaker"])
    job = manager.create(body, owner="root")
    observer.tick()
    with manager._lock:
        manager._jobs[job["id"]].update(status="running", started_at="now")
    observer.tick()
    with manager._lock:
        manager._jobs[job["id"]].update(status="failed", finished_at="later", fatal_error="provider down")
    observer.tick()
    assert [event.type for event in seen] == ["job.created", "job.started", "job.failed"]
    final = seen[-1].payload["job"]
    rest = manager.get(job["id"])
    assert final["status"] == rest["status"] == "failed" and final["has_error"] is True
    assert "provider down" not in str(seen[-1].payload)


def test_corpus_build_notes_become_corpus_and_operations_events():
    broker = EventBroker()
    seen = _collect(broker)
    observer = RealtimeObserver(broker, managers=lambda: [], interval=0.01)
    observer.tick()
    base = {
        "id": "build-1", "type": "pdf_corpus", "status": "running", "raw_status": "running", "stage": "enriching",
        "record_count": 4, "accepted_count": 0, "rejected_count": 0, "review_count": 0,
        "review_queue_counts": {"all": 4, "ready": 3, "issues": 1, "pending": 4},
        "metadata_total": 4, "metadata_completed": 1, "metadata_enriched_count": 1,
        "metadata_tasks_total": 10, "metadata_tasks_completed": 1, "request": {"api_key": "sk-secret"},
    }
    operation_events.note_corpus_build(dict(base))
    observer.tick()
    operation_events.note_corpus_build({
        **base,
        "metadata_enriched_count": 2,
        "metadata_completed": 2,
        "metadata_tasks_completed": 4,
        "review_count": 2,
        "review_queue_counts": {"all": 4, "ready": 2, "issues": 2, "pending": 4},
    })
    observer.tick()
    operation_events.note_corpus_build({**base, "metadata_tasks_completed": 10, "status": "completed", "raw_status": "completed"})
    observer.tick()
    types_by_resource = [(event.resource_type, event.type) for event in seen]
    assert types_by_resource == [
        ("corpus_build", "corpus.build_changed"),
        ("job", "job.snapshot"),
        ("corpus_build", "corpus.metadata_progress"),
        ("corpus_build", "corpus.review_queue_changed"),
        ("job", "job.progress"),
        ("corpus_build", "corpus.build_changed"),
        ("corpus_build", "corpus.metadata_progress"),
        ("corpus_build", "corpus.review_queue_changed"),
        ("job", "job.completed"),
    ]
    assert all(event.audience.admin_only for event in seen)
    metadata_progress = next(event for event in seen if event.type == "corpus.metadata_progress")
    assert metadata_progress.payload["build"]["record_count"] == 4
    assert metadata_progress.payload["build"]["metadata_total"] == 4
    assert metadata_progress.payload["build"]["metadata_completed"] == 2
    assert metadata_progress.payload["build"]["metadata_enriched_count"] == 2
    assert metadata_progress.payload["build"]["review_queue_counts"]["issues"] == 2
    assert "sk-secret" not in str([event.payload for event in seen])


def test_model_activity_events_carry_only_operational_state():
    broker = EventBroker()
    seen = _collect(broker)
    observer = RealtimeObserver(broker, managers=lambda: [], interval=0.01)
    observer.tick()
    call = {"started_token": 1, "task": "metadata", "provider": "ollama", "model": "gemma", "base_url": "http://secret-host"}
    operation_events.note_model_activity("build-1", [call])
    observer.tick()
    operation_events.note_model_activity("build-1", [])
    observer.tick()
    assert [event.type for event in seen] == ["llm.started", "llm.completed"]
    assert seen[0].payload == {"activity": {"calls_in_flight": 1, "task": "metadata", "provider": "ollama", "model": "gemma"}}


def test_job_event_types_orders_stage_before_status():
    assert job_event_types({"status": "running", "stage": "a"}, {"status": "completed", "stage": "b"}) == [
        "job.stage_changed", "job.completed",
    ]


def test_realtime_summaries_never_carry_error_text_or_research_questions():
    manager = RAGJobManager.__new__(RAGJobManager)
    manager._lock = threading.RLock()
    manager._jobs = {
        "failed": {"id": "failed", "type": "rag", "status": "failed", "stage_detail": "HTTP 500 · upstream said: secret body"},
        "grading": {
            "id": "grading", "type": "llm_tool", "tool": "rag_grade", "status": "running",
            "stage_detail": "Grading 1 of 3 · What does Derrida mean by the supplement?",
        },
        "live": {"id": "live", "type": "rag", "status": "running", "stage_detail": "Reranking 12 candidates"},
    }
    summaries = {summary["id"]: summary for summary in manager.realtime_job_summaries()}
    assert "stage_detail" not in summaries["failed"] and summaries["failed"]["status"] == "failed"
    assert "stage_detail" not in summaries["grading"]
    assert summaries["live"]["stage_detail"] == "Reranking 12 candidates"



def test_resume_requeues_replay_in_event_order_ahead_of_newer_live_events():
    broker = EventBroker(replay_events=16)
    admin = Subscriber(username="root", role="admin", topics={"jobs"})
    broker.register(admin)
    first = _publish(broker, "j1", owner=None, rag=False, event_type="job.started")
    missed = [_publish(broker, "j1", owner=None, rag=False, event_type=kind) for kind in ("job.stage_changed", "job.completed")]
    admin.queue.drain()  # the client never saw these (socket dropped)
    live = _publish(broker, "j2", owner=None, rag=False, event_type="job.created")
    assert broker.resume(admin, first.event_id) is True
    events, _ = admin.queue.drain()
    assert [event.event_id for event in events] == [missed[0].event_id, missed[1].event_id, live.event_id]
