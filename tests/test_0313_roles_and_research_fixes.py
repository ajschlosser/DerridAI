from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]








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
