"""Reviewer self-consistency: some decisions are asked again, blind, later."""

from __future__ import annotations

import sys
import types
from pathlib import Path

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules["chromadb"] = types.SimpleNamespace()

from app import corpus_builder as cb
from app.config import APP_VERSION
from app.enrichment_metrics import compute


def setup(tmp_path: Path, rate: float):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = repo.create_build({
        "asset_id": "a", "source_sha256": "x", "source_filename": "x.pdf", "source_page_count": 1, "source_block_count": 2,
        "schema_version": cb.SCHEMA_VERSION, "profile_id": cb.PROFILE_VERSION, "profile_version": 11, "app_version": APP_VERSION,
        "provider": "ollama", "model": "m", "request": {"recheck_rate": rate},
    })
    build.update(status="awaiting_review", stage="review")
    repo.save_build(build)
    repo.save_records(build["build_id"], [{"record_id": f"rec-{i}", "text": "t", "metadata_field_status": {}} for i in range(12)])
    manager = cb.PdfCorpusBuildManager(repo)
    manager._rewrite_and_validate = lambda bid, records: (repo.save_records(bid, records), repo.get_build(bid))[1]
    manager._rewrite_targeted_record = lambda bid, record, previous: (repo.update_record(bid, record), repo.get_build(bid))[1]
    manager._assert_human_review_available = lambda *a, **k: None
    manager._push_review_history = lambda *a, **k: None
    return manager, repo, build["build_id"]


def test_a_decision_is_reopened_blind_after_enough_others_then_scored(tmp_path):
    m, repo, bid = setup(tmp_path, 1.0)
    m.patch_metadata(bid, "rec-0", {"discourse_role": "assertion"})
    for i in range(1, 10):  # nine other decisions pass; the spacing is eight
        m.patch_metadata(bid, f"rec-{i}", {"discourse_role": "critique"})
    reopened = next(r for r in repo.load_records(bid) if r["record_id"] == "rec-0")
    status = reopened["metadata_field_status"]["discourse_role"]
    assert status["recheck"] is True and reopened["discourse_role"] is None
    assert "assertion" not in str(reopened)  # the earlier answer is not in what the browser gets
    answered = m.patch_metadata(bid, "rec-0", {"discourse_role": "assertion"})
    assert answered["recheck_results"]["discourse_role"] == {"first": "assertion", "second": "assertion", "agreed": True}
    assert answered["metadata_field_status"]["discourse_role"]["status"] == "human_confirmed"
    stats = compute(m._ledger.events())["self_consistency"]
    assert stats["n"] == 1 and stats["rate"] == 1.0


def test_changing_your_answer_on_a_recheck_is_logged_as_a_disagreement(tmp_path):
    m, repo, bid = setup(tmp_path, 1.0)
    m.patch_metadata(bid, "rec-0", {"discourse_role": "assertion"})
    for i in range(1, 10):
        m.patch_metadata(bid, f"rec-{i}", {"discourse_role": "critique"})
    m.patch_metadata(bid, "rec-0", {"discourse_role": "question"})
    row = next(e for e in m._ledger.events() if e["kind"] == "recheck")
    assert row["agreed"] is False and row["severity"] == "substantive"


def test_no_rechecks_when_the_rate_is_zero(tmp_path):
    m, repo, bid = setup(tmp_path, 0.0)
    for i in range(12):
        m.patch_metadata(bid, f"rec-{i}", {"discourse_role": "critique"})
    assert not any(e["kind"] in {"recheck", "recheck_seal"} for e in m._ledger.events())
