# Copyright 2026 Aaron John Schlosser, PhD.
"""The read-only cELF GraphQL façade: parity with REST, authorization, privacy and limits.

Why: GraphQL is a second transport over the same cELF reads. It must return what REST returns,
never bypass administrator-only or owner-scoped reads, never reveal a sealed first-review answer,
and stay bounded (no mutations, subscriptions, GET queries, introspection, or unbounded documents).
How: drives the real ASGI app through httpx with a stubbed session lookup, and compares GraphQL
results with the REST endpoints that share the same service code.
"""
from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.modules.setdefault("chromadb", types.SimpleNamespace())
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

import httpx  # noqa: E402
from app import main  # noqa: E402
from app.auth import auth_store  # noqa: E402
from app.celf_queries import claims as claim_queries  # noqa: E402
from app.celf_queries import records as record_queries  # noqa: E402
from app.celf_queries.access import AccessContext, NotFound  # noqa: E402
from app.derridai_model import normative_model  # noqa: E402
from app.graphql.loaders import RequestLoaders  # noqa: E402
from app.graphql.permissions import ROOT_FIELD_POLICY  # noqa: E402
from app.graphql.schema import schema  # noqa: E402
from app.routers import derridai as derridai_routes  # noqa: E402
from app.system_store import system_store  # noqa: E402

USERS = {
    "admin-cookie": SimpleNamespace(id=1, username="root", role="admin", active=True),
    "reviewer-cookie": SimpleNamespace(id=2, username="second", role="admin", active=True),
    "researcher-cookie": SimpleNamespace(id=3, username="ann", role="researcher", active=True),
}


@pytest.fixture(autouse=True)
def sessions(monkeypatch):
    monkeypatch.setattr(auth_store, "user_for_session", lambda cookie: USERS.get(cookie or ""))


def _call(method: str, path: str, *, cookie: str | None = "admin-cookie", **kwargs):
    async def run():
        transport = httpx.ASGITransport(app=main.app)
        cookies = {"derridai_session": cookie} if cookie else {}
        async with httpx.AsyncClient(transport=transport, base_url="http://t", cookies=cookies) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(run())


def gql(query: str, variables: dict | None = None, *, cookie: str | None = "admin-cookie"):
    response = _call("POST", "/api/graphql", cookie=cookie, json={"query": query, "variables": variables or {}})
    return response


RECORD = {
    "record_id": "rec-gql-1",
    "record_revision": 2,
    "source_document_id": "doc-gql",
    "work": "Of Grammatology",
    "page_start": 10,
    "source_spans": [{"source_unit_id": "b1", "page": 10, "char_start": 0, "char_end": 40}],
    "field_assertions": {
        "speaker": [{
            "assertion_id": "as-speaker", "record_id": "rec-gql-1", "field_id": "speaker",
            "field_name": "speaker", "value": "Derrida", "derivation_method": "model",
            "evaluation_status": "value_supported", "authority_status": "human_confirmed",
            "value_status": "present", "confidence": 0.93, "reason": "Signed preface.",
            "record_revision": 2,
        }],
        "position_holder": [{
            "assertion_id": "as-holder", "record_id": "rec-gql-1", "field_id": "position_holder",
            "field_name": "position_holder", "value": "Rousseau", "derivation_method": "model",
            "evaluation_status": "value_supported", "authority_status": "unreviewed",
            "value_status": "present", "confidence": 0.71, "record_revision": 2,
        }],
    },
    "current_field_assertions": {"speaker": "as-speaker", "position_holder": "as-holder"},
}

GRAPH_QUERY = """
query RecordGraph($record: JSON!) {
  record_graph(record: $record) {
    root_id
    record_state_origin
    nodes {
      id object_type object_id materialization status
      field_assertion { assertion_id field_name value authority_status evaluation_status confidence reason is_current }
      source_span { source_unit_ids physical_page_start character_start time_start speaker }
      generated_claim { claim_id validation_status }
    }
    edges { source target relation }
  }
}
"""


@pytest.fixture()
def claim_with_bindings():
    system_store.put_generated_claim({
        "claim_id": "gql-claim-1", "claim_text": "Writing supplements speech.", "owner": "root",
        "run_id": "run-9", "validation_status": "validated", "created_at": "2026-01-01T00:00:00+00:00",
    })
    system_store.put_claim_support_binding({
        "support_binding_id": "gql-binding-current", "claim_id": "gql-claim-1", "owner": "root",
        "record_id": "rec-gql-1", "record_revision": 2, "source_document_id": "doc-gql", "relation": "supports",
        "validation_status": "validated",
    })
    system_store.put_claim_support_binding({
        "support_binding_id": "gql-binding-stale", "claim_id": "gql-claim-1", "owner": "root",
        "record_id": "rec-gql-1", "record_revision": 1, "source_document_id": "doc-gql", "relation": "supports",
        "validation_status": "validated",
    })
    return "gql-claim-1"


def test_graphql_requires_an_authenticated_session():
    assert gql("{ celf_model { specification_version } }", cookie=None).status_code == 401


