# Copyright 2026 Aaron John Schlosser, PhD.
"""Pure LLM request/response helpers: generation options, budgets, JSON repair, transport errors.

Deterministic parsing and validation around a corpus-build LLM call, independent of any
particular provider session or build state. Moved verbatim out of PdfCorpusBuildManager
(see PROGRESS.md); the stateful methods that call these (_chat_json, _segment, etc.) stay
on the manager.
"""

from __future__ import annotations

import ast
import json
import re
from typing import Any

import httpx
from pydantic import ValidationError

from .config import settings
from .models import OllamaTouchupOptions
from .rag import _extract_json

_TRANSPORT_MARKERS = (
    "disconnected", "connection reset", "connection refused", "connection aborted", "broken pipe", "errno 97", "errno 104",
    "errno 111", "temporarily unavailable", "remote end closed", "eof occurred",
)


def _generation_options(request: dict[str, Any]) -> OllamaTouchupOptions:
    generation = request.get("generation")
    if isinstance(generation, OllamaTouchupOptions):
        return generation
    if isinstance(generation, dict):
        return OllamaTouchupOptions.model_validate(generation)
    return OllamaTouchupOptions()


def _context_window(request: dict[str, Any]) -> int | None:
    try:
        value = _generation_options(request).num_ctx
        return int(value) if value else None
    except (TypeError, ValueError, ValidationError):
        return None


def _validate_execution_budget(request: dict[str, Any]) -> None:
    """Reject an explicitly impossible segmentation context before work starts.

    Context size is a model execution constraint, never a record-boundary rule.
    Unknown remote-provider context limits are allowed; explicit local limits
    must be large enough for the configured source window plus structured
    output and conservative schema/system overhead.
    """
    context = _context_window(request)
    if not context:
        return
    limits = _stage_limits(request)
    required = int(limits["segmentation_window_tokens"]) + int(limits["segmentation_num_predict"]) + 1536
    if context < required:
        raise ValueError(
            f"Corpus build context is too small for the configured segmentation turn: "
            f"num_ctx={context}, approximate minimum={required}. Increase the provider/build context "
            "or reduce the segmentation input/output budgets."
        )


def _is_transport_error(exc: Exception) -> bool:
    """A dropped connection, not a bad answer or a timeout: worth trying again once the server is ready."""
    if isinstance(exc, (httpx.TimeoutException, InterruptedError)):
        return False
    text = f"{type(exc).__name__} {exc}".casefold()
    if "timeout" in text or "timed out" in text:
        return False
    return isinstance(exc, (httpx.TransportError, ConnectionError, OSError)) or any(marker in text for marker in _TRANSPORT_MARKERS)


def _llm_config(request: dict[str, Any]) -> tuple[str, str, str | None, str | None, OllamaTouchupOptions | None]:
    provider = str(request.get("provider") or "ollama")
    model = str(request.get("model") or (settings.openai_compat_model if provider == "openai" else settings.ollama_model))
    generation = request.get("generation")
    if isinstance(generation, dict):
        generation = OllamaTouchupOptions.model_validate(generation)
    return provider, model, request.get("base_url"), request.get("api_key"), generation


def _parse_json_robust(raw: str) -> dict[str, Any]:
    """Parse model JSON conservatively, repairing only syntax-level defects.

    The repair path never fabricates semantic values.  It handles the common
    local-model failures seen in long corpus runs: Markdown fences, leading
    prose, trailing commas and a response truncated after a complete object.
    """
    value = str(raw or "").strip()
    if not value:
        raise ValueError("LLM returned an empty response.")
    try:
        return _extract_json(value)
    except Exception:  # noqa: S110 — strict first pass; recovery below raises if nothing parses.
        pass
    value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.I)
    value = re.sub(r"\s*```$", "", value)
    start = value.find("{")
    if start < 0:
        raise ValueError("LLM response did not contain a JSON object.")
    # Find the last balanced object rather than assuming the final character
    # is a brace; routed/local providers occasionally append diagnostics.
    depth = 0
    in_string = False
    escaped = False
    end = -1
    for idx, char in enumerate(value[start:], start=start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = idx
                break
    if end < 0:
        raise ValueError("LLM JSON object was truncated before its closing brace.")
    candidate = value[start:end + 1]
    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        # Some otherwise capable local models occasionally emit a Python-like
        # object (single quotes / True / False / None) even while JSON mode is
        # requested. ``literal_eval`` is deliberately limited to literals and
        # therefore repairs syntax without executing code or inventing values.
        try:
            parsed = ast.literal_eval(candidate)
        except (ValueError, SyntaxError) as literal_exc:
            raise ValueError(f"LLM returned malformed JSON: {exc.msg} at character {exc.pos}.") from literal_exc
    if not isinstance(parsed, dict):
        raise ValueError("LLM response JSON was not an object.")
    return parsed


def _stage_limits(request: dict[str, Any]) -> dict[str, int]:
    defaults = {
        "manifest_num_predict": 1800,
        "segmentation_num_predict": 1200,
        "reconciliation_num_predict": 1000,
        "discourse_num_predict": 1600,
        "quotation_num_predict": 1500,
        "indexing_num_predict": 1200,
        "segmentation_window_tokens": 5000,
    }
    supplied = request.get("stage_limits")
    if hasattr(supplied, "model_dump"):
        supplied = supplied.model_dump()
    if isinstance(supplied, dict):
        for key, default in list(defaults.items()):
            try:
                value = int(supplied.get(key, default))
            except (TypeError, ValueError):
                value = default
            if key == "segmentation_window_tokens":
                defaults[key] = max(1024, min(24000, value))
            else:
                defaults[key] = max(256, min(8192, value))
    return defaults


def _stage_timeouts(request: dict[str, Any]) -> dict[str, int]:
    """Per-call read deadlines for long-running corpus LLM stages.

    These are deliberately much shorter than the provider-wide emergency
    network ceiling so one unhealthy generation cannot monopolize a corpus
    worker indefinitely. Values remain configurable per build.
    """
    defaults = {
        "manifest": 300, "segmentation": 300, "reconciliation": 240,
        "discourse": 240, "quotation": 240, "indexing": 180,
    }
    supplied = request.get("stage_timeouts")
    if isinstance(supplied, dict):
        for key, default in list(defaults.items()):
            try:
                value = int(supplied.get(key, default))
            except (TypeError, ValueError):
                value = default
            defaults[key] = max(30, min(1800, value))
    return defaults

