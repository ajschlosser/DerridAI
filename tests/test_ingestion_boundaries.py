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

"""Hostile source inputs and exact media provenance at ingestion boundaries."""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import threading
import types
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from xml.sax.saxutils import escape

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
from test_human_overrides_and_reruns import install_review_build


def test_slow_source_extraction_does_not_block_other_repository_work(tmp_path, monkeypatch):
    repo, build = install_review_build(tmp_path, {"text": "Reviewed source."})
    record = repo.load_records(build["build_id"])[0]
    extracting = threading.Event()
    release = threading.Event()
    original = repo._extract_for_ingest

    def extract(data, **kwargs):
        if data == b"Slow source.":
            extracting.set()
            assert release.wait(10)
        return original(data, **kwargs)

    monkeypatch.setattr(repo, "_extract_for_ingest", extract)
    with ThreadPoolExecutor(max_workers=2) as pool:
        slow = pool.submit(repo.save_asset, b"Slow source.", filename="slow.txt")
        try:
            assert extracting.wait(5)
            updated = {**record, "text": "Corrected source.", "record_revision": 2}
            write = pool.submit(repo.update_record, build["build_id"], updated)
            committed = write.result(timeout=5)
            assert committed["text"] == "Corrected source."
            restarted = PdfCorpusRepository(repo.root)
            assert restarted.load_records(build["build_id"])[0]["text"] == "Corrected source."
        finally:
            release.set()
        assert slow.result(timeout=5)["asset_id"]


def test_identical_source_imports_share_extraction(tmp_path, monkeypatch):
    repo = PdfCorpusRepository(tmp_path / "corpus")
    extracting = threading.Event()
    release = threading.Event()
    original = repo._extract_for_ingest
    calls = []

    def extract(data, **kwargs):
        calls.append(data)
        extracting.set()
        assert release.wait(10)
        return original(data, **kwargs)

    monkeypatch.setattr(repo, "_extract_for_ingest", extract)
    with ThreadPoolExecutor(max_workers=4) as pool:
        first = pool.submit(repo.save_asset, b"Same source.", filename="same.txt")
        try:
            assert extracting.wait(5)
            followers = [
                pool.submit(repo.save_asset, b"Same source.", filename="same.txt")
                for _ in range(3)
            ]
        finally:
            release.set()
        assets = [first.result(timeout=5), *(future.result(timeout=5) for future in followers)]
    assert len(calls) == 1
    assert all(asset == assets[0] for asset in assets)
    asset_id = assets[0]["asset_id"]
    assert repo.asset_content_path(asset_id, ".txt").read_bytes() == b"Same source."
    assert "".join(block["text"] for block in repo.load_blocks(asset_id)) == "Same source."


def test_failed_source_extraction_releases_admission_without_publishing(tmp_path, monkeypatch):
    repo = PdfCorpusRepository(tmp_path / "corpus")
    original = repo._extract_for_ingest

    def fail(*args, **kwargs):
        raise ValueError("Extraction failed")

    monkeypatch.setattr(repo, "_extract_for_ingest", fail)
    with pytest.raises(ValueError, match="Extraction failed"):
        repo.save_asset(b"Retry source.", filename="retry.txt")
    assert not list((repo.root / "assets").iterdir())
    monkeypatch.setattr(repo, "_extract_for_ingest", original)
    with ThreadPoolExecutor(max_workers=1) as pool:
        asset = pool.submit(repo.save_asset, b"Retry source.", filename="retry.txt").result(timeout=5)
    loaded = repo.get_asset(asset["asset_id"])
    assert all(loaded[key] == value for key, value in asset.items())


def test_source_publication_rechecks_an_asset_created_during_extraction(tmp_path, monkeypatch):
    repo = PdfCorpusRepository(tmp_path / "corpus")
    other = PdfCorpusRepository(repo.root)
    original = repo._extract_for_ingest
    winner = {}

    def extract(data, **kwargs):
        winner.update(other.save_asset(data, filename="winner.txt"))
        return original(data, **kwargs)

    monkeypatch.setattr(repo, "_extract_for_ingest", extract)
    asset = repo.save_asset(b"Shared source.", filename="later.txt")
    assert asset == winner
    assert asset["filename"] == "winner.txt"
    assert repo.asset_content_path(asset["asset_id"], ".txt").read_bytes() == b"Shared source."


