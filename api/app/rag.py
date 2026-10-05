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

from __future__ import annotations

import copy
import json
import logging
import re
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import httpx

from .chroma_store import ChromaStore
from .claim_memory import ClaimMemoryIndex
from .config import settings
from .cross_encoder import predict_scores
from .llm_failures import ProviderRequestError
from .models import OllamaTouchupOptions, RAGPromptMetadataPolicy, RAGRunRequest
from .pipelines.manager import pipeline_manager
from .pipelines.models import PipelineDefinition
from .pipelines.overrides import resolve_pipeline_config
from .pipelines.research import (
    classify_cross_encoder_failure,
    compile_research_pipeline,
    resolve_research_runtime_settings,
)
from .record_types import EvidenceItem, QueryDecomposition, RetrievalCandidate
from .research_filters import combine_metadata_filters, metadata_filter_fields
from .research_followup import (
    GENERATION_CONTRACT,
    QUERY_CONTRACT,
    advisory_context,
    contextual_query_prompt,
    validate_contextual_query,
)
from .research_memory import ResponseMemoryIndex, memory_guidance
from .research_semantics import (
    CONCEPTS_ID,
    PERSONS_ID,
    SOURCE_AUTHOR_ID,
    SPEAKER_ID,
    TOPICS_ID,
    rerank_attribution_context,
    semantic_text,
    semantic_value,
    source_author,
    source_work_label,
)
from .research_sizing import (
    automatic_collection_sizing,
    collapse_adjacent_candidates,
    expand_context_neighbors,
)
from .retrieval_selection import (
    cosine_similarity,
    distance_to_relevance,
    mmr_select,
    source_aware_select,
)
from .structured_completion import (
    StructuredAttemptContext,
    complete_structured_json,
)
from .structured_json import (
    StructuredJsonTruncatedError,
    finish_reason_is_truncated,
    parse_json_object,
)
from .system_store import system_store

logger = logging.getLogger(__name__)

QUERY_TEMPLATE = """
Your job is to extract query details from the user's research request.

Prompt:
{prompt}

Additional instructions supplied separately:
{instructions}

Return exactly one JSON object:
{{
  "prompt_query": "the actual research question in English",
  "prompt_query_fr": "the same research question in French",
  "prompt_instructions": "only instructions actually supplied by the user",
  "response_language": "en"
}}

Rules:
- Do not answer the research question.
- Do not invent instructions.
- Preserve philosophical terminology.
- prompt_query_fr is required even when the original prompt is English.
- response_language should be "fr" only when the user clearly requests a French answer or writes primarily in French; otherwise "en".
- Return JSON only.
""".strip()

FOCUSED_PROMPT = """
You are DerridAI, an evidence-grounded scholarly research assistant.

<MASTER PROMPT>
{prompt_query}
</MASTER PROMPT>

<MASTER INSTRUCTIONS>
{prompt_instructions}
</MASTER INSTRUCTIONS>

<RESPONSE LANGUAGE>
{response_language}
</RESPONSE LANGUAGE>

<PRIOR_RESEARCH_MEMORY>
{prior_response_memory}
</PRIOR_RESEARCH_MEMORY>

<PRIOR_CLAIM_PROVENANCE>
{prior_claim_memory}
</PRIOR_CLAIM_PROVENANCE>

<EVIDENCE>
{context}
</EVIDENCE>

Guidelines:
- Preserve all supplied source-identity, attribution, quotation, stance, target, discourse-role, and proposition-status metadata.
- Treat the supplied source-document author as document authorship only; never substitute a default author when it is absent.
- Do not equate document authorship with proposition ownership. Distinguish the source author's own claims from positions the passage quotes, describes, reconstructs, endorses, questions, or criticizes.
- Use the supplied EVIDENCE as the sole basis for substantive claims.
- Prior memory is advisory workflow context, not current evidence. Never cite it
  or repeat an unsupported claim from it.
- Do not flatten quotation provenance.
- Preserve modality and negation.
- If evidence is insufficient, say so rather than inventing support.
- Respond in cohesive scholarly prose unless the user's instructions explicitly require another form.

Citation rules:
- Tag every substantive claim with one or more evidence IDs using double square
  brackets by default, such as [[E0]] or [[E0, E3]].
- Do not cite an evidence ID that does not support the claim.
""".strip()

THREAD_FOCUSED_PROMPT = """
You are DerridAI, an evidence-grounded scholarly research assistant.

<CURRENT_QUESTION>
{prompt_query}
</CURRENT_QUESTION>

<THREAD_CONTEXT advisory="true" evidentiary="false">
{thread_context}
</THREAD_CONTEXT>

<MASTER INSTRUCTIONS>
{prompt_instructions}
</MASTER INSTRUCTIONS>

<RESPONSE LANGUAGE>
{response_language}
</RESPONSE LANGUAGE>

<PRIOR_RESEARCH_MEMORY>
{prior_response_memory}
</PRIOR_RESEARCH_MEMORY>

<PRIOR_CLAIM_PROVENANCE>
{prior_claim_memory}
</PRIOR_CLAIM_PROVENANCE>

<EVIDENCE>
{context}
</EVIDENCE>

Guidelines:
- Preserve all supplied source-identity, attribution, quotation, stance, target, discourse-role, and proposition-status metadata.
- Treat the supplied source-document author as document authorship only; never substitute a default author when it is absent.
- Do not equate document authorship with proposition ownership. Distinguish the source author's own claims from positions the passage quotes, describes, reconstructs, endorses, questions, or criticizes.
- Use the supplied EVIDENCE as the sole basis for substantive claims.
- Thread context and prior memory are advisory, non-evidentiary context.
  Current evidence governs any conflict with previous generated claims.
  Never cite thread context or reuse its historical evidence markers.
- Prior memory is advisory workflow context, not current evidence. Never cite it
  or repeat an unsupported claim from it.
- Do not flatten quotation provenance.
- Preserve modality and negation.
- If evidence is insufficient, say so rather than inventing support.
- Respond in cohesive scholarly prose unless the user's instructions explicitly require another form.

Citation rules:
- Tag every substantive claim with one or more evidence IDs using double square
  brackets by default, such as [[E0]] or [[E0, E3]].
- Do not cite an evidence ID that does not support the claim.
""".strip()


def _extract_json(text: str) -> dict[str, Any]:
    """Compatibility wrapper around the shared repair-first structured parser."""
    return parse_json_object(text)


def _response_error_metadata(
    response: httpx.Response,
) -> tuple[str, str | None, str | None]:
    """Return bounded diagnostics plus machine-readable provider error identity."""

    try:
        payload = response.json()
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                return (
                    str(error.get("message") or error)[:1200],
                    str(error.get("code") or "") or None,
                    str(error.get("type") or "") or None,
                )
            return (
                str(payload.get("detail") or payload.get("message") or "")[:1200],
                str(payload.get("code") or "") or None,
                str(payload.get("type") or "") or None,
            )
    except Exception:
        logger.debug("Could not parse provider error JSON; using response text", exc_info=True)
    return response.text[:1200], None, None


def _response_detail(response: httpx.Response) -> str:
    """Compatibility helper returning only the bounded provider diagnostic."""

    return _response_error_metadata(response)[0]


