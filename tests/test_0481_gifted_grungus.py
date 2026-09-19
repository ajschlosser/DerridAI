from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
def text(path): return (ROOT/path).read_text(encoding="utf-8")

def test_release_identity():
    assert json.loads(text("web/package.json"))["version"]=="0.57.6"
    assert 'APP_VERSION = "0.57.6"' in text("api/app/config.py")
    assert '0.57.6 — Quippy Quokka' in text("README.md")

def test_source_issue_is_not_duplicated_in_record_and_source_panel():
    ui=text("web/src/components/PdfCorpusBuilder.vue")
    assert ui.count("<CorpusSourceIssuePanel") == 1

def test_text_review_has_explicit_confirmation_and_sticky_actions():
    ui=text("web/src/components/PdfCorpusBuilder.vue")
    backend=text("api/app/corpus_builder.py")
    assert "markTextReviewed" in ui
    assert "save_and_mark_reviewed" in ui
    assert "position:sticky;bottom:0" in ui
    assert 'target["text_review_status"] = "human_reviewed"' in backend
    assert '"__text_reviewed__"' in backend

def test_metadata_proposals_have_family_assessments_and_pending_feedback():
    backend=text("api/app/corpus_builder.py")
    panel=text("web/src/components/CorpusMetadataResolutionPanel.vue")
    assert backend.count("field_assessments: dict[str, RecordFieldAssessmentModel]") >= 3
    assert "metadata_enrichment_pending" in panel
    field=text('web/src/components/CorpusMetadataFieldEditor.vue')
    assert "llm_suggestion_prefilled" in field

def test_bulk_editor_is_opaque_and_supports_enum_and_existing_value_autocomplete():
    bulk=text("web/src/components/CorpusBulkMetadataEditor.vue")
    assert "z-index:30000" in bulk
    assert "backdrop-filter:blur(8px)" in bulk
    assert "datalist" in bulk
    assert "regionTypes" in bulk and "discourseRoles" in bulk
    assert "suggestions" in bulk

def test_initialization_modal_sits_above_global_operation_chrome():
    init=text("web/src/components/CorpusInitializationDialog.vue")
    assert "z-index:30000" in init
    assert "backdrop-filter:blur(8px)" in init
