from pathlib import Path
import json
import sys
import types

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules['chromadb']=types.SimpleNamespace()

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'api'))
from app import corpus_builder as cb
from app.locales.en_us import EN_US
from app.locales.fr_ca import FR_CA

def text(path:str)->str: return (ROOT/path).read_text(encoding='utf-8')

def test_release_identity_and_locale_parity():
    assert json.loads(text('web/package.json'))['version']=='0.49.0'
    assert 'APP_VERSION = "0.49.0"' in text('api/app/config.py')
    assert '0.49.0 — Hungry Hippo' in text('README.md')
    assert set(EN_US)==set(FR_CA)
    for key in ['pdf_corpus.text_cleanup_title','pdf_corpus.llm_suggestion_prefilled','pdf_corpus.constraint_non_primary_region','pdf_corpus.accept_all_suggestions']:
        assert key in EN_US and key in FR_CA
        assert EN_US[key] != FR_CA[key]

def test_llm_suggestions_prefill_independent_of_confidence_threshold():
    field=text('web/src/components/CorpusMetadataFieldEditor.vue')
    panel=text('web/src/components/CorpusMetadataResolutionPanel.vue')
    assert 'const value=props.constraint?.value ?? props.value' in field
    assert 'PROPOSAL_PREFILL_CONFIDENCE' not in field
    assert 'llm_suggestion_prefilled' in field
    assert 'llmSuggestions' in panel and 'resolveMany' in panel

def test_metadata_constraints_are_central_and_hard():
    for region in ['front_matter','back_matter','bibliography','index','paratext']:
        record={'region_type':region,'primary_text':True,'metadata_field_status':{}}
        changed=cb.apply_metadata_constraints(record)
        assert record['primary_text'] is False
        assert changed and changed[0]['field']=='primary_text'
        assert record['metadata_field_status']['primary_text']['method']=='region_type_consistency'
    record={'region_type':'main_text','primary_text':False,'metadata_field_status':{}}
    cb.apply_metadata_constraints(record)
    assert record['primary_text'] is True

def test_text_cleanup_is_reversible_review_layer_and_storybook_componentized():
    builder=text('web/src/components/PdfCorpusBuilder.vue')
    cleanup=text('web/src/components/CorpusTextCleanupDialog.vue')
    util=text('web/src/domain/textCleanup.ts')
    assert 'CorpusTextCleanupDialog' in builder
    assert 'source_extracted_text' in text('api/app/corpus_builder.py')
    assert 'page_numbers' in util and 'repeated_short_lines' in util and 'line_hyphenation' in util
    assert 'role="dialog" aria-modal="true"' in cleanup
    assert 'Text Cleanup' in text('web/src/components/CorpusTextCleanupDialog.stories.ts')
    assert 'Metadata Field' in text('web/src/components/CorpusMetadataFieldEditor.stories.ts')

def test_new_components_keep_wcag_basics():
    for path in ['web/src/components/CorpusTextCleanupDialog.vue','web/src/components/CorpusMetadataFieldEditor.vue']:
        src=text(path)
        assert ':focus-visible' in src
        assert 'font-size:.8125rem' in src or 'font-size:.875rem' in src
    cleanup=text('web/src/components/CorpusTextCleanupDialog.vue')
    assert 'aria-labelledby="cleanup-title"' in cleanup
    assert 'aria-live="polite"' in cleanup
