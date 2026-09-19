"""Human text corrections, manifest overrides, selective reruns, and readiness.

Why: reviewers fix bad extractions and override document-level metadata per record.
Those human decisions must be remembered, must reopen acceptance when they change
reviewed content, and must survive reruns and manifest edits.
How: `install_review_build` makes a temp build containing one record built from the
given fields; LLM calls are faked where enrichment runs.
"""

from __future__ import annotations

import json
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
from app.config import APP_VERSION


def install_review_build(tmp_path: Path, record: dict):
    """Create a temp repository and build with one record (r1) built from the given fields."""
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    asset = {
        "asset_id": "asset-fox", "sha256": "sha-fox", "filename": "fox.pdf",
        "page_count": 1, "block_count": 1, "ocr_pages": 0, "warnings": [],
        "metadata": {}, "pages": [{"page": 1, "width": 612, "height": 792}],
    }
    cb._json_write(repo.asset_meta_path(asset["asset_id"]), asset)
    source_text = str(record.get("source_extracted_text") or record.get("text") or "Original extraction")
    repo.asset_blocks_path(asset["asset_id"]).write_text(
        json.dumps({
            "block_id": "b1", "page": 1, "bbox": [0, 0, 100, 100], "type": "paragraph",
            "text": source_text, "extraction_method": "native", "confidence": 1.0,
        }) + "\n", encoding="utf-8",
    )
    build = repo.create_build({
        "asset_id": asset["asset_id"], "source_sha256": asset["sha256"],
        "source_filename": asset["filename"], "source_page_count": 1, "source_block_count": 1,
        "schema_version": cb.SCHEMA_VERSION, "profile_id": cb.PROFILE_VERSION,
        "app_version": APP_VERSION, "provider": "ollama", "model": "test-model",
        "request": {"enrichment_mode": "fast", "semantic_indexing": False},
        "manifest": {}, "status": "awaiting_review", "stage": "review",
    })
    record.setdefault("record_id", "r1")
    record.setdefault("record_revision", 1)
    record.setdefault("text", source_text)
    record.setdefault("text_length", len(record["text"]))
    record.setdefault("source_asset_id", asset["asset_id"])
    record.setdefault("source_block_ids", ["b1"])
    record.setdefault("source_spans", [{"block_id": "b1", "page": 1, "confidence": 1.0}])
    record.setdefault("pdf_pages", [1])
    record.setdefault("review_disposition", "pending")
    record.setdefault("accepted", False)
    record.setdefault("rejected", False)
    record.setdefault("metadata_field_status", {})
    repo.save_records(build["build_id"], [record])
    build = repo.get_build(build["build_id"])
    build.update({"status": "awaiting_review", "stage": "review", "record_count": 1, "metadata_total": 1, "metadata_completed": 1})
    repo.save_build(build)
    return repo, build


def test_human_text_correction_preserves_immutable_extraction_and_can_resolve_source_issue(tmp_path: Path):
    """Correcting text keeps the original extraction and can clear the source issue.

    A record with a replacement character is corrected. The new text is stored, the
    original stays in source_extracted_text, status is "human_corrected", the issue moves
    to resolved_source_quality_issues, and history records the previous text's SHA-256
    and a diff. Why: the change must be auditable and reversible.
    """
    original = "A bro�ken extraction."
    record = {
        "text": original,
        "source_quality_issues": [{"code": "replacement_character", "severity": "minor", "pages": [1], "message": "Replacement character detected."}],
        "needs_review": True,
        "review_reason": "Source extraction issue: replacement_character.",
    }
    repo, build = install_review_build(tmp_path, record)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    updated = manager.patch_record_text(build["build_id"], "r1", "A broken extraction.", expected_revision=1, resolve_source_issues=True)
    assert updated["text"] == "A broken extraction."
    assert updated["source_extracted_text"] == original
    assert updated["text_review_status"] == "human_corrected"
    assert updated["source_quality_issues"] == []
    assert updated["resolved_source_quality_issues"][0]["code"] == "replacement_character"
    assert updated["text_revision_history"][-1]["previous_sha256"] == __import__("hashlib").sha256(original.encode("utf-8")).hexdigest()
    assert "-A bro�ken extraction." in updated["text_revision_history"][-1]["diff"]


