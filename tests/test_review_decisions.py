# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Review workflow: atomic decisions, blockers, and filters.

Why: reviewers accept or reject records one at a time. A decision must be applied
atomically (and tell the UI which record comes next), blocked with a structured
reason when metadata is incomplete, and source problems must be filterable.
How: `install_repo` builds a temp repository with the given record dicts and
`rec` creates a minimal valid record (optionally with a metadata or source blocker).
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app import corpus_builder as cb
from app import corpus_review_actions as review_actions


def install_repo(tmp_path: Path, records: list[dict]):
    """Create a temp repository and build containing the supplied records."""
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    cb._json_write(repo.asset_meta_path("a"), {
        "asset_id": "a", "sha256": "x", "filename": "x.pdf", "page_count": 1,
        "block_count": len(records), "ocr_pages": 0, "warnings": [], "metadata": {}, "pages": [],
    })
    with repo.asset_blocks_path("a").open("w", encoding="utf-8") as handle:
        for i, _record in enumerate(records, 1):
            handle.write(json.dumps({"block_id": f"b{i}", "page": 1, "bbox": [0,0,1,1], "type": "paragraph", "text": f"text {i}", "extraction_method": "native", "confidence": 1.0}) + "\n")
    build = repo.create_build({
        "asset_id":"a","source_sha256":"x","source_filename":"x.pdf","source_page_count":1,
        "source_block_count":len(records),"schema_version":cb.SCHEMA_VERSION,"profile_id":cb.PROFILE_VERSION,
        "profile_version":int(cb.CORPUS_PROFILES[cb.PROFILE_VERSION]["version"]),"provider":"ollama","model":"test",
        "request":{},"manifest":{},"validation":{"valid":True,"source_valid":True,"metadata_valid":True,"coverage":1.0},
    })
    repo.save_records(build["build_id"], records)
    return repo, build


def rec(rid: str, bid: str, *, blocked=False, source_problem=False):
    """Build a minimal record; blocked=True leaves primary_text unresolved, source_problem=True adds a blocking source-quality issue."""
    return {
        "record_id":rid,"record_revision":1,"text":"text","text_length":4,"source_block_ids":[bid],
        "source_spans":[{"block_id":bid,"page":1}],"metadata_incomplete_fields":["primary_text"] if blocked else [],
        "metadata_review_fields":[],"metadata_field_status":{},"metadata_complete":not blocked,"primary_text":None if blocked else True,
        "region_type":"main_text","discourse_role":"analysis","review_disposition":"pending","accepted":False,"rejected":False,
        "needs_review":False,"source_quality_issues":[{"code":"source_quality_blocking","pages":[1]}] if source_problem else [],
    }


def test_review_decision_is_atomic_and_returns_next(tmp_path: Path):
    """Accepting r1 succeeds, updates counts, and returns r2 as the next record."""
    repo, build = install_repo(tmp_path, [rec("r1","b1"), rec("r2","b2")])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    result = manager.review_decision(build["build_id"], "r1", "accepted", expected_revision=1)
    assert result["applied"] is True
    assert result["record"]["accepted"] is True
    assert result["next_record"]["record_id"] == "r2"
    assert result["build"]["accepted_count"] == 1
    assert result["build"]["publication_readiness"]["records_pending"] == 1


