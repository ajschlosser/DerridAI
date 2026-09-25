# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from app.system_chroma_console import (
    execute_system_chroma_command,
    list_system_chroma_collections,
    parse_system_chroma_command,
    validate_system_chroma_command,
)


class FakeCollection:
    def __init__(self, name="derridai_metadata_exemplars", *, provider="chroma", system=True):
        self.name = name
        self.metadata = {
            "derridai_hidden_system_collection": system,
            "__derridai_embedding_provider": provider,
            "__derridai_embedding_model": "model-1",
        }
        self.last_get = None
        self.last_query = None

    def count(self):
        return 2

    def get(self, **kwargs):
        self.last_get = kwargs
        return {"ids": ["a"], "documents": ["Evidence context"], "metadatas": [{"field_name": "speaker"}]}

    def query(self, **kwargs):
        self.last_query = kwargs
        return {"ids": [["a"]], "documents": [["Evidence context"]], "metadatas": [[{"field_name": "speaker"}]], "distances": [[0.1]]}


class FakeClient:
    def __init__(self, collections):
        self.collections = {item.name: item for item in collections}

    def list_collections(self):
        return list(self.collections.values())

    def get_collection(self, *, name):
        return self.collections[name]


class FakeEmbeddings:
    def embed_query(self, text, *, provider=None, model=None):
        assert text == "responsibility"
        return [0.1, 0.2]


class FakeStore:
    def __init__(self, collections):
        self.client = FakeClient(collections)
        self.embeddings = FakeEmbeddings()

    def _embedding_spec(self, collection):
        return (
            str(collection.metadata.get("__derridai_embedding_provider") or "chroma"),
            collection.metadata.get("__derridai_embedding_model"),
        )


def test_parser_accepts_cli_style_read_only_commands():
    parsed = parse_system_chroma_command(
        """get derridai_metadata_exemplars --where '{"field_name":"speaker"}' --limit 20"""
    )
    assert parsed.verb == "get"
    assert parsed.collection == "derridai_metadata_exemplars"
    assert parsed.options["where"] == {"field_name": "speaker"}
    assert parsed.options["limit"] == 20


def test_validation_rejects_mutation_and_non_system_collections():
    system = FakeCollection()
    ordinary = FakeCollection("corpus", system=False)
    store = FakeStore([system, ordinary])

    try:
        parse_system_chroma_command("delete derridai_metadata_exemplars")
        raise AssertionError("mutation command should fail")
    except ValueError as exc:
        assert "read-only" in str(exc)

    try:
        validate_system_chroma_command(store, "get corpus --limit 2")
        raise AssertionError("ordinary collection should fail")
    except ValueError as exc:
        assert "system collections" in str(exc)


def test_validation_explains_query_and_execution_uses_collection_embedding_contract():
    collection = FakeCollection()
    store = FakeStore([collection])
    command = (
        """query derridai_metadata_exemplars --text responsibility """
        """--where '{"field_name":"speaker"}' --n-results 2"""
    )
    validation = validate_system_chroma_command(store, command)
    assert validation["valid"] is True
    assert "read-only" in validation["explanation"].lower()
    assert "nearest" in validation["explanation"].lower()

    result = execute_system_chroma_command(store, command)
    assert result["result"]["ids"] == [["a"]]
    assert collection.last_query["query_embeddings"] == [[0.1, 0.2]]
    assert collection.last_query["where"] == {"field_name": "speaker"}


def test_precomputed_system_collection_rejects_text_similarity_query():
    store = FakeStore([FakeCollection(provider="precomputed")])
    try:
        validate_system_chroma_command(
            store,
            "query derridai_metadata_exemplars --text responsibility",
        )
        raise AssertionError("precomputed query should fail")
    except ValueError as exc:
        assert "precomputed vectors" in str(exc)


def test_system_collection_listing_excludes_ordinary_corpus_collections():
    rows = list_system_chroma_collections(
        FakeStore([FakeCollection(), FakeCollection("ordinary", system=False)])
    )
    assert [row["name"] for row in rows] == ["derridai_metadata_exemplars"]
