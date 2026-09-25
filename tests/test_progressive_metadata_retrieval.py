"""Semantic retrieval of progressive metadata exemplars."""

from __future__ import annotations

import sys
import types
from pathlib import Path

if "chromadb" not in sys.modules:
    sys.modules["chromadb"] = types.SimpleNamespace()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.metadata_exemplar_retrieval import ChromaMetadataExemplarIndex


class FakeEmbeddings:
    def __init__(self):
        self.calls = 0

    def embed_query(self, query, *, provider=None, model=None):
        self.calls += 1
        assert query
        return [1.0, 0.0]


def _matches_where(row, where):
    if "$and" in where:
        return all(_matches_where(row, item) for item in where["$and"])
    return all(row.get(key) == value for key, value in where.items())


class FakeCollection:
    def __init__(self):
        self.metadata = {"derridai_exemplar_schema": 3}
        self.rows = {
            "stale": {
                "scope_id": "build-1",
                "record_id": "r-speaker",
                "field_name": "speaker",
                "schema_version": "v1",
                "context_text": "stale",
            },
            "other-scope": {
                "scope_id": "build-2",
                "field_name": "speaker",
                "schema_version": "v1",
                "context_text": "other",
            },
        }

    def count(self):
        return len(self.rows)

    def get(self, *, where=None, include=None):
        ids = [
            exemplar_id
            for exemplar_id, row in self.rows.items()
            if where is None or _matches_where(row, where)
        ]
        return {"ids": ids, "metadatas": [self.rows[item] for item in ids]}

    def delete(self, *, ids):
        for exemplar_id in ids:
            self.rows.pop(exemplar_id, None)

    def query(self, *, query_embeddings, n_results, where, include):
        assert query_embeddings == [[1.0, 0.0]]
        ids = [
            exemplar_id
            for exemplar_id, row in self.rows.items()
            if _matches_where(row, where)
        ][:n_results]
        # Give every candidate a deterministic but different vector so MMR runs.
        vectors = [[1.0, float(index)] for index, _ in enumerate(ids)]
        return {
            "ids": [ids],
            "metadatas": [[self.rows[item] for item in ids]],
            "distances": [[0.05 + (index * 0.05) for index, _ in enumerate(ids)]],
            "embeddings": [vectors],
        }


class FakeClient:
    def __init__(self, collection):
        self.collection = collection

    def get_collection(self, *, name):
        assert name == "test_metadata_exemplars"
        return self.collection


class FakeStore:
    def __init__(self):
        self.collection = FakeCollection()
        self.client = FakeClient(self.collection)
        self.embeddings = FakeEmbeddings()

    def _embedding_spec(self, collection):
        assert collection is self.collection
        return "fake", "fake-model"

    def upsert_many(self, store, records, *, document_field, id_field):
        assert store == "test_metadata_exemplars"
        for record in records:
            exemplar_id = str(record[id_field])
            self.collection.rows[exemplar_id] = dict(record)
        return {"upserted": len(records), "count": self.collection.count()}


def exemplar(exemplar_id, field, value, evidence):
    return {
        "metadata_exemplar_id": exemplar_id,
        "kind": "positive",
        "record_id": exemplar_id.replace("mex-", "r-"),
        "record_revision": 2,
        "source_document_id": "doc-1",
        "field_name": field,
        "field_value": value,
        "assertion_status": "human_confirmed",
        "assertion_method": "human_review_of_llm_proposal",
        "evidence_ref": {
            "block_ids": [f"block-{exemplar_id}"],
            "quote_hash": f"hash-{exemplar_id}",
        },
        "evidence_text": evidence,
        "context_text": f"Context before. {evidence} Context after.",
        "schema_id": "schema",
        "schema_version": "v1",
        "language": "en",
        "region_type": "main_text",
    }


def test_retrieval_embeds_query_once_across_multiple_fields_and_syncs_scope():
    store = FakeStore()
    index = ChromaMetadataExemplarIndex(store, collection_name="test_metadata_exemplars")
    canonical = [
        {
            **exemplar("mex-speaker", "speaker", "Derrida", "Derrida replies to the interviewer."),
            "record_id": "r-speaker",
        },
        exemplar(
            "mex-holder-1",
            "position_holder",
            "Levinas",
            "For Levinas, responsibility precedes freedom.",
        ),
        exemplar(
            "mex-holder-2",
            "position_holder",
            "Kant",
            "Kant makes autonomy central to practical reason.",
        ),
    ]

    result = index.retrieve(
        scope_id="build-1",
        query_text="Derrida discusses Levinas and responsibility.",
        exemplars=canonical,
        fields=["speaker", "position_holder"],
        schema_id="schema",
        schema_version="v1",
        field_limits={"speaker": 1, "position_holder": 2},
    )

    assert result["ok"] is True
    assert store.embeddings.calls == 1
    assert "stale" not in store.collection.rows
    assert "other-scope" in store.collection.rows
    assert set(result["examples"]) == {"speaker", "position_holder"}
    assert result["examples"]["speaker"][0]["value"] == "Derrida"
    assert {
        item["value"] for item in result["examples"]["position_holder"]
    } == {"Levinas", "Kant"}
    assert all(
        item["evidence_bound"]
        for items in result["examples"].values()
        for item in items
    )
    assert result["telemetry"]["examples_used"] == 3
    assert result["telemetry"]["sync"]["upserted"] == 3
    assert result["telemetry"]["sync"]["deleted"] == 1


