# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import re
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator

from .enrichment_cycles import MAX_PASSES
from .metadata_schema import MetadataSchema

LanguageCode = Literal["en", "fr"]
CollectionRole = Literal["primary", "language", "general"]
RetrievalMode = Literal["semantic", "hybrid", "lexical"]
DistanceMetric = Literal["cosine", "l2", "ip"]
SearchType = Literal["mmr", "similarity", "lexical"]
TextCleanupRule = Literal[
    "page_numbers",
    "repeated_short_lines",
    "line_hyphenation",
    "paragraph_lines",
    "empty_lines",
    "ocr_artifacts",
    "whitespace",
]


def _default_locales() -> list[LanguageCode]:
    return ["en", "fr"]


def _default_search_types() -> list[SearchType]:
    return ["similarity", "lexical", "mmr"]


def _default_text_cleanup_rules() -> list[TextCleanupRule]:
    return [
        "page_numbers",
        "repeated_short_lines",
        "line_hyphenation",
        "paragraph_lines",
        "empty_lines",
        "ocr_artifacts",
        "whitespace",
    ]


def _clamp_concurrency(value: Any) -> Any:
    """A provider profile may allow more parallel requests (a FreeLLM profile defaults to 32) than one corpus operation
    uses. Clamp to the operation's ceiling instead of rejecting the whole request with a 422."""
    try:
        return max(1, min(16, int(value)))
    except (TypeError, ValueError):
        return value


ClampedConcurrency = Annotated[int, BeforeValidator(_clamp_concurrency)]


class ChromaPathUpdate(BaseModel):
    path: str = Field(min_length=1, max_length=4096)


class ChromaConnectionUpdate(BaseModel):
    """Switch or probe the Chroma backend. Token omitted keeps the current secret."""

    mode: Literal["embedded", "http"]
    path: str | None = Field(default=None, max_length=4096)
    url: str | None = Field(default=None, max_length=2048)
    token: str | None = Field(default=None, max_length=4096)
    tenant: str | None = Field(default=None, max_length=128)
    database: str | None = Field(default=None, max_length=128)