def test_celf_model_matches_the_rest_model():
    data = gql("{ celf_model { specification_version nodes { type profile persistence label normative } "
               "edges { id source_type target_type relation inverse_relation source_cardinality target_cardinality profile normative } } }").json()
    assert "errors" not in data
    rest = _call("GET", "/api/derridai/model").json()
    assert data["data"]["celf_model"] == rest == normative_model()


def test_record_graph_matches_rest_and_keeps_speaker_distinct_from_position_holder(claim_with_bindings):
    data = gql(GRAPH_QUERY, {"record": RECORD}).json()
    assert "errors" not in data, data
    graph = data["data"]["record_graph"]
    rest = _call("POST", "/api/derridai/graph/record", json={"record": RECORD}).json()

    assert graph["root_id"] == rest["root_id"]
    assert graph["record_state_origin"] == rest["record_state_origin"] == "client_snapshot"
    assert {node["id"] for node in graph["nodes"]} == {node["id"] for node in rest["nodes"]}
    assert {(e["source"], e["target"], e["relation"]) for e in graph["edges"]} == {
        (e["source"], e["target"], e["relation"]) for e in rest["edges"]
    }
    rest_status = {node["id"]: node["status"] for node in rest["nodes"]}
    assert {node["id"]: node["status"] for node in graph["nodes"]} == rest_status

    assertions = {
        node["field_assertion"]["field_name"]: node["field_assertion"]
        for node in graph["nodes"] if node["field_assertion"]
    }
    assert assertions["speaker"]["value"] == "Derrida"
    assert assertions["position_holder"]["value"] == "Rousseau"
    assert assertions["speaker"]["authority_status"] == "human_confirmed"
    assert assertions["position_holder"]["authority_status"] == "unreviewed"
    assert assertions["speaker"]["reason"] == "Signed preface." and assertions["speaker"]["is_current"] is True

    # The stale revision stays visible instead of being silently re-pointed at revision 2.
    assert "RecordRevision:rec-gql-1@1" in {node["id"] for node in graph["nodes"]}
    claims = [node["generated_claim"] for node in graph["nodes"] if node["generated_claim"]]
    assert claims == [{"claim_id": "gql-claim-1", "validation_status": "validated"}]
    span = next(node["source_span"] for node in graph["nodes"] if node["source_span"])
    assert span["physical_page_start"] == 10 and span["character_start"] == 0 and span["time_start"] is None


def test_record_graph_hides_a_sealed_first_answer_from_the_second_reviewer():
    sealed = {
        **RECORD,
        "speaker": "Sealed Speaker Answer",
        "second_opinion": {"speaker": {"first_reviewer": "user-1", "done": False}},
        "field_assertions": {"speaker": [{
            **RECORD["field_assertions"]["speaker"][0], "value": "Sealed Speaker Answer",
        }]},
        "current_field_assertions": {"speaker": "as-speaker"},
    }
    as_second = gql(GRAPH_QUERY, {"record": sealed}, cookie="reviewer-cookie")
    assert "Sealed Speaker Answer" not in as_second.text
    assert all(node["field_assertion"] is None for node in as_second.json()["data"]["record_graph"]["nodes"])
    rest = _call("POST", "/api/derridai/graph/record", cookie="reviewer-cookie", json={"record": sealed})
    assert "Sealed Speaker Answer" not in rest.text

    # The first reviewer is not owed an independent answer, so nothing is hidden.
    as_first = gql(GRAPH_QUERY, {"record": sealed}, cookie="admin-cookie")
    assert "Sealed Speaker Answer" in as_first.text


def test_researchers_reach_only_the_type_model_not_record_or_claim_reads(claim_with_bindings):
    ok = gql("{ celf_model { specification_version } }", cookie="researcher-cookie").json()
    assert ok["data"]["celf_model"]["specification_version"] == "1.0"

    denied = gql(GRAPH_QUERY, {"record": RECORD}, cookie="researcher-cookie").json()
    assert denied["data"] is None and "Administrator access required" in denied["errors"][0]["message"]
    claim = gql('{ generated_claim(claim_id: "gql-claim-1") { claim_text } }', cookie="researcher-cookie").json()
    assert claim["data"] is None and "Writing supplements" not in str(claim)


def test_generated_claim_is_owner_scoped_in_the_shared_service(claim_with_bindings):
    assert claim_queries.get_generated_claim(AccessContext("root", "admin", 1), "gql-claim-1")["run_id"] == "run-9"
    with pytest.raises(NotFound):
        claim_queries.get_generated_claim(AccessContext("mallory", "researcher", 9), "gql-claim-1")


