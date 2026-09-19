from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (ROOT / "web/src/runtime/runtime.js").read_text(encoding="utf-8")
STYLE = (ROOT / "web/src/style.css").read_text(encoding="utf-8")
SYSTEM = ((ROOT / "api/app/system_store.py").read_text(encoding="utf-8") + "\n" + (ROOT / "api/app/locales/en_us.py").read_text(encoding="utf-8") + "\n" + (ROOT / "api/app/locales/fr_ca.py").read_text(encoding="utf-8"))


def test_0362_release_identity_and_docs():
    assert (ROOT / "docs/SHAREABLE_STATE_AND_DATA_MODEL_0.36.2.md").exists()


def test_records_table_defaults_and_horizontal_overflow():
    assert 'list:["__db_status","work","page_start","needs_review","text"]' in RUNTIME
    assert 'class="card tablewrap records-table-wrap"' in RUNTIME
    assert ".records-table-wrap" in STYLE
    assert "overflow-x:auto" in STYLE
    assert ".page-start-cell" in STYLE
    assert ".extracted-text-cell" in STYLE


def test_shareable_url_state_covers_primary_views_and_stable_jsonl_identity():
    assert "async function stableJsonlFileIdentity" in RUNTIME
    assert 'crypto.subtle.digest("SHA-256"' in RUNTIME
    for view in ("list", "global", "works", "annotations", "home", "record", "faq"):
        assert f'view==="{view}"' in RUNTIME
    assert "requestedUrlState" in RUNTIME
    assert "applyCompressedTableUrlState(decompressUrlState(requestedUrlState),state.view)" in RUNTIME


def test_works_mixed_metadata_inspector_and_filtered_counts():
    assert "function openMixedWorkValuesDialog" in RUNTIME
    assert "function uniqueWorkValues" in RUNTIME
    assert "data-work-records" in RUNTIME
    assert "data-work-review" in RUNTIME
    assert 'field:"needs_review",op:"eq",value:"true"' in RUNTIME


def test_single_work_insights_and_storybook_component():
    assert "function workInsightMetrics" in RUNTIME
    for field in ("persons", "concepts", "topics", "target", "discourse_role"):
        assert f'field:"{field}"' in RUNTIME
    assert "singleLoadedWork?workInsightMetrics" in RUNTIME
    assert not (ROOT / "web/src/components/WorkInsightsPanel.vue").exists()
    assert not (ROOT / "web/src/components/WorkInsightsPanel.stories.ts").exists()


def test_llm_review_uses_central_provider_connection_settings():
    assert 'id="llmManageProvider"' in RUNTIME
    # The review workspace no longer duplicates endpoint/API-key form fields.
    assert 'id="openaiApiKey"' not in RUNTIME
    assert 'id="openaiBaseUrl"' not in RUNTIME
    assert 'id="ollamaBaseUrl"' not in RUNTIME
    assert 'const base_url=profile?.base_url||"";' in RUNTIME
    assert 'const api_key=provider==="openai"?(profile?.api_key||""):null;' in RUNTIME


def test_new_ux_strings_exist_in_both_builtin_dictionaries():
    for key in (
        "records.table_scroll_label",
        "records.open_shared_workspace",
        "works.metadata_variants",
        "works.work_insights",
        "dashboard.top_persons_work",
        "dashboard.top_discourse_targets_work",
        "dashboard.discourse_roles_share_work",
        "llm.connection_from_profile",
    ):
        assert SYSTEM.count(repr(key)) >= 2
