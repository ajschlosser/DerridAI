# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from app.routers import system_data as system_data_router


def test_system_data_deletes_one_response_through_admin_boundary(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(system_data_router, "require_admin", lambda _request: None)
    monkeypatch.setattr(
        system_data_router.store,
        "delete_record",
        lambda collection, record_id: calls.append((collection, record_id)),
    )

    result = system_data_router.delete_system_response_cache_record("rag-1", object())

    assert result == {"deleted": "rag-1"}
    assert calls == [("_response_cache", "rag-1")]


def test_system_data_clear_response_cache_reports_affected_count(monkeypatch) -> None:
    calls: list[tuple[str, bool]] = []
    monkeypatch.setattr(system_data_router, "require_admin", lambda _request: None)
    monkeypatch.setattr(
        system_data_router.store,
        "get_response_cache_records",
        lambda **_kwargs: {"total": 12},
    )
    monkeypatch.setattr(
        system_data_router.store,
        "delete_store",
        lambda name, *, force=False: calls.append((name, force)),
    )

    result = system_data_router.clear_system_response_cache(object())

    assert result == {"deleted": 12}
    assert calls == [("_response_cache", True)]


def test_system_data_clear_empty_cache_does_not_delete_collection(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(system_data_router, "require_admin", lambda _request: None)
    monkeypatch.setattr(
        system_data_router.store,
        "get_response_cache_records",
        lambda **_kwargs: {"total": 0},
    )
    monkeypatch.setattr(
        system_data_router.store,
        "delete_store",
        lambda name, **_kwargs: calls.append(name),
    )

    result = system_data_router.clear_system_response_cache(object())

    assert result == {"deleted": 0}
    assert calls == []
