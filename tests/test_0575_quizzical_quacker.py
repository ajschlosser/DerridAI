from __future__ import annotations

import json
import sys
import types
from pathlib import Path

try:
    import chromadb  # type: ignore  # noqa
except ModuleNotFoundError:
    sys.modules["chromadb"] = types.SimpleNamespace()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
from app import corpus_builder as cb
from app.config import APP_VERSION
from app.locales.en_us import EN_US
from app.locales.fr_ca import FR_CA


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_release_identity_and_locale_parity():
    assert APP_VERSION >= "0.60.0"
    assert json.loads(text("web/package.json"))["version"] >= "0.60.0"
    assert set(EN_US) == set(FR_CA)
    for key in (
        "pdf_corpus.document_structure",
        "pdf_corpus.source_transcription_title",
        "pdf_corpus.enrichment_profile_model",
        "pdf_corpus.active_enrichment_model",
    ):
        assert key in EN_US and key in FR_CA


def test_source_viewer_replaces_focus_iframe_and_is_storybook_backed():
    focus = text("web/src/components/CorpusRecordFocusReview.vue")
    builder = text("web/src/components/PdfCorpusBuilder.vue")
    dialog = text("web/src/components/SourceTranscriptionDialog.vue")
    main = text("api/app/main.py")
    assert "<iframe" not in focus
    assert "openSourceViewer" in focus
    assert "SourceTranscriptionDialog" in builder
    assert "PdfEvidenceViewer" in dialog and "Reviewed record text" in dialog
    assert "Content-Disposition" in main and "inline; filename" in main
    assert (ROOT / "web/src/components/SourceTranscriptionDialog.stories.ts").exists()


def test_document_structure_workspace_is_first_class_and_accessible():
    component = text("web/src/components/DocumentStructureConfigurator.vue")
    builder = text("web/src/components/PdfCorpusBuilder.vue")
    api = text("web/src/api/pdfCorpus.ts")
    main = text("api/app/main.py")
    for token in ("two_up", "main_text_pdf_start", "bibliography_pdf_start", "odd_even", "left_right"):
        assert token in component
    assert "DocumentStructureConfigurator" in builder
    assert "updateDocumentLayout" in api
    assert '/api/pdf/assets/{asset_id}/document-layout' in main
    assert "fieldset" in component and ":focus-visible" in component
    assert (ROOT / "web/src/components/DocumentStructureConfigurator.stories.ts").exists()


def test_document_layout_derives_two_up_pages_regions_and_threads(tmp_path: Path):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    asset = {
        "asset_id": "layout-a", "sha256": "x", "filename": "book.pdf",
        "page_count": 4, "block_count": 8, "ocr_pages": 0, "warnings": [], "metadata": {},
        "pages": [{"pdf_page": i, "width": 1000.0, "height": 1400.0} for i in range(1, 5)],
    }
    cb._json_write(repo.asset_meta_path("layout-a"), asset)
    blocks = []
    for page in range(1, 5):
        blocks += [
            {"block_id": f"p{page}l", "page": page, "bbox": [50, 100, 450, 300], "type": "paragraph", "text": "left", "extraction_method": "native", "confidence": 1.0},
            {"block_id": f"p{page}r", "page": page, "bbox": [550, 100, 950, 300], "type": "paragraph", "text": "right", "extraction_method": "native", "confidence": 1.0},
        ]
    with repo.asset_blocks_path("layout-a").open("w", encoding="utf-8") as handle:
        for block in blocks:
            handle.write(json.dumps(block) + "\n")
    updated = repo.update_document_layout("layout-a", {
        "page_layout": "two_up", "reading_order": "left_to_right",
        "main_text_pdf_start": 2, "main_text_printed_start": 1, "main_text_slot": "right",
        "bibliography_pdf_start": 4, "thread_mode": "left_right",
        "thread_a_language": "fr_fr", "thread_b_language": "en_us",
    })
    assert updated["pages"][0]["deterministic_region_type"] == "front_matter"
    assert updated["pages"][1]["deterministic_region_type"] == "main_text"
    assert updated["pages"][3]["deterministic_region_type"] == "bibliography"
    # A right-hand main-text start means the preceding left half is not assigned a later folio.
    assert updated["pages"][1]["logical_pages"][0]["printed_page_label"] is None
    assert updated["pages"][1]["logical_pages"][1]["printed_page_label"] == "1"
    derived = {b["block_id"]: b for b in repo.load_blocks("layout-a")}
    assert derived["p2r"]["printed_page_label"] == "1"
    assert derived["p3l"]["printed_page_label"] == "2"
    assert derived["p2l"]["document_thread"] == "thread_a"
    assert derived["p2r"]["document_thread"] == "thread_b"
    assert derived["p2l"]["thread_language"] == "fr_fr"
    assert derived["p2r"]["thread_language"] == "en_us"


def test_initial_topology_budget_is_smaller_and_second_reader_is_deferred():
    src = text("api/app/corpus_builder.py")
    segment = src[src.index("    def _segment("):src.index("    def _mark_segmentation_review")]
    run = src[src.index("    def _run("):src.index("    def _metadata_enrichment_finished", src.index("    def _run("))]
    assert "max_adjudications=min(16,max(4" in segment.replace(" ", "")
    assert "max_llm_boundary_calls_per_100_atoms" in segment
    assert "boundary_second_reader_deferred_count" in run
    assert "_audit_suspicious_record_boundaries(records" not in run
    assert "segmentation_elapsed_ms" in run


def test_provider_model_override_endpoint_sharing_and_free_entry_model_controls():
    backend = text("api/app/main.py")
    builder = text("web/src/components/PdfCorpusBuilder.vue")
    switcher = text("web/src/components/CorpusProviderSwitcher.vue")
    execution = text("web/src/components/LlmExecutionControl.vue")
    assert '"model": requested_model or profile.get("model")' in backend
    assert "providerResourceKey" in builder and "base_url" in builder
    assert "Model for newly scheduled tasks" in switcher
    assert "<input" in switcher and "<datalist" in switcher
    assert "<input" in execution and "modelOverride" in execution


def test_metadata_autopopulation_and_combobox_overlay_are_explicit():
    backend = text("api/app/corpus_builder.py")
    editor = text("web/src/components/CorpusMetadataFieldEditor.vue")
    combo = text("web/src/components/ui/UiCombobox.vue")
    assert '"auto_populated": bool(confidence is not None and confidence > minimum' in backend
    assert "status?.auto_populated" in editor
    assert '<Teleport to="body">' in combo
    assert "useId" in combo
    assert "position:fixed" in combo
    assert "human_document_layout" in backend
