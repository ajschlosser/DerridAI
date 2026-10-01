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


def test_every_registered_resource_is_admin_audience():
    assert DATA_RESOURCES
    assert all(spec.audience.admin_only for spec in DATA_RESOURCES.values())


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
