"""Run-scoped field guidance stays bounded, evidence-aware, and separate from schemas."""

from __future__ import annotations

import sys
import types

import pytest

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules["chromadb"] = types.SimpleNamespace()

from app import corpus_builder as cb
from app import metadata_schema as ms
from app.corpus_publication import serialize_public_record
from app.models import PdfCorpusBuildCreate
from app.run_guidance import find_guidance_matches, format_group_guidance


def test_guidance_matches_are_case_insensitive_whole_phrases_and_unicode_safe():
    guidance = {"persons": {"instructions": "", "look_for": ["Édouard Glissant", "Art"]}}

    matches = find_guidance_matches(
        "ÉDOUARD GLISSANT discusses Relation. The word artist is not itself a match.", guidance
    )

    assert matches == {"persons": [{"term": "Édouard Glissant", "occurrences": 1}]}


def test_group_prompt_receives_only_its_own_guidance_and_never_calls_matches_proof():
    guidance = {
        "mood": {"instructions": "Prefer a short phrase.", "look_for": ["anger"]},
        "ideas": {"instructions": "", "look_for": ["hospitality"]},
    }
    matches = {"mood": [{"term": "anger", "occurrences": 1}]}

    prompt = format_group_guidance(["region_type", "mood"], guidance, matches)

    assert "Field `mood`" in prompt
    assert "anger (1 occurrence(s))" in prompt
    assert "not proof" in prompt
    assert "Field `ideas`" not in prompt
    assert "hospitality" not in prompt


def test_required_guidance_has_a_reviewable_fallback_placeholder():
    prompt = format_group_guidance(
        ["mood"],
        {
            "mood": {
                "required": True,
                "default_placeholder": "[not established in source]",
            }
        },
        {},
    )

    assert "REQUIRED FOR THIS RUN" in prompt
    assert "[not established in source]" in prompt
    assert "mark the result unresolved" in prompt


def test_build_request_bounds_and_deduplicates_guidance_terms():
    request = PdfCorpusBuildCreate(
        asset_id="asset",
        run_guidance={"persons": {"instructions": "  Watch the argument. ", "look_for": ["Levinas", " levinas ", ""]}},
    )

    assert request.run_guidance["persons"].instructions == "Watch the argument."
    assert request.run_guidance["persons"].look_for == ["Levinas"]
    with pytest.raises(ValueError, match="160 characters"):
        PdfCorpusBuildCreate(asset_id="asset", run_guidance={"persons": {"look_for": ["x" * 161]}})


def test_build_snapshots_run_guidance_and_rejects_fields_outside_selected_schema(tmp_path, monkeypatch):
    manager = cb.PdfCorpusBuildManager(cb.PdfCorpusRepository(tmp_path / "repo"))
    manager.repo.get_asset = lambda asset_id: {"asset_id": asset_id, "sha256": "s", "filename": "f.pdf", "page_count": 1, "block_count": 1}  # type: ignore[method-assign]
    monkeypatch.setattr(manager._executor, "submit", lambda *args, **kwargs: None)
    schema = ms.MetadataSchema(
        name="Guided",
        groups=[ms.SchemaGroup(key="discourse", label="Discourse", intro="Read carefully."), ms.SchemaGroup(key="ideas", label="Ideas", intro="Find ideas.")],
        fields=[ms.SchemaField(name="ideas", label="Ideas", type="list", group="ideas")],
    )
    saved_schema = manager._schemas.save(schema)
    guidance = {"ideas": {"instructions": "Focus on concepts argued in the passage.", "look_for": ["hospitality"]}}

    build = manager.create({"asset_id": "a", "schema_id": saved_schema.id, "run_guidance": guidance})

    assert build["request"]["run_guidance"] == guidance
    with pytest.raises(ValueError, match="outside the selected schema"):
        manager.create({"asset_id": "a", "schema_id": saved_schema.id, "run_guidance": {"persons": {"look_for": ["Levinas"]}}})


def test_guidance_is_appended_only_to_its_schema_group_prompt(tmp_path):
    manager = cb.PdfCorpusBuildManager(cb.PdfCorpusRepository(tmp_path / "repo"))
    schema = ms.MetadataSchema(
        name="Guided",
        groups=[ms.SchemaGroup(key="discourse", label="Discourse", intro="Read carefully."), ms.SchemaGroup(key="ideas", label="Ideas", intro="Find ideas.")],
        fields=[ms.SchemaField(name="ideas", label="Ideas", type="list", group="ideas")],
    )
    record = {"record_id": "r", "text": "Hospitality is discussed.", "source_block_ids": ["b1"], "metadata_field_status": {}}
    guidance = {"ideas": {"instructions": "Track the argument.", "look_for": ["hospitality"]}}

    tasks, _, _ = manager._prepare_metadata_tasks(
        record,
        {},
        {"enrichment_mode": "deep", "run_guidance": guidance},
        cb.CORPUS_PROFILES[cb.PROFILE_VERSION],
        {},
        {},
        "",
        "",
        None,
        schema=schema,
    )

    discourse_prompt = next(task[1] for task in tasks if task[0] == "discourse")
    ideas_prompt = next(task[1] for task in tasks if task[0] == "ideas")
    assert "Track the argument" not in discourse_prompt
    assert "Track the argument" in ideas_prompt
    assert "Exact phrase matches in this record: hospitality (1 occurrence(s))" in ideas_prompt


def test_schema_nlp_hints_are_validated_and_included_in_group_prompt():
    schema = ms.MetadataSchema(
        name="NLP hints",
        groups=[ms.SchemaGroup(key="discourse", label="Discourse", intro="Read carefully.")],
        fields=[
            ms.SchemaField(
                name="region_author",
                label="Region author",
                pos_tags=["PROPN"],
                ner_tags=["PERSON"],
            )
        ],
    )

    prompt = ms.build_group_prompt(schema, "discourse", base_context="Text: Derrida cites Levinas.")

    assert "POS tags" in prompt
    assert "PERSON" in prompt


def test_required_run_guidance_field_enters_review_queue_when_model_returns_no_value(tmp_path):
    manager = cb.PdfCorpusBuildManager(tmp_path / "repo")
    schema = ms.MetadataSchema(
        name="Required guidance",
        groups=[ms.SchemaGroup(key="discourse", label="Discourse", intro="Read carefully.")],
        fields=[ms.SchemaField(name="region_author", label="Region author", group="discourse")],
    )
    record = {
        "record_id": "r1",
        "text": "No author is established here.",
        "metadata_field_status": {},
        "metadata_stage_status": {"discourse": "complete"},
    }
    profile = {**cb.CORPUS_PROFILES[cb.PROFILE_VERSION], "review_metadata_fields": schema.review_fields()}
    result = manager._reconcile_metadata_results(
        record,
        profile,
        [],
        [("discourse", {"metadata": {}, "field_assessments": {}}, None)],
        False,
        request={
            "run_guidance": {
                "region_author": {
                    "required": True,
                    "default_placeholder": "[not established in source]",
                }
            }
        },
        schema=schema,
    )

    assert result["region_author"] == "[not established in source]"
    assert "region_author" in result["metadata_incomplete_fields"]
    assert result["metadata_field_status"]["region_author"]["reason_code"] == "required_placeholder"


def test_run_guidance_match_diagnostics_do_not_leak_into_published_records():
    record = {
        "record_id": "r1",
        "text": "Hospitality is discussed.",
        "metadata_guidance_matches": {"concepts": [{"term": "hospitality", "occurrences": 1}]},
    }

    assert "metadata_guidance_matches" not in serialize_public_record(record)
