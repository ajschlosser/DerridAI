"""Multi-pass metadata enrichment: conflict rules, learning, and safe concurrency.

Why: enrichment passes may be chained while a reviewer keeps working. Human
edits must never be lost, disagreements must be decided only when the model is
confident, and what reviewers teach one pass must reach the next.
How: `resolve_conflict`, `learn_from_review`, and `learn_from_pass` are pure; the manager tests
stub `_enrich_record` (no provider) and run the worker inline.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules["chromadb"] = types.SimpleNamespace()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
from app import corpus_builder as cb
from app import enrichment_cycles as ec
from app.config import APP_VERSION
from app.corpus_review_mutations import requeue_record_metadata


def test_enrichment_scope_can_target_explicit_records() -> None:
    rows = [
        {"record_id": "r1", "review_disposition": "pending"},
        {"record_id": "r2", "review_disposition": "accepted"},
        {"record_id": "r3", "review_disposition": "pending"},
    ]
    assert cb._enrichment_pass_indices(rows, "all", ["r2", "r3"]) == [1, 2]


def test_trash_quality_ratio_is_deterministic() -> None:
    rows = [
        {"record_id": "good", "text": "A sufficiently legible scholarly passage with normal words."},
        {"record_id": "bad", "text": "\ufffd\ufffd\nx\nx"},
    ]
    report = cb._trash_quality_report(rows)
    assert report["deterministic"] is True
    assert report["trash_record_count"] == 1
    assert report["exceeds_threshold"] is True


def test_trash_quality_counts_high_text_noise() -> None:
    rows = [
        {"record_id": "good", "text": "A sufficiently legible scholarly passage with normal words.",
         "text_noise": {"score": 8, "threshold": 45, "unusable": False}},
        {"record_id": "ocr", "text": "enough letters here to skip sparse-text heuristics on this row",
         "text_noise": {"score": 72, "threshold": 45, "unusable": True}},
    ]
    report = cb._trash_quality_report(rows)
    assert report["trash_record_count"] == 1
    assert "high_text_noise" in report["records"][0]["reasons"]
    assert report["median_noise"] == 40.0
    assert report["noise_unusable_threshold"] == 45



class InlineExecutor:
    """Runs submitted work immediately so worker behavior is deterministic."""

    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)


def make_manager(tmp_path: Path, rows: list[dict], *, real_validation: bool = False):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    asset_id = "a"
    if real_validation:
        import fitz

        doc = fitz.open()
        doc.new_page().insert_text((72, 72), "A short source page.")
        asset_id = repo.save_asset(doc.tobytes(), filename="t.pdf", ocr_mode="off")["asset_id"]
    build = repo.create_build({
        "asset_id": asset_id, "source_sha256": "x", "source_filename": "x.pdf", "source_page_count": 1,
        "source_block_count": len(rows), "schema_version": cb.SCHEMA_VERSION, "profile_id": cb.PROFILE_VERSION,
        "profile_version": 11, "app_version": APP_VERSION, "provider": "ollama", "model": "m",
        "request": {"provider": "ollama", "model": "m"}, "manifest": {"title": "Book"},
    })
    build["status"], build["stage"] = "awaiting_review", "review"
    repo.save_build(build)
    for i, row in enumerate(rows, 1):
        row.setdefault("record_id", f"r{i}")
        row.setdefault("text", f"record {i}")
        row.setdefault("metadata_field_status", {})
    repo.save_records(build["build_id"], rows)
    manager = cb.PdfCorpusBuildManager(repo)
    manager._executor = InlineExecutor()
    manager._validate_execution_budget = lambda request: None
    if not real_validation:
        # Whole-build validation needs the real source asset; it is not under test here.
        manager._rewrite_and_validate = lambda build_id, records: repo.get_build(build_id)
    return manager, repo, build["build_id"]


def proposal(record: dict, **fields) -> dict:
    """What a pass returns: the record with new values and per-field confidence."""
    out = dict(record)
    status = dict(out.get("metadata_field_status") or {})
    for field, (value, confidence) in fields.items():
        out[field] = value
        status[field] = {"status": "model_inferred", "method": "llm", "confidence": confidence}
    out["metadata_field_status"] = status
    return out


def test_resolve_conflict_decides_only_when_confidence_separates():
    """Human wins; a confident, clearly better proposal replaces; ties keep both."""
    human = {"status": "human_confirmed", "confidence": 0.2}
    assert ec.resolve_conflict(human, {"confidence": 0.99}) == "keep_existing"
    weak_old = {"status": "model_inferred", "confidence": 0.6}
    assert ec.resolve_conflict(weak_old, {"confidence": 0.9}) == "replace"
    assert ec.resolve_conflict({"status": "model_inferred", "confidence": 0.85}, {"confidence": 0.8}) == "keep_both"
    assert ec.resolve_conflict({"status": "model_inferred", "confidence": 0.9}, {"confidence": 0.5}) == "keep_existing"
    assert ec.resolve_conflict(weak_old, {"confidence": None}) == "keep_both"
    assert ec.resolve_conflict({"status": "unresolved"}, {"confidence": 0.8}) == "replace"


def test_learn_from_review_counts_only_reviewer_decisions():
    """Accepted/rejected tallies come from human-resolved disputes and additions."""
    rows = [
        {"record_id": "a", "stance": "critical", "metadata_disputes": [{"field": "stance", "existing": "neutral", "proposed": "critical"}],
         "metadata_field_status": {"stance": {"status": "human_confirmed"}}},
        {"record_id": "b", "stance": "neutral", "metadata_disputes": [{"field": "stance", "existing": "neutral", "proposed": "critical"}],
         "metadata_field_status": {"stance": {"status": "human_override"}}},
        {"record_id": "c", "stance": "x", "metadata_disputes": [{"field": "stance", "existing": "y", "proposed": "x"}],
         "metadata_field_status": {"stance": {"status": "unresolved"}}},
    ]
    learned = ec.learn_from_review(rows)
    assert learned["field_stats"] == {"stance": {"accepted": 1, "rejected": 1}}
    assert learned["rejected_examples"]["stance"] == [{"record_id": "b", "rejected_value": "critical", "chosen_value": "neutral"}]


def test_learn_from_pass_uses_unreviewed_inferences_and_defers_to_reviewers():
    """A later pass can learn from the last one before any reviewer has judged those fields."""
    rows = [
        {"record_id": "rec-a", "discourse_role": "analysis", "speaker": "Derrida",
         "metadata_field_status": {
             "discourse_role": {"status": "model_inferred", "confidence": 0.9},
             "speaker": {"status": "model_inferred", "confidence": 0.88},
         }},
        {"record_id": "rec-b", "discourse_role": "analysis", "speaker": "Derrida",
         "metadata_field_status": {
             "discourse_role": {"status": "model_inferred", "confidence": 0.8},
             "speaker": {"status": "model_inferred", "confidence": 0.91},
         }},
        {"record_id": "rec-c", "discourse_role": "commentary", "stance": "critical",
         "metadata_field_status": {
             "discourse_role": {"status": "model_inferred", "confidence": 0.4},
             "stance": {"status": "human_confirmed"},
         },
         "metadata_disputes": [{"field": "stance", "existing": "neutral", "proposed": "critical"}]},
        {"record_id": "rec-d", "metadata_disputes": [{"field": "region_type", "existing": "main_text", "proposed": "note"}]},
    ]
    learned = ec.learn_from_pass(rows)
    assert learned["field_stats"] == {"stance": {"accepted": 1, "rejected": 0}}
    assert "stance" not in learned["prior_pass"]["inferred_conventions"]
    assert learned["prior_pass"]["inferred_conventions"]["discourse_role"]["value"] == "analysis"
    assert learned["prior_pass"]["inferred_conventions"]["discourse_role"]["records"] == 2
    assert learned["prior_pass"]["inferred_conventions"]["speaker"]["value"] == "Derrida"
    assert learned["prior_pass"]["disputed_fields"]["region_type"] == 1
    assert "commentary" != learned["prior_pass"]["inferred_conventions"]["discourse_role"]["value"]
    blocked = rows + [{
        "record_id": "e", "discourse_role": "reported_position",
        "metadata_field_status": {"discourse_role": {"status": "human_confirmed"}},
    }]
    assert "discourse_role" not in ec.learn_from_pass(blocked)["prior_pass"]["inferred_conventions"]


def test_global_store_promotes_only_generalizable_conventions_seen_in_several_builds(tmp_path: Path):
    """Names stay local; a role convention needs two builds with two confirmations each."""
    store = ec.GlobalLearningStore(tmp_path / "g.json")
    role = {"value": "analysis", "confirmed_records": 3}
    store.observe("b1", {"discourse_role": role, "speaker": {"value": "Derrida", "confirmed_records": 9}})
    assert store.conventions() == {}
    store.observe("b2", {"discourse_role": {"value": "analysis", "confirmed_records": 2}})
    promoted = store.conventions()
    assert promoted == {"discourse_role": {"value": "analysis", "confirmed_records": 5, "scope": "global"}}
    assert "speaker" not in promoted
    assert store.conventions(exclude_build_id="b2") == {}


def test_review_stays_editable_while_a_pass_runs(tmp_path: Path):
    manager, repo, build_id = make_manager(tmp_path, [{}])
    build = repo.get_build(build_id)
    build.update(status="running", stage="metadata_enrichment_rerun")
    repo.save_build(build)
    assert manager._assert_human_review_available(build_id)["stage"] == "metadata_enrichment_rerun"


def test_pass_preserves_edits_made_while_it_runs(tmp_path: Path):
    """A reviewer edit to another record during the pass survives the pass's writes."""
    manager, repo, build_id = make_manager(tmp_path, [{}, {}])

    def fake_enrich(record, manifest, request, **kwargs):
        if record["record_id"] == "r1":
            live = repo.load_records(build_id)
            live[1]["speaker"] = "typed by human"
            live[1]["metadata_field_status"]["speaker"] = {"status": "human_override"}
            repo.save_records(build_id, live)
        return proposal(record, stance=("critical", 0.9))

    manager._enrich_record = fake_enrich
    manager.rerun_metadata_enrichment(build_id, {"families": ["discourse"], "scope": "all"})
    rows = {row["record_id"]: row for row in repo.load_records(build_id)}
    assert rows["r2"]["speaker"] == "typed by human"
    assert rows["r2"]["metadata_field_status"]["speaker"]["status"] == "human_override"
    assert rows["r1"]["stance"] == "critical"
    assert repo.get_build(build_id)["status"] == "awaiting_review"