def test_text_save_returns_its_committed_payload_and_operational_version(tmp_path, monkeypatch):
    repo, build = install_repo(tmp_path, [rec("r1", "b1")])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    build_id = build["build_id"]
    try:
        result = manager.patch_record_text(build_id, "r1", "Reviewed correction.", expected_revision=1)
        stored = repo.get_record(build_id, "r1", include_queue_version=True)
        assert result["queue_state_version"] == stored["queue_state_version"]
        assert result["text"] == stored["text"] == "Reviewed correction."
        assert result["record_revision"] == stored["record_revision"] == 2
        assert "queue_state_version" not in repo.get_record(build_id, "r1")

        def later_write(_build_id):
            monkeypatch.setattr(repo, "_metadata_projection_callback", None)
            current = repo.get_record(build_id, "r1")
            current["operational_test_marker"] = "later completion"
            repo.update_record(build_id, current)

        monkeypatch.setattr(repo, "_metadata_projection_callback", later_write)
        saved = repo.update_record(build_id, {**stored, "text": "Second correction."})
        newer = repo.get_record(build_id, "r1", include_queue_version=True)
        assert saved["text"] == newer["text"] == "Second correction."
        assert saved["queue_state_version"] < newer["queue_state_version"]
        assert "operational_test_marker" not in saved
        assert newer["operational_test_marker"] == "later completion"
        repo.refresh_records_projection(build_id)
        assert "queue_state_version" not in json.loads(
            repo.build_records_path(build_id).read_text().splitlines()[0]
        )
    finally:
        manager._executor.shutdown(wait=True)


@pytest.mark.parametrize("absent", [False, True])
def test_metadata_decision_returns_current_operational_version(tmp_path, absent):
    repo, build = install_repo(tmp_path, [rec("r1", "b1", blocked=True)])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    try:
        result = manager.metadata_decision(
            build["build_id"], "r1", "primary_text", True,
            expected_revision=1, confirm_no_supported_value=absent,
        )
        stored = repo.get_record(build["build_id"], "r1", include_queue_version=True)
        assert result["record"]["queue_state_version"] == stored["queue_state_version"]
        assert result["record"]["record_revision"] == stored["record_revision"]
        assert result["record"]["primary_text"] == stored["primary_text"]
    finally:
        manager._executor.shutdown(wait=True)


def test_set_disposition_persists_promoted_metadata_memory(tmp_path: Path, monkeypatch):
    """Legacy acceptance must feed the same durable metadata-memory path as Accept & next."""

    record = rec("r1", "b1")
    record["metadata_field_status"]["discourse_role"] = {
        "status": "model_inferred",
        "method": "llm",
        "confidence": 0.9,
    }
    repo, build = install_repo(tmp_path, [record])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    persisted: list[tuple[str, str, object]] = []
    scheduled: list[str] = []
    monkeypatch.setattr(
        review_actions,
        "persist_record_decision",
        lambda **kwargs: persisted.append(
            (
                str(kwargs["record"].get("record_id") or ""),
                str(kwargs["field_name"]),
                kwargs["value"],
            )
        ),
    )
    monkeypatch.setattr(
        manager,
        "_schedule_metadata_exemplar_projection",
        lambda build_id: scheduled.append(build_id),
    )

    result = manager.set_disposition(
        build["build_id"],
        "r1",
        "accepted",
        expected_revision=1,
    )

    assert result["metadata_field_status"]["discourse_role"]["status"] == "human_confirmed"
    assert persisted == [("r1", "discourse_role", "analysis")]
    assert scheduled == [build["build_id"]]


def test_human_evidence_edit_reprojects_trusted_metadata_memory(tmp_path: Path, monkeypatch):
    """Adding reviewed evidence can make a human-confirmed field exemplar-eligible."""

    record = rec("r1", "b1")
    record["metadata_field_status"]["discourse_role"] = {
        "status": "human_confirmed",
        "method": "human",
        "confidence": 1.0,
    }
    repo, build = install_repo(tmp_path, [record])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    persisted: list[tuple[str, str, object]] = []
    scheduled: list[str] = []
    monkeypatch.setattr(
        review_actions,
        "persist_record_decision",
        lambda **kwargs: persisted.append(
            (
                str(kwargs["record"].get("record_id") or ""),
                str(kwargs["field_name"]),
                kwargs["value"],
            )
        ),
    )
    monkeypatch.setattr(
        manager,
        "_schedule_metadata_exemplar_projection",
        lambda build_id: scheduled.append(build_id),
    )

    result = manager.patch_evidence(
        build["build_id"],
        "r1",
        "discourse_role",
        ["b1"],
        expected_revision=1,
    )

    assert result["metadata_evidence"]["discourse_role"]["reviewed_by"] == "human"
    assert persisted == [("r1", "discourse_role", "analysis")]
    assert scheduled == [build["build_id"]]


