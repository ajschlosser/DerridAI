# Copyright 2026 Aaron John Schlosser, PhD.
"""System Data inspection of progressive metadata exemplars."""

from __future__ import annotations

from app.system_metadata_exemplars import MetadataExemplarInspector


def _matches(row, where):
    if not where:
        return True
    if "$and" in where:
        return all(_matches(row, item) for item in where["$and"])
    return all(row.get(key) == value for key, value in where.items())


class FakeCollection:
    def __init__(self):
        self.rows = [
            {
                "id": "mex-1",
                "document": "Derrida introduces Levinas's position and then questions it.",
                "metadata": {
                    "scope_id": "build-1",
                    "record_id": "r1",
                    "record_revision": 4,
                    "source_document_id": "doc-1",
                    "field_name": "position_holder",
                    "field_value_json": '"Levinas"',
                    "kind": "positive",
                    "assertion_status": "human_confirmed",
                    "schema_id": "derrida",
                    "schema_version": "v7",
                    "language": "en",
                    "region_type": "main_text",
                    "evidence_hash": "abc123",
                    "evidence_block_ids_json": '["b2"]',
                },
            },
            {
                "id": "mex-2",
                "document": "A quotation is explicitly attributed to Derrida.",
                "metadata": {
                    "scope_id": "build-2",
                    "record_id": "r2",
                    "record_revision": 2,
                    "source_document_id": "doc-2",
                    "field_name": "quoted_speaker",
                    "field_value_json": '["Derrida"]',
                    "kind": "correction",
                    "assertion_status": "human_override",
                    "schema_id": "derrida",
                    "schema_version": "v7",
                    "language": "fr",
                    "region_type": "quotation",
                    "evidence_hash": "def456",
                    "evidence_block_ids_json": '["b9","b10"]',
                },
            },
        ]

    def get(self, *, include, where=None, limit=None, offset=0):
        rows = [row for row in self.rows if _matches(row["metadata"], where)]
        if limit is not None:
            rows = rows[offset : offset + limit]
        return {
            "ids": [row["id"] for row in rows],
            "documents": [row["document"] for row in rows],
            "metadatas": [row["metadata"] for row in rows],
        }


class FakeClient:
    def __init__(self, collection=None):
        self.collection = collection

    def get_collection(self, *, name):
        assert name == "derridai_metadata_exemplars"
        if self.collection is None:
            raise RuntimeError("collection not found")
        return self.collection


class FakeStore:
    def __init__(self, collection=None):
        self.client = FakeClient(collection)

    @staticmethod
    def _is_missing_collection_error(exc):
        return "not found" in str(exc).casefold()


def test_exemplar_inspector_returns_semantic_rows_and_facets():
    inspector = MetadataExemplarInspector(FakeStore(FakeCollection()))

    payload = inspector.rows(limit=25, offset=0)

    assert payload["exists"] is True
    assert payload["count"] == 2
    assert payload["facets"]["fields"] == ["position_holder", "quoted_speaker"]
    assert payload["facets"]["kinds"] == ["correction", "positive"]
    assert payload["facets"]["languages"] == ["en", "fr"]
    assert payload["rows"][0] == {
        "exemplar_id": "mex-1",
        "scope_id": "build-1",
        "record_id": "r1",
        "record_revision": 4,
        "source_document_id": "doc-1",
        "field_name": "position_holder",
        "field_value": "Levinas",
        "kind": "positive",
        "assertion_status": "human_confirmed",
        "schema_id": "derrida",
        "schema_version": "v7",
        "language": "en",
        "region_type": "main_text",
        "evidence_hash": "abc123",
        "evidence_block_ids": ["b2"],
        "context_text": "Derrida introduces Levinas's position and then questions it.",
    }


def test_exemplar_inspector_filters_without_exposing_vector_details():
    inspector = MetadataExemplarInspector(FakeStore(FakeCollection()))

    payload = inspector.rows(field="quoted_speaker", language="fr")

    assert payload["count"] == 1
    row = payload["rows"][0]
    assert row["kind"] == "correction"
    assert row["field_value"] == ["Derrida"]
    assert "embedding" not in row
    assert "_chroma_id" not in row
    assert "distance" not in row


def test_exemplar_inspector_treats_missing_projection_as_empty_system_data():
    inspector = MetadataExemplarInspector(FakeStore())

    payload = inspector.rows(limit=25, offset=0)

    assert payload["exists"] is False
    assert payload["count"] == 0
    assert payload["rows"] == []
    assert payload["facets"]["fields"] == []
