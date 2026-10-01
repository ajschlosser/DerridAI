# Copyright 2026 Aaron John Schlosser, PhD.
"""Key-level data invalidation on ``data:<key>``: registry, authorization, collapse, emitters."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import operation_events  # noqa: E402
from app.auth import AuthStore  # noqa: E402
from app.realtime.broker import EventBroker  # noqa: E402
from app.realtime.events import RealtimeObserver  # noqa: E402
from app.realtime.protocol import valid_topic  # noqa: E402
from app.realtime.resources import DATA_RESOURCES  # noqa: E402
from app.realtime.subscriptions import authorize_topic  # noqa: E402


@pytest.fixture(autouse=True)
def clean_notes():
    operation_events.drain()
    yield
    operation_events.drain()


def _observer():
    broker = EventBroker()
    seen: list = []
    original = broker.publish

    def capture(*args, **kwargs):
        event = original(*args, **kwargs)
        if event is not None:
            seen.append(event)
        return event

    broker.publish = capture  # type: ignore[method-assign]
    observer = RealtimeObserver(broker, managers=lambda: [], interval=0.01)
    observer.tick()
    return observer, seen


def test_data_topics_are_valid_and_registered_keys_are_admin_only():
    assert valid_topic("data:users")
    assert not valid_topic("data:")
    admin = SimpleNamespace(is_admin=True, capabilities=frozenset(), username="root")
    researcher = SimpleNamespace(is_admin=False, capabilities=frozenset({"rag.run"}), username="ann")
    assert authorize_topic(admin, "data:users").allowed
    denied = authorize_topic(researcher, "data:users")
    assert (denied.allowed, denied.code) == (False, 4403)
    unknown = authorize_topic(admin, "data:nope")
    assert (unknown.allowed, unknown.code) == (False, 4404)


def test_repeated_notes_collapse_into_one_text_free_event():
    observer, seen = _observer()
    for _ in range(5):
        operation_events.note_resource_changed("users")
    operation_events.note_resource_changed("roles")
    observer.tick()
    assert sorted((e.type, e.resource_id) for e in seen) == [
        ("resource.changed", "roles"),
        ("resource.changed", "users"),
    ]
    users = next(e for e in seen if e.resource_id == "users")
    assert users.payload == {"resource": "users"}
    assert users.topics == ("data:users",)
    assert users.audience.admin_only
    assert users.coalescable
    observer.tick()
    assert len(seen) == 2


def test_unregistered_resources_are_never_published():
    observer, seen = _observer()
    operation_events.note_resource_changed("not-registered")
    observer.tick()
    assert seen == []


def test_every_registered_resource_is_admin_only_unless_it_names_a_read_capability():
    assert DATA_RESOURCES
    for key, spec in DATA_RESOURCES.items():
        if spec.capability:
            assert spec.audience.capability_only and not spec.audience.admin_only, key
        else:
            assert spec.audience.admin_only and not spec.audience.capability_only, key


@pytest.fixture()
def store(tmp_path, monkeypatch):
    from app import auth

    monkeypatch.setattr(auth, "settings", SimpleNamespace(auth_db_path=str(tmp_path / "auth.sqlite3")))
    return AuthStore()


def _noted() -> frozenset[str]:
    return operation_events.drain().resources


def test_user_and_role_mutations_note_their_resource(store):
    admin = store.bootstrap_admin("root", "secret-pass")
    _noted()
    ann = store.create_user("ann", "secret-pass", "researcher")
    assert _noted() == {"users"}
    store.update_user(ann.id, active=False)
    assert _noted() == {"users"}
    store.delete_user(ann.id)
    assert _noted() == {"users"}
    role = store.create_role("Reader")
    assert _noted() == {"roles"}
    store.set_role_permissions(role["id"], [])
    assert _noted() == {"roles"}
    store.delete_role(role["id"])
    assert _noted() == {"roles"}
    with pytest.raises(ValueError):
        store.delete_user(admin.id)
    assert _noted() == frozenset()


def test_frontend_resource_keys_match_the_server_registry():
    source = (Path(__file__).resolve().parents[1] / "web/src/realtime/resourceKeys.ts").read_text()
    match = re.search(r"DATA_RESOURCES = \[([^\]]*)\] as const", source)
    assert match, "web/src/realtime/resourceKeys.ts must declare DATA_RESOURCES"
    assert set(re.findall(r'"([a-z_]+)"', match.group(1))) == set(DATA_RESOURCES)


def test_pipeline_store_writes_note_their_resources(tmp_path):
    from app.pipelines.store import PipelineStore

    store = PipelineStore(tmp_path / "p.db")
    operation_events.drain()
    store.clear_all()
    drained = operation_events.drain()
    assert {"pipelines", "pipeline_runs"} <= set(drained.resources)

    assert store.delete_assignment("research") is False
    assert "pipelines" in operation_events.drain().resources


def test_vector_store_mutations_note_collections_changed():
    from app.chroma_store import ChromaStore

    class _Collection:
        metadata: dict = {}

        def modify(self, metadata):
            self.metadata = metadata

    store = ChromaStore.__new__(ChromaStore)
    store._collection = lambda name: _Collection()  # type: ignore[method-assign]
    store._public_store = lambda collection: {}  # type: ignore[method-assign]
    operation_events.drain()
    store.set_protection("x", True)
    assert "vector_collections" in operation_events.drain().resources


def test_record_content_mutations_note_corpus_records_but_not_a_protection_flip():
    from app.chroma_store import ChromaStore

    class _Collection:
        metadata: dict = {}

        def modify(self, metadata):
            self.metadata = metadata

        def delete(self, **_kwargs):
            return None

    store = ChromaStore.__new__(ChromaStore)
    store._collection = lambda name: _Collection()  # type: ignore[method-assign]
    store._public_store = lambda collection: {}  # type: ignore[method-assign]
    operation_events.drain()
    store.set_protection("x", True)
    assert "corpus_records" not in operation_events.drain().resources
    store.delete_record("x", "chroma-1")
    drained = operation_events.drain().resources
    assert {"corpus_records", "vector_collections"} <= set(drained)


def test_benchmark_cases_and_results_note_pipeline_benchmarks(tmp_path):
    from test_pipeline_benchmark import _case, _run

    from app.pipelines.store import PipelineStore

    store = PipelineStore(tmp_path / "b.db")
    case = _case()
    operation_events.drain()
    store.put_benchmark_case(case)
    assert "pipeline_benchmarks" in operation_events.drain().resources
    store.put_benchmark(_run(case))
    assert "pipeline_benchmarks" in operation_events.drain().resources
    store.benchmarks.clear()
    assert "pipeline_benchmarks" in operation_events.drain().resources


def test_capability_resources_reach_holders_of_the_read_capability_only():
    from app.realtime.broker import Subscriber, audience_allows
    from app.realtime.protocol import Audience
    from app.realtime.resources import follows_any_resource

    reader = Subscriber(username="ann", role="researcher", capabilities=frozenset({"corpus.read"}))
    other = Subscriber(username="bob", role="researcher", capabilities=frozenset({"rag.run"}))
    admin = Subscriber(username="root", role="admin")

    for key in ("corpus_records", "vector_collections"):
        spec = DATA_RESOURCES[key]
        assert spec.allows(reader) and spec.allows(admin) and not spec.allows(other)
        assert authorize_topic(reader, f"data:{key}").allowed
        assert not authorize_topic(other, f"data:{key}").allowed
        assert audience_allows(spec.audience, username="ann", is_admin=False, capabilities=reader.capabilities)
        assert not audience_allows(spec.audience, username="bob", is_admin=False, capabilities=other.capabilities)

    # Resources whose REST route is administrator-only stay so, whatever capabilities a user holds.
    holder = Subscriber(username="ann", role="researcher", capabilities=frozenset({"corpus.read", "page.faq"}))
    for key in ("response_library", "users", "roles", "pipelines", "pipeline_runs", "pipeline_benchmarks", "metadata_exemplars"):
        assert not DATA_RESOURCES[key].allows(holder), key
    assert follows_any_resource(reader) and not follows_any_resource(other)

    # The new flag cannot loosen owned or administrator-only audiences.
    job = Audience(owner="ann", admin_only=False, capability="rag.jobs.own")
    assert not audience_allows(job, username="bob", is_admin=False, capabilities=frozenset({"rag.jobs.own"}))
    assert not audience_allows(Audience(admin_only=True), username="ann", is_admin=False, capabilities=reader.capabilities)


def test_corpus_record_notice_carries_no_values_to_a_researcher():
    observer, seen = _observer()
    operation_events.note_resource_changed("corpus_records")
    observer.tick()
    event = next(e for e in seen if e.resource_id == "corpus_records")
    assert event.payload == {"resource": "corpus_records"}
    assert event.audience.capability == "corpus.read" and event.audience.capability_only
