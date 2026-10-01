"""A build follows the schema it was started with: prompts, accepted fields, evidence, review and edits."""

from __future__ import annotations

import hashlib
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
from app.field_assertions import create_memory_assertion, current_assertion_by_name, project_record_assertions


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
    m._rewrite_targeted_record = lambda bid, record, previous: (m.repo.update_record(bid, record), m.repo.get_build(bid))[1]
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


def test_deep_mode_skips_quotation_without_a_quotation_signal(tmp_path):
    m, bid = manager(tmp_path)
    record = {
        "record_id": "r",
        "text": "Hospitality and sovereignty remain in tension.",
        "source_block_ids": ["b1"],
        "metadata_field_status": {},
    }
    tasks, _, _ = m._prepare_metadata_tasks(
        record,
        {},
        {"enrichment_mode": "deep", "semantic_indexing": True},
        m._profile_for(bid),
        {},
        {},
        "",
        "",
        None,
        schema=m._schema_for(bid),
    )
    assert [t[0] for t in tasks] == ["discourse", "indexing"]


def test_deep_mode_uses_current_document_intelligence_as_a_quotation_signal(tmp_path):
    m, bid = manager(tmp_path)
    text = "Hospitality and sovereignty remain in tension."
    record = {
        "record_id": "r",
        "text": text,
        "source_block_ids": ["b1"],
        "metadata_field_status": {},
        "document_intelligence": {
            "status": "ok",
            "record_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "quotations": [{"text": "Hospitality and sovereignty", "speaker": ""}],
        },
    }
    tasks, _, _ = m._prepare_metadata_tasks(
        record,
        {},
        {"enrichment_mode": "deep", "semantic_indexing": True},
        m._profile_for(bid),
        {},
        {},
        "",
        "",
        None,
        schema=m._schema_for(bid),
    )
    assert [t[0] for t in tasks] == ["discourse", "quotation", "indexing"]


def test_strong_memory_prefills_skip_the_automatic_indexing_model_call(tmp_path):
    m, bid = manager(tmp_path)
    schema = m._schema_for(bid)
    record = {
        "record_id": "r",
        "record_revision": 1,
        "text": "Hospitality, sovereignty, Derrida, and Glas.",
        "source_block_ids": ["b1"],
        "metadata_field_status": {},
    }
    values = {
        "topics": ["hospitality"],
        "concepts": ["sovereignty"],
        "persons": ["Derrida"],
        "works_referenced": ["Glas"],
    }
    for field, value in values.items():
        create_memory_assertion(
            record,
            field,
            value,
            schema=schema,
            confidence=0.9,
            reason="Two reviewed precedents agree.",
            evidence=[{"block_ids": ["b1"], "confidence": 0.9, "reason": "memory match"}],
        )
        record[field] = value
    project_record_assertions(record)

    tasks, _, _ = m._prepare_metadata_tasks(
        record,
        {},
        {"enrichment_mode": "deep", "semantic_indexing": True},
        m._profile_for(bid),
        {},
        {},
        "",
        "",
        None,
        schema=schema,
    )
    assert [t[0] for t in tasks] == ["discourse"]
    assert record["metadata_stage_status"]["indexing"] == "skipped"
    assert record["metadata_execution_ledger"]["indexing"]["reason_code"] == "automatic_routing_skip"
    assert "reviewed-memory prefills" in record["metadata_execution_ledger"]["indexing"]["error"]

    rerun, _, _ = m._prepare_metadata_tasks(
        record,
        {},
        {"enrichment_mode": "deep", "semantic_indexing": True, "families": ["indexing"]},
        m._profile_for(bid),
        {},
        {},
        "",
        "",
        None,
        schema=schema,
    )
    assert [t[0] for t in rerun] == ["indexing"]

def answer(**metadata):
    return {"metadata": {"region_type": "main_text", "primary_text": True, "discourse_role": "assertion", **metadata},
            "field_evidence": {"mood": {"block_ids": ["b1"], "confidence": 0.95, "reason": "tone"}},
            "field_assessments": {"mood": {"confidence": 0.95, "needs_review": False, "reason": "clear"}}}