def _retry_after_seconds(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return None


def _provider_request_error(
    response: httpx.Response,
    *,
    prefix: str,
) -> ProviderRequestError:
    detail, provider_code, provider_error_type = _response_error_metadata(response)
    capability_text = f"{detail} {provider_code or ''} {provider_error_type or ''}".casefold()
    capability_mismatch = any(
        marker in capability_text
        for marker in ("format_ignored", "response_format", "json_schema")
    )
    return ProviderRequestError(
        f"{prefix} returned HTTP {response.status_code}: {detail}",
        status_code=response.status_code,
        provider_code=provider_code,
        provider_error_type=provider_error_type,
        retry_after_seconds=_retry_after_seconds(response),
        capability_mismatch=capability_mismatch,
    )


def _provider_request_error_from_raw(
    status_code: int,
    detail: str,
    *,
    prefix: str,
) -> ProviderRequestError:
    """Build the same typed error for streaming failures without a live Response."""

    provider_code: str | None = None
    provider_error_type: str | None = None
    bounded = str(detail or "")[:1200]
    try:
        payload = json.loads(detail)
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                bounded = str(error.get("message") or error)[:1200]
                provider_code = str(error.get("code") or "") or None
                provider_error_type = str(error.get("type") or "") or None
    except (TypeError, ValueError, json.JSONDecodeError):
        pass
    capability_text = f"{bounded} {provider_code or ''} {provider_error_type or ''}".casefold()
    return ProviderRequestError(
        f"{prefix} returned HTTP {status_code}: {bounded}",
        status_code=status_code,
        provider_code=provider_code,
        provider_error_type=provider_error_type,
        capability_mismatch=any(
            marker in capability_text
            for marker in ("format_ignored", "response_format", "json_schema")
        ),
    )


def chat_complete(
    *,
    provider: str,
    model: str,
    base_url: str | None,
    api_key: str | None,
    prompt: str,
    options: OllamaTouchupOptions | None = None,
    json_mode: bool = False,
    json_schema: dict[str, Any] | None = None,
    schema_name: str = "derridai_response",
    max_tokens: int | None = None,
    cancelled: Callable[[], bool] | None = None,
    timeout_seconds: float | None = None,
    on_delta: Callable[[str], None] | None = None,
) -> str:
    """One chat completion. ``on_delta`` receives streamed text pieces as they arrive.

    Deltas are an untrusted, unvalidated draft for live display only; the return
    value is the complete answer every caller must validate. A failing callback
    never interrupts generation.
    """
    tuning = options or OllamaTouchupOptions()
    provider = provider.strip().lower()
    structured_requested = bool(json_mode or json_schema is not None)

    def complete(content: Any, finish_reason: str | None = None) -> str:
        text = str(content or "").strip()
        if structured_requested and finish_reason_is_truncated(finish_reason):
            raise StructuredJsonTruncatedError(
                f"LLM structured response was cut off by provider finish reason {finish_reason!r}.",
                diagnostic=text[:2000],
                finish_reason=finish_reason,
            )
        return text

    def emit(piece: str) -> None:
        if on_delta is None or not piece:
            return
        try:
            on_delta(piece)
        except Exception:
            logger.debug("Generation delta callback failed; continuing", exc_info=True)

    if provider == "openai":
        url = (base_url or settings.openai_compat_base_url).rstrip("/")
        headers = {"Content-Type": "application/json"}
        key = api_key if api_key is not None else settings.openai_compat_api_key
        if key:
            headers["Authorization"] = f"Bearer {key}"
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0 if tuning.temperature is None else tuning.temperature,
            "max_tokens": max_tokens or tuning.num_predict or 4096,
        }
        if tuning.top_p is not None:
            body["top_p"] = tuning.top_p
        if tuning.seed is not None:
            body["seed"] = tuning.seed
        if tuning.stop:
            body["stop"] = tuning.stop
        if json_schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": json_schema},
            }
        elif json_mode:
            body["response_format"] = {"type": "json_object"}
        for key_name, value in (tuning.extra_options or {}).items():
            if key_name not in {"model", "messages"}:
                body[key_name] = value

        timeout = httpx.Timeout(
            connect=settings.openai_connect_timeout_seconds,
            read=min(settings.openai_timeout_seconds, timeout_seconds) if timeout_seconds else settings.openai_timeout_seconds,
            write=min(settings.openai_timeout_seconds, timeout_seconds) if timeout_seconds else settings.openai_timeout_seconds,
            pool=settings.openai_connect_timeout_seconds,
        )
        if cancelled is not None:
            def stream_once(payload: dict[str, Any]) -> tuple[int, str, str, str | None]:
                started_clock = time.monotonic()
                streaming = dict(payload)
                streaming["stream"] = True
                chunks: list[str] = []
                finish_reason: str | None = None
                with httpx.Client(timeout=timeout) as client:
                    with client.stream(
                        "POST",
                        f"{url}/chat/completions",
                        headers=headers,
                        json=streaming,
                    ) as response:
                        if response.status_code >= 400:
                            raw = response.read().decode("utf-8", errors="replace")
                            return response.status_code, "", raw[:2000], None
                        for line in response.iter_lines():
                            if timeout_seconds and time.monotonic() - started_clock > timeout_seconds:
                                raise TimeoutError(f"LLM generation exceeded {timeout_seconds:.0f}s stage deadline.")
                            if cancelled():
                                raise InterruptedError("RAG generation cancelled.")
                            if not line or not line.startswith("data:"):
                                continue
                            data = line[5:].strip()
                            if data == "[DONE]":
                                break
                            try:
                                event = json.loads(data)
                            except json.JSONDecodeError:
                                continue
                            choices = event.get("choices") or []
                            if choices and choices[0].get("finish_reason") is not None:
                                finish_reason = str(choices[0].get("finish_reason"))
                            delta = choices[0].get("delta") if choices else {}
                            piece = (delta or {}).get("content") or ""
                            if isinstance(piece, list):
                                piece = "".join(
                                    str(part.get("text") or "")
                                    for part in piece
                                    if isinstance(part, dict)
                                )
                            if piece:
                                chunks.append(str(piece))
                                emit(str(piece))
                return 200, "".join(chunks).strip(), "", finish_reason

            status, content, detail, finish_reason = stream_once(body)
            if status in {400, 422} and "response_format" in body:
                fallback = dict(body)
                # Some OpenAI-compatible routers support JSON mode but not JSON Schema.
                # Preserve structured output when possible before falling all the way
                # back to unconstrained text.
                if json_schema is not None:
                    fallback["response_format"] = {"type": "json_object"}
                else:
                    fallback.pop("response_format", None)
                status, content, detail, finish_reason = stream_once(fallback)
                if status in {400, 422} and "response_format" in fallback:
                    fallback.pop("response_format", None)
                    status, content, detail, finish_reason = stream_once(fallback)
            if status in {400, 422}:
                # Preserve compatibility with local OpenAI-compatible routers
                # that support Chat Completions but not streaming.
                fallback_body = dict(body)
                fallback_body.pop("stream", None)
                with httpx.Client(timeout=timeout) as client:
                    response = client.post(
                        f"{url}/chat/completions",
                        headers=headers,
                        json=fallback_body,
                    )
                if response.status_code < 400:
                    payload = response.json()
                    choices = payload.get("choices") or []
                    message = choices[0].get("message") if choices else {}
                    finish_reason = (
                        str(choices[0].get("finish_reason"))
                        if choices and choices[0].get("finish_reason") is not None
                        else None
                    )
                    content = (message or {}).get("content") or ""
                    if isinstance(content, list):
                        content = "".join(
                            str(part.get("text") or "")
                            for part in content
                            if isinstance(part, dict)
                        )
                    if cancelled and cancelled():
                        raise InterruptedError("RAG generation cancelled.")
                    status = 200
            if status >= 400:
                raise _provider_request_error_from_raw(
                    status,
                    detail,
                    prefix="OpenAI-compatible endpoint",
                )
            return complete(content, finish_reason)

        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{url}/chat/completions",
                headers=headers,
                json=body,
            )
            if response.status_code in {400, 422} and "response_format" in body:
                if json_schema is not None:
                    body["response_format"] = {"type": "json_object"}
                    response = client.post(
                        f"{url}/chat/completions",
                        headers=headers,
                        json=body,
                    )
                if response.status_code in {400, 422} and "response_format" in body:
                    body.pop("response_format", None)
                    response = client.post(
                        f"{url}/chat/completions",
                        headers=headers,
                        json=body,
                    )
        if response.status_code >= 400:
            raise _provider_request_error(
                response,
                prefix="OpenAI-compatible endpoint",
            )
        payload = response.json()
        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError("OpenAI-compatible endpoint returned no choices.")
        finish_reason = (
            str(choices[0].get("finish_reason"))
            if choices[0].get("finish_reason") is not None
            else None
        )
        content = (choices[0].get("message") or {}).get("content") or ""
        if isinstance(content, list):
            content = "".join(
                str(part.get("text") or "")
                for part in content
                if isinstance(part, dict)
            )
        return complete(content, finish_reason)

    url = (base_url or settings.ollama_base_url).rstrip("/")
    option_values: dict[str, Any] = dict(tuning.extra_options or {})
    for key_name, value in {
        "num_ctx": tuning.num_ctx,
        "num_predict": max_tokens or tuning.num_predict,
        "temperature": 0.0 if tuning.temperature is None else tuning.temperature,
        "top_k": tuning.top_k,
        "top_p": tuning.top_p,
        "min_p": tuning.min_p,
        "repeat_penalty": tuning.repeat_penalty,
        "seed": tuning.seed,
        "mirostat": tuning.mirostat,
        "mirostat_eta": tuning.mirostat_eta,
        "mirostat_tau": tuning.mirostat_tau,
        "stop": tuning.stop,
    }.items():
        if value is not None:
            option_values[key_name] = value

    body = {
        "model": model,
        "stream": False,
        "messages": [{"role": "user", "content": prompt}],
        "options": option_values,
    }
    if json_schema is not None:
        # Ollama accepts a JSON Schema object in `format`; this materially reduces
        # malformed output from local models while remaining compatible with the
        # ordinary `format: json` fallback below.
        body["format"] = json_schema
    elif json_mode:
        body["format"] = "json"
    if tuning.think is not None:
        body["think"] = tuning.think
    keep_alive = tuning.keep_alive or settings.ollama_keep_alive
    if keep_alive:
        body["keep_alive"] = keep_alive

    timeout = httpx.Timeout(
        connect=settings.ollama_connect_timeout_seconds,
        read=min(settings.ollama_timeout_seconds, timeout_seconds) if timeout_seconds else settings.ollama_timeout_seconds,
        write=min(settings.ollama_timeout_seconds, timeout_seconds) if timeout_seconds else settings.ollama_timeout_seconds,
        pool=settings.ollama_connect_timeout_seconds,
    )
    if cancelled is not None:
        def ollama_stream_once(payload: dict[str, Any]) -> tuple[int, str, str, str | None]:
            started_clock = time.monotonic()
            streaming = dict(payload)
            streaming["stream"] = True
            chunks: list[str] = []
            finish_reason: str | None = None
            with httpx.Client(timeout=timeout) as client:
                with client.stream("POST", f"{url}/api/chat", json=streaming) as response:
                    if response.status_code >= 400:
                        raw = response.read().decode("utf-8", errors="replace")
                        return response.status_code, "", raw[:2000], None
                    for line in response.iter_lines():
                        if timeout_seconds and time.monotonic() - started_clock > timeout_seconds:
                            raise TimeoutError(f"LLM generation exceeded {timeout_seconds:.0f}s stage deadline.")
                        if cancelled():
                            raise InterruptedError("RAG generation cancelled.")
                        if not line:
                            continue
                        payload_line = json.loads(line)
                        piece = ((payload_line.get("message") or {}).get("content") or "")
                        if piece:
                            chunks.append(str(piece))
                            emit(str(piece))
                        if payload_line.get("done"):
                            reason = payload_line.get("done_reason") or payload_line.get("stop_reason")
                            finish_reason = str(reason) if reason is not None else None
                            break
            return 200, "".join(chunks).strip(), "", finish_reason

        status, content, detail, finish_reason = ollama_stream_once(body)
        if status in {400, 422} and json_schema is not None:
            fallback = dict(body)
            fallback["format"] = "json"
            status, content, detail, finish_reason = ollama_stream_once(fallback)
        if status >= 400:
            raise RuntimeError(f"Ollama returned HTTP {status}: {detail}")
        return complete(content, finish_reason)

    with httpx.Client(timeout=timeout) as client:
        response = client.post(f"{url}/api/chat", json=body)
        if response.status_code in {400, 422} and json_schema is not None:
            # Older Ollama builds support JSON mode but not schema-valued format.
            # Keep the corpus builder compatible while Pydantic validation/retry
            # still enforces the contract after generation.
            fallback = dict(body)
            fallback["format"] = "json"
            response = client.post(f"{url}/api/chat", json=fallback)
    if response.status_code >= 400:
        raise _provider_request_error(response, prefix="Ollama")
    payload = response.json()
    finish_reason = payload.get("done_reason") or payload.get("stop_reason")
    return complete(
        (payload.get("message") or {}).get("content") or "",
        str(finish_reason) if finish_reason is not None else None,
    )


def structured_chat_complete(
    *,
    provider: str,
    model: str,
    base_url: str | None,
    api_key: str | None,
    prompt: str,
    options: OllamaTouchupOptions | None = None,
    json_schema: dict[str, Any] | None = None,
    schema_name: str = "derridai_response",
    max_tokens: int = 4096,
    attempts: int = 2,
    max_token_cap: int | None = None,
    validate: Callable[[dict[str, Any]], Any] | None = None,
    retry_guidance: Callable[[Exception], str] | None = None,
    cancelled: Callable[[], bool] | None = None,
    timeout_seconds: float | None = None,
    on_delta: Callable[[str], None] | None = None,
    on_metric: Callable[[str, int], None] | None = None,
    completion: Callable[..., str] | None = None,
) -> Any:
    """Run one JSON-object task through the shared repair/retry contract.

    completion is injectable for compatibility tests and specialized transports;
    production callers normally use the module's chat_complete.
    """

    transport = completion or chat_complete

    def request_once(context: StructuredAttemptContext) -> str:
        return transport(
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
            prompt=context.prompt,
            options=options,
            json_mode=True,
            json_schema=json_schema,
            schema_name=schema_name,
            max_tokens=context.max_tokens,
            cancelled=cancelled,
            timeout_seconds=timeout_seconds,
            on_delta=on_delta,
        )

    return complete_structured_json(
        request_once,
        prompt=prompt,
        validate=validate,
        attempts=attempts,
        max_tokens=max_tokens,
        max_token_cap=max_token_cap,
        retry_guidance=retry_guidance,
        on_metric=on_metric,
    )


