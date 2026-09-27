# Copyright 2026 Aaron John Schlosser, PhD.
"""Realtime "live hints": bounded operation notes and their ephemeral wire events.

Why: generation drafts, per-record metadata progress and background-activity summaries are
streamed live but are never canonical. Each note type must stay bounded (a per-job character
cap, a fixed-size ring, latest-value dedup), must never carry source text/evidence, and its
wire event must reach only the right topic/audience and never be replayed after a reconnect.
How: exercises ``operation_events`` directly for buffering/bounding semantics, drives
``RealtimeObserver.tick()`` against a real ``EventBroker`` for publication/topic/audience/dedup
behavior (matching ``tests/test_realtime_plane.py``'s conventions), and exercises the real
``RAGJobManager``/``MetadataEnrichmentExecutionMixin``/``GutenbergOfflineService`` wiring with
the pipeline/LLM calls stubbed out.
"""
from __future__ import annotations

import dataclasses
import sys
import types
from pathlib import Path

import pytest

sys.modules.setdefault("chromadb", types.SimpleNamespace())
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import job_rag, operation_events  # noqa: E402
from app.gutenberg_catalogue import GutenbergOfflineService  # noqa: E402
from app.job_rag import RAGJobManager  # noqa: E402
from app.metadata_schema import default_schema  # noqa: E402
from app.models import RAGRunRequest  # noqa: E402
from app.realtime.broker import EventBroker, Subscriber  # noqa: E402
from app.realtime.coalescing import OutgoingQueue  # noqa: E402
from app.realtime.events import RealtimeObserver  # noqa: E402
from app.realtime.protocol import (  # noqa: E402
    CLOSE_FORBIDDEN,
    CLOSE_NOT_FOUND,
    EPHEMERAL_EVENT_TYPES,
    Audience,
    Event,
)
from app.realtime.subscriptions import ACTIVITY_KINDS, TopicDecision, authorize_topic  # noqa: E402


@pytest.fixture(autouse=True)
def no_stale_operation_notes():
    """``operation_events`` is a process-global; keep each test's notes isolated."""
    operation_events.drain()
    yield
    operation_events.drain()


def _collect(broker: EventBroker) -> list[Event]:
    """Record every event the broker actually publishes, in order (mirrors test_realtime_plane.py)."""
    seen: list[Event] = []
    original = broker.publish

    def publish(*args, **kwargs):
        event = original(*args, **kwargs)
        if event is not None:
            seen.append(event)
        return event

    broker.publish = publish  # type: ignore[method-assign]
    return seen


def _event(event_id: int, event_type: str, resource_id: str = "j1") -> Event:
    return Event(event_type, event_id, "job", resource_id, event_id, "t", {}, ("jobs",))


# -- operation_events: drain() shape ------------------------------------------------------------


def test_drain_returns_the_documented_dataclass_shape_and_clears_state():
    operation_events.note_corpus_build({"id": "b1", "status": "running"})
    operation_events.note_model_activity("b1", [{"started_token": 1, "task": "t", "provider": "p", "model": "m"}])
    operation_events.note_activity("gutenberg", {"ready": True})
    operation_events.note_record_metadata("b1", "r1", "record_started")
    operation_events.note_generation_delta("job-x", "hi", owner="ann")

    drained = operation_events.drain()

    assert isinstance(drained, operation_events.Drained)
    assert {f.name for f in dataclasses.fields(drained)} == {
        "builds", "model_activity", "activity", "metadata", "metadata_dropped", "generation",
    }
    assert drained.builds == {"b1": {"id": "b1", "status": "running"}}
    assert drained.model_activity == {"b1": {"calls_in_flight": 1, "task": "t", "provider": "p", "model": "m"}}
    assert drained.activity == {"gutenberg": {"ready": True}}
    assert len(drained.metadata) == 1 and drained.metadata_dropped == 0
    assert drained.generation["job-x"].owner == "ann"

    # Draining clears every bucket for the next observer tick.
    second = operation_events.drain()
    assert second.builds == {} and second.model_activity == {} and second.activity == {}
    assert second.metadata == [] and second.metadata_dropped == 0 and second.generation == {}


