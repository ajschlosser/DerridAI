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

"""Sanitization and stage construction shared by pipeline trace adapters."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .models import PipelineStageTrace
from .registry import strategy_registry

SECRET_TRACE_KEYS = {
    "api_key",
    "authorization",
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
}
MAX_TRACE_STRING = 500


def parse_trace_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    text = str(value or "").strip()
    if not text:
        return datetime.now(UTC)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(UTC)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def sanitize_trace_value(value: Any, *, key: str = "") -> Any:
    """Recursively remove secrets and bound generic telemetry values."""

    normalized_key = str(key or "").casefold()
    if any(secret in normalized_key for secret in SECRET_TRACE_KEYS):
        return "[redacted]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:MAX_TRACE_STRING]
    if isinstance(value, (list, tuple)):
        return [sanitize_trace_value(item) for item in list(value)[:100]]
    if isinstance(value, dict):
        return {
            str(item_key)[:120]: sanitize_trace_value(item_value, key=str(item_key))
            for item_key, item_value in list(value.items())[:100]
        }
    return str(value)[:MAX_TRACE_STRING]


def trace_stage(
    stage_id: str,
    strategy_id: str,
    *,
    elapsed_seconds: float | None = None,
    input_count: int | None = None,
    output_count: int | None = None,
    parameters: dict[str, Any] | None = None,
    provider: str | None = None,
    model: str | None = None,
    collection: str | None = None,
    fallback_reason: str | None = None,
    warnings: list[str] | None = None,
    score_summary: dict[str, Any] | None = None,
    status: str = "completed",
) -> PipelineStageTrace:
    spec = strategy_registry.require(strategy_id)
    return PipelineStageTrace(
        stage_id=stage_id,
        strategy_id=strategy_id,
        strategy_version=spec.version,
        status=status,
        elapsed_ms=(
            max(0, int(float(elapsed_seconds) * 1000))
            if elapsed_seconds is not None
            else None
        ),
        input_count=input_count,
        output_count=output_count,
        parameters=sanitize_trace_value(parameters or {}),
        provider=provider,
        model=model,
        collection=collection,
        fallback_reason=fallback_reason,
        warnings=[str(item)[:MAX_TRACE_STRING] for item in (warnings or [])],
        score_summary=sanitize_trace_value(score_summary or {}),
    )
