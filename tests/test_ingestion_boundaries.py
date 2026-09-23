# Copyright 2026 Aaron John Schlosser, PhD.
"""Hostile source inputs and exact media provenance at ingestion boundaries."""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import types
import zipfile
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
try:
    import chromadb  # noqa: F401
except ImportError:
    sys.modules["chromadb"] = types.SimpleNamespace()

from app import corpus_builder as cb
from app import source_audio as audio
from app import source_gutenberg as gutenberg
from app import source_safety as safety
from app.corpus_builder import PdfCorpusRepository, _image_bytes_to_pdf
from app.corpus_segmentation import _construct_records
from app.rag import _citation_strings
from app.source_media import detect_media_kind, extract_non_pdf
from app.source_text import docx_to_text, rtf_to_text
from test_0610_warbling_wombat import minimal_docx
from test_human_overrides_and_reruns import install_review_build


def archive(entries):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for name, data in entries.items():
            package.writestr(name, data)
    return output.getvalue()


@pytest.mark.parametrize(
    "data",
    [
        b"broken",
        archive({"word/document.xml": b"<bad>"}),
        archive({"word/document.xml": b'<!DOCTYPE a [<!ENTITY x "bomb">]><a>&x;</a>'}),
        archive({"word/document.xml": b"x" * 100_000}),
        archive({"word/document.xml": b"<a/>", "word/vbaProject.bin": b"code"}),
        archive(
            {
                "word/document.xml": b'<a xmlns:w="urn:w"><w:instrText>DDE cmd</w:instrText></a>'
            }
        ),
        archive(
            {
                "word/document.xml": b"<a/>",
                "word/_rels/document.xml.rels": b'<Relationships><Relationship TargetMode="External" Type="template" Target="https://evil"/></Relationships>',
            }
        ),
    ],
)
def test_docx_rejects_malformed_bombs_and_active_content(data):
    with pytest.raises(ValueError):
        docx_to_text(data)


def test_docx_text_entities_and_provenance_persist(tmp_path):
    data = minimal_docx("Title", "Author", ["A & B < C"])
    repo = PdfCorpusRepository(tmp_path)
    asset = repo.save_asset(data, filename="source.docx")
    assert (
        json.loads(repo.asset_blocks_path(asset["asset_id"]).read_text())["text"]
        == "A & B < C"
    )
    stored = json.loads(repo.asset_meta_path(asset["asset_id"]).read_text())
    assert stored["extraction_provenance"]["contract"] == "source-extraction-v2"
    assert stored["extraction_provenance"]["python"]
    assert stored["sha256"] == hashlib.sha256(data).hexdigest()


@pytest.mark.parametrize(
    "data",
    [
        b"bad",
        rb"{\rtf1 unclosed",
        rb"{\rtf1\object code}",
        rb"{\rtf1\field DDE cmd}",
        b"{\\rtf1 " + b"{" * 129 + b"}" * 130,
    ],
)
def test_rtf_rejects_malformed_resource_bombs_and_active_content(data):
    with pytest.raises(ValueError):
        rtf_to_text(data)


@pytest.mark.parametrize("kind", ["docx", "rtf", "image"])
def test_oversized_sources_fail_before_extractors(monkeypatch, tmp_path, kind):
    monkeypatch.setattr(cb, "settings", replace(cb.settings, pdf_max_upload_mb=0))
    with pytest.raises(ValueError, match="size limit"):
        PdfCorpusRepository(tmp_path).save_asset(b"payload", filename=f"source.{kind}")


def image_bytes(format="PNG", size=(2, 2)):
    output = io.BytesIO()
    Image.new("RGB", size).save(output, format=format)
    return output.getvalue()


@pytest.mark.parametrize(
    "data", [b"broken", b'<svg onload="alert(1)"/>', image_bytes("GIF")]
)
def test_images_reject_malformed_unsupported_and_active_formats(data):
    with pytest.raises(ValueError):
        _image_bytes_to_pdf(data, "source.png")


