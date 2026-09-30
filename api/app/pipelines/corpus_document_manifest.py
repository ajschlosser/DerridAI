# Copyright 2026 Aaron John Schlosser, PhD.
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
