from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app import corpus_builder as cb
from app.config import APP_VERSION


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def install_repo(tmp_path: Path, record: dict):
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


def test_release_identity():
    assert APP_VERSION == "0.54.0"
    assert json.loads(text("web/package.json"))["version"] == "0.54.0"
    assert "0.54.0 — Neurotic Gnat" in text("README.md")


def test_primary_text_is_human_editable_and_false_persists(tmp_path: Path):
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


def test_review_ui_accept_is_actionable_and_preserves_viewport():
    builder = text("web/src/components/PdfCorpusBuilder.vue")
    assert "async function attemptAccept()" in builder
    assert "focusFirstMetadataBlocker" in builder
    assert "captureReviewViewport" in builder and "restoreReviewViewport" in builder
    assert "@click=\"toggleAccept\"" in builder
    assert ":disabled=\"busy!==''\"" in builder
    assert 'metadata_decision_required' in builder
    assert 'reviewDecision' in builder
    assert "scrollIntoView(" not in builder
    assert "reviewInspectorTab" in builder
    assert "selectedMetadataBlockingLabel" in builder


def test_primary_text_uses_boolean_radio_not_string_truthiness():
    panel = text("web/src/components/CorpusMetadataFieldEditor.vue")
    assert ":value=\"true\"" in panel
    assert ":value=\"false\"" in panel
    assert '@click="save"' in panel
    assert 'value==="true"' not in panel
    assert "required&&draft===null" in panel
    assert ":value=\"false\"" in panel
    stories = text("web/src/components/CorpusMetadataResolutionPanel.stories.ts")
    assert "PrimaryTextHumanDecisionNo" in stories


def test_review_i18n_has_en_and_fr_keys():
    store = text("api/app/locales/en_us.py") + text("api/app/locales/fr_ca.py")
    for key in (
        '"pdf_corpus.review_mode"',
        '"pdf_corpus.resolve_metadata_to_accept"',
        '"pdf_corpus.primary_text_help"',
        '"pdf_corpus.bulk_done_metadata_blocked"',
    ):
        assert store.count(key.strip('"')) >= 2
