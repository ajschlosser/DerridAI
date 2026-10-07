# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import pytest
from app.chroma_store import encode_metadata
from app.research_filter_catalog import (
    indexed_filter_inventory,
    validate_catalog_filter,
)
from app.research_filter_model import validate_model_proposal


class MetadataCollection:
    def __init__(self, records):
        self.rows = [encode_metadata(record, document_field="text", embedding_field="embedding") for record in records]
        self.calls = []

    def get(self, **kwargs):
        self.calls.append(kwargs)
        return {"metadatas": self.rows[kwargs["offset"]:kwargs["offset"] + kwargs["limit"]]}


def test_catalog_unions_custom_fields_across_works_collections_and_encoded_values(monkeypatch):
    from app import research_filter_catalog as catalog
    monkeypatch.setattr(catalog, "PAGE_SIZE", 1)
    left = MetadataCollection([{"record_id": "1", "work": "A", "custom_role": "witness", "text": "SECRET"},
                               {"record_id": "2", "work": "A", "custom_role": "editor", "attested": False}])
    right = MetadataCollection([{"record_id": "3", "work": "B", "certainty": 0.7, "topics": ["negation"]}])
    result = indexed_filter_inventory([left, right])
    fields = {item["key"]: item for item in result["fields"]}
    assert fields["custom_role"]["values"] == ["witness", "editor"]
    assert fields["certainty"]["type"] == "number"
    assert fields["attested"]["type"] == "boolean"
    assert fields["topics"]["encoding"] == "json"
    assert fields["topics"]["values"] == ['__json__:["negation"]']
    assert "text" not in fields and "field_assertions" not in fields
    assert [row["work"] for row in result["works"]] == ["A", "B"]
    assert all(call["include"] == ["metadatas"] for call in left.calls + right.calls)
    assert left.rows[0].get("field_assertions") is None  # discovery never mutates indexed metadata


def test_value_limit_does_not_truncate_field_discovery(monkeypatch):
    from app import research_filter_catalog as catalog
    monkeypatch.setattr(catalog, "VALUE_LIMIT", 1)
    result = indexed_filter_inventory([MetadataCollection([{"custom": "A"}, {"custom": "B", "rare": True}])])
    fields = {item["key"]: item for item in result["fields"]}
    assert fields["custom"]["values_truncated"]
    assert "rare" in fields


def test_model_proposals_reject_unknown_fields_values_numbers_and_types():
    fields = [{"key": "role", "type": "string", "values": ["witness"]},
              {"key": "certainty", "type": "number", "values": [0.5]}]
    valid = validate_model_proposal({"predicates": [{"field": "role", "operator": "$eq", "value": "witness"}], "unresolved": ["early works"]}, fields, "role is witness")
    assert valid["expression"] == 'role = "witness"' and valid["source"] == "model_assisted"
    for field, value in [("unknown", "witness"), ("role", "inventor"), ("certainty", 0.8), ("certainty", "witness")]:
        with pytest.raises(ValueError):
            validate_model_proposal({"predicates": [{"field": field, "operator": "$eq", "value": value}]}, fields, "certainty > 0.5")
    with pytest.raises(ValueError):
        validate_model_proposal({"predicates": [], "extra": "untrusted"}, fields, "q")
    assert validate_catalog_filter({"certainty": "high"}, fields)


def test_schema_identities_survive_union_and_unknown_schema_fields_fail_preview(monkeypatch):
    from app.field_assertions import FieldAssertion, store_assertion
    from app.routers import research_filters as routes
    records = []
    for schema_id, work, value in [("schema-a", "A", "witness"), ("schema-b", "B", "editor")]:
        record = {"record_id": work, "work": work, "custom_role": value}
        store_assertion(record, FieldAssertion(record_id=work, field_id=f"{schema_id}.role", field_name="custom_role",
            schema_id=schema_id, value=value, derivation_method="deterministic", evaluation_status="value_supported"))
        records.append(record)
    inventory = indexed_filter_inventory([MetadataCollection(records)])
    field = next(item for item in inventory["fields"] if item["key"] == "custom_role")
    assert field["schema_ids"] == ["schema-a", "schema-b"]
    assert field["field_ids"] == ["schema-a.role", "schema-b.role"]
    class Store:
        def list_stores(self):
            return [{"name": "corpus", "filter_fields": ["work"]}]
        def research_filter_inventory(self, names):
            return inventory
    monkeypatch.setattr(routes, "store", Store())
    assert routes.preview_research_filter(routes.ResearchFilterPreviewRequest(collection="corpus", metadata_filter={"custom_role": "witness"}))["valid"]
    assert not routes.preview_research_filter(routes.ResearchFilterPreviewRequest(collection="corpus", metadata_filter={"invented": "witness"}))["valid"]


def test_model_numeric_proposals_are_grounded_in_instruction():
    result = validate_model_proposal({"predicates": [{"field": "certainty", "operator": "$gte", "value": 0.75}]},
        [{"key": "certainty", "type": "number"}], "certainty >= 0.75")
    assert result["expression"] == "certainty >= 0.75"


