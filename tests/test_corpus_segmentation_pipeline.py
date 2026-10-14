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

"""Corpus Builder boundary questions run their model calls through the corpus_segmentation pipeline.

Why: which provider answers a boundary question, how many attempts it gets, and when it escalates
to the review provider used to be hard-coded in ``_chat_json``. The pipeline now owns that choice;
deterministic routing, block-ID validation, the confidence threshold, and "failure keeps the
boundary" stay segmentation code.
How: ``chat_complete`` is replaced by a scripted provider, so the tests compare the exact calls the
legacy chain and the pipeline make for both the batch classifier and the second reader, and check
the pass-level traces, identities, and failure handling.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app import corpus_builder as cb
from app import corpus_segmentation_execution as cse
from app.corpus_llm_helpers import _stage_limits
from app.corpus_models import BoundaryAuditResponseModel, BoundaryBatchResponseModel
from app.pipelines import manager as manager_module
from app.pipelines import store as store_module
from app.pipelines.corpus_segmentation import (
    SEGMENTATION_FEATURE,
    SegmentationSession,
    compile_segmentation_pipeline,
)
from app.pipelines.defaults import built_in_assignment, built_in_pipeline
from app.pipelines.manager import pipeline_manager
from app.pipelines.service import PipelineService, pipeline_hash

BUILT_IN = ("corpus.segmentation.current", 1)
REQUEST = {"provider": "ollama", "model": "primary-model"}
WITH_REVIEW = {**REQUEST, "_review_provider": {"provider": "ollama", "model": "review-model"}}
SOURCE = "A stable philosophical paragraph continues its argument."
SPLIT = '{"decisions": [{"after": "b0", "decision": "split", "confidence": 0.9, "changes": ["speaker"]}]}'
KEEP_SEAM = (
    '{"decisions": [{"boundary_id": "r1->r2", "decision": "keep", "confidence": 0.9, '
    '"signals": ["coherent_boundary"], "reason": "ok"}]}'
)


@pytest.fixture
def traces(monkeypatch):
    saved = []
    monkeypatch.setattr(store_module.pipeline_store, "put_run", lambda trace: saved.append(trace) or trace)
    return saved


@pytest.fixture
def manager(tmp_path: Path):
    return cb.PdfCorpusBuildManager(cb.PdfCorpusRepository(tmp_path / "repo"), max_workers=1)


def _build(manager) -> str:
    return manager.repo.create_build({
        "asset_id": "a", "source_sha256": "x", "source_filename": "x.pdf", "source_page_count": 1,
        "source_block_count": 12, "schema_version": cb.SCHEMA_VERSION, "profile_id": cb.PROFILE_VERSION,
        "profile_version": 7, "provider": "ollama", "model": "test", "request": {}, "warnings": [],
    })["build_id"]


def _provider(monkeypatch, replies: dict[str, list[object]]):
    """Script each model's replies in order; an Exception instance is raised instead of returned."""
    calls: list[dict[str, object]] = []

    def fake_chat_complete(**kwargs):
        calls.append({"model": kwargs["model"], "prompt": kwargs["prompt"], "max_tokens": kwargs["max_tokens"]})
        reply = replies[kwargs["model"]].pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(cb, "chat_complete", fake_chat_complete)
    return calls


def _use(monkeypatch, stages):
    source = built_in_pipeline(*BUILT_IN)
    pipeline = source.model_copy(update={
        "pipeline_id": "corpus.segmentation.custom",
        "built_in": False,
        "stages": [stage.model_copy(update=changes) for stage, changes in zip(source.stages, stages)],
    })
    monkeypatch.setattr(
        manager_module.pipeline_manager,
        "resolve",
        lambda _feature: {"pipeline": pipeline.model_dump(mode="json"), "pipeline_hash": pipeline_hash(pipeline)},
    )


def _unresolvable(monkeypatch):
    def broken(_feature):
        raise KeyError("corpus.segmentation.missing@9")

    monkeypatch.setattr(manager_module.pipeline_manager, "resolve", broken)


def _blocks(count: int = 3) -> list[dict[str, object]]:
    return [{"block_id": f"b{i}", "page": 1, "type": "paragraph", "text": SOURCE} for i in range(count)]


def _classify(manager, request):
    candidate = {"index": 0, "after_block_id": "b0", "signals": ["quotation_frame_change"]}
    session = SegmentationSession.open()
    results, failure = manager._segment_candidate_batch([candidate], _blocks(), {}, request, "", session=session)
    session.finish()
    return results, failure


def _seam():
    left = {"record_id": "r1", "text": "A thought that continues", "source_block_ids": ["b1", "b2"]}
    right = {"record_id": "r2", "text": "into the next block.", "source_block_ids": ["b3", "b4"]}
    return left, right


