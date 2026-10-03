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

"""Pipeline adapter for the reviewer's explicit request that a model choose evidence.

In Record review a reviewer can ask a chat model which of the Record's own source units
support a metadata value. The pipeline controls only how that call runs (see
``structured_llm_stage``).

Everything else stays domain code outside the pipeline: the closed-choice prompt over the
Record's current source-unit IDs, deterministic validation of every returned ID and of its
lexical support, and the rule that a suggestion is advisory until a reviewer binds it.
The reviewer evidence-suggestion pipeline and evidence recovery keep their own assignments.
"""

from __future__ import annotations

from .models import PipelineDefinition
from .structured_llm_stage import (
    StructuredStageFeature,
    StructuredStagePlan,
    StructuredStageSession,
    compile_structured_stage_pipeline,
)

REVIEWER_EVIDENCE_CHOICE_FEATURE = "corpus_reviewer_evidence_choice"
REVIEWER_EVIDENCE_CHOICE = StructuredStageFeature(
    feature=REVIEWER_EVIDENCE_CHOICE_FEATURE,
    purpose="corpus_reviewer_evidence_choice",
    strategy="llm.reviewer_evidence_choice",
    label="reviewer evidence choice",
)


def compile_reviewer_evidence_choice_pipeline(pipeline: PipelineDefinition) -> StructuredStagePlan:
    """Accept: one evidence-choice stage, optionally escalating to one other provider role."""
    return compile_structured_stage_pipeline(pipeline, REVIEWER_EVIDENCE_CHOICE)


class ReviewerEvidenceChoiceSession(StructuredStageSession):
    """One resolved evidence-choice pipeline used for one reviewer request, recorded as its own trace."""

    @classmethod
    def open(cls) -> ReviewerEvidenceChoiceSession:
        return cls.open_for(REVIEWER_EVIDENCE_CHOICE)
