# Copyright 2026 Aaron John Schlosser, PhD.
import io
import sqlite3
import tarfile
import zipfile
from pathlib import Path
from unittest.mock import patch

from app.gutenberg_catalogue import GutenbergOfflineService


def test_archive_state_is_resumable_without_downloading_archive(tmp_path: Path):
    service = GutenbergOfflineService(
        tmp_path / "state.sqlite", tmp_path / "archive.zip", start_worker=False
    )
    assert service.status()["search_ready"] is False
    assert service.set_archive_status("start")["archive"]["status"] == "downloading"
    assert service.set_archive_status("pause")["archive"]["status"] == "paused"
    assert service.set_archive_status("resume")["archive"]["status"] == "downloading"
    assert service.set_archive_status("refetch")["archive"]["bytes_done"] == 0


def _make_archive(path: Path) -> None:
    text = (
        b"Title: A Local Book\n"
        b"Author: A Local Author\n"
        b"\n"
        b"This text is available offline.\n"
    )
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        info = tarfile.TarInfo("1342.txt")
        info.size = len(text)
        tar.addfile(info, io.BytesIO(text))
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("txt-files.tar", tar_buffer.getvalue())


def test_streamed_archive_extraction_persists_text_and_metadata(tmp_path: Path):
    archive_path = tmp_path / "txt-files.tar.zip"
    _make_archive(archive_path)
    service = GutenbergOfflineService(
        tmp_path / "state.sqlite", archive_path, start_worker=False
    )

    assert service.extract_catalogue() == 1
    assert service.search("Local")[0]["etext_id"] == 1342
    text, metadata = service.text(1342) or ("", {})
    assert "available offline" in text
    assert metadata["document_author"] == "A Local Author"


def test_download_resume_requires_range_support(tmp_path: Path):
    service = GutenbergOfflineService(
        tmp_path / "state.sqlite", tmp_path / "archive.zip", start_worker=False
    )
    service.set_archive_status("pause")
    service.archive_path.parent.mkdir(parents=True, exist_ok=True)
    service.archive_path.write_bytes(b"partial")
    with sqlite3.connect(service.db_path) as db:
        db.execute("UPDATE gutenberg_archive SET status='downloading'")

    class Response:
        status_code = 200
        content = b"not a range response"
        headers = {"content-length": "20"}

        def raise_for_status(self):
            return None

    with patch("app.gutenberg_catalogue.httpx.get", return_value=Response()):
        try:
            service.download_chunk(chunk_size=4)
        except ValueError as exc:
            assert "range" in str(exc).lower()
        else:
            raise AssertionError("resume unexpectedly accepted an unbounded response")
