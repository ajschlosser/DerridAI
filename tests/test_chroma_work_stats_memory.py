# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

from __future__ import annotations

from app.chroma_store import ChromaStore


class _WorkStatsCollection:
    def __init__(self, count: int = 1200) -> None:
        self.rows = []
        self.calls: list[dict] = []
        for index in range(count):
            work = "Of Grammatology" if index < 700 else "Writing and Difference"
            publisher = "Stable Press" if work == "Writing and Difference" else (
                "Press A" if index == 0 else "Press B"
            )
            self.rows.append(
                (
                    f"r-{index}",
                    "one two three four",
                    {
                        "work": work,
                        "document_author": "Jacques Derrida",
                        "publisher": publisher,
                    },
                )
            )

    def get(self, *, include=(), limit=None, offset=0):
        self.calls.append({
            "include": list(include),
            "limit": limit,
            "offset": offset,
        })
        stop = offset + int(limit or len(self.rows))
        rows = self.rows[offset:stop]
        return {
            "ids": [row[0] for row in rows],
            "documents": [row[1] for row in rows],
            "metadatas": [row[2] for row in rows],
        }


def _store(collection: _WorkStatsCollection) -> ChromaStore:
    store = object.__new__(ChromaStore)
    store._collection = lambda _name: collection
    return store


def test_work_stats_scans_large_collections_in_bounded_pages() -> None:
    collection = _WorkStatsCollection()

    rows = _store(collection).work_stats("corpus")

    assert [call["limit"] for call in collection.calls] == [512, 512, 512]
    assert [call["offset"] for call in collection.calls] == [0, 512, 1024]
    assert all(
        call["include"] == ["metadatas", "documents"]
        for call in collection.calls
    )

    by_work = {row["work"]: row for row in rows}
    grammatology = by_work["Of Grammatology"]
    assert grammatology["count"] == 700
    assert grammatology["total_words"] == 2800
    assert grammatology["average_record_length"] == 4
    assert grammatology["document_author"] == "Jacques Derrida"
    assert grammatology["publisher_mixed"] is True
    assert "publisher" not in grammatology

    writing = by_work["Writing and Difference"]
    assert writing["count"] == 500
    assert writing["publisher"] == "Stable Press"
    assert "publisher_mixed" not in writing


class _RecordBrowseCollection:
    def __init__(self, count: int = 1200) -> None:
        self.rows = [
            (
                f"r-{index:04d}",
                f"passage {index}",
                {
                    "_record_id": f"record-{index:04d}",
                    "_document_field": "text",
                    "work": "Work A" if index < 1100 else "Work B",
                    "document_author": "Jacques Derrida" if index % 2 == 0 else "Other",
                    "year": 1900 + index,
                    "tags": ["target", str(index)] if index % 100 == 0 else ["other"],
                },
            )
            for index in range(count)
        ]
        self.calls: list[dict] = []

    def count(self) -> int:
        return len(self.rows)

    def get(self, *, where=None, include=(), limit=None, offset=0):
        self.calls.append({
            "where": where,
            "include": list(include),
            "limit": limit,
            "offset": offset,
        })
        rows = self.rows
        if where:
            rows = [
                row
                for row in rows
                if all(row[2].get(key) == value for key, value in where.items())
            ]
        stop = offset + int(limit or len(rows))
        rows = rows[offset:stop]
        payload = {"ids": [row[0] for row in rows]}
        if "documents" in include:
            payload["documents"] = [row[1] for row in rows]
        if "metadatas" in include:
            payload["metadatas"] = [row[2] for row in rows]
        return payload


def test_filtered_sorted_record_browsing_keeps_only_a_bounded_window() -> None:
    collection = _RecordBrowseCollection()
    store = _store(collection)

    result = store.get_records(
        "corpus",
        limit=5,
        offset=3,
        sort_field="year",
        sort_dir="desc",
        filters={"document_author": "derrida"},
    )

    assert result["count"] == 600
    assert [row["year"] for row in result["records"]] == [
        3092,
        3090,
        3088,
        3086,
        3084,
    ]
    scan_calls = [
        call
        for call in collection.calls
        if call["include"] == ["documents", "metadatas"]
    ]
    assert [call["limit"] for call in scan_calls] == [512, 512, 512]
    assert [call["offset"] for call in scan_calls] == [0, 512, 1024]


def test_plain_work_browse_counts_with_id_only_pages() -> None:
    collection = _RecordBrowseCollection()
    store = _store(collection)

    result = store.get_records("corpus", work="Work A", limit=10, offset=20)

    assert result["count"] == 1100
    assert len(result["records"]) == 10
    count_calls = [
        call
        for call in collection.calls
        if call["include"] == [] and call["where"] == {"work": "Work A"}
    ]
    assert [call["limit"] for call in count_calls] == [1000, 1000]
    assert [call["offset"] for call in count_calls] == [0, 1000]



def test_contains_filter_search_stops_after_bounded_page_finds_enough_rows() -> None:
    collection = _RecordBrowseCollection()
    store = _store(collection)

    rows = store.filter_search(
        "corpus",
        3,
        where={"tags": {"$contains": "target"}},
    )

    assert [row["id"] for row in rows] == [
        "r-0000",
        "r-0100",
        "r-0200",
    ]
    scan_calls = [
        call
        for call in collection.calls
        if call["include"] == ["documents", "metadatas"]
    ]
    assert len(scan_calls) == 1
    assert scan_calls[0]["limit"] == 512
    assert scan_calls[0]["offset"] == 0



def test_keyword_fallback_scans_only_bounded_pages() -> None:
    collection = _RecordBrowseCollection()
    store = _store(collection)

    rows = store.keyword_search("corpus", "PASSAGE 1199", 1)

    assert [row["id"] for row in rows] == ["r-1199"]
    scan_calls = [
        call
        for call in collection.calls
        if call["include"] == ["documents", "metadatas"]
    ]
    assert [call["limit"] for call in scan_calls] == [512, 488]
    assert [call["offset"] for call in scan_calls] == [0, 512]
    assert all(call["limit"] is not None for call in scan_calls)
