"""Unified memory, schema identity, and claim provenance contracts."""

from __future__ import annotations

from pathlib import Path

from app.metadata_schema import MetadataSchema, SchemaField, SchemaGroup
from app.persistence import SQLiteSystemRepository
from app.provenance_memory import (
    MetadataMemoryBinding,
    SupportBinding,
    persist_metadata_decision,
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