# -- operation_events: generation buffering, cap, gap -------------------------------------------


def test_generation_delta_buffers_per_job_independently():
    operation_events.note_generation_delta("job-a", "hello ", owner="ann")
    operation_events.note_generation_delta("job-a", "world", owner="ann")
    operation_events.note_generation_delta("job-b", "unrelated", owner="bob")

    drained = operation_events.drain()

    assert "".join(drained.generation["job-a"].chunks) == "hello world"
    assert drained.generation["job-a"].owner == "ann"
    assert "".join(drained.generation["job-b"].chunks) == "unrelated"
    assert drained.generation["job-b"].owner == "bob"


def test_generation_delta_caps_at_32000_chars_and_sets_the_gap_flag():
    assert operation_events.MAX_PENDING_GENERATION_CHARS == 32_000
    operation_events.note_generation_delta("job-a", "A" * 20_000, owner="ann")
    operation_events.note_generation_delta("job-a", "B" * 20_000, owner="ann")  # would total 40,000

    drained = operation_events.drain()
    buffer = drained.generation["job-a"]
    assert buffer.chars == 32_000
    assert "".join(buffer.chunks) == "A" * 20_000 + "B" * 12_000
    assert buffer.gap is True


def test_generation_delta_leaves_the_gap_flag_unset_when_it_fits():
    operation_events.note_generation_delta("job-c", "well within the cap", owner="ann")
    drained = operation_events.drain()
    assert drained.generation["job-c"].gap is False
    assert drained.generation["job-c"].chars == len("well within the cap")


def test_generation_finished_can_create_a_buffer_with_no_pending_text():
    operation_events.note_generation_finished("job-solo", owner="ann")
    drained = operation_events.drain()
    buffer = drained.generation["job-solo"]
    assert buffer.finished is True
    assert buffer.chunks == []
    assert buffer.owner == "ann"
    assert buffer.gap is False


# -- operation_events: metadata ring buffer ------------------------------------------------------


def test_metadata_ring_buffer_caps_at_512_and_counts_drops():
    assert operation_events.MAX_METADATA_NOTES == 512
    for index in range(520):
        operation_events.note_record_metadata("b1", f"r{index}", "record_started")

    drained = operation_events.drain()

    assert len(drained.metadata) == 512
    assert drained.metadata_dropped == 8  # 520 pushed - 512 kept
    assert drained.metadata[0]["record_id"] == "r8"  # the oldest 8 were evicted
    assert drained.metadata[-1]["record_id"] == "r519"


def test_metadata_notes_never_carry_source_text_and_bound_every_free_field():
    huge_family_text = "F" * 500
    long_field_id = "X" * 300

    operation_events.note_record_metadata(
        "b1", "r1", "field_checked",
        family=huge_family_text,
        state="complete",
        field_ids=[long_field_id] * 40,  # more than MAX_NOTE_FIELD_IDS
        precedents_used=-5,
    )

    drained = operation_events.drain()
    note = drained.metadata[0]

    # The function accepts only ids/state/counts: there is no parameter through which a
    # caller could pass full source text or evidence, and every free-form value is bounded.
    assert set(note) <= {"build_id", "record_id", "kind", "family", "state", "field_ids", "precedents_used"}
    assert len(note["family"]) == 80
    assert len(note["field_ids"]) == operation_events.MAX_NOTE_FIELD_IDS == 32
    assert all(len(field_id) == 120 for field_id in note["field_ids"])
    assert note["precedents_used"] == 0  # max(0, -5)
    assert huge_family_text not in str(note)
    assert long_field_id not in str(note)  # only the truncated 120-char prefix survives


def test_metadata_note_drops_a_state_outside_the_closed_vocabulary():
    operation_events.note_record_metadata("b1", "r1", "field_checked", state="not_a_real_state")
    note = operation_events.drain().metadata[0]
    assert "state" not in note


def test_metadata_note_rejects_an_unknown_kind():
    operation_events.note_record_metadata("b1", "r1", "not_a_kind")
    assert operation_events.drain().metadata == []


# -- realtime/events.py: observer -> llm.token -----------------------------------------------


