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

"""Isolated fixed-case execution of the historical metadata enrichment path.

Caller configuration must isolate system/Chroma stores before importing this
module. This runner never opens a user's corpus repository or retains prompts.
"""

from __future__ import annotations

import copy
import json
import platform
import time
from pathlib import Path
from typing import Any

from .config import APP_VERSION
from .corpus_builder import PdfCorpusBuildManager, PdfCorpusRepository
from .enrichment_benchmark import build_enrichment_benchmark_fixture
from .enrichment_benchmark_result import build_enrichment_benchmark_result
from .enrichment_ledger import RECORD_RUN
from .enrichment_metrics import _model_metrics
from .metadata_schema import MetadataSchema
from .pipelines.corpus_metadata_enrichment import EnrichmentSession


class _BenchmarkManager(PdfCorpusBuildManager):
    def __init__(self, root: Path, schema: MetadataSchema) -> None:
        super().__init__(PdfCorpusRepository(root), max_workers=1)
        self.benchmark_schema = schema

    def _schema_for(self, build_id: str) -> MetadataSchema:
        return self.benchmark_schema


def run_fixed_case(
    case: dict[str, Any], *, root: Path, baseline_commit: str, repeats: int = 1
) -> dict[str, Any]:
    """Use real providers, fresh record copies and an empty isolated memory store.

    Timing covers enrichment/reconciliation and local JSON persistence, not job
    queue admission. Frozen reviewed memory is intentionally a later benchmark
    profile; this first reproducible profile measures memory-disabled enrichment.
    """
    if repeats < 1 or not baseline_commit.strip():
        raise ValueError("A positive repeat count and baseline commit are required.")
    schema = MetadataSchema.model_validate(case["schema"])
    records = case["records"]
    if not records or len({item["record_id"] for item in records}) != len(records):
        raise ValueError("Benchmark records must have unique, non-empty identities.")
    request = copy.deepcopy(case["request"])
    request["ablations"] = sorted(
        set(request.get("ablations") or [])
        | {
            "cross_build_learning",
            "reviewer_conventions",
            "rejection_memory",
        }
    )
    identity = EnrichmentSession.open().identity()
    if (identity["pipeline_id"], identity["pipeline_version"]) != (
        "corpus.metadata_enrichment.current",
        2,
    ):
        raise ValueError("Baseline requires corpus.metadata_enrichment.current@2.")
    build = case.get("build") or {}
    fixture = build_enrichment_benchmark_fixture(
        fixture_id=str(case["case_id"]),
        version=int(case.get("version") or 1),
        build=build,
        records=records,
        schema=schema,
        request=request,
        pipeline_identity=identity,
    )
    manager = _BenchmarkManager(root, schema)
    workload: dict[str, Any] = {
        "repeats": repeats,
        "adjudication_lookups": 0,
        "duplicate_adjudication_lookups": 0,
        "retrieval_calls": 0,
        "provider_input_tokens": None,
        "provider_output_tokens": None,
    }
    model = str(request.get("model") or "")
    try:
        for repeat in range(repeats):
            for original in records:
                started = time.perf_counter()
                record = manager._enrich_record(
                    copy.deepcopy(original),
                    copy.deepcopy(build.get("manifest") or {}),
                    {**request, "run_id": f"benchmark-{repeat}"},
                )
                (root / "benchmark-record.json").write_text(
                    json.dumps(record, ensure_ascii=False), encoding="utf-8"
                )
                manager._ledger.append(
                    RECORD_RUN,
                    model=model,
                    field="",
                    record_id=str(original["record_id"]),
                    run_id=f"benchmark-{repeat}",
                    elapsed_ms=(time.perf_counter() - started) * 1000,
                )
                measured = record.get("metadata_candidate_workload") or {}
                for key in ("adjudication_lookups", "duplicate_adjudication_lookups"):
                    workload[key] += int(measured.get(key) or 0)
        events = manager._ledger.events()
        calls = [event for event in events if event["kind"] == "call"]
        for key in (
            "provider_input_chars",
            "provider_output_chars",
            "provider_responses",
        ):
            workload[key] = sum(int(event.get(key) or 0) for event in calls)
        workload["failed_family_calls"] = sum(not event.get("ok") for event in calls)
        result = build_enrichment_benchmark_result(
            result_id=f"{case['case_id']}-baseline",
            arm="historical",
            fixture=fixture,
            app_version=APP_VERSION,
            model_metrics=_model_metrics(events),
            workload=workload,
        )
        result.limitations.extend(
            [
                "Memory-disabled profile; retrieval speed and reviewer quality are not measured.",
                "Wall clock covers direct enrichment and local JSON persistence, excluding job admission.",
                "Provider token usage is unavailable; character counts include retries and malformed responses.",
            ]
        )
        return {
            "baseline_commit": baseline_commit,
            "environment": {
                "python": platform.python_version(),
                "platform": platform.system(),
            },
            "fixture": fixture.model_dump(mode="json"),
            "result": result.model_dump(mode="json"),
        }
    finally:
        manager._executor.shutdown(wait=True, cancel_futures=True)
