"""Saving document metadata: when it is allowed, and what it reopens.

Why: a save was refused during a multi-pass enrichment run, and every save reopened every record even
when nothing that record inherits had changed.
How: a temporary repository with a few records; whole-build validation needs a real source asset, so it
is stubbed here.
"""

from __future__ import annotations

from pathlib import Path
import sys
import types

import pytest

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules["chromadb"] = types.SimpleNamespace()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
from app import corpus_builder as cb
from app.config import APP_VERSION


def make(tmp_path: Path, *, status: str = "awaiting_review", stage: str = "review"):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = repo.create_build({
        "asset_id": "a", "source_sha256": "x", "source_filename": "x.pdf", "source_page_count": 1, "source_block_count": 2,
        "schema_version": cb.SCHEMA_VERSION, "profile_id": cb.PROFILE_VERSION, "profile_version": 11, "app_version": APP_VERSION,
        "provider": "ollama", "model": "m", "request": {}, "manifest": {"title": "Book", "document_author": "Derrida"},
    })
    build.update(manifest_revision=1)
    repo.save_build(build)
    rows = [
        {"record_id": f"r{i}", "text": f"text {i}", "accepted": True, "review_disposition": "accepted", "metadata_field_status": {}}
        for i in (1, 2)
    ]
    repo.save_records(build["build_id"], rows)
    manager = cb.PdfCorpusBuildManager(repo)
    # Set the state after the manager exists: constructing it marks any "running" build as interrupted.
    build = repo.get_build(build["build_id"])
    build.update(status=status, stage=stage)
    repo.save_build(build)
    manager._rewrite_and_validate = lambda build_id, records: (repo.save_records(build_id, records), repo.get_build(build_id))[1]
    return manager, repo, build["build_id"]


def test_a_save_is_allowed_while_a_multi_pass_run_is_working(tmp_path: Path):
    manager, repo, build_id = make(tmp_path, status="running", stage="metadata_enrichment_rerun")
    build = manager.patch_manifest(build_id, {"publisher": "Stanford University Press"})
    assert build["manifest"]["publisher"] == "Stanford University Press"


def test_the_main_text_bounds_still_wait_for_a_run_to_stop(tmp_path: Path):
    manager, _, build_id = make(tmp_path, status="running", stage="metadata_enrichment_rerun")
    with pytest.raises(ValueError, match="structural"):
        manager.patch_manifest(build_id, {"main_text_start_page": 18})


def test_other_running_stages_still_refuse_a_save(tmp_path: Path):
    manager, _, build_id = make(tmp_path, status="running", stage="segmenting")
    with pytest.raises(ValueError, match="segmentation is complete"):
        manager.patch_manifest(build_id, {"publisher": "X"})


def test_only_records_whose_inherited_values_changed_are_reopened(tmp_path: Path):
    manager, repo, build_id = make(tmp_path)
    manager.patch_manifest(build_id, {"publisher": "First Press"})
    rows = {row["record_id"]: row for row in repo.load_records(build_id)}
    assert all(row["accepted"] is False and row["needs_review"] for row in rows.values()), "an inherited value changed"
    for row in rows.values():
        row.update(accepted=True, needs_review=False, review_disposition="accepted")
    repo.save_records(build_id, list(rows.values()))
    # Saving the same publisher again changes nothing any record inherits.
    manager.patch_manifest(build_id, {"publisher": "First Press"})
    assert all(row["accepted"] is True for row in repo.load_records(build_id))


def test_a_page_range_change_reopens_exactly_the_records_it_reclassifies(tmp_path: Path):
    """The start page classifies records (front matter vs main text); a reclassified record must be reopened."""
    manager, repo, build_id = make(tmp_path)
    rows = repo.load_records(build_id)
    for row, page in zip(rows, (1, 30)):
        row.update(pdf_pages=[page], primary_text=True, region_type="main_text")
    repo.save_records(build_id, rows)
    manager.patch_manifest(build_id, {"publisher": "First Press"})  # settle the inherited fields first
    rows = repo.load_records(build_id)
    for row in rows:
        row.update(accepted=True, needs_review=False, review_disposition="accepted")
    repo.save_records(build_id, rows)

    manager.patch_manifest(build_id, {"main_text_start_page": 20})
    by_id = {row["record_id"]: row for row in repo.load_records(build_id)}
    assert by_id["r1"]["region_type"] == "front_matter" and by_id["r1"]["primary_text"] is False
    assert by_id["r1"]["accepted"] is False, "page 1 is before the new start page, so it was reclassified"
    assert by_id["r2"]["region_type"] == "main_text" and by_id["r2"]["accepted"] is True, "page 30 is unaffected"