def test_research_scope_inventory_is_metadata_only_cached_and_invalidated(monkeypatch):
    from app.chroma_store import ChromaStore, _notes_collection_change

    collection = MetadataCollection([
        {
            "record_id": "1",
            "work": "Of Grammatology",
            "document_author": "Jacques Derrida",
            "text": "This document text must never be requested by scope inference.",
        },
        {
            "record_id": "2",
            "work": "Totality and Infinity",
            "document_author": "Emmanuel Levinas",
            "text": "Nor should this document text be materialized.",
        },
    ])
    collection.id = "scope-corpus"
    collection.count = lambda: len(collection.rows)
    collection_lookups = []
    store = object.__new__(ChromaStore)

    def get_collection(name):
        collection_lookups.append(name)
        return collection

    store._collection = get_collection

    from app import chroma_store as chroma_store_module

    original_decode_metadata = chroma_store_module.decode_metadata
    decoded_key_sets = []

    def selective_decode(raw):
        decoded_key_sets.append(set(raw))
        return original_decode_metadata(raw)

    monkeypatch.setattr(chroma_store_module, "decode_metadata", selective_decode)

    first = store.research_scope_inventory(["corpus", "corpus"])
    assert first == [
        {
            "scope_label": "Of Grammatology",
            "source_authors": ["Jacques Derrida"],
        },
        {
            "scope_label": "Totality and Infinity",
            "source_authors": ["Emmanuel Levinas"],
        },
    ]
    assert collection_lookups == ["corpus"]
    assert collection.calls
    assert all(call["include"] == ["metadatas"] for call in collection.calls)
    allowed_scope_keys = {
        "work",
        "document_author",
        "field_assertions",
        "current_field_assertions",
    }
    assert decoded_key_sets
    assert all(keys <= allowed_scope_keys for keys in decoded_key_sets)

    calls = len(collection.calls)
    assert store.research_scope_inventory(["corpus"]) == first
    assert len(collection.calls) == calls

    @_notes_collection_change()
    def mutate(self):
        collection.rows[0] = encode_metadata(
            {
                "record_id": "1",
                "work": "Of Grammatology",
                "document_author": "Updated Author",
            },
            document_field="text",
            embedding_field="embedding",
        )

    mutate(store)
    refreshed = store.research_scope_inventory(["corpus"])
    assert refreshed[0]["source_authors"] == ["Updated Author"]
    assert len(collection.calls) > calls


def test_response_cache_write_preserves_corpus_derived_caches() -> None:
    from app.chroma_store import ChromaStore, _notes_collection_change

    store = object.__new__(ChromaStore)
    store._research_filter_cache = {("filters",): (0.0, {"fields": []})}
    store._research_scope_cache = {("scope",): [{"scope_label": "A"}]}
    store._record_size_cache = {("corpus", 1, 1): {"median_record_chars": 100}}
    store._research_filter_epoch = 7

    @_notes_collection_change()
    def mutate(self, name):
        return name

    mutate(store, "_response_cache")

    assert store._research_filter_cache
    assert store._research_scope_cache
    assert store._record_size_cache
    assert store._research_filter_epoch == 7

    mutate(store, "corpus")

    assert store._research_filter_cache == {}
    assert store._research_scope_cache == {}
    assert store._record_size_cache == {}
    assert store._research_filter_epoch == 8


def test_inventory_cache_is_invalidated_after_success_and_partial_failure():
    from app.chroma_store import ChromaStore, _notes_collection_change
    collection = MetadataCollection([{"work": "A", "custom": "old"}])
    collection.count = lambda: len(collection.rows)
    store = object.__new__(ChromaStore)
    store._collection = lambda name: collection
    first = store.research_filter_inventory(["corpus"])
    calls = len(collection.calls)
    assert store.research_filter_inventory(["corpus"]) == first
    assert len(collection.calls) == calls
    @_notes_collection_change()
    def mutate(self, fail=False):
        collection.rows[0]["custom"] = "new"
        if fail:
            raise RuntimeError("partial write")
    with pytest.raises(RuntimeError):
        mutate(store, fail=True)
    refreshed = store.research_filter_inventory(["corpus"])
    assert next(field for field in refreshed["fields"] if field["key"] == "custom")["values"] == ["new"]
    assert len(collection.calls) > calls


def test_model_endpoint_enforces_approved_profile_and_surfaces_failures(monkeypatch):
    from types import SimpleNamespace

    from app import content_filter, http_auth, research_filter_model
    from app.routers import research_filters as routes
    from app.system_store import system_store
    from fastapi import HTTPException
    monkeypatch.setattr(http_auth, "request_user", lambda request: SimpleNamespace(role="researcher"))
    monkeypatch.setattr(content_filter, "enforce_researcher_text", lambda value: None)
    monkeypatch.setattr(system_store, "researcher_profile", lambda key: None)
    request = routes.ResearchFilterResolveRequest(collection="corpus", instructions="only witnesses")
    with pytest.raises(HTTPException) as denied:
        routes.resolve_research_filter(request, None)
    assert denied.value.status_code == 403
    monkeypatch.setattr(system_store, "researcher_profile", lambda key: {"type": "openai"})
    with pytest.raises(HTTPException) as incompatible:
        routes.resolve_research_filter(request.model_copy(update={"provider_profile_id": "approved"}), None)
    assert incompatible.value.status_code == 422
    monkeypatch.setattr(http_auth, "request_user", lambda request: SimpleNamespace(role="admin"))
    monkeypatch.setattr(routes, "research_filter_inventory", lambda body: {"fields": [{"key": "role", "type": "string", "values": ["witness"]}]})
    def invalid(*args, **kwargs):
        raise ValueError("Invalid output")
    monkeypatch.setattr(research_filter_model, "resolve_with_local_model", invalid)
    with pytest.raises(HTTPException) as malformed:
        routes.resolve_research_filter(request, None)
    assert malformed.value.status_code == 422
    # A previous failed inference released the concurrency slot.
    assert routes._model_slot.acquire(blocking=False)
    routes._model_slot.release()
