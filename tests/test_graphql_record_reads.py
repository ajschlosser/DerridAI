# Copyright 2026 Aaron John Schlosser, PhD.
"""GraphQL reads for Corpus Builder review Records and vector-store projections.

Why: the review queue previously shipped full Records (text, every metadata field,
provenance) for a page that only ever renders identifiers, page labels, a short
preview and review state. GraphQL's `corpus_build.review_queue`/`rows` return a
much smaller `CorpusQueueRow` projection instead; opening a Record for review still
reads the full presented Record through `record`/`records`. Both paths must match
REST byte-for-byte in substance (same filtering, same counts, same blind-review
scrubbing) while the queue page itself is bounded and far smaller.
How: drives the real ASGI app through httpx with a stubbed session lookup and a
temporary Corpus Builder repository, and compares GraphQL results with the REST
endpoints that share the same underlying stored Records.
"""
from __future__ import annotations

import asyncio
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.modules.setdefault("chromadb", types.SimpleNamespace())
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

import httpx  # noqa: E402
from app import corpus_builder as cb  # noqa: E402
from app import main  # noqa: E402
from app.auth import auth_store  # noqa: E402
from app.celf_queries import access as access_module  # noqa: E402
from app.celf_queries import corpus_records as corpus_queries  # noqa: E402
from app.celf_queries import vector_records as vector_queries  # noqa: E402
from app.celf_queries.access import AccessContext  # noqa: E402
from app.graphql.loaders import RequestLoaders  # noqa: E402
from app.routers import corpus as corpus_routes  # noqa: E402

USERS = {
    "admin-cookie": SimpleNamespace(id=1, username="root", role="admin", active=True),
    "reviewer-cookie": SimpleNamespace(id=2, username="second", role="admin", active=True),
    "researcher-cookie": SimpleNamespace(id=3, username="ann", role="researcher", active=True),
}


@pytest.fixture(autouse=True)
def sessions(monkeypatch):
    monkeypatch.setattr(auth_store, "user_for_session", lambda cookie: USERS.get(cookie or ""))
    # Deterministic: a researcher has exactly corpus.read, regardless of seeded role defaults.
    monkeypatch.setattr(access_module, "role_has_capability", lambda role, capability: capability == "corpus.read")


def _call(method: str, path: str, *, cookie: str | None = "admin-cookie", **kwargs):
    async def run():
        transport = httpx.ASGITransport(app=main.app)
        cookies = {"derridai_session": cookie} if cookie else {}
        async with httpx.AsyncClient(transport=transport, base_url="http://t", cookies=cookies) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(run())


def gql(query: str, variables: dict | None = None, *, cookie: str | None = "admin-cookie"):
    return _call("POST", "/api/graphql", cookie=cookie, json={"query": query, "variables": variables or {}})


LONG_TEXT = (
    "Il n'y a pas de hors-texte. " * 40
    + "The trace is not a presence but is rather the simulacrum of a presence."
)


def _record(record_id: str, **overrides) -> dict:
    base = {
        "record_id": record_id,
        "record_revision": 1,
        "work": "Of Grammatology",
        "text": LONG_TEXT,
        "page_start": 10,
        "page_end": 12,
        "needs_review": False,
        "metadata_complete": True,
        "metadata_llm_processed": True,
        "source_quality_issues": False,
        "review_disposition": "pending",
        "discourse_role": "main_text",
        "region_type": "main_text",
        "speaker": "Derrida",
        "topics": ["writing", "supplement", "trace"],
        "concepts": ["différance", "arche-writing"],
        "field_assertions": {},
        "metadata_field_status": {},
    }
    base.update(overrides)
    return base