def test_llm_token_reaches_only_its_job_topic_with_the_documented_payload_shape():
    broker = EventBroker()
    seen = _collect(broker)
    observer = RealtimeObserver(broker, managers=lambda: [], interval=0.01)
    observer.tick()

    text = "x" * 9000  # spans multiple MAX_TOKEN_EVENT_CHARS-sized pieces
    operation_events.note_generation_delta("job-1", text, owner="ann")
    operation_events.note_generation_finished("job-1", owner="ann")
    observer.tick()

    tokens = [event for event in seen if event.type == "llm.token"]
    assert len(tokens) == 3  # ceil(9000 / 4096)
    assert all(event.topics == ("job:job-1",) for event in tokens)
    assert all(event.resource_type == "job" and event.resource_id == "job-1" for event in tokens)
    assert all(event.audience == Audience(owner="ann", admin_only=False, capability="rag.jobs.own") for event in tokens)
    assert all(len(event.payload["generation"]["delta"]) <= 4096 for event in tokens)
    assert all(set(event.payload["generation"]) == {"seq", "delta", "gap", "final"} for event in tokens)
    assert "".join(event.payload["generation"]["delta"] for event in tokens) == text
    assert [event.payload["generation"]["seq"] for event in tokens] == [1, 2, 3]
    assert [event.payload["generation"]["final"] for event in tokens] == [False, False, True]
    assert [event.payload["generation"]["gap"] for event in tokens] == [False, False, False]


def test_llm_token_marks_only_the_first_piece_after_a_gap():
    broker = EventBroker()
    seen = _collect(broker)
    observer = RealtimeObserver(broker, managers=lambda: [], interval=0.01)
    observer.tick()

    operation_events.note_generation_delta("job-2", "a" * 33_000, owner="ann")  # truncated to 32,000
    observer.tick()

    tokens = [event for event in seen if event.type == "llm.token"]
    assert sum(len(event.payload["generation"]["delta"]) for event in tokens) == 32_000
    assert tokens[0].payload["generation"]["gap"] is True
    assert all(event.payload["generation"]["gap"] is False for event in tokens[1:])


def test_finished_with_no_pending_text_still_emits_one_final_empty_event():
    broker = EventBroker()
    seen = _collect(broker)
    observer = RealtimeObserver(broker, managers=lambda: [], interval=0.01)
    observer.tick()

    operation_events.note_generation_finished("job-4", owner="ann")
    observer.tick()

    tokens = [event for event in seen if event.type == "llm.token"]
    assert len(tokens) == 1
    assert tokens[0].payload["generation"] == {"seq": 1, "delta": "", "gap": False, "final": True}


def test_llm_token_owner_audience_excludes_other_users_and_wrong_topics():
    broker = EventBroker()
    seen = _collect(broker)
    observer = RealtimeObserver(broker, managers=lambda: [], interval=0.01)
    observer.tick()

    operation_events.note_generation_delta("rag-job-1", "a private draft", owner="ann")
    operation_events.note_generation_finished("rag-job-1", owner="ann")
    observer.tick()

    token_event = next(event for event in seen if event.type == "llm.token")
    owner_on_job_topic = Subscriber(username="ann", role="researcher", capabilities=frozenset({"rag.jobs.own"}), topics={"job:rag-job-1"})
    other_user_on_job_topic = Subscriber(username="bob", role="researcher", capabilities=frozenset({"rag.jobs.own"}), topics={"job:rag-job-1"})
    owner_on_wrong_topic = Subscriber(username="ann", role="researcher", capabilities=frozenset({"rag.jobs.own"}), topics={"corpus-build:rag-job-1"})

    assert owner_on_job_topic.may_receive(token_event) is True
    assert other_user_on_job_topic.may_receive(token_event) is False  # not the job's owner
    assert owner_on_wrong_topic.may_receive(token_event) is False  # only published on job:<id>


# -- realtime/events.py: observer -> corpus.record_* ------------------------------------------


