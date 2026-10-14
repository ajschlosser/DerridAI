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

"""Shared structured-completion policy regression tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.structured_completion import (
    StructuredCompletionError,
    complete_structured_json,
)


def _metrics():
    values: dict[str, int] = {}

    def note(name: str, amount: int = 1) -> None:
        values[name] = values.get(name, 0) + amount

    return values, note


def test_repair_succeeds_before_retry_and_is_measured():
    calls = []
    metrics, note = _metrics()

    def request(context):
        calls.append(context)
        return '{"answer": 1,}'

    result = complete_structured_json(
        request,
        prompt="Return JSON.",
        attempts=3,
        on_metric=note,
        sleep_fn=lambda _: None,
    )

    assert result == {"answer": 1}
    assert len(calls) == 1
    assert metrics["calls"] == 1
    assert metrics["structured_output_repaired"] == 1
    assert metrics.get("retries", 0) == 0


def test_malformed_output_retries_with_syntax_specific_prompt():
    calls = []

    def request(context):
        calls.append(context)
        return "not json" if len(calls) == 1 else '{"answer": 1}'

    result = complete_structured_json(
        request,
        prompt="Return JSON.",
        attempts=2,
        sleep_fn=lambda _: None,
    )

    assert result == {"answer": 1}
    assert len(calls) == 2
    assert "JSON SYNTAX CORRECTION" in calls[1].prompt


def test_truncated_output_restarts_with_larger_budget():
    calls = []

    def request(context):
        calls.append(context)
        return '{"answer": [' if len(calls) == 1 else '{"answer": []}'

    result = complete_structured_json(
        request,
        prompt="Return JSON.",
        attempts=2,
        max_tokens=1200,
        sleep_fn=lambda _: None,
    )

    assert result == {"answer": []}
    assert "OUTPUT LIMIT CORRECTION" in calls[1].prompt
    assert "do not continue the partial object" in calls[1].prompt
    assert calls[1].max_tokens >= 1800
    assert calls[1].max_tokens > calls[0].max_tokens


def test_schema_failure_is_retried_after_syntax_succeeds():
    calls = []

    def request(context):
        calls.append(context)
        return '{"wrong": 1}' if len(calls) == 1 else '{"answer": 2}'

    def validate(value):
        if "answer" not in value:
            raise ValueError("answer is required")
        return {"answer": int(value["answer"])}

    result = complete_structured_json(
        request,
        prompt="Return JSON.",
        validate=validate,
        attempts=2,
        sleep_fn=lambda _: None,
    )

    assert result == {"answer": 2}
    assert "SCHEMA CORRECTION" in calls[1].prompt
    assert "answer is required" in calls[1].prompt


def test_timeout_is_classified_and_not_retried_by_default():
    calls = []
    metrics, note = _metrics()

    def request(context):
        calls.append(context)
        raise TimeoutError("provider timed out")

    with pytest.raises(StructuredCompletionError) as error:
        complete_structured_json(
            request,
            prompt="Return JSON.",
            attempts=3,
            on_metric=note,
            sleep_fn=lambda _: None,
        )

    assert len(calls) == 1
    assert error.value.timed_out is True
    assert error.value.kind == "timeout"
    assert metrics["timeouts"] == 1


def test_transport_failure_uses_bounded_retry():
    calls = []

    def request(context):
        calls.append(context)
        if len(calls) == 1:
            raise RuntimeError("temporary provider failure")
        return '{"answer": 3}'

    result = complete_structured_json(
        request,
        prompt="Return JSON.",
        attempts=2,
        sleep_fn=lambda _: None,
    )

    assert result == {"answer": 3}
    assert len(calls) == 2
    assert "RETRY CORRECTION" in calls[1].prompt
