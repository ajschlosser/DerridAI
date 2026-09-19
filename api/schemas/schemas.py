from __future__ import annotations

from enum import StrEnum
from typing import Any, NotRequired, Optional, TypedDict

from pydantic import BaseModel, Field, field_validator


class Languages(StrEnum):
    ENGLISH = "en"
    FRENCH = "fr"


class RAGSearchTypes(StrEnum):
    MMR = "mmr"
    SIMILARITY = "similarity"


class RetrievalMode(StrEnum):
    AUTO = "auto"
    SELECTED = "selected"


class QueryOptions(BaseModel):
    retrieval_mode: RetrievalMode = RetrievalMode.AUTO
    response_language: str = Field("en", min_length=2, max_length=16)
    document_languages: list[str] = Field(default_factory=lambda: ["en", "fr"])
    canonical_work_ids: list[str] = Field(default_factory=list)
    limit: int = Field(12, ge=1, le=48)
    include_diagnostics: bool = True

    @field_validator("document_languages")
    @classmethod
    def normalize_languages(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in value:
            lang = str(item).strip().lower()
            if lang and lang not in normalized:
                normalized.append(lang)
        if not normalized:
            raise ValueError("At least one document language is required")
        return normalized


class EvidenceInput(BaseModel):
    record_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    work: str = ""
    canonical_work_id: str = ""
    document_author: str = ""
    speaker: str | list[str] | None = None
    quoted_speaker: str | list[str] | None = None
    position_holder: str | list[str] | None = None
    stance: str | None = None
    proposition_status: str | None = None
    target: str | list[str] | None = None
    discourse_role: str | None = None
    language: str | None = None
    page_start: int | str | None = None
    page_end: int | str | None = None
    year: int | str | None = None
    edition: str | None = None
    translator: str | list[str] | None = None
    publisher: str | None = None


class QueryRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=20000)
    locale: str = Field("en", min_length=2, max_length=16)
    options: QueryOptions = Field(default_factory=QueryOptions)
    selected_evidence: list[EvidenceInput] = Field(default_factory=list, max_length=48)


class CitationInfo(BaseModel):
    record_id: str
    inline: str
    full: str
    work: str = ""
    page_start: int | str | None = None
    page_end: int | str | None = None


class EvidenceRecord(EvidenceInput):
    evidence_tag: str
    inline_citation: str = ""
    full_citation: str = ""
    retrieval_score: float | None = None
    rerank_score: float | None = None
    retrieval_method: str | list[str] | None = None
    provenance_warnings: list[str] = Field(default_factory=list)


class ValidationIssue(BaseModel):
    severity: str = Field(..., pattern="^(info|warning|error)$")
    code: str
    record_id: str | None = None
    message: str


class RetrievalDiagnostics(BaseModel):
    mode: RetrievalMode
    candidate_count: int = 0
    deduplicated_count: int = 0
    returned_count: int = 0
    languages: list[str] = Field(default_factory=list)
    canonical_work_ids: list[str] = Field(default_factory=list)


class ResearchResponseContent(BaseModel):
    response: str
    request_id: str
    locale: str
    response_language: str
    evidence: list[EvidenceRecord] = Field(default_factory=list)
    citations: list[CitationInfo] = Field(default_factory=list)
    validation_issues: list[ValidationIssue] = Field(default_factory=list)
    retrieval: RetrievalDiagnostics
    query_metadata: dict[str, Any] = Field(default_factory=dict)


class GenericResponse(BaseModel):
    content: ResearchResponseContent
    results: list[Any] = Field(default_factory=list)


class JobStartResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    phase: str | None = None
    result: Optional[GenericResponse] = None
    error: str | None = None