def _citation_strings(record: dict[str, Any]) -> tuple[str, str]:
    author = source_author(record) or semantic_text(record, SPEAKER_ID)
    work = source_work_label(record)
    edition = str(record.get("edition") or "")
    year = record.get("year") or ""
    page_start = record.get("page_start")
    page_end = record.get("page_end")
    translator = str(record.get("translator") or "")

    last = author.split()[-1] if author.split() else author
    if page_start is None:
        pages = ""
    elif page_end is None or page_end == page_start:
        pages = str(page_start)
    else:
        pages = f"{page_start}-{page_end}"
    timed_spans = [span for span in record.get("source_spans") or []
                   if span.get("locator_kind") == "time"]
    if timed_spans:
        from .source_audio import _timestamp_label

        pages = "; ".join(
            _timestamp_label(float(span["start"]), float(span["end"]))
            + (f" [{span['speaker']}]" if span.get("speaker") else "")
            for span in timed_spans
        )
    inline = f"{last} {year}{': ' + pages if pages else ''}".strip()

    parts = author.split()
    reversed_name = (
        f"{parts[-1]}, {' '.join(parts[:-1])}"
        if len(parts) > 1 else author
    )
    full = (
        # No author is assumed: when the record names none, the citation simply omits it.
        f"{reversed_name + '. ' if reversed_name else ''}{work}."
        f"{f' {translator} trans.' if translator else ''}"
        f"{f' {edition}.' if edition else ''}"
        f"{f' {year}.' if year else ''}"
    )
    return inline.strip(), re.sub(r"\s+", " ", full).strip()


def _prompt_metadata_value(record: Mapping[str, Any], selector: str) -> tuple[str, Any] | None:
    """Resolve a prompt selector through current FieldAssertions or record projection."""
    field = str(selector or "").strip()
    if not field:
        return None
    selected = record.get("current_field_assertions")
    buckets = record.get("field_assertions")
    if isinstance(selected, dict) and isinstance(buckets, dict):
        for field_id, values in buckets.items():
            if not isinstance(values, list) or not values:
                continue
            selected_id = str(selected.get(field_id) or "")
            current = next(
                (item for item in values if isinstance(item, dict) and str(item.get("assertion_id") or "") == selected_id),
                values[-1] if isinstance(values[-1], dict) else None,
            )
            if not isinstance(current, dict):
                continue
            name = str(current.get("field_name") or "")
            identity = str(current.get("field_id") or field_id)
            if field not in {name, identity}:
                continue
            if str(current.get("value_status") or "") == "confirmed_absent":
                return name or field, None
            if current.get("value_status") and str(current.get("value_status")) != "present":
                return None
            return name or field, current.get("value")
    if field in record:
        return field, record.get(field)
    return None


