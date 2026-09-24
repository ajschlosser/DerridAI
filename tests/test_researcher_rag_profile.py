"""Researcher RAG must use the approved server-side provider profile.

Why: researchers may not choose models or endpoints. The API must ignore browser
overrides and use the administrator-approved server profile instead.
How: compile only the route function so the test does not start global database
or job-worker services, and inject the real provider-option normalizer.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from app.models import RAGRunRequest
from app.provider_profile_options import profile_generation_options
from fastapi import HTTPException


def test_researcher_rag_uses_approved_model_and_not_browser_overrides():
    """Browser model, endpoint, and temperature are replaced by approved values."""
    path = Path(__file__).resolve().parents[1] / "api/app/routers/jobs.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    route = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "create_rag_job"
    )
    route.decorator_list = []

    profile = {
        "id": "approved",
        "type": "ollama",
        "model": "approved-model",
        "base_url": "http://approved:11434",
        "temperature": 0.2,
    }
    jobs = SimpleNamespace(create=Mock(return_value={"id": "job"}))
    scope = {
        "request_user": lambda request: SimpleNamespace(
            role="researcher",
            username="reader",
        ),
        "enforce_researcher_text": lambda payload: None,
        "system_store": SimpleNamespace(
            researcher_profile=lambda profile_id: profile,
        ),
        "rag_jobs": jobs,
        "RAGRunRequest": RAGRunRequest,
        "HTTPException": HTTPException,
        "profile_generation_options": profile_generation_options,
    }
    exec(
        compile(
            ast.Module(body=[route], type_ignores=[]),
            str(path),
            "exec",
            flags=__import__("__future__").annotations.compiler_flag,
        ),
        scope,
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

    assert scope["create_rag_job"](body, None) == {"id": "job"}
    submitted = jobs.create.call_args.args[0]
    assert submitted.model == "approved-model"
    assert submitted.base_url == "http://approved:11434"
    assert submitted.generation.temperature == 0.2
    assert jobs.create.call_args.kwargs == {"owner": "reader"}
