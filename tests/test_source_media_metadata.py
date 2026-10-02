from __future__ import annotations

import sys
import types
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

try:
    import chromadb  # noqa: F401
except ImportError:
    sys.modules["chromadb"] = types.SimpleNamespace()

from app import corpus_builder as cb
from app import corpus_segmentation as segmentation
from app import source_media as sm


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
