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

"""Pipeline adapter for Corpus Builder record text touch-up proposals.

Touch-up asks a chat model to propose cleaned-up text for one Record, on a reviewer's
request or during metadata enrichment when the build asks for it. The pipeline controls
only how that call runs (see ``structured_llm_stage``).

Everything else stays domain code outside the pipeline: the touch-up prompt, sanitizing the
answer against the source text, and the rule that a touch-up is only a proposal. Reviewed
text changes only when a person approves it.
"""

from __future__ import annotations

from typing import Any

from .models import PipelineDefinition
from .structured_llm_stage import (
    StructuredStageFeature,
    StructuredStagePlan,
    StructuredStageSession,
    compile_structured_stage_pipeline,
)

TEXT_TOUCHUP_FEATURE = "corpus_text_touchup"
TEXT_TOUCHUP = StructuredStageFeature(
    feature=TEXT_TOUCHUP_FEATURE,
    purpose="corpus_text_touchup",
    strategy="llm.text_touchup",
    label="text touch-up",
)


def compile_text_touchup_pipeline(pipeline: PipelineDefinition) -> StructuredStagePlan:
    """Accept: one text touch-up stage, optionally escalating to one other provider role."""
    return compile_structured_stage_pipeline(pipeline, TEXT_TOUCHUP)


class TextTouchupSession(StructuredStageSession):
    """One resolved text touch-up pipeline used for one proposal, recorded as its own trace."""

    @classmethod
    def open(
        cls,
        request: dict[str, Any] | None = None,
    ) -> TextTouchupSession:
        return cls.open_for(TEXT_TOUCHUP, request=request)
