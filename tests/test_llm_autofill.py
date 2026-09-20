"""LLM autofill in the reconcile step: the blended confidence, the ledger, and remembered rejections."""

from __future__ import annotations

import sys
import types
from pathlib import Path

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


def test_the_concurrency_limit_refuses_an_extra_run(tmp_path, monkeypatch):
    m = manager(tmp_path)
    monkeypatch.setattr(m, "active_enrichment_runs", lambda: 1)
    monkeypatch.setattr(m, "_validate_execution_budget", lambda request: None)
    build = m.repo.create_build({"asset_id": "a", "source_sha256": "x", "source_filename": "x.pdf", "source_page_count": 1, "source_block_count": 1,
                                 "schema_version": cb.SCHEMA_VERSION, "profile_id": cb.PROFILE_VERSION, "profile_version": 11, "app_version": "0", "provider": "ollama", "model": "m", "request": {}})
    build.update(status="awaiting_review")
    m.repo.save_build(build)
    import pytest
    with pytest.raises(ValueError, match="already working"):
        m.rerun_metadata_enrichment(build["build_id"], {"model": "m"})


def test_metrics_endpoint_payload_reports_the_limit(tmp_path):
    m = manager(tmp_path)
    m._ledger.append("accepted", model="q", field="f", run_id="r", confidence=0.9)
    payload = m.enrichment_metrics()
    assert payload["concurrency"]["limit"] >= 1 and payload["models"]["q"]["acceptance_rate"] == 1.0


def reconcile_with(m, request, record_id="rec-1"):
    record = {"record_id": record_id, "text": "x", "metadata_field_status": {}}
    result = {
        "metadata": {"discourse_role": "assertion"},
        "field_assessments": {"discourse_role": {"confidence": 0.95, "needs_review": True}},
        "field_evidence": {"discourse_role": {"block_ids": ["b1"], "confidence": 0.95}},
    }
    profile = cb.CORPUS_PROFILES[cb.PROFILE_VERSION]
    out = m._reconcile_metadata_results(record, profile, ["b1"], [("discourse", result, None)], False, request=request, build_id="b")
    return out["metadata_field_status"]["discourse_role"]


def test_the_autofill_ablation_is_the_no_autofill_baseline(tmp_path):
    status = reconcile_with(manager(tmp_path), {"model": "q", "ablations": ["autofill"]})
    assert status["status"] == "unresolved" and not status.get("autofilled")


def test_the_blend_ablation_ignores_reviewer_history(tmp_path):
    m = manager(tmp_path)
    for _ in range(20):
        m._ledger.append(CORRECTED, model="q", field="discourse_role")
    assert reconcile_with(m, {"model": "q"})["status"] == "unresolved"  # history drags the blend down
    assert reconcile_with(m, {"model": "q", "ablations": ["blended_confidence"]})["autofilled"] is True


def test_events_carry_the_conditions_they_ran_under(tmp_path):
    m = manager(tmp_path)
    reconcile_with(m, {"model": "q", "arm": "B", "run_id": "run7", "ablations": ["rejection_memory"], "generation": {"temperature": 0.1, "seed": 3}})
    row = next(e for e in m._ledger.events() if e["kind"] == "proposed")
    assert (row["arm"], row["run_id"], row["seed"], row["ablations"]) == ("B", "run7", 3, ["rejection_memory"])
    assert row["code_version"] and row["prompt_version"]


def test_gold_records_never_feed_the_blend(tmp_path):
    m = manager(tmp_path)
    m._ledger.append(CORRECTED, model="q", field="f", gold=True)
    m._ledger.append(ACCEPTED, model="q", field="f", gold=False)
    assert m._ledger.review_counts("q", "f") == (1, 1)


def test_blind_records_seal_the_models_value_and_score_the_reviewers_own(tmp_path):
    m = manager(tmp_path)
    request = {"model": "q", "blind_rate": 1.0}
    result = {
        "metadata": {"discourse_role": "assertion"},
        "field_assessments": {"discourse_role": {"confidence": 0.99, "needs_review": False, "reason": "it asserts"}},
        "field_evidence": {"discourse_role": {"block_ids": ["b1"], "confidence": 0.99, "reason": "it asserts"}},
    }
    # Execution stores the model's full answer on the record; blind review must scrub it too.
    record = {"record_id": "rec-9", "text": "x", "metadata_field_status": {}, "metadata_stage_results": {"discourse": __import__("copy").deepcopy(result)}}
    profile = cb.CORPUS_PROFILES[cb.PROFILE_VERSION]
    out = m._reconcile_metadata_results(record, profile, ["b1"], [("discourse", result, None)], False, request=request, build_id="b")
    status = out["metadata_field_status"]["discourse_role"]
    # Nothing the browser receives says what the model thought, and nothing is autofilled.
    assert out["discourse_role"] is None and status["blind"] is True and status["status"] == "unresolved"
    assert "assertion" not in str(out) and "it asserts" not in str(out) and "0.99" not in str(out) and "proposed_value" not in status and not status.get("autofilled")
    assert m._ledger.sealed_value("b", "rec-9", "discourse_role") == "assertion"
    # The reviewer decides without seeing it; then it is revealed and the agreement is logged.
    m._record_human_llm_feedback("b", "discourse_role", None, "critique", status, out)
    label = next(e for e in m._ledger.events() if e["kind"] == "blind_label")
    assert label["agreed"] is False and label["value"] == "assertion" and label["new_value"] == "critique"
    assert out["blind_reveals"]["discourse_role"] == "assertion"


def test_anchoring_compares_seen_and_blind_agreement():
    from app.enrichment_metrics import compute

    rows = [{"kind": "accepted", "model": "m", "field": "f", "confidence": 0.9}] * 9 + [{"kind": "corrected", "model": "m", "field": "f", "confidence": 0.9}]
    rows += [{"kind": "blind_label", "model": "m", "field": "f", "agreed": i < 5} for i in range(10)]
    m = compute(rows)["models"]["m"]
    assert m["blind_labels"] == 10 and m["blind_agreement_ci"]["rate"] == 0.5
    assert m["anchoring"]["difference"] == 0.4 and m["anchoring"]["p_value"] < 0.1