def test_staged_source_io_does_not_reserve_canonical_writer(tmp_path, monkeypatch):
    repo, build = install_review_build(tmp_path, {"text": "Reviewed source."})
    staging = threading.Event()
    release = threading.Event()
    original = repo._stage_asset

    def stage(*args):
        staging.set()
        assert release.wait(10)
        return original(*args)

    monkeypatch.setattr(repo, "_stage_asset", stage)
    with ThreadPoolExecutor(max_workers=2) as pool:
        source = pool.submit(repo.save_asset, b"Staged source.", filename="staged.txt")
        try:
            assert staging.wait(5)
            record = repo.get_record(build["build_id"], "r1")
            record["text"] = "Canonical correction."
            committed = pool.submit(repo.update_record, build["build_id"], record).result(timeout=5)
            assert committed["text"] == "Canonical correction."
        finally:
            release.set()
        asset = source.result(timeout=5)
    restarted = PdfCorpusRepository(repo.root)
    assert restarted.get_asset(asset["asset_id"])["extraction_provenance"] == asset["extraction_provenance"]
    assert restarted.asset_content_path(asset["asset_id"], ".txt").read_bytes() == b"Staged source."
    assert not list((repo.root / "assets").glob(".ingest-*"))


@pytest.mark.parametrize("failure", ["staging", "blocks", "meta"])
def test_source_staging_or_publication_failure_is_retryable(tmp_path, monkeypatch, failure):
    repo = PdfCorpusRepository(tmp_path / "corpus")
    original_stage = repo._stage_asset
    original_replace = cb.os.replace

    def stage(staged, *args):
        original_stage(staged, *args)
        if failure == "staging":
            raise OSError("injected source failure")

    def replace(source, target):
        source = Path(source)
        if source.parent.name.startswith(".ingest-") and source.name == failure:
            raise OSError("injected source failure")
        return original_replace(source, target)

    monkeypatch.setattr(repo, "_stage_asset", stage)
    monkeypatch.setattr(cb.os, "replace", replace)
    with pytest.raises(OSError, match="injected source failure"):
        repo.save_asset(b"Durable source.", filename="durable.txt")
    assert not list((repo.root / "assets").iterdir())
    monkeypatch.setattr(cb.os, "replace", original_replace)
    restarted = PdfCorpusRepository(repo.root)
    asset = restarted.save_asset(b"Durable source.", filename="durable.txt")
    assert restarted.load_blocks(asset["asset_id"])[0]["text"] == "Durable source."


def test_staging_rechecks_winner_and_discards_private_artifacts(tmp_path, monkeypatch):
    repo = PdfCorpusRepository(tmp_path / "corpus")
    other = PdfCorpusRepository(repo.root)
    original = repo._stage_asset
    winner = {}

    def stage(*args):
        original(*args)
        winner.update(other.save_asset(b"Winner source.", filename="winner.txt"))

    monkeypatch.setattr(repo, "_stage_asset", stage)
    assert repo.save_asset(b"Winner source.", filename="loser.txt") == winner
    assert not list((repo.root / "assets").glob(".ingest-*"))
    assert other.get_asset(winner["asset_id"])["filename"] == "winner.txt"


def test_checkpoint_io_is_build_scoped_and_deletion_cannot_resurrect(tmp_path, monkeypatch):
    repo, build = install_review_build(tmp_path, {"text": "Reviewed source."})
    second = repo.create_build({"asset_id": build["asset_id"]})
    writing = threading.Event()
    release = threading.Event()
    original = cb._json_write

    def write(path, payload):
        if path == repo.build_checkpoint_path(build["build_id"], "slow"):
            writing.set()
            assert release.wait(10)
        return original(path, payload)

    monkeypatch.setattr(cb, "_json_write", write)
    with ThreadPoolExecutor(max_workers=3) as pool:
        checkpoint = pool.submit(repo.save_checkpoint, build["build_id"], "slow", {"version": 1})
        try:
            assert writing.wait(5)
            pool.submit(repo.save_checkpoint, second["build_id"], "fast", {"version": 2}).result(timeout=5)
            record = repo.get_record(build["build_id"], "r1")
            record["text"] = "New authoritative text."
            committed = pool.submit(repo.update_record, build["build_id"], record).result(timeout=5)
            assert committed["text"] == "New authoritative text."
            deletion = pool.submit(repo.delete_build_files, build["build_id"])
            assert not deletion.done()
        finally:
            release.set()
        checkpoint.result(timeout=5)
        deletion.result(timeout=5)
    assert not repo.build_path(build["build_id"]).parent.exists()
    with pytest.raises(KeyError):
        repo.save_checkpoint(build["build_id"], "slow", {"version": 3})
    assert PdfCorpusRepository(repo.root).load_checkpoint(second["build_id"], "fast") == {"version": 2}


