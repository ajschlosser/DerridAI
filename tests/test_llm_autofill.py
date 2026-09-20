"""LLM autofill in the reconcile step: the blended confidence, the ledger, and remembered rejections."""

from __future__ import annotations

from pathlib import Path
import sys
import types

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules["chromadb"] = types.SimpleNamespace()

from app import corpus_builder as cb
from app.enrichment_cycles import learn_from_review
from app.enrichment_ledger import ACCEPTED, CORRECTED


def manager(tmp_path: Path):
    return cb.PdfCorpusBuildManager(cb.PdfCorpusRepository(tmp_path / "repo"))


def reconcile(m, confidence=0.95, needs_review=True, cite=True, record_id="r1"):
    record = {"record_id": record_id, "text": "x", "metadata_field_status": {}}
    result = {
        "metadata": {"discourse_role": "assertion"},
        "field_assessments": {"discourse_role": {"confidence": confidence, "needs_review": needs_review, "reason": "clear"}},
        "field_evidence": {"discourse_role": {"block_ids": ["b1"] if cite else [], "confidence": confidence, "reason": "quote"}},
    }
    profile = cb.CORPUS_PROFILES[cb.PROFILE_VERSION]
    return m._reconcile_metadata_results(record, profile, ["b1"], [("discourse", result, None)], False, request={"model": "qwen"}, build_id="b")


def test_a_confident_value_is_filled_even_though_the_model_asked_for_review(tmp_path):
    status = reconcile(manager(tmp_path))["metadata_field_status"]["discourse_role"]
    assert status["status"] == "llm_inferred" and status["autofilled"] is True
    assert status["self_reported_confidence"] == 0.95 and status["model"] == "qwen"


def test_no_cited_evidence_keeps_it_in_review(tmp_path):
    status = reconcile(manager(tmp_path), cite=False)["metadata_field_status"]["discourse_role"]
    assert status["status"] != "llm_inferred" or not status.get("autofilled")


def test_below_the_bar_it_still_needs_review(tmp_path):
    status = reconcile(manager(tmp_path), confidence=0.8)["metadata_field_status"]["discourse_role"]
    assert status["status"] == "unresolved" and not status.get("autofilled")


def test_reviews_that_corrected_the_model_suspend_autofill(tmp_path):
    m = manager(tmp_path)
    for i in range(20):
        m._ledger.append(ACCEPTED if i < 12 else CORRECTED, model="qwen", field="discourse_role")
    status = reconcile(m)["metadata_field_status"]["discourse_role"]
    assert status["status"] == "unresolved" and not status.get("autofilled")


def test_a_rejection_is_recorded_and_shown_to_the_next_pass(tmp_path):
    m = manager(tmp_path)
    record = {"record_id": "r1", "discourse_role": "assertion"}
    info = {"status": "llm_inferred", "method": "llm", "model": "qwen", "confidence": 0.95, "autofilled": True}
    build = m.repo.create_build({"asset_id": "a", "source_sha256": "x", "source_filename": "x.pdf", "source_page_count": 1, "source_block_count": 1,
                                 "schema_version": cb.SCHEMA_VERSION, "profile_id": cb.PROFILE_VERSION, "profile_version": 11, "app_version": "0", "provider": "ollama", "model": "qwen", "request": {}})
    m._record_human_llm_feedback(build["build_id"], "discourse_role", "assertion", "critique", info, record)
    assert record["llm_rejections"][0]["rejected_value"] == "assertion"
    assert m._ledger.review_counts("qwen", "discourse_role") == (1, 0)
    learned = learn_from_review([{**record, "discourse_role": "critique", "metadata_field_status": {}}])
    assert learned["rejected_examples"]["discourse_role"][0]["rejected_value"] == "assertion"
