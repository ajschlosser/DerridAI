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

"""Metadata pre-fill retrieval and hints run through the metadata_prefill pipeline."""

from __future__ import annotations

import pytest
from app import memory_prefill as mp
from app.pipelines import store as store_module
from app.pipelines.defaults import built_in_assignment, built_in_pipeline
from app.pipelines.metadata_prefill import PREFILL_FEATURE, compile_prefill_pipeline
from app.pipelines.service import PipelineService, pipeline_hash
from test_memory_prefill import (
    ROLE_A,
    ROLE_B,
    SPAN,
    FakeCollection,
    FakeIndex,
    meta,
    run,
)

BUILT_IN = ("metadata.prefill.current", 1)
AGREE = [(meta("discourse_role", ROLE_A, "b-old", "x1"), 0.05), (meta("discourse_role", ROLE_A, "b-old", "x2"), 0.07)]
RIVALS = [
    (meta("discourse_role", ROLE_A, "b-old", "x1"), 0.05), (meta("discourse_role", ROLE_A, "b-old", "x2"), 0.06),
    (meta("discourse_role", ROLE_B, "b-old", "x3"), 0.05), (meta("discourse_role", ROLE_B, "b-old", "x4"), 0.06),
]


@pytest.fixture
def traces(monkeypatch):
    saved = []
    monkeypatch.setattr(store_module.pipeline_store, "put_run", lambda trace: saved.append(trace) or trace)
    return saved


def _custom(monkeypatch, stage_id, config=None, **update):
    source = built_in_pipeline(*BUILT_IN)
    pipeline = source.model_copy(update={
        "pipeline_id": "metadata.prefill.custom",
        "built_in": False,
        "stages": [
            stage.model_copy(update={**({"config": config} if config is not None else {}), **update})
            if stage.id == stage_id else stage
            for stage in source.stages
        ],
    })
    monkeypatch.setattr(mp, "resolve_prefill_plan", lambda: (compile_prefill_pipeline(pipeline), pipeline_hash(pipeline)))
    return pipeline


def test_built_in_reproduces_the_legacy_settings() -> None:
    pipeline = built_in_pipeline(*BUILT_IN)
    assert PipelineService().validate(pipeline).valid
    plan = compile_prefill_pipeline(pipeline)
    assert (plan.fetch_k, plan.normalization, plan.hint_limit, plan.hint_min_similarity) == (
        8, "inverse_distance", 3, 0.72
    )
    assert plan.similarity(0.0) == 1.0 and plan.similarity(1.0) == 0.5
    assignment = built_in_assignment(PREFILL_FEATURE)
    assert (assignment.pipeline_id, assignment.pipeline_version) == BUILT_IN


def test_retrieval_depth_comes_from_the_pipeline(monkeypatch, traces) -> None:
    requested = []

    class Recording(FakeCollection):
        def query(self, *, n_results, **kwargs):
            requested.append(n_results)
            return super().query(n_results=n_results, **kwargs)

    index = FakeIndex(AGREE)
    index.collection = Recording(AGREE)
    run(AGREE, index=index)
    _custom(monkeypatch, "retrieve", {"fetch_k": 3})
    run(AGREE, index=index)
    assert requested == [8, 3]


def test_hint_selection_comes_from_the_pipeline(monkeypatch, traces) -> None:
    record, _ = run(RIVALS)
    assert len(record["memory_hints"]["discourse_role"]) == 2

    _custom(monkeypatch, "hints", {"limit": 1, "min_similarity": 0.72})
    record, _ = run(RIVALS)
    assert len(record["memory_hints"]["discourse_role"]) == 1

    _custom(monkeypatch, "hints", {"limit": 3, "min_similarity": 0.99})
    record, _ = run(RIVALS)
    assert "memory_hints" not in record


def test_pre_fill_policy_is_not_a_pipeline_setting(monkeypatch, traces) -> None:
    _custom(monkeypatch, "hints", {"limit": 20, "min_similarity": 0.0})
    record, summary = run([(meta("discourse_role", ROLE_A, "b-old", "x1"), 0.0)])
    assert summary["prefilled"] == 0, "one earlier record never pre-fills, however loose the hints"
    assert record["memory_hints"]["discourse_role"][0]["value"] == ROLE_A


def test_build_summary_and_trace_name_the_exact_pipeline(traces) -> None:
    _, summary = run(AGREE)

    pipeline = built_in_pipeline(*BUILT_IN)
    assert summary["pipeline"] == {
        "feature": PREFILL_FEATURE,
        "pipeline_id": "metadata.prefill.current",
        "pipeline_version": 1,
        "pipeline_hash": pipeline_hash(pipeline),
        "trace_id": traces[0].run_id,
    }
    trace = traces[0]
    assert trace.status == "completed"
    assert [stage.stage_id for stage in trace.stages] == ["retrieve", "normalize", "hints"]
    stages = {stage.stage_id: stage for stage in trace.stages}
    assert (stages["retrieve"].input_count, stages["retrieve"].output_count) == (1, 2)
    assert (stages["retrieve"].provider, stages["retrieve"].model) == ("ollama", "bge-m3")
    assert stages["normalize"].score_summary["score_type"] == "similarity"
    assert stages["hints"].output_count == 1
    assert SPAN not in trace.model_dump_json()


def test_unavailable_embedder_is_traced_as_a_failed_retrieval(traces) -> None:
    _, summary = run(AGREE, index=FakeIndex(AGREE, error=RuntimeError("provider down")))

    assert summary["status"] == "unavailable"
    assert traces[0].status == "failed"
    retrieve = traces[0].stages[0]
    assert retrieve.stage_id == "retrieve" and retrieve.status == "failed"
    assert "provider down" in retrieve.fallback_reason


def test_unresolvable_assignment_is_reported_and_never_blocks_the_build(monkeypatch) -> None:
    def missing():
        raise KeyError("metadata_prefill")

    monkeypatch.setattr(mp, "resolve_prefill_plan", missing)
    record, summary = run(AGREE)
    assert summary["status"] == "unavailable" and "metadata_prefill" in summary["error"]
    assert record.get("discourse_role") in (None, "")


@pytest.mark.parametrize(
    ("stage_id", "update", "match"),
    [
        ("retrieve", {"on_unavailable": "hints"}, "no fallback stages"),
        ("normalize", {"config": {"method": "metric"}}, "normalization method"),
        ("retrieve", {"next": ["hints"]}, "retrieval, then normalization"),
    ],
)
def test_unsupported_graphs_are_rejected(stage_id, update, match) -> None:
    source = built_in_pipeline(*BUILT_IN)
    pipeline = source.model_copy(update={
        "pipeline_id": "metadata.prefill.bad",
        "built_in": False,
        "stages": [stage.model_copy(update=update) if stage.id == stage_id else stage for stage in source.stages],
    })
    with pytest.raises(ValueError, match=match):
        compile_prefill_pipeline(pipeline)
