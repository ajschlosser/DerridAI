from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
def text(path:str)->str:return (ROOT/path).read_text(encoding='utf-8')

def test_document_metadata_uses_shared_dialog_and_impact_summary():
    dialog=text('web/src/components/DocumentManifestDialog.vue')
    editor=text('web/src/components/DocumentManifestEditor.vue')
    assert 'UiDialog' in dialog
    assert 'affected-records' in dialog or 'affectedRecords' in dialog
    assert 'manifest_propagation_preview' in editor
    assert 'position:sticky' in editor
    assert 'grid-template-columns:repeat(2' in editor

def test_dialog_foundation_has_keyboard_and_focus_management():
    dialog=text('web/src/components/ui/UiDialog.vue')
    assert 'aria-modal="true"' in dialog
    assert 'event.key === "Escape"' in dialog
    assert 'event.key !== "Tab"' in dialog
    assert 'priorActive' in dialog
    assert 'focus-visible' in dialog

def test_review_workspace_uses_componentized_session_and_effectiveness_surfaces():
    builder=text('web/src/components/PdfCorpusBuilder.vue')
    assert '<CorpusReviewSessionBar' in builder
    assert '<CorpusLlmEffectivenessPanel' in builder
    assert 'class="llm-contribution"' not in builder
    assert 'class="review-session-bar"' not in builder

def test_new_storybook_components_have_french_stress_states():
    for path in [
        'web/src/components/ui/UiDialog.stories.ts',
        'web/src/components/CorpusReviewSessionBar.stories.ts',
        'web/src/components/CorpusLlmEffectivenessPanel.stories.ts',
    ]:
        story=text(path)
        assert 'fr-CA' in story

def test_new_locale_keys_exist_in_both_builtins():
    en=text('api/app/locales/en_us.py'); fr=text('api/app/locales/fr_ca.py')
    for key in [
        'pdf_corpus.document_defaults_title',
        'pdf_corpus.manifest_propagation_preview',
        'pdf_corpus.llm_effectiveness_title',
        'pdf_corpus.useful_fields_per_minute',
    ]:
        assert repr(key) in en
        assert repr(key) in fr

def test_review_session_bar_accepts_nullable_model_from_build_contract():
    component=text('web/src/components/CorpusReviewSessionBar.vue')
    assert 'model?:string|null' in component