def test_protected_and_agreement_feedback_is_retained_without_reopening(tmp_path: Path):
    """Human-owned disagreement and model agreement are informational only."""
    manager, repo, build_id = make_manager(tmp_path, [{
        "review_disposition": "accepted",
        "accepted": True,
        "speaker": "Jacques Derrida",
        "stance": "critical",
        "metadata_field_status": {
            "speaker": {"status": "human_confirmed"},
            "stance": {"status": "model_inferred", "method": "llm", "confidence": 0.8},
        },
    }])
    manager._enrich_record = lambda record, manifest, request, **kw: proposal(
        record, speaker=("Another author", 0.92), stance=("critical", 0.91),
    )
    manager.rerun_metadata_enrichment(build_id, {"families": ["discourse"], "scope": "all", "model": "test-model"})
    current = repo.load_records(build_id)[0]
    events = current["metadata_enrichment_history"][-1]["informational"]
    assert current["speaker"] == "Jacques Derrida"
    assert current["review_disposition"] == "accepted"
    assert not current.get("needs_review")
    assert {event["kind"] for event in events} == {"protected_suggestion", "agreement"}
    assert repo.get_build(build_id)["metadata_operation"]["records_reopened"] == 0


def test_boundary_mutation_only_requeues_records_that_have_started_enrichment():
    queued = {
        "metadata_enrichment_state": "queued",
        "metadata_stage_status": {"discourse": "queued", "quotation": "queued", "indexing": "queued"},
    }
    completed = {
        "metadata_enrichment_state": "complete",
        "metadata_enrichment_finished": True,
        "metadata_stage_status": {"discourse": "complete", "quotation": "skipped", "indexing": "skipped"},
    }
    assert requeue_record_metadata(queued, "changed") is False
    assert "metadata_requeue_requested" not in queued
    assert requeue_record_metadata(completed, "changed") is True
    assert completed["metadata_requeue_requested"] is True


