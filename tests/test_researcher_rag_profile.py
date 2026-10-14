# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
        if isinstance(node, ast.FunctionDef) and node.name == "start_research_run"
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
        # Thread persistence is covered by the Research thread tests; here the
        # shared start helper just forwards to the job manager.
        "research_threads": SimpleNamespace(
            start_run=lambda manager, body, *, owner, **kwargs: manager.create(body, owner=owner)
        ),
        "ThreadNotFound": LookupError,
        "ThreadBusy": RuntimeError,
        "RAGRunRequest": RAGRunRequest,
        "HTTPException": HTTPException,
        "profile_generation_options": profile_generation_options,
        # Pipeline resolution is covered independently by pipeline-access tests.
        # This isolated route test remains scoped to researcher provider policy,
        # so provide the already-resolved server default as an explicit dependency.
        "resolve_research_pipeline": lambda **kwargs: SimpleNamespace(
            pipeline_id="research.current",
            version=1,
        ),
        "resolve_pipeline_config": lambda pipeline, **kwargs: SimpleNamespace(
            effective=pipeline,
        ),
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

    assert scope["start_research_run"](body, None) == {"id": "job"}
    submitted = jobs.create.call_args.args[0]
    assert submitted.model == "approved-model"
    assert submitted.base_url == "http://approved:11434"
    assert submitted.generation.temperature == 0.2
    assert jobs.create.call_args.kwargs == {"owner": "reader"}
