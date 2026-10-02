# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from types import SimpleNamespace

import app.source_embeddings as source_embeddings
import numpy as np
import pytest
from app.source_embeddings import (
    SourceEmbeddingProjection,
    embedding_identity,
    source_unit_identity,
)


class FakeEmbeddings:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed(self, texts, records, field, *, provider=None, model=None):
        self.calls.append(list(texts))
        return [[float(index + 1)] for index, _ in enumerate(texts)]


class FakeStore:
    def __init__(self) -> None:
        self.embeddings = FakeEmbeddings()


def block(block_id: str, text: str) -> dict[str, str]:
    return {"block_id": block_id, "text": text}


def test_source_unit_identity_is_stable_but_embedding_identity_tracks_content_and_contract():
    stable = source_unit_identity("doc-1", "block-1")
    assert stable == source_unit_identity("doc-1", "block-1")
    assert stable != source_unit_identity("doc-1", "block-2")

    original = embedding_identity("doc-1", "block-1", "Original text.", provider="ollama", model="m")
    changed_text = embedding_identity("doc-1", "block-1", "Changed text.", provider="ollama", model="m")
    changed_model = embedding_identity("doc-1", "block-1", "Original text.", provider="ollama", model="m2")
    assert original != changed_text
    assert original != changed_model


def test_projection_reuses_unchanged_vectors_and_invalidates_changed_content():
    store = FakeStore()
    projection = SourceEmbeddingProjection(store)
    source = [block("b1", "Repeated source text."), block("b2", "Repeated source text.")]

    first = projection.sync("doc-1", source, provider="ollama", model="m")
    second = projection.sync("doc-1", source, provider="ollama", model="m")

    assert first["embedded"] == 1
    assert second["embedded"] == 0
    assert second["reused"] == 2
    assert store.embeddings.calls == [["Repeated source text."]]

    changed = projection.sync(
        "doc-1",
        [block("b1", "A revised source text."), source[1]],
        provider="ollama",
        model="m",
    )
    assert changed["embedded"] == 1
    assert store.embeddings.calls == [["Repeated source text."], ["A revised source text."]]


def test_projection_embedding_contract_change_invalidates_cached_vectors():
    store = FakeStore()
    projection = SourceEmbeddingProjection(store)
    source = [block("b1", "Source text.")]

    projection.sync("doc-1", source, provider="ollama", model="m")
    result = projection.sync("doc-1", source, provider="ollama", model="new-model")

    assert result["embedded"] == 1
    assert len(store.embeddings.calls) == 2


def test_complete_snapshot_prunes_removed_source_units():
    store = FakeStore()
    projection = SourceEmbeddingProjection(store)
    projection.sync(
        "doc-1",
        [block("b1", "Keep this."), block("b2", "Remove this.")],
        provider="ollama",
        model="m",
    )

    result = projection.sync(
        "doc-1",
        [block("b1", "Keep this.")],
        provider="ollama",
        model="m",
    )

    assert result["deleted"] == 1
    assert set(projection.embeddings_for("doc-1", ["b1", "b2"], provider="ollama", model="m")) == {"b1"}


class FakeChromaCollection:
    """Mimics real chromadb: `.get(include=["embeddings"])` returns a numpy array,
    whose truth value is ambiguous under `or []` for more than one row."""

    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def get(self, *, where, include):
        return {
            "ids": [row["id"] for row in self._rows],
            "metadatas": [row["metadata"] for row in self._rows],
            "embeddings": np.array([row["embedding"] for row in self._rows]),
        }


def test_embeddings_for_handles_numpy_embeddings_array_from_real_chroma():
    store = FakeStore()
    projection = SourceEmbeddingProjection(store)
    projection._collection = lambda provider, model: FakeChromaCollection([
        {"id": "e1", "metadata": {"source_unit_id": "b1"}, "embedding": [1.0, 2.0]},
        {"id": "e2", "metadata": {"source_unit_id": "b2"}, "embedding": [3.0, 4.0]},
    ])

    vectors = projection.embeddings_for("doc-1", ["b1", "b2"], provider="ollama", model="m")

    assert vectors == {"b1": [1.0, 2.0], "b2": [3.0, 4.0]}


class BatchLimitedClient:
    def __init__(self, max_batch_size: int) -> None:
        self._max_batch_size = max_batch_size

    def get_max_batch_size(self) -> int:
        return self._max_batch_size


