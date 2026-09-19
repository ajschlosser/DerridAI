"""Role storage and RAG request validation fixes.

Why: custom roles decide what non-admin users may do, and the RAG request schema is
the first line of defense against malformed numeric settings posted by forms.
How: validates the Pydantic model directly, and drives AuthStore against a
temporary SQLite database.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]








def test_rag_schema_rejects_blank_numeric_values():
    """Blank strings and nulls for numeric RAG settings must fail validation.

    Why: an empty form field arrives as "" (or null). Accepting it would let a bogus
    value reach retrieval (k, fetch_k, lambda_mult) or concurrency limits.
    """
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
    """Create a custom role, use it, restrict it, and delete it.

    Flow: create "Evidence Reviewer" (its id becomes "evidence-reviewer" and it starts
    with the researcher permission set); assign a user to it and confirm sessions see
    that role; set its permissions; move the user back and delete the role.
    Key rule: even if "page.users" is requested, it is dropped, because system
    administration stays outside every non-admin role.
    """
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
