# Copyright 2026 Aaron John Schlosser, PhD.
"""Record Review treats a restated value as the same value, not as a model correction.

Why: a reviewer who changes "J.P. Dingus" to "J. P. Dingus" has accepted the model's
answer. Scoring that as a correction penalizes calibration, and remembering it as a
rejection teaches the next pass to avoid the right answer.
How: `install` creates a build whose record carries a model assertion with evidence;
tests then save reviewer values through the real review methods.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules["chromadb"] = types.SimpleNamespace()

from app import corpus_builder as cb
from app.config import APP_VERSION
from app.enrichment_cycles import learn_from_review
from app.enrichment_ledger import ACCEPTED, CORRECTED, UNRESOLVED
from app.enrichment_metrics import compute
from app.field_assertions import (
    create_model_assertion,
    current_assertion_by_name,
    project_record_assertions,
)
from app.metadata_exemplars import build_correction_exemplars, build_metadata_exemplar
from app.metadata_schema import default_schema
from app.semantic_identity import SEMANTIC_IDENTITY_VERSION

EVIDENCE = {"block_ids": ["b1"], "confidence": 0.9, "reason": "Named as the speaker."}


def install(tmp_path: Path, field: str, value, text="J. P. Dingus says so."):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    asset = {"asset_id": "a", "sha256": "x", "filename": "x.pdf", "page_count": 1, "block_count": 1, "ocr_pages": 0, "warnings": [], "metadata": {}, "pages": []}
    cb._json_write(repo.asset_meta_path("a"), asset)
    repo.asset_blocks_path("a").write_text(json.dumps({"block_id": "b1", "page": 1, "bbox": [0, 0, 1, 1], "type": "paragraph", "text": text, "extraction_method": "native", "confidence": 1.0}) + "\n", encoding="utf-8")
    build = repo.create_build({"asset_id": "a", "source_sha256": "x", "source_filename": "x.pdf", "source_page_count": 1, "source_block_count": 1,
                               "schema_version": cb.SCHEMA_VERSION, "profile_id": cb.PROFILE_VERSION, "profile_version": 11, "app_version": APP_VERSION,
                               "provider": "ollama", "model": "qwen", "request": {"enrichment_mode": "fast"}, "manifest": {"title": "Book", "document_author": "Derrida"}})
    build["status"] = "review"; build["stage"] = "review"; build["record_count"] = 1; repo.save_build(build)
    record = {"record_id": "r1", "record_revision": 1, "text": text, "text_length": len(text), "language": "en", "source_block_ids": ["b1"],
              "source_spans": [{"block_id": "b1", "page": 1}], "pdf_pages": [1], "metadata_field_status": {}, "review_disposition": "pending",
              "accepted": False, "rejected": False}
    create_model_assertion(record, field, value, schema=default_schema(), confidence=0.8, model="qwen", evidence=[dict(EVIDENCE)])
    project_record_assertions(record)
    record["metadata_field_status"][field]["model"] = "qwen"
    repo.save_records(build["build_id"], [record])
    return repo, build, cb.PdfCorpusBuildManager(repo, max_workers=1)


def review_rows(manager, kind=None):
    return [e for e in manager._ledger.events() if e.get("kind") in ({kind} if kind else {ACCEPTED, CORRECTED, UNRESOLVED, "rejected"})]


def test_equivalent_name_edit_is_an_acceptance_that_keeps_both_surfaces_and_the_evidence(tmp_path):
    repo, build, manager = install(tmp_path, "speaker", "J.P. Dingus")
    model_assertion = current_assertion_by_name(repo.load_records(build["build_id"])[0], "speaker")
    updated = manager.patch_metadata(build["build_id"], "r1", {"speaker": "J. P. Dingus"}, expected_revision=1)

    # The reviewer's surface is stored; the model's assertion still says exactly what it said.
    assert updated["speaker"] == "J. P. Dingus"
    stored = repo.load_records(build["build_id"])[0]
    current = current_assertion_by_name(stored, "speaker")
    assert current.value == "J. P. Dingus" and current.supersedes_assertion_id == model_assertion.assertion_id
    history = [a for a in stored["field_assertions"][current.field_id] if a["assertion_id"] == model_assertion.assertion_id]
    assert history and history[0]["value"] == "J.P. Dingus"
    # A restatement confirms rather than overrides, and is not a remembered rejection.
    assert current.authority_status == "human_confirmed"
    assert not stored.get("llm_rejections")
    # Evidence is kept, but it is still the model's selection: nothing promoted it.
    assert current.evidence and current.evidence[0]["block_ids"] == ["b1"]
    assert current.evidence[0].get("reviewed_by") != "human"
    assert current.evidence[0]["carried_from_assertion_id"] == model_assertion.assertion_id
    assert stored["metadata_evidence"]["speaker"]["block_ids"] == ["b1"]
    assert build_metadata_exemplar(stored, "speaker", {"b1": {"block_id": "b1", "text": "J. P. Dingus says so."}}) is None
    # Scored as accepted, with the relation and version on the ledger row and in the decision log.
    rows = review_rows(manager)
    assert [r["kind"] for r in rows] == [ACCEPTED]
    assert rows[0]["equivalence_relation"] == "equivalent" and rows[0]["equivalence_version"] == SEMANTIC_IDENTITY_VERSION
    assert rows[0]["surface_changed"] is True and rows[0]["value"] == "J.P. Dingus"
    decision = [d for d in stored["metadata_decisions"] if d.get("field") == "speaker"][-1]
    assert decision["equivalence_relation"] == "equivalent" and decision["prior_value"] == "J.P. Dingus"
    assert decision["equivalence_profile"] == "entity_name"
    calibration = repo.get_build(build["build_id"])["llm_confidence_calibration"]["speaker"]["medium"]
    assert calibration["accepted"] == 1 and calibration.get("corrected", 0) == 0


def test_different_value_is_still_a_correction_and_drops_the_evidence(tmp_path):
    repo, build, manager = install(tmp_path, "speaker", "J.P. Dingus")
    manager.patch_metadata(build["build_id"], "r1", {"speaker": "Levinas"}, expected_revision=1)
    stored = repo.load_records(build["build_id"])[0]
    assert [r["kind"] for r in review_rows(manager)] == [CORRECTED]
    assert stored["llm_rejections"][0]["rejected_value"] == "J.P. Dingus"
    assert stored["llm_rejections"][0]["equivalence_relation"] == "different"
    assert current_assertion_by_name(stored, "speaker").authority_status == "human_override"
    assert "speaker" not in (stored.get("metadata_evidence") or {})


def test_unknown_relation_is_neutral(tmp_path):
    repo, build, manager = install(tmp_path, "speaker", "J. Dingus")
    manager.patch_metadata(build["build_id"], "r1", {"speaker": "John Dingus"}, expected_revision=1)
    stored = repo.load_records(build["build_id"])[0]
    assert stored["speaker"] == "John Dingus"
    rows = review_rows(manager)
    assert [r["kind"] for r in rows] == [UNRESOLVED]
    assert rows[0]["equivalence_reasons"] == ["shared_surname"]
    assert not stored.get("llm_rejections")
    assert "calibration" not in json.dumps(repo.get_build(build["build_id"]).get("llm_confidence_calibration") or {})
    # Not counted as accepted or corrected anywhere.
    assert manager._ledger.review_counts("qwen", "speaker") == (0, 0)
    metrics = compute(manager._ledger.events())["models"].get("qwen", {})
    assert metrics.get("reviews", 0) == 0
    # The value is not newly bound to evidence chosen for another surface.
    assert "speaker" not in (stored.get("metadata_evidence") or {})


def test_bulk_edit_uses_the_same_equivalence(tmp_path):
    repo, build, manager = install(tmp_path, "speaker", "J.P. Dingus")
    manager.bulk_patch_metadata(build["build_id"], {"speaker": "JP Dingus"}, record_ids=["r1"])
    stored = repo.load_records(build["build_id"])[0]
    assert [r["kind"] for r in review_rows(manager)] == [ACCEPTED]
    assert not stored.get("llm_rejections")
    assert stored["metadata_evidence"]["speaker"]["block_ids"] == ["b1"]


def test_legacy_equivalent_rejections_do_not_become_hard_negatives_or_rejected_examples():
    schema = default_schema()
    record = {
        "record_id": "r1", "record_revision": 2, "source_block_ids": ["b1"], "text": "J. P. Dingus says so.", "language": "en",
        "speaker": "J. P. Dingus",
        "metadata_field_status": {"speaker": {"status": "human_confirmed", "method": "human"}},
        "metadata_evidence": {"speaker": {"block_ids": ["b1"], "reviewed_by": "human"}},
        # Recorded before equivalence existed: no relation stored on the row.
        "llm_rejections": [{"field": "speaker", "rejected_value": "J.P. Dingus", "chosen_value": "J. P. Dingus", "model": "qwen"}],
    }
    blocks = {"b1": {"block_id": "b1", "page": 1, "text": "J. P. Dingus says so."}}
    assert build_correction_exemplars(record, blocks, schema=schema) == []
    # The audit row itself is untouched.
    assert record["llm_rejections"][0]["rejected_value"] == "J.P. Dingus"
    learned = learn_from_review([record], schema)
    assert learned["field_stats"]["speaker"] == {"accepted": 1, "rejected": 0}
    assert "speaker" not in learned["rejected_examples"]
    # A real correction still is one, with identity keys beside the exact values.
    record["llm_rejections"] = [{"field": "speaker", "rejected_value": "Levinas", "chosen_value": "J. P. Dingus", "model": "qwen"}]
    [correction] = build_correction_exemplars(record, blocks, schema=schema)
    assert correction["field_value"] == "J. P. Dingus" and correction["rejected_value"] == "Levinas"
    assert correction["canonical_value_key"] != correction["rejected_canonical_value_key"]
    assert correction["equivalence_profile"] == "entity_name"
    # A stored relation is authoritative over recomputation.
    record["llm_rejections"][0]["equivalence_relation"] = "unknown"
    assert build_correction_exemplars(record, blocks, schema=schema) == []


def test_positive_exemplar_keeps_exact_surface_with_a_shared_identity_key():
    schema = default_schema()
    blocks = {"b1": {"block_id": "b1", "page": 1, "text": "J. P. Dingus says so."}}
    base = {"record_id": "r1", "record_revision": 1, "source_block_ids": ["b1"], "text": "J. P. Dingus says so.",
            "metadata_field_status": {"speaker": {"status": "human_confirmed", "method": "human"}},
            "metadata_evidence": {"speaker": {"block_ids": ["b1"], "reviewed_by": "human"}}}
    one = build_metadata_exemplar({**base, "speaker": "J.P. Dingus"}, "speaker", blocks, schema=schema)
    two = build_metadata_exemplar({**base, "record_id": "r2", "speaker": "JP Dingus"}, "speaker", blocks, schema=schema)
    assert one["field_value"] == "J.P. Dingus" and two["field_value"] == "JP Dingus"
    assert one["canonical_value_key"] == two["canonical_value_key"]
    assert one["metadata_exemplar_id"] != two["metadata_exemplar_id"]


def test_learning_counts_an_equivalent_edit_on_an_enriched_field_as_accepted():
    record = {
        "record_id": "r1", "speaker": "J. P. Dingus",
        "metadata_field_status": {"speaker": {"status": "human_confirmed", "method": "human"}},
        "metadata_enrichment_history": [{"added_fields": ["speaker"]}],
        "metadata_decisions": [{"field": "speaker", "value": "J. P. Dingus", "equivalence_relation": "equivalent"}],
    }
    assert learn_from_review([record], default_schema())["field_stats"]["speaker"] == {"accepted": 1, "rejected": 0}
    record["metadata_decisions"][0]["equivalence_relation"] = "unknown"
    assert "speaker" not in learn_from_review([record], default_schema())["field_stats"]


def test_blind_label_agreement_is_equivalence_aware(tmp_path):
    repo, build, manager = install(tmp_path, "speaker", "J.P. Dingus")
    bid = build["build_id"]
    manager._ledger.append("proposed", model="q", field="speaker", build_id=bid, record_id="r1", value="J.P. Dingus", blind=True)
    record = {"record_id": "r1", "text": "x"}
    manager._record_human_llm_feedback(bid, "speaker", None, "J. P. Dingus", {"status": "unresolved", "method": "llm", "model": "q", "blind": True}, record)
    label = next(e for e in manager._ledger.events() if e["kind"] == "blind_label")
    assert label["agreed"] is True and label["equivalence_relation"] == "equivalent"


def test_metrics_split_exact_from_restated_acceptance_and_count_unresolved_apart():
    rows = [
        {"kind": ACCEPTED, "model": "m", "field": "speaker", "confidence": 0.9, "equivalence_relation": "exact"},
        {"kind": ACCEPTED, "model": "m", "field": "speaker", "confidence": 0.9, "equivalence_relation": "equivalent"},
        {"kind": CORRECTED, "model": "m", "field": "speaker", "confidence": 0.9, "equivalence_relation": "different"},
        {"kind": UNRESOLVED, "model": "m", "field": "speaker", "confidence": 0.9, "equivalence_relation": "unknown"},
    ]
    metrics = compute(rows)["models"]["m"]
    assert metrics["reviews"] == 3 and metrics["acceptance_rate"] == pytest.approx(2 / 3, abs=1e-3)
    assert metrics["accepted_exact"] == 1 and metrics["accepted_equivalent"] == 1
    assert metrics["unresolved_reviews"] == 1
