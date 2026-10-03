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
        "semantic_function": "objection",
        "is_direct_quote": True,
        "quotation_chain": ["Derrida", "Hegel"],
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


def test_reader_profile_drops_only_the_assertion_layer(monkeypatch: pytest.MonkeyPatch) -> None:
    _, full_records, full_size = _site_records(monkeypatch)
    manifest, records, slim_size = _site_records(monkeypatch, record_profile="reader")
    record = records[0]

    assert "field_assertions" not in record and "current_field_assertions" not in record
    # Every metadata value survives unchanged: bibliographic, attribution, quotation, semantic and indexing.
    removed = set(full_records[0]) - set(record)
    assert removed == {"field_assertions", "current_field_assertions"}
    for field in set(record) - {"field_authority"}:
        assert record[field] == full_records[0][field]
    for field in ("topics", "extraction_quality", "semantic_function", "is_direct_quote", "quotation_chain"):
        assert record[field] == full_records[0][field]
    for field in ("edition", "translator", "page_start", "speaker", "quoted_speaker", "position_holder"):
        assert record[field] == full_records[0][field]
    assert slim_size < full_size

    conformance = manifest["celf_conformance"]
    assert conformance["record_profile"] == "reader"
    assert conformance["core_record"] is True
    assert conformance["field_assertions"] == "omitted"
    assert set(conformance["omitted_fields"]) == {"field_assertions", "current_field_assertions"}


def test_reader_profile_keeps_unreviewed_state_of_every_kept_value(monkeypatch: pytest.MonkeyPatch) -> None:
    _, records, _ = _site_records(monkeypatch, record_profile="reader")
    authority = records[0]["field_authority"]
    for field in ("position_holder", "topics"):
        assert authority[field]["derivation"] == "model"
        assert authority[field]["authority"] == "unreviewed"


def test_profile_never_removes_required_fields_and_rejects_unknown_profiles() -> None:
    slim = apply_record_profile([_record()], "reader")
    assert all(field in slim[0] for field in CELF_REQUIRED_RECORD_FIELDS)
    assert apply_record_profile([_record()], "complete")[0]["field_assertions"]
    with pytest.raises(ValueError):
        normalize_site_record_profile("minimal")
