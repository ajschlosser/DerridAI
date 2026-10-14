# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026 Aaron John Schlosser, PhD
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.corpus_pipeline import select_source_pages
from app.models import PdfCorpusBuildCreate


def _blocks() -> list[dict]:
    return [
        {"block_id": "p1-b1", "page": 1, "text": "one"},
        {"block_id": "p2-b1", "page": 2, "text": "two"},
        {"block_id": "p3-b1", "page": 3, "text": "three"},
    ]


def _asset() -> dict:
    return {
        "pages": [{"pdf_page": 1}, {"pdf_page": 2}, {"pdf_page": 3}],
        "page_count": 3,
    }


def test_source_page_scope_filters_without_mutating_source() -> None:
    blocks = _blocks()
    selected, pages = select_source_pages(blocks, _asset(), {"pages": [3, 1]})

    assert pages == [1, 3]
    assert [block["block_id"] for block in selected] == ["p1-b1", "p3-b1"]
    assert len(blocks) == 3


def test_source_page_scope_empty_means_complete_source() -> None:
    blocks = _blocks()
    selected, pages = select_source_pages(blocks, _asset(), {"pages": []})

    assert selected is blocks
    assert pages == []


def test_source_page_scope_rejects_unknown_pages() -> None:
    with pytest.raises(ValueError, match="not available"):
        select_source_pages(_blocks(), _asset(), {"pages": [4]})


def test_build_request_normalizes_source_page_scope() -> None:
    request = PdfCorpusBuildCreate(asset_id="asset", source_scope={"pages": [3, 1, 3]})
    assert request.source_scope is not None
    assert request.source_scope.pages == [1, 3]

    with pytest.raises(ValueError, match="positive integers"):
        PdfCorpusBuildCreate(asset_id="asset", source_scope={"pages": [0]})