def test_retrieval_packet_budget_is_global_not_per_field():
    store = FakeStore()
    index = ChromaMetadataExemplarIndex(store, collection_name="test_metadata_exemplars")
    canonical = [
        exemplar("mex-speaker", "speaker", "Derrida", "Derrida speaks."),
        exemplar("mex-holder", "position_holder", "Levinas", "Levinas is named."),
    ]

    result = index.retrieve(
        scope_id="build-1",
        query_text="Derrida and Levinas",
        exemplars=canonical,
        fields=["speaker", "position_holder"],
        schema_id="schema",
        schema_version="v1",
        packet_char_budget=350,
    )

    used = sum(len(items) for items in result["examples"].values())
    assert result["ok"] is True
    assert used <= 1
    assert result["telemetry"]["packet_chars"] <= 350


def test_backend_failure_disables_repeated_semantic_attempts_but_returns_fallback_reason():
    class BrokenClient:
        def get_collection(self, *, name):
            raise RuntimeError("vector backend unavailable")

    class BrokenStore:
        client = BrokenClient()

    index = ChromaMetadataExemplarIndex(
        BrokenStore(),
        collection_name="test_metadata_exemplars",
    )
    canonical = [exemplar("mex-one", "speaker", "Derrida", "Derrida speaks.")]

    first = index.retrieve(
        scope_id="build-1",
        query_text="Derrida",
        exemplars=canonical,
        fields=["speaker"],
        schema_id="schema",
        schema_version="v1",
    )
    second = index.retrieve(
        scope_id="build-1",
        query_text="Derrida",
        exemplars=canonical,
        fields=["speaker"],
        schema_id="schema",
        schema_version="v1",
    )

    assert first["ok"] is False
    assert second["ok"] is False
    assert "vector backend unavailable" in second["telemetry"]["fallback_reason"]



def test_selective_sync_does_not_delete_omitted_record_keys():
    store = FakeStore()
    store.collection.rows["kept-omitted"] = {
        "scope_id": "build-1",
        "record_id": "r-omitted",
        "field_name": "stance",
        "schema_version": "v1",
        "context_text": "older but still canonical outside this selective packet",
    }
    index = ChromaMetadataExemplarIndex(store, collection_name="test_metadata_exemplars")
    desired = [
        {
            **exemplar("mex-speaker", "speaker", "Derrida", "Derrida speaks."),
            "record_id": "r-speaker",
        }
    ]

    stats = index.sync("build-1", desired)

    assert "kept-omitted" in store.collection.rows
    assert stats["deleted"] == 1  # only the obsolete speaker exemplar is replaced
    assert "stale" not in store.collection.rows


def test_rebuild_scope_can_remove_all_stale_rows_deterministically():
    store = FakeStore()
    store.collection.rows["obsolete"] = {
        "scope_id": "build-1",
        "record_id": "r-old",
        "field_name": "stance",
        "schema_version": "v1",
        "context_text": "obsolete",
    }
    index = ChromaMetadataExemplarIndex(store, collection_name="test_metadata_exemplars")
    desired = [exemplar("mex-new", "stance", "critical", "Derrida criticizes the formulation.")]

    stats = index.rebuild_scope("build-1", desired)

    assert stats["deleted"] == 2
    assert stats["upserted"] == 1
    assert "obsolete" not in store.collection.rows
    assert "stale" not in store.collection.rows
    assert "other-scope" in store.collection.rows
    assert "mex-new" in store.collection.rows

def test_missing_metadata_exemplar_collection_is_created_on_first_use():
    class MissingCollectionError(RuntimeError):
        pass

    class Client:
        def __init__(self):
            self.collection = None

        def get_collection(self, *, name):
            assert name == "test_metadata_exemplars"
            if self.collection is None:
                raise MissingCollectionError("Collection [test_metadata_exemplars] does not exist")
            return self.collection

        def delete_collection(self, *, name):
            self.collection = None

    class Store:
        def __init__(self):
            self.client = Client()
            self.created = 0

        @staticmethod
        def _is_missing_collection_error(exc):
            return "does not exist" in str(exc).casefold()

        def create_store(self, name, **kwargs):
            assert name == "test_metadata_exemplars"
            self.created += 1
            self.client.collection = FakeCollection()
            return {"name": name}

    store = Store()
    index = ChromaMetadataExemplarIndex(store, collection_name="test_metadata_exemplars")

    collection = index._ensure()

    assert collection is store.client.collection
    assert store.created == 1


def test_exemplar_collection_creation_failure_is_not_rewritten_as_missing_collection():
    class Client:
        def get_collection(self, *, name):
            raise RuntimeError("Collection [test_metadata_exemplars] does not exist")

    class Store:
        client = Client()

        @staticmethod
        def _is_missing_collection_error(exc):
            return "does not exist" in str(exc).casefold()

        def create_store(self, name, **kwargs):
            raise RuntimeError("embedding provider unavailable")

    index = ChromaMetadataExemplarIndex(Store(), collection_name="test_metadata_exemplars")

    try:
        index._ensure()
        raise AssertionError("creation failure should propagate")
    except RuntimeError as exc:
        assert "embedding provider unavailable" in str(exc)