def _legacy(manager, request, prompt, response_model, max_tokens, schema_name, build_id=""):
    try:
        manager._chat_json(
            request, prompt, response_model=response_model, max_tokens=max_tokens,
            schema_name=schema_name, build_id=build_id,
        )
        return None
    except ValueError as exc:
        return str(exc)


def _scenarios(valid: str) -> dict[str, dict[str, list[object]]]:
    return {
        "primary answers": {"primary-model": [valid]},
        "review answers after primary retries": {"primary-model": ["no", "still no"], "review-model": [valid]},
        "both fail": {"primary-model": ["no", "no"], "review-model": ["no", "no"]},
        "primary times out": {"primary-model": [TimeoutError("read timed out")], "review-model": [valid]},
    }


@pytest.mark.parametrize("scenario", sorted(_scenarios(SPLIT)))
@pytest.mark.parametrize("request_", [REQUEST, WITH_REVIEW], ids=["no-review", "review"])
def test_batch_classifier_makes_the_legacy_chains_calls(monkeypatch, manager, traces, scenario, request_) -> None:
    replies = _scenarios(SPLIT)[scenario]
    pipeline_calls = _provider(monkeypatch, {model: list(items) for model, items in replies.items()})
    results, failure = _classify(manager, request_)

    legacy_calls = _provider(monkeypatch, {model: list(items) for model, items in replies.items()})
    legacy_error = _legacy(
        manager, request_, pipeline_calls[0]["prompt"], BoundaryBatchResponseModel,
        min(_stage_limits(request_)["segmentation_num_predict"], 1400), "derridai_boundary_batch_v6",
    )

    assert pipeline_calls == legacy_calls
    assert failure == legacy_error
    assert (results["b0"]["decision"] if results else None) == (None if legacy_error else "split")


@pytest.mark.parametrize("scenario", sorted(_scenarios(KEEP_SEAM)))
@pytest.mark.parametrize("request_", [REQUEST, WITH_REVIEW], ids=["no-review", "review"])
def test_second_reader_makes_the_legacy_chains_calls(monkeypatch, manager, traces, scenario, request_) -> None:
    replies = _scenarios(KEEP_SEAM)[scenario]
    pipeline_calls = _provider(monkeypatch, {model: list(items) for model, items in replies.items()})
    build_id = _build(manager)
    decision = manager._adjudicate_record_boundary_pair(*_seam(), {}, request_, build_id)

    legacy_calls = _provider(monkeypatch, {model: list(items) for model, items in replies.items()})
    legacy_error = _legacy(
        manager, request_, pipeline_calls[0]["prompt"], BoundaryAuditResponseModel,
        min(int(_stage_limits(request_).get("reconciliation_num_predict") or 1000), 1200),
        "derridai_boundary_second_reader_v1", build_id,
    )

    assert pipeline_calls == legacy_calls
    assert decision.get("error") == legacy_error
    assert decision["decision"] == ("uncertain" if legacy_error else "keep")
    # Without a pass session, the reviewer-triggered call is recorded as its own trace.
    assert [trace.run_id for trace in traces] == [decision["pipeline"]["trace_id"]]


def test_built_in_compiles_and_is_assigned() -> None:
    pipeline = built_in_pipeline(*BUILT_IN)
    assert PipelineService().validate(pipeline).valid
    plan = compile_segmentation_pipeline(pipeline)
    assert (plan.entry.id, plan.fallback.id) == ("primary", "review")
    assignment = built_in_assignment(SEGMENTATION_FEATURE)
    assert (assignment.pipeline_id, assignment.pipeline_version) == BUILT_IN
    assert pipeline_manager.runtime_support(pipeline) == {"supported": True, "adapter": SEGMENTATION_FEATURE}


def test_compiler_rejects_another_features_strategy() -> None:
    source = built_in_pipeline(*BUILT_IN)
    pipeline = source.model_copy(update={
        "stages": [stage.model_copy(update={"strategy": "llm.structured_metadata"}) for stage in source.stages],
    })
    with pytest.raises(ValueError, match="does not implement"):
        compile_segmentation_pipeline(pipeline)


def _segment_one_candidate(monkeypatch, manager, request, indexes=(5,)):
    build_id = _build(manager)
    candidates = [
        {
            "after_block_id": f"b{i}", "next_block_id": f"b{i + 1}", "signals": ["quotation_frame_change"],
            "candidate_score": 0.6, "source": "test", "index": i, "protected": False,
        }
        for i in indexes
    ]
    monkeypatch.setattr(cse, "_deterministic_boundary_candidates", lambda blocks, profile: candidates)
    boundaries = manager._segment(_blocks(12), {}, request, build_id)
    return build_id, boundaries


