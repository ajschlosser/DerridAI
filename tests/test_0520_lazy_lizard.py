from pathlib import Path
import json
import sys
import types

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules['chromadb'] = types.SimpleNamespace()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'api'))
from app import corpus_builder as cb
from app.models import PdfCorpusBuildCreate
from app.locales.en_us import EN_US
from app.locales.fr_ca import FR_CA


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_pre_enrichment_cleanup_is_default_and_preserves_source_truth():
    request = PdfCorpusBuildCreate(asset_id='pdf-test')
    assert request.auto_clean_text is True
    assert 'ocr_artifacts' in request.text_cleanup_rules
    records = [
        {
            'record_id': 'r1',
            'text': 'ON COSMOPOLITANISM\n12\nThis sentence was broken in the middle of\na clause by PDF layout.\nDownloaded from JSTOR.org\nON COSMOPOLITANISM',
            'text_length': 142,
        },
        {
            'record_id': 'r2',
            'text': 'ON COSMOPOLITANISM\n13\nAnother sentence continues over\na layout line without punctuation.\nON COSMOPOLITANISM',
            'text_length': 120,
        },
    ]
    report = cb.apply_automatic_text_cleanup(
        records,
        request.text_cleanup_rules,
        document_terms=['On Cosmopolitanism'],
    )
    assert report['records_changed'] == 2
    assert records[0]['source_extracted_text'].startswith('ON COSMOPOLITANISM')
    assert 'ON COSMOPOLITANISM' not in records[0]['text']
    assert '\n12\n' not in records[0]['text']
    assert 'Downloaded from JSTOR.org' not in records[0]['text']
    assert 'middle of a clause' in records[0]['text']
    assert records[0]['text_revision_history'][-1]['source'] == 'automatic_cleanup'
    assert records[0]['text_revision_history'][-1]['diff']


def test_cleanup_preserves_likely_poetry_and_quotation_layout():
    poetry = '“First short line\nSecond short line\nThird short line\nFourth short line”'
    cleaned, report = cb._clean_text_value(poetry, {'paragraph_lines'}, set())
    assert cleaned == poetry
    assert report['changed'] is False


def test_publication_readiness_requires_document_identity_and_semantic_integrity():
    build = {
        'profile_id': cb.PROFILE_VERSION,
        'record_count': 1,
        'accepted_count': 1,
        'rejected_count': 0,
        'needs_review_count': 0,
        'boundary_review_count': 0,
        'source_problem_count': 0,
        'metadata_total': 1,
        'metadata_completed': 1,
        'metadata_issue_summary': {'fields_unresolved': 0, 'records_incomplete': 0},
        'manifest': {'title': '', 'document_author': ''},
        'validation': {'valid': True, 'source_valid': True, 'metadata_valid': True},
        'status': 'ready',
        'stage': 'ready',
    }
    cb.PdfCorpusBuildManager._refresh_workflow_fields(build)
    readiness = build['publication_readiness']
    assert readiness['can_publish'] is False
    assert set(readiness['missing_document_fields']) == {'title', 'document_author'}
    assert any(item['code'] == 'required_document_metadata' for item in readiness['blockers'])


def test_adaptive_fast_mode_can_skip_repeatedly_low_yield_family_but_not_deep_or_explicit_rerun():
    class Repo:
        def get_build(self, _build_id):
            return {'llm_family_effectiveness': {'indexing': {'calls': 7, 'proposed_fields': 1}}}
    manager = object.__new__(cb.PdfCorpusBuildManager)
    manager.repo = Repo()
    skip, reason = manager._adaptive_family_should_skip('b1', 'indexing', {'enrichment_mode': 'fast'})
    assert skip is True and reason
    assert manager._adaptive_family_should_skip('b1', 'indexing', {'enrichment_mode': 'deep'})[0] is False
    assert manager._adaptive_family_should_skip('b1', 'indexing', {'enrichment_mode': 'fast', 'families': ['indexing']})[0] is False


def test_focus_view_has_history_queue_navigation_cleanup_and_revision_audit():
    focus = text('web/src/components/CorpusRecordFocusReview.vue')
    builder = text('web/src/components/PdfCorpusBuilder.vue')
    assert 'historyBack' in focus and 'historyForward' in focus
    assert 'previousRecord' in focus and 'nextRecord' in focus
    assert '<CorpusTextCleanupDialog' in focus
    assert '<CorpusRevisionHistory' in focus
    assert 'focusHistoryMove' in builder and 'focusQueueMove' in builder
    assert 'CorpusRevisionHistory :record="selectedRecord"' in builder


def test_lifecycle_and_storybook_cover_exception_resolution_and_french_layout():
    stepper = text('web/src/components/CorpusWorkflowStepper.vue')
    story = text('web/src/components/CorpusWorkflowStepper.stories.ts')
    cleanup_story = text('web/src/components/CorpusTextCleanupSummary.stories.ts')
    assert 'Source & configure' in stepper
    assert 'Build' in stepper
    assert 'Review' in stepper
    assert 'Initialize' not in stepper
    assert 'Segment' not in stepper
    assert 'Review' in story and 'Building' in story and 'ReadyToPublish' in story
    assert 'fr-CA' in story and 'fr-CA' in cleanup_story


def test_shared_review_surfaces_keep_wcag_basics_and_readable_type():
    for path in [
        'web/src/components/CorpusRecordFocusReview.vue',
        'web/src/components/CorpusRevisionHistory.vue',
        'web/src/components/CorpusTextCleanupSummary.vue',
        'web/src/components/CorpusLlmEffectivenessPanel.vue',
    ]:
        src = text(path)
        assert 'font-size:.8125rem' in src or 'font-size:.875rem' in src
    focus = text('web/src/components/CorpusRecordFocusReview.vue')
    assert ':focus-visible' in focus
    assert 'aria-label' in focus


def test_provider_payload_type_contract_from_0501_is_preserved_after_test_consolidation():
    builder = text('web/src/components/PdfCorpusBuilder.vue')
    assert 'function directProfilePayload(profileId:string): Record<string,unknown>|null{' in builder
    assert 'for(const key of ["provider","model","base_url","api_key","generation"])' in builder
