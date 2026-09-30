# Copyright 2026 Aaron John Schlosser, PhD.
"""In-memory Chroma collection and ChromaStore wiring for store-search tests."""

from __future__ import annotations

import math
from types import SimpleNamespace

from app import chroma_store as cs

RECORDS = [
    ("r1", "Hospitality welcomes the stranger.", {"work": "Of Hospitality"}, [1.0, 0.0]),
    ("r2", "The gift and the stranger at the door.", {"work": "Given Time"}, [0.9, 0.1]),
    ("r3", "Writing precedes speech in the tradition.", {"work": "Of Grammatology"}, [0.0, 1.0]),
    ("r4", "Différance defers and differs.", {"work": "Margins"}, [0.2, 0.98]),
    ("r5", "Stranger hospitality: the stranger is received.", {"work": "Of Hospitality"}, [0.7, 0.7]),
]
QUERY_VECTORS = {"stranger": [1.0, 0.0], "writing": [0.0, 1.0]}


def _cosine_distance(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return 1.0 - dot / norm


def _matches(meta, where):
    for key, value in (where or {}).items():
        if isinstance(value, dict):
            continue
        if meta.get(key) != value:
            return False
    return True


class FakeCollection:
    def __init__(self, metric="cosine"):
        self.metadata = {cs.ChromaStore._DISTANCE_KEY: metric} if metric else {}

    def _rows(self, where=None):
        return [
            (rid, text, {"_record_id": rid, **meta}, vector)
            for rid, text, meta, vector in RECORDS
            if _matches(meta, where)
        ]

    def count(self):
        return len(RECORDS)

    def query(self, *, query_embeddings, n_results, where=None, include=()):
        rows = sorted(self._rows(where), key=lambda row: _cosine_distance(query_embeddings[0], row[3]))
        rows = rows[:n_results]
        payload = {
            "ids": [[row[0] for row in rows]],
            "documents": [[row[1] for row in rows]],
            "metadatas": [[row[2] for row in rows]],
            "distances": [[round(_cosine_distance(query_embeddings[0], row[3]), 6) for row in rows]],
        }
        if "embeddings" in include:
            payload["embeddings"] = [[row[3] for row in rows]]
        return payload

    def get(self, *, include=(), where=None, limit=None, where_document=None):
        rows = self._rows(where)
        if where_document and "$contains" in where_document:
            rows = [row for row in rows if where_document["$contains"] in row[1]]
        if limit is not None:
            rows = rows[:limit]
        return {"ids": [r[0] for r in rows], "documents": [r[1] for r in rows], "metadatas": [r[2] for r in rows]}


class FakeEmbeddings:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def embed_query(self, query, *, provider=None, model=None):
        self.calls.append(query)
        if self.error:
            raise self.error
        return QUERY_VECTORS.get(query.strip().casefold(), [0.5, 0.5])


def fake_store(collection=None, embeddings=None):
    store = object.__new__(cs.ChromaStore)
    col = collection or FakeCollection()
    store._collection = lambda _name: col
    store._embedding_spec = lambda _col: ("local", "fake-embedder")
    store.embeddings = embeddings or FakeEmbeddings()
    return store


ADMIN = SimpleNamespace(role="admin", username="admin")
