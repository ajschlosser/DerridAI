# Copyright 2026 Aaron John Schlosser, PhD.
"""Shared structured-JSON parsing and failure classification for LLM responses.

Provider JSON modes reduce syntax errors but do not eliminate them, especially on
local/OpenAI-compatible runtimes.  This module keeps the recovery policy
deterministic:

1. strict JSON parse first;
2. never "repair" a response the provider says was cut off by an output limit;
3. classify structurally incomplete JSON as truncated when that is clear;
4. otherwise run json-repair once;
5. require one top-level JSON object after repair.

The parser repairs syntax only.  Domain/schema validation remains the caller's
responsibility so repair cannot silently invent a scholarly conclusion.
"""

from __future__ import annotations

import json
import re
from typing import Any

from json_repair import repair_json

_TRUNCATION_REASONS = {
    "length",
    "max_tokens",
    "max_output_tokens",
    "token_limit",
    "output_limit",
    "context_length",
    "max_length",
    "max_new_tokens",
}


class StructuredJsonError(ValueError):
    """Base class for structured-output failures with machine-readable kind."""

    kind = "malformed"
    truncated = False
    repaired = False

    def __init__(
        self,
        message: str,
        *,
        diagnostic: str | None = None,
        finish_reason: str | None = None,
    ) -> None:
        super().__init__(message)
        self.diagnostic = diagnostic
        self.finish_reason = finish_reason


class StructuredJsonTruncatedError(StructuredJsonError):
    """The model response ended before the JSON object was complete."""

    kind = "truncated"
    truncated = True


class StructuredJsonMalformedError(StructuredJsonError):
    """The response was complete enough to inspect but remained invalid after repair."""

    kind = "malformed"


def finish_reason_is_truncated(reason: str | None) -> bool:
    normalized = str(reason or "").strip().casefold().replace("-", "_").replace(" ", "_")
    return normalized in _TRUNCATION_REASONS


def _strip_wrappers(text: str) -> str:
    value = str(text or "").strip()
    value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.I)
    value = re.sub(r"\s*```$", "", value)
    return value.strip()


def _object_candidate(value: str) -> tuple[str, bool]:
    """Return the first complete object when one is present, plus incompleteness.

    A complete object may be surrounded by prose/diagnostics.  When the first
    opening brace never balances (or a string never terminates), the response is
    structurally incomplete and is treated as truncation rather than malformed
    content so json-repair cannot manufacture a syntactically complete but
    semantically partial answer.
    """
    start = value.find("{")
    if start < 0:
        return value, False

    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(value[start:], start=start):
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
                return value[start : index + 1], False

    return value[start:], True


def parse_json_object(
    text: str,
    *,
    finish_reason: str | None = None,
) -> dict[str, Any]:
    """Parse one JSON object, repairing malformed-but-complete syntax once.

    Truncation is intentionally detected before repair.  json-repair can close
    braces/strings and fill missing values; doing that to a token-limited answer
    could turn an incomplete model answer into apparently valid data.
    """
    value = _strip_wrappers(text)
    if not value:
        raise StructuredJsonMalformedError(
            "LLM returned an empty structured response.",
            diagnostic="",
            finish_reason=finish_reason,
        )

    if finish_reason_is_truncated(finish_reason):
        raise StructuredJsonTruncatedError(
            f"LLM structured response was cut off by provider finish reason {finish_reason!r}.",
            diagnostic=value[:2000],
            finish_reason=finish_reason,
        )

    # Strict parse of the whole response wins. This also prevents a valid
    # top-level array such as [{"value": 1}] from being silently converted into
    # its first nested object merely because the contract expects an object.
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = None
    else:
        if not isinstance(parsed, dict):
            raise StructuredJsonMalformedError(
                "LLM structured response was not a JSON object.",
                diagnostic=value[:2000],
                finish_reason=finish_reason,
            )
        return parsed

    candidate, structurally_incomplete = _object_candidate(value)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as strict_error:
        if structurally_incomplete:
            raise StructuredJsonTruncatedError(
                "LLM structured response ended before its JSON object was complete.",
                diagnostic=value[:2000],
                finish_reason=finish_reason,
            ) from strict_error
        try:
            parsed = repair_json(
                candidate,
                return_objects=True,
                skip_json_loads=True,
            )
        except Exception as repair_error:  # noqa: BLE001 - normalize third-party parser failures
            raise StructuredJsonMalformedError(
                f"LLM returned malformed JSON that could not be repaired: {strict_error.msg} "
                f"at character {strict_error.pos}.",
                diagnostic=value[:2000],
                finish_reason=finish_reason,
            ) from repair_error

    if not isinstance(parsed, dict):
        raise StructuredJsonMalformedError(
            "LLM structured response was not a JSON object.",
            diagnostic=value[:2000],
            finish_reason=finish_reason,
        )
    return parsed
