from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_0401_release_identity_and_notes():
    package = json.loads(text("web/package.json"))
    assert package["version"] == "0.40.10"
    assert 'version="0.40.10"' in text("api/app/main.py")
    assert 'APP_VERSION = "0.40.10"' in text("api/app/config.py")
    assert "0.40.1 — Dorar the Explorah" in text("README.md")


def test_corpus_llm_uses_typed_json_schema_validation_repair_and_bounded_retry():
    builder = text("api/app/corpus_builder.py")
    rag = text("api/app/rag.py")
    for token in (
        "class DocumentManifestModel(BaseModel)",
        "class SegmentationResponseModel(BaseModel)",
        "class MetadataResponseModel(BaseModel)",
        "response_model.model_json_schema()",
        "response_model.model_validate(value)",
        "def _parse_json_robust",
        "for attempt in range",
        "previous response could not be validated",
    ):
        assert token in builder
    assert "json_schema: dict[str, Any] | None = None" in rag
    assert 'body["format"] = json_schema' in rag
    assert '"type": "json_schema"' in rag


def test_malformed_metadata_is_reviewable_instead_of_aborting_build():
    builder = text("api/app/corpus_builder.py")
    enrich = builder[builder.index("    def _enrich_record("):builder.index("    @staticmethod\n    def validate_records")]
    assert "metadata extraction could not be validated" in enrich
    assert 'record["metadata_complete"] = successful_tasks == len(tasks)' in enrich
    assert "return record" in enrich
    run = builder[builder.index("    def _run("):builder.index("    def _rewrite_and_validate")]
    assert "self.repo.save_records(build_id, records)" in run
    assert 'if not record.get("metadata_complete")' in run


def test_segmentation_is_confidence_gated_and_semantically_reconciled():
    builder = text("api/app/corpus_builder.py")
    segmentation = builder[builder.index("    def _compact_segment_prompt("):builder.index("    @staticmethod\n    def _construct_records")]
    assert 'pair.get("decision") == "split"' in segmentation
    assert '>= threshold' in segmentation
    assert "_reconcile_boundaries" in segmentation
    assert "Judge only genuine discourse boundaries" in segmentation
    assert "NEVER split because a page changes" in segmentation


def test_metadata_has_neighbor_context_required_attribution_evidence_and_citations():
    builder = text("api/app/corpus_builder.py")
    enrich = builder[builder.index("    def _enrich_record("):builder.index("    @staticmethod\n    def validate_records")]
    assert "previous_record_tail" in enrich and "next_record_head" in enrich
    assert "ATTRIBUTION_EVIDENCE_FIELDS" in enrich
    assert "has no bound source evidence" in enrich
    assert "_citation_strings(record)" in enrich
    assert 'record["attribution_confidence"]' in enrich
    assert 'record["semantic_classification_confidence"]' in enrich


def test_resume_checkpoint_api_provider_profiles_i18n_and_storybook_are_present():
    builder = text("api/app/corpus_builder.py")
    main = text("api/app/main.py")
    component = text("web/src/components/PdfCorpusBuilder.vue")
    system_store = text("api/app/system_store.py")
    assert "save_checkpoint" in builder and "load_checkpoint" in builder
    assert '@app.post("/api/pdf/corpus-builds/{build_id}/resume")' in main
    assert "_resolve_pdf_corpus_provider" in main
    assert "ProviderProfileSelect" in component
    assert "CorpusBuildProgress" in component
    assert "FieldEvidenceList" in component
    assert "pdf_corpus.title" in system_store
    assert "DEFAULT_FR_CA.update" in system_store
    assert (ROOT / "web/src/components/CorpusBuildProgress.stories.ts").exists()
    assert (ROOT / "web/src/components/FieldEvidenceList.stories.ts").exists()


def test_validation_is_broader_than_source_coverage_only():
    builder = text("api/app/corpus_builder.py")
    validate = builder[builder.index("    @staticmethod\n    def validate_records"):builder.index("    def _run(")]
    for token in (
        "source_order_errors",
        "page_mapping_errors",
        "metadata_evidence_errors",
        "citation_errors",
        "text_fidelity_errors",
        "source_valid",
        "metadata_valid",
    ):
        assert token in validate


