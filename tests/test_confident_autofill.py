# Copyright 2026 Aaron John Schlosser, PhD.
"""LLM metadata values must arrive and auto-fill above the confidence threshold.

Why: the response schema used to make `metadata` optional, so small models replied with
confidence assessments only and no values (nothing was auto-filled, and deterministic fields
were never corroborated). These tests pin the fix and the >65% rule.
How: schema tests validate Pydantic models directly; behavior tests fake the LLM call and run the
real enrichment path (`_enrich_record`).
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.modules.setdefault("chromadb", types.SimpleNamespace())
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app import corpus_builder as cb
from test_metadata_stage_checkpoints import _install_minimal_build

NULL_DISCOURSE = {name: None for name in cb.DiscourseMetadataModel.model_fields}
NULL_DISCOURSE["semantic_function"] = []


def test_structured_output_cannot_return_assessments_without_metadata():
    """The response schema rejects assessments-only and partial metadata replies.

    Assessments with no `metadata` object, or a metadata object missing fields, must fail
    validation; an all-null (but complete) metadata object is valid. Why: this is the exact reply
    shape that used to leave every field empty while looking like a confident inference.
    """
    # Assessments-only replies are what small models produce under constrained
    # decoding when `metadata` is optional; the values were silently lost.
    with pytest.raises(ValidationError):
        cb.DiscourseMetadataResponseModel.model_validate({"field_assessments": {"speaker": {"confidence": 0.95}}})
    with pytest.raises(ValidationError):
        cb.DiscourseMetadataResponseModel.model_validate({"metadata": {"speaker": "Derrida"}})
    with pytest.raises(ValidationError):
        cb.DiscourseMetadataResponseModel.model_validate({"metadata": NULL_DISCOURSE})
    parsed = cb.DiscourseMetadataResponseModel.model_validate({"metadata": NULL_DISCOURSE, "field_assessments": {}})
    assert parsed.metadata.speaker is None


def test_confident_llm_value_is_auto_resolved_and_low_confidence_is_populated_for_review(tmp_path: Path, monkeypatch):
    """Confidence controls verification, not whether a valid proposal is visible.

    speaker at high confidence is populated and auto-resolved. stance at 50% is also
    populated, but remains unresolved until a reviewer confirms it.
    """
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = _install_minimal_build(repo)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    record = {"record_id": "r1", "record_revision": 1, "text": "Derrida discusses hospitality.", "text_length": 30,
              "source_asset_id": "asset-elephant", "source_block_ids": ["b1"],
              "source_spans": [{"block_id": "b1", "page": 1, "confidence": 1.0}]}

    def fake(_request, prompt, *, response_model, max_tokens, schema_name, build_id=""):
        if schema_name == "derridai_record_discourse":
            evidence = {"block_ids": ["b1"], "confidence": 0.95, "reason": "explicit"}
            return {
                "metadata": {**NULL_DISCOURSE, "region_type": "main_text", "primary_text": True,
                             "discourse_role": "analysis", "speaker": "Jacques Derrida", "stance": "describe"},
                "field_evidence": {name: evidence for name in ("region_type", "primary_text", "discourse_role", "speaker", "stance")},
                "field_assessments": {
                    "speaker": {"confidence": 0.95, "needs_review": False, "reason": "explicit", "outcome": "supported_value"},
                    "stance": {"confidence": 0.5, "needs_review": False, "reason": "weak", "outcome": "supported_value"},
                },
                "review_reason": "",
            }
        return {"metadata": {}, "field_evidence": {}, "field_assessments": {}, "review_reason": ""}

    monkeypatch.setattr(manager, "_chat_json", fake)
    manager._enrich_record(record, {}, {"provider": "ollama", "model": "test-model"}, build_id=build["build_id"])

    assert record["speaker"] == "Jacques Derrida"
    assert record["metadata_field_status"]["speaker"]["verification_status"] == "auto_resolved"
    assert record["stance"] == "describe"
    assert record["metadata_field_status"]["stance"]["proposed_value"] == "describe"
    assert record["metadata_field_status"]["stance"]["auto_populated"] is True
    assert record["metadata_field_status"]["stance"]["autofilled"] is False
    assert record["metadata_field_status"]["stance"]["verification_status"] == "pending_review"
    assert record["metadata_field_status"]["stance"]["status"] == "unresolved"


def _record():
    """Minimal one-block record used by the enrichment tests."""
    return {"record_id": "r1", "record_revision": 1, "text": "Derrida discusses hospitality.", "text_length": 30,
            "source_asset_id": "asset-elephant", "source_block_ids": ["b1"],
            "source_spans": [{"block_id": "b1", "page": 1, "confidence": 1.0}]}


def _discourse_reply(**metadata):
    """Fake discourse reply: given fields set, others null, all assessed at 95% confidence."""
    evidence = {"block_ids": ["b1"], "confidence": 0.95, "reason": "explicit"}
    return {
        "metadata": {**NULL_DISCOURSE, **metadata},
        "field_evidence": {name: evidence for name, value in metadata.items() if value is not None},
        "field_assessments": {
            name: {"confidence": 0.95, "needs_review": False, "reason": "model says explicit", "outcome": "supported_value"}
            for name in ("region_type", "primary_text", "discourse_role", "speaker", "position_holder", "target", "stance")
        },
        "review_reason": "",
    }


def _enrich(tmp_path: Path, monkeypatch, record: dict, reply: dict):
    """Run enrichment on a record with the given fake discourse reply and return the record."""
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = _install_minimal_build(repo)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)

    def fake(_request, prompt, *, response_model, max_tokens, schema_name, build_id=""):
        if schema_name == "derridai_record_discourse":
            return reply
        return {"metadata": {}, "field_evidence": {}, "field_assessments": {}, "review_reason": ""}

    monkeypatch.setattr(manager, "_chat_json", fake)
    manager._enrich_record(record, {}, {"provider": "ollama", "model": "test-model"}, build_id=build["build_id"])
    return record


def test_explicit_confident_supported_absence_can_auto_resolve_an_optional_field(tmp_path: Path, monkeypatch):
    """A supported absence is different from a failed/omitted value."""
    reply = _discourse_reply(region_type="main_text", primary_text=True, discourse_role="analysis")
    reply["field_assessments"]["speaker"] = {
        "confidence": 0.95, "needs_review": False, "reason": "No distinct speaker is supported.", "outcome": "no_supported_value",
    }
    record = _enrich(tmp_path, monkeypatch, _record(), reply)

    status = record["metadata_field_status"]["speaker"]
    assert record.get("speaker") in (None, "")
    assert status["status"] == "llm_inferred"
    assert status["reason_code"] == "no_supported_value"
    assert status["verification_status"] == "auto_resolved"


def test_null_confidence_populates_value_but_keeps_it_in_review(tmp_path: Path, monkeypatch):
    """An explicit confidence=null must not hide a valid model proposal."""
    reply = _discourse_reply(
        region_type="main_text", primary_text=True, discourse_role="analysis", speaker="Jacques Derrida",
    )
    reply["field_assessments"]["speaker"] = {
        "confidence": None, "needs_review": True, "reason": "Attribution is plausible but not certain.", "outcome": "supported_value",
    }
    reply["field_evidence"]["speaker"] = {"block_ids": ["b1"], "confidence": None, "reason": "speaker cue"}
    record = _enrich(tmp_path, monkeypatch, _record(), reply)

    status = record["metadata_field_status"]["speaker"]
    assert record["speaker"] == "Jacques Derrida"
    assert status["status"] == "unresolved"
    assert status["reason_code"] in {"ambiguous", "confidence_missing"}
    assert status["auto_populated"] is True
    assert status["autofilled"] is False
    assert status["verification_status"] == "pending_review"
    assert status["llm_checked"] is True


def test_deterministic_structure_is_corroborated_by_a_matching_llm_value(tmp_path: Path, monkeypatch):
    """A matching LLM value corroborates reviewer-defined region_type and primary_text.

    The fields stay "deterministic" but are marked llm_checked True and llm_corroborates True.
    This is the case that stayed empty ("never checked") when the model returned no metadata.
    """
    record = _record()
    record.update(region_type="main_text", primary_text=True)
    record["metadata_field_status"] = {
        name: {"status": "deterministic", "method": "human_document_layout", "confidence": 1.0, "reason": "reviewer-defined layout"}
        for name in ("region_type", "primary_text")
    }
    record = _enrich(tmp_path, monkeypatch, record, _discourse_reply(region_type="main_text", primary_text=True, discourse_role="analysis"))

    for name in ("region_type", "primary_text"):
        status = record["metadata_field_status"][name]
        assert status["status"] == "deterministic"
        assert status["llm_checked"] is True
        assert status["llm_corroborates"] is True
    assert record["region_type"] == "main_text"
