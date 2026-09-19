from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (ROOT / "web/src/runtime/runtime.js").read_text(encoding="utf-8")
SEARCH = (ROOT / "web/src/views/SearchView.vue").read_text(encoding="utf-8")
ROUTER = (ROOT / "web/src/router/index.ts").read_text(encoding="utf-8")
STYLE = (ROOT / "web/src/style.css").read_text(encoding="utf-8")
SYSTEM = ((ROOT / "api/app/system_store.py").read_text(encoding="utf-8") + "\n" + (ROOT / "api/app/locales/en_us.py").read_text(encoding="utf-8") + "\n" + (ROOT / "api/app/locales/fr_ca.py").read_text(encoding="utf-8"))
README = (ROOT / "README.md").read_text(encoding="utf-8")
MAIN = (ROOT / "api/app/main.py").read_text(encoding="utf-8")


def test_03610_release_identity():
    package = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    assert package["version"] == "0.49.0"
    assert 'version="0.49.0"' in MAIN
    assert '"app_version": "0.49.0"' in MAIN
    assert "# DerridAI Corpus Viewer 0.49.0" in README
    assert "0.36.10 — In Search of Lost Time" in README


def test_search_is_a_native_vue_workspace():
    assert 'import SearchView from "../views/SearchView.vue"' in ROUTER
    assert 'path: "/search"' in ROUTER and 'component: SearchView' in ROUTER and 'vueNative: true' in ROUTER
    assert "SearchWorkspaceHeader" in SEARCH
    assert "SearchFacetPanel" in SEARCH
    assert "SearchSelectionBar" in SEARCH
    assert 'class="search-command-surface"' in SEARCH


def test_search_scope_methods_facets_and_advanced_filters_are_separated():
    assert 'search.loaded_records' in SEARCH
    assert 'search.corpus_database' in SEARCH
    assert "['similarity','search.method_similarity','Similarity']" in SEARCH
    assert "['mmr','search.method_mmr','MMR']" in SEARCH
    assert "['filter','search.method_filter','Filters only']" in SEARCH
    assert 'class="search-advanced-filter-builder"' in SEARCH
    assert 'filter_suggestions' in (ROOT / "web/src/types/search.ts").read_text(encoding="utf-8")
    assert 'const SEARCH_FACET_FIELDS=' in RUNTIME
    assert 'buildSearchFacets' in RUNTIME
    assert 'searchSuggestions' in RUNTIME


def test_search_state_is_shareable_and_saved_views_reuse_share_url():
    assert 'sf:state.searchFacetFilters||{}' in RUNTIME
    assert 'ao:Boolean(state.globalAdvancedOpen)' in RUNTIME
    assert 'function getSearchShareHref()' in RUNTIME
    assert 'function restoreSearchViewFromHref' in RUNTIME
    assert 'derridai.search.savedViews.v1' in SEARCH
    assert 'derridai.search.recent.v1' in SEARCH
    assert 'runtime.getSearchShareHref()' in SEARCH


def test_search_result_workspace_has_contextual_actions_and_explanations():
    assert 'v-if="snapshot.selection_count"' in SEARCH
    assert 'search.why_result' in SEARCH
    assert 'similarityPercent(result)' in SEARCH
    assert 'result.evidence_available' in SEARCH
    assert '<CitationMenu' in SEARCH
    assert "v-if=\"databaseMode&&snapshot.layout!=='cards'\"" in SEARCH


def test_search_table_is_scrollable_sticky_resizable_and_readable():
    assert '.search-table-scroll{max-width:100%;overflow:auto' in STYLE
    assert '.search-results-table th{position:sticky' in STYLE
    assert '.search-actions-column{position:sticky!important;right:0' in STYLE
    assert '.search-results-table .sticky-status{position:sticky' in STYLE
    assert '.search-column-resizer{' in STYLE
    assert '.search-results-table.roomy .search-text-cell{font-size:14.5px' in STYLE
    assert 'startResize' in SEARCH


def test_search_missing_database_uses_creation_flow():
    assert 'const mustCreateDatabase=!next.has_database&&(next.scope==="database"||!next.has_loaded_records)' in SEARCH
    assert 'runtime.openDatabaseCreationFromResearch()' in SEARCH
    assert 'if(!stores.length){if(canAccessPage("vector"))openDatabaseCreationFromResearch()' in RUNTIME


def test_semantic_search_never_exposes_contains_metadata_operator():
    assert "const allowed=snapshot.value?.method==='filter'?['eq','has']:['eq']" in SEARCH
    assert 'if(method!=="filter")' in RUNTIME
    assert 'Object.prototype.hasOwnProperty.call(value,"$contains")' in RUNTIME
    assert 'function safeDbSearchWhere(method=state.dbSearchMethod)' in RUNTIME
    assert 'const safeWhere=safeDbSearchWhere(method);state.dbSearchWhere=safeWhere' in RUNTIME
    assert SYSTEM.count(repr("search.contains_filter_removed")) >= 2


def test_search_components_have_storybook_coverage():
    for rel in (
        "web/src/components/search/SearchWorkspaceHeader.stories.ts",
        "web/src/components/search/SearchFacetPanel.stories.ts",
        "web/src/components/search/SearchSelectionBar.stories.ts",
    ):
        assert (ROOT / rel).exists()


def test_new_search_strings_are_bilingual():
    for key in (
        "search.kicker",
        "search.loaded_records",
        "search.corpus_database",
        "search.advanced_filters",
        "search.saved_views",
        "search.recent_searches",
        "search.why_result",
        "search.layout_comfortable",
        "search.semantic_match",
        "search.results_table_scroll",
    ):
        assert SYSTEM.count(repr(key)) >= 2
