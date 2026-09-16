# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


LanguageCode = Literal["en", "fr"]
CollectionRole = Literal["primary", "language", "general"]


class ChromaPathUpdate(BaseModel):
    path: str = Field(min_length=1, max_length=4096)


class StoreCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    metadata: dict[str, Any] | None = None
    embedding_provider: Literal["chroma", "ollama", "precomputed"] | None = None
    embedding_model: str | None = None
    language_codes: list[LanguageCode] | None = None
    collection_role: CollectionRole | None = None


class StoreEmbeddingUpdate(BaseModel):
    embedding_provider: Literal["chroma", "ollama", "precomputed"]
    embedding_model: str | None = None


class StoreLanguageUpdate(BaseModel):
    language_codes: list[LanguageCode] = Field(default_factory=list)
    collection_role: CollectionRole | None = None


class DeriveLanguageStoresRequest(BaseModel):
    en_name: str | None = None
    fr_name: str | None = None
    # Backward-compatible aliases accepted from 0.7.x clients.
    english_name: str | None = None
    french_name: str | None = None
    en_us_name: str | None = None
    en_gb_name: str | None = None
    fr_fr_name: str | None = None
    overwrite: bool = True


class RecordUpsert(BaseModel):
    record: dict[str, Any]
    document_field: str = "text"
    id_field: str = "record_id"
    embedding_field: str = "embedding"
    id_prefix: str | None = None
    include_updates: bool = False


class StoredRecordUpdate(BaseModel):
    # Backward-compatible full-record update. New 0.30.11 clients should use
    # StoredRecordPatch so unchanged fields (especially ``updates``) never
    # cross the API boundary.
    record: dict[str, Any]
    document_field: str = "text"
    embedding_field: str = "embedding"
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
    # ``records`` is retained for older clients. 0.30.11 uses ``items`` so
    # audit-history deltas travel separately from the record itself.
    records: list[dict[str, Any]] = Field(default_factory=list)
    items: list[BulkUpsertItem] = Field(default_factory=list)
    document_field: str = "text"
    id_field: str = "record_id"
    embedding_field: str = "embedding"
    id_prefix: str | None = None
    include_updates: bool = False


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


class RecordStatusRequest(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=5000)


class SearchRequest(BaseModel):
    query: str = ""
    n_results: int = Field(default=10, ge=1, le=100)
    where: dict[str, Any] | None = None
    mode: Literal["similarity", "mmr", "filter", "keyword"] = "similarity"
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
    @model_validator(mode="before")
    @classmethod
    def _blank_numeric_fields_use_defaults(cls, value: Any) -> Any:
        # A stale browser draft/profile can carry blank or null numeric controls.
        # These values mean “use the request default”; removing them before field
        # validation keeps old clients compatible and avoids opaque 422 errors.
        if not isinstance(value, dict):
            return value
        cleaned = dict(value)
        for key in (
            "k", "fetch_k", "lambda_mult", "rrf_k", "rerank_top_n",
            "query_decomposition_num_predict", "evidence_record_char_limit",
            "evidence_total_char_limit", "max_concurrent_requests",
            "ollama_concurrency_limit",
        ):
            if cleaned.get(key) in (None, ""):
                cleaned.pop(key, None)
        return cleaned

    prompt: str = Field(min_length=1)
    instructions: str | None = None
    # Empty is valid only for selected-evidence-only runs. The pipeline enforces
    # a collection when vector retrieval is enabled.
    source_collection: str = ""
    locales: list[LanguageCode] = Field(default_factory=lambda: ["en", "fr"])
    search_types: list[Literal["mmr", "similarity"]] = Field(default_factory=lambda: ["mmr", "similarity"])
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
    # Keeping these fields flat preserves backward compatibility with older saved
    # RAG requests while making the final pipeline step fully configurable.
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


class LanguageInstallRequest(BaseModel):
    code: str = Field(min_length=4, max_length=16)
    name: str | None = Field(default=None, max_length=160)
    flag: str | None = Field(default=None, max_length=32)
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
