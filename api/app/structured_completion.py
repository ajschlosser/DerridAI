# Copyright 2026 Aaron John Schlosser, PhD.
"""Shared retry/validation policy for LLM responses that must be JSON objects.

Provider transports own HTTP/SSE details. This module owns the behavior after a
caller has decided that one model turn must satisfy a structured contract:

- deterministic parse/repair before another model call;
- explicit malformed vs. truncated vs. schema-invalid classification;
- truncation-aware output-budget growth;
- bounded retries with failure-specific correction prompts;
- shared attempt/metric hooks so tracing and persistence stay caller-owned.

The policy never repairs a response classified as truncated. Domain validation is
supplied by the caller and runs after syntax recovery.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, Literal, TypeVar, cast

from .structured_json import (
    StructuredJsonMalformedError,
    StructuredJsonTruncatedError,
    parse_json_object_result,
)

T = TypeVar("T")
StructuredFailureKind = Literal[
    "truncated",
    "malformed",
    "schema_invalid",
    "timeout",
    "transport",
]


@dataclass(frozen=True)
class StructuredAttemptContext:
    """Inputs for one provider turn after retry policy has been applied."""

    attempt: int
    prompt: str
    max_tokens: int
    prior_failure_kind: StructuredFailureKind | None = None


@dataclass(frozen=True)
class StructuredAttemptOutcome(Generic[T]):
    """Auditable result of one structured-output attempt."""

    context: StructuredAttemptContext
    raw_response: str = ""
    value: T | None = None
    error: Exception | None = None
    failure_kind: StructuredFailureKind | None = None
    repaired: bool = False


class StructuredCompletionError(ValueError):
    """Bounded structured generation exhausted without a validated value."""

    def __init__(
        self,
        message: str,
        *,
        last_error: Exception | None,
        failure_kinds: list[StructuredFailureKind],
        attempts: int,
    ) -> None:
        super().__init__(message)
        self.last_error = last_error
        self.failure_kinds = tuple(failure_kinds)
        self.attempts = attempts
        self.kind = self.failure_kinds[-1] if self.failure_kinds else None
        self.timed_out = "timeout" in self.failure_kinds
        self.truncated = "truncated" in self.failure_kinds
        self.diagnostic = str(getattr(last_error, "diagnostic", "") or "") or None


def classify_structured_failure(
    error: Exception,
    *,
    validation_error: bool = False,
) -> StructuredFailureKind:
    """Normalize parser, validator, provider, and timeout failures."""

    if validation_error:
        return "schema_invalid"
    if isinstance(error, StructuredJsonTruncatedError):
        return "truncated"
    if isinstance(error, StructuredJsonMalformedError):
        return "malformed"

    kind = str(getattr(error, "kind", "") or "").strip().casefold()
    if kind == "truncated":
        return "truncated"
    if kind == "malformed":
        return "malformed"
    if bool(getattr(error, "truncated", False)):
        return "truncated"

    status_code = getattr(error, "status_code", None)
    text = f"{type(error).__name__} {error}".casefold()
    if status_code == 504 or "timeout" in text or "timed out" in text:
        return "timeout"
    return "transport"


def structured_retry_note(
    kind: StructuredFailureKind,
    error: Exception | None,
    *,
    diagnostic: str = "",
) -> str:
    """Return the standard correction appended after a failed structured turn."""

    if kind == "truncated":
        note = (
            "\n\nOUTPUT LIMIT CORRECTION: the previous JSON response was cut off before "
            "completion. Start again; do not continue the partial object. Return one COMPLETE "
            "JSON object matching the schema, and keep optional explanations as concise as possible."
        )
    elif kind == "malformed":
        note = (
            "\n\nJSON SYNTAX CORRECTION: the previous response was malformed and could not "
            "be repaired locally. Return ONLY one complete JSON object matching the supplied "
            "schema. Do not include Markdown, commentary, or trailing text."
        )
    elif kind == "schema_invalid":
        note = (
            "\n\nSCHEMA CORRECTION: the previous JSON object was syntactically usable but "
            "did not satisfy the required response contract. "
            f"Validation error: {error}. Return ONLY one complete JSON object that exactly "
            "matches the supplied schema."
        )
    else:
        note = (
            "\n\nRETRY CORRECTION: the previous model request failed before a validated "
            "structured answer was available. Start the task again and return ONLY one complete "
            "JSON object matching the supplied schema."
        )

    if diagnostic:
        note += f"\nPrevious response excerpt: {diagnostic[:1200]}"
    return note


def structured_token_budget(
    *,
    base_max_tokens: int,
    attempt: int,
    prior_failure_kind: StructuredFailureKind | None,
    max_token_cap: int | None = None,
) -> int:
    """Apply one shared output-growth rule without reducing the initial budget."""

    base = max(1, int(base_max_tokens))
    cap = max(base, int(max_token_cap)) if max_token_cap is not None else max(base, 8192)
    budget = base + (max(1, int(attempt)) - 1) * 1024
    if prior_failure_kind == "truncated":
        budget = max(budget, int(base * 1.5))
    return min(cap, budget)


def complete_structured_json(
    request_once: Callable[[StructuredAttemptContext], str],
    *,
    prompt: str,
    validate: Callable[[dict[str, Any]], T] | None = None,
    attempts: int = 2,
    max_tokens: int = 4096,
    max_token_cap: int | None = None,
    initial_note: str = "",
    retry_guidance: Callable[[Exception], str] | None = None,
    retry_transport_errors: bool = True,
    retry_timeouts: bool = False,
    on_attempt_start: Callable[[StructuredAttemptContext], None] | None = None,
    on_attempt_finish: Callable[[StructuredAttemptOutcome[T]], None] | None = None,
    on_metric: Callable[[str, int], None] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> T:
    """Generate, parse, validate, and retry one structured model task.

    request_once performs exactly one provider request. It receives the rendered
    retry prompt and effective token budget. validate owns the semantic/domain
    contract (for example, Pydantic validation) and may return a transformed
    value.

    Timeouts are terminal by default because a hard read timeout normally
    consumed the caller's stage budget. Other transport failures are retried
    within the same bounded attempt count.
    """

    total_attempts = max(1, int(attempts))
    failure_kinds: list[StructuredFailureKind] = []
    last_error: Exception | None = None
    last_raw = ""

    def metric(name: str, amount: int = 1) -> None:
        if on_metric is None:
            return
        try:
            on_metric(name, amount)
        except Exception:
            # Telemetry must never alter the structured answer or retry policy.
            pass

    def finish(outcome: StructuredAttemptOutcome[T]) -> None:
        if on_attempt_finish is not None:
            on_attempt_finish(outcome)

    for attempt in range(1, total_attempts + 1):
        prior_kind = failure_kinds[-1] if failure_kinds else None
        rendered_prompt = prompt
        if attempt == 1 and initial_note:
            rendered_prompt += initial_note
        elif attempt > 1 and last_error is not None and prior_kind is not None:
            diagnostic = str(getattr(last_error, "diagnostic", "") or "") or last_raw
            rendered_prompt += structured_retry_note(
                prior_kind,
                last_error,
                diagnostic=diagnostic,
            )
            if retry_guidance is not None:
                extra = str(retry_guidance(last_error) or "").strip()
                if extra:
                    rendered_prompt += "\n" + extra

        context = StructuredAttemptContext(
            attempt=attempt,
            prompt=rendered_prompt,
            max_tokens=structured_token_budget(
                base_max_tokens=max_tokens,
                attempt=attempt,
                prior_failure_kind=prior_kind,
                max_token_cap=max_token_cap,
            ),
            prior_failure_kind=prior_kind,
        )
        metric("calls")
        if attempt > 1:
            metric("retries")
        if on_attempt_start is not None:
            on_attempt_start(context)

        try:
            raw = request_once(context)
        except InterruptedError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalize provider-specific failures
            last_error = exc
            last_raw = str(getattr(exc, "diagnostic", "") or "")
            kind = classify_structured_failure(exc)
            failure_kinds.append(kind)
            if kind in {"truncated", "malformed"}:
                metric("structured_output_failures")
                metric(f"structured_output_{kind}")
            elif kind == "timeout":
                metric("timeouts")
            else:
                metric("transport_failures")
            finish(
                StructuredAttemptOutcome(
                    context=context,
                    raw_response=last_raw,
                    error=exc,
                    failure_kind=kind,
                )
            )
            may_retry = (
                attempt < total_attempts
                and (
                    (kind == "timeout" and retry_timeouts)
                    or (kind != "timeout" and (kind != "transport" or retry_transport_errors))
                )
            )
            if not may_retry:
                break
            sleep_fn(min(1.0, 0.2 * attempt) if kind == "truncated" else min(2.0, 0.35 * attempt))
            continue

        last_raw = str(raw or "")
        try:
            parsed = parse_json_object_result(last_raw)
        except (StructuredJsonTruncatedError, StructuredJsonMalformedError) as exc:
            last_error = exc
            kind = classify_structured_failure(exc)
            failure_kinds.append(kind)
            metric("structured_output_failures")
            metric(f"structured_output_{kind}")
            finish(
                StructuredAttemptOutcome(
                    context=context,
                    raw_response=last_raw,
                    error=exc,
                    failure_kind=kind,
                )
            )
            if attempt >= total_attempts:
                break
            sleep_fn(min(1.0, 0.2 * attempt) if kind == "truncated" else min(2.0, 0.35 * attempt))
            continue

        if parsed.repaired:
            metric("structured_output_repaired")

        try:
            value = validate(parsed.value) if validate is not None else cast(T, parsed.value)
        except InterruptedError:
            raise
        except Exception as exc:  # noqa: BLE001 - caller validator defines its own error type
            last_error = exc
            kind: StructuredFailureKind = "schema_invalid"
            failure_kinds.append(kind)
            metric("structured_output_failures")
            metric("structured_output_schema_invalid")
            finish(
                StructuredAttemptOutcome(
                    context=context,
                    raw_response=last_raw,
                    error=exc,
                    failure_kind=kind,
                    repaired=parsed.repaired,
                )
            )
            if attempt >= total_attempts:
                break
            sleep_fn(min(2.0, 0.35 * attempt))
            continue

        finish(
            StructuredAttemptOutcome(
                context=context,
                raw_response=last_raw,
                value=value,
                repaired=parsed.repaired,
            )
        )
        return value

    summary = ", ".join(failure_kinds) or "unknown failure"
    raise StructuredCompletionError(
        f"LLM structured output failed after {len(failure_kinds) or total_attempts} attempt(s): {summary}",
        last_error=last_error,
        failure_kinds=failure_kinds,
        attempts=len(failure_kinds) or total_attempts,
    ) from last_error
