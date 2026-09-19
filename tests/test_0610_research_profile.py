"""Exercise endpoint policy without starting global database/job workers."""
from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi import HTTPException

from app.models import RAGRunRequest


def test_researcher_rag_uses_approved_model_and_not_browser_overrides():
    path = Path(__file__).resolve().parents[1] / "api/app/main.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name in {"create_rag_job", "_profile_generation_options"}]
    for node in functions:
        node.decorator_list = []
    profile = {"id": "approved", "type": "ollama", "model": "approved-model",
               "base_url": "http://approved:11434", "temperature": 0.2}
    jobs = SimpleNamespace(create=Mock(return_value={"id": "job"}))
    scope = {
        "json": json,
        "_request_user": lambda request: SimpleNamespace(role="researcher", username="reader"),
        "enforce_researcher_text": lambda payload: None,
        "system_store": SimpleNamespace(researcher_profile=lambda profile_id: profile),
        "rag_jobs": jobs, "RAGRunRequest": RAGRunRequest, "HTTPException": HTTPException,
    }
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id.startswith("_PROFILE_GENERATION_") for target in node.targets):
            scope[node.targets[0].id] = ast.literal_eval(node.value)
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec",
                 flags=__import__("__future__").annotations.compiler_flag), scope)
    body = RAGRunRequest(store="corpus", prompt="What is a trace?", provider="ollama",
                         provider_profile_id="approved", model="browser-model",
                         base_url="http://browser:11434", generation={"temperature": 1.5})
    assert scope["create_rag_job"](body, None) == {"id": "job"}
    submitted = jobs.create.call_args.args[0]
    assert submitted.model == "approved-model"
    assert submitted.base_url == "http://approved:11434"
    assert submitted.generation.temperature == 0.2
    assert jobs.create.call_args.kwargs == {"owner": "reader"}