def test_chain_replaces_confidently_keeps_both_when_unsure_and_stops_when_converged(tmp_path: Path):
    """Pass 1 decides confident conflicts; pass 2 sees nothing new and ends the chain."""
    rows = [
        {"stance": "neutral", "review_disposition": "accepted", "accepted": True, "metadata_field_status": {"stance": {"status": "model_inferred", "confidence": 0.5}}},
        {"stance": "neutral", "review_disposition": "accepted", "accepted": True, "metadata_field_status": {"stance": {"status": "model_inferred", "confidence": 0.8}}},
        {"stance": "neutral", "metadata_field_status": {"stance": {"status": "human_confirmed"}}},
    ]
    manager, repo, build_id = make_manager(tmp_path, rows)
    confidences = {"r1": 0.9, "r2": 0.82, "r3": 0.99}
    manager._enrich_record = lambda record, manifest, request, **kw: proposal(record, stance=("critical", confidences[record["record_id"]]))
    manager.rerun_metadata_enrichment(build_id, {"families": ["discourse"], "scope": "all", "passes": 5})
    by_id = {row["record_id"]: row for row in repo.load_records(build_id)}
    assert by_id["r1"]["stance"] == "critical"
    assert by_id["r2"]["stance"] == "neutral" and len(by_id["r2"]["metadata_disputes"]) == 1
    assert by_id["r3"]["stance"] == "neutral" and not by_id["r3"].get("metadata_disputes")
    op = repo.get_build(build_id)["metadata_operation"]
    assert op["passes_completed"] == 2 and op["converged"] is True
    assert op["state"] == "completed", op.get("error")
    assert op["records_reopened"] == 2