def test_field_assertion_canary_flows_from_schema_through_enrichment_and_review(tmp_path):
    schema = ms.MetadataSchema(
        name="Conceptual analysis",
        groups=[
            ms.SchemaGroup(
                key="discourse",
                label="Conceptual analysis",
                intro="Identify the central conceptual tension.",
                footer="Report {assessed_fields}.\n",
            )
        ],
        fields=[
            ms.SchemaField(
                field_id="field-conceptual-tension",
                name="conceptual_tension",
                label="Conceptual tension",
                type="text",
                instruction="names the central conceptual opposition in the passage.",
                assess=True,
                evidence=True,
                review=True,
            )
        ],
    )
    m, bid = manager(tmp_path, schema)
    record = {"record_id": "canary", "record_revision": 1, "text": "Hospitality strains against sovereignty.", "metadata_field_status": {}}
    result = {
        "metadata": {
            "region_type": "main_text",
            "primary_text": True,
            "discourse_role": "analysis",
            "conceptual_tension": "hospitality / sovereignty",
        },
        "field_evidence": {
            "conceptual_tension": {
                "block_ids": ["b1"],
                "confidence": 0.91,
                "reason": "Both concepts are explicitly opposed in the passage.",
            }
        },
        "field_assessments": {
            "conceptual_tension": {
                "confidence": 0.91,
                "needs_review": False,
                "reason": "The opposition is explicit.",
                "outcome": "supported_value",
            }
        },
    }
    out = m._reconcile_metadata_results(
        record,
        m._profile_for(bid),
        ["b1"],
        [("discourse", result, None)],
        False,
        request={"model": "q"},
        build_id=bid,
        schema=m._schema_for(bid),
    )
    assertion = current_assertion_by_name(out, "conceptual_tension")
    assert assertion is not None
    assert assertion.field_id == "field-conceptual-tension"
    assert assertion.derivation_method == "model"
    assert out["conceptual_tension"] == "hospitality / sovereignty"

    m.repo.save_records(bid, [out])
    saved = m.patch_metadata(
        bid,
        "canary",
        {"conceptual_tension": "conditional hospitality / sovereignty"},
        expected_revision=int(out.get("record_revision") or 1),
    )
    reviewed = current_assertion_by_name(saved, "conceptual_tension")
    assert reviewed is not None
    assert reviewed.field_id == "field-conceptual-tension"
    assert reviewed.authority_status in {"human_confirmed", "human_override"}
    assert saved["conceptual_tension"] == "conditional hospitality / sovereignty"


def test_a_custom_field_is_proposed_cited_and_reviewed_like_any_other(tmp_path):
    m, bid = manager(tmp_path, notes_schema())
    record = {"record_id": "r", "text": "t", "metadata_field_status": {}}
    out = m._reconcile_metadata_results(record, m._profile_for(bid), ["b1"], [("discourse", answer(mood="calm"), None)], False, request={"model": "q"}, build_id=bid, schema=m._schema_for(bid))
    assert out["mood"] == "calm" and out["metadata_field_status"]["mood"]["status"] == "model_inferred"
    assert out["metadata_evidence"]["mood"]["block_ids"] == ["b1"]
    # Without a cited source block the value waits for a person, because the field asks for evidence.
    bare = {"record_id": "r2", "text": "t", "metadata_field_status": {}}
    result = answer(mood="calm"); result["field_evidence"] = {}
    out2 = m._reconcile_metadata_results(bare, m._profile_for(bid), ["b1"], [("discourse", result, None)], False, request={"model": "q"}, build_id=bid, schema=m._schema_for(bid))
    assert out2["metadata_field_status"]["mood"]["status"] == "unresolved"
    # No real source blocks exist in this fixture, so the evidence cascade legitimately finds nothing.
    assert "mood" not in out2["metadata_evidence"]


def _no_evidence_answer(**metadata):
    result = answer(**metadata)
    result["field_evidence"] = {}
    return result


def test_evidence_uses_current_source_units_after_topology_changes(tmp_path):
    m, bid = manager(tmp_path, notes_schema())
    m._blocks_for = lambda _build_id: {
        "unit-new": {
            "block_id": "unit-new",
            "source_unit_id": "unit-new",
            "text": "The mood of the passage is calm and unhurried.",
        }
    }
    record = {
        "record_id": "r-unit",
        "text": "The mood of the passage is calm and unhurried.",
        "source_block_ids": ["retired-block"],
        "source_unit_ids": ["unit-new"],
        "metadata_field_status": {},
    }

    labelled = m._labelled_source_blocks(bid, record, {"evidence_mode": "with_value"})
    assert "[unit-new]" in labelled
    assert "retired-block" not in labelled

    tasks, source_ids, _ = m._prepare_metadata_tasks(
        record,
        {},
        {"enrichment_mode": "deep"},
        m._profile_for(bid),
        {},
        {},
        "",
        "",
        None,
        schema=m._schema_for(bid),
        labelled_blocks=labelled,
    )
    assert source_ids == ["unit-new"]
    assert any("[unit-new]" in task[1] for task in tasks)

    out = m._reconcile_metadata_results(
        record,
        m._profile_for(bid),
        source_ids,
        [("discourse", _no_evidence_answer(mood="calm"), None)],
        False,
        request={"model": "q"},
        build_id=bid,
        schema=m._schema_for(bid),
    )
    evidence = out["metadata_evidence"]["mood"]
    assert evidence["block_ids"] == ["unit-new"]
    assert evidence["backfilled"] is True


