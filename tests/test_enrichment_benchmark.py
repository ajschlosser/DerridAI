# Copyright 2026 Aaron John Schlosser, PhD.
"""Fixed-input identity for metadata-enrichment benchmarks."""

from __future__ import annotations

import json

import pytest

from app.enrichment_benchmark import (
    assert_enrichment_fixture_compatible,
    build_enrichment_benchmark_fixture,
)
from app.metadata_schema import default_schema


def _record(record_id: str = "r1", *, text: str = "Such genesis is impossible.") -> dict:
    return {
        "record_id": record_id,
        "record_revision": 3,
        "text": text,
        "source_document_id": "doc-1",
        "source_asset_id": "asset-1",
        "source_block_ids": [f"{record_id}-b1"],
        "source_spans": [
            {
                "block_id": f"{record_id}-b1",
                "page": 5,
                "bbox": [10, 20, 300, 80],
                "confidence": 1.0,
                "text": "must never be retained in the fixture",
            }
        ],
    }


def _fixture(*, records=None, request=None, schema=None):
    return build_enrichment_benchmark_fixture(
        fixture_id="bge-fixed",
        version=1,
        build={
            "build_id": "build-bge",
            "source_sha256": "a" * 64,
            "manifest": {
                "title": "Beyond Good and Evil",
                "document_author": "Friedrich Nietzsche",
            },
        },
        records=records or [_record()],
        schema=schema or default_schema(),
        request=request
        or {
            "provider_profile_id": "local-gemma",
            "provider": "ollama",
            "model": "gemma4:e4b-it-qat",
            "model_version": "digest-1",
            "enrichment_mode": "deep",
            "semantic_indexing": True,
            "evidence_mode": "with_value",
            "evidence_cascade_llm_enabled": False,
            "max_concurrent_requests": 1,
            "generation": {"temperature": 0.1, "num_ctx": 16384},
            "ablations": ["cross_build_learning"],
            "api_key": "SECRET",
            "base_url": "http://private-endpoint.invalid",
            "run_guidance": {"stance": "Watch for explicit negation."},
        },
        pipeline_identity={
            "pipeline_id": "corpus.metadata_enrichment.current",
            "pipeline_version": 2,
            "pipeline_hash": "pipeline-hash",
            "trace_id": "must-not-bind-a-fixture",
        },
    )


def test_fixture_retains_identity_without_source_text_or_credentials():
    fixture = _fixture()
    dumped = fixture.model_dump_json()

    assert fixture.records[0].text_sha256
    assert fixture.records[0].source_binding_sha256
    assert fixture.schema_hash == default_schema().content_hash()
    assert fixture.request_contract["run_guidance_sha256"]
    assert fixture.pipeline_identity == {
        "pipeline_id": "corpus.metadata_enrichment.current",
        "pipeline_version": 2,
        "pipeline_hash": "pipeline-hash",
    }
    assert "Such genesis is impossible." not in dumped
    assert "must never be retained in the fixture" not in dumped
    assert "Watch for explicit negation" not in dumped
    assert "SECRET" not in dumped
    assert "private-endpoint" not in dumped


def test_fixture_fingerprint_is_independent_of_record_input_order():
    left = _fixture(records=[_record("r2"), _record("r1")])
    right = _fixture(records=[_record("r1"), _record("r2")])

    assert left.fingerprint == right.fingerprint
    assert [row.record_id for row in left.records] == ["r1", "r2"]
    assert_enrichment_fixture_compatible(left, right)


@pytest.mark.parametrize(
    "changed",
    [
        "text",
        "revision",
        "schema",
        "request",
        "pipeline",
    ],
)
def test_fixture_fingerprint_changes_when_enrichment_input_identity_changes(changed):
    base = _fixture()

    if changed == "text":
        candidate = _fixture(records=[_record(text="A different proposition.")])
    elif changed == "revision":
        row = _record()
        row["record_revision"] = 4
        candidate = _fixture(records=[row])
    elif changed == "schema":
        schema = default_schema().model_copy(deep=True)
        schema.fields[0].instruction = "A benchmark-specific instruction."
        candidate = _fixture(schema=schema)
    elif changed == "request":
        request = {
            **base.request_contract,
            "provider_profile_id": "local-gemma",
            "provider": "ollama",
            "model": "gemma4:e4b-it-qat",
            "model_version": "digest-1",
            "semantic_indexing": False,
            "ablations": ["cross_build_learning"],
        }
        candidate = _fixture(request=request)
    else:
        candidate = build_enrichment_benchmark_fixture(
            fixture_id="bge-fixed",
            version=1,
            build={
                "build_id": "build-bge",
                "source_sha256": "a" * 64,
                "manifest": {
                    "title": "Beyond Good and Evil",
                    "document_author": "Friedrich Nietzsche",
                },
            },
            records=[_record()],
            schema=default_schema(),
            request={
                "provider_profile_id": "local-gemma",
                "provider": "ollama",
                "model": "gemma4:e4b-it-qat",
                "model_version": "digest-1",
                "enrichment_mode": "deep",
                "semantic_indexing": True,
                "evidence_mode": "with_value",
                "ablations": ["cross_build_learning"],
            },
            pipeline_identity={
                "pipeline_id": "corpus.metadata_enrichment.current",
                "pipeline_version": 3,
                "pipeline_hash": "different-pipeline",
            },
        )

    assert candidate.fingerprint != base.fingerprint
    with pytest.raises(ValueError, match="fingerprints match"):
        assert_enrichment_fixture_compatible(base, candidate)


def test_fixture_discloses_reproducibility_limitations_instead_of_hiding_them():
    row = _record()
    row["record_revision"] = 0
    fixture = build_enrichment_benchmark_fixture(
        fixture_id="limited",
        version=1,
        build={"build_id": "b", "manifest": {}},
        records=[row],
        schema=default_schema(),
        request={
            "provider": "ollama",
            "model": "local-model",
            "enrichment_mode": "fast",
        },
        pipeline_identity={
            "pipeline_id": "corpus.metadata_enrichment.current",
            "pipeline_version": 2,
            "pipeline_hash": "hash",
        },
    )

    limitations = json.dumps(fixture.limitations)
    assert "source SHA-256 is unavailable" in limitations
    assert "exact model revision" in limitations
    assert "no positive record_revision" in limitations
    assert "Cross-build editorial memory" in limitations
