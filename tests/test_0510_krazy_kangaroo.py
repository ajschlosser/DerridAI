from pathlib import Path

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



def test_review_session_bar_accepts_nullable_model_from_build_contract():
    component=text('web/src/components/CorpusReviewSessionBar.vue')
    assert 'model?:string|null' in component