def test_similar_validated_claims_matches_rest(claim_with_bindings, monkeypatch):
    class FakeIndex:
        def similar(self, text, **kwargs):
            return [{"claim_id": "gql-claim-1", "similarity": 0.88, "metadata": {}}]

    monkeypatch.setattr(claim_queries, "default_claim_index", lambda: FakeIndex())
    system_store.put_generated_claim({
        "claim_id": "gql-claim-2", "claim_text": "Speech is supplemented.", "owner": "root",
        "validation_status": "unvalidated", "created_at": "2026-01-02T00:00:00+00:00",
    })
    data = gql('{ generated_claim(claim_id: "gql-claim-2") { claim_id similar_validated_claims(limit: 3) '
               "{ claim_id claim_text similarity advisory support { record_id record_revision relation } } } }").json()
    assert "errors" not in data, data
    rest = _call("GET", "/api/derridai/claims/gql-claim-2/similar?limit=3").json()
    graph_items = data["data"]["generated_claim"]["similar_validated_claims"]
    assert [item["claim_id"] for item in graph_items] == [item["claim_id"] for item in rest["items"]] == ["gql-claim-1"]
    assert graph_items[0]["advisory"] is True and graph_items[0]["similarity"] == rest["items"][0]["similarity"]
    assert {s["record_id"] for s in graph_items[0]["support"]} == {s["record_id"] for s in rest["items"][0]["support"]}


def test_nested_support_bindings_keep_stale_status_visible(claim_with_bindings):
    data = gql('{ generated_claim(claim_id: "gql-claim-1") { support_bindings { support_binding_id record_revision validation_status } } }').json()
    bindings = {row["support_binding_id"]: row for row in data["data"]["generated_claim"]["support_bindings"]}
    assert set(bindings) == {"gql-binding-current", "gql-binding-stale"}
    assert bindings["gql-binding-stale"]["record_revision"] == 1


def test_the_schema_is_query_only_and_every_root_field_declares_a_policy():
    graphql_schema = schema._schema
    assert graphql_schema.mutation_type is None and graphql_schema.subscription_type is None
    assert set(graphql_schema.query_type.fields) <= set(ROOT_FIELD_POLICY)
    mutation = gql("mutation { celf_model { specification_version } }").json()
    assert mutation.get("data") is None and mutation["errors"]


def test_get_queries_introspection_and_excess_aliases_are_refused():
    get = _call("GET", "/api/graphql?query={celf_model{specification_version}}")
    assert get.status_code in {400, 404, 405} and "specification_version" not in get.text
    introspection = gql("{ __schema { types { name } } }").json()
    assert introspection.get("data") is None and introspection["errors"]
    aliases = " ".join(f"a{i}: celf_model {{ specification_version }}" for i in range(25))
    assert gql("{ " + aliases + " }").json()["errors"]


def test_depth_and_token_limits_are_enforced(monkeypatch):
    from dataclasses import replace

    from app.graphql import schema as schema_module
    from app.graphql.context import GraphQLContext

    monkeypatch.setattr(schema_module, "settings", replace(schema_module.settings, graphql_max_depth=1, graphql_max_tokens=40))
    limited = schema_module.build_schema()
    access = AccessContext("root", "admin", 1)
    context = GraphQLContext(access=access, loaders=RequestLoaders(access))
    shallow = limited.execute_sync("{ celf_model { specification_version } }", context_value=context)
    assert shallow.errors is None
    deep = limited.execute_sync("{ celf_model { nodes { type } } }", context_value=context)
    assert deep.errors and "depth" in str(deep.errors[0]).lower()
    long = "{ " + " ".join(f"a{i}: celf_model {{ specification_version }}" for i in range(12)) + " }"
    assert limited.execute_sync(long, context_value=context).errors


def test_internal_errors_are_masked(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("/secret/internal/path exploded")

    monkeypatch.setattr(record_queries, "record_graph", boom)
    body = gql(GRAPH_QUERY, {"record": RECORD}).text
    assert "/secret/internal/path" not in body and "Internal server error." in body


def test_invalid_record_snapshots_are_rejected_with_a_public_message():
    data = gql(GRAPH_QUERY, {"record": {"work": "no id"}}).json()
    assert data["errors"][0]["message"] == "record.record_id is required"


def test_dataloaders_batch_within_a_request_and_never_share_across_users(claim_with_bindings):
    system_store.put_generated_claim({
        "claim_id": "gql-claim-ann", "claim_text": "Ann's claim.", "owner": "ann",
        "validation_status": "unvalidated", "created_at": "2026-01-03T00:00:00+00:00",
    })

    async def run():
        root_loaders = RequestLoaders(AccessContext("root", "admin", 1))
        first, second = await asyncio.gather(
            root_loaders.claims.load("gql-claim-1"),
            root_loaders.claims.load("gql-claim-ann"),
        )
        bob_loaders = RequestLoaders(AccessContext("bob", "researcher", 7))
        bob_view = await bob_loaders.claims.load("gql-claim-ann")
        return root_loaders.batch_calls["claims"], first, second, bob_view

    batches, first, second, bob_view = asyncio.run(run())
    assert batches == 1
    assert first["claim_id"] == "gql-claim-1" and second["claim_id"] == "gql-claim-ann"
    assert bob_view is None


def test_rest_record_graph_still_rejects_missing_record_id():
    response = _call("POST", "/api/derridai/graph/record", json={"record": {"work": "x"}})
    assert response.status_code == 422 and response.json()["detail"] == "record.record_id is required"
    assert derridai_routes.router is not None
