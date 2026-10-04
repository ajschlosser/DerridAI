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

"""Typed, payload-safe LLM/provider failure classification.

Provider adapters may retain a bounded diagnostic message for administrators,
but orchestration should make retry decisions from these stable fields instead
of parsing rendered exception text. The classifier deliberately understands the
attributes exposed by structured-completion wrappers so retryability survives
provider escalation and the generic pipeline graph.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

FailureClass = Literal[
    "authentication",
    "capability",
    "rate_limit",
    "request",
    "timeout",
    "transient_provider",
    "transport",
    "structured_output",
    "unknown",
]


@dataclass(frozen=True)
class FailureDisposition:
    """Safe operational facts used by recovery policy and telemetry."""

    code: str
    failure_class: FailureClass
    retryable: bool
    http_status: int | None = None
    provider_code: str | None = None
    retry_after_seconds: float | None = None
    capability_mismatch: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "failure_class": self.failure_class,
            "retryable": self.retryable,
            "http_status": self.http_status,
            "provider_code": self.provider_code,
            "retry_after_seconds": self.retry_after_seconds,
            "capability_mismatch": self.capability_mismatch,
        }


def _http_disposition(
    status_code: int,
    *,
    provider_code: str | None = None,
    retry_after_seconds: float | None = None,
    capability_mismatch: bool = False,
) -> FailureDisposition:
    if status_code in {401, 403}:
        return FailureDisposition(
            "provider_authentication_failed",
            "authentication",
            False,
            status_code,
            provider_code,
            retry_after_seconds,
            capability_mismatch,
        )
    if status_code == 429:
        return FailureDisposition(
            "provider_rate_limited",
            "rate_limit",
            True,
            status_code,
            provider_code,
            retry_after_seconds,
            capability_mismatch,
        )
    if status_code in {408, 504}:
        return FailureDisposition(
            "provider_timeout",
            "timeout",
            True,
            status_code,
            provider_code,
            retry_after_seconds,
            capability_mismatch,
        )
    if status_code >= 500:
        return FailureDisposition(
            "provider_upstream_failure",
            "transient_provider",
            True,
            status_code,
            provider_code,
            retry_after_seconds,
            capability_mismatch,
        )
    if capability_mismatch:
        return FailureDisposition(
            "structured_output_capability_mismatch",
            "capability",
            False,
            status_code,
            provider_code,
            retry_after_seconds,
            True,
        )
    return FailureDisposition(
        "provider_request_failed",
        "request",
        False,
        status_code,
        provider_code,
        retry_after_seconds,
        False,
    )


class ProviderRequestError(RuntimeError):
    """An HTTP provider failure with machine-readable retry/capability facts."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        provider_code: str | None = None,
        provider_error_type: str | None = None,
        retry_after_seconds: float | None = None,
        capability_mismatch: bool = False,
    ) -> None:
        super().__init__(message)
        disposition = _http_disposition(
            int(status_code),
            provider_code=provider_code,
            retry_after_seconds=retry_after_seconds,
            capability_mismatch=capability_mismatch,
        )
        self.status_code = int(status_code)
        self.provider_code = provider_code
        self.provider_error_type = provider_error_type
        self.retry_after_seconds = retry_after_seconds
        self.capability_mismatch = capability_mismatch
        self.failure_code = disposition.code
        self.failure_class = disposition.failure_class
        self.retryable = disposition.retryable
        self.timed_out = disposition.failure_class == "timeout"
        self.kind = "timeout" if self.timed_out else "transport"

    @property
    def disposition(self) -> FailureDisposition:
        return _http_disposition(
            self.status_code,
            provider_code=self.provider_code,
            retry_after_seconds=self.retry_after_seconds,
            capability_mismatch=self.capability_mismatch,
        )


def combine_failure_dispositions(
    dispositions: list[FailureDisposition] | tuple[FailureDisposition, ...],
) -> FailureDisposition:
    """Combine a provider chain without turning a semantic failure into retryable work."""

    items = [item for item in dispositions if isinstance(item, FailureDisposition)]
    if not items:
        return FailureDisposition("unknown_failure", "unknown", False)
    if len(items) == 1:
        return items[0]

    retryable = all(item.retryable for item in items)
    capability_mismatch = any(item.capability_mismatch for item in items)
    retry_after = max(
        (item.retry_after_seconds for item in items if item.retry_after_seconds is not None),
        default=None,
    )
    classes = {item.failure_class for item in items}
    codes = {item.code for item in items}
    if len(classes) == 1 and len(codes) == 1:
        first = items[0]
        return FailureDisposition(
            first.code,
            first.failure_class,
            retryable,
            first.http_status if all(item.http_status == first.http_status for item in items) else None,
            first.provider_code if all(item.provider_code == first.provider_code for item in items) else None,
            retry_after,
            capability_mismatch,
        )
    return FailureDisposition(
        "provider_chain_failed",
        "transient_provider" if retryable else "structured_output",
        retryable,
        None,
        None,
        retry_after,
        capability_mismatch,
    )


def failure_disposition(error: BaseException) -> FailureDisposition:
    """Normalize nested structured/provider failures into one recovery decision."""

    if isinstance(error, ProviderRequestError):
        return error.disposition

    explicit = getattr(error, "failure_disposition", None)
    if isinstance(explicit, FailureDisposition):
        return explicit

    details = getattr(error, "failure_details", None)
    if isinstance(details, (list, tuple)) and details:
        normalized: list[FailureDisposition] = []
        for item in details:
            if isinstance(item, FailureDisposition):
                normalized.append(item)
            elif isinstance(item, dict):
                try:
                    normalized.append(FailureDisposition(**item))
                except (TypeError, ValueError):
                    continue
        if normalized:
            return combine_failure_dispositions(normalized)

    last_error = getattr(error, "last_error", None)
    if isinstance(last_error, BaseException) and last_error is not error:
        nested = failure_disposition(last_error)
        if nested.failure_class != "unknown":
            return nested

    if bool(getattr(error, "timed_out", False)):
        return FailureDisposition("provider_timeout", "timeout", True)
    if bool(getattr(error, "truncated", False)):
        return FailureDisposition("structured_output_truncated", "structured_output", False)

    kinds = {
        str(value)
        for value in (getattr(error, "failure_kinds", None) or [])
        if str(value)
    }
    if kinds:
        retryable_kinds = {"timeout", "transport"}
        if kinds <= retryable_kinds:
            return FailureDisposition(
                "structured_transport_failed",
                "timeout" if kinds == {"timeout"} else "transport",
                True,
            )
        if "schema_invalid" in kinds or "malformed" in kinds:
            return FailureDisposition(
                "structured_output_invalid",
                "structured_output",
                False,
            )

    status_code = getattr(error, "status_code", None)
    if isinstance(status_code, int):
        return _http_disposition(
            status_code,
            provider_code=getattr(error, "provider_code", None),
            retry_after_seconds=getattr(error, "retry_after_seconds", None),
            capability_mismatch=bool(getattr(error, "capability_mismatch", False)),
        )

    text = f"{type(error).__name__} {error}".casefold()
    if "timed out" in text or "timeout" in text:
        return FailureDisposition("provider_timeout", "timeout", True)
    if any(
        marker in text
        for marker in (
            "connection reset",
            "connection refused",
            "connection aborted",
            "broken pipe",
            "temporarily unavailable",
            "remote end closed",
        )
    ):
        return FailureDisposition("provider_transport_failed", "transport", True)
    return FailureDisposition("unknown_failure", "unknown", False)
