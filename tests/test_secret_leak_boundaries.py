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

import json

from app.corpus_publication import serialize_public_record
from app.pipelines.trace_safety import sanitize_trace_value
from app.system_store import SystemStore


def _serialized(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def test_secret_canary_is_absent_from_public_config_trace_and_publication() -> None:
    secret = "secret-canary-nfr003-7f80a9"

    public_profile = SystemStore._public_profile(
        {
            "id": "provider-1",
            "name": "Provider",
            "type": "openai",
            "base_url": "https://example.invalid/v1",
            "model": "example",
            "api_key": secret,
        }
    )
    assert public_profile["has_api_key"] is True
    assert secret not in _serialized(public_profile)
    assert "api_key" not in public_profile

    trace = sanitize_trace_value(
        {
            "provider": "provider-1",
            "api_key": secret,
            "nested": {
                "authorization": secret,
                "refresh_token": secret,
                "safe": "kept",
            },
        }
    )
    assert secret not in _serialized(trace)
    assert trace["api_key"] == "[redacted]"
    assert trace["nested"]["authorization"] == "[redacted]"
    assert trace["nested"]["refresh_token"] == "[redacted]"
    assert trace["nested"]["safe"] == "kept"

    publication = serialize_public_record(
        {
            "record_id": "r1",
            "source_document_id": "doc1",
            "text": "A scholarly passage.",
            "source_spans": [
                {
                    "source_document_id": "doc1",
                    "source_unit_id": "u1",
                }
            ],
            "openai_api_key": secret,
            "provider_runtime": {
                "client_secret": secret,
                "session-token": secret,
                "safe_label": "kept",
            },
            "legacy_metadata": {
                "access_token": secret,
                "safe_note": "kept",
            },
            "token_count": 12,
        }
    )
    encoded_publication = _serialized(publication)
    assert secret not in encoded_publication
    assert "openai_api_key" not in encoded_publication
    assert "client_secret" not in encoded_publication
    assert "session-token" not in encoded_publication
    assert "access_token" not in encoded_publication
    assert publication["token_count"] == 12
