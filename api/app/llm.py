# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Callable

import httpx

from .config import settings
from .models import OllamaTouchupOptions

logger = logging.getLogger(__name__)

ARRAY_FIELDS = {
    "semantic_function",
    "topics",
    "concepts",
    "persons",
    "works_referenced",
    "document_language",
    "original_language",
    "quoted_speaker",
    "quoted_author",
    "quoted_work",
    "quoted_position_holder",
    "quoted_addressee",
    "quoted_referent",
    "quotation_chain",
}
BOOLEAN_FIELDS = {
    "primary_text",
    "is_direct_quote",
    "needs_review",
    "document_is_translation",
}
NUMBER_FIELDS = {
    "year",
    "page_start",
    "page_end",
    "attribution_confidence",
    "semantic_classification_confidence",
    "extraction_quality",
    "text_length",
}
STRING_FIELDS = {
    "record_id",
    "work",
    "document_author",
    "edition",
    "region_type",
    "region_author",
    "canonical_work_id",
    "speaker",
    "position_holder",
    "target",
    "discourse_role",
    "proposition_status",
    "stance",
    "claim_scope",
    "review_reason",
    "translator",
    "inline_citation",
    "full_citation",
    "text",
}

SYSTEM_PROMPT = r"""
You are a conservative scholarly record auditor for a Derrida research corpus.
Your task is to PROPOSE corrections, never to silently rewrite a record.

Return exactly one JSON object and no markdown.

Rules:
1. Change only fields listed in requested_fields.
2. Omit a field from changes when the current value is defensible or evidence is insufficient.
3. Never invent bibliographic facts, speakers, sources, positions, or citations.
4. Ground attribution proposals in the supplied record text and local metadata.
5. Keep distinct relations distinct. In particular, do not collapse these into quoted_speaker:
   quoted_author, quoted_work, quoted_position_holder, quoted_addressee,
   quoted_referent, quotation_chain.
6. For text: do not paraphrase, summarize, modernize, or improve style. Only repair
   high-confidence OCR/transcription defects such as broken ligatures, obvious scanning
   artifacts, clearly broken word joins, or unmistakable punctuation/spacing corruption.
7. Preserve semantic modality, negation, uncertainty, and quotation boundaries.
8. Preserve field data types. Arrays remain arrays, booleans remain booleans, numbers
   remain numbers, and null remains null unless evidence supports a replacement.
9. If a proposed attribution or quotation boundary is uncertain, make no change and add
   a warning describing the uncertainty.
10. Keep rationales short and evidence-focused.
11. Do not repeat unchanged values or restate the record.
12. For metadata review, keep the entire response concise; one short rationale sentence
    per changed field is enough.
13. If no change is warranted, return empty changes/rationale objects and warnings only
    when there is a genuine uncertainty worth flagging.

Required JSON shape:
{
  "changes": {"field": proposed_value},
  "rationale": {"field": "brief reason"},
  "warnings": ["warning if needed"]
}
""".strip()


@dataclass
class TouchupFailure(Exception):
    status_code: int
    message: str
    diagnostic: str | None = None

    def __str__(self) -> str:
        return self.message


