# Copyright 2026 Aaron John Schlosser, PhD.
"""Typed dictionaries for scholarly records and RAG payloads.

These contracts name the provenance chain without flattening speaker,
quoted_speaker, and position_holder. Runtime records still carry extra keys;
total=False matches incomplete records still under review.
"""
from __future__ import annotations

from typing import Any, TypedDict


class ProvenanceRecord(TypedDict, total=False):
    record_id: str
    text: str
    work: str
    document_author: str
    document_language: str
    document_languages: Any
    speaker: str
    quoted_speaker: Any
    quoted_author: Any
    quoted_work: Any
    quoted_position_holder: Any
    quoted_addressee: Any
    quoted_referent: Any
    quotation_chain: Any
    position_holder: str
    target: str
    stance: str
    discourse_role: str
    proposition_status: str
    region_type: str
    primary_text: bool
    inline_citation: str
    full_citation: str
    page_start: Any
    page_end: Any


class QueryDecomposition(TypedDict):
    prompt_query: str
    prompt_query_fr: str
    prompt_instructions: str
    limit_retrieval: int
    limit_reranking: int
    response_language: str
    document_languages: list[str]


class RetrievalHit(TypedDict, total=False):
    collection: str
    search_type: str
    rank: int


class RetrievalCandidate(TypedDict, total=False):
    id: str
    collection: str
    record: dict[str, Any]
    distance: float | None
    rrf_score: float
    rerank_score: float
    retrieval_hits: list[RetrievalHit]
    selected_evidence: bool
    embedding: list[float] | None
    mmr_score: float


class EvidenceItem(TypedDict, total=False):
    evidence_id: str
    collection: str
    distance: float | None
    rerank_score: float
    rrf_score: float
    retrieval_hits: list[Any]
    record: dict[str, Any]
    inline_citation: str
    full_citation: str
    text_truncated: bool
