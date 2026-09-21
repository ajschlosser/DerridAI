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

from app import main
from app.reviewer_context import current_reviewer
from starlette.responses import JSONResponse


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


# ---- channels a walk over the response JSON cannot see -------------------------------------------------------------

from pathlib import Path  # noqa: E402

from app import corpus_builder as cb  # noqa: E402
from app.config import APP_VERSION  # noqa: E402


def _manager(tmp_path: Path):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = repo.create_build({
        "asset_id": "a", "source_sha256": "x", "source_filename": "x.pdf", "source_page_count": 1, "source_block_count": 1,
        "schema_version": cb.SCHEMA_VERSION, "profile_id": cb.PROFILE_VERSION, "profile_version": 11, "app_version": APP_VERSION,
        "provider": "ollama", "model": "m", "request": {},
    })
    return cb.PdfCorpusBuildManager(repo), repo, build["build_id"]


def test_the_rest_of_the_record_stops_repeating_the_first_answer(tmp_path):
    rec = record(
        llm_rejections=[{"field": "discourse_role", "rejected_value": "commentary", "chosen_value": "assertion"}, {"field": "speaker", "rejected_value": "x", "chosen_value": "y"}],
        recheck_results={"discourse_role": {"first": "assertion", "second": "assertion", "agreed": True}},
        blind_reveals={"discourse_role": "assertion"}, recheck_scheduled={"discourse_role": {"due": 3}},
    )
    token = current_reviewer.set("user-2")
    try:
        main.scrub_second_opinions({"record": rec})
    finally:
        current_reviewer.reset(token)
    assert "assertion" not in json.dumps(rec)
    assert rec["llm_rejections"] == [{"field": "speaker", "rejected_value": "x", "chosen_value": "y"}]  # other fields keep theirs


def test_the_record_preview_is_built_from_what_this_reviewer_may_see(tmp_path):
    m, repo, bid = _manager(tmp_path)
    repo.save_records(bid, [record(review_disposition="pending")])
    token = current_reviewer.set("user-2")
    try:
        out = m.preview_record(bid, "r1")
    finally:
        current_reviewer.reset(token)
    assert "assertion" not in out["jsonl"] and "assertion" not in json.dumps(out)


def test_editorial_examples_do_not_teach_a_second_reviewer_the_first_answer(tmp_path):
    m, repo, bid = _manager(tmp_path)
    rows = [record(record_id=f"rec-{i}") for i in range(3)]
    repo.save_records(bid, rows)
    token = current_reviewer.set("user-1")
    try:
        mine = json.dumps(m.editorial_memory(bid))
    finally:
        current_reviewer.reset(token)
    token = current_reviewer.set("user-2")
    try:
        theirs = json.dumps(m.editorial_memory(bid))
    finally:
        current_reviewer.reset(token)
    assert "assertion" in mine and "assertion" not in theirs


def test_the_ledger_export_does_not_carry_sealed_values(tmp_path):
    from app.enrichment_ledger import EnrichmentLedger

    ledger = EnrichmentLedger(tmp_path / "l.jsonl")
    ledger.append("proposed", model="m", field="f", value="the model said this", blind=True)
    ledger.append("proposed", model="m", field="f", value="shown value", blind=False)
    ledger.append("recheck_seal", model="", field="f", value="first answer")
    ledger.append("blind_label", model="m", field="f", value="the model said this", new_value="reviewer said this", agreed=False)
    text = ledger.to_csv()
    assert "the model said this" in text  # only the decision row, after the fact
    assert text.count("the model said this") == 1 and "first answer" not in text and "shown value" in text


# ---- a guard: a new corpus-build route has to be looked at ---------------------------------------------------------

# Routes whose responses can carry a record or values derived from one. Each passes through the response filter, which
# hides a pending second opinion in any record it finds, and the channels tested above cover what it cannot see.
CARRIES_RECORDS = {
    ("GET", "/api/pdf/corpus-builds/{build_id}/records"),
    ("PATCH", "/api/pdf/corpus-builds/{build_id}/records/{record_id}/metadata"),
    ("PATCH", "/api/pdf/corpus-builds/{build_id}/records/{record_id}/text"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/records/{record_id}/metadata-decision"),
    ("PATCH", "/api/pdf/corpus-builds/{build_id}/records/{record_id}/evidence"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/records/{record_id}/accept"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/records/{record_id}/disposition"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/records/{record_id}/review-decision"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/records/disposition"),
    ("PATCH", "/api/pdf/corpus-builds/{build_id}/records/metadata"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/review/undo"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/review/redo"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/records/{record_id}/merge"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/records/{record_id}/slice"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/records/{record_id}/boundary-adjudication"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/records/{record_id}/split"),
    ("GET", "/api/pdf/corpus-builds/{build_id}/editorial-memory"),
    ("GET", "/api/pdf/corpus-builds/{build_id}/records/{record_id}/preview"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/records/{record_id}/viewed"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/records/{record_id}/text-touchup"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/records/{record_id}/rerun-metadata"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/publish"),
    ("GET", "/api/pdf/corpus-builds/{build_id}/second-opinions"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/records/{record_id}/second-opinion"),
}
# Routes that return only build-level state (status, counters, manifest) or start work.
BUILD_LEVEL = {
    ("POST", "/api/pdf/corpus-builds"),
    ("GET", "/api/pdf/corpus-builds"),
    ("GET", "/api/pdf/corpus-builds/{build_id}"),
    ("PATCH", "/api/pdf/corpus-builds/{build_id}/provider-profile"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/manifest/regenerate"),
    ("PATCH", "/api/pdf/corpus-builds/{build_id}/manifest"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/confirm-manifest"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/cancel"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/settle-metadata"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/resume"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/metadata/retry"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/metadata/enrich"),
    ("POST", "/api/pdf/corpus-builds/{build_id}/autonomous/run"),
    ("DELETE", "/api/pdf/corpus-builds/{build_id}/editorial-memory"),
}


def test_every_corpus_build_route_has_been_considered_for_second_opinion_leaks():
    seen = {
        (method, route.path)
        for route in main.app.routes
        if getattr(route, "path", "").startswith("/api/pdf/corpus-builds")
        for method in getattr(route, "methods", set()) - {"HEAD", "OPTIONS"}
    }
    assert len(seen) > 25  # the route table was actually read
    unreviewed = sorted(seen - CARRIES_RECORDS - BUILD_LEVEL)
    assert not unreviewed, (
        "New corpus-build route(s) not classified in tests/test_second_opinion_scrub.py: " + ", ".join(f"{m} {p}" for m, p in unreviewed)
        + ". Decide whether the response can carry a record or a value derived from one, and add it to CARRIES_RECORDS or BUILD_LEVEL."
    )
