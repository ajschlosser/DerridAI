"""Every corpus-build response hides a pending second opinion from the reviewer who owes it."""

from __future__ import annotations

import asyncio
import json
import sys
import types

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules["chromadb"] = types.SimpleNamespace()

from starlette.responses import JSONResponse

from app import main
from app.reviewer_context import current_reviewer


def record(**over):
    return {
        "record_id": "r1", "discourse_role": "assertion", "text": "t",
        "second_opinion": {"discourse_role": {"first_reviewer": "user-1"}},
        "metadata_field_status": {"discourse_role": {"status": "human_confirmed"}},
        "metadata_decisions": [{"field": "discourse_role", "value": "assertion"}], **over,
    }


def test_nested_records_are_scrubbed_for_the_second_reviewer_only():
    token = current_reviewer.set("user-2")
    try:
        payload = {"record": record(), "records": [record(record_id="r2")], "left_record": record(record_id="r3")}
        assert main.scrub_second_opinions(payload) is True
        assert "assertion" not in json.dumps(payload)
    finally:
        current_reviewer.reset(token)
    token = current_reviewer.set("user-1")
    try:
        payload = {"record": record()}
        assert main.scrub_second_opinions(payload) is False
        assert payload["record"]["discourse_role"] == "assertion"
    finally:
        current_reviewer.reset(token)


def test_a_response_from_any_route_is_rewritten_in_flight():
    token = current_reviewer.set("user-2")
    try:
        original = JSONResponse({"record": record(), "build": {"status": "awaiting_review"}})
        cleaned = asyncio.run(main._hide_pending_second_opinions(original))
        body = json.loads(cleaned.body)
        assert "assertion" not in json.dumps(body) and body["build"]["status"] == "awaiting_review"
        assert cleaned.headers["content-type"].startswith("application/json")
    finally:
        current_reviewer.reset(token)


def test_responses_that_never_mention_a_second_opinion_pass_through_untouched():
    token = current_reviewer.set("user-2")
    try:
        original = JSONResponse({"record": {"record_id": "r9", "discourse_role": "assertion"}})
        assert json.loads(asyncio.run(main._hide_pending_second_opinions(original)).body)["record"]["discourse_role"] == "assertion"
    finally:
        current_reviewer.reset(token)


def test_through_the_real_app_an_accept_response_hides_the_first_answer(monkeypatch):
    import httpx

    user = types.SimpleNamespace(id=2, role="admin", username="b")
    monkeypatch.setattr(main.auth_store, "user_for_session", lambda cookie: user)
    monkeypatch.setattr(main.pdf_corpus_builds, "accept_record", lambda *a, **k: record())

    async def call():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
            return await client.post("/api/pdf/corpus-builds/b/records/r1/accept", json={"accepted": True})

    response = asyncio.run(call())
    assert response.status_code == 200
    assert "assertion" not in response.text and response.json()["record_id"] == "r1"