def test_image_pixel_bomb(monkeypatch):
    monkeypatch.setattr(safety, "MAX_IMAGE_PIXELS", 3)
    with pytest.raises(ValueError):
        safety.validate_image(image_bytes())


def test_supported_image_conversion():
    assert _image_bytes_to_pdf(image_bytes(), "scan.png").startswith(b"%PDF")


def test_unsupported_binary_and_extractor():
    with pytest.raises(ValueError):
        detect_media_kind("source.xyz", b"\x00\x01")
    with pytest.raises(ValueError):
        extract_non_pdf(b"text", filename="source.xyz", kind="unknown")


TRANSCRIPT = {"text": "Hello.", "segments": [{"start": 1, "end": 3, "text": "Hello."}]}


def test_audio_optional_dependency_missing(monkeypatch):
    def missing(*args):
        raise ImportError("missing")

    monkeypatch.setattr(audio.importlib, "import_module", missing)
    with pytest.raises(RuntimeError, match="not installed"):
        audio.diarize_with_whisperx(Path("audio.wav"))


@pytest.mark.parametrize(
    "failure",
    [
        FileNotFoundError(),
        subprocess.TimeoutExpired("ffprobe", 15),
        subprocess.CalledProcessError(1, "ffprobe"),
    ],
)
def test_audio_probe_dependency_codec_and_timeout(monkeypatch, failure):
    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr(audio.subprocess, "run", fail)
    with pytest.raises(ValueError):
        audio.probe_audio(Path("bad.wav"))


def test_long_audio_rejected_before_transcription(monkeypatch):
    monkeypatch.setattr(
        audio.subprocess,
        "run",
        lambda *args, **kwargs: types.SimpleNamespace(
            stdout=json.dumps(
                {
                    "format": {"duration": audio.MAX_AUDIO_SECONDS + 1},
                    "streams": [{"codec_type": "audio"}],
                }
            )
        ),
    )
    with pytest.raises(ValueError, match="duration"):
        audio.extract_audio(b"data", filename="long.wav")


@pytest.mark.parametrize(
    "payload",
    [
        {"text": ""},
        {"text": "unlocated"},
        {"segments": [{"text": "bad", "start": float("nan"), "end": 1}]},
    ],
)
def test_silence_and_unlocated_transcript_fail(payload):
    with pytest.raises(ValueError):
        audio.spans_from_transcript(payload, [])