@pytest.fixture()
def build(tmp_path, monkeypatch):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    monkeypatch.setattr(corpus_routes, "pdf_corpus_repository", repo)
    monkeypatch.setattr(corpus_queries, "pdf_corpus_repository", repo)

    asset = {
        "asset_id": "asset-gql", "sha256": "sha", "filename": "book.pdf", "page_count": 20,
        "block_count": 12, "ocr_pages": 0, "warnings": [], "metadata": {}, "pages": [],
    }
    cb._json_write(repo.asset_meta_path(asset["asset_id"]), asset)
    built = repo.create_build({
        "asset_id": asset["asset_id"], "source_sha256": "sha", "source_filename": "book.pdf",
        "source_page_count": 20, "source_block_count": 12, "schema_version": cb.SCHEMA_VERSION,
        "profile_id": cb.PROFILE_VERSION, "profile_version": 8, "app_version": "0.60.0",
        "provider": "ollama", "model": "test-model", "request": {"provider_profile_id": "primary"},
        "manifest": {}, "validation": {"valid": True},
    })
    build_id = built["build_id"]

    records = [
        _record("r1", review_disposition="accepted", accepted=True),
        _record("r2", review_disposition="rejected", rejected=True),
        _record(
            "r3", review_disposition="pending", needs_review=True, metadata_complete=False,
            metadata_incomplete_fields=["discourse_role"], review_reason="Pending human review.",
        ),
        _record(
            "r4", review_disposition="pending",
            second_opinion={"speaker": {"first_reviewer": "user-1", "done": False}},
            speaker="Sealed First Answer",
        ),
        *[_record(f"r{i}") for i in range(5, 13)],
    ]
    repo.save_records(build_id, records)
    return repo, build_id


REVIEW_QUEUE_QUERY = """
query Q($build_id: String!, $offset: Int!, $limit: Int!) {
  corpus_build(build_id: $build_id) {
    review_queue(offset: $offset, limit: $limit) {
      items {
        record_id record_revision page_start page_end text_length text_preview
        review_state review_disposition review_issue_codes metadata_llm_processed
        needs_review source_quality_issues metadata_complete
      }
      total offset limit
      queue_counts { all ready preparing issues metadata topology source accepted rejected pending }
    }
  }
}
"""


def test_review_queue_matches_rest_counts_and_ordering(build):
    repo, build_id = build
    data = gql(REVIEW_QUEUE_QUERY, {"build_id": build_id, "offset": 0, "limit": 50}).json()
    assert "errors" not in data, data
    page = data["data"]["corpus_build"]["review_queue"]
    rest = _call("GET", f"/api/pdf/corpus-builds/{build_id}/records", params={"limit": 50}).json()

    assert page["total"] == rest["total"] == 12
    assert [item["record_id"] for item in page["items"]] == [item["record_id"] for item in rest["items"]]
    assert page["queue_counts"] == rest["queue_counts"]
    rest_by_id = {item["record_id"]: item for item in rest["items"]}
    for item in page["items"]:
        rest_item = rest_by_id[item["record_id"]]
        assert item["review_state"] == rest_item["review_state"]
        assert item["review_disposition"] == (rest_item.get("review_disposition") or "pending")
        assert item["text_length"] == len(rest_item["text"])


def test_review_queue_filters_match_rest(build):
    repo, build_id = build
    for params in (
        {"needs_review": True},
        {"disposition": "accepted"},
        {"metadata_incomplete": True},
        {"review_queue": "issues"},
    ):
        rest = _call("GET", f"/api/pdf/corpus-builds/{build_id}/records", params=params).json()
        gql_query = """
        query Q($build_id: String!, $needs_review: Boolean, $disposition: String,
                $metadata_incomplete: Boolean, $review_queue: String) {
          corpus_build(build_id: $build_id) {
            review_queue(needs_review: $needs_review, disposition: $disposition,
                          metadata_incomplete: $metadata_incomplete, review_queue: $review_queue) {
              items { record_id }
              total
            }
          }
        }
        """
        data = gql(gql_query, {
            "build_id": build_id,
            "needs_review": params.get("needs_review"),
            "disposition": params.get("disposition"),
            "metadata_incomplete": params.get("metadata_incomplete"),
            "review_queue": params.get("review_queue"),
        }).json()
        assert "errors" not in data, data
        page = data["data"]["corpus_build"]["review_queue"]
        assert page["total"] == rest["total"], params
        assert [i["record_id"] for i in page["items"]] == [i["record_id"] for i in rest["items"]], params


def test_review_queue_page_is_far_smaller_than_the_rest_response(build):
    repo, build_id = build
    gql_data = gql(REVIEW_QUEUE_QUERY, {"build_id": build_id, "offset": 0, "limit": 50}).json()
    rest_data = _call("GET", f"/api/pdf/corpus-builds/{build_id}/records", params={"limit": 50}).json()

    gql_bytes = len(json.dumps(gql_data["data"]["corpus_build"]["review_queue"]["items"]).encode("utf-8"))
    rest_bytes = len(json.dumps(rest_data["items"]).encode("utf-8"))
    assert rest_bytes >= gql_bytes * 10, (rest_bytes, gql_bytes)