def test_corpus_record_notes_reach_only_their_corpus_build_topic():
    broker = EventBroker()
    seen = _collect(broker)
    observer = RealtimeObserver(broker, managers=lambda: [], interval=0.01)
    observer.tick()

    operation_events.note_record_metadata("build-9", "rec-1", "record_started", precedents_used=3)
    operation_events.note_record_metadata(
        "build-9", "rec-1", "field_checked", family="discourse", state="complete", field_ids=["discourse_role"],
    )
    operation_events.note_record_metadata("build-9", "rec-1", "record_completed")
    observer.tick()

    record_events = [
        event for event in seen
        if event.type in {"corpus.record_started", "corpus.field_checked", "corpus.record_completed"}
    ]
    assert [event.type for event in record_events] == [
        "corpus.record_started", "corpus.field_checked", "corpus.record_completed",
    ]
    assert all(event.topics == ("corpus-build:build-9",) for event in record_events)
    assert all(event.audience == Audience(admin_only=True) for event in record_events)
    payloads = {event.type: event.payload for event in record_events}
    assert payloads["corpus.record_started"] == {"metadata": {"record_id": "rec-1", "precedents_used": 3}}
    assert payloads["corpus.field_checked"] == {
        "metadata": {"record_id": "rec-1", "family": "discourse", "state": "complete", "field_ids": ["discourse_role"]},
    }
    assert payloads["corpus.record_completed"] == {"metadata": {"record_id": "rec-1"}}

    started_event = next(event for event in record_events if event.type == "corpus.record_started")
    build_topic_sub = Subscriber(username="root", role="admin", topics={"corpus-build:build-9"})
    job_topic_sub = Subscriber(username="root", role="admin", topics={"job:build-9"})
    assert build_topic_sub.may_receive(started_event) is True
    assert job_topic_sub.may_receive(started_event) is False


# -- realtime/events.py: activity.changed dedup ---------------------------------------------


def test_activity_changed_deduplicates_identical_summaries():
    broker = EventBroker()
    seen = _collect(broker)
    observer = RealtimeObserver(broker, managers=lambda: [], interval=0.01)
    observer.tick()

    operation_events.note_activity("gutenberg", {"archive_status": "downloading", "bytes_done": 10})
    observer.tick()
    operation_events.note_activity("gutenberg", {"archive_status": "downloading", "bytes_done": 10})  # unchanged
    observer.tick()
    operation_events.note_activity("gutenberg", {"archive_status": "downloading", "bytes_done": 20})  # changed
    observer.tick()

    activity_events = [event for event in seen if event.type == "activity.changed"]
    assert len(activity_events) == 2
    assert activity_events[0].payload == {"activity": {"archive_status": "downloading", "bytes_done": 10}}
    assert activity_events[1].payload == {"activity": {"archive_status": "downloading", "bytes_done": 20}}
    assert all(event.topics == ("activity:gutenberg",) for event in activity_events)
    assert all(event.audience == Audience(admin_only=True) for event in activity_events)


# -- realtime/protocol.py + broker.py: ephemeral events are never replayed ----------------------


def test_ephemeral_event_types_are_exactly_the_documented_set():
    assert EPHEMERAL_EVENT_TYPES == frozenset({
        "llm.token", "corpus.record_started", "corpus.field_checked", "corpus.record_completed",
    })


def test_ephemeral_events_are_never_added_to_the_replay_ring():
    broker = EventBroker(replay_events=16)
    admin = Subscriber(username="root", role="admin", topics={"job:j1"})
    broker.register(admin)

    ephemeral = broker.publish(
        "llm.token", resource_type="job", resource_id="j1",
        payload={"generation": {"seq": 1, "delta": "hi", "gap": False, "final": False}},
        topics=("job:j1",), audience=Audience(admin_only=True),
    )
    normal = broker.publish(
        "job.progress", resource_type="job", resource_id="j1",
        payload={}, topics=("job:j1",), audience=Audience(admin_only=True),
    )

    replayed = broker.replay_since(admin, 0)
    assert replayed == [normal]
    assert ephemeral not in replayed


