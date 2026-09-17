from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (ROOT / "web/src/legacy/runtime.js").read_text(encoding="utf-8")
STYLE = (ROOT / "web/src/style.css").read_text(encoding="utf-8")
SYSTEM = (ROOT / "api/app/system_store.py").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
I18N = (ROOT / "web/src/stores/i18n.ts").read_text(encoding="utf-8")
LANGUAGES = (ROOT / "web/src/views/LanguagesView.vue").read_text(encoding="utf-8")
INSPECTOR = (ROOT / "web/src/components/record/RecordInspector.vue").read_text(encoding="utf-8")
EMPTY = (ROOT / "web/src/components/AccessibleEmptyState.vue").read_text(encoding="utf-8")
FAQ = (ROOT / "web/src/views/ResponseFaqView.vue").read_text(encoding="utf-8")


def test_0363_release_identity():
    assert "0.36.3 — All The Little Things" in README
    assert "# DerridAI Corpus Viewer 0.40.20" in README


def test_export_still_has_shared_download_blob_support_for_subset_exports():
    assert 'function downloadBlob' in RUNTIME
    assert 'downloadBlob(blob,name)' in RUNTIME


def test_scroll_regions_own_wheel_input_and_do_not_scroll_background():
    assert 'body:has(dialog[open]){overflow:hidden}' in STYLE
    assert '.mixed-values-dialog[open]{display:grid;grid-template-rows:auto minmax(0,1fr) auto}' in STYLE
    assert '.mixed-values-body{min-height:0' in STYLE
    assert 'overflow:auto' in STYLE[STYLE.index('.mixed-values-body{'):STYLE.index('.mixed-values-list{')]
    assert 'overscroll-behavior:auto' in INSPECTOR


def test_record_search_layout_cleanup_and_db_evidence_path():
    assert 'clamp(255px,29.75vw,425px)' in STYLE
    assert 'searchResultLayout("traditional")!=="cards"' in RUNTIME
    assert 'function workspaceDbEvidenceTarget' in RUNTIME
    assert 'toggleDbEvidence(dbTarget.collection,dbTarget.id,record)' in RUNTIME
    assert 'storePresenceIds' in RUNTIME


def test_record_inspector_has_page_context():
    assert 'const pageSpan=computed' in INSPECTOR
    assert "'region_author','__pages','primary_text'" in INSPECTOR
    assert "i18n.t('record.page','Page')" in INSPECTOR


def test_subset_builder_autocomplete_is_source_scoped_and_skips_large_text():
    assert 'subsetAutocompleteExcluded=new Set(["text","extracted_text","extractedText","raw_text","ocr_text"])' in RUNTIME
    assert 'class="subset-value-options"' in RUNTIME
    assert 'for(const {record} of selectedRows())' in RUNTIME
    assert 'refreshSubsetSuggestions' in RUNTIME


def test_language_updates_propagate_without_refresh():
    assert 'derridai:languages-changed' in I18N
    assert 'refreshLanguagesFromEvent' in I18N
    assert 'derridai:languages-changed' in LANGUAGES
    assert 'job.status==="completed"&&job.type==="llm_tool"&&(job.tool||job.mode)==="language_dictionary"' in RUNTIME


def test_annotations_page_supports_permission_aware_local_and_shared_delete():
    assert 'canDeleteServer=item.server&&' in RUNTIME
    assert 'canDeleteLocal=!item.server&&canUse("editLocalRecords")' in RUNTIME
    assert 'data-delete-local-annotation' in RUNTIME
    assert '{source:"annotation-delete"}' in RUNTIME
    assert 'data-delete-server-annotation' in RUNTIME


def test_response_faq_neutral_empty_state_and_storybook_variant():
    assert 'iconTone?:"accent"|"neutral"' in EMPTY
    assert 'icon-tone="neutral"' in FAQ
    story = (ROOT / "web/src/components/AccessibleEmptyState.stories.ts").read_text(encoding="utf-8")
    assert 'NeutralIcon' in story
    assert 'iconTone: "neutral"' in story


def test_new_strings_are_bilingual():
    for key in (
        "subset.autocomplete_count",
        "subset.autocomplete_large_field",
        "records.columns",
        "record.page",
        "annotations.remove_local_help",
    ):
        assert SYSTEM.count(f'"{key}"') >= 2