def test_transcription_network_failure(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    path = tmp_path / "clip.wav"
    path.write_bytes(b"data")

    def fail(*args, **kwargs):
        raise httpx.ReadTimeout("timeout")

    monkeypatch.setattr(audio.httpx, "post", fail)
    with pytest.raises(ValueError, match="transcription failed"):
        audio.transcribe_entire_file(path)


def test_diarization_failure_preserves_transcript_and_timed_evidence(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(audio, "probe_audio", lambda path: 4)
    monkeypatch.setattr(audio, "transcribe_entire_file", lambda path: TRANSCRIPT)

    def fail(path):
        raise RuntimeError("diarizer failed")

    monkeypatch.setattr(audio, "diarize_with_whisperx", fail)
    repo = PdfCorpusRepository(tmp_path)
    asset = repo.save_asset(b"audio", filename="clip.wav")
    assert asset["source_transcription"] == TRANSCRIPT
    assert asset["audio_provenance"]["diarization_status"] == "failed"
    assert asset["warnings"]
    blocks = [
        json.loads(line)
        for line in repo.asset_blocks_path(asset["asset_id"]).read_text().splitlines()
    ]
    record = _construct_records(asset, blocks, [])[0]
    assert record["pdf_pages"] == [] and record["page_start"] is None
    assert record["source_spans"][0]["start"] == 1
    assert "page" not in record["source_spans"][0]
    assert "00:00:01–00:00:03" in _citation_strings(record)[0]
    with pytest.raises(ValueError, match="Page layout"):
        repo.update_page_labels(asset["asset_id"], {1: "12"})
    with pytest.raises(ValueError, match="Page layout"):
        repo.update_document_layout(asset["asset_id"], {})


def test_audio_human_correction_is_revision(tmp_path):
    repo, build = install_review_build(
        tmp_path,
        {
            "media_kind": "audio",
            "text": "Hello.",
            "source_spans": [
                {"locator_kind": "time", "start": 1, "end": 3, "speaker": "S1"}
            ],
            "pdf_pages": [],
        },
    )
    manager = cb.PdfCorpusBuildManager(repo)
    updated = manager.patch_record_text(
        build["build_id"], "r1", "Hello there.", expected_revision=1
    )
    assert updated["record_revision"] == 2
    assert updated["source_extracted_text"] == "Hello."
    assert updated["text_revision_history"][-1]["source"] == "human"
    assert updated["source_spans"][0]["speaker"] == "S1"


def catalog_transport(monkeypatch, payload, data=b"text", status=200):
    def handler(request):
        if request.url.host == "gutendex.com":
            return httpx.Response(status, json=payload)
        return httpx.Response(200, content=data)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(gutenberg.httpx, "get", client.get)
    monkeypatch.setattr(gutenberg.httpx, "stream", client.stream)


def catalog(id=12, mime="text/plain; charset=utf-8"):
    return {
        "id": id,
        "title": "Selected edition",
        "authors": [{"name": "Doe, Jane"}],
        "languages": ["en"],
        "formats": {mime: f"https://www.gutenberg.org/ebooks/{id}.txt.utf-8"},
    }


def test_gutenberg_encoding_metadata_and_exact_edition(monkeypatch, tmp_path):
    catalog_transport(
        monkeypatch, catalog(mime="text/plain; charset=iso-8859-1"), b"caf\xe9"
    )
    text, meta = gutenberg.load_gutenberg_etext(12)
    assert text == "café"
    assert meta["encoding"] == "iso-8859-1"
    assert meta["gutenberg_id"] == 12 and meta["document_author"] == "Jane Doe"
    assert meta["source_sha256"] == hashlib.sha256(b"caf\xe9").hexdigest()
    repo = PdfCorpusRepository(tmp_path)
    first = repo.save_asset(text.encode(), filename="book.txt", catalog_metadata=meta)
    second = repo.save_asset(
        text.encode(),
        filename="book.txt",
        catalog_metadata={**meta, "gutenberg_id": 13},
    )
    assert first["asset_id"] != second["asset_id"]
    assert (
        repo.get_asset(first["asset_id"])["catalog_metadata"]["source_url"]
        == meta["source_url"]
    )


@pytest.mark.parametrize(
    "payload,data",
    [
        (catalog(13), b"text"),
        ({"id": 12, "formats": {}}, b"text"),
        (catalog(), b"\xff"),
        (catalog(), b""),
    ],
)
def test_gutenberg_never_substitutes_on_identity_format_or_encoding_failure(
    monkeypatch, payload, data
):
    catalog_transport(monkeypatch, payload, data)
    with pytest.raises(ValueError):
        gutenberg.load_gutenberg_etext(12)


@pytest.mark.parametrize("status", [404, 500])
def test_gutenberg_lookup_failure_visible(monkeypatch, status):
    catalog_transport(monkeypatch, {}, status=status)
    with pytest.raises(httpx.HTTPStatusError):
        gutenberg.load_gutenberg_etext(12)


def test_gutenberg_timeout_visible(monkeypatch):
    def timeout(*args, **kwargs):
        raise httpx.ReadTimeout("timeout")

    monkeypatch.setattr(gutenberg.httpx, "get", timeout)
    with pytest.raises(httpx.ReadTimeout):
        gutenberg.search_project_gutenberg("book")


def test_gutenberg_no_results_and_multiple_editions(monkeypatch):
    catalog_transport(monkeypatch, {"results": []})
    assert gutenberg.search_project_gutenberg("missing") == []
    catalog_transport(monkeypatch, {"results": [catalog(12), catalog(13)]})
    assert [
        hit["etext_id"] for hit in gutenberg.search_project_gutenberg("edition")
    ] == [12, 13]


def test_audio_missing_credentials_and_unsupported_format(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(audio, "settings", replace(audio.settings, openai_compat_api_key=""))
    with pytest.raises(ValueError, match="API_KEY"):
        audio.transcribe_entire_file(Path("absent.wav"))
    with pytest.raises(ValueError, match="Unsupported"):
        audio.extract_audio(b"data", filename="clip.xyz")
    monkeypatch.setattr(audio, "MAX_AUDIO_BYTES", 2)
    with pytest.raises(ValueError, match="size limit"):
        audio.extract_audio(b"data", filename="clip.wav")


def test_whisper_multipart_and_segment_timestamps(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    path = tmp_path / "clip.wav"
    path.write_bytes(b"audio")
    def handle(request):
        content = request.read()
        assert b'timestamp_granularities[]' in content
        assert b'verbose_json' in content
        assert b'audio' in content
        return httpx.Response(200, json=TRANSCRIPT)
    client = httpx.Client(transport=httpx.MockTransport(handle))
    monkeypatch.setattr(audio.httpx, "post", client.post)
    assert audio.transcribe_entire_file(path) == TRANSCRIPT


def test_audio_speakers_remain_timed_in_evidence():
    blocks = audio.spans_from_transcript(TRANSCRIPT, [{"start": 0, "end": 4, "speaker": "S1"}])
    record = _construct_records({"asset_id": "a", "filename": "clip.wav", "media_kind": "audio"}, blocks, [])[0]
    assert record["source_spans"][0]["speaker"] == "S1"
    assert "[S1]" in _citation_strings(record)[0]


def test_gutenberg_rejects_wrong_download_edition_and_oversize(monkeypatch):
    payload = catalog()
    payload["formats"] = {"text/plain": "https://www.gutenberg.org/ebooks/13.txt"}
    catalog_transport(monkeypatch, payload)
    with pytest.raises(ValueError, match="selected edition"):
        gutenberg.load_gutenberg_etext(12)
    catalog_transport(monkeypatch, catalog(), b"long")
    monkeypatch.setattr(gutenberg, "MAX_SOURCE_BYTES", 2)
    with pytest.raises(ValueError, match="size limit"):
        gutenberg.load_gutenberg_etext(12)


def test_audio_manifest_rejects_physical_page_edits(tmp_path):
    repo, build = install_review_build(tmp_path, {"text": "Hello."})
    asset_path = repo.asset_meta_path(build["asset_id"])
    meta = json.loads(asset_path.read_text())
    meta["media_kind"] = "audio"
    asset_path.write_text(json.dumps(meta))
    manager = cb.PdfCorpusBuildManager(repo)
    with pytest.raises(ValueError, match="Page boundaries"):
        manager.patch_manifest(build["build_id"], {"main_text_start_page": 2})


def test_transcript_cannot_silently_drop_provider_text():
    with pytest.raises(ValueError, match="conserve"):
        audio.spans_from_transcript({**TRANSCRIPT, "text": "Hello. Missing words."}, [])


def test_png_script_metadata_is_inert_text():
    from app.source_text import png_text_metadata
    from PIL.PngImagePlugin import PngInfo

    metadata = PngInfo()
    metadata.add_text("Title", "<script>alert('inert')</script>")
    output = io.BytesIO()
    Image.new("RGB", (2, 2)).save(output, format="PNG", pnginfo=metadata)
    safety.validate_image(output.getvalue())
    assert png_text_metadata(output.getvalue())["title"] == "<script>alert('inert')</script>"
