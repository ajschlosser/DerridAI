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

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import corpus_segmentation as seg  # noqa: E402
from app import source_audio  # noqa: E402
from app.routers import system as system_routes  # noqa: E402
from app.system_store import system_store  # noqa: E402


def _admin_request():
    return SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(role="admin", username="root")), headers={}, cookies={})


def test_key_is_stored_server_side_and_never_returned(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    saved = system_store.set_audio_transcription_settings(
        base_url="https://api.example.org/v1/", model="whisper-2", api_key="sk-secret",
    )
    assert saved["has_key"] and saved["key_source"] == "settings" and "api_key" not in saved
    assert saved["base_url"] == "https://api.example.org/v1"
    assert system_store.audio_transcription_settings(include_key=True)["api_key"] == "sk-secret"
    # Omitting the key keeps it; clear_key removes it.
    system_store.set_audio_transcription_settings(base_url="https://api.example.org/v1", model="whisper-2")
    assert system_store.audio_transcription_settings(include_key=True)["api_key"] == "sk-secret"
    cleared = system_store.set_audio_transcription_settings(base_url="https://api.example.org/v1", model="whisper-2", clear_key=True)
    assert cleared["key_source"] in {"none", "environment"}


def test_transcription_uses_the_settings_key_and_explains_a_missing_one(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    system_store.set_audio_transcription_settings(base_url="https://x.test/v1", model="m", clear_key=True)
    with pytest.raises(ValueError, match="Settings"):
        source_audio.transcribe_entire_file(tmp_path / "a.wav")


def test_transcription_requests_segment_and_word_timestamps(monkeypatch, tmp_path):
    system_store.set_audio_transcription_settings(
        base_url="https://x.test/v1",
        model="whisper-test",
        api_key="sk-test",
    )
    path = tmp_path / "a.wav"
    path.write_bytes(b"audio")
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "text": "Hello.",
                "segments": [{"start": 0.0, "end": 1.0, "text": "Hello."}],
                "words": [{"start": 0.0, "end": 1.0, "word": "Hello."}],
            }

    def post(url, **kwargs):
        captured["url"] = url
        captured["data"] = kwargs["data"]
        return Response()

    monkeypatch.setattr(source_audio.httpx, "post", post)

    source_audio.transcribe_entire_file(path)

    assert captured["url"] == "https://x.test/v1/audio/transcriptions"
    assert captured["data"]["timestamp_granularities[]"] == ["segment", "word"]


def test_settings_route_rejects_bad_urls():
    from app.models import SystemAudioTranscriptionUpdate

    body = SystemAudioTranscriptionUpdate(base_url="ftp://nope.example", model="m")
    with pytest.raises(Exception) as info:
        system_routes.update_audio_transcription(body, _admin_request())
    assert getattr(info.value, "status_code", None) == 422


def test_records_over_the_absolute_ceiling_warn_instead_of_failing_the_topology():
    policy = {"preferred_record_chars": 100, "record_length_tolerance": 10, "long_record_chars": 150, "absolute_record_chars": 200}
    records = [{"record_id": "r1", "text": "x" * 500, "text_length": 500, "source_block_ids": ["b1"]}]
    blocks = [{"block_id": "b1", "text": "x" * 500}]
    result = seg._topology_sanity(records, policy, blocks)
    assert result["valid"] is True
    finding = next(f for f in result["findings"] if f["code"] == "topology.over_absolute_limit")
    assert finding["severity"] == "warning" and finding["record_id"] == "r1"
