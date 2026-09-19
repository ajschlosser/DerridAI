from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def text(path): return (ROOT/path).read_text(encoding='utf-8')

def test_quiet_camel_release_and_metadata_field_typing():
    assert '0.59.0 — Serious Sandpipers' in text('README.md')
    registry=text('web/src/domain/metadataFieldRegistry.ts')
    assert "field==='proposition_status'" in registry and "field==='stance'" in registry
    assert "field==='claim_scope'" in registry and "control:'combobox'" in registry
    assert "SPEAKER_FIELDS.includes(field)" in registry and "control:'combobox'" in registry
    panel=text('web/src/components/CorpusMetadataResolutionPanel.vue')
    assert 'metadataFieldSpec' in panel
    assert "['region_author','speaker','position_holder'" not in panel

def test_interactive_llm_provider_is_not_replaced_by_build_runtime():
    src=text('api/app/corpus_builder.py')
    assert 'def _interactive_llm_request' in src
    assert 'active_request = self._interactive_llm_request(build_id, request or None)' in src
    assert 'request = self._interactive_llm_request(build_id, request_override)' in src
    assert '_interactive_provider_override' in src

def test_conflicts_keep_both_candidates_and_prefill_llm():
    src=text('api/app/corpus_builder.py')
    assert 'existing_status["deterministic_value"] = deterministic_value' in src
    assert 'existing_status["llm_value"] = value' in src
    assert 'record[key] = value' in src
    editor=text('web/src/components/CorpusMetadataFieldEditor.vue')
    assert "status?.reason_code==='deterministic_llm_disagreement'" in editor

def test_llm_execution_supports_model_override_and_touchup_redundancy_warning():
    control=text('web/src/components/LlmExecutionControl.vue')
    assert 'modelOverride' in control and 'researcherProviderStatus' in control
    assert 'ollama_concurrency_warning' in control
    touchup=text('web/src/components/CorpusLlmTextTouchupDialog.vue')
    assert 'touchup_redundant_instruction' in touchup
    assert 'touchup_builtin_policy' in touchup
