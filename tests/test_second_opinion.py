"""Reviewer identity and second opinions (inter-annotator agreement)."""

from __future__ import annotations

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
from app.enrichment_metrics import compute
from app.reviewer_context import current_reviewer


def setup(tmp_path: Path, **experiment):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = repo.create_build({
        "asset_id": "a", "source_sha256": "x", "source_filename": "x.pdf", "source_page_count": 1, "source_block_count": 2,
        "schema_version": cb.SCHEMA_VERSION, "profile_id": cb.PROFILE_VERSION, "profile_version": 11, "app_version": APP_VERSION,
        "provider": "ollama", "model": "m", "request": experiment,
    })
    build.update(status="awaiting_review", stage="review")
    repo.save_build(build)
    repo.save_records(build["build_id"], [{"record_id": f"rec-{i}", "text": f"text {i}", "metadata_field_status": {}} for i in range(3)])
    manager = cb.PdfCorpusBuildManager(repo)
    manager._rewrite_and_validate = lambda bid, records: (repo.save_records(bid, records), repo.get_build(bid))[1]
    manager._rewrite_targeted_record = lambda bid, record, previous: (repo.update_record(bid, record), repo.get_build(bid))[1]
    manager._assert_human_review_available = lambda *a, **k: None
    manager._push_review_history = lambda *a, **k: None
    return manager, repo, build["build_id"]


def as_user(name):
    return current_reviewer.set(name)


def test_human_events_carry_the_reviewer_and_background_events_do_not(tmp_path):
    m, repo, bid = setup(tmp_path)
    token = as_user("user-1")
    m.patch_metadata(bid, "rec-0", {"discourse_role": "assertion"})
    m._ledger.append("proposed", model="q", field="f")
    current_reviewer.reset(token)
    m._ledger.append("accepted", model="q", field="f")
    rows = {e["kind"]: e.get("reviewer") for e in m._ledger.events()}
    assert rows["proposed"] is None and rows["accepted"] == ""


def test_a_second_reviewer_labels_blind_and_agreement_is_scored(tmp_path):
    m, repo, bid = setup(tmp_path, iaa_rate=1.0)
    t = as_user("user-1")
    m.patch_metadata(bid, "rec-0", {"discourse_role": "assertion"})
    m.patch_metadata(bid, "rec-1", {"discourse_role": "critique"})
    assert m.pending_second_opinions(bid) == []  # the first reviewer is never asked to second-guess themselves
    current_reviewer.reset(t)
    t = as_user("user-2")
    pending = m.pending_second_opinions(bid)
    assert {p["record_id"] for p in pending} == {"rec-0", "rec-1"} and all("value" not in p for p in pending)
    m.submit_second_opinion(bid, "rec-0", "discourse_role", "assertion")
    m.submit_second_opinion(bid, "rec-1", "discourse_role", "question")
    assert m.pending_second_opinions(bid) == []
    with pytest.raises(ValueError):
        m.submit_second_opinion(bid, "rec-0", "discourse_role", "assertion")  # already given
    stats = compute(m._ledger.events())["inter_annotator"]
    assert stats["n"] == 2 and stats["rate"] == 0.5
    disagreement = next(e for e in m._ledger.events() if e["kind"] == "second_label" and not e["agreed"])
    assert disagreement["first_reviewer"] == "user-1" and disagreement["reviewer"] == "user-2"
    current_reviewer.reset(t)


def test_no_second_opinions_when_the_rate_is_zero_or_nobody_is_identified(tmp_path):
    m, repo, bid = setup(tmp_path, iaa_rate=0.0)
    t = as_user("user-1")
    m.patch_metadata(bid, "rec-0", {"discourse_role": "assertion"})
    current_reviewer.reset(t)
    t = as_user("user-2")
    assert m.pending_second_opinions(bid) == []
    current_reviewer.reset(t)


def test_self_consistency_counts_only_the_same_reviewer():
    rows = [
        {"kind": "recheck", "field": "f", "agreed": True, "same_reviewer": True, "value": "a", "new_value": "a"},
        {"kind": "recheck", "field": "f", "agreed": False, "same_reviewer": False, "value": "a", "new_value": "b"},
    ]
    out = compute(rows)
    assert out["self_consistency"]["n"] == 1 and out["inter_annotator"]["n"] == 1


def test_the_second_reviewer_never_sees_the_first_answer_and_cannot_overwrite_it(tmp_path):
    m, repo, bid = setup(tmp_path, iaa_rate=1.0)
    t = as_user("user-1")
    m.patch_metadata(bid, "rec-0", {"discourse_role": "assertion"})
    current_reviewer.reset(t)
    t = as_user("user-2")
    served = repo.page_records(bid, offset=0, limit=10)["items"]
    row = next(r for r in served if r["record_id"] == "rec-0")
    assert row["discourse_role"] is None and row["metadata_field_status"]["discourse_role"]["blind"] is True
    assert "assertion" not in str(row)
    # Answering through the ordinary editor is the second opinion: the stored answer is unchanged.
    shown = m.patch_metadata(bid, "rec-0", {"discourse_role": "critique"})
    stored = next(r for r in repo.load_records(bid) if r["record_id"] == "rec-0")
    assert stored["discourse_role"] == "assertion" and shown["discourse_role"] == "assertion"  # revealed once given
    label = next(e for e in m._ledger.events() if e["kind"] == "second_label")
    assert label["agreed"] is False and label["value"] == "assertion" and label["new_value"] == "critique"
    current_reviewer.reset(t)
