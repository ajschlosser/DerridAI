from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app import corpus_builder as cb
from app.models import PdfCorpusBuildCreate


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_release_identity_and_legacy_profile_contract():
    assert cb.PROFILE_VERSION == "derrida-scholarly-v12"
    assert cb.METADATA_PROMPT_VERSION == "derridai-record-metadata-v9"
    assert cb.PUBLICATION_SCHEMA_VERSION == "derridai-corpus-jsonl-v1"
    assert PdfCorpusBuildCreate(asset_id="asset").profile_id == "derrida-scholarly-v12"
    assert set(cb.CORPUS_PROFILES) == {cb.PROFILE_VERSION}
    assert "0.59.0 — Serious Sandpipers" in text("README.md")


def test_source_quality_blocks_corruption_not_unicode():
    healthy = [{"page": 1, "text": "Hélène Cixous · Édouard Glissant · différance · Łódź · Ελληνικά · 東京", "extraction_method": "native"}]
    report = cb.PdfCorpusBuildManager._source_quality_report(healthy)
    assert report["valid_for_enrichment"] is True
    assert report["blocking_pages"] == []
    damaged = [{"page": 2, "text": "corrupt � � source text", "extraction_method": "ocr"}]
    report = cb.PdfCorpusBuildManager._source_quality_report(damaged)
    assert report["valid_for_enrichment"] is False
    assert report["blocking_pages"] == [2]


def test_publication_schema_is_namespaced_unicode_safe_and_enum_valid():
    public = {
        "record_id": "rec-1",
        "text": "Édouard Glissant writes of relation — 東京",
        "source_block_ids": ["p001-b001"],
        "region_type": cb.REGION_TYPES[0],
        "discourse_role": cb.DISCOURSE_ROLES[0],
        "primary_text": True,
        "corpus_build_details": {
            "build_id": "build-1", "publication_id": "publication-1", "published_at": "2026-09-17T00:00:00Z",
            "app_version": "0.59.0", "schema_version": cb.SCHEMA_VERSION,
            "publication_schema_version": cb.PUBLICATION_SCHEMA_VERSION,
            "profile_id": cb.PROFILE_VERSION, "source_sha256": "abc",
        },
    }
    assert cb.PdfCorpusBuildManager._validate_publication_record(public) == []
    assert "東京" in json.dumps(public, ensure_ascii=False)
    public["region_type"] = "invented"
    assert any("region_type" in error for error in cb.PdfCorpusBuildManager._validate_publication_record(public))


def test_frontend_exposes_finish_metadata_resolution_and_reload_safe_queue():
    builder = text("web/src/components/PdfCorpusBuilder.vue")
    api = text("web/src/api/pdfCorpus.ts")
    for token in ("CorpusFinishWorkspace", "CorpusMetadataResolutionPanel", "ensureReviewHydrated", "reviewQueue", "selectedRecordId"):
        assert token in builder
    assert 'query:{' in builder.replace(" ", "") or "router.replace" in builder
    assert "retryMetadata" in api and "/metadata/retry" in api


def test_storybook_covers_new_finish_and_metadata_workflows():
    for name in (
        "CorpusFinishWorkspace.stories.ts",
        "CorpusMetadataResolutionPanel.stories.ts",
        "CorpusMetadataIssues.stories.ts",
        "CorpusBuildLifecycleCard.stories.ts",
    ):
        assert (ROOT / "web/src/components" / name).exists()
