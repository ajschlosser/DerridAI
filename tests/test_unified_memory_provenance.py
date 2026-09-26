"""Unified memory, schema identity, and claim provenance contracts."""

from __future__ import annotations

from pathlib import Path

from app.metadata_schema import MetadataSchema, SchemaField, SchemaGroup
from app.persistence import SQLiteSystemRepository
from app.provenance_memory import (
    MetadataMemoryBinding,
    SupportBinding,
    persist_metadata_decision,
    persist_record_decision,
    resolve_support_binding,
)
from app.system_store import SystemStore


def test_legacy_schema_fields_receive_stable_identities_and_renames_can_retain_them():
    schema = MetadataSchema(
        name="Notes",
        groups=[SchemaGroup(key="discourse", label="Discourse", intro="Read it.")],
        fields=[SchemaField(name="mood", label="Mood")],
    )
    field_id = schema.fields[0].field_id
    reloaded = MetadataSchema.model_validate(schema.model_dump(mode="json"))
    assert reloaded.fields[0].field_id == field_id

    renamed = MetadataSchema.model_validate({
        **schema.model_dump(mode="json"),
        "fields": [{**schema.fields[0].model_dump(mode="json"), "name": "tone", "field_id": field_id}],
    })
    assert renamed.field_id("tone") == field_id


def test_memory_binding_distinguishes_explicit_absence_from_empty_text():
    binding = MetadataMemoryBinding.absence(
        record_id="r1",
        field_id="field-mood",
        field_name="mood",
    )
    assert binding.decision_kind == "absence"
    assert binding.value is None


def test_memory_and_support_bindings_are_durable_and_stale_revision_is_visible(tmp_path: Path, monkeypatch):
    import app.provenance_memory as memory_module
    import app.system_store as store_module

    repository = SQLiteSystemRepository(tmp_path / "system.sqlite3")
    monkeypatch.setattr(store_module, "system_repository", repository)
    store = SystemStore()
    monkeypatch.setattr(memory_module, "system_store", store)

    binding = MetadataMemoryBinding(
        record_id="r1",
        record_revision=2,
        field_id="field-mood",
        field_name="mood",
        decision_kind="value",
        value="calm",
    )
    persist_metadata_decision(binding)
    assert store.list_memory_bindings(field_id="field-mood")[0]["value"] == "calm"
    assert store.list_semantic_memory_dirty("metadata_exemplars")

    support = SupportBinding(
        claim_id="claim-1",
        record_id="r1",
        record_revision=2,
        relation="supports",
    )
    stale = resolve_support_binding(support, lambda _record_id: {"record_id": "r1", "record_revision": 3})
    assert stale.validation_status == "stale"




def test_record_decision_preserves_evidence_span_provenance(tmp_path: Path, monkeypatch):
    import app.provenance_memory as memory_module
    import app.system_store as store_module

    repository = SQLiteSystemRepository(tmp_path / "system.sqlite3")
    monkeypatch.setattr(store_module, "system_repository", repository)
    store = SystemStore()
    monkeypatch.setattr(memory_module, "system_store", store)

    schema = MetadataSchema(
        id="schema-1",
        name="Notes",
        groups=[SchemaGroup(key="discourse", label="Discourse", intro="Read it.")],
        fields=[SchemaField(name="mood", label="Mood")],
    )
    record = {
        "record_id": "r1",
        "record_revision": 4,
        "source_asset_id": "asset-1",
        "source_block_ids": ["b1", "b2"],
        "source_spans": [
            {
                "source_document_id": "asset-1",
                "source_unit_id": "b2",
                "block_id": "b2",
                "page": 7,
                "printed_page_label": "23",
                "char_start": 40,
                "char_end": 88,
            }
        ],
        "metadata_evidence": {"mood": {"block_ids": ["b2"]}},
    }

    binding = persist_record_decision(
        record=record,
        schema=schema,
        field_name="mood",
        value="critical",
        scope_id="build-1",
    )

    assert binding.source_document_id == "asset-1"
    assert len(binding.evidence) == 1
    span = binding.evidence[0]
    assert span.source_unit_ids == ["b2"]
    assert span.physical_page_start == 7
    assert span.physical_page_end == 7
    assert span.printed_page_start == "23"
    assert span.printed_page_end == "23"
    assert span.character_start == 40
    assert span.character_end == 88
    assert store.list_semantic_memory_dirty("metadata_exemplars", scope_id="build-1")


