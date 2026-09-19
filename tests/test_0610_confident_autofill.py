# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from pathlib import Path
import sys
import types

import pytest
from pydantic import ValidationError

sys.modules.setdefault("chromadb", types.SimpleNamespace())
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app import corpus_builder as cb
from test_0450_energized_elephant import _install_minimal_build

NULL_DISCOURSE = {name: None for name in cb.DiscourseMetadataModel.model_fields}
NULL_DISCOURSE["semantic_function"] = []


def test_structured_output_cannot_return_assessments_without_metadata():
    # Assessments-only replies are what small models produce under constrained
    # decoding when `metadata` is optional; the values were silently lost.
    with pytest.raises(ValidationError):
        cb.DiscourseMetadataResponseModel.model_validate({"field_assessments": {"speaker": {"confidence": 0.95}}})
    with pytest.raises(ValidationError):
        cb.DiscourseMetadataResponseModel.model_validate({"metadata": {"speaker": "Derrida"}})
    parsed = cb.DiscourseMetadataResponseModel.model_validate({"metadata": NULL_DISCOURSE})
    assert parsed.metadata.speaker is None


def test_confident_llm_value_is_autofilled_and_low_confidence_stays_a_suggestion(tmp_path: Path, monkeypatch):
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
                    "speaker": {"confidence": 0.95, "needs_review": False, "reason": "explicit"},
                    "stance": {"confidence": 0.5, "needs_review": False, "reason": "weak"},
                },
                "review_reason": "",
            }
        return {"metadata": {}, "field_evidence": {}, "field_assessments": {}, "review_reason": ""}

    monkeypatch.setattr(manager, "_chat_json", fake)
    manager._enrich_record(record, {}, {"provider": "ollama", "model": "test-model"}, build_id=build["build_id"])

    assert record["speaker"] == "Jacques Derrida"
    assert record["metadata_field_status"]["speaker"]["auto_populated"] is True
    assert record.get("stance") in (None, "")
    assert record["metadata_field_status"]["stance"]["proposed_value"] == "describe"
    assert record["metadata_field_status"]["stance"]["auto_populated"] is False