def test_review_action_during_a_pass_does_not_end_the_running_state(tmp_path: Path):
    """Every review action revalidates the build; that must not flip a running pass to review.

    Why: found in a live run. The build went to awaiting_review at the reviewer's first
    edit, so the UI lost the run and a second pass could start alongside the first.
    """
    manager, repo, build_id = make_manager(tmp_path, [{}, {}], real_validation=True)
    seen: dict = {}

    def fake_enrich(record, manifest, request, **kwargs):
        if record["record_id"] == "r1" and not seen:
            manager.metadata_decision(build_id, "r2", "stance", "chosen by reviewer")
            during = repo.get_build(build_id)
            seen["status"], seen["stage"] = during["status"], during["stage"]
            with pytest.raises(ValueError, match="active corpus operation"):
                manager.rerun_metadata_enrichment(build_id, {"families": ["discourse"], "scope": "all"})
        return proposal(record, stance=("critical", 0.9))

    manager._enrich_record = fake_enrich
    manager.rerun_metadata_enrichment(build_id, {"families": ["discourse"], "scope": "all"})
    assert seen == {"status": "running", "stage": "metadata_enrichment_rerun"}
    rows = {row["record_id"]: row for row in repo.load_records(build_id)}
    assert rows["r2"]["stance"] == "chosen by reviewer"
    assert repo.get_build(build_id)["status"] == "awaiting_review"