def test_checkpoint_failure_releases_build_admission(tmp_path, monkeypatch):
    repo, build = install_review_build(tmp_path, {"text": "Reviewed source."})
    bid = build["build_id"]
    repo.save_checkpoint(bid, "resume", {"version": 1})
    original = cb._json_write

    def fail(path, payload):
        if path == repo.build_checkpoint_path(bid, "resume"):
            raise OSError("checkpoint failure")
        return original(path, payload)

    monkeypatch.setattr(cb, "_json_write", fail)
    with pytest.raises(OSError, match="checkpoint failure"):
        repo.save_checkpoint(bid, "resume", {"version": 2})
    assert repo.load_checkpoint(bid, "resume") == {"version": 1}
    monkeypatch.setattr(cb, "_json_write", original)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(repo.save_checkpoint, bid, "resume", {"version": 3}).result(timeout=5)
    assert PdfCorpusRepository(repo.root).load_checkpoint(bid, "resume") == {"version": 3}


def test_restart_ignores_unpublished_source_artifacts_and_retries(tmp_path, monkeypatch):
    repo = PdfCorpusRepository(tmp_path / "corpus")
    original = repo._stage_asset
    captured = {}

    def stage(staged, data, blocks, meta):
        original(staged, data, blocks, meta)
        captured.update(meta)
        raise OSError("interrupted")

    monkeypatch.setattr(repo, "_stage_asset", stage)
    with pytest.raises(OSError, match="interrupted"):
        repo.save_asset(b"Recovery source.", filename="recovery.txt")
    # Simulate process death after content rename but before the metadata marker.
    repo.asset_content_path(captured["asset_id"], ".txt").write_bytes(b"Recovery source.")
    orphan = repo.root / "assets" / ".ingest-interrupted"
    orphan.mkdir()
    (orphan / "meta").write_text(json.dumps(captured), encoding="utf-8")
    restarted = PdfCorpusRepository(repo.root)
    assert restarted.list_assets() == []
    with pytest.raises(KeyError):
        restarted.get_asset(captured["asset_id"])
    asset = restarted.save_asset(b"Recovery source.", filename="recovery.txt")
    assert restarted.load_blocks(asset["asset_id"])[0]["text"] == "Recovery source."
    assert restarted.get_asset(asset["asset_id"])["sha256"] == captured["sha256"]


def minimal_docx(title: str, author: str, paragraphs: list[str]) -> bytes:
    """Build the smallest DOCX fixture needed by ingestion-boundary tests."""
    body = "".join(
        f"<w:p><w:r><w:t>{escape(paragraph)}</w:t></w:r></w:p>"
        for paragraph in paragraphs
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    core = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f"<dc:title>{escape(title)}</dc:title>"
        f"<dc:creator>{escape(author)}</dc:creator>"
        "</cp:coreProperties>"
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as package:
        package.writestr("word/document.xml", document)
        package.writestr("docProps/core.xml", core)
    return output.getvalue()


def archive(entries):
    """Build deterministic ZIP fixtures for xdist collection.

    zipfile.writestr(name, data) stamps members with the current local time.
    These archives are created at module import time inside parametrization, so
    parallel pytest workers can otherwise collect different binary parameter
    IDs when they cross a ZIP timestamp boundary.
    """
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for name, data in entries.items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            package.writestr(info, data)
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
    # The Corpus Builder setup summary reads the probed duration from the stored asset.
    assert asset["audio_provenance"]["duration_seconds"] == 4
    assert repo.list_assets()[0]["audio_provenance"]["duration_seconds"] == 4
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
    from app import system_store as store_module

    monkeypatch.setattr(store_module, "app_settings", replace(store_module.app_settings, openai_compat_api_key=""))
    store_module.system_store.set_audio_transcription_settings(
        base_url="https://api.openai.com/v1", model="whisper-1", clear_key=True
    )
    with pytest.raises(ValueError, match="API key"):
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
