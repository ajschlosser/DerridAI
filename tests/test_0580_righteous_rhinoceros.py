from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def text(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_release_identity_0580():
    assert json.loads(text('web/package.json'))['version'] == '0.58.0'
    assert '0.58.0 — Righteous Rhinoceros' in text('README.md')
    assert 'APP_VERSION = "0.58.0"' in text('api/app/config.py')


def test_metadata_semantic_fields_have_correct_control_kinds():
    registry = text('web/src/domain/metadataFieldRegistry.ts')
    assert "field==='proposition_status'" in registry and "control:'enum'" in registry
    assert "field==='stance'" in registry
    assert "'asserted'" in registry and "'rejected'" in registry and "'criticized'" in registry
    assert "'affirm'" in registry and "'qualify'" in registry
    assert "field==='claim_scope'" in registry and "control:'combobox'" in registry
    assert "SPEAKER_FIELDS.includes(field)" in registry and "control:'combobox'" in registry


def test_confident_llm_values_are_preserved_as_explicit_field_proposals():
    backend = text('api/app/corpus_builder.py')
    editor = text('web/src/components/CorpusMetadataFieldEditor.vue')
    assert '"proposed_value": record.get(field)' in backend
    assert '"proposed_value": value' in backend
    assert 'confidence.value>0.65&&hasValue(status.proposed_value)' in editor
    assert "status.prefilled_candidate==='llm'" in editor
    assert 'Select from text' in editor
    # Alternate acquisition belongs after save/no-value controls.
    assert editor.index("save_field_value") < editor.index("select_from_text','Select from text")


def test_source_inspector_is_compact_and_full_viewer_is_shared():
    builder = text('web/src/components/PdfCorpusBuilder.vue')
    focus = text('web/src/components/CorpusRecordFocusReview.vue')
    summary = text('web/src/components/CorpusSourceSummary.vue')
    viewer = text('web/src/components/PdfEvidenceViewer.vue')
    assert 'CorpusSourceSummary' in builder and 'CorpusSourceSummary' in focus
    assert 'Open source viewer' in summary
    assert 'source-tool-section' in builder and 'focus-source-section' in focus
    assert 'Math.max(160' in viewer
    assert 'ResizeObserver' in viewer
    assert (ROOT/'web/src/components/CorpusSourceSummary.stories.ts').exists()


def test_document_structure_has_dirty_saved_feedback_and_mapping_summary():
    component = text('web/src/components/DocumentStructureConfigurator.vue')
    builder = text('web/src/components/PdfCorpusBuilder.vue')
    for token in ('Unsaved changes','Save document structure','Generated page mapping','Review mapping'):
        assert token in component
    assert ':saving="busy===\'document-layout\'"' in builder
    assert 'dirty=computed' in component
    assert 'mappedCount' in component and 'exceptionCount' in component


def test_combobox_is_viewport_clamped_and_high_layer():
    combo = text('web/src/components/ui/UiCombobox.vue')
    assert 'viewportWidth-width-margin' in combo
    assert 'z-index:2147483000' in combo
    assert '<Teleport to="body">' in combo


def test_storybook_covers_problem_states():
    field_story = text('web/src/components/CorpusMetadataFieldEditor.stories.ts')
    assert 'AutoPopulatedStance' in field_story
    assert 'AutoPopulatedPropositionStatus' in field_story
    assert 'NarrowOpenCombobox' in field_story
    assert (ROOT/'web/src/components/DocumentStructureConfigurator.stories.ts').exists()
    assert (ROOT/'web/src/components/SourceTranscriptionDialog.stories.ts').exists()