def test_research_memory_reads_are_owner_scoped(tmp_path: Path):
    repository = SQLiteSystemRepository(tmp_path / "system.sqlite3")
    repository.put_response_memory({
        "response_id": "private-a",
        "owner": "alice",
        "question": "A",
        "answer": "Answer A",
    })
    repository.put_response_memory({
        "response_id": "private-b",
        "owner": "bob",
        "question": "B",
        "answer": "Answer B",
    })
    assert [row["response_id"] for row in repository.list_response_memory(owner="alice")] == ["private-a"]

def test_record_support_lookup_is_owner_scoped(tmp_path: Path):
    repository = SQLiteSystemRepository(tmp_path / "system.sqlite3")
    repository.put_generated_claim({
        "claim_id": "claim-a",
        "owner": "alice",
        "claim_text": "A claim",
    })
    repository.put_generated_claim({
        "claim_id": "claim-b",
        "owner": "bob",
        "claim_text": "B claim",
    })
    repository.put_claim_support_binding({
        "support_binding_id": "support-a",
        "claim_id": "claim-a",
        "owner": "alice",
        "record_id": "r1",
        "record_revision": 2,
        "relation": "supports",
    })
    repository.put_claim_support_binding({
        "support_binding_id": "support-b",
        "claim_id": "claim-b",
        "owner": "bob",
        "record_id": "r1",
        "record_revision": 2,
        "relation": "supports",
    })

    alice_bindings = repository.list_claim_support_bindings_for_record("r1", owner="alice")
    assert [item["support_binding_id"] for item in alice_bindings] == ["support-a"]
    assert repository.get_generated_claim("claim-a", owner="alice")["claim_text"] == "A claim"
    assert repository.get_generated_claim("claim-b", owner="alice") is None



def test_claim_support_persistence_uses_raw_markers_before_citation_rendering(
    tmp_path: Path,
    monkeypatch,
):
    import app.provenance_memory as memory_module
    import app.system_store as store_module
    from app.job_rag import RAGJobManager

    repository = SQLiteSystemRepository(tmp_path / "system.sqlite3")
    monkeypatch.setattr(store_module, "system_repository", repository)
    store = SystemStore()
    monkeypatch.setattr(memory_module, "system_store", store)

    result = {
        "answer": "The passage resists a simple hierarchy (Derrida 1967: 12).",
        "raw_answer": "The passage resists a simple hierarchy [[E0]].",
        "evidence": [
            {
                "evidence_id": "E0",
                "inline_citation": "Derrida 1967: 12",
                "full_citation": "Derrida, Jacques. Of Grammatology. 1967.",
                "record": {
                    "record_id": "r1",
                    "record_revision": 3,
                    "source_document_id": "doc-1",
                    "source_spans": [
                        {
                            "source_document_id": "doc-1",
                            "source_unit_id": "b1",
                            "page": 12,
                            "char_start": 0,
                            "char_end": 80,
                        }
                    ],
                },
            }
        ],
    }

    persisted = RAGJobManager._persist_response_provenance(
        result,
        run_id="run-1",
        response_record_id="response-1",
        owner="alice",
    )

    assert len(persisted["claims"]) == 1
    assert persisted["claims"][0]["claim_text"] == "The passage resists a simple hierarchy."
    assert len(persisted["support_bindings"]) == 1
    binding = persisted["support_bindings"][0]
    assert binding["citation"]["evidence_marker"] == "E0"
    assert binding["source_spans"][0]["source_unit_ids"] == ["b1"]
    assert binding["source_spans"][0]["character_start"] == 0