class StoreCreate(BaseModel):
    name: str = Field(min_length=3, max_length=128)
    metadata: dict[str, Any] | None = None
    description: str | None = Field(default=None, max_length=2000)
    embedding_provider: Literal["chroma", "ollama", "precomputed"] | None = None
    embedding_model: str | None = None
    embedding_dimension: int | None = Field(default=None, ge=1, le=65536)
    distance_metric: DistanceMetric = "cosine"
    retrieval_mode: RetrievalMode = "hybrid"
    text_field: str = Field(default="text", min_length=1, max_length=128)
    filter_fields: list[str] = Field(default_factory=list, max_length=128)
    language_codes: list[LanguageCode] | None = None
    collection_role: CollectionRole | None = None
    protected: bool = False

    @field_validator("name")
    @classmethod
    def _validate_collection_name(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*[A-Za-z0-9]", value):
            raise ValueError(
                "Collection names must start and end with a letter or number and "
                "contain only letters, numbers, periods, underscores, or hyphens."
            )
        if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", value):
            raise ValueError("Collection names cannot be IPv4 addresses.")
        return value

    @field_validator("filter_fields")
    @classmethod
    def _validate_filter_fields(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value or len(value) > 128:
                raise ValueError("Filter field names must contain 1 to 128 characters.")
            if value.startswith("__derridai_") or value.startswith("_chroma_"):
                raise ValueError("Reserved internal fields cannot be declared filter fields.")
            if value not in cleaned:
                cleaned.append(value)
        return cleaned


class EmbeddingPreflightRequest(BaseModel):
    embedding_provider: Literal["chroma", "ollama", "precomputed"] = "ollama"
    embedding_model: str | None = None
    embedding_dimension: int | None = Field(default=None, ge=1, le=65536)
    distance_metric: DistanceMetric = "cosine"


class StoreProtectionUpdate(BaseModel):
    protected: bool


class StoreEmbeddingUpdate(BaseModel):
    embedding_provider: Literal["chroma", "ollama", "precomputed"]
    embedding_model: str | None = None


class StoreLanguageUpdate(BaseModel):
    language_codes: list[LanguageCode] = Field(default_factory=list)
    collection_role: CollectionRole | None = None


class DeriveLanguageStoresRequest(BaseModel):
    en_name: str | None = None
    fr_name: str | None = None
    overwrite: bool = True


class RecordUpsert(BaseModel):
    record: dict[str, Any]
    document_field: str = "text"
    id_field: str = "record_id"
    embedding_field: str = "embedding"
    id_prefix: str | None = None
    include_updates: bool = False


class StoredRecordPatch(BaseModel):
    changes: dict[str, Any] = Field(default_factory=dict)
    audit_entries: list[dict[str, Any]] = Field(default_factory=list, max_length=500)
    document_field: str = "text"
    embedding_field: str = "embedding"


class BulkUpsertItem(BaseModel):
    record: dict[str, Any]
    chroma_id: str | None = None
    audit_entries: list[dict[str, Any]] = Field(default_factory=list, max_length=5000)
    replace_updates: list[dict[str, Any]] | None = None
    updates_count: int | None = Field(default=None, ge=0)


class BulkUpsert(BaseModel):
    items: list[BulkUpsertItem] = Field(min_length=1)
    document_field: str = "text"
    id_field: str = "record_id"
    embedding_field: str = "embedding"
    id_prefix: str | None = None


class UpsertJobItem(BaseModel):
    key: str
    record: dict[str, Any]
    fingerprint: str | None = None
    chroma_id: str | None = None
    file_name: str | None = None
    audit_entries: list[dict[str, Any]] = Field(default_factory=list, max_length=5000)
    replace_updates: list[dict[str, Any]] | None = None
    updates_count: int | None = Field(default=None, ge=0)


class UpsertJobCreate(BaseModel):
    store_name: str = Field(min_length=1)
    label: str | None = None
    items: list[UpsertJobItem] = Field(min_length=1, max_length=50000)
    document_field: str = "text"
    embedding_field: str = "embedding"
    batch_size: int = Field(default=500, ge=1, le=1000)
    mirror_languages: bool = True
    include_updates: bool = False
    source_kind: Literal["browser_workspace", "database", "subset", "manual"] = "browser_workspace"
    source_label: str | None = Field(default=None, max_length=500)
    source_works: list[str] = Field(default_factory=list, max_length=10000)


class RecordStatusRequest(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=5000)


class SourceFingerprintProbe(BaseModel):
    id: str = Field(min_length=1, max_length=1024)
    fingerprint: str = Field(min_length=1, max_length=256)


class StoreDriftRequest(BaseModel):
    items: list[SourceFingerprintProbe] = Field(min_length=1, max_length=50000)


class SearchRequest(BaseModel):
    query: str = ""
    n_results: int = Field(default=10, ge=1, le=100)
    where: dict[str, Any] | None = None
    mode: Literal["similarity", "mmr", "filter", "keyword", "lexical", "hybrid"] = "similarity"
    fetch_k: int = Field(default=100, ge=1, le=1000)
    lambda_mult: float = Field(default=0.7, ge=0.0, le=1.0)


class OllamaTouchupOptions(BaseModel):
    @field_validator(
        "num_ctx", "num_predict", "temperature", "top_k", "top_p", "min_p",
        "repeat_penalty", "seed", "mirostat", "mirostat_eta", "mirostat_tau",
        mode="before",
    )
    @classmethod
    def _blank_optional_numbers(cls, value: Any) -> Any:
        # Saved provider profiles from older releases can contain empty strings.
        # Treat those as omitted optional values rather than rejecting the entire
        # Research request with a numeric-validation 422.
        return None if value == "" else value

    num_ctx: int | None = Field(default=None, ge=512, le=262144)
    num_predict: int | None = Field(default=None, ge=16, le=32768)
    temperature: float | None = Field(default=0.0, ge=0.0, le=2.0)
    top_k: int | None = Field(default=None, ge=0, le=1000)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    min_p: float | None = Field(default=None, ge=0.0, le=1.0)
    repeat_penalty: float | None = Field(default=None, ge=0.0, le=5.0)
    seed: int | None = None
    mirostat: int | None = Field(default=None, ge=0, le=2)
    mirostat_eta: float | None = Field(default=None, ge=0.0)
    mirostat_tau: float | None = Field(default=None, ge=0.0)
    stop: list[str] | None = None
    think: bool | Literal["low", "medium", "high"] | None = False
    keep_alive: str | None = None
    extra_options: dict[str, Any] = Field(default_factory=dict)


class LLMStatusRequest(BaseModel):
    provider: Literal["ollama", "openai"] = "ollama"
    base_url: str | None = None
    api_key: str | None = None


class LLMWarmupRequest(BaseModel):
    provider: Literal["ollama", "openai"] = "ollama"
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    num_ctx: int | None = Field(default=None, ge=256, le=1048576)


class TouchupRequest(BaseModel):
    record: dict[str, Any]
    fields: list[str] = Field(min_length=1)
    instructions: str | None = None
    model: str | None = None
    provider: Literal["ollama", "openai"] = "ollama"
    base_url: str | None = None
    api_key: str | None = None
    ollama: OllamaTouchupOptions | None = None


class TouchupResponse(BaseModel):
    changes: dict[str, Any]
    rationale: dict[str, str]
    warnings: list[str]
    model: str
    provider: str = "ollama"
    record_id: Any | None = None
    context_truncated: bool = False
    effective_options: dict[str, Any] = Field(default_factory=dict)


class LLMJobItem(BaseModel):
    key: str
    record: dict[str, Any]
    fingerprint: str | None = None


class LLMJobCreate(BaseModel):
    items: list[LLMJobItem] = Field(min_length=1, max_length=5000)
    fields: list[str] = Field(min_length=1)
    instructions: str | None = None
    model: str | None = None
    provider: Literal["ollama", "openai"] = "ollama"
    base_url: str | None = None
    api_key: str | None = None
    provider_profile_id: str | None = None
    max_concurrent_requests: int = Field(default=1, ge=1, le=64)
    ollama: OllamaTouchupOptions | None = None
    mode: Literal["review", "auto"] = "review"


class LLMResultResolutionItem(BaseModel):
    key: str
    fields: list[str] | None = None
    resolve_record: bool = False


class LLMResultResolutionRequest(BaseModel):
    action: Literal["accept", "reject"]
    items: list[LLMResultResolutionItem] = Field(default_factory=list)
    dismiss_job: bool = False


class LLMJobRejectRequest(BaseModel):
    dismiss: bool = True

class RAGEvidenceSelection(BaseModel):
    """A user-selected evidence item supplied to a RAG run.

    DB-backed selections should provide ``collection`` + ``chroma_id`` so the
    server can rehydrate the authoritative full record without exposing it to a
    researcher browser. Admin-only local workspace selections may provide a
    record directly.
    """
    collection: str | None = None
    chroma_id: str | None = None
    record: dict[str, Any] | None = None


class RAGRunRequest(BaseModel):
    prompt: str = Field(min_length=1)
    instructions: str | None = None
    # Empty is valid only for selected-evidence-only runs. The pipeline enforces
    # a collection when vector retrieval is enabled.
    source_collection: str = ""
    locales: list[LanguageCode] = Field(default_factory=_default_locales)
    search_types: list[SearchType] = Field(default_factory=_default_search_types)
    k: int = Field(default=64, ge=1, le=500)
    fetch_k: int = Field(default=500, ge=1, le=5000)
    lambda_mult: float = Field(default=0.7, ge=0.0, le=1.0)
    rrf_k: int = Field(default=60, ge=1, le=10000)
    rerank_top_n: int = Field(default=24, ge=1, le=500)
    reranker: Literal["cross_encoder", "lexical", "none"] = "cross_encoder"
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    query_decomposition: bool = True
    query_decomposition_num_predict: int = Field(default=768, ge=64, le=8192)
    response_language: Literal["auto", "en", "fr"] = "auto"
    evidence_record_char_limit: int = Field(default=12000, ge=500, le=100000)
    evidence_total_char_limit: int = Field(default=120000, ge=5000, le=1000000)
    provider: Literal["ollama", "openai"] = "ollama"
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    provider_profile_id: str | None = None
    max_concurrent_requests: int = Field(default=32, ge=1, le=64)
    generation: OllamaTouchupOptions | None = None
    ollama_concurrency_limit: int | None = Field(default=None, ge=1, le=32)
    bind_citations: bool = True
    include_works_cited: bool = True
    selected_evidence: list[RAGEvidenceSelection] = Field(default_factory=list, max_length=500)
    skip_retrieval: bool = False
    auto_grade: bool = False
    # Auto-grading can use an independent provider/model from answer generation.
    # These execution fields are resolved server-side from the selected profile.
    auto_grade_provider: Literal["ollama", "openai"] | None = None
    auto_grade_model: str | None = None
    auto_grade_base_url: str | None = None
    auto_grade_api_key: str | None = None
    auto_grade_provider_profile_id: str | None = None
    auto_grade_generation: OllamaTouchupOptions | None = None


class PdfLlmRequest(BaseModel):
    mode: Literal["clean_text", "draft_record", "link_record"]
    raw_text: str = ""
    pdf_file: str | None = None
    pdf_title: str | None = None
    pdf_author: str | None = None
    pdf_page: int | None = Field(default=None, ge=1)
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    provider: Literal["ollama", "openai"] = "ollama"
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    generation: OllamaTouchupOptions | None = None



class PdfPageLabelsPatch(BaseModel):
    labels: dict[int, str | None] = Field(default_factory=dict)


class PdfSourceUrlImport(BaseModel):
    url: str = Field(min_length=8, max_length=2000)
    source_illegibility: float = Field(default=0, ge=0, le=100)


class GutenbergImport(BaseModel):
    etext_id: int = Field(ge=1)
    source_illegibility: float = Field(default=0, ge=0, le=100)


class PdfDocumentLayoutPatch(BaseModel):
    page_layout: Literal["single", "two_up"] = "single"
    reading_order: Literal["left_to_right", "right_to_left"] = "left_to_right"
    main_text_pdf_start: int | None = Field(default=None, ge=1)
    main_text_printed_start: int | None = Field(default=None, ge=1)
    main_text_slot: Literal["left", "right"] | None = None
    bibliography_pdf_start: int | None = Field(default=None, ge=1)
    thread_mode: Literal["continuous", "odd_even", "even_odd", "left_right", "right_left"] = "continuous"
    thread_a_language: str | None = None
    thread_b_language: str | None = None


class PdfCorpusProviderConfig(BaseModel):
    provider: Literal["ollama", "openai"] = "ollama"
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    generation: OllamaTouchupOptions | None = None




class PdfCorpusStageLimits(BaseModel):
    """Per-build structured-output budgets for corpus construction stages.

    These limits deliberately sit beside, rather than inside, the reusable
    provider profile. A corpus build can need larger/smaller output envelopes
    than ordinary metadata review without mutating the saved profile.
    """
    manifest_num_predict: int = Field(default=1800, ge=256, le=8192)
    segmentation_num_predict: int = Field(default=1200, ge=256, le=8192)
    reconciliation_num_predict: int = Field(default=1000, ge=256, le=8192)
    discourse_num_predict: int = Field(default=1600, ge=256, le=8192)
    quotation_num_predict: int = Field(default=1500, ge=256, le=8192)
    indexing_num_predict: int = Field(default=1200, ge=256, le=8192)
    segmentation_window_tokens: int = Field(default=5000, ge=1024, le=24000)



class PdfCorpusStageTimeouts(BaseModel):
    """Per-build wall-clock/read deadlines for corpus LLM stages, in seconds."""
    manifest: int = Field(default=300, ge=30, le=1800)
    segmentation: int = Field(default=300, ge=30, le=1800)
    reconciliation: int = Field(default=240, ge=30, le=1800)
    discourse: int = Field(default=240, ge=30, le=1800)
    quotation: int = Field(default=240, ge=30, le=1800)
    indexing: int = Field(default=180, ge=30, le=1800)


class PdfCorpusRecordSizing(BaseModel):
    """Soft record-length policy for retrieval-oriented corpus topology.

    Length is never semantic evidence. These values guide deterministic
    post-segmentation normalization toward readable/retrievable records while
    protected attribution and discourse structure remain higher priority.
    """
    preferred_record_chars: int = Field(default=1750, ge=600, le=12000)
    record_length_tolerance: int = Field(default=200, ge=50, le=2000)
    long_record_chars: int = Field(default=3500, ge=1200, le=24000)
    absolute_record_chars: int = Field(default=6000, ge=1800, le=48000)

    def model_post_init(self, __context: Any) -> None:
        preferred = self.preferred_record_chars
        tolerance = self.record_length_tolerance
        if self.long_record_chars < preferred + tolerance:
            raise ValueError("long_record_chars must be at least preferred_record_chars + record_length_tolerance")
        if self.absolute_record_chars < self.long_record_chars:
            raise ValueError("absolute_record_chars must be at least long_record_chars")


class PdfCorpusExperimentArm(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    ablations: list[Literal["autofill", "blended_confidence", "rejection_memory", "reviewer_conventions", "cross_build_learning"]] = Field(default_factory=list)


class PdfCorpusExperiment(BaseModel):
    """Optional experiment conditions. Absent, a run behaves normally and records the default arm."""

    ablations: list[Literal["autofill", "blended_confidence", "rejection_memory", "reviewer_conventions", "cross_build_learning"]] = Field(default_factory=list)
    arms: list[PdfCorpusExperimentArm] = Field(default_factory=list, max_length=8)
    arm_salt: str = Field(default="", max_length=60)
    blind_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    recheck_rate: float = Field(default=0.0, ge=0.0, le=0.5)
    iaa_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    model_version: str | None = Field(default=None, max_length=120)



class PdfCorpusAutonomy(BaseModel):
    """Hands-free mode: nobody reviews the records, so a stated policy makes the decisions. Off unless enabled."""

    enabled: bool = False
    passes: int = Field(default=1, ge=0, le=3)
    min_confidence: float = Field(default=0.8, ge=0.5, le=0.99)
    unresolved: Literal["best_guess", "leave"] = "best_guess"
    accept_records: bool = True
    publish: bool = False


class PdfCorpusFieldRunGuidance(BaseModel):
    """A temporary, build-specific instruction for one metadata field."""

    model_config = ConfigDict(extra="forbid")
    instructions: str = Field(default="", max_length=1200)
    look_for: list[str] = Field(default_factory=list, max_length=40)
    required: bool = False
    default_placeholder: str = Field(default="[not established in source]", max_length=200)

    @field_validator("instructions", mode="before")
    @classmethod
    def trim_instructions(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("look_for", mode="before")
    @classmethod
    def clean_terms(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("look_for must be a list of phrases")
        if len(value) > 40:
            raise ValueError("A field can have at most 40 look-for phrases")
        terms: list[str] = []
        seen: set[str] = set()
        for item in value:
            term = str(item or "").strip()
            if not term:
                continue
            if len(term) > 160:
                raise ValueError("Each look-for phrase must be 160 characters or fewer")
            if term.casefold() not in seen:
                terms.append(term)
                seen.add(term.casefold())
        return terms

    @field_validator("default_placeholder", mode="before")
    @classmethod
    def trim_placeholder(cls, value: Any) -> str:
        return str(value or "").strip()


class PdfCorpusBuildCreate(BaseModel):
    asset_id: str = Field(min_length=1, max_length=200)
    profile_id: str = Field(default="derrida-scholarly-v12", min_length=1, max_length=200)
    provider: Literal["ollama", "openai"] = "ollama"
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    provider_profile_id: str | None = None
    review_provider_profile_id: str | None = None
    review_provider: PdfCorpusProviderConfig | None = None
    generation: OllamaTouchupOptions | None = None
    use_profile_defaults: bool = True
    max_concurrent_requests: ClampedConcurrency = Field(default=1)
    stage_limits: PdfCorpusStageLimits = Field(default_factory=PdfCorpusStageLimits)
    stage_timeouts: PdfCorpusStageTimeouts = Field(default_factory=PdfCorpusStageTimeouts)
    record_sizing: PdfCorpusRecordSizing = Field(default_factory=PdfCorpusRecordSizing)
    auto_enrich_work_metadata: bool = True
    experiment: PdfCorpusExperiment | None = None
    schema_id: str = Field(default="default", min_length=1, max_length=64)
    run_guidance: dict[str, PdfCorpusFieldRunGuidance] = Field(default_factory=dict, max_length=60)
    autonomous: PdfCorpusAutonomy | None = None
    auto_clean_text: bool = True
    llm_touchup_during_enrichment: bool = False
    noise_unusable_threshold: float = Field(default=45, ge=0, le=100)
    llm_assess_text_noise: bool = False
    text_cleanup_rules: list[TextCleanupRule] = Field(default_factory=_default_text_cleanup_rules)
    enrichment_mode: Literal["fast", "deep"] = "fast"
    semantic_indexing: bool = False

    @field_validator("run_guidance")
    @classmethod
    def bound_run_guidance(cls, value: dict[str, PdfCorpusFieldRunGuidance]) -> dict[str, PdfCorpusFieldRunGuidance]:
        total = sum(len(item.instructions) + sum(map(len, item.look_for)) for item in value.values())
        if total > 24000:
            raise ValueError("Run guidance must contain 24,000 characters or fewer in total")
        return value


class PdfCorpusManifestPatch(BaseModel):
    changes: dict[str, Any] = Field(default_factory=dict)
    expected_revision: int | None = Field(default=None, ge=1)


class PdfCorpusRecordPatch(BaseModel):
    changes: dict[str, Any] = Field(default_factory=dict)
    expected_revision: int | None = Field(default=None, ge=1)


class PdfCorpusRecordTextPatch(BaseModel):
    text: str = Field(min_length=1, max_length=500000)
    expected_revision: int | None = Field(default=None, ge=1)
    resolve_source_issues: bool = False


class PdfCorpusMetadataDecision(BaseModel):
    field: str = Field(min_length=1, max_length=120)
    value: Any = None
    confirm_no_supported_value: bool = False
    expected_revision: int | None = Field(default=None, ge=1)


class PdfCorpusMetadataCacheClear(BaseModel):
    field: str | None = Field(default=None, min_length=1, max_length=120)


class PdfCorpusMetadataDecisionBatch(BaseModel):
    changes: dict[str, Any] = Field(min_length=1, max_length=60)
    expected_revision: int | None = Field(default=None, ge=1)


class PdfCorpusEvidencePatch(BaseModel):
    field: str = Field(min_length=1, max_length=120)
    block_ids: list[str] = Field(default_factory=list, max_length=500)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reason: str = Field(default="", max_length=2000)
    expected_revision: int | None = Field(default=None, ge=1)


class PdfCorpusRecordAccept(BaseModel):
    accepted: bool = True
    expected_revision: int | None = Field(default=None, ge=1)


class PdfCorpusRecordDisposition(BaseModel):
    disposition: Literal["pending", "accepted", "rejected"]
    reason: str = Field(default="", max_length=2000)
    expected_revision: int | None = Field(default=None, ge=1)


class PdfCorpusBulkDisposition(BaseModel):
    disposition: Literal["pending", "accepted", "rejected"]
    reason: str = Field(default="", max_length=2000)
    needs_review: bool | None = None
    filter_disposition: Literal["pending", "accepted", "rejected"] | None = None
    review_queue: Literal["ready", "issues", "metadata", "source", "topology"] | None = None
    query: str = Field(default="", max_length=500)
    record_ids: list[str] = Field(default_factory=list, max_length=500)


class PdfCorpusBulkMetadataPatch(BaseModel):
    changes: dict[str, Any] = Field(default_factory=dict)
    record_ids: list[str] = Field(default_factory=list, max_length=5000)
    apply_to_all: bool = False
    review_queue: Literal["ready", "issues", "metadata", "source", "topology", "accepted", "rejected"] | None = None
    query: str = Field(default="", max_length=500)


class PdfCorpusReviewDecision(BaseModel):
    disposition: Literal["accepted", "rejected"]
    reason: str = Field(default="", max_length=2000)
    expected_revision: int | None = Field(default=None, ge=1)
    review_queue: Literal["all", "ready", "issues", "metadata", "topology", "source", "accepted", "rejected"] | None = None


class PdfCorpusRecordMerge(BaseModel):
    direction: Literal["previous", "next"]
    expected_revision: int | None = Field(default=None, ge=1)


class PdfCorpusRecordSplit(BaseModel):
    after_block_id: str = Field(min_length=1, max_length=200)
    expected_revision: int | None = Field(default=None, ge=1)

class PdfCorpusRecordSlice(BaseModel):
    direction: Literal["previous", "next", "keep", "new"]
    offset: int = Field(ge=1, le=500000)
    keep_end: int | None = Field(default=None, ge=2, le=500000)
    expected_revision: int | None = Field(default=None, ge=1)


class PdfCorpusBoundaryAdjudication(BaseModel):
    direction: Literal["previous", "next"]
    provider: Literal["ollama", "openai"] = "ollama"
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    provider_profile_id: str | None = None
    generation: OllamaTouchupOptions | None = None
    use_profile_defaults: bool = True


class PdfCorpusProviderSwitch(BaseModel):
    provider_profile_id: str = Field(min_length=1, max_length=200)
    provider: Literal["ollama", "openai"] | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    generation: OllamaTouchupOptions | None = None
    review_provider_profile_id: str | None = None
    review_provider: PdfCorpusProviderConfig | None = None


class PdfCorpusRecordRerun(BaseModel):
    provider: Literal["ollama", "openai"] = "ollama"
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    provider_profile_id: str | None = None
    review_provider_profile_id: str | None = None
    review_provider: PdfCorpusProviderConfig | None = None
    generation: OllamaTouchupOptions | None = None
    use_profile_defaults: bool = True
    max_concurrent_requests: ClampedConcurrency = Field(default=1)
    stage_limits: PdfCorpusStageLimits = Field(default_factory=PdfCorpusStageLimits)
    stage_timeouts: PdfCorpusStageTimeouts = Field(default_factory=PdfCorpusStageTimeouts)
    record_sizing: PdfCorpusRecordSizing = Field(default_factory=PdfCorpusRecordSizing)
    enrichment_mode: Literal["fast", "deep"] = "fast"
    experiment: PdfCorpusExperiment | None = None
    autonomous: PdfCorpusAutonomy | None = None
    semantic_indexing: bool = False
    families: list[Literal["discourse", "quotation", "indexing"]] | None = None
    scope: Literal["all", "accepted", "pending", "selected"] = "all"
    record_ids: list[str] = Field(default_factory=list, max_length=5000)
    # 1 runs a single pass; more chains passes, each learning from the last.
    passes: int = Field(default=1, ge=1, le=MAX_PASSES)


class PdfCorpusTextTouchupRequest(BaseModel):
    provider: Literal["ollama", "openai"] = "ollama"
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    provider_profile_id: str | None = None
    review_provider_profile_id: str | None = None
    review_provider: PdfCorpusProviderConfig | None = None
    generation: OllamaTouchupOptions | None = None
    use_profile_defaults: bool = True
    max_concurrent_requests: ClampedConcurrency = Field(default=1)
    stage_limits: PdfCorpusStageLimits = Field(default_factory=PdfCorpusStageLimits)
    stage_timeouts: PdfCorpusStageTimeouts = Field(default_factory=PdfCorpusStageTimeouts)
    instructions: str = Field(default="", max_length=2000)
    text: str | None = Field(default=None, min_length=1, max_length=500000)


class PdfCorpusTextTouchupProposalStatus(BaseModel):
    status: Literal["pending_review", "dismissed"]


class PdfCorpusPublishRequest(BaseModel):
    require_acceptance: bool = True

class RAGGradeRequest(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    provider: Literal["ollama", "openai"] = "ollama"
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    generation: OllamaTouchupOptions | None = None
    response_record_id: str | None = None
    generation_provider: str | None = None
    generation_model: str | None = None


class RAGGradeBatchRequest(BaseModel):
    """Grade or re-grade every cached RAG response in one background job."""
    provider: Literal["ollama", "openai"] = "ollama"
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    generation: OllamaTouchupOptions | None = None
    provider_profile_id: str | None = None
    max_concurrent_requests: int = Field(default=1, ge=1, le=64)


class WorkMetadataSeed(BaseModel):
    work: str = Field(min_length=1, max_length=500)
    current_metadata: dict[str, Any] = Field(default_factory=dict)


class WorkMetadataRequest(BaseModel):
    """Fetch and propose bibliographic metadata for one or more works.

    The browser applies accepted proposals to its local corpus records; the
    background task only resolves catalogue metadata and returns proposals.
    """
    works: list[WorkMetadataSeed] = Field(min_length=1, max_length=500)
    provider: Literal["ollama", "openai"] = "ollama"
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    generation: OllamaTouchupOptions | None = None
    provider_profile_id: str | None = None


class LLMToolJobCreate(BaseModel):
    task: Literal[
        "pdf_clean_text",
        "pdf_draft_record",
        "pdf_link_record",
        "rag_grade",
        "rag_grade_batch",
        "work_metadata",
        "language_dictionary",
        "language_content_policy",
    ]
    pdf: PdfLlmRequest | None = None
    grade: RAGGradeRequest | None = None
    grade_batch: RAGGradeBatchRequest | None = None
    work_metadata: WorkMetadataRequest | None = None
    language: LanguageInstallRequest | None = None
    label: str | None = None
    provider_profile_id: str | None = None
    max_concurrent_requests: int = Field(default=1, ge=1, le=64)


class RAGConcurrencyUpdate(BaseModel):
    ollama_max_concurrent: int = Field(ge=1, le=32)

class ResearcherProviderProfilesUpdate(BaseModel):
    profiles: list[dict[str, Any]] = Field(default_factory=list, max_length=200)


class ResearcherProviderStatusRequest(BaseModel):
    id: str | None = Field(default=None, max_length=200)
    type: Literal["ollama", "openai"] = "ollama"
    base_url: str | None = None
    api_key: str | None = None


class AnnotationCreateRequest(BaseModel):
    store: str | None = Field(default=None, max_length=300)
    record_id: str = Field(min_length=1, max_length=500)
    work: str | None = Field(default=None, max_length=500)
    page_start: int | str | None = None
    page_end: int | str | None = None
    field: str = Field(default="text", max_length=200)
    quote: str = Field(default="", max_length=10000)
    note: str = Field(default="", max_length=20000)
    tags: list[str] = Field(default_factory=list, max_length=100)


class LanguageDictionaryUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    flag: str = Field(default="🌐", max_length=32)
    dictionary: dict[str, str] = Field(default_factory=dict)


class LanguageContentPolicyUpdate(BaseModel):
    blocked_terms: list[str] = Field(default_factory=list, max_length=150)
    contextual_terms: list[dict[str, Any]] = Field(default_factory=list, max_length=24)


class LanguageInstallRequest(BaseModel):
    code: str = Field(min_length=2, max_length=35)
    name: str | None = Field(default=None, max_length=160)
    flag: str | None = Field(default=None, max_length=32)
    resume_job_id: str | None = Field(default=None, max_length=100)
    provider: Literal["ollama", "openai"] = "ollama"
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    generation: OllamaTouchupOptions | None = None


class AuthBootstrapRequest(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=6, max_length=512)


class AuthLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=512)


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=6, max_length=512)
    role: str = Field(min_length=1, max_length=64)


class UserUpdateRequest(BaseModel):
    role: str | None = Field(default=None, min_length=1, max_length=64)
    active: bool | None = None
    password: str | None = Field(default=None, min_length=6, max_length=512)


class RoleCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=500)
    clone_from: str = Field(default="researcher", min_length=1, max_length=64)


class RolePermissionsUpdate(BaseModel):
    permissions: list[str] = Field(default_factory=list, max_length=200)


class PdfCorpusSecondOpinion(BaseModel):
    field: str = Field(min_length=1, max_length=80)
    value: Any = None


class MetadataSchemaPreview(PdfCorpusRecordRerun):
    """Try one group of a schema on a passage of text, without a build."""

    schema_: MetadataSchema = Field(alias="schema")
    group: str = Field(min_length=1, max_length=24)
    text: str = Field(min_length=1, max_length=20000)
    run: bool = False  # false: show the prompt only, without calling a model
