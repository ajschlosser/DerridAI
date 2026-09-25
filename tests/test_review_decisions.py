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



