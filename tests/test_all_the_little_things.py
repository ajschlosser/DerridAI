from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (ROOT / "web/src/legacy/runtime.js").read_text(encoding="utf-8")
MAIN = (ROOT / "api/app/main.py").read_text(encoding="utf-8")
JOBS = (ROOT / "api/app/jobs.py").read_text(encoding="utf-8")
SYSTEM_STORE = (ROOT / "api/app/system_store.py").read_text(encoding="utf-8")
USERS_VIEW = (ROOT / "web/src/views/UsersView.vue").read_text(encoding="utf-8")
LANGUAGES_VIEW = (ROOT / "web/src/views/LanguagesView.vue").read_text(encoding="utf-8")
APP_VUE = (ROOT / "web/src/App.vue").read_text(encoding="utf-8")
APP_ICON = (ROOT / "web/src/components/AppIcon.vue").read_text(encoding="utf-8")


def _load_content_filter():
    path = ROOT / "api/app/content_filter.py"
    spec = importlib.util.spec_from_file_location("derridai_content_filter_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_version_is_current_everywhere_primary():
    package = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    assert package["version"] == "0.35.12"
    assert 'version="0.35.12"' in MAIN
    assert "Corpus Viewer 0.35.12" in (ROOT / "web/index.html").read_text(encoding="utf-8")


def test_sidebar_uses_specific_users_and_language_icons():
    assert 'label:i18n.t("nav.users","Users"),icon:"users"' in APP_VUE
    assert 'label:i18n.t("language.manage","Manage languages"),icon:"language"' in APP_VUE
    assert "users:'" in APP_ICON
    assert "language:'" in APP_ICON


def test_dashboard_contains_requested_new_metrics_and_annotation_details():
    assert 'id:"record-share"' in RUNTIME
    assert 'id:"word-share"' in RUNTIME
    assert 'id:"annotations-14"' not in RUNTIME
    assert "dashboard-annotation-author" in RUNTIME
    assert "dashboard-annotation-pages" in RUNTIME
    assert "dashboard-record-pages" in RUNTIME


def test_inline_citation_uses_requested_author_year_colon_pages_format():
    # The implementation uses an ASCII hyphen for a page range specifically so
    # Derrida 1999, pp. 20-21 renders as exactly: (Derrida 1999: 20-21).
    assert "`${a}-${b}`" in RUNTIME
    assert "return `(${head}: ${page})`" in RUNTIME


def test_global_search_operators_are_field_type_aware():
    assert 'numericFilterFields=new Set(["page_start","page_end","year"' in RUNTIME
    assert 'collectionFilterFields=new Set(["topics","concepts"' in RUNTIME
    start = RUNTIME.index("function filterOpsForField")
    body = RUNTIME[start:start + 1600]
    assert 'numericFilterFields.has(field)' in body
    assert 'collectionFilterFields.has(field)' in body
    assert '"gte"' in body and '"lte"' in body


def test_research_defaults_and_model_autocomplete():
    assert "auto_grade: false" in RUNTIME
    assert "if(!selectedEvidenceCount)cfg.skip_retrieval=false" in RUNTIME
    assert 'list="rag-model-options"' in RUNTIME
    assert '<datalist id="rag-model-options">' in RUNTIME


def test_language_translation_is_a_background_job_with_clear_followup():
    assert 'task: "language_dictionary"' in (ROOT / "web/src/api/system.ts").read_text(encoding="utf-8")
    assert "registerExternalJob" in LANGUAGES_VIEW
    assert "Runs in the background" in LANGUAGES_VIEW
    assert "Track it in Operations" in LANGUAGES_VIEW
    assert "Translate & install" in LANGUAGES_VIEW
    assert 'body.task == "language_dictionary"' in JOBS
    # The worker delegates to the bounded validator and keeps the large translated
    # dictionary out of the job result packet.
    language_runner = JOBS[JOBS.index("def _run_language_dictionary"):JOBS.index("def _run(", JOBS.index("def _run_language_dictionary"))]
    assert "translate_english_dictionary(" in language_runner
    assert "**stats" in language_runner
    assert '"dictionary": clean' not in language_runner


def test_record_badges_use_robust_flattening_and_history_clear_is_modernized():
    assert "function flattenValueList" in RUNTIME
    assert "flattenValueList(values)" in RUNTIME
    assert "Clear search" in RUNTIME
    assert "Delete audit history" in RUNTIME


def test_openai_model_discovery_and_shared_ollama_endpoint_limit_are_implemented():
    llm = (ROOT / "api/app/llm.py").read_text(encoding="utf-8")
    assert 'client.get(f"{url}/models"' in llm
    assert "OpenAI-compatible profiles query GET /models" in RUNTIME
    assert "endpoint_limits" in SYSTEM_STORE
    assert 'if profile.get("type") != "ollama"' in SYSTEM_STORE
    assert 'profile["max_concurrent_requests"] = endpoint_limits.get' in SYSTEM_STORE
    assert "shared endpoint" in MAIN or "same normalized endpoint" in MAIN


def test_researcher_llm_access_is_integrated_into_main_profiles_ui():
    assert "ResearcherProviderProfileCard" not in USERS_VIEW
    assert 'data-profile-field="researcher_enabled"' in RUNTIME
    assert "provider-researcher-access" in RUNTIME
    assert "Researcher access" in RUNTIME


def test_researchers_can_read_shared_annotations_and_corpus_ui_is_unified():
    annotation_route = MAIN[MAIN.index('@app.get("/api/annotations")'):MAIN.index('@app.post("/api/annotations")')]
    assert "system_store.list_annotations()" in annotation_route
    assert "user_id=user.id" not in annotation_route
    assert "databaseResultsHtml({admin:false" in RUNTIME
    assert "databaseResultsHtml({admin:true" in RUNTIME
    assert 'const shared=await api("/api/annotations"' in RUNTIME
    assert "shared_annotation_id" in RUNTIME


def test_researcher_text_policy_detects_nested_and_obfuscated_language():
    content_filter = _load_content_filter()
    assert not content_filter.contains_disallowed_language("hospitality and différance")
    assert content_filter.contains_disallowed_language("f.u.c.k")
    assert content_filter.contains_disallowed_language("sh1t")
    assert content_filter.find_disallowed_path({"note": "clean", "tags": ["ok", "f.u.c.k"]}) == "input.tags[1]"
    assert "enforce_researcher_text" in MAIN
    assert "That language is not permitted for researcher accounts" in RUNTIME
    assert 'document.addEventListener("input",event=>filterResearcherInputElement(event.target),true)' in RUNTIME


def test_server_enforces_researcher_text_on_writable_and_search_surfaces():
    assert 'enforce_researcher_text({"quote": body.quote, "note": body.note, "tags": body.tags})' in MAIN
    assert 'enforce_researcher_text({"prompt": body.prompt, "instructions": body.instructions})' in MAIN
    assert 'enforce_researcher_text({"work": work, "filters": parsed_filters})' in MAIN
    assert 'enforce_researcher_text({"query": body.query, "where": body.where})' in MAIN
