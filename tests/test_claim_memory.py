# Copyright 2026 Aaron John Schlosser, PhD.
"""Validated-claim memory: human validation feeds a derived, advisory vector projection."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import claim_memory  # noqa: E402
from app.routers import derridai as routes  # noqa: E402
from app.system_store import system_store  # noqa: E402


class FakeIndex:
    def __init__(self):
        self.rows = {}

    def upsert(self, entry):
        self.rows[entry["claim_id"]] = entry

    def remove(self, claim_id):
        self.rows.pop(claim_id, None)


def _user(name="ann", role="user"):
    return SimpleNamespace(username=name, role=role)


def _request(user):
    return SimpleNamespace(state=SimpleNamespace(user=user), headers={}, cookies={})


@pytest.fixture()
def claim(monkeypatch):
    fake = FakeIndex()
    monkeypatch.setattr(routes, "_claim_memory", lambda: fake)
    monkeypatch.setattr(routes, "request_user", lambda request: request.state.user)
    payload = {"claim_id": "c-1", "claim_text": "Presence is deferred.", "owner": "ann", "validation_status": "unvalidated", "created_at": "2026-01-01T00:00:00+00:00"}
    system_store.put_generated_claim(payload)
    return fake, payload


def test_validating_a_claim_projects_it_with_the_reviewers_identity(claim):
    fake, _ = claim
    record = {
        "record_id": "r1", "record_revision": 1, "source_document_id": "d1",
        "field_assertions": {"speaker": [{
            "assertion_id": "a1", "field_id": "speaker", "field_name": "speaker", "record_id": "r1",
            "value": "Derrida", "derivation_method": "model", "evaluation_status": "value_supported",
            "authority_status": "human_confirmed", "value_status": "present", "record_revision": 1,
        }]},
        "current_field_assertions": {"speaker": "a1"},
    }
    result = routes.set_claim_validation("c-1", {"status": "validated", "record": record}, _request(_user()))
    assert result["projection"]["status"] == "indexed"
    assert result["claim"]["validated_by"] == "ann"
    assert system_store.get_generated_claim("c-1", owner="ann")["validation_status"] == "validated"
    assert "c-1" in fake.rows


def test_rejecting_or_reopening_removes_the_projection(claim):
    fake, _ = claim
    routes.set_claim_validation("c-1", {"status": "validated"}, _request(_user()))
    routes.set_claim_validation("c-1", {"status": "rejected"}, _request(_user()))
    assert "c-1" not in fake.rows
    assert system_store.get_generated_claim("c-1", owner="ann")["validation_status"] == "rejected"


def test_projection_failure_is_reported_but_the_audit_decision_stands(claim, monkeypatch):
    def boom():
        raise RuntimeError("chroma down")

    monkeypatch.setattr(routes, "_claim_memory", boom)
    result = routes.set_claim_validation("c-1", {"status": "validated"}, _request(_user()))
    assert result["projection"]["status"] == "failed" and "chroma down" in result["projection"]["error"]
    assert system_store.get_generated_claim("c-1", owner="ann")["validation_status"] == "validated"


def test_other_users_cannot_validate_someone_elses_claim(claim):
    with pytest.raises(Exception) as info:
        routes.set_claim_validation("c-1", {"status": "validated"}, _request(_user("bob")))
    assert getattr(info.value, "status_code", None) == 404


def test_only_validated_claims_are_eligible_and_stale_bindings_are_skipped():
    base = {"claim_id": "c", "claim_text": "X.", "owner": "ann"}
    assert claim_memory.derive_entry({**base, "validation_status": "unvalidated"}, []) is None
    entry = claim_memory.derive_entry(
        {**base, "validation_status": "validated"},
        [{"claim_id": "c", "record_id": "r1", "relation": "supports", "validation_status": "stale"},
         {"claim_id": "c", "record_id": "r2", "relation": "supports", "validation_status": "validated"}],
    )
    assert [s["record_id"] for s in entry["support"]] == ["r2"]


def test_similar_hits_are_rejoined_to_authority_and_stale_rows_dropped():
    class Store:
        def get_generated_claim(self, claim_id, owner=None):
            return {"claim_id": claim_id, "claim_text": "Y", "owner": owner,
                    "validation_status": "validated" if claim_id == "live" else "rejected"}

        def list_claim_support_bindings(self, claim_id, owner=None):
            return [{"claim_id": claim_id, "record_id": "r9", "relation": "supports", "validation_status": "validated"}]

    class Index:
        def similar(self, text, **kw):
            return [{"claim_id": "live", "similarity": 0.9, "metadata": {"support_json": '[{"record_id": "r9", "semantic": {"speaker": {"value": "Derrida"}}}]'}},
                    {"claim_id": "dead", "similarity": 0.8, "metadata": {}}]

    out = claim_memory.similar_validated_claims(Index(), Store(), {"claim_id": "c0", "claim_text": "Z"}, owner="ann")
    assert [i["claim_id"] for i in out["items"]] == ["live"]
    assert out["items"][0]["advisory"] is True
    assert out["items"][0]["support"][0]["semantic"]["speaker"]["value"] == "Derrida"
