from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import TYPE_CHECKING

from clients.llm import LLMClient
from clients.rag import RAGClient
from schemas.schemas import (
    CitationInfo,
    GenericResponse,
    QueryRequest,
    ResearchResponseContent,
    RetrievalDiagnostics,
    RetrievalMode,
    ValidationIssue,
)
from services.nlp import NLPService
from templates.research_prompt import RESEARCH_PROMPT
from utils.generate_context_string import generate_context_string
from utils.provenance import (
    document_to_evidence_record,
    input_to_evidence_record,
    validation_issues,
)
from utils.request_id import request_id

if TYPE_CHECKING:
    from services.jobs import JobService

LOG = logging.getLogger(__name__)
EVIDENCE_TAG_RE = re.compile(r"\[E(?P<index>\d+)\]")


def _detected_languages(nlp_service: NLPService, text: str, fallback: str) -> list[str]:
    try:
        values = list(nlp_service.detect_languages(text))
        normalized: list[str] = []
        for value in values:
            code = str(value).strip().lower()
            if code and code not in normalized:
                normalized.append(code)
        return normalized or [fallback]
    except Exception:
        LOG.exception("Language detection failed; using request locale")
        return [fallback]


def _queries_by_language(
    nlp_service: NLPService,
    prompt: str,
    prompt_languages: list[str],
    document_languages: list[str],
) -> dict[str, str]:
    primary = prompt_languages[0] if prompt_languages else "en"
    result = {language: prompt for language in document_languages}
    for language in document_languages:
        if language == primary:
            continue
        if {primary, language}.issubset({"en", "fr"}):
            try:
                result[language] = nlp_service.translate(
                    prompt,
                    from_lang=primary,
                    to_lang=language,
                )
            except Exception:
                LOG.exception("Prompt translation %s -> %s failed", primary, language)
    return result


def _bind_response_citations(response: str, evidence):
    cited_indexes: list[int] = []
    issues: list[ValidationIssue] = []
    for match in EVIDENCE_TAG_RE.finditer(response):
        index = int(match.group("index"))
        if index >= len(evidence):
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="unknown_evidence_tag",
                    message=f"The synthesis model referenced unknown evidence tag E{index}.",
                )
            )
        elif index not in cited_indexes:
            cited_indexes.append(index)

    if evidence and not cited_indexes:
        issues.append(
            ValidationIssue(
                severity="warning",
                code="response_missing_evidence_tags",
                message="The synthesis model returned source-dependent prose without evidence tags.",
            )
        )

    def replace(match: re.Match[str]) -> str:
        index = int(match.group("index"))
        if index >= len(evidence):
            return match.group(0)
        return f"({evidence[index].inline_citation}) [E{index}]"

    bound = EVIDENCE_TAG_RE.sub(replace, response)
    citations = [
        CitationInfo(
            record_id=evidence[index].record_id,
            inline=evidence[index].inline_citation,
            full=evidence[index].full_citation,
            work=evidence[index].work,
            page_start=evidence[index].page_start,
            page_end=evidence[index].page_end,
        )
        for index in cited_indexes
        if index < len(evidence)
    ]
    return bound, citations, issues


async def handle_query(
    request: QueryRequest,
    rag_client: RAGClient,
    llm_client: LLMClient,
    nlp_service: NLPService,
    job_service: JobService,
    job_id: str,
) -> GenericResponse:
    start = time.perf_counter()
    token = request_id.set(job_id)
    try:
        await job_service.update_job(job_id, status="running", phase="preparing_evidence")
        prompt_languages = _detected_languages(nlp_service, request.prompt, request.locale)
        options = request.options
        evidence = []
        counts = {"candidate_count": 0, "deduplicated_count": 0, "returned_count": 0}

        if options.retrieval_mode == RetrievalMode.SELECTED:
            if not request.selected_evidence:
                raise ValueError("retrieval_mode='selected' requires selected_evidence")
            evidence = [
                input_to_evidence_record(item, evidence_tag=f"E{index}")
                for index, item in enumerate(request.selected_evidence[: options.limit])
            ]
            counts = {
                "candidate_count": len(request.selected_evidence),
                "deduplicated_count": len(evidence),
                "returned_count": len(evidence),
            }
        else:
            await job_service.update_job(job_id, status="running", phase="retrieving")
            query_by_language = _queries_by_language(
                nlp_service,
                request.prompt,
                prompt_languages,
                options.document_languages,
            )
            async with rag_client.lookup_semaphore:
                docs, counts = await asyncio.to_thread(
                    rag_client.hybrid_lookup,
                    query=request.prompt,
                    query_by_language=query_by_language,
                    languages=options.document_languages,
                    canonical_work_ids=options.canonical_work_ids,
                    limit=options.limit,
                )
            evidence = [
                document_to_evidence_record(doc, evidence_tag=f"E{index}")
                for index, doc in enumerate(docs)
            ]

        issues = validation_issues(evidence)
        if not evidence:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    code="no_evidence",
                    message="No evidence records were available for synthesis.",
                )
            )

        await job_service.update_job(job_id, status="running", phase="synthesizing")
        response, _ = await llm_client.prompt(
            params={
                "user": RESEARCH_PROMPT,
                "template": {
                    "prompt": request.prompt,
                    "response_language": options.response_language,
                    "context": generate_context_string(evidence) or "No evidence was retrieved.",
                },
            }
        )

        await job_service.update_job(job_id, status="running", phase="validating")
        bound_response, citations, citation_issues = _bind_response_citations(str(response), evidence)
        issues.extend(citation_issues)

        retrieval = RetrievalDiagnostics(
            mode=options.retrieval_mode,
            candidate_count=counts["candidate_count"],
            deduplicated_count=counts["deduplicated_count"],
            returned_count=counts["returned_count"],
            languages=options.document_languages,
            canonical_work_ids=options.canonical_work_ids,
        )
        content = ResearchResponseContent(
            response=bound_response,
            request_id=job_id,
            locale=request.locale,
            response_language=options.response_language,
            evidence=evidence,
            citations=citations,
            validation_issues=issues if options.include_diagnostics else [],
            retrieval=retrieval,
            query_metadata={
                "prompt_languages": prompt_languages,
                "document_languages": options.document_languages,
                "canonical_work_ids": options.canonical_work_ids,
                "retrieval_mode": options.retrieval_mode.value,
                "elapsed_seconds": round(time.perf_counter() - start, 4),
            },
        )
        return GenericResponse(content=content, results=[])
    finally:
        request_id.reset(token)