def test_human_evidence_edit_persists_confirmed_absence_as_absence_binding(tmp_path: Path, monkeypatch):
    """Evidence-bound no-value decisions remain absence audit events, not null positives."""

    record = rec("r1", "b1")
    record["position_holder"] = None
    record["metadata_field_status"]["position_holder"] = {
        "status": "confirmed_absent",
        "method": "human",
        "confidence": 1.0,
    }
    repo, build = install_repo(tmp_path, [record])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    persisted: list[tuple[str, str, object, str]] = []
    scheduled: list[str] = []
    monkeypatch.setattr(
        review_actions,
        "persist_record_decision",
        lambda **kwargs: persisted.append(
            (
                str(kwargs["record"].get("record_id") or ""),
                str(kwargs["field_name"]),
                kwargs["value"],
                str(kwargs["decision_kind"]),
            )
        ),
    )
    monkeypatch.setattr(
        manager,
        "_schedule_metadata_exemplar_projection",
        lambda build_id: scheduled.append(build_id),
    )

    result = manager.patch_evidence(
        build["build_id"],
        "r1",
        "position_holder",
        ["b1"],
        expected_revision=1,
    )

    assert result["metadata_field_status"]["position_holder"]["status"] == "confirmed_absent"
    assert persisted == [("r1", "position_holder", None, "absence")]
    assert scheduled == [build["build_id"]]


def test_human_value_change_invalidates_evidence_for_previous_assertion(tmp_path: Path, monkeypatch):
    record = rec("r1", "b1")
    record["position_holder"] = "Levinas"
    record["metadata_field_status"]["position_holder"] = {
        "status": "human_confirmed",
        "method": "human",
        "confidence": 1.0,
    }
    record["metadata_evidence"] = {
        "position_holder": {
            "block_ids": ["b1"],
            "reviewed_by": "human",
            "reviewed_at": "2026-09-24T00:00:00Z",
        }
    }
    repo, build = install_repo(tmp_path, [record])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    monkeypatch.setattr(review_actions, "persist_record_decision", lambda **kwargs: None)
    monkeypatch.setattr(manager, "_schedule_metadata_exemplar_projection", lambda build_id: None)

    updated = manager.patch_metadata(
        build["build_id"],
        "r1",
        {"position_holder": "Derrida"},
        expected_revision=1,
    )

    assert updated["position_holder"] == "Derrida"
    assert "position_holder" not in (updated.get("metadata_evidence") or {})


def test_confirmed_absence_invalidates_evidence_for_previous_value(tmp_path: Path, monkeypatch):
    record = rec("r1", "b1")
    record["position_holder"] = "Levinas"
    record["metadata_field_status"]["position_holder"] = {
        "status": "human_confirmed",
        "method": "human",
        "confidence": 1.0,
    }
    record["metadata_evidence"] = {
        "position_holder": {
            "block_ids": ["b1"],
            "reviewed_by": "human",
            "reviewed_at": "2026-09-24T00:00:00Z",
        }
    }
    repo, build = install_repo(tmp_path, [record])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    monkeypatch.setattr(review_actions, "persist_record_decision", lambda **kwargs: None)
    monkeypatch.setattr(manager, "_schedule_metadata_exemplar_projection", lambda build_id: None)

    updated = manager.metadata_decision(
        build["build_id"],
        "r1",
        "position_holder",
        None,
        expected_revision=1,
        confirm_no_supported_value=True,
    )["record"]

    assert updated["metadata_field_status"]["position_holder"]["status"] == "confirmed_absent"
    assert "position_holder" not in (updated.get("metadata_evidence") or {})


