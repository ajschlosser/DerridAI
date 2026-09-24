"""Researcher RAG must use the approved server-side provider profile."""

from types import SimpleNamespace
from unittest.mock import Mock

from app.models import RAGRunRequest
from app.routers import jobs as jobs_routes


def test_researcher_rag_uses_approved_model_and_not_browser_overrides(monkeypatch):
    """A researcher request is rebuilt from the administrator-owned profile."""
    profile = {
        "id": "approved",
        "type": "ollama",
        "model": "approved-model",
        "base_url": "http://approved:11434",
        "temperature": 0.2,
    }
    monkeypatch.setattr(
        jobs_routes.system_store,
        "researcher_profile",
        lambda profile_id: profile,
    )
    monkeypatch.setattr(
        jobs_routes,
        "enforce_researcher_text",
        lambda payload: None,
    )

    rag_manager = SimpleNamespace(create=Mock(return_value={"id": "job"}))
    managers = SimpleNamespace(rag=rag_manager)
    request = SimpleNamespace(
        state=SimpleNamespace(
            user=SimpleNamespace(role="researcher", username="reader")
        )
    )
    body = RAGRunRequest(
        store="corpus",
        prompt="What is a trace?",
        provider="ollama",
        provider_profile_id="approved",
        model="browser-model",
        base_url="http://browser:11434",
        generation={"temperature": 1.5},
    )

    assert jobs_routes.create_rag_job(body, request, managers) == {"id": "job"}

    submitted = rag_manager.create.call_args.args[0]
    assert submitted.model == "approved-model"
    assert submitted.base_url == "http://approved:11434"
    assert submitted.generation.temperature == 0.2
    assert rag_manager.create.call_args.kwargs == {"owner": "reader"}