def test_human_text_correction_reopens_previously_accepted_record(tmp_path: Path):
    """Editing an accepted record sends it back to pending review with a text_corrected event."""
    record = {
        "text": "Accepted text.",
        "review_disposition": "accepted",
        "accepted": True,
        "rejected": False,
        "needs_review": False,
    }
    repo, build = install_review_build(tmp_path, record)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    updated = manager.patch_record_text(build["build_id"], "r1", "Accepted text, corrected.", expected_revision=1)
    assert updated["review_disposition"] == "pending"
    assert updated["accepted"] is False
    assert updated["rejected"] is False
    assert updated["needs_review"] is True
    assert "reviewed record text changed" in updated["review_reason"].lower()
    assert updated["review_events"][-1]["event"] == "text_corrected"


def test_manifest_metadata_can_be_overridden_at_record_scope_without_future_overwrite():
    """A record-level author override survives later manifest changes.

    The manifest author is inherited first (status "inherited"); after a human override,
    changing the manifest author does not replace it.
    """
    record = {"metadata_field_status": {}, "pdf_pages": [10]}
    manifest = {"title": "Document title", "document_author": "Jacques Derrida", "main_text_start_page": 5, "main_text_end_page": 20}
    cb.PdfCorpusBuildManager._apply_manifest_metadata(record, manifest)
    assert record["document_author"] == "Jacques Derrida"
    assert record["metadata_field_status"]["document_author"]["status"] == "inherited"
    record["document_author"] = "Different record author"
    record["metadata_field_status"]["document_author"] = {"status": "human_override", "method": "human_record_override"}
    cb.PdfCorpusBuildManager._apply_manifest_metadata(record, {**manifest, "document_author": "Changed manifest author"})
    assert record["document_author"] == "Different record author"


def test_fast_enrichment_skips_unsignaled_quotation_and_indexing_but_deep_runs_all(tmp_path: Path, monkeypatch):
    """Fast mode only runs discourse when there is no quotation signal; deep runs everything.

    Fast: only the discourse family is called; quotation and indexing become "skipped".
    Deep: all three families are called, in order.
    """
    repo, build = install_review_build(tmp_path, {"text": "Derrida discusses hospitality without a direct citation."})
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    called: list[str] = []
    def fake(_request, prompt, *, response_model, max_tokens, schema_name, build_id=""):
        called.append(schema_name)
        if schema_name == "derridai_record_discourse":
            return {"metadata": {"region_type": "main_text", "primary_text": True, "discourse_role": "analysis"}, "field_evidence": {}, "review_reason": ""}
        if schema_name == "derridai_record_quotation":
            return {"metadata": {}, "field_evidence": {}, "review_reason": ""}
        return {"metadata": {"topics": ["hospitality"]}, "review_reason": ""}
    monkeypatch.setattr(manager, "_chat_json", fake)
    fast = {"record_id": "fast", "text": "Derrida discusses hospitality without citation.", "source_block_ids": ["b1"], "source_spans": [{"block_id": "b1", "page": 1, "confidence": 1.0}]}
    manager._enrich_record(fast, {}, {"provider": "ollama", "model": "test", "enrichment_mode": "fast", "semantic_indexing": False}, build_id=build["build_id"])
    assert called == ["derridai_record_discourse"]
    assert fast["metadata_stage_status"]["quotation"] == "skipped"
    assert fast["metadata_stage_status"]["indexing"] == "skipped"
    called.clear()
    deep = {"record_id": "deep", "text": "Derrida discusses hospitality.", "source_block_ids": ["b1"], "source_spans": [{"block_id": "b1", "page": 1, "confidence": 1.0}]}
    manager._enrich_record(deep, {}, {"provider": "ollama", "model": "test", "enrichment_mode": "deep"}, build_id=build["build_id"])
    assert called == ["derridai_record_discourse", "derridai_record_quotation", "derridai_record_indexing"]


