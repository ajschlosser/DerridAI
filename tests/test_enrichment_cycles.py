"""Multi-pass metadata enrichment: conflict rules, learning, and safe concurrency.

Why: enrichment passes may be chained while a reviewer keeps working. Human
edits must never be lost, disagreements must be decided only when the model is
confident, and what reviewers teach one pass must reach the next.
How: `resolve_conflict` and `learn_from_review` are pure; the manager tests
stub `_enrich_record` (no provider) and run the worker inline.
"""

from __future__ import annotations

from pathlib import Path
import sys
import types

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules["chromadb"] = types.SimpleNamespace()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
from app import corpus_builder as cb
from app import enrichment_cycles as ec
from app.config import APP_VERSION


class InlineExecutor:
    """Runs submitted work immediately so worker behavior is deterministic."""

    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)


def make_manager(tmp_path: Path, rows: list[dict]):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = repo.create_build({
        "asset_id": "a", "source_sha256": "x", "source_filename": "x.pdf", "source_page_count": 1,
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
    # Whole-build validation needs the real source asset; it is not under test here.
    manager._rewrite_and_validate = lambda build_id, records: repo.get_build(build_id)
    return manager, repo, build["build_id"]


def proposal(record: dict, **fields) -> dict:
    """What a pass returns: the record with new values and per-field confidence."""
    out = dict(record)
    status = dict(out.get("metadata_field_status") or {})
    for field, (value, confidence) in fields.items():
        out[field] = value
        status[field] = {"status": "llm_inferred", "method": "llm", "confidence": confidence}
    out["metadata_field_status"] = status
    return out


def test_resolve_conflict_decides_only_when_confidence_separates():
    """Human wins; a confident, clearly better proposal replaces; ties keep both."""
    human = {"status": "human_confirmed", "confidence": 0.2}
    assert ec.resolve_conflict(human, {"confidence": 0.99}) == "keep_existing"
    weak_old = {"status": "llm_inferred", "confidence": 0.6}
    assert ec.resolve_conflict(weak_old, {"confidence": 0.9}) == "replace"
    assert ec.resolve_conflict({"status": "llm_inferred", "confidence": 0.85}, {"confidence": 0.8}) == "keep_both"
    assert ec.resolve_conflict({"status": "llm_inferred", "confidence": 0.9}, {"confidence": 0.5}) == "keep_existing"
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


def test_chain_replaces_confidently_keeps_both_when_unsure_and_stops_when_converged(tmp_path: Path):
    """Pass 1 decides confident conflicts; pass 2 sees nothing new and ends the chain."""
    rows = [
        {"stance": "neutral", "metadata_field_status": {"stance": {"status": "llm_inferred", "confidence": 0.5}}},
        {"stance": "neutral", "metadata_field_status": {"stance": {"status": "llm_inferred", "confidence": 0.8}}},
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
