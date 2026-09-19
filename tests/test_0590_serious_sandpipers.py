from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
def text(path): return (ROOT/path).read_text(encoding='utf-8')

def test_0590_release_identity_and_product_name():
    assert json.loads(text('web/package.json'))['name']=='derridai'

def test_user_workflow_is_four_phases_not_machine_stages():
    stepper=text('web/src/components/CorpusWorkflowStepper.vue')
    for label in ('Source & configure','Build','Review','Publish'):
        assert label in stepper
    assert 'Initialize' not in stepper
    assert 'Segment' not in stepper
    assert 'repeat(4' in stepper

def test_setup_order_places_structure_before_llm_and_launch_summary():
    builder=text('web/src/components/PdfCorpusBuilder.vue')
    source=builder.index('pdf-corpus-source-title')
    structure=builder.index('pdf-corpus-structure-phase-title')
    llm=builder.index('pdf_corpus.llm_enrichment_title')
    construction=builder.index('pdf_corpus.record_construction')
    execution=builder.index('pdf_corpus.advanced_execution')
    readiness=builder.index('<CorpusBuildReadiness')
    assert source < structure < llm < construction < execution < readiness
    assert 'build-launch-row' not in builder[builder.index('<template>'):builder.index('<details v-if="currentBuild && !showBuildConfiguration"')]

def test_build_readiness_is_responsive_and_storybook_covered():
    component=text('web/src/components/CorpusBuildReadiness.vue')
    story=text('web/src/components/CorpusBuildReadiness.stories.ts')
    assert 'position:sticky' in component
    assert 'contextSafe' in component
    assert 'structureSummary' in component
    assert 'NeedsAttention' in story and 'ConcurrentBuild' in story

def test_document_structure_is_two_pane_with_single_column_rules():
    component=text('web/src/components/DocumentStructureConfigurator.vue')
    assert 'grid-template-columns:minmax(520px,1.2fr) minmax(360px,.8fr)' in component
    assert '.rules{display:grid;grid-template-columns:minmax(0,1fr)' in component
    assert 'position:sticky;top:78px' in component

def test_review_can_promote_metadata_and_source_to_full_workspaces():
    builder=text('web/src/components/PdfCorpusBuilder.vue')
    assert 'reviewWorkspaceMode=ref<"record"|"metadata"|"source">' in builder
    assert "setReviewWorkspaceMode('metadata')" in builder
    assert "setReviewWorkspaceMode('source')" in builder
    assert "'detail-mode':reviewWorkspaceMode!=='record'" in builder
    assert '.record-first-review.detail-mode' in builder

def test_deep_enrichment_does_not_render_semantic_indexing_as_disabled_control():
    builder=text('web/src/components/PdfCorpusBuilder.vue')
    setup=builder[builder.index('<section v-if="showBuildConfiguration"'):builder.index('<details v-if="currentBuild && !showBuildConfiguration"')]
    assert "v-if=\"enrichmentMode==='deep'\" class=\"included-feature\"" in setup
    assert ':disabled="enrichmentMode===\'deep\'"' not in setup

def test_new_strings_exist_in_both_locales():
    en=text('api/app/locales/en_us.py'); fr=text('api/app/locales/fr_ca.py')
    for key in ('pdf_corpus.workflow.source_configure','pdf_corpus.readiness.ready','pdf_corpus.review_workspace','pdf_corpus.workspace.metadata','pdf_corpus.document_structure_saved_impact'):
        assert key in en and key in fr

def test_build_history_is_available_without_leaving_current_phase():
    builder=text('web/src/components/PdfCorpusBuilder.vue')
    menu=text('web/src/components/CorpusBuildHistoryMenu.vue')
    story=text('web/src/components/CorpusBuildHistoryMenu.stories.ts')
    assert '<CorpusBuildHistoryMenu' in builder
    assert 'history-popover' in menu
    assert 'Open or monitor another build without leaving the current task.' in menu
    assert 'Build History Menu' in story
