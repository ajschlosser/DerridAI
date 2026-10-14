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

"""Non-authoritative enrichment benchmark runs and their comparison.

A result summarizes one arm's measurements against a fixed fixture. It never
carries source text or reviewer values, and a comparison reports raw left/right
values, deltas, and per-gate outcomes without choosing an overall winner.
Tolerances are declared by the caller before the arms are compared.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .enrichment_benchmark import EnrichmentBenchmarkFixture, _canonical_hash

GateStatus = Literal["met", "not_met", "not_measured"]


class EnrichmentBenchmarkResult(BaseModel):
    result_id: str = Field(min_length=1, max_length=160)
    arm: str = Field(min_length=1, max_length=80)
    fixture_fingerprint: str = Field(min_length=64, max_length=64)
    app_version: str
    pipeline_identity: dict[str, Any]
    provider_identity: dict[str, Any]
    created_at: datetime
    record_count: int = Field(ge=0)
    record_latency_ms: dict[str, Any]
    call_latency_ms: dict[str, Any]
    call_contract: dict[str, Any]
    structured_model_invocations: dict[str, Any]
    workload: dict[str, Any] = Field(default_factory=dict)
    quality: dict[str, Any] = Field(default_factory=dict)
    human_or_deterministic_overwrites: int | None = Field(default=None, ge=0)
    unsupported_evidence_suggestions: int | None = Field(default=None, ge=0)
    citation_binding_failures: int | None = Field(default=None, ge=0)
    limitations: list[str] = Field(default_factory=list)


class BenchmarkTolerances(BaseModel):
    """Declared before comparing; never tuned after seeing a result."""

    max_p50_ratio: float = Field(default=0.5, gt=0)
    max_p95_ratio: float = Field(default=0.9, gt=0)
    max_coverage_drop: float = Field(default=0.05, ge=0)
    max_rate_increase: float = Field(default=0.02, ge=0)
    max_precision_drop: float = Field(default=0.02, ge=0)


_QUALITY_KEYS = (
    "proposals",
    "reviews",
    "acceptance_rate",
    "correction_rate",
    "rejection_rate",
    "grounded_rate",
    "supported_rate",
    "autofill_precision",
    "unresolved_remaining",
)


def build_enrichment_benchmark_result(
    *,
    result_id: str,
    arm: str,
    fixture: EnrichmentBenchmarkFixture,
    app_version: str,
    model_metrics: dict[str, Any],
    workload: dict[str, Any] | None = None,
    unresolved_remaining: int | None = None,
    human_or_deterministic_overwrites: int | None = None,
    unsupported_evidence_suggestions: int | None = None,
    citation_binding_failures: int | None = None,
) -> EnrichmentBenchmarkResult:
    """Condense one model's `enrichment_metrics` entry; no per-event data is kept."""
    record_latency = dict(model_metrics.get("record_latency_ms") or {})
    quality = {key: model_metrics.get(key) for key in _QUALITY_KEYS if key in model_metrics}
    if unresolved_remaining is not None:
        quality["unresolved_remaining"] = unresolved_remaining
    limitations = list(fixture.limitations)
    if not record_latency.get("records"):
        limitations.append("No Record wall-clock events were captured; latency gates cannot be evaluated.")
    for name, value in (
        ("human/deterministic overwrite count", human_or_deterministic_overwrites),
        ("unsupported evidence suggestion count", unsupported_evidence_suggestions),
        ("citation binding failure count", citation_binding_failures),
    ):
        if value is None:
            limitations.append(f"The {name} was not measured for this run.")
    return EnrichmentBenchmarkResult(
        result_id=result_id,
        arm=arm,
        fixture_fingerprint=fixture.fingerprint,
        app_version=app_version,
        pipeline_identity=dict(fixture.pipeline_identity),
        provider_identity=dict(fixture.provider_identity),
        created_at=datetime.now(UTC),
        record_count=int(record_latency.get("records") or 0),
        record_latency_ms=record_latency,
        call_latency_ms=dict(model_metrics.get("call_latency_ms") or {}),
        call_contract=dict(model_metrics.get("call_contract") or {}),
        structured_model_invocations=dict(model_metrics.get("structured_model_invocations") or {}),
        workload=dict(workload or {}),
        quality=quality,
        human_or_deterministic_overwrites=human_or_deterministic_overwrites,
        unsupported_evidence_suggestions=unsupported_evidence_suggestions,
        citation_binding_failures=citation_binding_failures,
        limitations=limitations,
    )


def input_fingerprint(fixture: EnrichmentBenchmarkFixture) -> str:
    """Fixture identity with the pipeline left out, so pipeline versions can be A/B compared."""
    return _canonical_hash(
        {
            "source_sha256": fixture.source_sha256,
            "schema": [fixture.schema_id, fixture.schema_version, fixture.schema_hash],
            "manifest_sha256": fixture.manifest_sha256,
            "records": [item.model_dump(mode="json") for item in fixture.records],
            "request_contract": fixture.request_contract,
            "provider_identity": fixture.provider_identity,
        }
    )


def _delta(left: Any, right: Any) -> float | None:
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return round(float(right) - float(left), 6)
    return None


def _gate(name: str, status: GateStatus, left: Any, right: Any, rule: str) -> dict[str, Any]:
    return {"gate": name, "status": status, "left": left, "right": right, "rule": rule}


