# Copyright 2026 Aaron John Schlosser, PhD.
"""Store-search characterization cases shared by the snapshot and parity tests."""

from __future__ import annotations

from app.models import SearchRequest
from app.routers import stores as stores_router
from store_search_fakes import ADMIN, FakeEmbeddings, fake_store

CASES = [
    {"name": "similarity", "mode": "similarity", "query": "stranger"},
    {"name": "similarity_where", "mode": "similarity", "query": "stranger", "where": {"work": "Given Time"}},
    {"name": "mmr", "mode": "mmr", "query": "stranger", "fetch_k": 4, "lambda_mult": 0.5},
    {"name": "mmr_default", "mode": "mmr", "query": "writing"},
    {"name": "hybrid", "mode": "hybrid", "query": "stranger"},
    {"name": "hybrid_empty_query", "mode": "hybrid", "query": ""},
    {"name": "hybrid_without_embeddings", "mode": "hybrid", "query": "stranger", "embed_error": True},
    {"name": "hybrid_no_tokens", "mode": "hybrid", "query": "!!!"},
    {"name": "similarity_empty_query", "mode": "similarity", "query": ""},
    {"name": "lexical", "mode": "lexical", "query": "stranger"},
    {"name": "lexical_empty_query", "mode": "lexical", "query": ""},
    {"name": "lexical_no_tokens", "mode": "lexical", "query": "!!!"},
    {"name": "keyword", "mode": "keyword", "query": "stranger"},
    {"name": "keyword_case_fold", "mode": "keyword", "query": "STRANGER"},
    {"name": "filter", "mode": "filter", "query": "", "where": {"work": "Of Hospitality"}},
    {"name": "filter_contains", "mode": "filter", "query": "", "where": {"work": {"$contains": "hospitality"}}},
]


def run_case(case, monkeypatch=None):
    embeddings = FakeEmbeddings(error=ValueError("no embedding function") if case.get("embed_error") else None)
    store = fake_store(embeddings=embeddings)
    if monkeypatch is not None:
        monkeypatch.setattr(stores_router, "store", store)
        monkeypatch.setattr(stores_router, "request_user", lambda _request: ADMIN)
    else:
        stores_router.store = store
        stores_router.request_user = lambda _request: ADMIN
    body = SearchRequest(
        query=case["query"],
        mode=case["mode"],
        n_results=3,
        where=case.get("where"),
        **{key: case[key] for key in ("fetch_k", "lambda_mult") if key in case},
    )
    return stores_router.search("db", body, None)
