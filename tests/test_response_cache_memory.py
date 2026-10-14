# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

from __future__ import annotations

from app.chroma_store import ChromaStore


class _ResponseCacheCollection:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.rows = [
            ("r1", "old answer", {"_record_id": "resp-1", "question": "old", "created_at": "2026-01-01T00:00:00+00:00"}),
            ("r2", "newer answer", {"_record_id": "resp-2", "question": "trace", "created_at": "2026-01-03T00:00:00+00:00"}),
            ("r3", "middle answer", {"_record_id": "resp-3", "question": "trace supplement", "created_at": "2026-01-02T00:00:00+00:00"}),
            ("r4", "newest answer", {"_record_id": "resp-4", "question": "latest", "created_at": "2026-01-04T00:00:00+00:00"}),
        ]

    def count(self) -> int:
        return len(self.rows)

    def get(self, *, ids=None, include=(), limit=None, offset=0):
        self.calls.append({
            "ids": list(ids) if ids is not None else None,
            "include": list(include),
            "limit": limit,
            "offset": offset,
        })
        if ids is not None:
            wanted = set(ids)
            rows = [row for row in self.rows if row[0] in wanted]
        else:
            stop = offset + int(limit or len(self.rows))
            rows = self.rows[offset:stop]
        payload = {"ids": [row[0] for row in rows]}
        if "documents" in include:
            payload["documents"] = [row[1] for row in rows]
        if "metadatas" in include:
            payload["metadatas"] = [row[2] for row in rows]
        return payload


class _ResponseCacheClient:
    def __init__(self, collection: _ResponseCacheCollection) -> None:
        self.collection = collection

    def get_collection(self, *, name: str):
        assert name == "derridai_response_cache"
        return self.collection


def _store(collection: _ResponseCacheCollection) -> ChromaStore:
    store = object.__new__(ChromaStore)
    store._client = _ResponseCacheClient(collection)
    return store


def test_response_cache_page_scans_metadata_then_hydrates_only_requested_rows() -> None:
    collection = _ResponseCacheCollection()
    result = _store(collection).get_response_cache_records(limit=2, offset=1)

    assert result["total"] == 4
    assert result["count"] == 4
    assert [row["record_id"] for row in result["records"]] == ["resp-2", "resp-3"]

    scan_calls = [call for call in collection.calls if call["ids"] is None]
    assert scan_calls == [{
        "ids": None,
        "include": ["metadatas"],
        "limit": 4,
        "offset": 0,
    }]
    hydrate_calls = [call for call in collection.calls if call["ids"] is not None]
    assert len(hydrate_calls) == 1
    assert hydrate_calls[0]["ids"] == ["r2", "r3"]
    assert hydrate_calls[0]["include"] == ["documents", "metadatas"]


def test_response_cache_query_filters_metadata_without_hydrating_nonmatches() -> None:
    collection = _ResponseCacheCollection()
    result = _store(collection).get_response_cache_records(limit=10, query="trace")

    assert result["total"] == 4
    assert result["count"] == 2
    assert [row["record_id"] for row in result["records"]] == ["resp-2", "resp-3"]
    hydrate_calls = [call for call in collection.calls if call["ids"] is not None]
    assert len(hydrate_calls) == 1
    assert hydrate_calls[0]["ids"] == ["r2", "r3"]


def test_response_cache_maintenance_iterator_is_page_bounded() -> None:
    collection = _ResponseCacheCollection()
    records = list(_store(collection).iter_response_cache_records(page_size=2))

    assert [row["record_id"] for row in records] == ["resp-1", "resp-2", "resp-3", "resp-4"]
    scan_calls = [call for call in collection.calls if call["ids"] is None]
    assert [call["limit"] for call in scan_calls] == [2, 2, 2]
    assert [call["offset"] for call in scan_calls] == [0, 2, 4]
    assert all(call["include"] == ["documents", "metadatas"] for call in scan_calls)


def test_response_cache_count_does_not_read_records() -> None:
    collection = _ResponseCacheCollection()
    assert _store(collection).response_cache_count() == 4
    assert collection.calls == []
