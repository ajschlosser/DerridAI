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
import sys
import types
from pathlib import Path

import fitz
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

try:
    import chromadb  # noqa: F401
except ImportError:
    sys.modules["chromadb"] = types.SimpleNamespace()

from app import corpus_builder as cb
from app import corpus_segmentation as segmentation
from app import source_audio
from app import source_media as sm
from app.field_assertions import (
    create_model_assertion,
    current_assertion_by_name,
    project_record_assertions,
)


def test_dialogue_speakers_and_record_inheritance():
    blocks, _pages = sm.prose_to_blocks(
        "ADA: The gift exceeds the economy.\n\nADA: It does so without return.",
        extraction_method="text",
    )
    assert [block["speaker"] for block in blocks] == ["ADA", "ADA"]
    records = segmentation._construct_records(
        {"filename": "seminar.txt", "asset_id": "asset"},
        blocks,
        [],
    )
    assert records[0]["speaker"] == "ADA"
    assert records[0]["metadata_field_status"]["speaker"]["method"] == "source_span_speaker"
    segmentation._apply_manifest_metadata(records[0], {"speaker": "Not Ada", "title": "Seminar"})
    assert records[0]["speaker"] == "ADA"
    assert records[0]["document_title"] == "Seminar"


def test_whisper_spans_use_whisperx_speakers_after_full_transcript():
    transcript = {
        "text": "Hello there. And good evening.",
        "language": "en",
        "segments": [
            {"start": 0.0, "end": 2.0, "text": "Hello there.", "avg_logprob": -0.2},
            {"start": 2.2, "end": 4.4, "text": "And good evening.", "avg_logprob": -0.2},
        ],
    }
    turns = [
        {"start": 0.0, "end": 2.1, "speaker": "SPEAKER_00"},
        {"start": 2.1, "end": 5.0, "speaker": "SPEAKER_01"},
    ]
    blocks = sm.spans_from_transcript(transcript, turns)
    assert [block["speaker"] for block in blocks] == ["SPEAKER_00", "SPEAKER_01"]
    assert blocks[0]["extraction_method"] == "whisper"
    meta = sm.infer_initial_metadata(transcript["text"], blocks=blocks)
    assert meta["speakers"] == ["SPEAKER_00", "SPEAKER_01"]
    assert "speaker" not in meta


def test_audio_ingest_automatically_diarizes_and_exposes_distinct_speakers(monkeypatch):
    transcript = {
        "text": "Hello there. Good evening.",
        "language": "en",
        "segments": [
            {"start": 0.0, "end": 2.0, "text": "Hello there.", "avg_logprob": -0.2},
            {"start": 2.0, "end": 4.0, "text": "Good evening.", "avg_logprob": -0.2},
        ],
    }
    diarization_calls: list[Path] = []

    monkeypatch.setattr(source_audio, "probe_audio", lambda _path: 4.0)
    monkeypatch.setattr(source_audio, "transcribe_entire_file", lambda _path: transcript)
    monkeypatch.setattr(source_audio, "tool_version", lambda _name: "test")
    monkeypatch.setattr(source_audio, "executable_version", lambda _name: "test")

    def diarize(path: Path):
        diarization_calls.append(path)
        return [
            {
                "start": 0.0,
                "end": 2.0,
                "speaker": "SPEAKER_1",
                "provider_speaker": "SPEAKER_00",
            },
            {
                "start": 2.0,
                "end": 4.0,
                "speaker": "SPEAKER_2",
                "provider_speaker": "SPEAKER_01",
            },
        ]

    monkeypatch.setattr(source_audio, "diarize_with_whisperx", diarize)

    extracted = source_audio.extract_audio(b"not-real-audio", filename="interview.wav")

    assert len(diarization_calls) == 1
    assert extracted["audio_provenance"]["diarization_status"] == "complete"
    assert extracted["initial_metadata"]["speakers"] == ["SPEAKER_1", "SPEAKER_2"]
    assert [block["speaker"] for block in extracted["blocks"]] == ["SPEAKER_1", "SPEAKER_2"]



