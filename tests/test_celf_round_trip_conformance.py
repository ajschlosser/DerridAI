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

from copy import deepcopy

from app.derridai_ledger import iter_jsonl_zst, write_jsonl_zst


def _identity(record: dict) -> dict:
    return deepcopy(record)


def _revision(revision: int) -> dict:
    evidence = [
        {
            "source_document_id": "doc-glas",
            "source_unit_id": f"unit-{revision}",
            "quote": "Il n'y a pas de hors-texte.",
        }
    ]
    first_id = f"speaker-model-r{revision}"
    current_id = f"speaker-reviewed-r{revision}"
    return {
        "record_id": "record-stable-1",
        "record_revision": revision,
        "source_document_id": "doc-glas",
        "text": "Il n'y a pas de hors-texte.",
        "source_spans": [
            {
                "source_document_id": "doc-glas",
                "source_unit_id": f"unit-{revision}",
            }
        ],
        "speaker": "Derrida",
        "field_assertions": {
            "schema-field-speaker": [
                {
                    "assertion_id": first_id,
                    "record_id": "record-stable-1",
                    "record_revision": revision,
                    "field_id": "schema-field-speaker",
                    "field_name": "speaker",
                    "value": "Derrida",
                    "derivation_method": "model",
                    "evaluation_status": "value_supported",
                    "authority_status": "unreviewed",
                    "value_status": "present",
                    "confidence": 0.91,
                    "evidence": evidence,
                },
                {
                    "assertion_id": current_id,
                    "record_id": "record-stable-1",
                    "record_revision": revision,
                    "field_id": "schema-field-speaker",
                    "field_name": "speaker",
                    "value": "Derrida",
                    "derivation_method": "model",
                    "evaluation_status": "value_supported",
                    "authority_status": "human_confirmed",
                    "value_status": "present",
                    "confidence": 0.91,
                    "evidence": evidence,
                    "supersedes_assertion_id": first_id,
                },
            ]
        },
        "current_field_assertions": {
            "schema-field-speaker": current_id,
        },
    }


def test_celf_ledger_round_trip_preserves_scholarly_identity_and_revision_semantics(
    tmp_path,
) -> None:
    path = tmp_path / "round-trip.jsonl.zst"
    source = [_revision(3), _revision(4)]

    result = write_jsonl_zst(path, source, serialize_record=_identity)
    restored = list(iter_jsonl_zst(path, rehydrate_evidence=True))

    assert result.record_count == 2
    assert [(row["record_id"], row["record_revision"]) for row in restored] == [
        ("record-stable-1", 3),
        ("record-stable-1", 4),
    ]
    assert [row["source_document_id"] for row in restored] == ["doc-glas", "doc-glas"]

    for original, round_tripped in zip(source, restored, strict=True):
        field_id = "schema-field-speaker"
        selected_id = original["current_field_assertions"][field_id]
        assert round_tripped["current_field_assertions"][field_id] == selected_id
        assertions = round_tripped["field_assertions"][field_id]
        assert [item["assertion_id"] for item in assertions] == [
            f"speaker-model-r{original['record_revision']}",
            selected_id,
        ]
        assert all(item["field_id"] == field_id for item in assertions)
        assert assertions[-1]["supersedes_assertion_id"] == assertions[0]["assertion_id"]
        assert assertions[-1]["authority_status"] == "human_confirmed"
        assert assertions[-1]["evaluation_status"] == "value_supported"
        assert assertions[-1]["value_status"] == "present"
        assert assertions[-1]["evidence"] == assertions[0]["evidence"]
        assert round_tripped["speaker"] == "Derrida"