class AppCapabilities(BaseModel):
    api_version: str
    product_name: str = "DerridAI"
    release_name: str = "Risky Rabbit"
    supported_locales: list[str] = Field(default_factory=lambda: ["en", "fr"])
    supported_document_languages: list[str] = Field(default_factory=lambda: ["en", "fr"])
    retrieval_modes: list[str] = Field(default_factory=lambda: [mode.value for mode in RetrievalMode])
    accessibility_target: str = "WCAG 2.0 AA"


class DerridAIQueryMetadata(TypedDict):
    canonical_work_ids: list[str]
    works_referenced: list[str]
    canonical_work_ids_works_referenced: list[str]
    materials_languages: list[str]
    institutions_referenced: list[str]
    locations_referenced: list[str]
    persons_referenced: list[str]
    events_referenced: list[str]
    groups_referenced: list[str]
    languages_referenced: list[str]
    limit: int
    response_language: str
    prompt_languages: list[str]
    document_languages: list[str]
    prompt: NotRequired[str | None]
    prompt_fr: NotRequired[str | None]
    keywords: NotRequired[list[str] | None]
    keywords_fr: NotRequired[list[str] | None]
    prompt_query: NotRequired[str | None]
    prompt_query_fr: NotRequired[str | None]
    prompt_instructions: NotRequired[str | None]


class LLMModels(StrEnum):
    DEEPSEEK_14B = "deepseek-r1:14b"
    DEEPSEEK_DISTILL_QWEN_14B = "hf.co/unsloth/DeepSeek-R1-Distill-Qwen-14B-GGUF:Q4_K_M"
    GEMMA4_E2B = "gemma4:e2b"
    GEMMA4_E4B = "gemma4:e4b"
    GEMMA4_E4B_MTB = "hf.co/unsloth/gemma-4-E4B-it-GGUF:Q8_0"
    GEMMA4_12B = "gemma4:12b"
    GEMMA4_12B_MTB = "4skl/gemma4-12b-mtp:latest"
    GEMMA4_26B = "hf.co/unsloth/gemma-4-26B-A4B-it-GGUF:UD-IQ4_XS"
    GPT_OSS_20B = "gpt-oss:20b"
    GPT_OSS_20B_GGUF = "hf.co/unsloth/gpt-oss-20b-GGUF:Q4_0"
    GRANITE_3B = "granite4.2:3b"
    GRANITE_8B = "granite4.2:8b"
    LLAMA_3B = "llama3.2:3b"
    MISTRAL_24B = "hf.co/unsloth/Mistral-Small-3.1-24B-Instruct-2503-GGUF:Q4_0"
    NEMOTRON_30B = "hf.co/tngtech/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4-GGUF:NVFP4"
    ORNITH_9B = "ornith-1.5:9b"
    ORNITH_35B = "hf.co/AtomicChat/Ornith-1.5-35B-A3B-GGUF:IQ3_XXS"
    PHI4_14B = "phi4:14b"
    PHI4_MINI_4B = "phi4-mini:3.8b"
    PHI4_MINI_REASONING_4B = "phi4-mini-reasoning:3.8b"
    QWEN_0B = "qwen3.5:0.8b"
    QWEN_2B = "qwen3.5:2b"
    QWEN_4B = "qwen3.5:4b"
    QWEN_9B = "qwen3.5:9b"
    QWEN_14B = "qwen3:14b"
    QWEN_3_5_27B = "hf.co/unsloth/Qwen3.5-27B-GGUF:IQ4_XS"
    QWEN_3_6_14B = "hf.co/tvall43/Qwen3.6-14B-A3B-FableVibes-GGUF:Q6_K"
    QWEN_3_8_27B = "hf.co/unsloth/Qwen3.8-27B-GGUF:UD-IQ4_XS"
    QWEN_3_8_27B_3BIT = "hf.co/unsloth/Qwen3.8-27B-GGUF:UD-IQ3_XXS"
    TIEL_CODER_35B_3BIT = "hf.co/peculiar-ragdoll/Tiel-Coder-35B-A3B-GGUF:UD-IQ3_XXS"
