# Copyright 2026 Aaron John Schlosser, PhD.
"""Pure LLM request/response helpers: generation options, budgets, JSON repair, transport errors.

Deterministic parsing and validation around a corpus-build LLM call, independent of any
particular provider session or build state. Moved verbatim out of PdfCorpusBuildManager
(extracted during the 0.70 decomposition); the stateful methods that call these (_chat_json, _segment, etc.) stay
on the manager.
"""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import ValidationError

from .config import settings
from .models import OllamaTouchupOptions
from .structured_json import parse_json_object


class StructuredOutputError(ValueError):
    """Every attempt of one or more provider roles failed to return a valid structured answer.

    ``failures`` holds one ``"<role> <provider>/<model>: <error>"`` entry per role that ran, and
    ``timed_out`` says whether the last role stopped on a read timeout (pipeline timeout edges
    route on it).
    """

    def __init__(
        self,
        message: str,
        *,
        failures: list[str],
        timed_out: bool = False,
        truncated: bool = False,
    ) -> None:
        super().__init__(message)
        self.failures = failures
        self.timed_out = timed_out
        self.truncated = truncated


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


def _provider_roles(request: dict[str, Any]) -> dict[str, tuple[str, str]]:
    """Provider/model identity of each provider role the request configures."""
    roles = {"primary": _llm_config(request)[:2]}
    reviewer = request.get("_review_provider")
    if isinstance(reviewer, dict) and reviewer:
        roles["review"] = _llm_config(reviewer)[:2]
    return roles


def _parse_json_robust(raw: str) -> dict[str, Any]:
    """Parse one model JSON object through the shared repair-first policy.

    Syntax-level defects are repaired locally before the caller spends another
    model turn. Structurally incomplete or token-limited output raises a
    StructuredJsonTruncatedError instead of being repaired into apparently
    complete data.
    """
    return parse_json_object(raw)


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