def test_review_queue_limit_is_clamped_to_the_bounded_maximum(build):
    repo, build_id = build
    data = gql(REVIEW_QUEUE_QUERY, {"build_id": build_id, "offset": 0, "limit": 100000}).json()
    assert data["data"]["corpus_build"]["review_queue"]["limit"] == corpus_queries.MAX_QUEUE_PAGE


RECORD_QUERY = """
query Q($build_id: String!, $record_id: String!) {
  corpus_build(build_id: $build_id) {
    record(record_id: $record_id) { record_id record_revision work text review_state review_document }
  }
}
"""


def test_record_returns_the_full_reviewer_presented_record(build):
    repo, build_id = build
    data = gql(RECORD_QUERY, {"build_id": build_id, "record_id": "r1"}).json()
    assert "errors" not in data, data
    record = data["data"]["corpus_build"]["record"]
    assert record["record_id"] == "r1"
    assert record["text"] == LONG_TEXT
    assert record["review_document"]["work"] == "Of Grammatology"
    assert record["review_state"] == "accepted"



def test_reviewer_projection_retains_metadata_evidence_source_unit_bindings(build):
    """Persisted evidence suggestions remain visible in the reviewer-facing Record projection."""
    repo, build_id = build
    records = repo.load_records(build_id)
    target = next(record for record in records if record["record_id"] == "r3")
    target["source_unit_ids"] = ["u-1"]
    target["metadata_evidence"] = {
        "speaker": {
            "block_ids": ["u-1"],
            "confidence": None,
            "reason": "Deterministic fallback suggestion.",
            "backfilled": True,
            "method": "deterministic-lexical-v1",
        }
    }
    repo.save_records(build_id, records)

    data = gql(RECORD_QUERY, {"build_id": build_id, "record_id": "r3"}).json()
    assert "errors" not in data, data
    presented = data["data"]["corpus_build"]["record"]["review_document"]

    assert presented["source_unit_ids"] == ["u-1"]
    assert presented["metadata_evidence"]["speaker"]["block_ids"] == ["u-1"]
    assert presented["metadata_evidence"]["speaker"]["method"] == "deterministic-lexical-v1"


def test_record_reads_a_missing_id_as_not_found(build):
    repo, build_id = build
    data = gql(RECORD_QUERY, {"build_id": build_id, "record_id": "nope"}).json()
    assert data["data"] is None
    assert "not found" in data["errors"][0]["message"].casefold()


def test_missing_build_reads_as_not_found(build):
    data = gql(RECORD_QUERY, {"build_id": "no-such-build", "record_id": "r1"}).json()
    assert data["data"] is None
    assert "not found" in data["errors"][0]["message"].casefold()


ROWS_QUERY = """
query Q($build_id: String!, $ids: [String!]!) {
  corpus_build(build_id: $build_id) {
    rows(record_ids: $ids) { record_id text_length review_state }
  }
}
"""


def test_rows_returns_lightweight_projections_for_specific_ids_in_order(build):
    repo, build_id = build
    data = gql(ROWS_QUERY, {"build_id": build_id, "ids": ["r2", "does-not-exist", "r1"]}).json()
    assert "errors" not in data, data
    rows = data["data"]["corpus_build"]["rows"]
    assert [row["record_id"] if row else None for row in rows] == ["r2", None, "r1"]
    assert rows[0]["review_state"] == "rejected" and rows[2]["review_state"] == "accepted"


METADATA_FACETS_QUERY = """
query Q($build_id: String!, $fields: [String!]) {
  corpus_build(build_id: $build_id) { metadata_facets(fields: $fields) }
}
"""


def test_metadata_facets_matches_rest_observed_values(build):
    repo, build_id = build
    rest = _call("GET", f"/api/pdf/corpus-builds/{build_id}/records", params={"limit": 50}).json()
    data = gql(METADATA_FACETS_QUERY, {"build_id": build_id, "fields": None}).json()
    assert "errors" not in data, data
    assert data["data"]["corpus_build"]["metadata_facets"] == rest["metadata_values"]


