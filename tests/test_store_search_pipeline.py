# Copyright 2026 Aaron John Schlosser, PhD.
"""General Vector Store search resolves and executes versioned pipelines."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from app.models import SearchRequest
from app.pipelines import manager as manager_module
from app.pipelines import store as pipeline_store_module
from app.pipelines.defaults import built_in_assignment, built_in_pipeline
from app.pipelines.models import InputBinding
from app.pipelines.service import PipelineService, pipeline_hash
from app.pipelines.store_search import (
    MODE_PIPELINES,
    SEARCH_FEATURE,
    compile_store_search_pipeline,
)
from app.routers import stores as stores_router
from fastapi import HTTPException
from store_search_fakes import ADMIN, FakeEmbeddings, fake_store

RESEARCHER = SimpleNamespace(role="researcher", username="reader")


@pytest.fixture
def traces(monkeypatch):
    saved = []
    monkeypatch.setattr(pipeline_store_module.pipeline_store, "put_run", lambda trace: saved.append(trace) or trace)
    return saved


def _search(monkeypatch, *, user=ADMIN, embeddings=None, **body):
    monkeypatch.setattr(stores_router, "store", fake_store(embeddings=embeddings))
    monkeypatch.setattr(stores_router, "request_user", lambda _request: user)
    # The researcher text policy gate is covered elsewhere; these tests are about pipelines.
    monkeypatch.setattr(stores_router, "enforce_researcher_text", lambda _payload: None)
    return stores_router.search("db", SearchRequest(**{"n_results": 3, **body}), None)


def _variant(mode, pipeline_id, stages):
    source = built_in_pipeline(*MODE_PIPELINES[mode])
    return source.model_copy(
        update={"pipeline_id": pipeline_id, "built_in": False, "stages": stages(source.stages)}
    )


def _with_config(stage_id, config):
    return lambda stages: [
        stage.model_copy(update={"config": config}) if stage.id == stage_id else stage for stage in stages
    ]


def test_every_mode_has_a_valid_executable_built_in() -> None:
    service = PipelineService()
    modes = set(SearchRequest.model_fields["mode"].annotation.__args__) - {"assigned"}
    assert modes == set(MODE_PIPELINES)
    for pipeline_id, version in MODE_PIPELINES.values():
        pipeline = built_in_pipeline(pipeline_id, version)
        assert service.validate(pipeline).valid, pipeline_id
        compile_store_search_pipeline(pipeline)
    assignment = built_in_assignment(SEARCH_FEATURE)
    assert (assignment.pipeline_id, assignment.pipeline_version) == MODE_PIPELINES["similarity"]


def test_response_names_the_exact_pipeline_and_trace(monkeypatch, traces) -> None:
    result = _search(monkeypatch, query="stranger", mode="hybrid")

    pipeline = built_in_pipeline(*MODE_PIPELINES["hybrid"])
    assert result["pipeline"] == {
        "feature": SEARCH_FEATURE,
        "pipeline_id": "store_search.hybrid",
        "pipeline_version": 1,
        "pipeline_hash": pipeline_hash(pipeline),
        "trace_id": traces[0].run_id,
    }
    assert traces[0].feature == SEARCH_FEATURE and traces[0].owner == "admin"
    assert [stage.stage_id for stage in traces[0].stages] == ["query", "dense", "lexical", "fuse", "select"]


def test_trace_keeps_identity_and_score_types_without_query_or_filter_values(monkeypatch, traces) -> None:
    _search(monkeypatch, query="stranger", mode="hybrid", where={"work": "Of Hospitality"})

    stages = {stage.stage_id: stage for stage in traces[0].stages}
    assert stages["dense"].collection == "db"
    assert (stages["dense"].provider, stages["dense"].model) == ("local", "fake-embedder")
    assert stages["dense"].parameters["filter_fields"] == ["work"]
    assert stages["dense"].score_summary["score_type"] == "distance"
    assert stages["lexical"].score_summary["score_type"] == "lexical_score"
    assert stages["fuse"].score_summary["score_type"] == "hybrid_score"
    serialized = traces[0].model_dump_json()
    assert "stranger" not in serialized and "Of Hospitality" not in serialized


def test_unhandled_unavailable_stage_fails_the_search(monkeypatch, traces) -> None:
    broken = FakeEmbeddings(error=ValueError("Collection has no query embedding function."))
    with pytest.raises(HTTPException) as caught:
        _search(monkeypatch, query="stranger", mode="similarity", embeddings=broken)
    assert caught.value.status_code == 400
    assert "no query embedding function" in caught.value.detail


def test_configured_fallback_edge_is_traced(monkeypatch, traces) -> None:
    broken = FakeEmbeddings(error=ValueError("Collection has no query embedding function."))
    result = _search(monkeypatch, query="stranger", mode="hybrid", embeddings=broken)

    assert result["results"], "the lexical leg still answers"
    stages = {stage.stage_id: stage for stage in traces[0].stages}
    assert stages["dense"].status == "unavailable"
    assert "no query embedding function" in stages["dense"].fallback_reason


def test_assigned_mode_runs_the_assignment(monkeypatch, traces) -> None:
    single = _variant("similarity", "store_search.one", _with_config("select", {"limit": 1}))

    def resolve(feature):
        assert feature == SEARCH_FEATURE
        return {"pipeline": single.model_dump(mode="json"), "pipeline_hash": pipeline_hash(single)}

    monkeypatch.setattr(manager_module.pipeline_manager, "resolve", resolve)
    result = _search(monkeypatch, query="stranger", mode="assigned")

    assert [row["id"] for row in result["results"]] == ["r1"]
    assert result["pipeline"]["pipeline_id"] == "store_search.one"


def test_stage_config_is_authoritative_over_request_defaults(monkeypatch, traces) -> None:
    pinned = _variant("mmr", "store_search.mmr.pinned", lambda stages: [
        stage.model_copy(update={"config": {"fetch_k": 2}}) if stage.id == "dense"
        else stage.model_copy(update={"config": {"lambda_mult": 1.0}}) if stage.id == "mmr"
        else stage
        for stage in stages
    ])
    monkeypatch.setattr(manager_module.pipeline_manager, "get_definition", lambda _id, _version=None: pinned)

    result = _search(
        monkeypatch, query="stranger", mode="mmr", pipeline_id="store_search.mmr.pinned", pipeline_version=1,
        fetch_k=100, lambda_mult=0.0,
    )

    assert [row["id"] for row in result["results"]] == ["r1", "r2"], "pool of 2, pure relevance order"
    stages = {stage.stage_id: stage for stage in traces[0].stages}
    assert stages["dense"].parameters["fetch_k"] == 2
    assert stages["mmr"].parameters["lambda_mult"] == 1.0


def test_only_administrators_may_name_a_pipeline_version(monkeypatch, traces) -> None:
    with pytest.raises(HTTPException) as caught:
        _search(monkeypatch, user=RESEARCHER, query="stranger", pipeline_id="store_search.hybrid", pipeline_version=1)
    assert caught.value.status_code == 403


def test_researchers_still_receive_sanitized_records(monkeypatch, traces) -> None:
    result = _search(monkeypatch, user=RESEARCHER, query="stranger", mode="similarity")
    assert result["pipeline"]["pipeline_id"] == "store_search.similarity"
    assert result["results"]
    assert all(row["record"]["_researcher_text_policy"]["mode"] == "edmundson" for row in result["results"])


def test_named_pipeline_must_be_a_store_search_pipeline(monkeypatch, traces) -> None:
    with pytest.raises(HTTPException) as caught:
        _search(monkeypatch, query="stranger", pipeline_id="research.current", pipeline_version=1)
    assert "not a store-search pipeline" in caught.value.detail


@pytest.mark.parametrize(
    ("mode", "stages", "match"),
    [
        (
            "lexical",
            lambda stages: [
                stage.model_copy(update={"strategy": "select.mmr"}) if stage.id == "keyword" else stage
                for stage in stages
            ],
            "may only follow semantic similarity",
        ),
        (
            "mmr",
            lambda stages: [
                stage.model_copy(update={"next": ["mmr", "select"]}) if stage.id == "dense" else stage
                for stage in stages
            ],
            "feeds nothing else",
        ),
        ("lexical", _with_config("lexical", {"min_score": 0.5}), "does not apply min_score"),
    ],
)
def test_unsupported_graphs_are_rejected(mode, stages, match) -> None:
    with pytest.raises(ValueError, match=match):
        compile_store_search_pipeline(_variant(mode, "store_search.bad", stages))


def _rebound_hybrid(pipeline_id="store_search.rebound"):
    """Hybrid search whose final selection is bound to the dense leg, bypassing fusion."""

    def stages(source):
        binding = InputBinding(source="stage", stage="dense", output="candidates")
        return [
            stage.model_copy(update={"inputs": {"candidates": [binding]}}) if stage.id == "select" else stage
            for stage in source
        ]

    return _variant("hybrid", pipeline_id, stages)


def test_explicit_input_binding_changes_what_a_stage_receives(monkeypatch) -> None:
    from app.pipelines.store_search import StoreSearchRequest, execute_store_search

    pipeline = _rebound_hybrid()
    plan = compile_store_search_pipeline(pipeline)
    assert "select" in plan.consumers["dense"]
    assert "select" not in plan.consumers.get("fuse", [])

    store = fake_store(embeddings=FakeEmbeddings())
    request = StoreSearchRequest(store="db", query="stranger", n_results=3, where=None, fetch_k=12, lambda_mult=0.5)
    rebound = execute_store_search(plan, store=store, request=request, resolved_hash=pipeline_hash(pipeline))
    similarity = built_in_pipeline(*MODE_PIPELINES["similarity"])
    baseline = execute_store_search(
        compile_store_search_pipeline(similarity),
        store=store,
        request=request,
        resolved_hash=pipeline_hash(similarity),
    )
    assert [row["id"] for row in rebound.results] == [row["id"] for row in baseline.results]
    assert not any("hybrid_score" in row for row in rebound.results)
    assert rebound.trace.warnings == ["rewired_inputs: select.candidates"]
    assert baseline.trace.warnings == []


def test_rebound_store_search_pipeline_is_reported_executable() -> None:
    from app.pipelines.workflows import runtime_support

    support = runtime_support(_rebound_hybrid())
    assert support["supported"] is True


# --- Parallel branches ---------------------------------------------------------------------


def _run(mode, *, parallel, store=None):
    from app.pipelines.store_search import StoreSearchRequest, execute_store_search

    pipeline = built_in_pipeline(*MODE_PIPELINES[mode])
    request = StoreSearchRequest(store="db", query="stranger", n_results=3, where=None, fetch_k=12, lambda_mult=0.5)
    return execute_store_search(
        compile_store_search_pipeline(pipeline),
        store=store or fake_store(embeddings=FakeEmbeddings()),
        request=request,
        resolved_hash=pipeline_hash(pipeline),
        parallel=parallel,
    )


@pytest.mark.parametrize("mode", sorted(MODE_PIPELINES))
def test_parallel_execution_matches_sequential_results_and_stage_order(mode) -> None:
    sequential, overlapped = _run(mode, parallel=False), _run(mode, parallel=True)
    assert overlapped.results == sequential.results
    shape = lambda run: [(s.stage_id, s.status, s.input_count, s.output_count) for s in run.trace.stages]  # noqa: E731
    assert shape(overlapped) == shape(sequential)
    assert [s.stage_id for s in overlapped.trace.stages] == [s.stage_id for s in sequential.trace.stages]


def test_hybrid_legs_really_overlap_and_the_trace_says_so() -> None:
    import threading

    store = fake_store(embeddings=FakeEmbeddings())
    meeting = threading.Barrier(2, timeout=5)  # both legs must be inside at once, or the wait breaks

    def rendezvous(original):
        def wrapped(*args, **kwargs):
            meeting.wait()
            return original(*args, **kwargs)

        return wrapped

    store.search = rendezvous(store.search)
    store.lexical_search = rendezvous(store.lexical_search)
    run = _run("hybrid", parallel=True, store=store)
    assert "branches_overlapped" in run.trace.warnings
    assert _run("hybrid", parallel=False).trace.warnings == []


def test_failed_leg_behaves_the_same_with_and_without_overlap() -> None:
    def broken(*_args, **_kwargs):
        raise RuntimeError("index unavailable")

    for parallel in (False, True):
        store = fake_store(embeddings=FakeEmbeddings())
        store.lexical_search = broken
        with pytest.raises(RuntimeError, match="index unavailable"):
            _run("hybrid", parallel=parallel, store=store)


def test_undeclared_strategies_are_exclusive() -> None:
    from app.pipelines.contracts import strategy_concurrency

    assert strategy_concurrency("fusion.rrf") == "exclusive"
    assert strategy_concurrency("not.registered") == "exclusive"
    assert strategy_concurrency("retrieve.lexical_bm25") == "safe"
    assert strategy_concurrency("retrieve.chroma_similarity") == "provider_limited"