def test_same_value_treats_restatements_as_agreement_and_real_changes_as_disagreement():
    """Found live: a 0.9917 vs 0.99 wobble and a one-item list difference are not disagreements."""
    assert ec.same_value("Critical", " critical ")
    assert ec.same_value(0.9917, 0.99)
    assert ec.same_value(["a", "b", "c", "d"], ["A", "b", "c", "d", "e"])
    assert not ec.same_value("critical", "affirmative")
    assert not ec.same_value(0.5, 0.9)
    assert not ec.same_value(["a", "b"], ["c", "d"])
    assert not ec.same_value(["a"], "a")


def test_pass_ignores_confidence_telemetry_and_near_duplicate_lists(tmp_path: Path):
    """Neither a self-reported confidence nor a near-identical topic list raises a dispute."""
    rows = [{
        "semantic_classification_confidence": 0.9917, "topics": ["hospitality", "ethics", "borders", "asylum"],
        "metadata_field_status": {"topics": {"status": "model_inferred", "confidence": 1.0}, "semantic_classification_confidence": {"status": "model_inferred"}},
    }]
    manager, repo, build_id = make_manager(tmp_path, rows)
    manager._enrich_record = lambda record, manifest, request, **kw: proposal(
        record, topics=(["hospitality", "ethics", "borders", "asylum", "law"], 1.0), semantic_classification_confidence=(0.6, 1.0), stance=("critical", 0.9),
    )
    manager.rerun_metadata_enrichment(build_id, {"families": ["discourse", "indexing"], "scope": "all"})
    row = repo.load_records(build_id)[0]
    assert row["semantic_classification_confidence"] == 0.9917
    assert row["topics"] == ["hospitality", "ethics", "borders", "asylum"]
    assert not row.get("metadata_disputes")
    assert row["stance"] == "critical"


def test_next_pass_reads_last_pass_inferences_without_reviewing_records(tmp_path: Path):
    """Starting another pass does not require accepting records; it sees last-pass conventions."""
    rows = [
        {"discourse_role": "analysis", "metadata_field_status": {"discourse_role": {"status": "model_inferred", "confidence": 0.9}}},
        {"discourse_role": "analysis", "metadata_field_status": {"discourse_role": {"status": "model_inferred", "confidence": 0.86}}},
        {"discourse_role": "analysis", "review_disposition": "pending", "metadata_field_status": {"discourse_role": {"status": "model_inferred", "confidence": 0.84}}},
    ]
    manager, repo, build_id = make_manager(tmp_path, rows)
    seen: list[dict] = []

    def fake_enrich(record, manifest, request, **kwargs):
        seen.append(manager._editorial_memory(build_id, record, exclude_record_id=str(record.get("record_id") or "")))
        return proposal(record, stance=("critical", 0.9))

    manager._enrich_record = fake_enrich
    manager.rerun_metadata_enrichment(build_id, {"families": ["discourse"], "scope": "all"})
    conventions = [memory["pass_learning"]["prior_pass"]["inferred_conventions"] for memory in seen]
    assert any(item.get("discourse_role", {}).get("value") == "analysis" for item in conventions)
    dispositions = [str(row.get("review_disposition") or "pending") for row in repo.load_records(build_id)]
    assert "accepted" not in dispositions[:2]
    assert repo.get_build(build_id)["status"] == "awaiting_review"


def test_initial_enrichment_operation_marks_the_first_pass_complete():
    op = cb._initial_enrichment_operation("build-abc123def", [{}, {}], started_at="t0")
    assert op["kind"] == "metadata_enrichment"
    assert op["state"] == "completed"
    assert op["passes_completed"] == 1
    assert op["records_processed"] == 2
    assert op["started_at"] == "t0"