def test_segmentation_pass_is_one_trace_and_checkpoints_its_identity(monkeypatch, manager, traces) -> None:
    _provider(monkeypatch, {"primary-model": [SPLIT.replace("b0", "b5")]})
    build_id, boundaries = _segment_one_candidate(monkeypatch, manager, REQUEST)

    assert [b["after_block_id"] for b in boundaries if b.get("source") == "local_batch_classifier"] == ["b5"]
    (trace,) = traces
    assert trace.feature == SEGMENTATION_FEATURE and trace.status == "completed"
    assert trace.stages[0].parameters["response_contracts"] == ["derridai_boundary_batch_v6"]
    assert SOURCE not in trace.model_dump_json()
    cached = manager.repo.load_checkpoint(build_id, "local_boundary_state", {})["decisions"]["b5"]
    assert cached["pipeline"]["trace_id"] == trace.run_id
    assert cached["pipeline"]["stages"] == [{"stage_id": "primary", "provider_role": "primary", "status": "completed"}]


def test_review_provider_can_answer_boundary_questions_first(monkeypatch, manager, traces) -> None:
    _use(monkeypatch, [
        {"config": {"provider_role": "review", "attempts": 1}, "on_error": None, "on_timeout": None},
        {"enabled": False},
    ])
    calls = _provider(monkeypatch, {"review-model": [SPLIT]})
    results, failure = _classify(manager, WITH_REVIEW)

    assert [call["model"] for call in calls] == ["review-model"]
    assert "ESCALATION REVIEW" not in str(calls[0]["prompt"])
    assert failure is None and results["b0"]["decision"] == "split"


def test_unresolvable_pipeline_keeps_boundaries_without_a_model_call(monkeypatch, manager, traces) -> None:
    _unresolvable(monkeypatch)
    calls = _provider(monkeypatch, {"primary-model": [SPLIT]})
    build_id, boundaries = _segment_one_candidate(monkeypatch, manager, REQUEST)

    build = manager.repo.get_build(build_id)
    assert calls == [] and traces == []
    assert not any(b.get("source") == "local_batch_classifier" for b in boundaries)
    assert build["boundary_classifier_failure_count"] == 1 and build["boundary_llm_keep_count"] == 1
    assert any("corpus segmentation pipeline is unavailable" in warning for warning in build["warnings"])
    # Not cached, so the transition is asked again once the pipeline resolves.
    assert "b5" not in manager.repo.load_checkpoint(build_id, "local_boundary_state", {}).get("decisions", {})


def test_unresolvable_pipeline_leaves_a_reviewer_seam_uncertain(monkeypatch, manager, traces) -> None:
    _unresolvable(monkeypatch)
    calls = _provider(monkeypatch, {"primary-model": [KEEP_SEAM]})
    decision = manager._adjudicate_record_boundary_pair(*_seam(), {}, REQUEST, _build(manager))

    assert calls == [] and traces == []
    assert decision["decision"] == "uncertain" and decision["confidence"] == 0.0
    assert "corpus segmentation pipeline is unavailable" in decision["error"]


def test_second_reader_pass_is_one_trace(monkeypatch, manager, traces) -> None:
    build_id = _build(manager)
    suspects = []
    for index in range(2):
        left, right = _seam()
        left, right = {**left, "record_id": f"r{2 * index + 1}"}, {**right, "record_id": f"r{2 * index + 2}"}
        left["boundary_quality_issues"] = [{"code": "boundary_suspect", "edge": "end"}]
        suspects += [left, right]
    replies = [KEEP_SEAM, KEEP_SEAM.replace("r1->r2", "r3->r4")]
    _provider(monkeypatch, {"primary-model": replies})
    metrics = manager._audit_suspicious_record_boundaries(suspects, {}, REQUEST, build_id)

    assert metrics["audited"] == 2 and metrics["keep"] == 2
    (trace,) = traces
    assert trace.stages[0].input_count == 2
    decisions = manager.repo.load_checkpoint(build_id, "boundary_second_reader", {})["decisions"]
    assert {d["pipeline"]["trace_id"] for d in decisions} == {trace.run_id}


def test_cancelled_segmentation_pass_records_a_cancelled_trace(monkeypatch, manager, traces) -> None:
    _provider(monkeypatch, {"primary-model": [SPLIT.replace("b0", "b5")]})
    profile = manager._profile_for
    monkeypatch.setattr(manager, "_profile_for", lambda build_id: {**profile(build_id), "boundary_batch_size": 1})
    # Checks: before batch 1, before its model call, then before batch 2.
    cancelled = iter([False, False, True])
    monkeypatch.setattr(manager, "_cancelled", lambda _build_id: next(cancelled, True))
    with pytest.raises(InterruptedError):
        _segment_one_candidate(monkeypatch, manager, REQUEST, indexes=(5, 7))

    assert [trace.status for trace in traces] == ["cancelled"]
