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

"""Pipeline adapter for Corpus Builder structured metadata enrichment.

Enrichment asks a chat model for one schema-derived metadata group at a time.
The pipeline controls only how that model call runs (see ``structured_llm_stage``).
It never owns the task itself. The active metadata schema supplies the prompt and
response model, the backend validates every answer, and reconciliation, evidence
binding, FieldAssertion authority, and autofill stay domain code downstream of
this adapter.
"""

from __future__ import annotations

from .models import PipelineDefinition
from .structured_llm_stage import (
    DEFAULT_ATTEMPTS,
    PROVIDER_ROLES,
    StageInvoker,
    StructuredStageFeature,
    StructuredStagePlan,
    StructuredStageSession,
    compile_structured_stage_pipeline,
    stage_attempts,
    stage_role,
)

__all__ = [
    "DEFAULT_ATTEMPTS", "ENRICHMENT", "ENRICHMENT_FEATURE", "ENRICHMENT_PURPOSE", "PROVIDER_ROLES",
    "EnrichmentPlan", "EnrichmentSession", "StageInvoker", "compile_enrichment_pipeline",
    "stage_attempts", "stage_role",
]

ENRICHMENT_FEATURE = "corpus_metadata_enrichment"
ENRICHMENT_PURPOSE = "corpus_metadata_enrichment"
ENRICHMENT = StructuredStageFeature(
    feature=ENRICHMENT_FEATURE,
    purpose=ENRICHMENT_PURPOSE,
    strategy="llm.structured_metadata",
    label="metadata enrichment",
)

EnrichmentPlan = StructuredStagePlan


def compile_enrichment_pipeline(pipeline: PipelineDefinition) -> StructuredStagePlan:
    """Accept: one structured-metadata stage, optionally escalating to one other provider role."""
    return compile_structured_stage_pipeline(pipeline, ENRICHMENT)


class EnrichmentSession(StructuredStageSession):
    """One resolved enrichment pipeline used for a Record's metadata groups, recorded as a single trace."""

    @classmethod
    def open(cls) -> EnrichmentSession:
        return cls.open_for(ENRICHMENT)