def test_metadata_facets_can_be_narrowed_to_specific_fields(build):
    repo, build_id = build
    data = gql(METADATA_FACETS_QUERY, {"build_id": build_id, "fields": ["speaker"]}).json()
    assert "errors" not in data, data
    assert set(data["data"]["corpus_build"]["metadata_facets"]) == {"speaker"}


def test_second_reviewer_never_sees_a_sealed_first_answer_through_record_or_rest(build):
    repo, build_id = build
    as_second = gql(RECORD_QUERY, {"build_id": build_id, "record_id": "r4"}, cookie="reviewer-cookie")
    assert "Sealed First Answer" not in as_second.text
    rest_as_second = _call(
        "GET", f"/api/pdf/corpus-builds/{build_id}/records", cookie="reviewer-cookie", params={"limit": 50},
    )
    assert "Sealed First Answer" not in rest_as_second.text

    # The first reviewer is not owed an independent answer, so nothing is hidden from them.
    as_first = gql(RECORD_QUERY, {"build_id": build_id, "record_id": "r4"}, cookie="admin-cookie")
    assert "Sealed First Answer" in as_first.text


def test_researchers_are_forbidden_from_corpus_build(build):
    repo, build_id = build
    data = gql(RECORD_QUERY, {"build_id": build_id, "record_id": "r1"}, cookie="researcher-cookie").json()
    assert data["data"] is None
    assert "Administrator access required" in data["errors"][0]["message"]


def test_the_loader_batches_one_build_read_per_request(build):
    repo, build_id = build

    async def run():
        loaders = RequestLoaders(AccessContext("root", "admin", 1))
        first, second, third = await asyncio.gather(
            loaders.corpus_build_records.load(build_id),
            loaders.corpus_build_records.load(build_id),
            loaders.corpus_build_records.load(build_id),
        )
        return loaders.batch_calls["corpus_build_records"], first, second, third

    calls, first, second, third = asyncio.run(run())
    assert calls == 1
    assert first is second is third
    assert len(first) == 12


VECTOR_RECORDS_QUERY = """
query Q($name: String!) {
  vector_store(name: $name) {
    records { items { chroma_id record_id work text_preview } count offset limit }
  }
}
"""


def test_vector_store_records_apply_researcher_text_policy(monkeypatch):
    admin_record = {
        "_chroma_id": "c1", "record_id": "r1", "work": "Of Grammatology",
        "text": "word " * 500,
    }

    def fake_records_page(access, store_name, **kwargs):
        assert store_name == "Corpus"
        records = [dict(admin_record)]
        if not access.is_admin:
            from app.researcher_view import sanitize_records_payload

            return sanitize_records_payload({"records": records, "count": 1}, max_chars=50)
        return {"records": records, "count": 1}

    monkeypatch.setattr(vector_queries, "records_page", fake_records_page)

    admin_data = gql(VECTOR_RECORDS_QUERY, {"name": "Corpus"}, cookie="admin-cookie").json()
    assert "errors" not in admin_data, admin_data
    admin_page = admin_data["data"]["vector_store"]["records"]
    assert admin_page["items"][0]["chroma_id"] == "c1" and admin_page["count"] == 1

    researcher_data = gql(VECTOR_RECORDS_QUERY, {"name": "Corpus"}, cookie="researcher-cookie").json()
    assert "errors" not in researcher_data, researcher_data
    # Researcher text was summarized server-side before this ever reaches the row projection.
    researcher_items = researcher_data["data"]["vector_store"]["records"]["items"]
    assert len(researcher_items[0]["text_preview"]) < len(admin_page["items"][0]["text_preview"])


def test_vector_store_hides_hidden_and_response_cache_collections_from_researchers(monkeypatch):
    monkeypatch.setattr(
        vector_queries.store, "get_store",
        lambda name: {"name": name, "metadata": {"derridai_hidden_system_collection": True}},
    )
    data = gql(VECTOR_RECORDS_QUERY, {"name": "hidden-store"}, cookie="researcher-cookie").json()
    assert data["data"] is None
    assert "not found" in data["errors"][0]["message"].casefold()

    cache_query = 'query { vector_store(name: "_response_cache") { works { work } } }'
    cache_data = gql(cache_query, cookie="researcher-cookie").json()
    assert cache_data["data"] is None
    assert "not found" in cache_data["errors"][0]["message"].casefold()