def test_pdf_review_uses_physical_pdf_page_and_wcag_patterns():
    component = text("web/src/components/PdfCorpusBuilder.vue")
    workspace = text("web/src/views/PdfWorkspaceView.vue")
    progress = text("web/src/components/CorpusBuildProgress.vue")
    evidence = text("web/src/components/FieldEvidenceList.vue")
    assert "selectedRecord.value?.pdf_pages" in component
    assert 'role="progressbar"' in progress
    assert 'aria-live="polite"' in component
    assert ':aria-current' in component
    assert ':aria-pressed' in evidence
    assert "focus-visible" in component
    assert "prefers-reduced-motion" in progress
    assert "useI18nStore" in component and "useI18nStore" in workspace
    assert "margin-inline-start" in workspace


def test_structured_output_escalation_and_streaming_schema_fallbacks_are_resilient():
    builder = text("api/app/corpus_builder.py")
    rag = text("api/app/rag.py")
    main = text("api/app/main.py")
    assert 'request_chain: list[tuple[str, dict[str, Any]]]' in builder
    assert 'review_provider_profile_id' in main
    assert '"_review_provider"' in main
    assert 'bounded retry' in builder
    assert 'fallback["format"] = "json"' in rag
    assert 'status in {400, 422}' in rag


def test_segmentation_checkpoints_degraded_mode_and_resume_do_not_discard_work():
    builder = text("api/app/corpus_builder.py")
    segment = builder[builder.index("    def _segment("):builder.index("    def _reconcile_boundaries")]
    run = builder[builder.index("    def _run("):builder.index("    def _rewrite_and_validate")]
    assert 'load_checkpoint(build_id,"local_boundary_state"' in segment
    assert 'save_checkpoint(build_id,"local_boundary_state"' in segment
    assert 'segmentation_failed_windows' in segment
    assert 'segmentation_degraded' in segment
    assert 'status="awaiting_review"' in run or 'status=status' in run
    assert '"segmentation_blocked":False' in segment or '"segmentation_blocked": False' in segment
    assert '_construct_records' in run
    assert '_mark_segmentation_review' in run
    assert 'Ordinary uncertainty has already resolved conservatively to KEEP' in segment


def test_document_manifest_and_printed_page_mapping_are_human_correctable():
    builder = text("api/app/corpus_builder.py")
    main = text("api/app/main.py")
    component = text("web/src/components/PdfCorpusBuilder.vue")
    assert "def update_page_labels" in builder
    assert '"human_override"' in builder
    assert "visible_folio" in builder and "inferred_from_folios" in builder
    assert "def patch_manifest" in builder
    assert '@app.patch("/api/pdf/assets/{asset_id}/page-labels")' in main
    assert '@app.patch("/api/pdf/corpus-builds/{build_id}/manifest")' in main
    assert "PdfPageLabelEditor" in component
    assert "DocumentManifestEditor" in component
    assert (ROOT / "web/src/components/PdfPageLabelEditor.stories.ts").exists()
    assert (ROOT / "web/src/components/DocumentManifestEditor.stories.ts").exists()


def test_pdf_evidence_viewer_overlays_source_boxes_and_has_storybook_coverage():
    viewer = text("web/src/components/PdfEvidenceViewer.vue")
    component = text("web/src/components/PdfCorpusBuilder.vue")
    assert "pdfjs-dist/legacy/build/pdf.mjs" in viewer
    assert "block-overlay" in viewer
    assert "evidenceBlockIds" in viewer
    assert 'aria-live="polite"' in viewer
    assert "PdfEvidenceViewer" in component
    assert "selectedPdfPage" in component
    assert (ROOT / "web/src/components/PdfEvidenceViewer.stories.ts").exists()


def test_pdf_upload_is_bounded_and_metadata_edits_use_optimistic_revision():
    config = text("api/app/config.py")
    main = text("api/app/main.py")
    api = text("web/src/api/pdfCorpus.ts")
    component = text("web/src/components/PdfCorpusBuilder.vue")
    assert "pdf_max_upload_mb" in config
    assert "status_code=413" in main
    assert "await file.read(1024 * 1024)" in main
    assert "expected_revision" in api
    assert "record_revision" in api
    assert "selectedRecord.value.record_revision" in component


