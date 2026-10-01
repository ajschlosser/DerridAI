# Copyright 2026 Aaron John Schlosser, PhD.
"""Immutable input identity for reproducible metadata-enrichment benchmarks.

The fixture is deliberately descriptive rather than authoritative. It fingerprints
the Record text/revision/source bindings, schema, prompt-affecting request controls,
provider/model identity, and enrichment pipeline without retaining source text,
credentials, endpoints, or prompt bodies.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from .evidence_suggestions import evidence_cascade_llm_enabled, evidence_mode
from .metadata_schema import MetadataSchema


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _text_hash(value: Any) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _json_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_value(item) for item in value]
    return value


class EnrichmentBenchmarkRecordIdentity(BaseModel):
    record_id: str = Field(min_length=1, max_length=240)
    record_revision: int = Field(default=0, ge=0)
    text_sha256: str = Field(min_length=64, max_length=64)
    source_binding_sha256: str = Field(min_length=64, max_length=64)
    source_block_ids: list[str] = Field(default_factory=list)


class EnrichmentBenchmarkFixture(BaseModel):
    fixture_id: str = Field(min_length=1, max_length=160)
    version: int = Field(default=1, ge=1)
    fingerprint: str = Field(min_length=64, max_length=64)
    created_at: datetime
    source_build_id: str | None = None
    source_sha256: str | None = None
    schema_id: str
    schema_version: str
    schema_hash: str
    manifest_sha256: str = Field(min_length=64, max_length=64)
    records: list[EnrichmentBenchmarkRecordIdentity] = Field(min_length=1)
    request_contract: dict[str, Any]
    provider_identity: dict[str, Any]
    pipeline_identity: dict[str, Any]
    limitations: list[str] = Field(default_factory=list)


def _source_binding(record: dict[str, Any]) -> dict[str, Any]:
    safe_spans: list[dict[str, Any]] = []
    for raw in record.get("source_spans") or []:
        if not isinstance(raw, dict):
            continue
        safe_spans.append(
            {
                key: raw.get(key)
                for key in (
                    "block_id",
                    "page",
                    "printed_page_label",
                    "bbox",
                    "confidence",
                    "extraction_method",
                )
                if raw.get(key) is not None
            }
        )
    return {
        "source_document_id": record.get("source_document_id"),
        "source_asset_id": record.get("source_asset_id"),
        "source_block_ids": [str(value) for value in record.get("source_block_ids") or []],
        "source_spans": safe_spans,
    }


def _record_identity(record: dict[str, Any]) -> EnrichmentBenchmarkRecordIdentity:
    return EnrichmentBenchmarkRecordIdentity(
        record_id=str(record.get("record_id") or ""),
        record_revision=max(0, int(record.get("record_revision") or 0)),
        text_sha256=_text_hash(record.get("text")),
        source_binding_sha256=_canonical_hash(_source_binding(record)),
        source_block_ids=[str(value) for value in record.get("source_block_ids") or []],
    )


def _request_contract(request: dict[str, Any]) -> dict[str, Any]:
    """Retain prompt/execution controls, never credentials or provider endpoints."""
    contract: dict[str, Any] = {
        "enrichment_mode": str(
            request.get("enrichment_mode")
            if "enrichment_mode" in request
            else "deep"
        ),
        "semantic_indexing": bool(request.get("semantic_indexing")),
        "evidence_mode": evidence_mode(request),
        "evidence_cascade_llm_enabled": evidence_cascade_llm_enabled(request),
        "max_concurrent_requests": max(
            1, min(16, int(request.get("max_concurrent_requests") or 1))
        ),
    }
    for key in (
        "generation",
        "stage_limits",
        "stage_timeouts",
        "families",
        "ablations",
        "model_version",
        "llm_touchup_during_enrichment",
    ):
        if key in request:
            contract[key] = _json_value(request[key])
    if isinstance(request.get("run_guidance"), dict) and request["run_guidance"]:
        contract["run_guidance_sha256"] = _canonical_hash(request["run_guidance"])
    return contract


def _provider_identity(request: dict[str, Any]) -> dict[str, Any]:
    identity: dict[str, Any] = {
        "provider_profile_id": request.get("provider_profile_id"),
        "provider": request.get("provider"),
        "model": request.get("model"),
        "model_version": request.get("model_version"),
    }
    reviewer = request.get("_review_provider")
    if isinstance(reviewer, dict) and reviewer:
        identity["review"] = {
            "provider_profile_id": (
                request.get("review_provider_profile_id")
                or reviewer.get("provider_profile_id")
            ),
            "provider": reviewer.get("provider"),
            "model": reviewer.get("model"),
            "model_version": reviewer.get("model_version"),
        }
    return identity


def build_enrichment_benchmark_fixture(
    *,
    fixture_id: str,
    version: int,
    build: dict[str, Any],
    records: list[dict[str, Any]],
    schema: MetadataSchema,
    request: dict[str, Any],
    pipeline_identity: dict[str, Any],
) -> EnrichmentBenchmarkFixture:
    """Freeze non-secret enrichment input identity without retaining source text."""
    if not records:
        raise ValueError("An enrichment benchmark fixture needs at least one Record.")

    record_rows = sorted(
        (_record_identity(record) for record in records),
        key=lambda item: item.record_id.casefold(),
    )
    request_contract = _request_contract(request)
    provider_identity = _provider_identity(request)
    pipeline = {
        key: pipeline_identity.get(key)
        for key in ("pipeline_id", "pipeline_version", "pipeline_hash")
        if pipeline_identity.get(key) is not None
    }
    manifest_sha256 = _canonical_hash(build.get("manifest") or {})
    source_sha256 = str(build.get("source_sha256") or "") or None

    limitations: list[str] = []
    if not source_sha256:
        limitations.append(
            "The source SHA-256 is unavailable; source-file identity cannot be independently verified."
        )
    if not provider_identity.get("model_version"):
        limitations.append(
            "The provider did not expose an exact model revision; reproducibility is limited to the retained model name."
        )
    missing_revisions = [
        item.record_id for item, raw in zip(record_rows, sorted(records, key=lambda row: str(row.get("record_id") or "").casefold()))
        if not raw.get("record_revision")
    ]
    if missing_revisions:
        limitations.append(
            f"{len(missing_revisions)} Record(s) have no positive record_revision."
        )
    if "cross_build_learning" not in set(request_contract.get("ablations") or []):
        limitations.append(
            "Cross-build editorial memory is enabled but not fingerprinted by this fixture; the isolated runner must freeze or disable it."
        )

    fingerprint_payload = {
        "source_sha256": source_sha256,
        "schema": {
            "id": schema.id,
            "version": schema.schema_version,
            "hash": schema.content_hash(),
        },
        "manifest_sha256": manifest_sha256,
        "records": [item.model_dump(mode="json") for item in record_rows],
        "request_contract": request_contract,
        "provider_identity": provider_identity,
        "pipeline_identity": pipeline,
    }
    return EnrichmentBenchmarkFixture(
        fixture_id=fixture_id,
        version=version,
        fingerprint=_canonical_hash(fingerprint_payload),
        created_at=datetime.now(UTC),
        source_build_id=str(build.get("build_id") or "") or None,
        source_sha256=source_sha256,
        schema_id=schema.id,
        schema_version=schema.schema_version,
        schema_hash=schema.content_hash(),
        manifest_sha256=manifest_sha256,
        records=record_rows,
        request_contract=request_contract,
        provider_identity=provider_identity,
        pipeline_identity=pipeline,
        limitations=limitations,
    )


def assert_enrichment_fixture_compatible(
    left: EnrichmentBenchmarkFixture,
    right: EnrichmentBenchmarkFixture,
) -> None:
    """Reject an A/B comparison whose fixed enrichment inputs differ."""
    if left.fingerprint != right.fingerprint:
        raise ValueError(
            "Enrichment benchmark fixtures differ in Record/schema/configuration identity; "
            "compare runs only when their fixture fingerprints match."
        )
