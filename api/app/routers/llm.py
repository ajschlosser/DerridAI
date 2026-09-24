# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ..llm import TouchupFailure, llm_status, warmup_model
from ..llm_tools import run_pdf_llm, run_rag_grade
from ..models import LLMStatusRequest, LLMWarmupRequest, PdfLlmRequest, RAGGradeRequest
from ..services import store

router = APIRouter(tags=["llm"])


@router.get("/api/llm/status")
def llm_status_endpoint(
    provider: str = Query(default="ollama"),
    base_url: str | None = Query(default=None),
    api_key: str | None = Query(default=None),
) -> dict[str, Any]:
    provider = provider.strip().lower()
    if provider not in {"ollama", "openai"}:
        raise HTTPException(status_code=400, detail="provider must be ollama or openai")
    return llm_status(
        provider,
        base_url=base_url,
        api_key=api_key,
    )


@router.post("/api/llm/status")
def llm_status_post(body: LLMStatusRequest) -> dict[str, Any]:
    return llm_status(
        body.provider,
        base_url=body.base_url,
        api_key=body.api_key,
    )


@router.post("/api/llm/warmup")
def llm_warmup(body: LLMWarmupRequest) -> dict[str, Any]:
    try:
        return warmup_model(
            provider=body.provider,
            model=body.model,
            base_url=body.base_url,
            api_key=body.api_key,
            num_ctx=body.num_ctx,
        )
    except TouchupFailure as exc:
        detail = {"message": exc.message}
        if exc.diagnostic:
            detail["diagnostic"] = exc.diagnostic
        raise HTTPException(status_code=exc.status_code, detail=detail) from exc


@router.post("/api/rag/grade")
def grade_rag_response(body: RAGGradeRequest) -> dict[str, Any]:
    try:
        for evidence in body.evidence:
            record = evidence.get("record") if isinstance(evidence, dict) else None
            if isinstance(record, dict):
                record.pop("updates", None)
        return run_rag_grade(body, store)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"RAG grading failed: {exc}") from exc


@router.post("/api/pdf/llm")
def pdf_llm(body: PdfLlmRequest) -> dict[str, Any]:
    try:
        return run_pdf_llm(body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

