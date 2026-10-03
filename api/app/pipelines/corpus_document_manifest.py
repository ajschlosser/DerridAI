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

"""Pipeline adapter for the Corpus Builder document manifest.

The manifest asks a chat model once per analysis for a source-bound description of the
document (bibliography, language, main-text page range), when a build starts and when a
reviewer asks for the document to be analysed again. The pipeline controls only how that
call runs (see ``structured_llm_stage``).

Everything else stays domain code outside the pipeline: the whole-document sample and
prompt, the embedded-PDF-metadata fallback when the call fails, and the deterministic
values that outrank the model (embedded author, a confident start-page inference, the
reviewer-confirmed layout, media-specific page semantics, ingest metadata).
"""

from __future__ import annotations

from .models import PipelineDefinition
from .structured_llm_stage import (
    StructuredStageFeature,
    StructuredStagePlan,
    StructuredStageSession,
    compile_structured_stage_pipeline,
)

DOCUMENT_MANIFEST_FEATURE = "corpus_document_manifest"
DOCUMENT_MANIFEST = StructuredStageFeature(
    feature=DOCUMENT_MANIFEST_FEATURE,
    purpose="corpus_document_manifest",
    strategy="llm.document_manifest",
    label="document manifest",
)


def compile_document_manifest_pipeline(pipeline: PipelineDefinition) -> StructuredStagePlan:
    """Accept: one document-manifest stage, optionally escalating to one other provider role."""
    return compile_structured_stage_pipeline(pipeline, DOCUMENT_MANIFEST)


class DocumentManifestSession(StructuredStageSession):
    """One resolved document-manifest pipeline used for one analysis, recorded as its own trace."""

    @classmethod
    def open(cls) -> DocumentManifestSession:
        return cls.open_for(DOCUMENT_MANIFEST)
