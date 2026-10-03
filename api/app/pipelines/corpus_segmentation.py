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

"""Pipeline adapter for Corpus Builder boundary classification.

Segmentation asks a chat model two kinds of closed-choice boundary question: the batch
classifier (SPLIT or KEEP for transitions deterministic routing left ambiguous) and the
second reader (KEEP, MOVE_EARLIER, MOVE_LATER or UNCERTAIN for a suspicious record seam,
run during the build and on a reviewer's request). The pipeline controls only how each
call runs (see ``structured_llm_stage``).

Topology stays domain code outside the pipeline: deterministic candidate routing, the
adjudication budget, validation of returned block IDs, the confidence threshold, text
conservation, and the rule that a failed, omitted, or low-confidence answer keeps the
boundary where it is.
"""

from __future__ import annotations

from .models import PipelineDefinition
from .structured_llm_stage import (
    StructuredStageFeature,
    StructuredStagePlan,
    StructuredStageSession,
    compile_structured_stage_pipeline,
)

SEGMENTATION_FEATURE = "corpus_segmentation"
SEGMENTATION = StructuredStageFeature(
    feature=SEGMENTATION_FEATURE,
    purpose="corpus_segmentation",
    strategy="llm.boundary_classification",
    label="corpus segmentation",
)


def compile_segmentation_pipeline(pipeline: PipelineDefinition) -> StructuredStagePlan:
    """Accept: one boundary-classification stage, optionally escalating to one other provider role."""
    return compile_structured_stage_pipeline(pipeline, SEGMENTATION)


class SegmentationSession(StructuredStageSession):
    """One resolved segmentation pipeline used for a pass's boundary calls, recorded as a single trace."""

    @classmethod
    def open(cls) -> SegmentationSession:
        return cls.open_for(SEGMENTATION)
