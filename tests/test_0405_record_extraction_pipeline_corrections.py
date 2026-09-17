from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def text(path:str)->str:return (ROOT/path).read_text(encoding="utf-8")


def test_0405_release_identity_and_name():
    package=json.loads(text("web/package.json"))
    assert package["version"]=="0.40.25"
    assert 'version="0.40.25"' in text("api/app/main.py")
    assert 'APP_VERSION = "0.40.25"' in text("api/app/config.py")
    assert "0.40.5 — Record Extraction Pipeline Corrections" in text("README.md")


def test_0405_new_semantic_pipeline_is_provenance_versioned():
    builder=text("api/app/corpus_builder.py")
    assert 'SEGMENTATION_PROMPT_VERSION = "derridai-local-boundaries-v7"' in builder
    assert 'METADATA_PROMPT_VERSION = "derridai-record-metadata-v3"' in builder
    assert 'PROFILE_VERSION = "derrida-scholarly-v7"' in builder
    assert '"derrida-scholarly-v2"' in builder  # old build compatibility


def test_segmentation_never_fabricates_one_giant_fallback_record():
    builder=text("api/app/corpus_builder.py")
    run=builder[builder.index("    def _run("):builder.index("    def _rewrite_and_validate")]
    segment=builder[builder.index("    def _segment("):builder.index("    def _reconcile_boundaries")]
    assert "self._normalize_topology(" in segment
    assert "normalization_reviews" in segment
    assert '"segmentation_blocked":False' in segment or '"segmentation_blocked": False' in segment
    assert "Ordinary uncertainty has already resolved conservatively to KEEP" in segment
    assert "self._normalize_topology(" in segment
    assert "_mark_segmentation_review" in builder


def test_segmentation_reduces_failed_windows_to_pairwise_structured_tasks():
    builder=text("api/app/corpus_builder.py")
    assert "def _segment_window_recursive" in builder
    assert "if len(window) > 6 and depth < 4" in builder
    assert "def _segment_pair" in builder
    assert "PairBoundaryResponseModel" in builder
    assert "CompactSegmentationResponseModel" in builder


def test_metadata_is_split_into_small_typed_families_and_preserves_source_record():
    builder=text("api/app/corpus_builder.py")
    enrich=builder[builder.index("    def _enrich_record("):builder.index("    @staticmethod\n    def validate_records")]
    for token in ("DiscourseMetadataResponseModel","QuotationMetadataResponseModel","IndexMetadataResponseModel","metadata_complete","metadata_stage_status"):
        assert token in enrich
    run=builder[builder.index("    def _run("):builder.index("    def _rewrite_and_validate")]
    assert "Metadata worker failed and requires review" in run
    assert 'fallback["needs_review"] = True' in run


def test_build_level_provider_parameters_and_stage_budgets_are_exposed():
    component=text("web/src/components/CorpusExecutionSettings.vue")
    for token in ("num_ctx","temperature","top_k","top_p","min_p","repeat_penalty","seed","mirostat","mirostat_eta","mirostat_tau","think","segmentation_window_tokens","segmentation_num_predict","discourse_num_predict"):
        assert token in component
    assert "Use provider-profile generation defaults" in component
    assert "+1536" in component


def test_pdf_corpus_builds_join_global_operations_and_open_from_home():
    main=text("api/app/main.py")
    runtime=text("web/src/legacy/runtime.js")
    assert "pdf_corpus_builds.list_operations()" in main
    assert "pdf_corpus_builds.clear_finished()" in main
    assert 'job.type==="pdf_corpus"' in runtime
    assert "PDF corpus builds" in runtime
    assert "Open corpus build" in runtime
    assert '["completed","blocked"].includes(job.status)' in runtime


def test_corpus_builder_workflow_quality_ui_storybook_i18n_and_wcag():
    builder=text("web/src/components/PdfCorpusBuilder.vue")
    stepper=text("web/src/components/CorpusWorkflowStepper.vue")
    quality=text("web/src/components/CorpusQualitySummary.vue")
    dictionary=text("api/app/system_store.py")
    assert "CorpusWorkflowStepper" in builder and "CorpusQualitySummary" in builder
    assert ":aria-current=\"step.state==='current'?'step':undefined\"" in stepper
    assert "<ol>" in stepper and "<nav" in stepper
    assert "<dl>" in quality
    assert "DEFAULT_FR_CA.update" in dictionary
    for key in ("pdf_corpus.workflow.label","pdf_corpus.quality.title","pdf_corpus.mirostat"):
        assert key in dictionary
    assert (ROOT/"web/src/components/CorpusWorkflowStepper.stories.ts").exists()
    assert (ROOT/"web/src/components/CorpusQualitySummary.stories.ts").exists()
    assert (ROOT/"web/src/components/CorpusExecutionSettings.stories.ts").exists()


def test_document_manifest_is_a_review_checkpoint_before_segmentation():
    builder=text("api/app/corpus_builder.py")
    main=text("api/app/main.py")
    models=text("api/app/models.py")
    component=text("web/src/components/PdfCorpusBuilder.vue")
    api=text("web/src/api/pdfCorpus.ts")
    assert "review_manifest_before_segmentation: bool = False" in models
    assert 'status="awaiting_manifest_review"' in builder
    assert "def confirm_manifest(" in builder
    assert '@app.post("/api/pdf/corpus-builds/{build_id}/confirm-manifest")' in main
    assert "confirmManifest:" in api
    assert "manifest_review_required" in component
    assert "Confirm document & continue" in component


def test_reconciliation_failures_cannot_silently_undersegment():
    builder=text("api/app/corpus_builder.py")
    reconcile=builder[builder.index("    def _reconcile_boundaries("):builder.index("    @staticmethod\n    def _scholarly_page_range")]
    assert "could not be automatically reconciled" in reconcile
    assert '"kind": "reconciliation"' in reconcile
    assert "remained uncertain after pairwise fallback" in reconcile
    assert "if not batch_unresolved" in reconcile
    assert "return accepted, unresolved" in reconcile