def _ratio_gate(name: str, left: Any, right: Any, limit: float, *, strict: bool) -> dict[str, Any]:
    rule = f"right/left {'<' if strict else '<='} {limit}"
    if not isinstance(left, (int, float)) or not isinstance(right, (int, float)) or left <= 0:
        return _gate(name, "not_measured", left, right, rule)
    ratio = right / left
    met = ratio < limit if strict else ratio <= limit
    return _gate(name, "met" if met else "not_met", left, right, rule)


def _drop_gate(name: str, left: Any, right: Any, limit: float, *, higher_is_better: bool) -> dict[str, Any]:
    rule = (
        f"right may be at most {limit} lower than left"
        if higher_is_better
        else f"right may be at most {limit} higher than left"
    )
    change = _delta(left, right)
    if change is None:
        return _gate(name, "not_measured", left, right, rule)
    worse = -change if higher_is_better else change
    return _gate(name, "met" if worse <= limit else "not_met", left, right, rule)


def _count_gate(name: str, left: int | None, right: int | None, *, zero: bool) -> dict[str, Any]:
    rule = "right must be 0" if zero else "right must not exceed left"
    if right is None or (not zero and left is None):
        return _gate(name, "not_measured", left, right, rule)
    met = right == 0 if zero else right <= (left or 0)
    return _gate(name, "met" if met else "not_met", left, right, rule)


def compare_enrichment_benchmark_results(
    left: EnrichmentBenchmarkResult,
    right: EnrichmentBenchmarkResult,
    *,
    left_fixture: EnrichmentBenchmarkFixture,
    right_fixture: EnrichmentBenchmarkFixture,
    tolerances: BenchmarkTolerances,
) -> dict[str, Any]:
    """Raw values, deltas, and declared-gate outcomes. Left is the baseline arm.

    Raises ValueError when the arms differ in anything but the enrichment pipeline
    (Records, schema, manifest, request controls, provider/model). A pipeline A/B
    is the one intended difference; a model study needs its own explicit comparison.
    """
    for result, fixture in ((left, left_fixture), (right, right_fixture)):
        if result.fixture_fingerprint != fixture.fingerprint:
            raise ValueError("A benchmark result does not match the fixture supplied for it.")
    if input_fingerprint(left_fixture) != input_fingerprint(right_fixture):
        raise ValueError(
            "Enrichment benchmark arms differ in Record/schema/configuration/provider identity; "
            "only the enrichment pipeline may differ between compared arms."
        )

    ll, rl = left.record_latency_ms, right.record_latency_ms
    lq, rq = left.quality, right.quality
    left_cov = (lq.get("proposals") or 0) / left.record_count if left.record_count else None
    right_cov = (rq.get("proposals") or 0) / right.record_count if right.record_count else None
    gates = [
        _ratio_gate("record_p50", ll.get("p50"), rl.get("p50"), tolerances.max_p50_ratio, strict=False),
        _ratio_gate("record_p95", ll.get("p95"), rl.get("p95"), tolerances.max_p95_ratio, strict=True),
        _count_gate("human_deterministic_overwrites", left.human_or_deterministic_overwrites, right.human_or_deterministic_overwrites, zero=True),
        _count_gate("unsupported_evidence_suggestions", left.unsupported_evidence_suggestions, right.unsupported_evidence_suggestions, zero=False),
        _count_gate("citation_binding_failures", left.citation_binding_failures, right.citation_binding_failures, zero=False),
        _drop_gate("proposals_per_record", left_cov, right_cov, tolerances.max_coverage_drop * (left_cov or 0), higher_is_better=True),
        _drop_gate("correction_rate", lq.get("correction_rate"), rq.get("correction_rate"), tolerances.max_rate_increase, higher_is_better=False),
        _drop_gate("rejection_rate", lq.get("rejection_rate"), rq.get("rejection_rate"), tolerances.max_rate_increase, higher_is_better=False),
        _drop_gate("autofill_precision", lq.get("autofill_precision"), rq.get("autofill_precision"), tolerances.max_precision_drop, higher_is_better=True),
    ]
    return {
        "input_fingerprint": input_fingerprint(left_fixture),
        "left": {"result_id": left.result_id, "arm": left.arm, "pipeline": left.pipeline_identity},
        "right": {"result_id": right.result_id, "arm": right.arm, "pipeline": right.pipeline_identity},
        "tolerances": tolerances.model_dump(),
        "deltas": {
            "record_latency_ms": {key: _delta(ll.get(key), rl.get(key)) for key in ("p50", "p95", "max", "total")},
            "call_latency_ms": {key: _delta(left.call_latency_ms.get(key), right.call_latency_ms.get(key)) for key in ("p50", "p95", "max", "total")},
            "model_invocations_total": _delta(
                left.structured_model_invocations.get("total"),
                right.structured_model_invocations.get("total"),
            ),
            "recovery_calls": _delta(
                left.structured_model_invocations.get("recovery_calls"),
                right.structured_model_invocations.get("recovery_calls"),
            ),
            "quality": {key: _delta(lq.get(key), rq.get(key)) for key in _QUALITY_KEYS},
        },
        "gates": gates,
        "limitations": sorted(set(left.limitations) | set(right.limitations)),
    }