def test_review_decision_returns_structured_metadata_blocker(tmp_path: Path):
    """Accepting a record with unresolved required metadata is refused with details.

    Expect applied False, blocked True, blocker "metadata_decision_required", and the
    blocking field list (["primary_text"]) so the UI can point the reviewer at it.
    """
    repo, build = install_repo(tmp_path, [rec("r1","b1",blocked=True)])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    result = manager.review_decision(build["build_id"], "r1", "accepted", expected_revision=1)
    assert result["applied"] is False
    assert result["blocked"] is True
    assert result["blocker"] == "metadata_decision_required"
    assert result["blocking_fields"] == ["primary_text"]


def test_empty_metadata_issue_summary_is_authoritative(tmp_path: Path):
    """With no incomplete fields, validation reports zero unresolved and no metadata blocker.

    Why: an empty issue list must mean "complete", not fall back to a stale count.
    """
    repo, build = install_repo(tmp_path, [rec("r1","b1")])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    refreshed = manager._rewrite_and_validate(build["build_id"], repo.load_records(build["build_id"]))
    assert refreshed["metadata_issue_summary"]["fields_unresolved"] == 0
    assert refreshed["metadata_completed"] == 1
    assert not any(b["code"] == "required_metadata" for b in refreshed["publication_readiness"]["blockers"])


def test_source_problem_filter_is_first_class(tmp_path: Path):
    """page_records(source_problem=True) returns only records with source-quality issues."""
    repo, build = install_repo(tmp_path, [rec("r1","b1",source_problem=True), rec("r2","b2")])
    page = repo.page_records(build["build_id"], source_problem=True)
    assert page["total"] == 1
    assert page["items"][0]["record_id"] == "r1"


def test_fragmented_glyph_record_is_detected():
    """Text broken into single glyphs is flagged "fragmented_glyph_layout".

    Why: this is a bad text layer (valid Unicode but unusable), so it should go to the
    source-problem queue instead of looking ready for acceptance.
    """
    record={"text":"OFF\n:\n=\n*\n?\n;\ni\n2\nA\nl\n©\nCosmopolitanism and Forgiveness","pdf_pages":[1]}
    issues=cb._record_extraction_quality_issues(record)
    assert issues and issues[0]["code"]=="fragmented_glyph_layout"





def _evidence_fixture(tmp_path, monkeypatch):
    record = rec("r1", "b1")
    record["discourse_role"] = "analysis"
    record["metadata_field_status"] = {
        "discourse_role": {"status": "human_confirmed", "method": "human", "confidence": 1.0},
    }
    repo, build = install_repo(tmp_path, [record, rec("r2", "b2")])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    monkeypatch.setattr(review_actions, "persist_record_decision", lambda **kwargs: None)
    monkeypatch.setattr(manager, "_schedule_metadata_exemplar_projection", lambda build_id: None)
    return manager, build


def test_reviewer_knowledge_is_recorded_as_such_without_a_span(tmp_path, monkeypatch):
    manager, build = _evidence_fixture(tmp_path, monkeypatch)
    result = manager.patch_evidence(
        build["build_id"], "r1", "discourse_role", [],
        reason="Known from the critical edition's apparatus.", expected_revision=1,
        source_kind="reviewer_knowledge",
    )
    entry = result["metadata_evidence"]["discourse_role"]
    assert entry["source_kind"] == "reviewer_knowledge" and entry["block_ids"] == []
    assert entry["reviewed_by"] == "human"


