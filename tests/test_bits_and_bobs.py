from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (ROOT / "web/src/legacy/runtime.js").read_text(encoding="utf-8")
STYLE = (ROOT / "web/src/style.css").read_text(encoding="utf-8")
AUTH = (ROOT / "api/app/auth.py").read_text(encoding="utf-8")
MAIN = (ROOT / "api/app/main.py").read_text(encoding="utf-8")
ROUTER = (ROOT / "web/src/router/index.ts").read_text(encoding="utf-8")
APP = (ROOT / "web/src/App.vue").read_text(encoding="utf-8")
ROLES = (ROOT / "web/src/views/RolesView.vue").read_text(encoding="utf-8")


def _load_content_filter():
    path = ROOT / "api/app/content_filter.py"
    spec = importlib.util.spec_from_file_location("derridai_content_filter_bits", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_version_03013():
    package = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    assert package["version"] == "0.36.4"
    assert 'version="0.36.4"' in MAIN
    assert "Corpus Viewer 0.36.4" in (ROOT / "web/index.html").read_text(encoding="utf-8")


def test_dashboard_background_ops_fixed_open_and_annotation_graph_removed():
    assert 'id="operationsPanel" data-no-collapse="true"' in RUNTIME
    assert 'matches("[data-no-collapse=true]")' in RUNTIME
    assert 'id:"annotations-14"' not in RUNTIME
    assert 'id:"record-share"' in RUNTIME
    assert 'id:"word-share"' in RUNTIME


def test_dashboard_researcher_activity_and_appearance_are_permission_aware():
    assert 'hasCapability("activity.read")' in RUNTIME
    assert 'hasCapability("annotations.read")' in RUNTIME
    assert 'hasCapability("rag.jobs.own")' in RUNTIME
    assert "dashboard-appearance-card" in RUNTIME
    assert 'data-dashboard-theme' in RUNTIME
    assert 'hasCapability("appearance.manage")' in RUNTIME


def test_roles_page_and_permission_contract_exist():
    assert "CAPABILITY_CATALOG" in AUTH
    assert "role_permissions" in AUTH
    assert "ADMIN_ONLY_CAPABILITIES" in AUTH
    assert '@app.get("/api/auth/roles")' in MAIN
    assert '@app.put("/api/auth/roles/{role}/permissions")' in MAIN
    assert 'path: "/roles"' in ROUTER
    assert 'capability: "page.roles"' in ROUTER
    assert "RolePermissionMatrix" in ROLES
    assert 'nav.roles","Roles & permissions"' in APP


def test_every_legacy_page_has_a_capability_route_guard():
    for capability in (
        "page.dashboard", "page.records", "page.record", "page.works", "page.search",
        "page.annotations", "page.pdf", "page.compare", "page.vector", "page.research",
        "page.faq", "page.response_cache", "page.providers", "page.settings",
    ):
        assert capability in RUNTIME
        assert capability in ROUTER
    assert "canAccessPage(view)" in RUNTIME
    assert "auth.can(capability)" in ROUTER


def test_collection_wizard_summary_precedes_work_list_and_is_aligned():
    line = next(line for line in RUNTIME.splitlines() if "wizard-sync-summary" in line and "wizard-work-list" in line)
    assert line.index("wizard-sync-summary") < line.index("wizard-work-list")
    assert "grid-template-columns:repeat(2,minmax(140px,190px))" in STYLE


def test_provider_researcher_access_uses_dedicated_switch_card():
    assert "provider-researcher-access" in RUNTIME
    assert "provider-access-switch" in RUNTIME
    assert "provider-access-switch-track" in STYLE
    assert "Allow researcher accounts to use this profile" in RUNTIME


def test_record_badges_size_to_text_without_ellipsis():
    assert "width:fit-content !important" in STYLE
    assert "text-overflow:clip !important" in STYLE
    assert "overflow:visible !important" in STYLE


def test_research_progressive_disclosure_and_primary_run_bar():
    assert "research-context-bar" in RUNTIME
    assert "research-settings-drawer" in RUNTIME
    assert "research-generation-advanced" in RUNTIME
    assert "research-run-bar" in RUNTIME
    assert "Advanced generation parameters" in RUNTIME


def test_researcher_annotations_are_scoped_to_active_store_and_works():
    route = MAIN[MAIN.index('@app.get("/api/annotations")'):MAIN.index('@app.post("/api/annotations")')]
    assert 'Query(default=None, alias="store")' in route
    assert "accessible_works" in route
    assert "item_store not in accessible_works" in route
    assert "serverAnnotationsStore" in RUNTIME
    assert '?store=${encodeURIComponent(storeName)}' in RUNTIME


def test_researcher_record_keyword_search_has_casefold_fallback():
    chroma = (ROOT / "api/app/chroma_store.py").read_text(encoding="utf-8")
    assert "where_document" in chroma
    assert "casefold" in chroma
    assert "n_results * 50" in chroma and "10000" in chroma


def test_content_filter_avoids_name_and_substring_false_positives():
    content_filter = _load_content_filter()
    assert not content_filter.contains_disallowed_language("Dick Higgins discusses intermedia.")
    assert not content_filter.contains_disallowed_language("Dickens and Dickinson are authors.")
    assert not content_filter.contains_disallowed_language("The British term fag can mean cigarette.")
    assert content_filter.contains_disallowed_language("you dick")
    assert content_filter.contains_disallowed_language("what the damn")
    assert content_filter.contains_disallowed_language("f.u.c.k")


def test_storybook_expands_with_role_permission_matrix():
    story = ROOT / "web/src/stories/RolePermissionMatrix.stories.ts"
    assert story.exists()
    assert "RolePermissionMatrix" in story.read_text(encoding="utf-8")


def test_new_ui_has_focus_and_responsive_accessibility_rules():
    assert "focus-visible" in STYLE
    assert "aria-label=\"Researcher access\"" in RUNTIME
    assert 'role="radiogroup"' in RUNTIME or "dashboard-theme-options" in RUNTIME
    assert "@media(max-width:640px)" in STYLE
