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

"""Finer source-unit policies: every N sentences / paragraphs, conserving text."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app.unit_policy import apply_unit_policy, normalize_policy  # noqa: E402


def _block(i, text, page=1, **extra):
    return {"block_id": f"b{i}", "page": page, "type": "paragraph", "text": text, **extra}


def test_every_n_sentences_conserves_text():
    text = "One is here. Two is here. Three is here. Four is here. Five is here."
    out, _ = apply_unit_policy([_block(1, text)], {"mode": "sentence", "per": 2})
    assert len(out) == 3
    assert " ".join(b["text"] for b in out) == text


def test_every_n_paragraphs_merges_within_page_only():
    blocks = [_block(1, "A."), _block(2, "B."), _block(3, "C."), _block(4, "D", page=2),
              _block(5, "Nums", excluded_reason="page_number")]
    out, remap = apply_unit_policy(blocks, {"mode": "paragraph", "per": 2})
    assert [b["text"] for b in out] == ["A.\n\nB.", "C.", "D", "Nums"]
    assert remap[0] == remap[1] and out[0]["parent_block_ids"] == ["b1", "b2"]


def test_group_size_is_validated():
    assert "per" not in normalize_policy({"mode": "sentence", "per": 1})
    with pytest.raises(ValueError):
        normalize_policy({"mode": "sentence", "per": 0})