def test_external_evidence_must_come_from_the_builds_own_source(tmp_path, monkeypatch):
    import pytest

    manager, build = _evidence_fixture(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        manager.patch_evidence(build["build_id"], "r1", "discourse_role", [], expected_revision=1,
                               external_block_ids=["not-in-source"])
    result = manager.patch_evidence(build["build_id"], "r1", "discourse_role", ["b1"], expected_revision=1,
                                    external_block_ids=["b2"])
    entry = result["metadata_evidence"]["discourse_role"]
    assert entry["block_ids"] == ["b1"] and entry["external_block_ids"] == ["b2"]


def test_review_decision_and_record_view_never_touch_the_whole_corpus(tmp_path: Path, monkeypatch):
    """Latency contract: decisions write one row; compatibility views do not write.

    Whole-corpus snapshots, validation and rewrites made every Accept click and every Record open
    scale with corpus size (and kept up to 40 full-corpus undo copies).
    """
    repo, build = install_repo(tmp_path, [rec(f"r{i}", f"b{i}") for i in range(1, 6)])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    bid = build["build_id"]

    repo.page_records(bid)  # projected pages do not require a full-corpus snapshot

    def forbidden(*_args, **_kwargs):
        raise AssertionError("whole-corpus operation on an interactive review path")

    monkeypatch.setattr(repo, "save_records", forbidden)
    monkeypatch.setattr(repo, "load_records", forbidden)
    monkeypatch.setattr(manager, "_rewrite_and_validate", forbidden)

    viewed = manager.record_view(bid, "r2")
    assert viewed["activity"] == {}
    assert "activity" not in repo.get_record(bid, "r2")

    result = manager.review_decision(bid, "r1", "accepted", expected_revision=1, review_queue="all")
    assert result["applied"] is True and result["record"]["record_id"] == "r1"
    assert result["next_record"]["record_id"] == "r2"
    assert result["queue_counts"]["accepted"] == 1
    assert repo.get_record(bid, "r1")["review_disposition"] == "accepted"
    assert repo.get_record(bid, "r2")["review_disposition"] == "pending"

    # History is record-local (the previous Record only), not a corpus snapshot, and still undoes.
    undo = repo.load_checkpoint(bid, "review_history", {})["undo"]
    assert undo[-1]["record_id"] == "r1" and "records" not in undo[-1]
    # Projected pages reflect the write without a canonical corpus reparse.
    assert [r["review_disposition"] for r in repo.page_records(bid)["items"]][:2] == ["accepted", "pending"]


def test_deprecated_record_view_preserves_history_without_mutation(tmp_path: Path, monkeypatch):
    import pytest

    record = rec("r1", "b1")
    record["activity"] = {"human_view_count": 7, "last_human_viewed_at": "2026-09-01"}
    record["human_view_count"] = 7
    repo, build = install_repo(tmp_path, [record])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    bid = build["build_id"]
    before = repo.get_record(bid, "r1")

    def forbidden(*_args, **_kwargs):
        raise AssertionError("navigation must not mutate canonical Records")

    monkeypatch.setattr(repo, "update_record", forbidden)
    monkeypatch.setattr(repo, "save_records", forbidden)
    monkeypatch.setattr(manager, "_schedule_metadata_exemplar_projection", forbidden)
    for _ in range(2):
        assert manager.record_view(bid, "r1") == {"record_id": "r1", "activity": record["activity"]}
    assert repo.get_record(bid, "r1") == before
    with pytest.raises(KeyError):
        manager.record_view(bid, "missing")


def test_reading_a_legacy_asset_infers_the_start_once_without_recursing(tmp_path: Path, monkeypatch):
    """An asset stored before `main_text_start_inference` existed gets it on first read and keeps it.

    `get_asset` -> inference -> `load_blocks` -> `get_asset` used to recurse to the interpreter's
    limit, swallow the RecursionError and never persist, so every read (including every review
    click) repeated the work and its fsyncs.
    """
    repo, _build = install_repo(tmp_path, [rec("r1", "b1")])
    reads = {"count": 0}
    original = repo._load_block_rows

    def counted(asset_id: str):
        reads["count"] += 1
        return original(asset_id)

    monkeypatch.setattr(repo, "_load_block_rows", counted)
    first = repo.get_asset("a")
    assert "main_text_start_inference" in first
    assert reads["count"] <= 2  # one for quality scoring, one for inference: never a recursion
    reads["count"] = 0
    repo.get_asset("a")
    repo.load_blocks("a")
    assert reads["count"] <= 1  # persisted: only load_blocks' own read remains
