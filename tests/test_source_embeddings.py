# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import numpy as np

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