def test_backfill_mode_attaches_untrusted_evidence_the_model_did_not_cite(tmp_path):
    m, bid = manager(tmp_path, notes_schema())
    m._evidence_source_blocks = lambda *a, **k: [
        {"block_id": "b1", "text": "The mood of the passage is calm and unhurried."},
        {"block_id": "b2", "text": "Unrelated footnote."},
    ]
    record = {"record_id": "r", "text": "t", "metadata_field_status": {}}
    out = m._reconcile_metadata_results(
        record, m._profile_for(bid), ["b1", "b2"], [("discourse", _no_evidence_answer(mood="calm"), None)], False,
        request={"model": "q", "evidence_mode": "backfill"}, build_id=bid, schema=m._schema_for(bid),
    )
    evidence = out["metadata_evidence"]["mood"]
    assert evidence["block_ids"] == ["b1"] and evidence["backfilled"] is True and evidence["confidence"] is None
    # Populated for the reviewer, but never trusted: pending review, not autofilled.
    assert out["metadata_field_status"]["mood"]["status"] != "autofilled"
    assert not out["metadata_field_status"]["mood"].get("autofilled")


def test_the_evidence_cascade_runs_regardless_of_evidence_mode(tmp_path):
    """The cascade is a universal safety net now: the same result no longer depends on ``evidence_mode``."""
    m, bid = manager(tmp_path, notes_schema())
    m._evidence_source_blocks = lambda *a, **k: [
        {"block_id": "b1", "text": "The mood of the passage is calm and unhurried."},
        {"block_id": "b2", "text": "Unrelated footnote."},
    ]
    record = {"record_id": "r", "text": "t", "metadata_field_status": {}}
    out = m._reconcile_metadata_results(
        record, m._profile_for(bid), ["b1", "b2"], [("discourse", _no_evidence_answer(mood="calm"), None)], False,
        request={"model": "q"}, build_id=bid, schema=m._schema_for(bid),  # default "with_value" mode, unset
    )
    evidence = out["metadata_evidence"]["mood"]
    assert evidence["block_ids"] == ["b1"] and evidence["backfilled"] is True and evidence["confidence"] is None
    assert out["metadata_field_status"]["mood"]["status"] != "autofilled"


def test_with_value_mode_still_runs_the_evidence_cascade_when_the_model_cites_nothing(tmp_path):
    m, bid = manager(tmp_path, notes_schema())
    m._evidence_source_blocks = lambda *a, **k: [{"block_id": "b1", "text": "calm calm calm"}]
    record = {"record_id": "r", "text": "t", "metadata_field_status": {}}
    out = m._reconcile_metadata_results(
        record, m._profile_for(bid), ["b1"], [("discourse", _no_evidence_answer(mood="calm"), None)], False,
        request={"model": "q"}, build_id=bid, schema=m._schema_for(bid),
    )
    evidence = out["metadata_evidence"]["mood"]
    # Bound by the cascade's deterministic stage (verbatim match), but still untrusted and unconfirmed.
    assert evidence["block_ids"] == ["b1"] and evidence["backfilled"] is True and evidence["confidence"] is None
    assert out["metadata_field_status"]["mood"]["status"] == "unresolved"
    assert not out["metadata_field_status"]["mood"].get("autofilled")


def test_evidence_cascade_llm_stage_only_runs_when_enabled(tmp_path):
    """The cascade's LLM stage is wired end-to-end, but stays off unless explicitly enabled.

    ``discourse_role="assertion"`` has no lexical or local-semantic match in these fake blocks
    (chromadb is stubbed in this test environment, so the semantic stages fail open), so it is
    exactly the case that would reach the cascade's LLM stage. ``_chat_json`` is stubbed so this
    never touches a real provider.
    """
    m, bid = manager(tmp_path, notes_schema())
    m._evidence_source_blocks = lambda *a, **k: [{"block_id": "b1", "text": "Unrelated text."}]
    calls: list[str] = []

    def fake_chat_json(request, prompt, **kwargs):
        calls.append(prompt)
        return {"block_ids": ["b1"], "reason": "The model's own last-resort choice."}

    m._chat_json = fake_chat_json
    record = {"record_id": "r", "text": "t", "metadata_field_status": {}}

    out_disabled = m._reconcile_metadata_results(
        record, m._profile_for(bid), ["b1"], [("discourse", _no_evidence_answer(mood="calm"), None)], False,
        request={"model": "q"}, build_id=bid, schema=m._schema_for(bid),
    )
    assert not calls
    assert out_disabled["metadata_evidence"].get("discourse_role") is None

    record2 = {"record_id": "r2", "text": "t", "metadata_field_status": {}}
    out_enabled = m._reconcile_metadata_results(
        record2, m._profile_for(bid), ["b1"], [("discourse", _no_evidence_answer(mood="calm"), None)], False,
        request={"model": "q", "evidence_cascade_llm_enabled": True}, build_id=bid, schema=m._schema_for(bid),
    )
    assert calls
    evidence = out_enabled["metadata_evidence"]["discourse_role"]
    assert evidence["block_ids"] == ["b1"] and evidence["backfilled"] is True and evidence["confidence"] is None
    assert evidence["method"] == "llm-evidence-choice-v1"


