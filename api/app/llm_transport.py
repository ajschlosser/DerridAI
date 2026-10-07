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

"""Provider transport and structured-completion boundary shared by Research and Corpus Builder.

This module deliberately has no vector-store or Research-memory imports. Keeping the
transport boundary small lets the native corpus CLI call the same provider logic
without pulling Chroma or reranking dependencies into its binary.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from typing import Any

import httpx

from .config import settings
from .llm_failures import ProviderRequestError
from .models import OllamaTouchupOptions
from .structured_completion import StructuredAttemptContext, complete_structured_json
from .structured_json import StructuredJsonTruncatedError, finish_reason_is_truncated

logger = logging.getLogger(__name__)


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
        # Provider-specific extras may tune generation, but they must not override
        # transport-owned request shape or force structured output onto prose tasks.
        reserved_extra_options = {"model", "messages", "response_format", "stream"}
        for key_name, value in (tuning.extra_options or {}).items():
            if key_name not in reserved_extra_options:
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
    # Ollama structured-output format is transport-owned; do not allow raw
    # profile options to smuggle request-shape controls into generation settings.
    option_values: dict[str, Any] = {
        key: value
        for key, value in (tuning.extra_options or {}).items()
        if key not in {"format", "model", "messages", "stream"}
    }
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
