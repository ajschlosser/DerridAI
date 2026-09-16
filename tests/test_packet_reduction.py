from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

# chromadb is a runtime container dependency and is not installed in the
# lightweight source-validation environment used by this repository test.
# The packet helpers/upsert logic under test do not need a real client.
sys.modules.setdefault("chromadb", types.SimpleNamespace())

store_module = importlib.import_module("app.chroma_store")
ChromaStore = store_module.ChromaStore
_JSON_PREFIX = store_module._JSON_PREFIX
compact_record_payload = store_module.compact_record_payload
compact_nested_record_payloads = store_module.compact_nested_record_payloads


class FakeEmbeddings:
    def embed(self, docs, records, embedding_field, *, provider=None, model=None):
        return [[1.0, 0.0] for _ in docs]


class FakeCollection:
    def __init__(self, existing=None):
        self.existing = existing or {}
        self.last_upsert = None

    def count(self):
        return len(self.existing)

    def get(self, ids=None, include=None, **kwargs):
        ids = list(ids or [])
        found = [item for item in ids if item in self.existing]
        return {
            "ids": found,
            "metadatas": [self.existing[item] for item in found],
        }

    def upsert(self, *, ids, documents, metadatas, embeddings):
        self.last_upsert = {
            "ids": ids,
            "documents": documents,
            "metadatas": metadatas,
            "embeddings": embeddings,
        }
        for item_id, metadata in zip(ids, metadatas):
            self.existing[item_id] = metadata


class FakeStore(ChromaStore):
    def __init__(self, collection):
        self.collection = collection
        self.embeddings = FakeEmbeddings()

    def _collection(self, name):
        return self.collection

    def _embedding_spec(self, collection):
        return "precomputed", "test"


def encoded_updates(entries):
    return _JSON_PREFIX + json.dumps(entries, ensure_ascii=False, separators=(",", ":"))


def decoded_updates(metadata):
    raw = metadata.get("updates", "")
    assert raw.startswith(_JSON_PREFIX)
    return json.loads(raw[len(_JSON_PREFIX):])


def test_compact_record_omits_history_but_keeps_count():
    record = {"record_id": "r1", "text": "x", "updates": [{"field_name": "text"}] * 4}
    compact = compact_record_payload(record)
    assert "updates" not in compact
    assert compact["_updates_count"] == 4
    assert compact["text"] == "x"


def test_nested_rag_record_compaction_does_not_delete_unrelated_updates_key():
    payload = {
        "evidence": [{"record": {"record_id": "r1", "updates": [{"x": 1}]}}],
        "pipeline": {"updates": ["this is not record audit history"]},
    }
    compact = compact_nested_record_payloads(payload)
    assert "updates" not in compact["evidence"][0]["record"]
    assert compact["evidence"][0]["record"]["_updates_count"] == 1
    assert compact["pipeline"]["updates"] == ["this is not record audit history"]


def test_upsert_without_history_preserves_existing_history_server_side():
    old = [{"field_name": "speaker", "new_value": "Derrida"}]
    collection = FakeCollection({
        "r1": {
            "record_id": "r1",
            "updates": encoded_updates(old),
            "_updates_count": 1,
        }
    })
    store = FakeStore(collection)
    store.upsert_many("test", [{"record_id": "r1", "text": "new text", "speaker": "Derrida"}])
    metadata = collection.last_upsert["metadatas"][0]
    assert decoded_updates(metadata) == old
    assert metadata["_updates_count"] == 1


def test_upsert_appends_only_audit_delta_server_side():
    old = [{"field_name": "speaker", "new_value": "Derrida"}]
    delta = [{"field_name": "stance", "new_value": "questions"}]
    collection = FakeCollection({
        "r1": {
            "record_id": "r1",
            "updates": encoded_updates(old),
            "_updates_count": 1,
        }
    })
    store = FakeStore(collection)
    store.upsert_many(
        "test",
        [{"record_id": "r1", "text": "new text"}],
        audit_entries_by_id={"r1": delta},
    )
    metadata = collection.last_upsert["metadatas"][0]
    assert decoded_updates(metadata) == old + delta
    assert metadata["_updates_count"] == 2


def test_explicit_history_replacement_is_possible_without_record_round_trip():
    old = [{"field_name": "a"}, {"field_name": "b"}]
    collection = FakeCollection({
        "r1": {
            "record_id": "r1",
            "updates": encoded_updates(old),
            "_updates_count": 2,
        }
    })
    store = FakeStore(collection)
    store.upsert_many(
        "test",
        [{"record_id": "r1", "text": "new text"}],
        replace_updates_by_id={"r1": []},
    )
    metadata = collection.last_upsert["metadatas"][0]
    assert decoded_updates(metadata) == []
    assert metadata["_updates_count"] == 0
