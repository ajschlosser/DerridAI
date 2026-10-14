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

"""Structured JSON repair and cutoff classification.

Malformed-but-complete model JSON is repaired locally so a usable generation does
not spend another model turn.  Incomplete/token-limited output is never repaired
into apparently complete data.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app import structured_json as sj


def test_parse_json_object_accepts_valid_object():
    assert sj.parse_json_object('{"answer": 1}') == {"answer": 1}


def test_parse_json_object_repairs_malformed_complete_json():
    raw = '{"answer": 1, "items": ["a", "b",],}'
    parsed = sj.parse_json_object(raw)
    result = sj.parse_json_object_result(raw)
    assert parsed == {"answer": 1, "items": ["a", "b"]}
    assert result.value == parsed
    assert result.repaired is True


def test_parse_json_object_extracts_complete_object_from_wrapped_response():
    raw = 'Model preface\n```json\n{"answer": 1}\n```\nprovider diagnostic'
    assert sj.parse_json_object(raw) == {"answer": 1}


def test_parse_json_object_does_not_repair_structurally_truncated_json(monkeypatch):
    called = False

    def fail_if_called(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("json-repair must not run on a structurally truncated answer")

    monkeypatch.setattr(sj, "repair_json", fail_if_called)
    with pytest.raises(sj.StructuredJsonTruncatedError) as error:
        sj.parse_json_object('{"answer": [1, 2')

    assert called is False
    assert error.value.kind == "truncated"
    assert error.value.truncated is True


def test_parse_json_object_honours_provider_output_limit_before_repair(monkeypatch):
    called = False

    def fail_if_called(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("json-repair must not run after a provider output-limit finish")

    monkeypatch.setattr(sj, "repair_json", fail_if_called)
    with pytest.raises(sj.StructuredJsonTruncatedError) as error:
        sj.parse_json_object('{"answer": 1}', finish_reason="length")

    assert called is False
    assert error.value.finish_reason == "length"
    assert sj.finish_reason_is_truncated("max_new_tokens") is True


def test_parse_json_object_rejects_non_object_garbage_as_malformed():
    with pytest.raises(sj.StructuredJsonMalformedError) as error:
        sj.parse_json_object("not JSON")

    assert error.value.kind == "malformed"
    assert error.value.truncated is False


def test_parse_json_object_requires_top_level_object():
    with pytest.raises(sj.StructuredJsonMalformedError):
        sj.parse_json_object("[1, 2, 3]")

    with pytest.raises(sj.StructuredJsonMalformedError):
        sj.parse_json_object('[{"answer": 1}]')
