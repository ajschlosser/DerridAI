from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def text(path): return (ROOT/path).read_text(encoding="utf-8")

def test_release_identity_and_metadata_threshold():
    assert json.loads(text("web/package.json"))["version"]=="0.56.0"
    assert "0.56.0 — Perilous Penguins" in text("README.md")
    src=text("api/app/corpus_builder.py")
    assert '"min_metadata_confidence": 0.65' in src
    assert 'confidence <= minimum' in src

def test_clean_jsonl_and_repeatable_enrichment_contract():
    src=text("api/app/corpus_builder.py"); api=text("api/app/main.py")
    assert 'def rerun_metadata_enrichment' in src
    assert 'metadata_enrichment_runs' in src
    assert '/metadata/enrich' in api
    assert '"corpus_build_details"' in src # explicit deny-list guard
    serializer=src[src.index('def _serialize_public_record'):src.index('def preview_record')]
    assert 'public["corpus_build_details"]' not in serializer

def test_llm_actions_have_visible_profile_choice_and_storybook_primitives():
    assert (ROOT/'web/src/components/LlmExecutionControl.vue').exists()
    assert (ROOT/'web/src/components/LlmExecutionControl.stories.ts').exists()
    assert (ROOT/'web/src/components/MetadataEnrichmentDialog.stories.ts').exists()
    builder=text('web/src/components/PdfCorpusBuilder.vue')
    assert 'LlmExecutionControl' in builder and 'MetadataEnrichmentDialog' in builder
    touchup=text('web/src/components/CorpusLlmTextTouchupDialog.vue')
    assert 'providerProfileId' in touchup and 'recordId' in touchup and 'reset()' in touchup

def test_confirmed_absence_and_shared_slice_dialog():
    src=text('api/app/corpus_builder.py'); field=text('web/src/components/CorpusMetadataFieldEditor.vue'); slice_dialog=text('web/src/components/CorpusBoundarySliceDialog.vue')
    assert 'human_confirmed_absent' in src
    assert "emit('noValue')" in field
    assert '<UiDialog' in slice_dialog



def test_unconfirmed_manifest_bounds_are_non_destructive_and_resume_repairs_old_scope():
    src=text("api/app/corpus_builder.py")
    helper=src[src.index("def _manifest_main_text_blocks"):src.index("def _segmentation_windows")]
    assert "bounds_confirmed: bool = False" in helper
    assert "if not bounds_confirmed:" in helper
    assert "return blocks" in helper
    run=src[src.index("def _run("):src.index("def _metadata_enrichment_finished", src.index("def _run("))]
    assert "source_scope_repair" in run
    assert "resume and not source_scope_repair" in run
    assert "previously truncated automatic main-text scope" in run