def test_0401_new_pdf_components_are_i18n_and_accessibility_aware():
    system_store = text("api/app/system_store.py")
    for key in (
        "pdf_corpus.page_mapping",
        "pdf_corpus.document_manifest",
        "pdf_corpus.pdf_loading",
        "pdf_corpus.escalation_provider",
    ):
        assert key in system_store
    assert "DEFAULT_FR_CA.update" in system_store
    page_map = text("web/src/components/PdfPageLabelEditor.vue")
    manifest = text("web/src/components/DocumentManifestEditor.vue")
    viewer = text("web/src/components/PdfEvidenceViewer.vue")
    assert 'role="table"' in page_map
    assert "focus-visible" in page_map
    assert "focus-visible" in manifest
    assert 'role="alert"' in viewer


def test_0401_human_evidence_binding_is_editable_but_source_fields_are_not():
    builder = text("api/app/corpus_builder.py")
    main = text("api/app/main.py")
    api = text("web/src/api/pdfCorpus.ts")
    component = text("web/src/components/PdfCorpusBuilder.vue")
    assert "HUMAN_EDITABLE_METADATA_FIELDS" in builder
    assert "def patch_evidence(" in builder
    assert "Evidence blocks must belong to the selected record" in builder
    assert '@app.patch("/api/pdf/corpus-builds/{build_id}/records/{record_id}/evidence")' in main
    assert "patchEvidence:" in api
    assert "toggleEvidenceBlock" in component
    assert "record_revision" in component
    assert "Add as evidence" in component


def test_0401_review_revalidation_ignores_intentionally_excluded_source_blocks_and_bad_validation_keeps_review_open():
    builder = text("api/app/corpus_builder.py")
    rewrite = builder[builder.index("    def _rewrite_and_validate"):builder.index("    def patch_manifest")]
    assert 'if not block.get("excluded_reason")' in rewrite
    assert 'or not validation.get("valid")' in rewrite


def test_0401_structural_edits_keep_scholarly_page_labels_distinct_from_physical_pdf_pages():
    builder = text("api/app/corpus_builder.py")
    merge = builder[builder.index("    def merge("):builder.index("    def split(")]
    split = builder[builder.index("    def split("):builder.index("    def rerun_metadata(")]
    assert "self._scholarly_page_range(group)" in merge
    assert "self._scholarly_page_range(group)" in split
    assert '"pdf_pages": pages' in merge and '"pdf_pages": pages' in split


def test_0401_field_evidence_list_preserves_button_semantics_for_wcag():
    evidence = text("web/src/components/FieldEvidenceList.vue")
    assert "<ul" in evidence and "<li" in evidence
    assert 'role="listitem"' not in evidence
    assert ':aria-pressed' in evidence


def test_0401_build_observability_tracks_structured_output_retries_and_escalations():
    builder = text("api/app/corpus_builder.py")
    progress = text("web/src/components/CorpusBuildProgress.vue")
    for token in ("structured_output_failures", "escalations", "llm_metrics"):
        assert token in builder
    assert "llmMetrics" in progress
    assert "validation_details" in progress


def test_0401_pdf_builder_uses_configured_admin_profiles_not_only_researcher_allowlist():
    component = text("web/src/components/PdfCorpusBuilder.vue")
    runtime = text("web/src/legacy/runtime.js")
    main = text("api/app/main.py")
    models = text("api/app/models.py")
    assert "getProviderProfilesForUi" in component
    assert "serverProviderIds" in component
    assert "directProfilePayload" in component
    assert "getProviderRequestConfigForUi" in runtime
    assert 'elif not (resolved.get("provider") and (resolved.get("model") or resolved.get("base_url")))' in main
    assert "review_provider: PdfCorpusProviderConfig | None = None" in models


def test_0401_pdf_builder_does_not_persist_direct_provider_secrets_in_public_manifest():
    builder = text("api/app/corpus_builder.py")
    main = text("api/app/main.py")
    assert 'public_request = {k: v for k, v in request.items() if k not in {"api_key", "_review_provider"}}' in builder
    assert 'direct_review = resolved.pop("review_provider", None)' in main
