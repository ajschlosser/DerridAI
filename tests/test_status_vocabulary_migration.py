"""Assertion-status vocabulary rename: llm_inferred/human_confirmed_absent migrate on read.

Why: the DERRIDAI Core Specification names the assertion-status vocabulary
`model_inferred` and `confirmed_absent`; the codebase previously used
`llm_inferred` and `human_confirmed_absent`. Builds and records written before
the rename still have the old values on disk, and must keep working without a
one-off migration script -- the repository normalizes them the first time
they are read, in place, so nothing downstream has to know two vocabularies.
How: writes a build/records/checkpoint directly to disk with the old status
strings (bypassing the repository's own write path, the way an old on-disk
build actually looks), then reads them back through the repository and checks
every read path returns the new vocabulary.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
from app import corpus_builder as cb


def _install_build_with_old_vocabulary(tmp_path: Path) -> tuple[cb.PdfCorpusRepository, str]:
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    asset = {
        "asset_id": "a",
        "sha256": "x",
        "filename": "x.pdf",
        "page_count": 1,
        "block_count": 1,
        "ocr_pages": 0,
        "warnings": [],
        "metadata": {},
        "pages": [],
    }
    cb._json_write(repo.asset_meta_path("a"), asset)
    with repo.asset_blocks_path("a").open("w", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "block_id": "b1",
                    "page": 1,
                    "bbox": [0, 0, 1, 1],
                    "type": "paragraph",
                    "text": "text",
                    "extraction_method": "native",
                    "confidence": 1.0,
                }
            )
            + "\n"
        )
    build = repo.create_build(
        {
            "asset_id": "a",
            "source_sha256": "x",
            "source_filename": "x.pdf",
            "source_page_count": 1,
            "source_block_count": 1,
            "schema_version": cb.SCHEMA_VERSION,
            "profile_id": cb.PROFILE_VERSION,
            "profile_version": 11,
            "app_version": "test",
            "provider": "ollama",
            "model": "test",
            "request": {"enrichment_mode": "fast"},
            "manifest": {"title": "Book", "document_author": "Derrida"},
        }
    )
    build_id = build["build_id"]
    # Overwrite build.json directly with a leftover old-vocabulary status, as a
    # build written before the rename would actually have on disk.
    build["last_field_status"] = {"status": "llm_inferred", "method": "model", "confidence": 0.7, "reason": ""}
    repo.save_build(build)

    record = {
        "record_id": "r1",
        "record_revision": 1,
        "text": "text",
        "text_length": 4,
        "source_block_ids": ["b1"],
        "source_spans": [{"block_id": "b1", "page": 1}],
        "pdf_pages": [1],
        "metadata_field_status": {
            "region_type": {"status": "llm_inferred", "method": "model", "confidence": 0.8, "reason": ""},
            "speaker": {"status": "human_confirmed_absent", "method": "human", "confidence": 1.0, "reason": ""},
        },
        "metadata_decisions": [{"field": "speaker", "value": None, "at": "2026-01-01T00:00:00Z", "source": "human_confirmed_absent"}],
        "review_disposition": "pending",
        "accepted": False,
        "rejected": False,
        "metadata_stage_status": {"discourse": "queued", "quotation": "queued", "indexing": "queued"},
        "metadata_enrichment_state": "queued",
    }
    repo.save_records(build_id, [record])
    repo.save_checkpoint(build_id, "undo", {"records": [dict(record)]})
    return repo, build_id


def test_get_build_migrates_old_status_vocabulary(tmp_path: Path) -> None:
    """A build.json written with llm_inferred reads back as model_inferred."""
    repo, build_id = _install_build_with_old_vocabulary(tmp_path)
    build = repo.get_build(build_id)
    assert build["last_field_status"]["status"] == "model_inferred"


def test_list_builds_migrates_old_status_vocabulary(tmp_path: Path) -> None:
    """The build-listing path (which reads build.json directly, not via get_build) also migrates."""
    repo, _build_id = _install_build_with_old_vocabulary(tmp_path)
    page = repo.list_builds()
    assert page["items"][0]["last_field_status"]["status"] == "model_inferred"


def test_load_records_migrates_old_status_vocabulary(tmp_path: Path) -> None:
    """Both the field-status dict and the metadata-decision source migrate."""
    repo, build_id = _install_build_with_old_vocabulary(tmp_path)
    records = repo.load_records(build_id)
    status = records[0]["metadata_field_status"]
    assert status["region_type"]["status"] == "model_inferred"
    assert status["speaker"]["status"] == "confirmed_absent"
    assert records[0]["metadata_decisions"][0]["source"] == "confirmed_absent"


def test_page_records_migrates_old_status_vocabulary(tmp_path: Path) -> None:
    """The paginated browse path (a separate JSONL-streaming read) also migrates."""
    repo, build_id = _install_build_with_old_vocabulary(tmp_path)
    page = repo.page_records(build_id)
    status = page["items"][0]["metadata_field_status"]
    assert status["region_type"]["status"] == "model_inferred"
    assert status["speaker"]["status"] == "confirmed_absent"


def test_load_checkpoint_migrates_old_status_vocabulary(tmp_path: Path) -> None:
    """Review-undo and other checkpoint payloads also migrate."""
    repo, build_id = _install_build_with_old_vocabulary(tmp_path)
    checkpoint = repo.load_checkpoint(build_id, "undo")
    status = checkpoint["records"][0]["metadata_field_status"]
    assert status["region_type"]["status"] == "model_inferred"
    assert status["speaker"]["status"] == "confirmed_absent"


def test_migration_leaves_unrelated_status_bearing_values_alone() -> None:
    """The migration only rewrites the two renamed values, nothing else."""
    value = cb._migrate_status_vocabulary(
        {
            "status": "human_confirmed",
            "nested": {"source": "human_confirmed_boundary"},
            "list": [{"status": "deterministic"}, {"status": "llm_inferred"}],
        }
    )
    assert value["status"] == "human_confirmed"
    assert value["nested"]["source"] == "human_confirmed_boundary"
    assert value["list"][0]["status"] == "deterministic"
    assert value["list"][1]["status"] == "model_inferred"
