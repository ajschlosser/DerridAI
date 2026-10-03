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

import pytest
from app import corpus_builder as cb
from app.corpus_manifest_workflow import _validated_document_metadata
from app.corpus_segmentation import source_unit_record_boundaries
from app.models import PdfCorpusBuildCreate


def test_topology_policy_accepts_fixed_sourceunit_groups_and_record_pages():
    request = PdfCorpusBuildCreate(
        asset_id="asset-1",
        topology_policy={
            "mode": "source_units",
            "source_units_per_record": 2,
            "records_per_page": 4,
        },
    )
    assert request.topology_policy.mode == "source_units"
    assert request.topology_policy.source_units_per_record == 2
    assert request.topology_policy.records_per_page == 4


@pytest.mark.parametrize(
    ("field", "value"),
    [("source_units_per_record", 0), ("source_units_per_record", 101), ("records_per_page", 0)],
)
def test_topology_policy_rejects_invalid_group_sizes(field: str, value: int):
    policy = {"mode": "source_units", "source_units_per_record": 1, "records_per_page": None}
    policy[field] = value
    with pytest.raises(ValueError):
        PdfCorpusBuildCreate(asset_id="asset-1", topology_policy=policy)


def test_sourceunit_record_boundaries_split_after_each_fixed_group():
    blocks = [{"block_id": f"u{index}"} for index in range(1, 8)]
    boundaries = source_unit_record_boundaries(blocks, 2)
    assert [item["after_block_id"] for item in boundaries] == ["u2", "u4", "u6"]
    assert all(item["source"] == "source_unit_policy" for item in boundaries)
    assert all(item["semantic_boundary"] is False for item in boundaries)


def test_synthetic_record_pages_apply_only_when_source_pagination_is_not_authoritative():
    text_asset = {
        "media_kind": "text",
        "page_number_detection": {"status": "estimated"},
    }
    pdf_asset = {
        "media_kind": "pdf",
        "page_number_detection": {"status": "detected"},
    }
    assert cb._can_use_synthetic_record_pages(text_asset) is True
    assert cb._can_use_synthetic_record_pages(pdf_asset) is False

    records = [{"record_id": f"r{index}"} for index in range(1, 6)]
    cb._apply_synthetic_record_pages(records, 2)
    assert [record["page_start"] for record in records] == [1, 1, 2, 2, 3]
    assert [record["page_end"] for record in records] == [1, 1, 2, 2, 3]
    assert all(record["page_number_source"] == "record_grouping" for record in records)


def test_prebuild_manifest_can_explicitly_clear_a_detected_value():
    validated = _validated_document_metadata({"title": None, "document_author": "  Derrida  "})
    assert validated["title"] is None
    assert validated["document_author"] == "Derrida"
