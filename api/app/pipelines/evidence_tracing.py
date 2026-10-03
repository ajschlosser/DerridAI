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

"""Evidence-suggestion adapter from runtime observations to pipeline traces."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import PipelineDefinition, PipelineRunTrace
from .trace_safety import trace_stage


def build_evidence_trace(
    *,
    run_id: str,
    pipeline: PipelineDefinition,
    resolved_hash: str,
    started_at: datetime,
    finished_at: datetime,
    observations: dict[str, dict[str, Any]],
    owner: str | None = None,
    status: str = "completed",
) -> PipelineRunTrace:
    """Translate one reviewer evidence execution into the common trace contract.

    The adapter records only bounded operational diagnostics. Candidate text,
    proposed metadata values, prompts, and reviewer-private state are deliberately
    excluded from pipeline telemetry.
    """

    stages = []
    for stage in pipeline.stages:
        if not stage.enabled:
            continue
        observation = observations.get(stage.id) or {"status": "skipped"}
        stages.append(
            trace_stage(
                stage.id,
                stage.strategy,
                elapsed_seconds=observation.get("elapsed_seconds"),
                input_count=observation.get("input_count"),
                output_count=observation.get("output_count"),
                parameters=observation.get("parameters"),
                provider=observation.get("provider"),
                model=observation.get("model"),
                fallback_reason=observation.get("fallback_reason"),
                warnings=observation.get("warnings"),
                score_summary=observation.get("score_summary"),
                status=str(observation.get("status") or "completed"),
            )
        )

    return PipelineRunTrace(
        run_id=run_id,
        feature="evidence_suggestion.reviewer",
        pipeline_id=pipeline.pipeline_id,
        pipeline_version=pipeline.version,
        resolved_pipeline=pipeline.model_dump(mode="json"),
        resolved_hash=resolved_hash,
        owner=owner,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        total_elapsed_ms=max(0, int((finished_at - started_at).total_seconds() * 1000)),
        stages=stages,
    )