def test_updated_existing_dispute_counts_as_a_change_and_keeps_pass_provenance(tmp_path: Path):
    live = {
        "record_id": "r1", "text": "record 1", "stance": "neutral",
        "metadata_field_status": {
            "stance": {"status": "unresolved", "method": "llm", "confidence": 0.70, "value_source": "llm", "verification_status": "pending_review"}
        },
    }
    manager, repo, build_id = make_manager(tmp_path, [live])
    current = repo.load_records(build_id)[0]

    first = proposal(current, stance=("critical", 0.75))
    first["metadata_field_status"]["stance"].update(value_source="llm", verification_status="pending_review")
    one = manager._merge_enrichment_candidate(
        current, first, ["discourse"], "run-x", {"model": "m1"},
        manager._profile_for(build_id), schema=manager._schema_for(build_id), pass_number=1,
    )
    assert one["outcome"] == "disputed"

    second = proposal(current, stance=("qualified", 0.78))
    second["metadata_field_status"]["stance"].update(value_source="llm", verification_status="pending_review")
    two = manager._merge_enrichment_candidate(
        current, second, ["discourse"], "run-x", {"model": "m2"},
        manager._profile_for(build_id), schema=manager._schema_for(build_id), pass_number=2,
    )
    assert two["outcome"] == "disputed"
    assert two["disputed"] == 1
    dispute = current["metadata_disputes"][0]
    assert [item["value"] for item in dispute["candidates"]] == ["neutral", "critical", "qualified"]
    assert dispute["candidates"][-1]["model"] == "m2"
    assert dispute["candidates"][-1]["pass"] == 2
    assert current["metadata_enrichment_history"][-1]["pass"] == 2


def test_settled_enrichment_reason_is_not_left_as_a_fake_blocker():
    record = {
        "needs_review": True,
        "review_reason": "Metadata enrichment added, replaced, or disputed metadata; review the highlighted changes.",
        "metadata_incomplete_fields": [],
        "metadata_review_fields": [],
        "metadata_disputes": [{"field": "stance", "resolved_at": "now"}],
    }
    cb._settle_enrichment_review_reason(record)
    assert record["review_reason"] == "Pending human review."


def test_pending_llm_proposals_are_preserved_as_dispute_candidates(tmp_path: Path):
    # PR #81 disputes must preserve PR #83's populated-but-unverified proposal.
    live = {
        "record_id": "r1",
        "text": "record 1",
        "stance": "neutral",
        "metadata_field_status": {
            "stance": {
                "status": "unresolved",
                "method": "llm",
                "confidence": None,
                "value_source": "llm",
                "verification_status": "pending_review",
                "proposed_value": "neutral",
            }
        },
    }
    manager, repo, build_id = make_manager(tmp_path, [live])
    current = repo.load_records(build_id)[0]

    candidate = dict(current)
    candidate["stance"] = "critical"
    candidate["metadata_field_status"] = {
        **dict(current.get("metadata_field_status") or {}),
        "stance": {
            "status": "unresolved",
            "method": "llm",
            "confidence": 0.4,
            "value_source": "llm",
            "verification_status": "pending_review",
            "proposed_value": "critical",
        },
    }

    result = manager._merge_enrichment_candidate(
        current,
        candidate,
        ["discourse"],
        "run-2",
        {"provider": "ollama", "model": "m"},
        manager._profile_for(build_id),
        schema=manager._schema_for(build_id),
        pass_number=2,
    )

    assert result["outcome"] == "disputed"
    assert current["stance"] == "neutral"
    dispute = current["metadata_disputes"][0]
    assert dispute["existing"] == "neutral"
    assert dispute["proposed"] == "critical"
    assert [item["value"] for item in dispute["candidates"]] == ["neutral", "critical"]
    assert dispute["candidates"][0]["source"] == "llm"
    assert dispute["candidates"][0]["verification_status"] == "pending_review"
    assert dispute["candidates"][1]["source"] == "llm"
    assert dispute["candidates"][1]["run_id"] == "run-2"
    assert dispute["candidates"][1]["pass"] == 2
    assert dispute["candidates"][1]["verification_status"] == "pending_review"
    assert dispute["candidates"][1]["confidence"] == 0.4
