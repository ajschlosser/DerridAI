# Copyright 2026 Aaron John Schlosser, PhD.
"""Prompt/schema version constants, the corpus-profile registry, and the Pydantic
response models validated against LLM output for segmentation, metadata, and
document-manifest inference.

Moved verbatim out of corpus_builder.py: these definitions have no dependency on
PdfCorpusRepository or PdfCorpusBuildManager, only on pydantic and corpus_metadata's
closed vocabularies, so extracting them unblocks every method that was previously
deferred by the circular import (extracted during the 0.70 decomposition).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .corpus_metadata import (
    DISCOURSE_ROLES,
    HYBRID_REQUIRED_FIELDS,
    REGION_TYPES,
    REVIEW_METADATA_FIELDS,
)

SCHEMA_VERSION = "pdf-corpus-v3"



SEGMENTATION_PROMPT_VERSION = "derridai-local-boundaries-v7"



METADATA_PROMPT_VERSION = "derridai-record-metadata-v11"



DOCUMENT_PROMPT_VERSION = "derridai-document-manifest-v3"



PROFILE_VERSION = "derrida-scholarly-v12"



class DocumentManifestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = None
    short_title: str | None = None
    original_title: str | None = None
    document_author: str | None = None
    translator: str | None = None
    publisher: str | None = None
    publication_place: str | None = None
    publication_year: int | str | None = None
    edition: str | None = None
    isbn: str | None = None
    language: str | None = None
    original_language: str | None = None
    document_is_translation: bool | None = None
    document_type: str | None = None
    main_text_start_page: int | None = None
    main_text_end_page: int | None = None
    notes: str = ""

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_nullable_notes(cls, value: Any) -> str:
        # Optional LLM manifest notes may be JSON null. Normalize that at
        # the schema boundary so an internal validation detail never reaches UI.
        return "" if value is None else str(value)



class BoundaryChangeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    speaker: bool = False
    position_holder: bool = False
    stance: bool = False
    target: bool = False
    quotation_frame: bool = False
    discourse_role: bool = False
    argumentative_move: bool = False



class BoundaryDecisionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    after_block_id: str
    decision: Literal["split", "keep", "uncertain"] = "uncertain"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = ""
    change: BoundaryChangeModel = Field(default_factory=BoundaryChangeModel)



class PageMarkerChoiceModel(BaseModel):
    """A model's choice among candidate lines: which ones are printed page numbers."""
    model_config = ConfigDict(extra="forbid")
    page_marker_ids: list[int] = Field(default_factory=list, max_length=400)


class SegmentationResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    boundaries: list[BoundaryDecisionModel] = Field(default_factory=list)



class ReconciliationDecisionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    after_block_id: str
    decision: Literal["split", "keep"]
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = ""



class ReconciliationResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decisions: list[ReconciliationDecisionModel] = Field(default_factory=list)



class FieldEvidenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    block_ids: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    reason: str = ""



class RecordMetadataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: str | None = None
    region_type: str | None = None
    region_author: str | None = None
    primary_text: bool | None = None
    speaker: str | None = None
    position_holder: str | None = None
    target: str | None = None
    discourse_role: str | None = None
    proposition_status: str | None = None
    semantic_function: list[str] = Field(default_factory=list)
    stance: str | None = None
    claim_scope: str | None = None
    is_direct_quote: bool | None = None
    quoted_speaker: list[str] = Field(default_factory=list)
    quoted_author: list[str] = Field(default_factory=list)
    quoted_work: list[str] = Field(default_factory=list)
    quoted_position_holder: list[str] = Field(default_factory=list)
    quoted_addressee: list[str] = Field(default_factory=list)
    quoted_referent: list[str] = Field(default_factory=list)
    quotation_chain: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    persons: list[str] = Field(default_factory=list)
    works_referenced: list[str] = Field(default_factory=list)



class MetadataResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metadata: RecordMetadataModel = Field(default_factory=RecordMetadataModel)
    field_evidence: dict[str, FieldEvidenceModel] = Field(default_factory=dict)
    review_reason: str = ""



BoundaryDimension = Literal[
    "speaker", "position_holder", "stance", "target", "quotation_frame",
    "discourse_role", "argumentative_move",
]



class CompactBoundaryDecisionModel(BaseModel):
    """Compact boundary response used by book-scale segmentation.

    Large prose reasons and nested boolean objects were a major source of local
    model truncation. The corpus builder asks only for the topology-changing
    facts here; uncertain boundaries can be adjudicated in a later, smaller call.
    """
    model_config = ConfigDict(extra="forbid")
    after: str = Field(min_length=1, max_length=200)
    decision: Literal["split", "keep", "uncertain"] = "uncertain"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    changes: list[BoundaryDimension] = Field(default_factory=list, max_length=7)



class PairBoundaryResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["split", "keep", "uncertain"] = "uncertain"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    changes: list[BoundaryDimension] = Field(default_factory=list, max_length=7)



class BatchBoundaryDecisionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    after: str = Field(min_length=1, max_length=200)
    decision: Literal["split", "keep"]
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    changes: list[BoundaryDimension] = Field(default_factory=list, max_length=7)



class BoundaryBatchResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decisions: list[BatchBoundaryDecisionModel] = Field(default_factory=list, max_length=12)



class BoundaryAuditDecisionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    boundary_id: str = Field(min_length=1, max_length=240)
    decision: Literal["keep", "move_earlier", "move_later", "uncertain"] = "uncertain"
    suggested_after_block_id: str | None = Field(default=None, max_length=200)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    signals: list[str] = Field(default_factory=list, max_length=8)
    reason: str = Field(default="", max_length=500)



class BoundaryAuditResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decisions: list[BoundaryAuditDecisionModel] = Field(default_factory=list, max_length=12)



class CompactSegmentationResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    boundaries: list[CompactBoundaryDecisionModel] = Field(default_factory=list, max_length=96)



class CompactReconciliationDecisionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    after: str = Field(min_length=1, max_length=200)
    decision: Literal["split", "keep"]
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)



class CompactReconciliationResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decisions: list[CompactReconciliationDecisionModel] = Field(default_factory=list, max_length=16)



class DiscourseMetadataModel(BaseModel):
    # Every field is required (null when unsupported). Optional fields let
    # schema-constrained decoders omit them, which small models do routinely.
    model_config = ConfigDict(extra="forbid")
    language: str | None
    region_type: Literal["front_matter", "main_text", "notes", "bibliography", "index", "appendix", "back_matter", "paratext", "unknown"] | None
    region_author: str | None
    primary_text: bool | None
    speaker: str | None
    position_holder: str | None
    target: str | None
    discourse_role: Literal["assertion", "analysis", "quotation", "reported_position", "critique", "qualification", "transition", "question", "definition", "example", "commentary", "paratext", "bibliographic"] | None
    proposition_status: str | None
    semantic_function: list[str] = Field(max_length=12)
    stance: str | None
    claim_scope: str | None



class RecordFieldAssessmentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # The property is required; an explicit null means confidence is unavailable.
    confidence: float | None = Field(ge=0.0, le=1.0)
    needs_review: bool
    reason: str = Field(max_length=500)
    outcome: Literal["supported_value", "no_supported_value", "uncertain"]



class DiscourseMetadataResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Required so schema-constrained decoding cannot return assessments alone.
    metadata: DiscourseMetadataModel
    field_evidence: dict[str, FieldEvidenceModel] = Field(default_factory=dict)
    field_assessments: dict[str, RecordFieldAssessmentModel]
    review_reason: str = Field(default="", max_length=1000)



class QuotationMetadataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_direct_quote: bool | None
    quoted_speaker: list[str] = Field(max_length=12)
    quoted_author: list[str] = Field(max_length=12)
    quoted_work: list[str] = Field(max_length=12)
    quoted_position_holder: list[str] = Field(max_length=12)
    quoted_addressee: list[str] = Field(max_length=12)
    quoted_referent: list[str] = Field(max_length=12)
    quotation_chain: list[str] = Field(max_length=16)



class QuotationMetadataResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Required so schema-constrained decoding cannot return assessments alone.
    metadata: QuotationMetadataModel
    field_evidence: dict[str, FieldEvidenceModel] = Field(default_factory=dict)
    field_assessments: dict[str, RecordFieldAssessmentModel]
    review_reason: str = Field(default="", max_length=1000)



class IndexMetadataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topics: list[str] = Field(max_length=24)
    concepts: list[str] = Field(max_length=24)
    persons: list[str] = Field(max_length=24)
    works_referenced: list[str] = Field(max_length=24)



class TextTouchupResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1)
    changes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)



class IndexMetadataResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Required so schema-constrained decoding cannot return assessments alone.
    metadata: IndexMetadataModel
    field_assessments: dict[str, RecordFieldAssessmentModel]
    review_reason: str = Field(default="", max_length=1000)



CORPUS_PROFILES: dict[str, dict[str, Any]] = {
    PROFILE_VERSION: {
        "id": PROFILE_VERSION,
        "name": "Derrida scholarly corpus v12",
        "version": 12,
        "description": "Testy Titmouse: reviewer-owned document structure outranks semantic inference, closed-vocabulary LLM output is normalized with raw provenance retained, and field-level LLM participation remains auditable.",
        "boundary_dimensions": ["speaker", "position_holder", "stance", "target", "quotation_frame", "discourse_role", "argumentative_move"],
        "discourse_roles": DISCOURSE_ROLES,
        "region_types": REGION_TYPES,
        "required_metadata_fields": list(HYBRID_REQUIRED_FIELDS),
        "publication_required_metadata_fields": list(HYBRID_REQUIRED_FIELDS),
        "publication_required_document_fields": ["title", "document_author"],
        "review_metadata_fields": list(REVIEW_METADATA_FIELDS),
        "min_boundary_confidence": 0.72,
        "candidate_llm_threshold": 0.30,
        "deterministic_split_threshold": 0.92,
        "review_risk_threshold": 0.90,
        "max_llm_boundary_calls_per_100_atoms": 18,
        "boundary_batch_size": 6,
        "min_metadata_confidence": 0.65,
        "soft_min_chars": 180,
        "preferred_record_chars": 1750,
        "record_length_tolerance": 200,
        "long_record_chars": 3500,
        "absolute_record_chars": 6000,
        "soft_max_chars": 3500,
        "topology_review_chars": 6000,
    }
}

