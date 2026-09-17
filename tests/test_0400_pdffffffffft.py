from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_0400_release_identity_and_notes():
    package = json.loads(text("web/package.json"))
    assert package["version"] == "0.40.15"
    assert 'version="0.40.15"' in text("api/app/main.py")
    assert 'APP_VERSION = "0.40.15"' in text("api/app/config.py")
    assert "# DerridAI Corpus Viewer 0.40.15" in text("README.md")
    assert "0.40.0 — Pdffffffffft." in text("README.md")


def test_pdf_sources_are_content_addressed_layout_aware_and_ocr_capable():
    builder = text("api/app/corpus_builder.py")
    dockerfile = text("api/Dockerfile")
    assert "hashlib.sha256(data).hexdigest()" in builder
    assert 'page.get_text("dict", sort=True)' in builder
    assert "get_textpage_ocr" in builder
    assert '"printed_page_label"' in builder
    assert '"block_id"' in builder
    assert "tesseract-ocr-eng" in dockerfile
    assert "tesseract-ocr-fra" in dockerfile
    assert "tesseract-ocr-deu" in dockerfile


def test_semantic_segmentation_does_not_use_page_or_character_boundaries():
    builder = text("api/app/corpus_builder.py")
    segmentation = builder[builder.index("    def _compact_segment_prompt("):builder.index("    def _reconcile_boundaries")]
    assert "speaker, position holder, stance, target, quotation frame, discourse role, or argumentative move" in segmentation
    assert "NEVER split because a page changes" in segmentation
    assert "execution window ends" in segmentation
    assert "text reaches a size" in segmentation
    assert "after_block_id" in segmentation
    # Length is no longer a semantic candidate at all; size handling is a deterministic local safety search.
    assert "soft_length_candidate" not in segmentation
    assert "_normalize_topology" in segmentation
    assert "deterministic_topology_normalizer" in segmentation
    assert "provisional" in segmentation


def test_record_text_is_deterministic_and_metadata_is_source_evidence_bound():
    builder = text("api/app/corpus_builder.py")
    construct = builder[builder.index("    @staticmethod\n    def _construct_records"):builder.index("    def _enrich_record")]
    enrich = builder[builder.index("    def _enrich_record"):builder.index("    @staticmethod\n    def validate_records")]
    assert 'text = "\\n\\n".join(block["text"].strip()' in construct
    assert '"source_block_ids"' in construct
    assert '"source_spans"' in construct
    assert "Do not return quotation relations, topical indexing, bibliographic metadata, summaries, or source text" in enrich
    assert "POSITION HOLDER" in enrich
    assert '"field_evidence"' in enrich
    assert "Source-bound fields cannot be edited" in builder


def test_corpus_build_api_is_paginated_reviewable_and_publishable():
    main = text("api/app/main.py")
    for route in (
        '@app.post("/api/pdf/assets")',
        '@app.get("/api/pdf/assets/{asset_id}/blocks")',
        '@app.post("/api/pdf/corpus-builds")',
        '@app.get("/api/pdf/corpus-builds")',
        '@app.get("/api/pdf/corpus-builds/{build_id}/records")',
        '@app.patch("/api/pdf/corpus-builds/{build_id}/records/{record_id}/metadata")',
        '@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/accept")',
        '@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/merge")',
        '@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/split")',
        '@app.post("/api/pdf/corpus-builds/{build_id}/publish")',
    ):
        assert route in main
    assert "offset: int = Query(default=0, ge=0)" in main
    assert "limit: int = Query(default=50, ge=1, le=200)" in main


def test_native_vue_corpus_builder_has_history_review_and_three_pane_source_binding():
    component = text("web/src/components/PdfCorpusBuilder.vue")
    workspace = text("web/src/views/PdfWorkspaceView.vue")
    tools = text("web/src/views/ToolsView.vue")
    for token in (
        "Corpus builds",
        "Needs review only",
        "Source PDF",
        "Generated records",
        "Interpretive metadata",
        "Field evidence",
        "Merge previous",
        "Split after this block",
        "Publish JSONL",
        "pageSize=50",
    ):
        assert token in component
    assert "PdfCorpusBuilder" in workspace
    assert "Corpus Builder" in workspace
    assert "PdfWorkspaceView" in tools
    assert "Use current Explorer PDF" in component


def test_pdf_corpus_builds_are_provenanced_backed_up_and_publication_gated():
    builder = text("api/app/corpus_builder.py")
    main = text("api/app/main.py")
    for token in (
        "source_sha256",
        "schema_version",
        "profile_version",
        "segmentation_prompt_version",
        "metadata_prompt_version",
        "source_block_count",
        "text_fidelity_errors",
        "Publication is blocked until source coverage and text-fidelity validation pass",
        "Publication is blocked:",
    ):
        assert token in builder
    assert 'snapshot_root / "pdf-corpus"' in main
    assert 'data_root / ".home" / "pdf-corpus"' in main
    assert "pdf_corpus_builds.active_count()" in main
