# Copyright 2026 Aaron John Schlosser, PhD.
"""Pipeline adapter for Corpus Builder record text touch-up proposals.

Touch-up asks a chat model to propose cleaned-up text for one Record, on a reviewer's
request or during metadata enrichment when the build asks for it. The pipeline controls
only how that call runs (see ``structured_llm_stage``).

Everything else stays domain code outside the pipeline: the touch-up prompt, sanitizing the
answer against the source text, and the rule that a touch-up is only a proposal. Reviewed
text changes only when a person approves it.
"""

from __future__ import annotations

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
    def open(cls) -> TextTouchupSession:
        return cls.open_for(TEXT_TOUCHUP)
