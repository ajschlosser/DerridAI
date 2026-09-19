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


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def install_repo(tmp_path: Path, records: list[dict]):
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
    return {
        "record_id":rid,"record_revision":1,"text":"text","text_length":4,"source_block_ids":[bid],
        "source_spans":[{"block_id":bid,"page":1}],"metadata_incomplete_fields":["primary_text"] if blocked else [],
        "metadata_review_fields":[],"metadata_field_status":{},"metadata_complete":not blocked,"primary_text":None if blocked else True,
        "region_type":"main_text","discourse_role":"analysis","review_disposition":"pending","accepted":False,"rejected":False,
        "needs_review":False,"source_quality_issues":[{"code":"source_quality_blocking","pages":[1]}] if source_problem else [],
    }


def test_release_identity():
    assert APP_VERSION == "0.52.0"
    assert json.loads(text("web/package.json"))["version"] == "0.52.0"
    assert "0.52.0 — Lazy Lizard" in text("README.md")


def test_review_decision_is_atomic_and_returns_next(tmp_path: Path):
    repo, build = install_repo(tmp_path, [rec("r1","b1"), rec("r2","b2")])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    result = manager.review_decision(build["build_id"], "r1", "accepted", expected_revision=1)
    assert result["applied"] is True
    assert result["record"]["accepted"] is True
    assert result["next_record"]["record_id"] == "r2"
    assert result["build"]["accepted_count"] == 1
    assert result["build"]["publication_readiness"]["records_pending"] == 1


def test_review_decision_returns_structured_metadata_blocker(tmp_path: Path):
    repo, build = install_repo(tmp_path, [rec("r1","b1",blocked=True)])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    result = manager.review_decision(build["build_id"], "r1", "accepted", expected_revision=1)
    assert result["applied"] is False
    assert result["blocked"] is True
    assert result["blocker"] == "metadata_decision_required"
    assert result["blocking_fields"] == ["primary_text"]


def test_empty_metadata_issue_summary_is_authoritative(tmp_path: Path):
    repo, build = install_repo(tmp_path, [rec("r1","b1")])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    refreshed = manager._rewrite_and_validate(build["build_id"], repo.load_records(build["build_id"]))
    assert refreshed["metadata_issue_summary"]["fields_unresolved"] == 0
    assert refreshed["metadata_completed"] == 1
    assert not any(b["code"] == "required_metadata" for b in refreshed["publication_readiness"]["blockers"])


def test_source_problem_filter_is_first_class(tmp_path: Path):
    repo, build = install_repo(tmp_path, [rec("r1","b1",source_problem=True), rec("r2","b2")])
    page = repo.page_records(build["build_id"], source_problem=True)
    assert page["total"] == 1
    assert page["items"][0]["record_id"] == "r1"



def test_fragmented_glyph_record_is_detected():
    record={"text":"OFF\n:\n=\n*\n?\n;\ni\n2\nA\nl\n©\nCosmopolitanism and Forgiveness","pdf_pages":[1]}
    issues=cb.PdfCorpusBuildManager._record_extraction_quality_issues(record)
    assert issues and issues[0]["code"]=="fragmented_glyph_layout"

def test_ui_suppresses_empty_review_and_zero_metadata_attention():
    builder = text("web/src/components/PdfCorpusBuilder.vue")
    issues = text("web/src/components/CorpusMetadataIssues.vue")
    assert "reviewDecision" in builder
    assert "buildRunning && !hasRecordTopology" in builder
    assert "metadataFieldIssueCount>0" in builder
    assert 'v-if="totalIssues>0"' in issues
    assert 'reviewQueue.value="source"' in builder or "reviewQueue==='source'" in builder
    assert "showBuildConfiguration" in builder


def test_dundee_i18n_and_storybook_surface():
    store = text("api/app/locales/en_us.py") + text("api/app/locales/fr_ca.py")
    for key in ('"pdf_corpus.building_records_title"','"pdf_corpus.queue_source"','"pdf_corpus.configure_new_build"'):
        assert store.count(key.strip('"')) >= 2
    # Existing review and resolution components stay independently testable in Storybook.
    assert (ROOT / "web/src/components/CorpusMetadataResolutionPanel.stories.ts").exists()
    assert (ROOT / "web/src/components/CorpusRecordFocusReview.stories.ts").exists()