class BatchLimitedCollection:
    def __init__(self, max_batch_size: int) -> None:
        self.max_batch_size = max_batch_size
        self.rows: dict[str, dict[str, object]] = {}
        self.upsert_batch_sizes: list[int] = []
        self.delete_batch_sizes: list[int] = []
        self.fail_upserts = False

    def get(self, *, where, include):
        document_id = str(where.get("source_document_id") or "")
        matching = [
            (storage_id, row)
            for storage_id, row in self.rows.items()
            if str((row.get("metadata") or {}).get("source_document_id") or "") == document_id
        ]
        return {
            "ids": [storage_id for storage_id, _ in matching],
            "metadatas": [row["metadata"] for _, row in matching],
            "embeddings": [row["embedding"] for _, row in matching],
        }

    def upsert(self, *, ids, documents, metadatas, embeddings):
        if len(ids) > self.max_batch_size:
            raise ValueError(
                f"Batch size of {len(ids)} is greater than max batch size of {self.max_batch_size}"
            )
        if self.fail_upserts:
            raise RuntimeError("simulated upsert failure")
        self.upsert_batch_sizes.append(len(ids))
        for storage_id, document, metadata, embedding in zip(
            ids, documents, metadatas, embeddings
        ):
            self.rows[str(storage_id)] = {
                "document": document,
                "metadata": dict(metadata),
                "embedding": list(embedding),
            }

    def delete(self, *, ids):
        if len(ids) > self.max_batch_size:
            raise ValueError(
                f"Batch size of {len(ids)} is greater than max batch size of {self.max_batch_size}"
            )
        self.delete_batch_sizes.append(len(ids))
        for storage_id in ids:
            self.rows.pop(str(storage_id), None)


class BatchLimitedStore(FakeStore):
    def __init__(self, max_batch_size: int) -> None:
        super().__init__()
        self.collection = BatchLimitedCollection(max_batch_size)
        self.client = BatchLimitedClient(max_batch_size)


def batch_limited_projection(store: BatchLimitedStore) -> SourceEmbeddingProjection:
    projection = SourceEmbeddingProjection(store)
    projection._collection = lambda provider, model: store.collection
    return projection


def test_projection_batches_embeddings_upserts_and_deletes_to_backend_limit(monkeypatch):
    monkeypatch.setattr(
        source_embeddings,
        "settings",
        SimpleNamespace(api_batch_size=10),
    )
    store = BatchLimitedStore(max_batch_size=3)
    projection = batch_limited_projection(store)
    source = [block(f"b{index}", f"Source text {index}.") for index in range(7)]

    first = projection.sync("doc-1", source, provider="ollama", model="m")

    assert [len(call) for call in store.embeddings.calls] == [3, 3, 1]
    assert store.collection.upsert_batch_sizes == [3, 3, 1]
    assert first["batch_size"] == 3
    assert first["embedding_batches"] == 3
    assert first["upsert_batches"] == 3
    assert first["delete_batches"] == 0
    assert first["batches"] == 6
    assert len(store.collection.rows) == 7

    second = projection.sync(
        "doc-1",
        source[:1],
        provider="ollama",
        model="m",
    )

    assert second["embedded"] == 0
    assert second["upserted"] == 0
    assert second["deleted"] == 6
    assert second["delete_batches"] == 2
    assert store.collection.delete_batch_sizes == [3, 3]
    assert len(store.collection.rows) == 1


def test_projection_does_not_prune_previous_rows_before_replacement_upserts_succeed(monkeypatch):
    monkeypatch.setattr(
        source_embeddings,
        "settings",
        SimpleNamespace(api_batch_size=10),
    )
    store = BatchLimitedStore(max_batch_size=2)
    projection = batch_limited_projection(store)
    projection.sync(
        "doc-1",
        [block("old", "Previous source text.")],
        provider="ollama",
        model="m",
    )
    old_storage_id = source_unit_identity("doc-1", "old")
    store.collection.delete_batch_sizes.clear()
    store.collection.fail_upserts = True

    with pytest.raises(RuntimeError, match="simulated upsert failure"):
        projection.sync(
            "doc-1",
            [block("new", "Replacement source text.")],
            provider="ollama",
            model="m",
        )

    assert old_storage_id in store.collection.rows
    assert store.collection.delete_batch_sizes == []
