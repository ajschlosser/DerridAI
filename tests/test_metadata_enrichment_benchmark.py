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

"""Benchmark counters, legacy duplicate lookup baseline, and safe reports."""

from __future__ import annotations

import json

from app import corpus_builder as cb
from app import corpus_metadata_enrichment_execution as execution
from app.corpus_models import CORPUS_PROFILES, PROFILE_VERSION
from app.metadata_enrichment_benchmark import run_fixed_case
from app.metadata_schema import default_schema
from pydantic import BaseModel


class Answer(BaseModel):
    label: str


def test_actual_provider_attempt_characters_include_invalid_response(
    monkeypatch, tmp_path
):
    replies = iter(['{"label":', '{"label":"ok"}'])
    prompts = []

    def chat(**kwargs):
        prompts.append(kwargs["prompt"])
        return next(replies)

    monkeypatch.setattr(cb, "chat_complete", chat)
    manager = cb.PdfCorpusBuildManager(cb.PdfCorpusRepository(tmp_path / "repo"))
    counter = {}
    try:
        result = manager._chat_json(
            {
                "provider": "ollama",
                "model": "test-model",
                "_structured_call_counter": counter,
            },
            "Private prompt",
            response_model=Answer,
            attempts=2,
        )
        assert result == {"label": "ok"}
        assert counter["attempts"] == 2
        assert counter["provider_input_chars"] == sum(map(len, prompts))
        assert counter["provider_output_chars"] == len('{"label":') + len(
            '{"label":"ok"}'
        )
        assert counter["provider_responses"] == 2
        assert "Private prompt" not in json.dumps(counter)
    finally:
        manager._executor.shutdown(wait=True)


def test_legacy_exact_adjudication_is_repeated_for_same_field_snapshot(monkeypatch):
    calls = []
    monkeypatch.setattr(
        execution,
        "adjudication_suggestions",
        lambda **kwargs: calls.append(kwargs) or {},
    )
    schema = default_schema()
    record = {
        "record_id": "r1",
        "text": "Such genesis is impossible.",
        "source_block_ids": ["b1"],
    }
    execution.MetadataEnrichmentExecutionMixin()._prepare_metadata_tasks(
        record,
        {},
        {"schema_version": schema.schema_version, "families": ["discourse"]},
        dict(CORPUS_PROFILES[PROFILE_VERSION]),
        {},
        {},
        "",
        "",
        None,
        schema=schema,
    )
    # This captures the historical behavior before the collection checkpoint.
    names = [item["field"] for item in calls]
    for field in schema.fields:
        assert names.count(field.name) == 2
    measured = record["metadata_candidate_workload"]
    assert measured["adjudication_lookups"] == len(calls)
    assert measured["duplicate_adjudication_lookups"] == len(schema.fields)


def test_fixed_case_runs_real_enrichment_with_scripted_provider_and_safe_report(
    monkeypatch, tmp_path
):
    def chat(**kwargs):
        return json.dumps(
            {
                "metadata": {
                    "region_type": "main_text",
                    "primary_text": True,
                    "discourse_role": "assertion",
                },
                "field_assessments": {},
                "field_evidence": {},
            }
        )

    monkeypatch.setattr(cb, "chat_complete", chat)
    schema = default_schema()
    case = {
        "case_id": "baseline-smoke",
        "schema": schema.model_dump(mode="json"),
        "build": {"source_sha256": "a" * 64, "manifest": {}},
        "request": {
            "provider": "ollama",
            "model": "scripted",
            "api_key": "PRIVATE_KEY",
            "families": ["discourse"],
        },
        "records": [
            {
                "record_id": "r1",
                "record_revision": 1,
                "text": "PRIVATE_SOURCE",
                "source_block_ids": ["b1"],
            }
        ],
    }
    report = run_fixed_case(
        case, root=tmp_path / "isolated", baseline_commit="a7d6d553", repeats=2
    )
    assert report["result"]["record_count"] == 2
    assert report["result"]["workload"]["provider_input_chars"] > 0
    assert report["result"]["workload"]["provider_output_chars"] > 0
    assert report["result"]["workload"]["provider_output_tokens"] is None
    serialized = json.dumps(report)
    assert "PRIVATE_KEY" not in serialized
    assert "PRIVATE_SOURCE" not in serialized