def test_word_timestamps_split_one_whisper_segment_at_speaker_change():
    transcript = {
        "text": "Hello there, good evening.",
        "language": "en",
        "segments": [
            {
                "start": 0.0,
                "end": 4.0,
                "text": "Hello there, good evening.",
                "avg_logprob": -0.1,
            }
        ],
        "words": [
            {"start": 0.0, "end": 0.8, "word": "Hello"},
            {"start": 0.9, "end": 1.8, "word": "there,"},
            {"start": 2.1, "end": 2.8, "word": "good"},
            {"start": 2.9, "end": 3.8, "word": "evening."},
        ],
    }
    turns = source_audio.normalize_speaker_labels(
        [
            {"start": 0.0, "end": 2.0, "speaker": "voice-a"},
            {"start": 2.0, "end": 4.0, "speaker": "voice-b"},
        ]
    )

    blocks = source_audio.spans_from_transcript(transcript, turns)

    assert [block["text"] for block in blocks] == ["Hello there,", "good evening."]
    assert [block["speaker"] for block in blocks] == ["SPEAKER_1", "SPEAKER_2"]
    assert all(
        block["speaker_assignment"]["method"] == "word_overlap" for block in blocks
    )
    assert all(
        block["extraction_method"] == "whisper+word-speaker-alignment"
        for block in blocks
    )
    assert " ".join(block["text"] for block in blocks) == transcript["text"]


def test_word_speaker_assignment_marks_close_overlap_for_review():
    transcript = {
        "text": "Crossing",
        "language": "en",
        "segments": [{"start": 0.0, "end": 1.0, "text": "Crossing"}],
        "words": [{"start": 0.0, "end": 1.0, "word": "Crossing"}],
    }
    turns = source_audio.normalize_speaker_labels(
        [
            {"start": 0.0, "end": 0.55, "speaker": "voice-a"},
            {"start": 0.45, "end": 1.0, "speaker": "voice-b"},
        ]
    )

    blocks = source_audio.spans_from_transcript(transcript, turns)

    assert len(blocks) == 1
    assignment = blocks[0]["speaker_assignment"]
    assert assignment["ambiguous_word_count"] == 1
    assert assignment["review_recommended"] is True
    assert blocks[0]["source_words"][0]["speaker_ambiguous"] is True


def test_provider_words_skip_whisperx_forced_alignment():
    transcript = {
        "text": "Hello.",
        "language": "en",
        "segments": [{"start": 0.0, "end": 1.0, "text": "Hello."}],
        "words": [{"start": 0.0, "end": 1.0, "word": "Hello."}],
    }

    aligned, status = source_audio.align_transcript_with_whisperx(
        Path("unused.wav"), transcript
    )

    assert aligned is transcript
    assert status == "provider_word_timestamps"


def test_diarized_speaker_changes_are_deterministic_record_boundaries():
    blocks = [
        {
            "block_id": "audio-1",
            "text": "First voice.",
            "type": "paragraph",
            "speaker": "SPEAKER_1",
        },
        {
            "block_id": "audio-2",
            "text": "Second voice.",
            "type": "paragraph",
            "speaker": "SPEAKER_2",
        },
    ]

    candidates = segmentation._deterministic_boundary_candidates(blocks, {}, "en")

    assert len(candidates) == 1
    assert "speaker_change" in candidates[0]["signals"]
    assert segmentation._candidate_route(candidates[0], {}) == "split"


def test_audio_voice_labels_start_at_one_and_reviewed_names_project_to_records():
    turns = source_audio.normalize_speaker_labels(
        [
            {"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"},
            {"start": 1.0, "end": 2.0, "speaker": "voice-b"},
            {"start": 2.0, "end": 3.0, "speaker": "SPEAKER_00"},
        ]
    )
    assert [turn["speaker"] for turn in turns] == ["SPEAKER_1", "SPEAKER_2", "SPEAKER_1"]
    assert turns[0]["provider_speaker"] == "SPEAKER_00"

    blocks, _pages = sm.prose_to_blocks("One.\n\nTwo.", extraction_method="whisper")
    for block in blocks:
        block["speaker"] = "SPEAKER_1"
        block["start"] = 0.0
        block["end"] = 1.0
    records = segmentation._construct_records(
        {
            "filename": "seminar.mp3",
            "asset_id": "asset",
            "media_kind": "audio",
            "voice_assignments": {
                "SPEAKER_1": {"voice_id": "SPEAKER_1", "display_name": "Jacques Derrida"}
            },
        },
        blocks,
        [],
    )
    assert records[0]["speaker"] == "Jacques Derrida"
    assert records[0]["source_spans"][0]["speaker"] == "SPEAKER_1"
    assert records[0]["source_spans"][0]["resolved_speaker"] == "Jacques Derrida"
    assert records[0]["metadata_field_status"]["speaker"]["method"] == "human_voice_assignment"
    assertion = current_assertion_by_name(records[0], "speaker")
    assert assertion is not None
    assert assertion.derivation_method == "human"
    assert assertion.authority_status == "human_override"

    # A later enrichment worker may propose another identity, but the reviewed
    # diarization assignment remains authoritative.
    worker = json.loads(json.dumps(records[0]))
    create_model_assertion(worker, "speaker", "Model guess", confidence=0.91)
    project_record_assertions(worker)
    merged = cb._merge_enrichment_snapshot(records[0], worker)
    assert merged["speaker"] == "Jacques Derrida"
    merged_assertion = current_assertion_by_name(merged, "speaker")
    assert merged_assertion is not None
    assert merged_assertion.authority_status == "human_override"


