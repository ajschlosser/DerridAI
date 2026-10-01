# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import base64
import io
import json
import zipfile
from typing import Any

import pytest
from app import site_publication
from app.field_assertions import create_model_assertion
from app.site_record_profile import (
    CELF_REQUIRED_RECORD_FIELDS,
    apply_record_profile,
    normalize_site_record_profile,
)


def _record(record_id: str = "r1") -> dict[str, Any]:
    record: dict[str, Any] = {
        "record_id": record_id,
        "source_document_id": "source-1",
        "source_spans": [
            {"source_document_id": "source-1", "source_unit_id": f"u-{record_id}", "printed_page": "12"}
        ],
        "work": "Glas",
        "document_author": "Jacques Derrida",
        "edition": "Galilée, 1974",
        "translator": "John P. Leavey",
        "citation": "Derrida, Jacques. Glas.",
        "page_start": 12,
        "speaker": "Derrida",
        "quoted_speaker": "Hegel",
        "position_holder": "Hegel",
        "topics": ["sublation", "family"],
        "extraction_quality": 0.91,
        "text": "A publication-safe passage.",
    }
    # An unreviewed model assertion: exactly what must not read as settled once assertions are omitted.
    create_model_assertion(record, "position_holder", "Hegel", confidence=0.7, reason="x" * 400)
    create_model_assertion(record, "topics", ["sublation", "family"], confidence=0.8, reason="y" * 400)
    return record


def _site_records(monkeypatch: pytest.MonkeyPatch, **options: Any) -> tuple[dict, list[dict], int]:
    filter_fields = options.pop("filter_fields", ["work"])
    monkeypatch.setattr(
        site_publication.store,
        "export_site_projection",
        lambda store_name, works: {
            "store": {"name": store_name, "filter_fields": filter_fields},
            "records": [{"record": _record("r1"), "embedding": None}],
        },
    )
    bundle = site_publication.build_site_bundle(
        store_name="derrida", works=["Glas"], title="Site", **options
    )
    with zipfile.ZipFile(io.BytesIO(bundle.payload)) as archive:
        runtime = archive.read("derridai-site.js").decode("utf-8")
    payload = runtime[len(f"globalThis.{site_publication.PACKAGE_GLOBAL}=") :].split(";\n", 1)[0]
    package = json.loads(payload)
    records = json.loads(base64.b64decode(package["chunks"][0]["records_b64"]))
    return package["manifest"], records, len(bundle.payload)


def test_default_profile_is_complete_and_keeps_field_assertions(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest, records, _ = _site_records(monkeypatch)
    assert records[0]["field_assertions"]
    assert manifest["celf_conformance"]["record_profile"] == "complete"
    assert manifest["celf_conformance"]["field_assertions"] == "retained"
    assert manifest["celf_conformance"]["core_record"] is True


def test_reader_profile_drops_assertions_but_keeps_core_citation_and_attribution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, full_records, full_size = _site_records(monkeypatch)
    manifest, records, slim_size = _site_records(monkeypatch, record_profile="reader")
    record = records[0]

    assert "field_assertions" not in record and "current_field_assertions" not in record
    assert "extraction_quality" not in record and "topics" not in record
    for field in CELF_REQUIRED_RECORD_FIELDS:
        assert record[field] == full_records[0][field]
    # Edition, translation, page and the three separate attribution fields survive unflattened.
    for field in ("edition", "translator", "page_start", "citation", "speaker", "quoted_speaker", "position_holder"):
        assert record[field] == full_records[0][field]
    assert slim_size < full_size

    conformance = manifest["celf_conformance"]
    assert conformance["record_profile"] == "reader"
    assert conformance["core_record"] is True
    assert conformance["field_assertions"] == "omitted"
    assert "field_assertions" in conformance["omitted_fields"]


def test_reader_profile_keeps_unreviewed_state_of_attribution_values(monkeypatch: pytest.MonkeyPatch) -> None:
    _, records, _ = _site_records(monkeypatch, record_profile="reader")
    authority = records[0]["field_authority"]
    assert authority["position_holder"]["derivation"] == "model"
    assert authority["position_holder"]["authority"] == "unreviewed"
    # Only attribution fields are summarized; indexing fields that were dropped leave no trace to misread.
    assert "topics" not in authority


def test_reader_profile_keeps_collection_filter_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    _, records, _ = _site_records(monkeypatch, record_profile="reader", filter_fields=["work", "topics"])
    assert records[0]["topics"] == ["sublation", "family"]


def test_profile_never_removes_required_fields_and_rejects_unknown_profiles() -> None:
    slim = apply_record_profile([_record()], "reader")
    assert all(field in slim[0] for field in CELF_REQUIRED_RECORD_FIELDS)
    assert apply_record_profile([_record()], "complete")[0]["field_assertions"]
    with pytest.raises(ValueError):
        normalize_site_record_profile("minimal")
