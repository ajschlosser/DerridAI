# Copyright 2026 Aaron John Schlosser, PhD.
"""Benchmark-run artifacts and their declared-gate comparison."""

from __future__ import annotations

import pytest
from app.enrichment_benchmark import build_enrichment_benchmark_fixture
from app.enrichment_benchmark_result import (
    BenchmarkTolerances,
    build_enrichment_benchmark_result,
    compare_enrichment_benchmark_results,
)
from app.metadata_schema import default_schema

REQUEST = {
    "provider": "ollama",
    "model": "m",
    "model_version": "d1",
    "enrichment_mode": "deep",
    "ablations": ["cross_build_learning"],
    "api_key": "SECRET",
}
RECORD = {"record_id": "r1", "record_revision": 1, "text": "t", "source_block_ids": ["b"]}


def _fixture(version=2, request=None):
    return build_enrichment_benchmark_fixture(
        fixture_id="f",
        version=1,
        build={"source_sha256": "a" * 64, "manifest": {}},
        records=[RECORD],
        schema=default_schema(),
        request=request or REQUEST,
        pipeline_identity={"pipeline_id": "p", "pipeline_version": version, "pipeline_hash": f"h{version}"},
    )


def _metrics(p50, p95, **extra):
    return {
        "record_latency_ms": {"records": 10, "p50": p50, "p95": p95, "max": p95, "total": p50 * 10},
        "call_latency_ms": {"p50": p50 / 2, "p95": p95 / 2, "max": p95, "total": 1.0},
        "structured_model_invocations": {"total": 30, "recovery_calls": 1},
        "proposals": 100,
        "correction_rate": 0.10,
        "rejection_rate": 0.05,
        "autofill_precision": 0.95,
        **extra,
    }


def _result(fixture, arm, metrics, **kw):
    return build_enrichment_benchmark_result(
        result_id=arm, arm=arm, fixture=fixture, app_version="x", model_metrics=metrics, **kw
    )


def _clean(**kw):
    return {"human_or_deterministic_overwrites": 0, "unsupported_evidence_suggestions": 2, "citation_binding_failures": 0, **kw}


def _gates(report):
    return {g["gate"]: g["status"] for g in report["gates"]}


def test_result_keeps_distributions_not_text_and_discloses_unmeasured_counts():
    fx = _fixture()
    result = _result(fx, "new", _metrics(1000, 2000))
    dumped = result.model_dump_json()
    assert "SECRET" not in dumped
    assert result.fixture_fingerprint == fx.fingerprint
    assert any("overwrite" in text for text in result.limitations)


def test_comparison_reports_deltas_and_gate_outcomes_without_a_winner():
    old, new = _fixture(1), _fixture(2)
    left = _result(old, "old", _metrics(1000, 4000), **_clean())
    right = _result(new, "new", _metrics(450, 2000), **_clean(unsupported_evidence_suggestions=1))
    report = compare_enrichment_benchmark_results(
        left, right, left_fixture=old, right_fixture=new, tolerances=BenchmarkTolerances()
    )
    assert report["deltas"]["record_latency_ms"]["p50"] == -550
    assert set(_gates(report).values()) == {"met"}
    assert "winner" not in report


def test_each_regression_fails_only_its_own_gate():
    old, new = _fixture(1), _fixture(2)
    left = _result(old, "old", _metrics(1000, 4000), **_clean())
    right = _result(
        new,
        "new",
        _metrics(600, 3900, rejection_rate=0.20, autofill_precision=0.80),
        **_clean(human_or_deterministic_overwrites=1),
    )
    status = _gates(
        compare_enrichment_benchmark_results(
            left, right, left_fixture=old, right_fixture=new, tolerances=BenchmarkTolerances()
        )
    )
    failed = {name for name, value in status.items() if value == "not_met"}
    assert failed == {"record_p50", "record_p95", "human_deterministic_overwrites", "rejection_rate", "autofill_precision"}


def test_unmeasured_gates_are_not_reported_as_met():
    old, new = _fixture(1), _fixture(2)
    left = _result(old, "old", _metrics(1000, 4000))
    right = _result(new, "new", _metrics(400, 2000))
    status = _gates(
        compare_enrichment_benchmark_results(
            left, right, left_fixture=old, right_fixture=new, tolerances=BenchmarkTolerances()
        )
    )
    assert status["human_deterministic_overwrites"] == "not_measured"
    assert status["unsupported_evidence_suggestions"] == "not_measured"


def test_comparison_rejects_arms_with_different_model_or_records():
    old = _fixture(1)
    other = _fixture(2, request={**REQUEST, "model_version": "d2"})
    left = _result(old, "old", _metrics(1000, 4000))
    right = _result(other, "new", _metrics(400, 2000))
    with pytest.raises(ValueError, match="only the enrichment pipeline"):
        compare_enrichment_benchmark_results(
            left, right, left_fixture=old, right_fixture=other, tolerances=BenchmarkTolerances()
        )
