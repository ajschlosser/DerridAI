"""Human-editable primary_text and acceptance gating.

Why: primary_text is a boolean where False is a real answer ("this is not primary
text"). It must be editable by a reviewer, False must persist and count as resolved,
and no record may be accepted while required metadata is still missing.
How: `install_repo` builds a temp repository with one custom record.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app import corpus_builder as cb


def install_repo(tmp_path: Path, record: dict):
    """Create a temp asset, block, build, and save the given record."""
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    cb._json_write(
        repo.asset_meta_path("a"),
        {
            "asset_id": "a",
            "sha256": "x",
            "filename": "x.pdf",
            "page_count": 1,
            "block_count": 1,
            "ocr_pages": 0,
            "warnings": [],
            "metadata": {},
            "pages": [],
        },
    )
    repo.asset_blocks_path("a").write_text(
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
        + "\n",
        encoding="utf-8",
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
            "profile_version": int(cb.CORPUS_PROFILES[cb.PROFILE_VERSION]["version"]),
            "provider": "ollama",
            "model": "test",
            "request": {},
            "manifest": {},
            "validation": {"valid": True},
        }
    )
    repo.save_records(build["build_id"], [record])
    return repo, build


def test_primary_text_is_human_editable_and_false_persists(tmp_path: Path):
    """A reviewer can set primary_text to False and it is kept and treated as resolved.

    Flow: an unresolved primary_text (50% LLM confidence) is patched to False. The
    field is "human_confirmed", removed from the incomplete and review lists, saved to
    disk, and the record can then be accepted.
    Why: a naive "empty means missing" check would treat False as missing forever.
    """
    assert "primary_text" in cb.HUMAN_EDITABLE_METADATA_FIELDS
    record = {
        "record_id": "r1",
        "record_revision": 1,
        "text": "text",
        "text_length": 4,
        "source_block_ids": ["b1"],
        "source_spans": [{"block_id": "b1", "page": 1}],
        "metadata_incomplete_fields": ["primary_text"],
        "metadata_review_fields": ["primary_text"],
        "metadata_field_status": {
            "primary_text": {
                "status": "unresolved",
                "method": "llm",
                "confidence": 0.5,
            }
        },
        "primary_text": None,
        "region_type": "main_text",
        "discourse_role": "analysis",
        "review_disposition": "pending",
        "accepted": False,
        "rejected": False,
        "needs_review": True,
    }
    repo, build = install_repo(tmp_path, record)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    updated = manager.patch_metadata(
        build["build_id"], "r1", {"primary_text": False}, expected_revision=1
    )
    assert updated["primary_text"] is False
    assert updated["metadata_field_status"]["primary_text"]["status"] == "human_confirmed"
    assert "primary_text" not in updated["metadata_incomplete_fields"]
    assert "primary_text" not in updated["metadata_review_fields"]
    persisted = repo.load_records(build["build_id"])[0]
    assert persisted["primary_text"] is False
    accepted = manager.set_disposition(
        build["build_id"], "r1", "accepted", expected_revision=2
    )
    assert accepted["accepted"] is True


def test_accept_and_bulk_accept_block_any_incomplete_metadata(tmp_path: Path):
    """Neither single nor bulk accept may bypass incomplete required metadata.

    Single accept raises a metadata ValueError. Bulk accept changes 0 records and
    reports 1 blocked record (r1) so the UI can explain why.
    """
    record = {
        "record_id": "r1",
        "record_revision": 1,
        "text": "text",
        "text_length": 4,
        "source_block_ids": ["b1"],
        "source_spans": [{"block_id": "b1", "page": 1}],
        "metadata_incomplete_fields": ["primary_text"],
        "metadata_review_fields": [],
        "metadata_field_status": {},
        "primary_text": None,
        "review_disposition": "pending",
        "accepted": False,
        "rejected": False,
        "needs_review": True,
    }
    repo, build = install_repo(tmp_path, record)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    try:
        manager.set_disposition(build["build_id"], "r1", "accepted", expected_revision=1)
        assert False, "accept must be blocked by incomplete required metadata"
    except ValueError as exc:
        assert "metadata" in str(exc).lower()
    result = manager.bulk_disposition(build["build_id"], "accepted")
    assert result["changed"] == 0
    assert result["blocked_metadata"] == 1
    assert result["blocked_record_ids"] == ["r1"]






