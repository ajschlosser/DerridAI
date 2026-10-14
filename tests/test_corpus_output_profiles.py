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

"""Research-output projection tests for the headless corpus CLI."""

from __future__ import annotations

import json

import zstandard as zstd
from app.corpus_output_profiles import (
    project_research_record,
    write_research_jsonl_zst,
)
from app.metadata_schema import default_schema


def _record() -> dict:
    return {
        "record_id": "rec-1",
        "text": "Derrida discusses a position.",
        "source_document_id": "doc-1",
        "source_spans": [{"source_document_id": "doc-1", "page_start": 12, "page_end": 12}],
        "work": "Example Work",
        "document_author": "Jacques Derrida",
        "speaker": "Derrida",
        "position_holder": "Heidegger",
        "stance": "questioning",
        "topics": ["being"],
        "needs_review": True,
        "review_reason": "internal workflow state",
        "field_assertions": [{"assertion_id": "a-1"}],
        "document_intelligence": {"entities": ["ignored"]},
        "metadata_execution_ledger": {"ignored": True},
    }


def test_research_projection_is_allow_listed_from_schema_and_document_metadata():
    schema = default_schema()

    projected = project_research_record(_record(), schema)

    assert projected["record_id"] == "rec-1"
    assert projected["text"].startswith("Derrida")
    assert projected["source_document_id"] == "doc-1"
    assert projected["source_spans"][0]["page_start"] == 12
    assert projected["work"] == "Example Work"
    assert projected["speaker"] == "Derrida"
    assert projected["position_holder"] == "Heidegger"
    assert projected["topics"] == ["being"]
    assert "needs_review" not in projected
    assert "review_reason" not in projected
    assert "field_assertions" not in projected
    assert "document_intelligence" not in projected
    assert "metadata_execution_ledger" not in projected


def test_research_writer_is_atomic_zstd_jsonl_with_archive_hash(tmp_path):
    schema = default_schema()
    target = tmp_path / "research.jsonl.zst"

    result = write_research_jsonl_zst(target, [_record()], schema=schema)

    assert result.record_count == 1
    assert result.compressed_bytes == target.stat().st_size
    assert len(result.archive_sha256) == 64

    with target.open("rb") as handle:
        with zstd.ZstdDecompressor().stream_reader(handle) as reader:
            payload = json.loads(reader.read().decode("utf-8").strip())

    assert payload["record_id"] == "rec-1"
    assert payload["position_holder"] == "Heidegger"
    assert "field_assertions" not in payload