def test_voice_assignments_are_reviewed_asset_state_not_block_rewrites(tmp_path: Path):
    repo = cb.PdfCorpusRepository(tmp_path)
    asset_id = "pdf-audio"
    repo.asset_meta_path(asset_id).write_text(
        json.dumps({"asset_id": asset_id, "filename": "seminar.mp3", "media_kind": "audio"}),
        encoding="utf-8",
    )
    original = {"block_id": "p00001-b0001", "text": "Hello", "speaker": "SPEAKER_1"}
    repo.asset_blocks_path(asset_id).write_text(json.dumps(original) + "\n", encoding="utf-8")

    updated = repo.update_voice_assignments(
        asset_id, {"SPEAKER_1": "Jacques Derrida"}, reviewer="reviewer"
    )

    assert updated["voice_assignments"]["SPEAKER_1"]["display_name"] == "Jacques Derrida"
    assert repo.load_blocks(asset_id) == [original]
    with pytest.raises(ValueError, match="Unknown diarized voice"):
        repo.update_voice_assignments(asset_id, {"SPEAKER_2": "Other"})


def test_initial_metadata_uses_deterministic_language_detection_when_missing():
    text = "the cat and the dog went to the market with a friend of the family " * 5
    meta = sm.infer_initial_metadata(text, blocks=[])
    assert meta["language"] == "en"
    assert meta["field_provenance"]["language"] == {
        "method": "nlp:stopword_frequency",
        "confidence": 0.68,
        "derivation": "nlp_derived",
        "reason": "Deterministic language signal from bounded function-word frequency.",
    }


def test_high_confidence_ingest_metadata_overrides_blank_manifest_fields():
    result = sm.apply_deterministic_ingest_metadata(
        {"title": None, "document_author": "Catalog Guess"},
        {"deterministic_checked_at": "t", "initial_metadata": {
            "title": "Of Hospitality",
            "document_author": "Jacques Derrida",
            "field_provenance": {
                "title": {"method": "labeled_line", "confidence": 0.9},
                "document_author": {"method": "labeled_line", "confidence": 0.9},
            },
        }},
    )
    assert result["title"] == "Of Hospitality"
    assert result["document_author"] == "Jacques Derrida"


def test_illegibility_forces_ocr_and_zero_preserves_native_text(monkeypatch, tmp_path: Path):
    assert sm.native_text_ocr_threshold(0) == 24
    assert sm.native_text_ocr_threshold(100) >= 10**8
    calls: list[int] = []

    def boom(self, *args, **kwargs):
        calls.append(1)
        raise RuntimeError("no-ocr")

    monkeypatch.setattr(fitz.Page, "get_textpage_ocr", boom)
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "A complete native text layer for this page.")
    data = doc.tobytes()
    doc.close()
    repo = cb.PdfCorpusRepository(tmp_path)
    legible = repo.save_asset(data, filename="legible.pdf", source_illegibility=0)
    assert calls == []
    assert legible["media_kind"] == "pdf"
    illegible = repo.save_asset(data, filename="illegible.pdf", source_illegibility=100)
    assert calls
    assert any("OCR unavailable" in warning for warning in illegible["warnings"])
    assert illegible["deterministic_checked_at"]


def test_url_scheme_is_http_only():
    try:
        sm.fetch_source_url("file:///tmp/secret.txt", max_bytes=1000)
    except ValueError as exc:
        assert "http" in str(exc)
    else:
        raise AssertionError("file URLs must be rejected")