def test_source_problem_is_not_mislabeled_as_topology():
    """A source-extraction problem is a "source" issue, not a "topology" one."""
    record = {"source_quality_issues": [{"code": "replacement_character", "severity": "minor"}], "review_reason": "Source extraction issue: replacement_character."}
    codes = cb.PdfCorpusBuildManager._review_issue_codes(record)
    assert "source" in codes
    assert "topology" not in codes




def test_selective_metadata_rerun_preserves_human_values_and_other_family_state(tmp_path: Path, monkeypatch):
    """Rerunning only the discourse family keeps human values and other families' results.

    The model proposes a different speaker, but the human-confirmed one is kept; only
    discourse is called; quotation and indexing stay "complete".
    """
    record = {
        "text": "Derrida discusses hospitality.",
        "speaker": "Human reviewer",
        "metadata_field_status": {"speaker": {"status": "human_confirmed", "method": "human"}},
        "metadata_stage_status": {"discourse": "complete", "quotation": "complete", "indexing": "complete"},
        "metadata_execution_ledger": {
            "discourse": {"state": "complete"}, "quotation": {"state": "complete"}, "indexing": {"state": "complete"},
        },
    }
    repo, build = install_review_build(tmp_path, record)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    called: list[str] = []
    def fake(_request, prompt, *, response_model, max_tokens, schema_name, build_id=""):
        called.append(schema_name)
        return {
            "metadata": {"speaker": "Model speaker", "region_type": "main_text", "primary_text": True, "discourse_role": "analysis"},
            "field_evidence": {}, "review_reason": "",
        }
    monkeypatch.setattr(manager, "_chat_json", fake)
    updated = manager.rerun_metadata(build["build_id"], "r1", {
        "provider": "ollama", "model": "test", "enrichment_mode": "fast", "families": ["discourse"],
    })
    assert called == ["derridai_record_discourse"]
    assert updated["speaker"] == "Human reviewer"
    assert updated["metadata_field_status"]["speaker"]["status"] == "human_confirmed"
    assert updated["metadata_stage_status"]["quotation"] == "complete"
    assert updated["metadata_stage_status"]["indexing"] == "complete"


def test_document_manifest_refresh_preserves_explicit_record_override(tmp_path: Path):
    """Editing the document manifest does not overwrite a record-level human override."""
    record = {
        "text": "Primary text.",
        "document_author": "Section author",
        "metadata_field_status": {"document_author": {"status": "human_override", "method": "human_record_override"}},
    }
    repo, build = install_review_build(tmp_path, record)
    build = repo.get_build(build["build_id"])
    build["manifest"] = {"title": "Book", "document_author": "Book author"}
    build["manifest_revision"] = 1
    repo.save_build(build)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    manager.patch_manifest(build["build_id"], {"document_author": "Changed book author"}, expected_revision=1)
    updated = repo.load_records(build["build_id"])[0]
    assert updated["document_author"] == "Section author"
    assert updated["metadata_field_status"]["document_author"]["status"] == "human_override"


def test_resolved_record_source_issue_unblocks_raw_page_quality_for_publication_readiness():
    """Raw page-quality warnings block publishing only while record-level issues remain.

    With no open source problems the build is publishable; with one open source problem a
    "source_quality" blocker appears.
    """
    build = {
        "record_count": 1, "accepted_count": 1, "rejected_count": 0, "needs_review_count": 0,
        "metadata_total": 1, "metadata_completed": 1, "metadata_issue_summary": {"fields_unresolved": 0, "records_incomplete": 0},
        "boundary_review_count": 0, "validation": {"valid": True, "source_valid": True, "metadata_valid": True},
        "source_quality": {"blocking_page_count": 1, "blocking_pages": [1]},
        "manifest": {"title": "Test Book", "document_author": "Test Author"},
        "source_problem_count": 0, "status": "awaiting_review", "stage": "review", "profile_id": cb.PROFILE_VERSION,
    }
    cb.PdfCorpusBuildManager._refresh_workflow_fields(build)
    assert build["publication_readiness"]["can_publish"] is True
    assert not any(item["code"] == "source_quality" for item in build["publication_readiness"]["blockers"])
    build["source_problem_count"] = 1
    cb.PdfCorpusBuildManager._refresh_workflow_fields(build)
    assert any(item["code"] == "source_quality" for item in build["publication_readiness"]["blockers"])
