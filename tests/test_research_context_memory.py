# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

from __future__ import annotations

from app.chroma_store import ChromaStore


class _DocumentCollection:
    def __init__(self, count: int = 1200) -> None:
        self.rows = [
            (
                f"c-{index:04d}",
                f"passage {index}",
                {
                    "_record_id": f"record-{index:04d}",
                    "_document_field": "text",
                    "source_document_id": "source-1",
                    "record_ordinal": index,
                },
            )
            for index in range(count)
        ]
        self.calls: list[dict] = []

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
        return {
            "ids": [row[0] for row in rows],
            "documents": [row[1] for row in rows],
            "metadatas": [row[2] for row in rows],
        }


def test_same_document_context_reads_chroma_in_bounded_pages() -> None:
    collection = _DocumentCollection()
    store = object.__new__(ChromaStore)
    store._collection = lambda _name: collection

    records = store.document_records("corpus", "source-1")

    assert len(records) == 1200
    assert records[0]["record_id"] == "record-0000"
    assert records[-1]["record_id"] == "record-1199"
    assert [call["limit"] for call in collection.calls] == [512, 512, 512]
    assert [call["offset"] for call in collection.calls] == [0, 512, 1024]
    assert all(
        call["include"] == ["documents", "metadatas"]
        for call in collection.calls
    )
