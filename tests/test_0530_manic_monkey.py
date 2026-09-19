from pathlib import Path
import json
import sys
import types

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules['chromadb'] = types.SimpleNamespace()

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'api'))
from app import corpus_builder as cb
from app.locales.en_us import EN_US
from app.locales.fr_ca import FR_CA

def text(path:str)->str:return (ROOT/path).read_text(encoding='utf-8')

def test_release_identity_and_i18n_parity():
    assert json.loads(text('web/package.json'))['version']=='0.55.0'
    assert 'APP_VERSION = "0.55.0"' in text('api/app/config.py')
    assert 'version="0.55.0"' in text('api/app/main.py')
    assert '0.55.0 — Outrageous Orangutan' in text('README.md')
    assert set(EN_US)==set(FR_CA)
    for key in ['pdf_corpus.llm_touchup','pdf_corpus.preview_jsonl','pdf_corpus.editorial_memory_title','pdf_corpus.confidence_calibration']:
        assert key in EN_US and key in FR_CA and EN_US[key]!=FR_CA[key]

def test_cleanup_repairs_multi_line_prose_and_ocr_without_flattening_poetry():
    prose='This sentence is artificially wrapped across\nseveral physical PDF lines in the middle\nof one continuous thought and contains ﬁ ligature.\n\nNext paragraph.'
    cleaned,report=cb._clean_text_value(prose,{'paragraph_lines','ocr_artifacts','empty_lines'},set())
    assert 'wrapped across several physical PDF lines in the middle of one continuous thought' in cleaned
    assert 'fi ligature' in cleaned
    assert '\n\nNext paragraph.' in cleaned
    assert report['changed'] is True
    verse='“First short line\nSecond short line\nThird short line\nFourth short line”'
    verse_cleaned,_=cb._clean_text_value(verse,{'paragraph_lines'},set())
    assert verse_cleaned==verse

def test_rejected_records_are_not_publication_metadata_blockers_and_all_rejected_is_terminal():
    build={'record_count':3,'accepted_count':2,'rejected_count':1,'needs_review_count':0,'boundary_review_count':0,'source_problem_count':0,'metadata_total':3,'metadata_completed':3,'metadata_issue_summary':{'records_incomplete':0,'fields_unresolved':0},'manifest':{'title':'Book','document_author':'Author'},'validation':{'valid':True,'source_valid':True,'metadata_valid':True},'status':'awaiting_review','stage':'review'}
    cb.PdfCorpusBuildManager._refresh_workflow_fields(build)
    assert build['publication_readiness']['can_publish'] is True
    assert not any(row['code']=='rejected_records' for row in build['publication_readiness']['blockers'])
    build.update({'accepted_count':0,'rejected_count':3})
    cb.PdfCorpusBuildManager._refresh_workflow_fields(build)
    assert build['publication_readiness']['no_publishable_records'] is True
    assert build['publication_readiness']['next_action']=='no_publishable_records'

def test_review_workspace_has_non_destructive_drafts_json_preview_touchup_and_pinned_refresh():
    builder=text('web/src/components/PdfCorpusBuilder.vue')
    assert 'textDraftKey' in builder and 'metadataDraftKey' in builder
    assert 'preserveDraft' in builder and 'selectedRecord.value&&selectedRecordId.value===wanted' in builder
    assert '<CorpusJsonlPreviewDialog' in builder
    assert '<CorpusLlmTextTouchupDialog' in builder
    assert '@preview-jsonl="openJsonlPreview"' in builder
    assert '@llm-touchup=' in builder

def test_llm_values_prefill_and_calibration_does_not_mark_initial_value_dirty():
    editor=text('web/src/components/CorpusMetadataFieldEditor.vue')
    assert 'watch(isLlm,value=>{if(value)editing.value=true}' in editor
    assert 'draft.value=editableValue()' in editor
    assert 'watch(draft' not in editor
    assert 'calibratedAcceptance' in editor
    assert "@change=\"markDirty\"" in editor or '@input="markDirty"' in editor

def test_primary_text_determinism_is_semantically_corroborated():
    src=text('api/app/corpus_builder.py')
    assert 'tasks.append(all_task_specs["discourse"])' in src
    assert 'llm_corroborates' in src
    assert 'deterministic_llm_disagreement' in src

def test_editorial_memory_is_inspectable_resettable_and_storybooked():
    main=text('api/app/main.py'); api=text('web/src/api/pdfCorpus.ts'); builder=text('web/src/components/PdfCorpusBuilder.vue')
    assert '/editorial-memory' in main
    assert 'editorialMemory:' in api and 'resetEditorialMemory:' in api
    assert '<CorpusEditorialMemoryDialog' in builder
    for path in ['web/src/components/CorpusEditorialMemoryDialog.stories.ts','web/src/components/CorpusJsonlPreviewDialog.stories.ts','web/src/components/CorpusLlmTextTouchupDialog.stories.ts']:
        assert 'fr-CA' in text(path)

def test_focus_view_has_back_forward_queue_navigation_and_same_cleanup_touchup_tools():
    focus=text('web/src/components/CorpusRecordFocusReview.vue')
    assert "emit('historyBack')" in focus and "emit('historyForward')" in focus
    assert "emit('previousRecord')" in focus and "emit('nextRecord')" in focus
    assert '<CorpusTextCleanupDialog' in focus
    assert "emit('llmTouchup',textDraft)" in focus
    assert 'documentTerms' in focus

def test_wcag_dialog_and_focus_surfaces_have_keyboard_and_readable_text_contracts():
    for path in ['web/src/components/ui/UiDialog.vue','web/src/components/CorpusLlmTextTouchupDialog.vue','web/src/components/CorpusEditorialMemoryDialog.vue','web/src/components/CorpusJsonlPreviewDialog.vue']:
        src=text(path)
        assert 'role="dialog"' in src or 'UiDialog' in src
        assert '.8125rem' in src or '.875rem' in src
    assert ':focus-visible' in text('web/src/components/CorpusMetadataFieldEditor.vue')

def test_finish_workspace_routes_current_backend_review_state_to_an_actionable_queue():
    finish=text('web/src/components/CorpusFinishWorkspace.vue')
    assert "next.value==='review_records'" in finish
    assert "emit('reviewRecords')" in finish
    assert "'review_records','resolve_document_metadata','resolve_validation','publish'" in finish
    assert "next.value==='resolve_rejections'" not in finish


def test_effectiveness_story_covers_calibration_and_mixed_model_profile_metrics():
    story=text('web/src/components/CorpusLlmEffectivenessPanel.stories.ts')
    assert 'confidenceCalibration' in story
    assert 'modelEffectiveness' in story
    assert 'fr-CA' in story
