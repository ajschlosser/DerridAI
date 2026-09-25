# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.metadata_memory import MetadataMemoryService


class FakeCollection:
    def __init__(self, name, system_kind, rows):
        self.name = name
        self.metadata = {"derridai_system_collection": system_kind}
        self.rows = rows

    def count(self):
        return len(self.rows)

    def get(self, *, limit=500, offset=0, include=None):
        page = self.rows[offset : offset + limit]
        return {
            "ids": [row["id"] for row in page],
            "documents": [row.get("document", "") for row in page],
            "metadatas": [row.get("metadata", {}) for row in page],
        }


class FakeClient:
    def __init__(self, collections):
        self.collections = {item.name: item for item in collections}

    def list_collections(self):
        return list(self.collections.values())

    def get_collection(self, *, name):
        return self.collections[name]


class FakeStore:
    def __init__(self, collections):
        self.client = FakeClient(collections)


class FakeCorpusRepository:
    def get_build(self, build_id):
        assert build_id == "build-1"
        return {"build_id": build_id, "asset_id": "asset-1"}

    def load_blocks(self, asset_id):
        assert asset_id == "asset-1"
        return [
            {"block_id": "b1", "text": "Context before."},
            {"block_id": "b2", "text": "For Levinas, responsibility precedes freedom."},
        ]

    def load_records(self, build_id):
        assert build_id == "build-1"
        return [{"record_id": "r1", "record_revision": 4}]


def progressive_row(*, kind="positive", rejected=""):
    return {
        "id": "mex-1",
        "document": "Context before. For Levinas, responsibility precedes freedom.",
        "metadata": {
            "metadata_exemplar_id": "mex-1",
            "scope_id": "build-1",
            "record_id": "r1",
            "record_revision": 4,
            "source_document_id": "asset-1",
            "field_name": "position_holder",
            "field_value_json": '"Levinas"',
            "rejected_value_json": rejected,
            "kind": kind,
            "assertion_status": "human_override",
            "assertion_method": "human_review_of_llm_proposal",
            "reviewed_at": "2026-09-24T00:00:00Z",
            "schema_id": "derrida",
            "schema_version": "v1",
            "language": "en",
            "region_type": "main_text",
            "page_start": 12,
            "page_end": 12,
            "evidence_hash": hashlib.sha256(
                b"For Levinas, responsibility precedes freedom."
            ).hexdigest(),
            "evidence_block_ids_json": '["b2"]',
        },
    }


def reviewer_memory_row():
    return {
        "id": "legacy-1",
        "document": "Whole reviewed record text.",
        "metadata": {
            "source_record_id": "r1",
            "memory_field": "position_holder",
            "memory_value": '"Levinas"',
            "schema_version": "v1",
            "status": "human_confirmed",
        },
    }


def test_inspector_ignores_superseded_reviewer_memory_and_uses_evidence_bound_entries():
    service = MetadataMemoryService(
        FakeStore(
            [
                FakeCollection(
                    "derridai_metadata_exemplars",
                    "metadata_exemplars",
                    [progressive_row()],
                ),
                FakeCollection(
                    "derridai_metadata_memory",
                    "metadata_memory",
                    [reviewer_memory_row()],
                ),
            ]
        ),
        FakeCorpusRepository(),
    )

    payload = service.list_entries()

    assert payload["available"] is True
    assert payload["total"] == 1
    assert payload["summary"]["backends"] == 1
    assert payload["summary"]["entries"] == 1
    item = payload["items"][0]
    assert item["memory_type"] == "evidence_bound"
    assert item["value"] == "Levinas"
    assert item["evidence_text"] == "For Levinas, responsibility precedes freedom."
    assert item["source_current"] is True
    assert item["evidence_current"] is True


def test_inspector_exposes_correction_as_negative_precedent():
    service = MetadataMemoryService(
        FakeStore(
            [
                FakeCollection(
                    "derridai_metadata_exemplars",
                    "metadata_exemplars",
                    [progressive_row(kind="correction", rejected='"Derrida"')],
                )
            ]
        ),
        FakeCorpusRepository(),
    )

    item = service.list_entries()["items"][0]

    assert item["kind"] == "correction"
    assert item["value"] == "Levinas"
    assert item["rejected_value"] == "Derrida"
    assert item["authority"] == "human_override"
    assert item["review_method"] == "human_review_of_llm_proposal"


def test_inspector_filters_conceptual_fields_without_exposing_collection_names():
    rows = [
        progressive_row(),
        {
            **progressive_row(),
            "id": "mex-2",
            "metadata": {
                **progressive_row()["metadata"],
                "metadata_exemplar_id": "mex-2",
                "record_id": "r2",
                "field_name": "stance",
                "field_value_json": '"critical"',
            },
        },
    ]
    service = MetadataMemoryService(
        FakeStore([FakeCollection("derridai_metadata_exemplars", "metadata_exemplars", rows)])
    )

    payload = service.list_entries(field="stance")

    assert payload["total"] == 1
    assert payload["items"][0]["field"] == "stance"
    assert "derridai_metadata_exemplars" not in str(payload)


def test_inspector_fails_open_when_memory_backend_is_unavailable():
    class BrokenClient:
        def list_collections(self):
            raise RuntimeError("memory backend unavailable")

    class BrokenStore:
        client = BrokenClient()

    payload = MetadataMemoryService(BrokenStore()).list_entries()

    assert payload["available"] is False
    assert payload["items"] == []
    assert "memory backend unavailable" in payload["error"]



def test_inspector_marks_changed_evidence_as_not_current():
    row = progressive_row()
    row["metadata"]["evidence_hash"] = "not-the-current-evidence-hash"
    service = MetadataMemoryService(
        FakeStore(
            [
                FakeCollection(
                    "derridai_metadata_exemplars",
                    "metadata_exemplars",
                    [row],
                )
            ]
        ),
        FakeCorpusRepository(),
    )

    item = service.list_entries()["items"][0]

    assert item["source_current"] is True
    assert item["evidence_current"] is False