def test_enrichment_evidence_is_bound_to_the_recovery_pipeline_identity(tmp_path):
    m, bid = manager(tmp_path, notes_schema())
    m._evidence_source_blocks = lambda *a, **k: [{"block_id": "b1", "text": "calm calm calm"}]
    record = {"record_id": "r", "text": "t", "metadata_field_status": {}}
    out = m._reconcile_metadata_results(
        record, m._profile_for(bid), ["b1"], [("discourse", _no_evidence_answer(mood="calm"), None)], False,
        request={"model": "q"}, build_id=bid, schema=m._schema_for(bid),
    )
    pipeline = out["metadata_evidence"]["mood"]["pipeline"]
    assert pipeline["feature"] == "evidence_recovery"
    assert pipeline["pipeline_id"] == "evidence.recovery.celf"
    assert pipeline["pipeline_hash"] and pipeline["trace_id"]


def test_failed_evidence_recovery_pipeline_stays_visible_and_pending_review(tmp_path, monkeypatch, caplog):
    from app import corpus_metadata_enrichment_execution as enrichment

    def unavailable(**_kwargs):
        raise KeyError("evidence_recovery")

    monkeypatch.setattr(enrichment, "execute_evidence_recovery", unavailable)
    m, bid = manager(tmp_path, notes_schema())
    m._evidence_source_blocks = lambda *a, **k: [{"block_id": "b1", "text": "calm calm calm"}]
    record = {"record_id": "r", "text": "t", "metadata_field_status": {}}
    out = m._reconcile_metadata_results(
        record, m._profile_for(bid), ["b1"], [("discourse", _no_evidence_answer(mood="calm"), None)], False,
        request={"model": "q"}, build_id=bid, schema=m._schema_for(bid),
    )
    assert out["metadata_evidence"].get("mood") is None
    status = out["metadata_field_status"]["mood"]
    assert status["reason_code"] == "evidence_failed"
    assert status["verification_status"] == "pending_review" and not status["autofilled"]
    assert any("Evidence recovery pipeline did not run for mood" in message for message in caplog.messages)


def test_missing_source_document_identity_is_logged_and_left_pending_review(tmp_path, monkeypatch, caplog):
    m, bid = manager(tmp_path, notes_schema())
    real_get_build = m.repo.get_build
    monkeypatch.setattr(m.repo, "get_build", lambda build_id: {**real_get_build(build_id), "asset_id": ""})
    m._evidence_source_blocks = lambda *a, **k: [{"block_id": "b1", "text": "calm calm calm"}]
    record = {"record_id": "r", "text": "t", "metadata_field_status": {}}
    out = m._reconcile_metadata_results(
        record, m._profile_for(bid), ["b1"], [("discourse", _no_evidence_answer(mood="calm"), None)], False,
        request={"model": "q"}, build_id=bid, schema=m._schema_for(bid),
    )
    assert out["metadata_evidence"].get("mood") is None
    assert out["metadata_field_status"]["mood"]["reason_code"] == "evidence_failed"
    assert any("no source document identity" in message for message in caplog.messages)


def test_evidence_mode_defaults_to_with_value_and_rejects_unknown_values(monkeypatch):
    import dataclasses

    from app import config
    from app import evidence_suggestions as es

    def configured(value):
        monkeypatch.setattr(config, "settings", dataclasses.replace(config.settings, metadata_evidence_mode=value))

    configured("with_value")
    assert es.evidence_mode({}) == "with_value"
    assert es.evidence_mode({"evidence_mode": "backfill"}) == "backfill"
    assert es.evidence_mode({"evidence_mode": "nonsense"}) == "with_value"
    configured("backfill")
    assert es.evidence_mode(None) == "backfill"
    configured("garbage")
    assert es.evidence_mode(None) == "with_value"


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
