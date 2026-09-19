from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (ROOT / "web/src/runtime/runtime.js").read_text(encoding="utf-8")
STYLE = (ROOT / "web/src/style.css").read_text(encoding="utf-8")
APP = (ROOT / "web/src/App.vue").read_text(encoding="utf-8")
RESEARCH = (ROOT / "web/src/views/ResearchView.vue").read_text(encoding="utf-8")
ROLES = (ROOT / "web/src/views/RolesView.vue").read_text(encoding="utf-8")
USERS = (ROOT / "web/src/views/UsersView.vue").read_text(encoding="utf-8")
AUTH_API = (ROOT / "web/src/api/auth.ts").read_text(encoding="utf-8")
MAIN = (ROOT / "api/app/main.py").read_text(encoding="utf-8")


def test_release_version_is_0313():
    package = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    assert package["version"] == "0.57.6"
    assert 'version="0.57.6"' in MAIN
    assert "Corpus Viewer 0.57.6" in (ROOT / "web/index.html").read_text(encoding="utf-8")


def test_sidebar_tooltips_escape_sidebar_and_stack_above_workspace():
    assert ".shell-sidebar{z-index:500!important;overflow:visible!important}" in STYLE
    assert "z-index:20000!important" in STYLE
    assert ".shell-primary-nav,.shell-primary-nav .nav-tooltip-wrap{overflow:visible!important}" in STYLE


def test_research_no_database_redirects_instead_of_disabling_navigation():
    # Neither navigation layer rejects Research using cached DB state. The
    # native Research view refreshes stores and owns the helpful redirect.
    assert 'if(view==="rag"&&!hasCorpusDb())' not in RUNTIME
    assert 'authoritative store refresh on entry' in RUNTIME
    # The shell must not trust its cached DB snapshot; ResearchView refreshes the
    # authoritative collection list and redirects only when that refreshed list is empty.
    assert 'if(view==="rag"&&!s.value.hasCorpusDb)' not in APP
    assert 'getResearchWorkspaceSnapshot({refresh})' in RESEARCH
    assert 'runtime.openDatabaseCreationFromResearch?.()' in RESEARCH
    assert 'vectorAutoCreateRequested' in RUNTIME
    assert 'openCollectionCreationWizard' in RUNTIME


def test_research_request_normalizes_numeric_fields_before_post():
    assert "function finiteResearchNumber" in RUNTIME
    assert "function sanitizeResearchGeneration" in RUNTIME
    assert "function normalizedResearchConfig" in RUNTIME
    assert "const cfg=normalizedResearchConfig(updateResearchConfig(input.config||{}));" in RUNTIME
    assert "const generation=sanitizeResearchGeneration" in RUNTIME
    assert "auto_grade_generation:gradeConfig?.ollama?sanitizeResearchGeneration" in RUNTIME



def test_rag_schema_rejects_blank_numeric_values():
    import sys
    import pytest
    from pydantic import ValidationError
    if str(ROOT / "api") not in sys.path:
        sys.path.insert(0, str(ROOT / "api"))
    from app.models import RAGRunRequest

    with pytest.raises(ValidationError):
        RAGRunRequest.model_validate({
            "prompt": "What is différance?",
            "k": "",
            "fetch_k": None,
            "lambda_mult": "",
            "max_concurrent_requests": "",
        })

def test_research_heading_hierarchy_is_distinct():
    assert "research.page_kicker" in RESEARCH
    assert "Evidence-grounded inquiry" in RESEARCH
    assert "research.page_title" in RESEARCH
    assert "Research workspace" in RESEARCH
    assert "research.page_subtitle" in RESEARCH


def test_roles_are_dynamic_and_assignable_to_users():
    assert "createRole" in AUTH_API and "deleteRole" in AUTH_API
    assert "Create role" in ROLES
    assert "cloneFrom" in ROLES
    assert "v-for=\"item in roles\"" in USERS
    assert "Researcher is the default non-admin role" in ROLES
    assert '@app.post("/api/auth/roles")' in MAIN
    assert '@app.delete("/api/auth/roles/{role}")' in MAIN


def test_custom_role_store_round_trip(tmp_path, monkeypatch):
    import sys
    sys.path.insert(0, str(ROOT / "api"))
    from app import auth

    monkeypatch.setattr(auth, "settings", SimpleNamespace(auth_db_path=str(tmp_path / "auth.sqlite3")))
    store = auth.AuthStore()
    store.create_user("admin-test", "secret1", "admin")
    created = store.create_role("Evidence Reviewer", "Reviews evidence", "researcher")
    assert created["id"] == "evidence-reviewer"
    assert set(created["permissions"]) == set(store.capabilities_for_role("researcher"))

    user = store.create_user("reviewer", "secret1", created["id"])
    assert user.role == created["id"]
    assert user.role_name == "Evidence Reviewer"

    token = store.create_session(user.id)
    session_user = store.user_for_session(token)
    assert session_user is not None and session_user.role == created["id"]

    permissions = store.set_role_permissions(created["id"], ["page.research", "rag.run", "page.users"])
    assert "page.research" in permissions and "rag.run" in permissions
    # System administration remains outside every protected non-admin role.
    assert "page.users" not in permissions

    store.update_user(user.id, role="researcher")
    store.delete_role(created["id"])
    assert created["id"] not in store.role_ids()