def _extract_json(text: str) -> dict[str, Any]:
    value = text.strip()
    if not value:
        raise TouchupFailure(502, "The LLM returned an empty response.")

    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.I)
        value = re.sub(r"\s*```$", "", value)

    candidates = [value]
    start = value.find("{")
    end = value.rfind("}")
    if start >= 0 and end > start:
        candidates.append(value[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    raise TouchupFailure(
        502,
        "The model response was not valid JSON.",
        diagnostic=value[:2000],
    )


def _field_type_ok(field: str, current: Any, proposed: Any) -> bool:
    if field in ARRAY_FIELDS:
        return proposed is None or isinstance(proposed, list)
    if field in BOOLEAN_FIELDS:
        return proposed is None or isinstance(proposed, bool)
    if field in NUMBER_FIELDS:
        return proposed is None or (
            isinstance(proposed, (int, float))
            and not isinstance(proposed, bool)
        )
    if field in STRING_FIELDS:
        return proposed is None or isinstance(proposed, str)

    if current is None:
        return True
    if isinstance(current, bool):
        return proposed is None or isinstance(proposed, bool)
    if isinstance(current, list):
        return proposed is None or isinstance(proposed, list)
    if isinstance(current, dict):
        return proposed is None or isinstance(proposed, dict)
    if isinstance(current, (int, float)) and not isinstance(current, bool):
        return proposed is None or (
            isinstance(proposed, (int, float))
            and not isinstance(proposed, bool)
        )
    if isinstance(current, str):
        return proposed is None or isinstance(proposed, str)
    return True


def _compact_record_context(
    record: dict[str, Any],
    requested_fields: list[str],
) -> dict[str, Any]:
    evidence_fields = [
        "record_id",
        "work",
        "document_author",
        "edition",
        "year",
        "page_start",
        "page_end",
        "region_type",
        "region_author",
        "primary_text",
        "speaker",
        "position_holder",
        "target",
        "discourse_role",
        "proposition_status",
        "semantic_function",
        "stance",
        "claim_scope",
        "text",
        "topics",
        "concepts",
        "persons",
        "works_referenced",
        "is_direct_quote",
        "quoted_speaker",
        "quoted_author",
        "quoted_work",
        "quoted_position_holder",
        "quoted_addressee",
        "quoted_referent",
        "quotation_chain",
        "inline_citation",
        "full_citation",
        "needs_review",
        "review_reason",
    ]
    keys: list[str] = []
    for key in [*requested_fields, *evidence_fields]:
        if key not in keys and key in record:
            keys.append(key)

    context = {key: record[key] for key in keys}
    text = context.get("text")
    if isinstance(text, str) and len(text) > settings.llm_max_text_chars:
        context["text"] = text[: settings.llm_max_text_chars]
        context["_text_truncated"] = True
        context["_original_text_length"] = len(text)
    return context


def _common_status(
    *,
    provider: str,
    base_url: str,
    configured_model: str,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "available": False,
        "base_url": base_url,
        "configured_model": configured_model,
        "models": [],
        "error": None,
        "limits": {
            "max_fields": settings.llm_max_fields,
            "metadata_num_predict": settings.llm_metadata_num_predict,
            "text_num_predict": settings.llm_text_num_predict,
        },
        "defaults": {
            "think": False,
            "temperature": 0.0,
            "metadata_num_predict": settings.llm_metadata_num_predict,
            "text_num_predict": settings.llm_text_num_predict,
            "keep_alive": settings.ollama_keep_alive,
        },
    }


def ollama_status(
    base_url: str | None = None,
) -> dict[str, Any]:
    url = (base_url or settings.ollama_base_url).rstrip("/")
    result = _common_status(
        provider="ollama",
        base_url=url,
        configured_model=settings.ollama_model,
    )
    try:
        with httpx.Client(
            timeout=settings.ollama_status_timeout_seconds
        ) as client:
            response = client.get(f"{url}/api/tags")
            response.raise_for_status()
            payload = response.json()
    except httpx.ConnectError:
        result["error"] = "Could not connect to Ollama."
        return result
    except httpx.TimeoutException:
        result["error"] = "Ollama did not respond before the status timeout."
        return result
    except httpx.HTTPStatusError as exc:
        result["error"] = f"Ollama returned HTTP {exc.response.status_code}."
        return result
    except Exception as exc:
        logger.exception("Unexpected Ollama status error")
        result["error"] = str(exc)
        return result

    models = []
    for item in payload.get("models") or []:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("model")
        if not name:
            continue
        details = item.get("details") or {}
        models.append({
            "name": str(name),
            "size": item.get("size"),
            "parameter_size": details.get("parameter_size"),
            "quantization_level": details.get("quantization_level"),
            "family": details.get("family"),
        })

    result["available"] = True
    result["models"] = models
    return result


def openai_compat_status(
    *,
    base_url: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    url = (base_url or settings.openai_compat_base_url).rstrip("/")
    key = api_key if api_key is not None else settings.openai_compat_api_key
    result = _common_status(
        provider="openai",
        base_url=url,
        configured_model=settings.openai_compat_model,
    )
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        with httpx.Client(
            timeout=settings.ollama_status_timeout_seconds
        ) as client:
            response = client.get(f"{url}/models", headers=headers)
            response.raise_for_status()
            payload = response.json()
    except httpx.ConnectError:
        result["error"] = "Could not connect to the OpenAI-compatible endpoint."
        return result
    except httpx.TimeoutException:
        result["error"] = "The OpenAI-compatible endpoint did not respond before the status timeout."
        return result
    except httpx.HTTPStatusError as exc:
        result["error"] = (
            f"OpenAI-compatible endpoint returned HTTP "
            f"{exc.response.status_code}."
        )
        return result
    except Exception as exc:
        logger.exception("Unexpected OpenAI-compatible status error")
        result["error"] = str(exc)
        return result

    models: list[dict[str, Any]] = []
    data = payload.get("data") if isinstance(payload, dict) else None
    for item in data or []:
        if not isinstance(item, dict):
            continue
        name = item.get("id")
        if name:
            models.append({"name": str(name)})

    result["available"] = True
    result["models"] = models
    return result


def llm_status(
    provider: str = "ollama",
    *,
    base_url: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    if provider == "openai":
        return openai_compat_status(base_url=base_url, api_key=api_key)
    return ollama_status(base_url=base_url)


def _parse_proposal(
    *,
    content: str,
    record: dict[str, Any],
    field_list: list[str],
    selected_model: str,
    provider: str,
    context: dict[str, Any],
    effective_options: dict[str, Any],
) -> dict[str, Any]:
    parsed = _extract_json(content)

    changes = parsed.get("changes") or {}
    rationale = parsed.get("rationale") or {}
    warnings = parsed.get("warnings") or []

    if not isinstance(changes, dict):
        raise TouchupFailure(502, "Model field 'changes' was not a JSON object.")
    if not isinstance(rationale, dict):
        rationale = {}
    if not isinstance(warnings, list):
        warnings = [str(warnings)]

    allowed = set(field_list)
    cleaned_changes: dict[str, Any] = {}
    cleaned_rationale: dict[str, str] = {}
    type_warnings: list[str] = []

    for field, proposed in changes.items():
        if field not in allowed:
            continue
        current = record.get(field)
        if not _field_type_ok(field, current, proposed):
            type_warnings.append(
                f"Ignored '{field}' because the model returned an incompatible data type."
            )
            continue
        if proposed == current:
            continue
        cleaned_changes[field] = proposed
        if field in rationale:
            cleaned_rationale[field] = str(rationale[field])

    return {
        "changes": cleaned_changes,
        "rationale": cleaned_rationale,
        "warnings": [str(item) for item in warnings] + type_warnings,
        "model": selected_model,
        "provider": provider,
        "record_id": record.get("record_id"),
        "context_truncated": bool(context.get("_text_truncated")),
        "effective_options": effective_options,
    }


def propose_touchup(
    record: dict[str, Any],
    fields: list[str],
    instructions: str | None,
    model: str | None,
    ollama: OllamaTouchupOptions | None = None,
    *,
    provider: str = "ollama",
    base_url: str | None = None,
    api_key: str | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    field_list = list(
        dict.fromkeys(
            str(field).strip()
            for field in fields
            if str(field).strip()
        )
    )
    if not field_list:
        raise TouchupFailure(422, "Select at least one field for LLM review.")
    if len(field_list) > settings.llm_max_fields:
        raise TouchupFailure(
            422,
            f"Select at most {settings.llm_max_fields} fields per LLM review.",
        )
    if "updates" in field_list:
        raise TouchupFailure(
            422,
            "The updates audit history is read-only for LLM review.",
        )
    if "text" in field_list and len(field_list) > 1:
        raise TouchupFailure(
            422,
            "Text touch-up must run separately from metadata touch-up.",
        )

    provider = (provider or "ollama").strip().lower()
    if provider not in {"ollama", "openai"}:
        raise TouchupFailure(422, f"Unsupported LLM provider: {provider}")

    default_model = (
        settings.openai_compat_model
        if provider == "openai"
        else settings.ollama_model
    )
    selected_model = (model or default_model).strip()
    if not selected_model:
        raise TouchupFailure(
            422,
            f"No model was selected for provider '{provider}'.",
        )

    context = _compact_record_context(record, field_list)
    user_prompt = {
        "requested_fields": field_list,
        "current_values": {
            field: record.get(field)
            for field in field_list
        },
        "record_context": context,
        "additional_instructions": (instructions or "").strip(),
    }
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(
                user_prompt,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        },
    ]

    tuning = ollama or OllamaTouchupOptions()
    requested_num_predict = tuning.num_predict
    if requested_num_predict is None:
        requested_num_predict = (
            settings.llm_text_num_predict
            if "text" in field_list
            else settings.llm_metadata_num_predict
        )
    temperature = (
        0.0
        if tuning.temperature is None
        else tuning.temperature
    )

    if provider == "openai":
        return _propose_openai(
            record=record,
            field_list=field_list,
            context=context,
            messages=messages,
            selected_model=selected_model,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            max_tokens=requested_num_predict,
            tuning=tuning,
            cancelled=cancelled,
        )

    return _propose_ollama(
        record=record,
        field_list=field_list,
        context=context,
        messages=messages,
        selected_model=selected_model,
        base_url=base_url,
        temperature=temperature,
        num_predict=requested_num_predict,
        tuning=tuning,
        cancelled=cancelled,
    )


def _propose_ollama(
    *,
    record: dict[str, Any],
    field_list: list[str],
    context: dict[str, Any],
    messages: list[dict[str, str]],
    selected_model: str,
    base_url: str | None,
    temperature: float,
    num_predict: int,
    tuning: OllamaTouchupOptions,
    cancelled: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    url = (base_url or settings.ollama_base_url).rstrip("/")
    option_values: dict[str, Any] = dict(tuning.extra_options or {})
    explicit_options = {
        "num_ctx": tuning.num_ctx,
        "num_predict": num_predict,
        "temperature": temperature,
        "top_k": tuning.top_k,
        "top_p": tuning.top_p,
        "min_p": tuning.min_p,
        "repeat_penalty": tuning.repeat_penalty,
        "seed": tuning.seed,
        "mirostat": tuning.mirostat,
        "mirostat_eta": tuning.mirostat_eta,
        "mirostat_tau": tuning.mirostat_tau,
        "stop": tuning.stop,
    }
    for key, value in explicit_options.items():
        if value is not None:
            option_values[key] = value

    request_body: dict[str, Any] = {
        "model": selected_model,
        "stream": False,
        "format": "json",
        "messages": messages,
        "options": option_values,
    }
    if tuning.think is not None:
        request_body["think"] = tuning.think

    keep_alive = (
        tuning.keep_alive
        if tuning.keep_alive is not None
        else settings.ollama_keep_alive
    )
    if keep_alive:
        request_body["keep_alive"] = keep_alive

    timeout = httpx.Timeout(
        connect=settings.ollama_connect_timeout_seconds,
        read=settings.ollama_timeout_seconds,
        write=settings.ollama_timeout_seconds,
        pool=settings.ollama_connect_timeout_seconds,
    )
    content = ""
    try:
        if cancelled is not None:
            request_body["stream"] = True
            chunks: list[str] = []
            with httpx.Client(timeout=timeout) as client:
                with client.stream("POST", f"{url}/api/chat", json=request_body) as response:
                    if response.status_code >= 400:
                        response.read()
                        detail = _response_detail(response)
                        message = f"Ollama returned HTTP {response.status_code}."
                        if detail:
                            message += f" {detail}"
                        if response.status_code == 404:
                            message += " Check that the selected model is installed."
                        raise TouchupFailure(502, message)
                    for line in response.iter_lines():
                        if cancelled():
                            raise InterruptedError("LLM review cancelled.")
                        if not line:
                            continue
                        try:
                            payload = json.loads(line)
                        except json.JSONDecodeError as exc:
                            raise TouchupFailure(
                                502,
                                "Ollama returned an invalid streaming response.",
                                line[:1500],
                            ) from exc
                        piece = ((payload.get("message") or {}).get("content") or "")
                        if piece:
                            chunks.append(str(piece))
                        if payload.get("done"):
                            break
            content = "".join(chunks).strip()
        else:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(f"{url}/api/chat", json=request_body)
            if response.status_code >= 400:
                detail = _response_detail(response)
                message = f"Ollama returned HTTP {response.status_code}."
                if detail:
                    message += f" {detail}"
                if response.status_code == 404:
                    message += " Check that the selected model is installed."
                raise TouchupFailure(502, message)
            try:
                payload = response.json()
            except json.JSONDecodeError as exc:
                raise TouchupFailure(
                    502,
                    "Ollama returned a non-JSON API response.",
                    response.text[:1500],
                ) from exc
            content = ((payload.get("message") or {}).get("content") or "").strip()
    except InterruptedError:
        raise
    except TouchupFailure:
        raise
    except httpx.ConnectError as exc:
        raise TouchupFailure(
            503,
            f"Cannot connect to Ollama at {url}.",
            "Check the Ollama endpoint and confirm it is reachable from the API container.",
        ) from exc
    except httpx.TimeoutException as exc:
        raise TouchupFailure(
            504,
            f"Ollama did not finish within {settings.ollama_timeout_seconds:g} seconds.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected network failure while calling Ollama")
        raise TouchupFailure(
            502,
            "Unexpected error while contacting Ollama.",
            str(exc),
        ) from exc

    return _parse_proposal(
        content=content,
        record=record,
        field_list=field_list,
        selected_model=selected_model,
        provider="ollama",
        context=context,
        effective_options={
            "base_url": url,
            "think": request_body.get("think"),
            "keep_alive": request_body.get("keep_alive"),
            **option_values,
        },
    )


def _propose_openai(
    *,
    record: dict[str, Any],
    field_list: list[str],
    context: dict[str, Any],
    messages: list[dict[str, str]],
    selected_model: str,
    base_url: str | None,
    api_key: str | None,
    temperature: float,
    max_tokens: int,
    tuning: OllamaTouchupOptions,
    cancelled: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    url = (base_url or settings.openai_compat_base_url).rstrip("/")
    key = api_key if api_key is not None else settings.openai_compat_api_key
    headers = {
        "Content-Type": "application/json",
    }
    if key:
        headers["Authorization"] = f"Bearer {key}"

    body: dict[str, Any] = {
        "model": selected_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    extra = dict(tuning.extra_options or {})
    for unsupported in {
        "num_ctx",
        "num_predict",
        "keep_alive",
        "think",
    }:
        extra.pop(unsupported, None)

    if tuning.seed is not None:
        body["seed"] = tuning.seed
    if tuning.top_p is not None:
        body["top_p"] = tuning.top_p
    if tuning.stop:
        body["stop"] = tuning.stop
    body.update(extra)

    timeout = httpx.Timeout(
        connect=settings.openai_connect_timeout_seconds,
        read=settings.openai_timeout_seconds,
        write=settings.openai_timeout_seconds,
        pool=settings.openai_connect_timeout_seconds,
    )

    def stream_request(payload: dict[str, Any]) -> tuple[int, str, str]:
        streaming = dict(payload)
        streaming["stream"] = True
        chunks: list[str] = []
        with httpx.Client(timeout=timeout) as client:
            with client.stream(
                "POST",
                f"{url}/chat/completions",
                headers=headers,
                json=streaming,
            ) as response:
                if response.status_code >= 400:
                    raw = response.read().decode("utf-8", errors="replace")
                    return response.status_code, "", raw[:2000]
                for line in response.iter_lines():
                    if cancelled and cancelled():
                        raise InterruptedError("LLM review cancelled.")
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
                    delta = choices[0].get("delta") if choices else {}
                    piece = (delta or {}).get("content") or ""
                    if isinstance(piece, list):
                        piece = "".join(
                            str(item.get("text") or "")
                            for item in piece
                            if isinstance(item, dict)
                        )
                    if piece:
                        chunks.append(str(piece))
        return 200, "".join(chunks).strip(), ""

    try:
        if cancelled is not None:
            status_code, content, detail = stream_request(body)
            if status_code == 400 and "response_format" in body:
                fallback = dict(body)
                fallback.pop("response_format", None)
                status_code, content, detail = stream_request(fallback)
                body = fallback
            if status_code in {400, 422}:
                # Some OpenAI-compatible local routers implement Chat Completions
                # but not SSE streaming. Fall back to a normal request so those
                # endpoints remain usable; cancellation then completes at the
                # next safe checkpoint instead of interrupting mid-request.
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
                    message_payload = choices[0].get("message") if choices else {}
                    content = (message_payload or {}).get("content") or ""
                    if isinstance(content, list):
                        content = "".join(
                            str(item.get("text") or "")
                            for item in content
                            if isinstance(item, dict)
                        )
                    if cancelled and cancelled():
                        raise InterruptedError("LLM review cancelled.")
                    status_code = 200
            if status_code >= 400:
                message = f"OpenAI-compatible endpoint returned HTTP {status_code}."
                if detail:
                    message += f" {detail}"
                raise TouchupFailure(502, message)
        else:
            def do_request(payload: dict[str, Any]) -> httpx.Response:
                with httpx.Client(timeout=timeout) as client:
                    return client.post(
                        f"{url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
            response = do_request(body)
            if response.status_code == 400 and "response_format" in body:
                fallback = dict(body)
                fallback.pop("response_format", None)
                response = do_request(fallback)
                body = fallback
            if response.status_code >= 400:
                detail = _response_detail(response)
                message = f"OpenAI-compatible endpoint returned HTTP {response.status_code}."
                if detail:
                    message += f" {detail}"
                raise TouchupFailure(502, message)
            try:
                payload = response.json()
            except json.JSONDecodeError as exc:
                raise TouchupFailure(
                    502,
                    "OpenAI-compatible endpoint returned a non-JSON API response.",
                    response.text[:1500],
                ) from exc
            choices = payload.get("choices") or []
            message = choices[0].get("message") if choices else {}
            content = (message or {}).get("content") or ""
            if isinstance(content, list):
                content = "".join(
                    str(item.get("text") or "")
                    for item in content
                    if isinstance(item, dict)
                )
            content = str(content).strip()
    except InterruptedError:
        raise
    except TouchupFailure:
        raise
    except httpx.ConnectError as exc:
        raise TouchupFailure(
            503,
            f"Cannot connect to OpenAI-compatible endpoint at {url}.",
        ) from exc
    except httpx.TimeoutException as exc:
        raise TouchupFailure(
            504,
            f"OpenAI-compatible endpoint did not finish within "
            f"{settings.openai_timeout_seconds:g} seconds.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected network failure while calling OpenAI-compatible endpoint")
        raise TouchupFailure(
            502,
            "Unexpected error while contacting OpenAI-compatible endpoint.",
            str(exc),
        ) from exc

    return _parse_proposal(
        content=str(content).strip(),
        record=record,
        field_list=field_list,
        selected_model=selected_model,
        provider="openai",
        context=context,
        effective_options={
            "base_url": url,
            "temperature": body.get("temperature"),
            "max_tokens": body.get("max_tokens"),
            "top_p": body.get("top_p"),
            "seed": body.get("seed"),
        },
    )



def warmup_model(
    *,
    provider: str = "ollama",
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    num_ctx: int | None = None,
) -> dict[str, Any]:
    provider = (provider or "ollama").strip().lower()
    selected_model = (
        model
        or (
            settings.openai_compat_model
            if provider == "openai"
            else settings.ollama_model
        )
    ).strip()
    if not selected_model:
        raise TouchupFailure(422, "No model was selected for warmup.")

    if provider == "openai":
        url = (base_url or settings.openai_compat_base_url).rstrip("/")
        key = api_key if api_key is not None else settings.openai_compat_api_key
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        body = {
            "model": selected_model,
            "messages": [{"role": "user", "content": "Reply only: OK"}],
            "temperature": 0,
            "max_tokens": 1,
        }
        timeout = httpx.Timeout(
            connect=settings.openai_connect_timeout_seconds,
            read=min(settings.openai_timeout_seconds, 60.0),
            write=60.0,
            pool=settings.openai_connect_timeout_seconds,
        )
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    f"{url}/chat/completions",
                    headers=headers,
                    json=body,
                )
            response.raise_for_status()
        except Exception as exc:
            raise TouchupFailure(
                502,
                "OpenAI-compatible warmup request failed.",
                str(exc),
            ) from exc
        return {
            "ok": True,
            "provider": "openai",
            "model": selected_model,
            "base_url": url,
        }

    url = (base_url or settings.ollama_base_url).rstrip("/")
    body = {
        "model": selected_model,
        "stream": False,
        "messages": [{"role": "user", "content": "Reply only: OK"}],
        "think": False,
        "keep_alive": settings.ollama_keep_alive or "10m",
        "options": {
            "temperature": 0,
            "num_predict": 1,
            # Load the model with the context the real calls will use. Without this Ollama loads it at its own
            # default (which can be 262144 tokens), and the first real call then forces a second, slower load.
            **({"num_ctx": int(num_ctx)} if num_ctx else {}),
        },
    }
    # Loading is the point of a warmup, and a large model can take minutes. A short timeout here abandons the load,
    # and Ollama aborts a load whose requester has gone, which also fails every other request waiting on it.
    timeout = httpx.Timeout(
        connect=settings.ollama_connect_timeout_seconds,
        read=min(settings.ollama_timeout_seconds, 900.0),
        write=60.0,
        pool=settings.ollama_connect_timeout_seconds,
    )
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(f"{url}/api/chat", json=body)
        response.raise_for_status()
    except Exception as exc:
        raise TouchupFailure(
            502,
            "Ollama warmup request failed.",
            str(exc),
        ) from exc
    return {
        "ok": True,
        "provider": "ollama",
        "model": selected_model,
        "base_url": url,
    }


def _response_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                return str(
                    error.get("message")
                    or error.get("detail")
                    or error
                )
            return str(payload.get("detail") or payload.get("message") or "")
    except Exception:
        # Safe: only extracts a friendlier message from an error body; the raw
        # response text below is returned instead and the HTTP failure stands.
        pass
    return response.text[:1500]