def _prompt_metadata(record: Mapping[str, Any], selectors: Sequence[str]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for selector in selectors:
        resolved = _prompt_metadata_value(record, selector)
        if resolved is None:
            continue
        field, value = resolved
        # Preserve false/zero/null when explicitly selected; only absent selectors are omitted.
        metadata[field] = value
    return metadata

def _context_string(
    records: list[dict[str, Any]],
    *,
    record_char_limit: int,
    total_char_limit: int,
    prompt_metadata: RAGPromptMetadataPolicy | None = None,
    skip_overflow: bool = False,
) -> tuple[str, dict[str, str], list[EvidenceItem]]:
    blocks: list[str] = []
    works: dict[str, str] = {}
    evidence: list[EvidenceItem] = []
    total_chars = 0

    for item in records:
        record = dict(item["record"])
        record.pop("updates", None)
        inline, full = _citation_strings(record)
        raw_text = " ".join(str(record.get("text") or "").split())
        text_truncated = len(raw_text) > record_char_limit
        compact_text = raw_text[:record_char_limit]
        if text_truncated:
            compact_text = compact_text.rstrip() + " …"

        tag = f"E{len(evidence)}"
        policy = prompt_metadata or RAGPromptMetadataPolicy()
        evidence_metadata = _prompt_metadata(record, policy.evidence)
        context_metadata = _prompt_metadata(record, policy.context)
        record_metadata = _prompt_metadata(record, policy.record)
        metadata_lines = [
            f"{field}={json.dumps(value, ensure_ascii=False)}"
            for field, value in evidence_metadata.items()
        ]
        if context_metadata:
            metadata_lines.append(
                "context_metadata=" + json.dumps(context_metadata, ensure_ascii=False, sort_keys=True)
            )
        if record_metadata:
            metadata_lines.append(
                "record_metadata=" + json.dumps(record_metadata, ensure_ascii=False, sort_keys=True)
            )
        block = "\n".join([
            f"<BEGIN EVIDENCE_TAG {tag}>",
            f"evidence_tag=[[{tag}]]",
            f"record_id={record.get('record_id', '')}",
            f"source_work={source_work_label(record)}",
            f"source_document_author={source_author(record)}",
            *metadata_lines,
            f"citation={inline}",
            f"text={compact_text}",
            f"<END EVIDENCE_TAG {tag}>",
        ])

        projected = total_chars + len(block) + (2 if blocks else 0)
        if blocks and projected > total_char_limit:
            if skip_overflow:
                # Auto-sizing packs all ranking anchors before neighbors. When
                # one item cannot fit, keep looking rather than letting a single
                # large Record prevent later compact evidence from using the
                # remaining budget.
                continue
            break

        total_chars = projected
        works[tag] = inline
        evidence.append({
            "evidence_id": tag,
            "collection": item.get("collection"),
            "distance": item.get("distance"),
            "rerank_score": item.get("rerank_score"),
            "rrf_score": item.get("rrf_score"),
            "retrieval_hits": item.get("retrieval_hits", []),
            "record": record,
            "inline_citation": inline,
            "full_citation": full,
            "text_truncated": text_truncated,
            "selection_role": item.get("selection_role"),
            "neighbor_of": item.get("neighbor_of"),
            "neighbor_distance": item.get("neighbor_distance"),
            "neighbor_reason": item.get("neighbor_reason"),
            "automatic_region_size": item.get("automatic_region_size"),
        })
        blocks.append(block)

    return "\n\n".join(blocks), works, evidence


def evidence_sufficiency_issues(evidence: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    """Return deterministic provenance failures before generation can begin."""
    issues: list[dict[str, str]] = []
    for item in evidence:
        record = item.get("record") if isinstance(item.get("record"), dict) else {}
        evidence_id = str(item.get("evidence_id") or "unknown")
        missing = [
            field
            for field, value in {
                "record_id": record.get("record_id"),
                "work": source_work_label(record),
                "document_author": source_author(record),
                "exact_text": record.get("text"),
                "inline_citation": item.get("inline_citation"),
                "full_citation": item.get("full_citation"),
            }.items()
            if not str(value or "").strip()
        ]
        if missing:
            issues.append({"evidence_id": evidence_id, "missing": ", ".join(missing)})
    return issues


def partition_sufficient_records(
    records: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Split ranked candidates into citable records and provenance-incomplete ones.

    Incomplete records are excluded before evidence tags are assigned, so one
    record lacking e.g. ``document_author`` cannot abort the whole run; the
    exclusions are returned so callers can surface them for review.
    """
    kept: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    for item in records:
        record = item.get("record") if isinstance(item.get("record"), dict) else {}
        inline, full = _citation_strings(dict(record))
        issues = evidence_sufficiency_issues([{
            "evidence_id": str(record.get("record_id") or "unknown"),
            "record": record,
            "inline_citation": inline,
            "full_citation": full,
        }])
        if issues:
            excluded.append({"record_id": issues[0]["evidence_id"], "missing": issues[0]["missing"]})
        else:
            kept.append(dict(item))
    return kept, excluded


_EVIDENCE_TAG_GROUP = r"((?:E\d+)(?:\s*[,;]\s*E\d+)*)"
# Memory-guidance prompt tags are internal grounding context, never citation syntax.
# If a model echoes one, strip it before the answer reaches the reader.
_STRAY_MEMORY_TAG_PATTERN = re.compile(
    r"\[{1,2}\s*(?:prior-claim|prior-response):[^\[\]]+\]{1,2}"
)
EVIDENCE_MARKER_PATTERNS = (
    rf"\[\[\s*{_EVIDENCE_TAG_GROUP}\s*\]\]",
    rf"\(\(\s*{_EVIDENCE_TAG_GROUP}\s*\)\)",
    rf"\{{\{{\s*{_EVIDENCE_TAG_GROUP}\s*\}}\}}",
    rf"\[\s*{_EVIDENCE_TAG_GROUP}\s*\]",
    rf"\(\s*{_EVIDENCE_TAG_GROUP}\s*\)",
    rf"\{{\s*{_EVIDENCE_TAG_GROUP}\s*\}}",
)


def extract_evidence_ids(text: str) -> list[str]:
    """Return evidence IDs from every marker syntax accepted by citation binding."""
    ids: list[str] = []
    for pattern in EVIDENCE_MARKER_PATTERNS:
        for match in re.finditer(pattern, str(text or "")):
            for tag in re.findall(r"\bE\d+\b", match.group(1)):
                if tag not in ids:
                    ids.append(tag)
    return ids


def strip_evidence_markers(text: str) -> str:
    """Remove citation markers without changing the substantive claim text."""
    value = str(text or "")
    for pattern in EVIDENCE_MARKER_PATTERNS:
        value = re.sub(pattern, "", value)
    value = re.sub(r"\s+([.,;:!?])", r"\1", value)
    return re.sub(r"\s{2,}", " ", value).strip()


def _bind_sources(answer: str, evidence: list[EvidenceItem], include_works_cited: bool) -> str:
    citation_map = {
        item["evidence_id"]: item["inline_citation"]
        for item in evidence
    }

    def replace_group(match: re.Match[str]) -> str:
        inside = match.group(1)
        tags = re.findall(r"\bE\d+\b", inside)
        if not tags:
            return match.group(0)
        rendered = [
            citation_map.get(tag, tag)
            for tag in tags
        ]
        return "(" + "; ".join(dict.fromkeys(rendered)) + ")"

    used_ids = set(extract_evidence_ids(answer))
    # Generators do not always obey one citation wrapper exactly. Keep rendering
    # and durable claim/support persistence on the same accepted marker syntax.
    bound = _STRAY_MEMORY_TAG_PATTERN.sub("", answer)
    for pattern in EVIDENCE_MARKER_PATTERNS:
        bound = re.sub(pattern, replace_group, bound)

    if include_works_cited:
        seen: set[str] = set()
        citations: list[str] = []
        for item in evidence:
            if used_ids and item["evidence_id"] not in used_ids:
                continue
            record = item["record"]
            canonical = str(
                record.get("canonical_work_id")
                or item["full_citation"]
            )
            if canonical in seen:
                continue
            seen.add(canonical)
            citations.append(item["full_citation"])
        if citations:
            bound += "\n\n**Works Cited**\n\n" + "\n".join(
                f"{index}. {citation}"
                for index, citation in enumerate(citations, start=1)
            )
    return bound


def _cosine(a: Any, b: Any) -> float:
    """Compatibility wrapper around the shared retrieval-scoring primitive."""

    return cosine_similarity(a, b)


def _distance_similarity(distance: float | None) -> float:
    """Legacy metric-unknown wrapper retained for memory/reranker compatibility."""

    return distance_to_relevance(distance)


def _mmr_select(
    candidates: list[dict[str, Any]],
    *,
    k: int,
    lambda_mult: float,
) -> list[dict[str, Any]]:
    """Compatibility wrapper that now preserves MMR objective provenance."""

    return mmr_select(
        candidates,
        limit=k,
        lambda_mult=lambda_mult,
        relevance=lambda candidate: float(
            candidate.get("relevance")
            if candidate.get("relevance") is not None
            else _distance_similarity(candidate.get("distance"))
        ),
        vector=lambda candidate: candidate.get("embedding"),
    )


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[\wÀ-ÿ'-]+", str(text).casefold())
        if len(token) > 2
    }


def _rerank_candidate_text(item: Mapping[str, Any]) -> str:
    """Expose semantic attribution roles to rerankers."""

    record = item.get("record") if isinstance(item.get("record"), Mapping) else {}
    passage = str(item.get("_rerank_text") or record.get("text") or "")
    return rerank_attribution_context(record, passage)


def _lexical_rerank(query: str, docs: list[dict[str, Any]], top_n: int) -> list[dict[str, Any]]:
    q = _tokenize(query)
    scored: list[dict[str, Any]] = []
    for index, item in enumerate(docs):
        record = item["record"]
        text = " ".join([
            source_author(record),
            source_work_label(record),
            semantic_text(record, SPEAKER_ID),
            semantic_text(record, TOPICS_ID),
            semantic_text(record, CONCEPTS_ID),
            semantic_text(record, PERSONS_ID),
            _rerank_candidate_text(item),
        ])
        tokens = _tokenize(text)
        overlap = len(q & tokens) / max(1, len(q))
        author_tokens = _tokenize(source_author(record))
        source_author_overlap = len(q & author_tokens) / max(1, len(q))
        retrieval_bonus = 1.0 / (60.0 + index + 1.0)
        similarity = float(
            item.get("relevance")
            if item.get("relevance") is not None
            else _distance_similarity(item.get("distance"))
        )
        row = dict(item)
        # Explicit source-author agreement is stronger evidence of source scope
        # than merely mentioning the same author in passage text/metadata.
        row["rerank_score"] = (
            overlap * 2.0
            + source_author_overlap
            + similarity
            + retrieval_bonus
        )
        scored.append(row)
    return sorted(
        scored,
        key=lambda item: item.get("rerank_score", 0.0),
        reverse=True,
    )[:top_n]


def _cross_encoder_rerank(
    query: str,
    docs: list[dict[str, Any]],
    top_n: int,
    model_name: str,
    *,
    timeout_seconds: float | None,
) -> tuple[list[dict[str, Any]] | None, str | None, dict[str, Any]]:
    """Attempt CrossEncoder reranking without inventing a fallback path.

    Fallback routing belongs to the selected pipeline graph. This helper reports
    the operational failure; run_rag_pipeline then follows the configured
    on_unavailable/on_timeout/on_error edge.
    """

    scores, telemetry = predict_scores(
        [
            (
                query,
                _rerank_candidate_text(item),
            )
            for item in docs
        ],
        model_name=model_name,
        timeout_seconds=timeout_seconds,
    )
    if scores is None:
        reason = str(telemetry.get("fallback_reason") or "unavailable")
        return None, f"Cross-encoder unavailable ({reason}).", {
            **telemetry,
            "mode": "unavailable",
            "fallback_reason": reason,
        }

    ranked = []
    for item, score in zip(docs, scores):
        row = dict(item)
        row["rerank_score"] = score
        row["cross_encoder_score"] = score
        ranked.append(row)
    ranked.sort(key=lambda item: item["rerank_score"], reverse=True)
    return ranked[:top_n], None, {**telemetry, "mode": "cross_encoder"}


def _resolve_search_collections(
    store: ChromaStore,
    source_name: str,
    locales: list[str],
) -> list[dict[str, Any]]:
    stores = store.list_stores()
    source = next((item for item in stores if item["name"] == source_name), None)
    if source is None:
        raise ValueError(f"Collection {source_name!r} does not exist.")

    source_metadata = (
        source.get("metadata") if isinstance(source.get("metadata"), dict) else {}
    )
    system_kind = str(source_metadata.get("derridai_system_collection") or "").strip()
    if system_kind:
        raise ValueError(
            f"Collection {source_name!r} is a DerridAI system collection "
            f"({system_kind}) and cannot be used as a Research source collection."
        )

    requested = list(dict.fromkeys(locales or ["en", "fr"]))
    requested_set = set(requested)

    if source.get("collection_role") == "language":
        codes = set(source.get("language_codes") or [])
        if requested_set and not (codes & requested_set):
            return []
        row = dict(source)
        row["_rag_locales"] = list(codes & requested_set) or list(codes)
        return [row]

    resolved: list[dict[str, Any]] = []
    for locale in requested:
        derived = next((
            item
            for item in stores
            if item.get("collection_role") == "language"
            and (
                item.get("source_collection") == source_name
                or item.get("name") == f"{source_name}_{locale}"
            )
            and locale in set(item.get("language_codes") or [])
        ), None)
        if derived:
            row = dict(derived)
            row["_rag_locales"] = [locale]
            row["_rag_route"] = f"{locale}:derived"
            resolved.append(row)
        else:
            # Keep one source-collection route per requested language rather
            # than merging en/fr into one query. This preserves bilingual
            # retrieval even when derivative collections have not been built.
            row = dict(source)
            row["_rag_locales"] = [locale]
            row["_rag_route"] = f"{locale}:source_fallback"
            resolved.append(row)

    if not resolved:
        row = dict(source)
        row["_rag_locales"] = list(source.get("language_codes") or ["en", "fr"])
        row["_rag_route"] = "source"
        resolved.append(row)
    return resolved


def _selected_evidence_candidates(request: RAGRunRequest, store: ChromaStore) -> list[RetrievalCandidate]:
    """Resolve user-selected evidence to authoritative records.

    DB-backed researcher selections are sent as collection/id pairs so the full
    source stays server-side. Admin-only workspace selections may carry a record
    directly. The resulting candidate shape matches retrieval candidates and can
    therefore enter the existing context/citation pipeline unchanged.
    """
    resolved: list[RetrievalCandidate] = []
    seen: set[str] = set()
    for selection in request.selected_evidence or []:
        record: dict[str, Any] | None = None
        collection = selection.collection
        chroma_id = selection.chroma_id
        if collection and chroma_id:
            record = store.get_record(collection, chroma_id)
        elif selection.record:
            record = dict(selection.record)
            record.pop("updates", None)
        if not record:
            continue
        logical = str(record.get("record_id") or chroma_id or len(resolved))
        key = f"{collection or 'workspace'}::{logical}"
        if key in seen:
            continue
        seen.add(key)
        resolved.append({
            "id": chroma_id or logical,
            "collection": collection or "selected_workspace",
            "record": record,
            "distance": None,
            "rrf_score": 1.0,
            "rerank_score": 1.0,
            "retrieval_hits": [{"collection": collection or "workspace", "search_type": "selected", "rank": 0}],
            "selected_evidence": True,
        })
    return resolved


def _candidate_diagnostic(item: Mapping[str, Any], rank: int) -> dict[str, Any]:
    """Bounded candidate lineage for non-persistent comparison/benchmark runs.

    Source text and arbitrary Record metadata are intentionally excluded. The
    retained fields are enough to compare membership, rank, retrieval route,
    and stage-specific scores without copying the corpus into diagnostics.
    """

    record = item.get("record") if isinstance(item.get("record"), Mapping) else {}
    return {
        "record_id": str(
            record.get("record_id")
            or item.get("chroma_id")
            or item.get("id")
            or ""
        ),
        "rank": rank,
        "collection": item.get("collection"),
        "selected_evidence": bool(item.get("selected_evidence")),
        "distance": item.get("distance"),
        "distance_metric": item.get("distance_metric"),
        "relevance": item.get("relevance"),
        "rrf_score": item.get("rrf_score"),
        "rerank_score": item.get("rerank_score"),
        "retrieval_hits": list(item.get("retrieval_hits") or []),
    }


def _candidate_diagnostics(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        diagnostic
        for rank, item in enumerate(rows, start=1)
        if (diagnostic := _candidate_diagnostic(item, rank))["record_id"]
    ]


def _normalized_scope_text(value: Any) -> str:
    """Normalize author/work names for deterministic prompt-scope matching."""

    folded = str(value or "").casefold().replace("’", "'")
    folded = re.sub(r"'s\b", "", folded)
    return re.sub(r"[^\wÀ-ÿ]+", " ", folded, flags=re.UNICODE).strip()


def _mentions_scope_author(question: str, author: str) -> bool:
    """Return whether a prompt explicitly names a corpus author."""

    query = _normalized_scope_text(question)
    normalized_author = _normalized_scope_text(author)
    if not query or not normalized_author:
        return False
    if normalized_author in query:
        return True
    parts = [part for part in normalized_author.split() if part]
    surname = parts[-1] if parts else ""
    return bool(surname and len(surname) >= 4 and surname in set(query.split()))


def _mentioned_work_groups(
    work_summaries: Sequence[Mapping[str, Any]],
    question: str,
    *,
    max_groups: int = 4,
) -> list[list[str]]:
    """Resolve explicitly named works/authors to bounded corpus work groups.

    Named authors and works are routing signals only. They do not establish any
    scholarly claim or source authority; they reserve retrieval coverage for
    corpus scopes the researcher explicitly requested.
    """

    query = _normalized_scope_text(question)
    if not query:
        return []

    groups: list[list[str]] = []
    author_works: dict[str, set[str]] = {}
    for summary in work_summaries:
        work = str(summary.get("scope_label") or "").strip()
        if not work:
            continue
        normalized_work = _normalized_scope_text(work)
        if normalized_work and normalized_work in query:
            groups.append([work])

        author_values = summary.get("source_authors")
        if not isinstance(author_values, (list, tuple, set)):
            author_values = []
        for raw_author in author_values:
            author = str(raw_author or "").strip()
            if not author or not _mentions_scope_author(question, author):
                continue
            key = _normalized_scope_text(author)
            author_works.setdefault(key, set()).add(work)

    groups.extend(sorted(works) for works in author_works.values())

    distinct: list[list[str]] = []
    for group in groups:
        works = sorted({str(work).strip() for work in group if str(work).strip()})
        if not works:
            continue
        # A specifically named work already satisfies the broader author group
        # containing it; do not consume another reserved evidence slot.
        if any(set(existing) & set(works) for existing in distinct):
            continue
        distinct.append(works)
        if len(distinct) >= max(1, int(max_groups)):
            break
    return distinct


def _explicit_scope_work_groups(
    store: ChromaStore,
    collections: Sequence[Mapping[str, Any]],
    question: str,
) -> list[list[str]]:
    """Collect author/work targets from the searched corpus inventory."""

    work_summaries: dict[str, dict[str, Any]] = {}
    work_stats = getattr(store, "work_stats", None)
    if not callable(work_stats):
        return []
    for collection in collections:
        name = str(collection.get("name") or "")
        if not name:
            continue
        try:
            rows = work_stats(name)
        except Exception:
            logger.debug("Could not inspect work inventory for explicit Research scope", exc_info=True)
            continue
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            work = source_work_label(row)
            if not work:
                continue
            summary = work_summaries.setdefault(
                work,
                {"scope_label": work, "source_authors": set()},
            )
            author = source_author(row)
            if author:
                summary["source_authors"].add(author)

    normalized = [
        {
            "scope_label": item["scope_label"],
            "source_authors": sorted(item["source_authors"]),
        }
        for item in work_summaries.values()
    ]
    return _mentioned_work_groups(normalized, question)


def _scope_rag_candidates(
    rows: list[dict[str, Any]],
    collection: dict[str, Any],
    locale_codes: set[str],
) -> list[dict[str, Any]]:
    if collection.get("collection_role") == "language":
        return rows
    scoped: list[dict[str, Any]] = []
    for candidate in rows:
        record = candidate.get("record") or {}
        language_value = record.get("document_language")
        if language_value is None:
            language_value = record.get("document_languages")
        codes = ChromaStore._record_language_codes(language_value)
        # Records that declare no language cannot be excluded by a locale
        # filter; dropping them made small single-work corpora return nothing.
        if not codes or not locale_codes or codes & locale_codes:
            scoped.append(candidate)
    return scoped


def run_rag_pipeline(
    request: RAGRunRequest,
    store: ChromaStore,
    *,
    progress: Callable[[str, int, int, str], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
    owner: str | None = None,
    on_generation_delta: Callable[[str], None] | None = None,
    stop_after_context: bool = False,
    thread_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    stages: list[dict[str, Any]] = []
    warnings: list[str] = []
    thread_audit = copy.deepcopy(thread_audit)
    thread_context = advisory_context(thread_audit, request.prompt)

    if request.pipeline_id:
        pipeline = pipeline_manager.get_definition(
            request.pipeline_id,
            request.pipeline_version,
        )
        if pipeline is None:
            raise ValueError(
                f"Research pipeline {request.pipeline_id!r}"
                + (
                    f"@{request.pipeline_version}"
                    if request.pipeline_version is not None
                    else ""
                )
                + " was not found."
            )
    else:
        resolved = pipeline_manager.resolve("research")
        pipeline = PipelineDefinition.model_validate(resolved["pipeline"])
    config_resolution = resolve_pipeline_config(
        pipeline,
        settings_overrides=request.settings_pipeline_overrides,
        run_overrides=request.run_pipeline_overrides,
    )
    pipeline = config_resolution.effective
    pipeline_plan = compile_research_pipeline(pipeline)
    runtime_settings = resolve_research_runtime_settings(
        pipeline_plan,
        request.model_dump(mode="python"),
    )
    pipeline_summary = {
        "pipeline_id": pipeline.pipeline_id,
        "pipeline_version": pipeline.version,
        # The effective hash binds the trace to the configuration that actually
        # executed; the immutable Pipeline Studio baseline remains separately
        # identified for audit/reproduction.
        "pipeline_hash": config_resolution.effective_hash,
        "baseline_pipeline_hash": config_resolution.baseline_hash,
        "name": pipeline.name,
        "purpose": pipeline.purpose,
        "resolved_pipeline": pipeline.model_dump(mode="json"),
        "config_resolution": config_resolution.summary(),
    }

    def update(stage: str, current: int, total: int, detail: str = "") -> None:
        if progress:
            progress(stage, current, total, detail)

    def check_cancel() -> None:
        if cancelled and cancelled():
            raise InterruptedError("RAG job cancelled.")

    provider = request.provider
    model = (
        request.model
        or (
            settings.openai_compat_model
            if provider == "openai"
            else settings.ollama_model
        )
    )
    effective_query_decomposition = (
        (request.query_decomposition or bool(thread_context)) and pipeline_plan.query_decomposition_available
    )
    if not model and (effective_query_decomposition or not stop_after_context):
        raise ValueError("No generation model selected.")

    # Step 1-2: query metadata/decomposition, adapted from the supplied pipeline.
    stage_start = time.perf_counter()
    update("query_metadata", 0, 1, "Decomposing the research prompt")
    parsed_query: dict[str, Any] = {}
    if effective_query_decomposition:
        decomposition_prompt = (
            contextual_query_prompt(request.prompt, request.instructions or "", thread_context)
            if thread_context else QUERY_TEMPLATE.format(
                prompt=request.prompt, instructions=request.instructions or "",
            )
        )
        try:
            parsed_query = structured_chat_complete(
                provider=provider,
                model=model,
                base_url=request.base_url,
                api_key=request.api_key,
                prompt=decomposition_prompt,
                options=request.generation,
                max_tokens=runtime_settings.query_decomposition_num_predict,
                validate=validate_contextual_query if thread_context else None,
                attempts=2,
                cancelled=cancelled,
            )
        except InterruptedError:
            raise
        except Exception as exc:
            warnings.append(
                f"Query decomposition failed ({exc}); using the original prompt."
            )
            parsed_query = {}
    query_metadata: QueryDecomposition = {
        "prompt_query": str(
            parsed_query.get("prompt_query")
            or request.prompt
        ).strip(),
        "prompt_query_fr": str(
            parsed_query.get("prompt_query_fr")
            or request.prompt
        ).strip(),
        "prompt_instructions": str(
            (None if thread_context else parsed_query.get("prompt_instructions"))
            or request.instructions
            or ""
        ).strip(),
        # Retrieval/reranking limits are deterministic controls, not LLM
        # decisions. Pipeline Studio supplies the baseline; Settings and run
        # override layers have already been resolved into the effective pipeline.
        "limit_retrieval": int(request.k),
        "limit_reranking": int(request.rerank_top_n),
        "response_language": (
            request.response_language
            if request.response_language in {"en", "fr"}
            else str(parsed_query.get("response_language") or "en")
        ),
        "document_languages": [str(code) for code in request.locales],
    }
    if thread_audit is not None:
        thread_audit.update({
            "version": "research-thread-run-v2",
            "context_consumed": bool(thread_context) and not stop_after_context,
            "contextualization": {
                "contract": QUERY_CONTRACT,
                "attempted": bool(thread_context) and effective_query_decomposition,
                "fallback": bool(thread_context) and effective_query_decomposition and not bool(parsed_query),
                "provider": provider if thread_context and effective_query_decomposition else None,
                "model": model if thread_context and effective_query_decomposition else None,
                "original_question": request.prompt,
                "derived_query": query_metadata["prompt_query"],
                "derived_query_fr": query_metadata["prompt_query_fr"],
            },
        })
    stages.append({
        "name": "query_metadata",
        "seconds": time.perf_counter() - stage_start,
        "detail": query_metadata,
    })
    update("query_metadata", 1, 1, "Query decomposition complete")
    check_cancel()

    available_search_types = pipeline_plan.available_search_types
    effective_search_types = [
        search_type
        for search_type in request.search_types
        if search_type in available_search_types
    ]
    if not effective_search_types and not request.skip_retrieval:
        # The pipeline is the authoritative set of available retrieval stages.
        # A stale client may submit only a route the selected chain no longer
        # exposes, so fall back to the chain rather than silently retrieving zero.
        effective_search_types = [
            value
            for value in ("similarity", "lexical", "mmr")
            if value in available_search_types
        ]
    if not request.skip_retrieval and not effective_search_types:
        raise ValueError("The selected Research pipeline has no usable retrieval route.")

    filter_plan = request.filter_plan
    metadata_filter = filter_plan.metadata_filter if filter_plan else None
    document_filter = filter_plan.document_filter if filter_plan else None
    filter_detail = {
        "source": filter_plan.source if filter_plan else None,
        "metadata_filter": metadata_filter,
        "document_filter": document_filter,
        "metadata_fields": sorted(metadata_filter_fields(metadata_filter)),
    }

    selected_candidates = _selected_evidence_candidates(request, store)
    if request.skip_retrieval and not selected_candidates:
        raise ValueError("Selected-evidence-only RAG requires at least one selected evidence record.")
    if not request.skip_retrieval and not str(request.source_collection or "").strip():
        raise ValueError("Select a source collection when retrieval is enabled.")

    # Step 3: semantic + lexical + MMR retrieval. Selected-evidence-only runs bypass
    # vector retrieval completely; ordinary runs pin selected evidence alongside
    # retrieved candidates so user-curated context cannot be dropped by reranking.
    stage_start = time.perf_counter()
    collections = [] if request.skip_retrieval else _resolve_search_collections(
        store,
        request.source_collection,
        list(request.locales),
    )
    if not request.skip_retrieval and not collections:
        raise ValueError(
            "No selected language collection matches the requested locale scope."
        )

    requested_retrieve_k = max(1, int(request.k))
    semantic_fetch_k = max(requested_retrieve_k, runtime_settings.semantic_fetch_k)
    lexical_fetch_k = max(requested_retrieve_k, runtime_settings.lexical_fetch_k)
    effective_retrieve_k = requested_retrieve_k
    automatic_sizing_detail: dict[str, Any] = {
        "enabled": bool(request.automatic_sizing),
        "collections": [],
    }
    if request.automatic_sizing and collections:
        sizing_started = time.perf_counter()
        for collection in collections:
            try:
                stats = store.record_size_stats(collection["name"])
                sizing = automatic_collection_sizing(
                    count=max(0, int(collection.get("count") or 0)),
                    median_record_chars=stats.get("median_record_chars"),
                    requested_k=requested_retrieve_k,
                    semantic_fetch_k=runtime_settings.semantic_fetch_k,
                    lexical_fetch_k=runtime_settings.lexical_fetch_k,
                    mmr_limit=runtime_settings.retrieval_mmr_limit,
                )
                sizing["sample_count"] = int(stats.get("sample_count") or 0)
            except Exception as exc:
                sizing = automatic_collection_sizing(
                    count=max(0, int(collection.get("count") or 0)),
                    median_record_chars=None,
                    requested_k=requested_retrieve_k,
                    semantic_fetch_k=runtime_settings.semantic_fetch_k,
                    lexical_fetch_k=runtime_settings.lexical_fetch_k,
                    mmr_limit=runtime_settings.retrieval_mmr_limit,
                )
                sizing["sample_count"] = 0
                sizing["fallback_reason"] = type(exc).__name__
            collection["_rag_automatic_sizing"] = sizing
            automatic_sizing_detail["collections"].append({
                "collection": collection["name"],
                "route": collection.get("_rag_route"),
                **sizing,
            })
            effective_retrieve_k = max(effective_retrieve_k, int(sizing["k"]))
            semantic_fetch_k = max(semantic_fetch_k, int(sizing["semantic_fetch_k"]))
            lexical_fetch_k = max(lexical_fetch_k, int(sizing["lexical_fetch_k"]))
        stages.append({
            "name": "automatic_sizing",
            "seconds": time.perf_counter() - sizing_started,
            "detail": automatic_sizing_detail,
        })
        query_metadata["limit_retrieval"] = effective_retrieve_k

    raw_results: list[dict[str, Any]] = []
    total_units = len(collections) * max(1, len(effective_search_types))
    unit = 0

    if request.skip_retrieval:
        update("retrieval", 1, 1, f"Retrieval skipped · {len(selected_candidates)} selected evidence records")

    for collection in collections:
        sizing = (
            collection.get("_rag_automatic_sizing")
            if request.automatic_sizing
            else None
        )
        collection_retrieve_k = int((sizing or {}).get("k") or requested_retrieve_k)
        collection_semantic_fetch_k = int(
            (sizing or {}).get("semantic_fetch_k") or semantic_fetch_k
        )
        collection_lexical_fetch_k = int(
            (sizing or {}).get("lexical_fetch_k") or lexical_fetch_k
        )
        collection_mmr_limit = int(
            (sizing or {}).get("mmr_limit") or runtime_settings.retrieval_mmr_limit
        )
        check_cancel()
        locale_codes = set(collection.get("_rag_locales") or collection.get("language_codes") or [])
        query = (
            query_metadata["prompt_query_fr"]
            if "fr" in locale_codes and "en" not in locale_codes
            else query_metadata["prompt_query"]
        )

        semantic_candidates: list[dict[str, Any]] = []
        if {"similarity", "mmr"} & set(effective_search_types):
            try:
                semantic_kwargs: dict[str, Any] = {}
                if metadata_filter:
                    semantic_kwargs["where"] = metadata_filter
                if document_filter:
                    semantic_kwargs["where_document"] = document_filter
                semantic_candidates = _scope_rag_candidates(
                    store.semantic_candidates(
                        collection["name"],
                        query,
                        min(collection_semantic_fetch_k, max(1, collection["count"])),
                        **semantic_kwargs,
                    ),
                    collection,
                    locale_codes,
                )
            except ValueError as exc:
                # Precomputed-vector collections remain useful through the lexical
                # route even though they cannot embed a new query.
                if "lexical" not in effective_search_types:
                    raise
                update(
                    "retrieval",
                    unit,
                    total_units,
                    f"Semantic route unavailable for {collection['name']}: {exc}",
                )

        if "similarity" in effective_search_types:
            unit += 1
            update(
                "retrieval",
                unit,
                total_units,
                f"Similarity · {collection['name']} · {collection.get('_rag_route', '')}",
            )
            for rank, candidate in enumerate(
                semantic_candidates[:collection_retrieve_k],
                start=1,
            ):
                row = dict(candidate)
                row["search_type"] = "similarity"
                row["search_rank"] = rank
                raw_results.append(row)

        if "lexical" in effective_search_types:
            unit += 1
            update(
                "retrieval",
                unit,
                total_units,
                f"Lexical · {collection['name']} · {collection.get('_rag_route', '')}",
            )
            lexical_kwargs: dict[str, Any] = {}
            if metadata_filter:
                lexical_kwargs["where"] = metadata_filter
            if document_filter:
                lexical_kwargs["where_document"] = document_filter
            lexical_candidates = _scope_rag_candidates(
                store.lexical_search(
                    collection["name"],
                    query,
                    min(collection_lexical_fetch_k, max(1, collection["count"])),
                    **lexical_kwargs,
                ),
                collection,
                locale_codes,
            )
            for rank, candidate in enumerate(
                lexical_candidates[:collection_retrieve_k],
                start=1,
            ):
                row = dict(candidate)
                row["collection"] = collection["name"]
                row["search_type"] = "lexical"
                row["search_rank"] = rank
                raw_results.append(row)

        if "mmr" in effective_search_types:
            unit += 1
            update(
                "retrieval",
                unit,
                total_units,
                f"MMR · {collection['name']} · {collection.get('_rag_route', '')}",
            )
            mmr = _mmr_select(
                semantic_candidates,
                k=min(collection_retrieve_k, collection_mmr_limit),
                lambda_mult=runtime_settings.retrieval_mmr_lambda,
            )
            for rank, candidate in enumerate(mmr, start=1):
                row = dict(candidate)
                row["search_type"] = "mmr"
                row["search_rank"] = rank
                raw_results.append(row)

    # Explicitly named authors/works are corpus-scope constraints, not merely
    # generation instructions. Query decomposition may correctly move wording
    # such as "cite the named author" into prompt_instructions; if retrieval used only the
    # cleaned research question, that target could disappear before evidence
    # selection. Reserve one relevant Record for each named in-corpus scope.
    explicit_scope_text = "\n".join(
        value
        for value in (
            str(request.prompt or "").strip(),
            str(request.instructions or "").strip(),
        )
        if value
    )
    explicit_scope_groups = _explicit_scope_work_groups(
        store,
        collections,
        explicit_scope_text,
    )
    explicit_scope_seed_ids: set[str] = set()
    explicit_scope_seed_detail: list[dict[str, Any]] = []
    scoped_query = "\n".join(
        value
        for value in (
            query_metadata["prompt_query"],
            query_metadata["prompt_query_fr"],
            explicit_scope_text,
        )
        if value
    ).strip()

    for group_index, works in enumerate(explicit_scope_groups, start=1):
        existing = next(
            (
                item
                for item in raw_results
                if source_work_label(item.get("record") or {}) in works
            ),
            None,
        )
        seed = existing
        if seed is None:
            for collection in collections:
                try:
                    scope_metadata_filter = combine_metadata_filters(
                        metadata_filter,
                        {"work": {"$in": works}},
                    )
                    scope_kwargs: dict[str, Any] = {}
                    if scope_metadata_filter:
                        scope_kwargs["where"] = scope_metadata_filter
                    if document_filter:
                        scope_kwargs["where_document"] = document_filter
                    scoped_rows = _scope_rag_candidates(
                        store.lexical_search(
                            collection["name"],
                            scoped_query,
                            min(4, max(1, int(collection.get("count") or 1))),
                            **scope_kwargs,
                        ),
                        collection,
                        set(
                            collection.get("_rag_locales")
                            or collection.get("language_codes")
                            or []
                        ),
                    )
                except Exception:
                    logger.debug(
                        "Explicit Research scope retrieval failed for %s",
                        works,
                        exc_info=True,
                    )
                    continue
                if scoped_rows:
                    seed = dict(scoped_rows[0])
                    seed["collection"] = collection["name"]
                    seed["search_type"] = "explicit_scope"
                    seed["search_rank"] = 1
                    raw_results.append(seed)
                    break

        if seed is None:
            explicit_scope_seed_detail.append(
                {"works": works, "matched": False, "record_id": None}
            )
            continue
        record = seed.get("record") if isinstance(seed.get("record"), Mapping) else {}
        logical = str(record.get("record_id") or seed.get("id") or "")
        if not logical:
            continue
        explicit_scope_seed_ids.add(logical)
        explicit_scope_seed_detail.append(
            {
                "works": works,
                "matched": True,
                "record_id": logical,
                "scope_label": source_work_label(record),
                "source_document_author": semantic_value(record, SOURCE_AUTHOR_ID),
                "group": group_index,
            }
        )

    # Deduplicate by logical record ID, retaining a retrieval-rank fusion score.
    update("deduplicate", 0, 1, f"Fusing {len(raw_results)} retrieval hits")
    dedup: dict[str, dict[str, Any]] = {}
    for item in raw_results:
        record = item["record"]
        logical = str(
            record.get("record_id")
            or item.get("id")
        )
        rrf = 1.0 / (float(runtime_settings.rrf_k) + float(item.get("search_rank") or 1))
        if logical not in dedup:
            row = dict(item)
            row["rrf_score"] = rrf
            row["retrieval_hits"] = [{
                "collection": item.get("collection"),
                "search_type": item.get("search_type"),
                "rank": item.get("search_rank"),
            }]
            dedup[logical] = row
        else:
            dedup[logical]["rrf_score"] += rrf
            dedup[logical]["retrieval_hits"].append({
                "collection": item.get("collection"),
                "search_type": item.get("search_type"),
                "rank": item.get("search_rank"),
            })
            # Distances from cosine, L2, and inner-product collections are
            # not directly comparable. Prefer the best normalized relevance and
            # carry the distance/metric that produced it for traceability.
            old_relevance = dedup[logical].get("relevance")
            new_relevance = item.get("relevance")
            if new_relevance is not None and (
                old_relevance is None or float(new_relevance) > float(old_relevance)
            ):
                dedup[logical]["distance"] = item.get("distance")
                dedup[logical]["distance_metric"] = item.get("distance_metric")
                dedup[logical]["relevance"] = float(new_relevance)

    for logical in explicit_scope_seed_ids:
        if logical not in dedup:
            continue
        dedup[logical]["explicit_scope_seed"] = True
        dedup[logical]["selection_role"] = "explicit_scope_seed"

    for item in selected_candidates:
        record = item["record"]
        logical = str(record.get("record_id") or item.get("id"))
        # A selected source wins over the retrieved copy of the same logical
        # record and receives a deliberately dominant fusion score.
        item = dict(item)
        item["rrf_score"] = max(1.0, float((dedup.get(logical) or {}).get("rrf_score") or 0.0))
        dedup[logical] = item

    deduped = sorted(
        dedup.values(),
        key=lambda item: (
            item.get("rrf_score", 0.0),
            float(
                item.get("relevance")
                if item.get("relevance") is not None
                else _distance_similarity(item.get("distance"))
            ),
        ),
        reverse=True,
    )
    fused_deduplicated_count = len(deduped)
    ranking_candidates = deduped
    region_collapse_detail: dict[str, Any] = {
        "enabled": bool(request.automatic_sizing and not request.skip_retrieval),
        "input_count": len(deduped),
        "output_count": len(deduped),
        "collapsed_records": 0,
    }
    if request.automatic_sizing and not request.skip_retrieval:
        collapse_started = time.perf_counter()
        ranking_candidates, collapse_counts = collapse_adjacent_candidates(deduped)
        region_collapse_detail.update(collapse_counts)
        stages.append({
            "name": "automatic_region_collapse",
            "seconds": time.perf_counter() - collapse_started,
            "detail": region_collapse_detail,
        })

    pre_rerank_diagnostics = (
        _candidate_diagnostics(ranking_candidates) if stop_after_context else []
    )
    update("deduplicate", 1, 1, f"{len(deduped)} unique records after rank fusion")
    stages.append({
        "name": "retrieval",
        "seconds": time.perf_counter() - stage_start,
        "detail": {
            "collections": list(dict.fromkeys(
            [item["name"] for item in collections]
            + [str(item.get("collection")) for item in selected_candidates if item.get("collection")]
        )),
            "retrieval_skipped": bool(request.skip_retrieval),
            "selected_evidence_count": len(selected_candidates),
            "filter_plan": filter_detail,
            "routes": [
                {
                    "collection": item["name"],
                    "route": item.get("_rag_route"),
                    "languages": item.get("_rag_locales", []),
                }
                for item in collections
            ],
            "raw_results": len(raw_results),
            "deduplicated_results": len(deduped),
        },
    })
    check_cancel()

    # Step 4: rerank and follow only fallback edges declared by the pipeline.
    stage_start = time.perf_counter()

    requested_reranker = request.reranker
    if requested_reranker == "cross_encoder" and pipeline_plan.cross_encoder_available:
        effective_reranker = "cross_encoder"
    elif requested_reranker == "lexical" and pipeline_plan.lexical_rerank_available:
        effective_reranker = "lexical"
    elif (
        requested_reranker == "cross_encoder"
        and pipeline_plan.rerank_strategy == "rerank.lexical_fallback"
    ):
        effective_reranker = "lexical"
    else:
        effective_reranker = "none"

    update("rerank", 0, 1, effective_reranker)
    rerank_query = "\n".join(
        value
        for value in (
            query_metadata["prompt_query"],
            query_metadata["prompt_query_fr"],
            explicit_scope_text,
        )
        if value
    ).strip()
    requested_top_n = (
        len(ranking_candidates)
        if request.skip_retrieval
        else runtime_settings.rerank_top_n
    )
    selected_pool = [
        item for item in ranking_candidates if item.get("selected_evidence")
    ]
    scope_seed_pool = [
        item
        for item in ranking_candidates
        if item.get("explicit_scope_seed") and not item.get("selected_evidence")
    ]
    pinned_pool = selected_pool + scope_seed_pool
    retrieved_pool = [
        item
        for item in ranking_candidates
        if not item.get("selected_evidence") and not item.get("explicit_scope_seed")
    ]
    effective_top_n = (
        len(ranking_candidates)
        if request.skip_retrieval
        else min(
            max(requested_top_n, len(pinned_pool)),
            max(1, len(ranking_candidates)),
        )
    )
    remaining_slots = max(0, effective_top_n - len(pinned_pool))
    post_diversity = pipeline_plan.post_rerank_diversity
    rerank_pool_limit = min(
        len(retrieved_pool),
        max(
            remaining_slots,
            remaining_slots * 3 if post_diversity != "none" else remaining_slots,
        ),
    )
    diversity_slots = min(remaining_slots, runtime_settings.diversity_limit)

    rerank_telemetry: dict[str, Any] = {"mode": effective_reranker}
    active_rerank_stage_id: str | None = None
    fallback_condition: str | None = None
    cross_encoder_calls = 0

    if request.skip_retrieval:
        reranked = pinned_pool or ranking_candidates
        for item in reranked:
            item["rerank_score"] = item.get("rerank_score", 1.0)
        reranked_retrieved: list[dict[str, Any]] = []
        selected_ranked = list(reranked)
    else:
        selected_ranked = []
        for item in selected_pool:
            row = dict(item)
            row["rerank_score"] = max(
                1.0,
                float(item.get("rerank_score") or 0.0),
            )
            selected_ranked.append(row)
        for item in scope_seed_pool:
            row = dict(item)
            row["selection_role"] = "explicit_scope_seed"
            row["rerank_score"] = float(
                item.get("rerank_score")
                if item.get("rerank_score") is not None
                else item.get("rrf_score") or 0.0
            )
            selected_ranked.append(row)

        reranked_retrieved = []
        if rerank_pool_limit and retrieved_pool:
            if effective_reranker == "cross_encoder":
                active_rerank_stage_id = pipeline_plan.rerank_stage_id
                cross_encoder_calls += 1
                attempted, rerank_warning, rerank_telemetry = _cross_encoder_rerank(
                    rerank_query,
                    retrieved_pool,
                    rerank_pool_limit,
                    runtime_settings.cross_encoder_model,
                    timeout_seconds=(
                        runtime_settings.cross_encoder_timeout_seconds
                        if runtime_settings.cross_encoder_timeout_seconds is not None
                        else settings.ollama_timeout_seconds
                    ),
                )
                if attempted is not None:
                    reranked_retrieved = attempted
                else:
                    reason = str(
                        rerank_telemetry.get("fallback_reason") or "unavailable"
                    )
                    fallback_condition = classify_cross_encoder_failure(reason)
                    fallback = pipeline_plan.rerank_fallback(fallback_condition)
                    if fallback and fallback[1] == "rerank.lexical_fallback":
                        active_rerank_stage_id = fallback[0]
                        effective_reranker = "lexical"
                        reranked_retrieved = _lexical_rerank(
                            rerank_query,
                            retrieved_pool,
                            rerank_pool_limit,
                        )
                        rerank_telemetry = {
                            **rerank_telemetry,
                            "mode": "lexical_fallback",
                            "fallback_condition": fallback_condition,
                            "fallback_stage_id": fallback[0],
                        }
                        warnings.append(
                            f"Cross-encoder fallback ({reason}); followed "
                            f"{fallback_condition} edge to lexical/vector fallback."
                        )
                    elif fallback and fallback[1] == "select.top_k":
                        active_rerank_stage_id = fallback[0]
                        effective_reranker = "none"
                        fallback_limit = max(
                            1,
                            int(
                                pipeline_plan.config_value(
                                    fallback[0],
                                    "limit",
                                    rerank_pool_limit,
                                )
                            ),
                        )
                        reranked_retrieved = [
                            dict(item)
                            for item in retrieved_pool[
                                : min(rerank_pool_limit, fallback_limit)
                            ]
                        ]
                        for item in reranked_retrieved:
                            item["rerank_score"] = item.get("rrf_score", 0.0)
                        rerank_telemetry = {
                            **rerank_telemetry,
                            "mode": "top_k_fallback",
                            "fallback_condition": fallback_condition,
                            "fallback_stage_id": fallback[0],
                        }
                        warnings.append(
                            f"Cross-encoder fallback ({reason}); followed "
                            f"{fallback_condition} edge to deterministic top-K."
                        )
                    else:
                        effective_reranker = "none"
                        reranked_retrieved = [
                            dict(item) for item in retrieved_pool[:rerank_pool_limit]
                        ]
                        for item in reranked_retrieved:
                            item["rerank_score"] = item.get("rrf_score", 0.0)
                        rerank_telemetry = {
                            **rerank_telemetry,
                            "mode": "none",
                            "fallback_condition": fallback_condition,
                        }
                        if rerank_warning:
                            warnings.append(
                                rerank_warning
                                + f" No {fallback_condition} fallback edge is configured; "
                                "retained fused retrieval order."
                            )
            elif effective_reranker == "lexical":
                active_rerank_stage_id = pipeline_plan.lexical_rerank_stage_id
                reranked_retrieved = _lexical_rerank(
                    rerank_query,
                    retrieved_pool,
                    rerank_pool_limit,
                )
            else:
                reranked_retrieved = retrieved_pool[:rerank_pool_limit]
                for item in reranked_retrieved:
                    item["rerank_score"] = item.get("rrf_score", 0.0)

        if post_diversity == "none":
            reranked_retrieved = reranked_retrieved[:remaining_slots]
        reranked = selected_ranked + reranked_retrieved

    stages.append({
        "name": "rerank",
        "seconds": time.perf_counter() - stage_start,
        "detail": {
            "mode": effective_reranker,
            "requested_mode": requested_reranker,
            "requested_top_n": requested_top_n,
            "rerank_pool_count": len(reranked_retrieved),
            "selected_evidence_pinned": len(selected_pool),
            "explicit_scope_seeds_pinned": len(scope_seed_pool),
            "active_stage_id": active_rerank_stage_id,
            "fallback_condition": fallback_condition,
            "cross_encoder_calls": cross_encoder_calls,
            "cross_encoder_model": (
                runtime_settings.cross_encoder_model
                if requested_reranker == "cross_encoder"
                else None
            ),
            "reranker_telemetry": rerank_telemetry,
        },
    })
    post_rerank_diagnostics = (
        _candidate_diagnostics(reranked) if stop_after_context else []
    )
    update("rerank", 1, 1, f"{len(reranked)} records after relevance reranking")
    check_cancel()

    if (
        not request.skip_retrieval
        and post_diversity != "none"
        and diversity_slots
    ):
        diversity_started = time.perf_counter()
        if post_diversity == "source_aware":
            diversified = source_aware_select(
                reranked_retrieved,
                limit=diversity_slots,
                relevance=lambda item: float(
                    item.get("rerank_score")
                    if item.get("rerank_score") is not None
                    else item.get("rrf_score") or 0.0
                ),
            )
        else:
            ranked_for_diversity: list[dict[str, Any]] = []
            denominator = max(1, len(reranked_retrieved) - 1)
            for index, item in enumerate(reranked_retrieved):
                row = dict(item)
                row["_diversity_relevance"] = 1.0 - (index / denominator)
                ranked_for_diversity.append(row)
            diversified = mmr_select(
                ranked_for_diversity,
                limit=diversity_slots,
                lambda_mult=runtime_settings.diversity_lambda,
                relevance=lambda item: float(item.get("_diversity_relevance") or 0.0),
                vector=lambda item: item.get("embedding"),
            )
            for item in diversified:
                item.pop("_diversity_relevance", None)

        reranked = selected_ranked + diversified
        stages.append({
            "name": "diversity",
            "seconds": time.perf_counter() - diversity_started,
            "detail": {
                "mode": post_diversity,
                "stage_id": pipeline_plan.diversity_stage_id,
                "input_count": len(reranked_retrieved),
                "output_count": len(diversified),
                "selected_evidence_pinned": len(selected_pool),
                "explicit_scope_seeds_pinned": len(scope_seed_pool),
                "lambda_mult": (
                    runtime_settings.diversity_lambda
                    if post_diversity == "mmr"
                    else None
                ),
                "limit": diversity_slots,
            },
        })
        update(
            "diversity",
            1,
            1,
            f"{len(reranked)} records retained after {post_diversity} diversity",
        )
        check_cancel()

    # Step 5: build compact evidence context.
    post_selection_diagnostics = (
        _candidate_diagnostics(reranked) if stop_after_context else []
    )
    context_candidates = list(reranked)
    context_expansion_detail: dict[str, Any] = {
        "enabled": bool(request.automatic_sizing),
        "anchor_count": len(reranked),
        "neighbor_count": 0,
    }
    if request.automatic_sizing:
        expansion_started = time.perf_counter()
        context_candidates, expansion_counts = expand_context_neighbors(
            reranked,
            load_document_records=store.document_records,
            total_char_limit=runtime_settings.evidence_total_char_limit,
        )
        context_expansion_detail.update(expansion_counts)
        stages.append({
            "name": "automatic_context_expansion",
            "seconds": time.perf_counter() - expansion_started,
            "detail": context_expansion_detail,
        })

    stage_start = time.perf_counter()
    context_candidates, insufficient_records = partition_sufficient_records(
        context_candidates
    )
    if not request.automatic_sizing:
        # Preserve the historical manual-mode meaning of reranked_count: only
        # provenance-sufficient Records that can enter the evidence packet.
        reranked = context_candidates
    if insufficient_records:
        warnings.append(
            "Excluded provenance-incomplete records from evidence: "
            + "; ".join(
                f"{item['record_id']} missing {item['missing']}"
                for item in insufficient_records
            )
        )
    retrieval_context, works, evidence = _context_string(
        context_candidates,
        record_char_limit=runtime_settings.evidence_record_char_limit,
        total_char_limit=runtime_settings.evidence_total_char_limit,
        prompt_metadata=request.prompt_metadata,
        skip_overflow=request.automatic_sizing,
    )
    sufficiency_issues = evidence_sufficiency_issues(evidence)
    stages.append({
        "name": "retrieval_context",
        "seconds": time.perf_counter() - stage_start,
        "detail": {
            "evidence_count": len(evidence),
            "characters": len(retrieval_context),
            "sufficiency_issues": sufficiency_issues,
            "excluded_insufficient_records": insufficient_records,
        },
    })
    update("context", 1, 1, f"{len(evidence)} evidence records packaged")
    if not evidence and insufficient_records:
        detail = "; ".join(
            f"{item['record_id']} missing {item['missing']}"
            for item in insufficient_records
        )
        raise ValueError(
            "RAG evidence sufficiency failed: every retrieved record lacks required "
            f"provenance ({detail})."
        )
    if not evidence:
        raise ValueError("RAG evidence sufficiency failed: retrieval produced no evidence records.")
    if sufficiency_issues:
        detail = "; ".join(
            f"{item['evidence_id']} missing {item['missing']}"
            for item in sufficiency_issues
        )
        raise ValueError(f"RAG evidence sufficiency failed: {detail}")
    check_cancel()

    retrieval_summary = {
        "raw_count": len(raw_results),
        # Items in the searched collections (counts only), for scaling fits.
        "scope_size": sum(max(0, int(item.get("count") or 0)) for item in collections),
        "deduplicated_count": fused_deduplicated_count,
        "ranking_region_count": len(ranking_candidates),
        "reranked_count": len(reranked),
        "evidence_count": len(evidence),
        "search_types": list(effective_search_types),
        "requested_search_types": list(request.search_types),
        "available_search_types": sorted(available_search_types),
        "post_rerank_diversity": pipeline_plan.post_rerank_diversity,
        "k": request.k,
        "effective_k": effective_retrieve_k,
        "fetch_k": max(semantic_fetch_k, lexical_fetch_k),
        "requested_fetch_k": request.fetch_k,
        "automatic_sizing": automatic_sizing_detail,
        "automatic_region_collapse": region_collapse_detail,
        "automatic_context_expansion": context_expansion_detail,
        "semantic_fetch_k": semantic_fetch_k,
        "lexical_fetch_k": lexical_fetch_k,
        "lambda_mult": runtime_settings.retrieval_mmr_lambda,
        "retrieval_mmr_lambda": runtime_settings.retrieval_mmr_lambda,
        "diversity_lambda": runtime_settings.diversity_lambda,
        "rrf_k": runtime_settings.rrf_k,
        "reranker": effective_reranker,
        "requested_reranker": request.reranker,
        "rerank_top_n": runtime_settings.rerank_top_n,
        "effective_rerank_top_n": len(reranked),
        "query_decomposition": effective_query_decomposition,
        "query_transform_model_calls": 1 if effective_query_decomposition else 0,
        "cross_encoder_calls": cross_encoder_calls,
        "requested_query_decomposition": request.query_decomposition,
        "query_decomposition_num_predict": runtime_settings.query_decomposition_num_predict,
        "skip_retrieval": request.skip_retrieval,
        "selected_evidence_count": len(selected_candidates),
        "filter_plan": filter_detail,
        "explicit_scope_groups": explicit_scope_seed_detail,
        "explicit_scope_seed_count": len(explicit_scope_seed_ids),
        "response_language": request.response_language,
        "evidence_record_char_limit": runtime_settings.evidence_record_char_limit,
        "evidence_total_char_limit": runtime_settings.evidence_total_char_limit,
        "evidence_sufficiency": {"passed": True, "issues": []},
    }

    if stop_after_context:
        return {
            "prompt": request.prompt,
            "research_thread": thread_audit,
            "prompt_contract": GENERATION_CONTRACT,
            "query_contract": QUERY_CONTRACT,
            "query_metadata": query_metadata,
            "answer": "",
            "raw_answer": "",
            "evidence": evidence,
            "works": works,
            "collections": [item["name"] for item in collections],
            "warnings": warnings,
            "stages": stages,
            "provider": provider,
            "model": model,
            "pipeline": pipeline_summary,
            "elapsed_seconds": time.perf_counter() - started,
            "retrieval": retrieval_summary,
            "diagnostics": {
                "candidate_retention": "complete_for_comparison",
                "pre_rerank": pre_rerank_diagnostics,
                "post_rerank": post_rerank_diagnostics,
                "post_selection": post_selection_diagnostics,
                "context_characters": len(retrieval_context),
            },
            "memory": {
                "mode": "skipped_for_non_persistent_dry_run",
                "warnings": [],
            },
            "dry_run": True,
        }

    # Advisory memory is chosen after the evidence packet exists so validated-claim
    # support can be checked against the Records this answer may actually cite.
    excluded_thread_response_ids: list[str] = []
    if thread_audit:
        excluded_thread_response_ids = [
            str(item["response_id"])
            for item in (thread_audit.get("context_selection") or {}).get("items", [])
            if item.get("role") == "assistant" and item.get("response_id")
        ]
    prior_response_memory, prior_claim_memory, memory_detail = memory_guidance(
        query_metadata["prompt_query"],
        use_responses=request.use_prior_response_memory,
        use_claims=request.use_prior_claim_memory,
        owner=owner,
        evidence=evidence,
        system_store=system_store,
        response_index_factory=lambda: ResponseMemoryIndex(store),
        claim_index_factory=lambda: ClaimMemoryIndex(store),
        excluded_response_ids=excluded_thread_response_ids,
    )
    warnings.extend(memory_detail["warnings"])

    # Step 6: generate answer.
    stage_start = time.perf_counter()
    update("generation", 0, 1, f"Invoking {provider} · {model}")
    generation_prompt = (THREAD_FOCUSED_PROMPT if thread_context else FOCUSED_PROMPT).format(
        prompt_query=request.prompt,
        thread_context=thread_context or "(none selected)",
        prompt_instructions=query_metadata["prompt_instructions"],
        response_language=("French" if query_metadata.get("response_language") == "fr" else "English"),
        prior_response_memory=prior_response_memory or "(none selected)",
        prior_claim_memory=prior_claim_memory or "(none selected)",
        context=retrieval_context,
    )
    raw_answer = chat_complete(
        provider=provider,
        model=model,
        base_url=request.base_url,
        api_key=request.api_key,
        prompt=generation_prompt,
        options=request.generation,
        json_mode=False,
        max_tokens=(
            request.generation.num_predict
            if request.generation and request.generation.num_predict
            else 8192
        ),
        cancelled=cancelled,
        on_delta=on_generation_delta,
    )
    stages.append({
        "name": "generation",
        "seconds": time.perf_counter() - stage_start,
        "detail": {
            "provider": provider,
            "model": model,
            "characters": len(raw_answer),
        },
    })
    update("generation", 1, 1, "Draft generated")
    check_cancel()

    # Step 7: bind evidence IDs to bibliographic citations.
    stage_start = time.perf_counter()
    answer = (
        _bind_sources(
            raw_answer,
            evidence,
            request.include_works_cited,
        )
        if request.bind_citations
        else _STRAY_MEMORY_TAG_PATTERN.sub("", raw_answer)
    )
    stages.append({
        "name": "bind_sources",
        "seconds": time.perf_counter() - stage_start,
        "detail": {
            "bound": request.bind_citations,
            "works": works,
        },
    })
    update("bind_sources", 1, 1, "Citations bound")

    return {
        "prompt": request.prompt,
        "research_thread": thread_audit,
        "prompt_contract": GENERATION_CONTRACT,
        "query_contract": QUERY_CONTRACT,
        "query_metadata": query_metadata,
        "answer": answer,
        "raw_answer": raw_answer,
        "evidence": evidence,
        "works": works,
        "collections": [item["name"] for item in collections],
        "warnings": warnings,
        "stages": stages,
        "provider": provider,
        "model": model,
        "pipeline": pipeline_summary,
        "elapsed_seconds": time.perf_counter() - started,
        "retrieval": retrieval_summary,
        "memory": memory_detail,
    }