def test_reconnect_never_replays_corpus_record_notes():
    broker = EventBroker(replay_events=16)
    admin = Subscriber(username="root", role="admin", topics={"corpus-build:build-1"})
    broker.register(admin)

    broker.publish(
        "corpus.record_started", resource_type="corpus_build", resource_id="build-1",
        payload={"metadata": {"record_id": "r1"}}, topics=("corpus-build:build-1",), audience=Audience(admin_only=True),
    )
    kept = broker.publish(
        "corpus.build_changed", resource_type="corpus_build", resource_id="build-1",
        payload={}, topics=("corpus-build:build-1",), audience=Audience(admin_only=True),
    )

    assert broker.replay_since(admin, 0) == [kept]


# -- realtime/coalescing.py: droppable events are evicted first ---------------------------------


def test_droppable_ephemeral_events_are_evicted_before_non_droppable_ones():
    queue = OutgoingQueue(max_events=3)
    queue.put(_event(1, "llm.token", "j1"))  # ephemeral -> droppable
    queue.put(_event(2, "job.warning", "j1"))  # not droppable
    queue.put(_event(3, "job.completed", "j1"))  # not droppable
    queue.put(_event(4, "corpus.record_started", "c1"))  # ephemeral -> droppable; queue is full

    events, overflowed = queue.drain()

    assert not overflowed
    assert [event.event_id for event in events] == [2, 3, 4]  # event 1 (llm.token) was dropped first


def test_a_queue_of_only_non_droppable_events_overflows_instead_of_dropping_them():
    queue = OutgoingQueue(max_events=2)
    queue.put(_event(1, "job.warning", "j1"))
    queue.put(_event(2, "job.completed", "j1"))
    queue.put(_event(3, "job.failed", "j1"))  # nothing droppable to evict

    events, overflowed = queue.drain()
    assert overflowed
    assert [event.event_id for event in events] == [3]


# -- realtime/subscriptions.py: activity:gutenberg gating ---------------------------------------


def test_activity_kinds_constant_is_gutenberg_only():
    assert ACTIVITY_KINDS == frozenset({"gutenberg"})


def test_admin_may_subscribe_to_activity_gutenberg_but_a_researcher_may_not():
    admin = Subscriber(username="root", role="admin")
    researcher = Subscriber(username="ann", role="researcher")

    assert authorize_topic(admin, "activity:gutenberg") == TopicDecision("activity:gutenberg", True)
    decision = authorize_topic(researcher, "activity:gutenberg")
    assert decision.allowed is False and decision.code == CLOSE_FORBIDDEN


def test_an_unknown_activity_kind_is_refused_as_not_found_for_any_role():
    for subscriber in (Subscriber(username="root", role="admin"), Subscriber(username="ann", role="researcher")):
        decision = authorize_topic(subscriber, "activity:nonsense")
        assert decision.allowed is False and decision.code == CLOSE_NOT_FOUND


# -- job_rag.py -> rag.py wiring: generation deltas reach operation_events with the job's owner --


class _StubStore:
    def cache_rag_response(self, **kwargs):
        return {"record_id": "resp-1"}


class _ImmediateThread:
    """Runs its target synchronously instead of on a background thread."""

    def __init__(self, target, args=(), kwargs=None, daemon=None, name=None):
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}

    def start(self) -> None:
        self._target(*self._args, **self._kwargs)

    def join(self, timeout=None) -> None:
        return None

    def is_alive(self) -> bool:
        return False


def test_rag_job_generation_deltas_are_noted_with_the_jobs_owner(monkeypatch):
    captured: dict = {}

    def fake_run_rag_pipeline(body, store, *, progress=None, cancelled=None, owner=None, on_generation_delta=None):
        captured["owner"] = owner
        on_generation_delta("Hello ")
        on_generation_delta("world.")
        return {
            "answer": "Hello world.",
            "raw_answer": "Hello world.",
            "prompt": body.prompt,
            "evidence": [],
            "provider": body.provider,
            "model": body.model,
        }

    monkeypatch.setattr(job_rag, "run_rag_pipeline", fake_run_rag_pipeline)
    monkeypatch.setattr(job_rag.threading, "Thread", _ImmediateThread)

    manager = RAGJobManager(_StubStore(), ollama_max_concurrent=1)
    body = RAGRunRequest(prompt="What is deconstruction?", source_collection="corpus", provider="openai", model="test-model")
    created = manager.create(body, owner="ann")
    job_id = created["id"]

    assert manager.get(job_id)["status"] == "completed"
    assert captured["owner"] == "ann"

    drained = operation_events.drain()
    buffer = drained.generation[job_id]
    assert "".join(buffer.chunks) == "Hello world."
    assert buffer.owner == "ann"
    assert buffer.finished is True
    assert buffer.gap is False


