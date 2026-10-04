# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

from __future__ import annotations

import pytest

from app.models import RAGRunRequest
from app.pipelines.defaults import built_in_pipeline
from app.pipelines.models import PipelineConfigOverrideSet
from app.pipelines.overrides import resolve_pipeline_config
from app.pipelines.research import (
    compile_research_pipeline,
    resolve_research_runtime_settings,
)


def _override(stages: dict[str, dict[str, object]]) -> PipelineConfigOverrideSet:
    return PipelineConfigOverrideSet(
        pipeline_id="research.current",
        pipeline_version=1,
        stages=stages,
    )


def test_rag_request_accepts_distinct_settings_and_run_override_layers() -> None:
    request = RAGRunRequest.model_validate(
        {
            "prompt": "What is différance?",
            "settings_pipeline_overrides": {
                "pipeline_id": "research.current",
                "pipeline_version": 1,
                "stages": {"rerank": {"top_k": 31}},
            },
            "run_pipeline_overrides": {
                "pipeline_id": "research.current",
                "pipeline_version": 1,
                "stages": {"rerank": {"top_k": 48}},
            },
        }
    )

    assert request.settings_pipeline_overrides is not None
    assert request.run_pipeline_overrides is not None
    assert request.settings_pipeline_overrides.stages["rerank"]["top_k"] == 31
    assert request.run_pipeline_overrides.stages["rerank"]["top_k"] == 48


def test_settings_overrides_pipeline_stage_configuration() -> None:
    pipeline = built_in_pipeline("research.current", 1)
    assert pipeline is not None

    resolution = resolve_pipeline_config(
        pipeline,
        settings_overrides=_override(
            {
                "dense": {"fetch_k": 750},
                "rrf": {"rrf_k": 41},
                "rerank": {"top_k": 31},
                "pack": {"total_char_limit": 90000},
            }
        ),
    )
    plan = compile_research_pipeline(resolution.effective)
    runtime = resolve_research_runtime_settings(
        plan,
        {
            "k": 64,
            "fetch_k": 500,
            "rrf_k": 60,
            "rerank_top_n": 24,
            "evidence_total_char_limit": 120000,
        },
    )

    assert runtime.semantic_fetch_k == 750
    assert runtime.rrf_k == 41
    assert runtime.rerank_top_n == 31
    assert runtime.evidence_total_char_limit == 90000
    assert resolution.provenance["rerank"]["top_k"] == {
        "pipeline": 24,
        "settings": 31,
        "run": None,
        "effective": 31,
        "source": "settings",
    }


def test_run_overrides_settings_and_pipeline_configuration() -> None:
    pipeline = built_in_pipeline("research.current", 1)
    assert pipeline is not None

    resolution = resolve_pipeline_config(
        pipeline,
        settings_overrides=_override(
            {
                "dense": {"fetch_k": 750},
                "rerank": {"top_k": 31},
            }
        ),
        run_overrides=_override(
            {
                "dense": {"fetch_k": 900},
                "rerank": {"top_k": 48},
            }
        ),
    )
    plan = compile_research_pipeline(resolution.effective)
    runtime = resolve_research_runtime_settings(
        plan,
        {"k": 64, "fetch_k": 500, "rerank_top_n": 24},
    )

    assert runtime.semantic_fetch_k == 900
    assert runtime.rerank_top_n == 48
    assert resolution.provenance["rerank"]["top_k"]["source"] == "run"
    assert resolution.provenance["rerank"]["top_k"]["pipeline"] == 24
    assert resolution.provenance["rerank"]["top_k"]["settings"] == 31
    assert resolution.provenance["rerank"]["top_k"]["run"] == 48
    assert resolution.provenance["rerank"]["top_k"]["effective"] == 48


def test_overrides_are_bound_to_exact_pipeline_version() -> None:
    pipeline = built_in_pipeline("research.current", 1)
    assert pipeline is not None

    with pytest.raises(ValueError, match="target.*research.current@2"):
        resolve_pipeline_config(
            pipeline,
            settings_overrides=PipelineConfigOverrideSet(
                pipeline_id="research.current",
                pipeline_version=2,
                stages={"rerank": {"top_k": 32}},
            ),
        )


@pytest.mark.parametrize(
    ("stages", "message"),
    [
        ({"missing": {"top_k": 12}}, "stage.*missing"),
        ({"rerank": {"not_a_setting": 12}}, "not declared"),
        ({"rerank": {"top_k": 0}}, "at least 1"),
    ],
)
def test_invalid_override_targets_are_rejected(
    stages: dict[str, dict[str, object]],
    message: str,
) -> None:
    pipeline = built_in_pipeline("research.current", 1)
    assert pipeline is not None

    with pytest.raises(ValueError, match=message):
        resolve_pipeline_config(
            pipeline,
            run_overrides=_override(stages),
        )
