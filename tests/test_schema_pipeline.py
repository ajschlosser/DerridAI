"""A build follows the schema it was started with: prompts, accepted fields, evidence, review and edits."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules["chromadb"] = types.SimpleNamespace()

from app import corpus_builder as cb
from app import metadata_schema as ms
from app.config import APP_VERSION


def notes_schema():
    return ms.MetadataSchema(
        name="Reading notes",
        groups=[ms.SchemaGroup(key="discourse", label="Notes", intro="Read the record and note its mood.", footer="Report {assessed_fields}.\n"),
                ms.SchemaGroup(key="ideas", label="Ideas", intro="List the ideas the record raises.")],
        fields=[
            ms.SchemaField(name="mood", label="Mood", type="choice", values=[ms.SchemaValue(value="calm"), ms.SchemaValue(value="angry")], strict=True,
                           instruction="is the register of the passage. One of: {values}", assess=True, evidence=True, review=True),
            ms.SchemaField(name="ideas", label="Ideas", type="list", group="ideas"),
            ms.SchemaField(name="year_mentioned", label="Year mentioned", type="number", group="ideas"),
        ],
    )


def manager(tmp_path: Path, schema: ms.MetadataSchema | None = None):
    m = cb.PdfCorpusBuildManager(cb.PdfCorpusRepository(tmp_path / "repo"))
    payload = {
        "asset_id": "a", "source_sha256": "x", "source_filename": "x.pdf", "source_page_count": 1, "source_block_count": 1,
        "schema_version": cb.SCHEMA_VERSION, "profile_id": cb.PROFILE_VERSION, "profile_version": 11, "app_version": APP_VERSION,
        "provider": "ollama", "model": "m", "request": {},
    }
    if schema is not None:
        payload["schema"] = schema.model_dump(mode="json")
    build = m.repo.create_build(payload)
    build.update(status="awaiting_review", stage="review")
    m.repo.save_build(build)
    m._rewrite_and_validate = lambda bid, records: (m.repo.save_records(bid, records), m.repo.get_build(bid))[1]
    m._assert_human_review_available = lambda *a, **k: None
    m._push_review_history = lambda *a, **k: None
    return m, build["build_id"]


def test_creating_a_build_copies_the_chosen_schema_onto_it(tmp_path, monkeypatch):
    m = cb.PdfCorpusBuildManager(cb.PdfCorpusRepository(tmp_path / "repo"))
    m.repo.get_asset = lambda asset_id: {"asset_id": asset_id, "sha256": "s", "filename": "f.pdf", "page_count": 1, "block_count": 1}  # type: ignore[method-assign]
    monkeypatch.setattr(m._executor, "submit", lambda *a, **k: None)
    saved = m._schemas.save(notes_schema())
    build = m.create({"asset_id": "a", "schema_id": saved.id, "model": "m"})
    assert build["schema_id"] == "reading-notes" and build["schema"]["name"] == "Reading notes" and build["schema_hash"] == notes_schema().content_hash()
    # Editing or deleting the saved schema afterwards does not touch the build.
    m._schemas.delete(saved.id)
    assert m._schema_for(build["build_id"]).name == "Reading notes"
    assert m.create({"asset_id": "a", "model": "m"})["schema_id"] == "default"
    with pytest.raises(ValueError, match="Unknown metadata schema"):
        m.create({"asset_id": "a", "schema_id": "nope", "model": "m"})


def test_tasks_follow_the_schemas_groups_prompts_and_shapes(tmp_path):
    m, bid = manager(tmp_path, notes_schema())
    schema = m._schema_for(bid)
    record = {"record_id": "r", "text": "A calm passage.", "source_block_ids": ["b1"], "metadata_field_status": {}}
    tasks, _, _ = m._prepare_metadata_tasks(record, {}, {"enrichment_mode": "deep"}, m._profile_for(bid), {}, {}, "", "", None, schema=schema)
    assert [t[0] for t in tasks] == ["discourse", "ideas"]
    discourse = next(t for t in tasks if t[0] == "discourse")
    assert "Read the record and note its mood." in discourse[1] and '- mood is the register of the passage. One of: ["calm", "angry"]' in discourse[1]
    assert "Report region_type, primary_text, discourse_role, and mood." in discourse[1]
    assert "mood" in discourse[2].model_json_schema()["$defs"]["DiscourseMetadata"]["properties"] and discourse[4] == "derridai_record_discourse"
    # The quotation and indexing groups of the default schema are not in this schema, so they never run.
    assert not any("quoted_" in t[1] for t in tasks)


def test_the_default_schema_still_runs_the_three_families(tmp_path):
    m, bid = manager(tmp_path)
    record = {"record_id": "r", "text": 'He said "no" and wrote about hospitality.', "source_block_ids": ["b1"], "metadata_field_status": {}}
    tasks, _, _ = m._prepare_metadata_tasks(record, {}, {"enrichment_mode": "deep", "semantic_indexing": True}, m._profile_for(bid), {}, {}, "", "", None, schema=m._schema_for(bid))
    assert [t[0] for t in tasks] == ["discourse", "quotation", "indexing"]


def answer(**metadata):
    return {"metadata": {"region_type": "main_text", "primary_text": True, "discourse_role": "assertion", **metadata},
            "field_evidence": {"mood": {"block_ids": ["b1"], "confidence": 0.95, "reason": "tone"}},
            "field_assessments": {"mood": {"confidence": 0.95, "needs_review": False, "reason": "clear"}}}


def test_a_custom_field_is_proposed_cited_and_reviewed_like_any_other(tmp_path):
    m, bid = manager(tmp_path, notes_schema())
    record = {"record_id": "r", "text": "t", "metadata_field_status": {}}
    out = m._reconcile_metadata_results(record, m._profile_for(bid), ["b1"], [("discourse", answer(mood="calm"), None)], False, request={"model": "q"}, build_id=bid, schema=m._schema_for(bid))
    assert out["mood"] == "calm" and out["metadata_field_status"]["mood"]["status"] == "llm_inferred"
    assert out["metadata_evidence"]["mood"]["block_ids"] == ["b1"]
    # Without a cited source block the value waits for a person, because the field asks for evidence.
    bare = {"record_id": "r2", "text": "t", "metadata_field_status": {}}
    result = answer(mood="calm"); result["field_evidence"] = {}
    out2 = m._reconcile_metadata_results(bare, m._profile_for(bid), ["b1"], [("discourse", result, None)], False, request={"model": "q"}, build_id=bid, schema=m._schema_for(bid))
    assert out2["metadata_field_status"]["mood"]["status"] == "unresolved"


def test_a_field_the_schema_leaves_out_cannot_be_set_by_the_model_or_a_person(tmp_path):
    m, bid = manager(tmp_path, notes_schema())
    record = {"record_id": "r", "text": "t", "metadata_field_status": {}}
    out = m._reconcile_metadata_results(record, m._profile_for(bid), ["b1"], [("discourse", answer(mood="calm", speaker="Derrida"), None)], False, request={"model": "q"}, build_id=bid, schema=m._schema_for(bid))
    assert "speaker" not in out
    m.repo.save_records(bid, [{"record_id": "r", "text": "t", "metadata_field_status": {}}])
    with pytest.raises(ValueError, match="speaker"):
        m.patch_metadata(bid, "r", {"speaker": "Derrida"})
    saved = m.patch_metadata(bid, "r", {"mood": "angry", "year_mentioned": 1795, "ideas": ["hospitality"]})
    assert (saved["mood"], saved["year_mentioned"], saved["ideas"]) == ("angry", 1795, ["hospitality"])
    with pytest.raises(ValueError, match="Invalid"):
        m.patch_metadata(bid, "r", {"mood": "furious"})  # strict values
    with pytest.raises(ValueError):
        m.patch_metadata(bid, "r", {"year_mentioned": "not a year"})
    # The locked core is always editable.
    assert m.patch_metadata(bid, "r", {"discourse_role": "critique"})["discourse_role"] == "critique"


def test_review_fields_come_from_the_schema(tmp_path):
    m, bid = manager(tmp_path, notes_schema())
    assert m._profile_for(bid)["review_metadata_fields"] == ["region_type", "primary_text", "discourse_role", "mood"]
    default, dbid = manager(tmp_path / "d")
    assert "stance" in default._profile_for(dbid)["review_metadata_fields"]


def test_a_reported_position_needs_a_position_holder_only_when_the_schema_has_one():
    profile_without = {"schema_field_names": ["region_type", "mood"]}
    profile_with = {"schema_field_names": ["region_type", "position_holder"]}
    records = [{"record_id": "r", "text": "t", "discourse_role": "reported_position", "source_block_ids": [], "page_start": 1, "page_end": 1}]
    for profile, expect in ((profile_without, 0), (profile_with, 1)):
        result = cb.PdfCorpusBuildManager.validate_records([], records, {**cb.CORPUS_PROFILES[cb.PROFILE_VERSION], **profile})
        errors = [e for e in result.get("relationship_errors", [])] if isinstance(result, dict) else []
        assert len(errors) == expect


def test_a_schema_group_can_be_previewed_without_a_build(tmp_path):
    m, _ = manager(tmp_path)
    shown = m.preview_schema_group(notes_schema(), "discourse", "It was a calm evening.", {}, run=False)
    assert shown["ran"] is False and "It was a calm evening." in shown["prompt"] and "note its mood" in shown["prompt"]
    assert "mood" in str(shown["answer_schema"])
    with pytest.raises(ValueError, match="no group"):
        m.preview_schema_group(notes_schema(), "nowhere", "x", {}, run=False)
    m._chat_json = lambda request, prompt, **kw: {"metadata": {"mood": "calm"}}  # type: ignore[method-assign]
    m._interactive_llm_request = lambda build_id, override=None: {}  # type: ignore[method-assign]
    ran = m.preview_schema_group(notes_schema(), "discourse", "It was a calm evening.", {"model": "q"}, run=True)
    assert ran["ran"] is True and ran["answer"]["metadata"]["mood"] == "calm"