# -- corpus_metadata_enrichment_execution.py: _with_progress_notes wraps without changing behavior --


def test_with_progress_notes_calls_the_wrapped_callback_and_notes_field_progress():
    from app.corpus_metadata_enrichment_execution import MetadataEnrichmentExecutionMixin

    schema = default_schema()

    class Harness(MetadataEnrichmentExecutionMixin):
        def _schema_for(self, build_id):
            return schema

    harness = Harness()
    calls: list[tuple] = []

    def stage_callback(record, family, state, error):
        calls.append((record.get("record_id"), family, state, error))

    wrapped = harness._with_progress_notes("build-1", stage_callback)
    record = {"record_id": "r1", "text": "SENSITIVE SOURCE TEXT " * 5000}

    result = wrapped(record, "discourse", "complete", None)

    # The wrapper must not swallow or alter the wrapped callback's own contract.
    assert result is None
    assert calls == [("r1", "discourse", "complete", None)]

    drained = operation_events.drain()
    note = drained.metadata[0]
    assert note["kind"] == "field_checked"
    assert note["build_id"] == "build-1" and note["record_id"] == "r1"
    assert note["family"] == "discourse" and note["state"] == "complete"
    assert note["field_ids"] == sorted(schema.family_fields().get("discourse", set()))
    assert "SENSITIVE SOURCE TEXT" not in str(note)


def test_with_progress_notes_skips_the_note_for_a_state_outside_the_closed_vocabulary():
    from app.corpus_metadata_enrichment_execution import MetadataEnrichmentExecutionMixin

    class Harness(MetadataEnrichmentExecutionMixin):
        def _schema_for(self, build_id):
            return default_schema()

    harness = Harness()
    wrapped = harness._with_progress_notes("build-1", None)
    wrapped({"record_id": "r1"}, "discourse", "running", None)  # "running" is not a terminal family state

    assert operation_events.drain().metadata == []


# -- gutenberg_catalogue.py: state writes notify note_activity -----------------------------------


def test_gutenberg_state_write_notes_a_bounded_activity_summary(tmp_path):
    service = GutenbergOfflineService(tmp_path / "state.sqlite", tmp_path / "archive.zip", start_worker=False)
    operation_events.drain()  # clear construction-time notes, if any

    service.set_archive_status("start")

    drained = operation_events.drain()
    summary = drained.activity["gutenberg"]
    assert summary == service.realtime_summary()
    assert set(summary) == {
        "catalogue_status", "archive_status", "bytes_done", "total_bytes", "ready", "search_ready", "has_error",
    }
    assert summary["archive_status"] == "downloading"
    # Never a path, URL, or error string.
    assert str(service.archive_path) not in str(summary)
    assert str(service.db_path) not in str(summary)


def test_gutenberg_repeated_identical_writes_do_not_repeat_the_published_event(tmp_path):
    service = GutenbergOfflineService(tmp_path / "state.sqlite", tmp_path / "archive.zip", start_worker=False)
    operation_events.drain()

    broker = EventBroker()
    seen = _collect(broker)
    observer = RealtimeObserver(broker, managers=lambda: [], interval=0.01)
    observer.tick()

    service.set_archive_status("start")
    observer.tick()
    service.set_archive_status("start")  # same action; the resulting summary is unchanged
    observer.tick()
    service.set_archive_status("pause")  # this does change the summary
    observer.tick()

    activity_events = [event for event in seen if event.type == "activity.changed"]
    # gutenberg_catalogue._changed() itself always calls note_activity unconditionally
    # (its "changed" check does not compare to the previous value); deduplication happens
    # downstream, in the observer's own latest-published-value comparison.
    assert [event.payload["activity"]["archive_status"] for event in activity_events] == ["downloading", "paused"]
