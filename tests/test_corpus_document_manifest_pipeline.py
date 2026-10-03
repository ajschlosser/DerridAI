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

"""The Corpus Builder document manifest runs its model call through the corpus_document_manifest pipeline.

Why: which provider answers the manifest, how many attempts it gets, and when it escalates to the
review provider used to be hard-coded in ``_chat_json``. The pipeline now owns that choice; the
whole-document sample, the embedded-metadata fallback and the deterministic values that outrank the
model stay manifest code.
How: ``chat_complete`` is replaced by a scripted provider, so the tests compare the exact calls the
legacy chain and the pipeline make, and check the trace, the identity checkpoint and failure handling.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app import corpus_builder as cb
from app.corpus_llm_helpers import _stage_limits
from app.pipelines import manager as manager_module
from app.pipelines import store as store_module
from app.pipelines.corpus_document_manifest import (
    DOCUMENT_MANIFEST_FEATURE,
    compile_document_manifest_pipeline,
)
from app.pipelines.defaults import built_in_assignment, built_in_pipeline
from app.pipelines.manager import pipeline_manager
from app.pipelines.service import PipelineService, pipeline_hash
from app.source_audio import spans_from_transcript

BUILT_IN = ("corpus.document_manifest.current", 1)
REQUEST = {"provider": "ollama", "model": "primary-model"}
WITH_REVIEW = {**REQUEST, "_review_provider": {"provider": "ollama", "model": "review-model"}}
SOURCE = "A stable philosophical paragraph continues its argument."
ASSET = {"asset_id": "a", "filename": "x.pdf", "metadata": {"title": "Embedded title"}, "media_kind": "pdf"}
MANIFEST = '{"title": "Model title", "language": "fr"}'


def test_audio_preparation_uses_time_locators_without_page_fields(manager, monkeypatch):
    blocks = spans_from_transcript({
        "text": "First spoken passage. Second spoken passage.",
        "segments": [
            {"start": 0, "end": 4.5, "text": "First spoken passage."},
            {"start": 4.5, "end": 9, "text": "Second spoken passage."},
        ],
    }, [])
    asset = {**ASSET, "filename": "lecture.wav", "media_kind": "audio", "pages": [],
             "metadata": {"title": "Lecture", "author": "Source author"}}
    cb._json_write(manager.repo.asset_meta_path("a"), asset)
    manager.repo.asset_blocks_path("a").write_text(
        "".join(json.dumps(block) + "\n" for block in blocks), encoding="utf-8",
    )
    calls = _provider(monkeypatch, {"primary-model": ['{"title":"Lecture","main_text_start_page":1}']})
    build_id = _build(manager)
    scope = manager._prepare_build_scope(build_id, {**REQUEST, "auto_enrich_work_metadata": False}, False)
    assert scope is not None
    assert scope.source_blocks == blocks
    assert scope.manifest["main_text_start_page"] is None
    assert scope.manifest["main_text_end_page"] is None
    assert scope.manifest["document_author_source"] == "source_metadata"
    assert scope.manifest["document_author"] == "Source author"
    prompt = str(calls[0]["prompt"])
    assert blocks[0]["time_label"] in prompt
    assert "PDF p." not in prompt
    assert "audio" in prompt
    assert manager.repo.get_build(build_id)["stage"] == "segmenting"


def test_audio_manifest_provider_failure_preserves_embedded_metadata(manager, monkeypatch):
    _unresolvable(monkeypatch)
    asset = {**ASSET, "filename": "lecture.wav", "media_kind": "audio"}
    blocks = [{"block_id": "s1", "type": "paragraph", "start": 0, "end": 2, "text": SOURCE}]
    result = manager._document_manifest(asset, blocks, REQUEST, _build(manager))
    assert result["title"] == "Embedded title"
    assert result["main_text_start_page"] is None
    assert "source metadata" in result["notes"]


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
        "source_block_count": 3, "schema_version": cb.SCHEMA_VERSION, "profile_id": cb.PROFILE_VERSION,
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
        "pipeline_id": "corpus.document_manifest.custom",
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
        raise KeyError("corpus.document_manifest.missing@9")

    monkeypatch.setattr(manager_module.pipeline_manager, "resolve", broken)


def _analyse(manager, request, build_id):
    blocks = [{"block_id": f"b{i}", "page": 1, "type": "paragraph", "text": SOURCE} for i in range(3)]
    return manager._document_manifest(ASSET, blocks, request, build_id)


def _fallback_warnings(manager, build_id) -> list[str]:
    prefix = "Document manifest used PDF-metadata fallback: "
    return [w[len(prefix):] for w in manager.repo.get_build(build_id)["warnings"] if w.startswith(prefix)]


def _scenarios() -> dict[str, dict[str, list[object]]]:
    return {
        "primary answers": {"primary-model": [MANIFEST]},
        "review answers after primary retries": {"primary-model": ["no", "still no"], "review-model": [MANIFEST]},
        "both fail": {"primary-model": ["no", "no"], "review-model": ["no", "no"]},
        "primary times out": {"primary-model": [TimeoutError("read timed out")], "review-model": [MANIFEST]},
    }


@pytest.mark.parametrize("scenario", sorted(_scenarios()))
@pytest.mark.parametrize("request_", [REQUEST, WITH_REVIEW], ids=["no-review", "review"])
def test_manifest_makes_the_legacy_chains_calls(monkeypatch, manager, traces, scenario, request_) -> None:
    replies = _scenarios()[scenario]
    pipeline_calls = _provider(monkeypatch, {model: list(items) for model, items in replies.items()})
    build_id = _build(manager)
    manifest = _analyse(manager, request_, build_id)

    legacy_calls = _provider(monkeypatch, {model: list(items) for model, items in replies.items()})
    try:
        manager._chat_json(
            request_, pipeline_calls[0]["prompt"], response_model=cb.DocumentManifestModel,
            max_tokens=_stage_limits(request_)["manifest_num_predict"],
            schema_name="derridai_document_manifest", build_id=build_id,
        )
        legacy_error = None
    except ValueError as exc:
        legacy_error = str(exc)

    assert pipeline_calls == legacy_calls
    assert _fallback_warnings(manager, build_id) == ([legacy_error] if legacy_error else [])
    assert manifest["title"] == ("Embedded title" if legacy_error else "Model title")


def test_built_in_compiles_and_is_assigned() -> None:
    pipeline = built_in_pipeline(*BUILT_IN)
    assert PipelineService().validate(pipeline).valid
    plan = compile_document_manifest_pipeline(pipeline)
    assert (plan.entry.id, plan.fallback.id) == ("primary", "review")
    assignment = built_in_assignment(DOCUMENT_MANIFEST_FEATURE)
    assert (assignment.pipeline_id, assignment.pipeline_version) == BUILT_IN
    assert pipeline_manager.runtime_support(pipeline) == {"supported": True, "adapter": DOCUMENT_MANIFEST_FEATURE}


def test_compiler_rejects_another_features_strategy() -> None:
    source = built_in_pipeline(*BUILT_IN)
    pipeline = source.model_copy(update={
        "stages": [stage.model_copy(update={"strategy": "llm.boundary_classification"}) for stage in source.stages],
    })
    with pytest.raises(ValueError, match="does not implement"):
        compile_document_manifest_pipeline(pipeline)


def test_each_analysis_is_one_trace_with_its_identity_beside_the_manifest(monkeypatch, manager, traces) -> None:
    _provider(monkeypatch, {"primary-model": [MANIFEST, MANIFEST]})
    build_id = _build(manager)
    first = _analyse(manager, REQUEST, build_id)
    _analyse(manager, REQUEST, build_id)  # a reviewer's "analyse again" makes the same call

    assert [trace.feature for trace in traces] == [DOCUMENT_MANIFEST_FEATURE] * 2
    assert traces[0].stages[0].parameters["response_contracts"] == ["derridai_document_manifest"]
    assert SOURCE not in traces[0].model_dump_json()
    runs = manager.repo.load_checkpoint(build_id, "document_manifest_pipeline")["runs"]
    assert [run["trace_id"] for run in runs] == [trace.run_id for trace in traces]
    assert runs[0]["stages"] == [{"stage_id": "primary", "provider_role": "primary", "status": "completed"}]
    # The manifest is sent verbatim in enrichment prompts, so it must not carry the identity.
    assert "pipeline" not in first and traces[0].run_id not in str(first)


def test_review_provider_can_answer_the_manifest_first(monkeypatch, manager, traces) -> None:
    _use(monkeypatch, [
        {"config": {"provider_role": "review", "attempts": 1}, "on_error": None, "on_timeout": None},
        {"enabled": False},
    ])
    calls = _provider(monkeypatch, {"review-model": [MANIFEST]})
    manifest = _analyse(manager, WITH_REVIEW, _build(manager))

    assert [call["model"] for call in calls] == ["review-model"]
    assert "ESCALATION REVIEW" not in str(calls[0]["prompt"])
    assert manifest["title"] == "Model title"


def test_unresolvable_pipeline_uses_embedded_metadata_without_a_model_call(monkeypatch, manager, traces) -> None:
    _unresolvable(monkeypatch)
    calls = _provider(monkeypatch, {"primary-model": [MANIFEST]})
    build_id = _build(manager)
    manifest = _analyse(manager, REQUEST, build_id)

    assert calls == [] and traces == []
    assert manifest["title"] == "Embedded title"
    (warning,) = _fallback_warnings(manager, build_id)
    assert "document manifest pipeline is unavailable" in warning
    assert manager.repo.load_checkpoint(build_id, "document_manifest_pipeline") is None


def test_cancelled_analysis_records_a_cancelled_trace(monkeypatch, manager, traces) -> None:
    _provider(monkeypatch, {"primary-model": ["no", "no"], "review-model": [MANIFEST]})
    # Checks: before each primary attempt, then before the review provider's first attempt.
    cancelled = iter([False, False, True])
    monkeypatch.setattr(manager, "_cancelled", lambda _build_id: next(cancelled, True))
    with pytest.raises(InterruptedError):
        _analyse(manager, WITH_REVIEW, _build(manager))

    assert [trace.status for trace in traces] == ["cancelled"]
