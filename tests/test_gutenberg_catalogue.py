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

import io
import sqlite3
import tarfile
import zipfile
from pathlib import Path
from unittest.mock import patch

import httpx
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
    with sqlite3.connect(service.db_path) as db:
        db.execute(
            """
            INSERT INTO gutenberg_catalogue_books(
                etext_id,title,author,language,issued,updated_at
            ) VALUES(1342,'A Local Book','A Local Author','en','','now')
            """
        )
        db.execute(
            "UPDATE gutenberg_catalogue SET status='ready',item_count=1 WHERE id=1"
        )

    assert service.extract_catalogue() == 1
    assert service.search("Local")[0]["etext_id"] == 1342
    text, metadata = service.text(1342) or ("", {})
    assert "available offline" in text
    assert metadata["document_author"] == "A Local Author"
    with sqlite3.connect(service.db_path) as db:
        row = db.execute(
            "SELECT path,content FROM gutenberg_books WHERE etext_id=1342"
        ).fetchone()
    assert row is not None
    assert Path(row[0]).is_file()
    assert row[1] == ""


def test_catalogue_refresh_indexes_local_search_before_archive_download(tmp_path: Path):
    service = GutenbergOfflineService(
        tmp_path / "state.sqlite", tmp_path / "archive.zip", start_worker=False
    )

    class Response:
        content = (
            b"Text#,Type,Issued,Title,Language,Authors\n"
            b"1342,Text,1998-06-01,Pride and Prejudice,en,Austen Jane\n"
        )

        def raise_for_status(self):
            return None

    with patch("app.gutenberg_catalogue.httpx.get", return_value=Response()):
        state = service.refresh_catalogue()

    assert state["search_ready"] is True
    assert state["ready"] is False
    assert state["catalogue"]["item_count"] == 1
    assert service.search("Prejudice")[0]["etext_id"] == 1342


def test_first_archive_request_is_always_bounded_by_range(tmp_path: Path):
    service = GutenbergOfflineService(
        tmp_path / "state.sqlite", tmp_path / "archive.zip", start_worker=False
    )
    service.set_archive_status("start")
    seen: dict[str, str] = {}

    class Response:
        status_code = 206
        content = b"four"
        headers = {"content-range": "bytes 0-3/8"}

        def raise_for_status(self):
            return None

    def fake_get(_url, *, headers, **_kwargs):
        seen.update(headers)
        return Response()

    with patch("app.gutenberg_catalogue.httpx.get", side_effect=fake_get):
        state = service.download_chunk(chunk_size=4)

    assert seen["Range"] == "bytes=0-3"
    assert state["archive"]["bytes_done"] == 4
    assert state["archive"]["status"] == "downloading"


def test_pause_during_inflight_chunk_does_not_resurrect_download(tmp_path: Path):
    service = GutenbergOfflineService(
        tmp_path / "state.sqlite", tmp_path / "archive.zip", start_worker=False
    )
    service.set_archive_status("start")

    class Response:
        status_code = 206
        content = b"four"
        headers = {"content-range": "bytes 0-3/8"}

        def raise_for_status(self):
            return None

    def fake_get(*_args, **_kwargs):
        service.set_archive_status("pause")
        return Response()

    with patch("app.gutenberg_catalogue.httpx.get", side_effect=fake_get):
        state = service.download_chunk(chunk_size=4)

    assert state["archive"]["status"] == "paused"
    assert not service.archive_path.exists()


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


def _complete_archive(tmp_path: Path, size: int = 8):
    service = GutenbergOfflineService(
        tmp_path / "state.sqlite", tmp_path / "archive.zip", start_worker=False
    )
    service.archive_path.parent.mkdir(parents=True, exist_ok=True)
    service.archive_path.write_bytes(b"x" * size)
    return service


class _Unsatisfiable:
    status_code = 416
    content = b""
    headers: dict[str, str] = {}

    def raise_for_status(self):
        raise AssertionError("a 416 after a complete download is not an error")


class _Head:
    def __init__(self, length: int):
        self.headers = {"content-length": str(length)}

    def raise_for_status(self):
        return None


def test_resuming_a_finished_download_moves_on_instead_of_failing_with_416(tmp_path: Path):
    """Start/Resume on a complete archive used to fail: the total was forgotten and the next range was past the end.

    Why: an 11.29 GB archive fully on disk stayed in "error" with "416 Requested Range Not Satisfiable" and was never
    unpacked. The known total is now kept, and a 416 whose length matches the file marks the download complete.
    """
    service = _complete_archive(tmp_path)
    with sqlite3.connect(service.db_path) as db:
        db.execute("UPDATE gutenberg_archive SET status='paused',bytes_done=8,total_bytes=8")
    assert service.set_archive_status("resume")["archive"]["total_bytes"] == 8
    with patch("app.gutenberg_catalogue.httpx.get", return_value=_Unsatisfiable()), patch(
        "app.gutenberg_catalogue.httpx.head", return_value=_Head(8)
    ):
        state = service.download_chunk(chunk_size=4)
    assert state["archive"]["status"] == "downloaded"
    assert state["archive"]["error"] is None


def test_a_file_larger_than_the_archive_is_reported_with_the_way_out(tmp_path: Path):
    service = _complete_archive(tmp_path, size=12)
    service.set_archive_status("start")
    with patch("app.gutenberg_catalogue.httpx.get", return_value=_Unsatisfiable()), patch(
        "app.gutenberg_catalogue.httpx.head", return_value=_Head(8)
    ):
        try:
            service.download_chunk(chunk_size=4)
        except ValueError as exc:
            assert "Redownload" in str(exc)
        else:
            raise AssertionError("expected an explanation")


def test_archive_timeout_is_persisted_as_terminal_error(tmp_path: Path):
    service = GutenbergOfflineService(
        tmp_path / "state.sqlite", tmp_path / "archive.zip", start_worker=False
    )
    service.set_archive_status("start")
    with patch(
        "app.gutenberg_catalogue.httpx.get",
        side_effect=httpx.ReadTimeout("slow"),
    ):
        try:
            service.download_chunk(chunk_size=4)
        except httpx.ReadTimeout:
            pass
        else:
            raise AssertionError("timeout unexpectedly succeeded")
    state = service.status()["archive"]
    assert state["status"] == "error"
    assert "slow" in state["error"]


def test_stale_ready_archive_and_catalogue_are_not_reported_ready(tmp_path: Path):
    service = GutenbergOfflineService(
        tmp_path / "state.sqlite", tmp_path / "archive.zip", start_worker=False
    )
    with sqlite3.connect(service.db_path) as db:
        db.execute(
            "UPDATE gutenberg_archive SET status='ready',total_bytes=8,bytes_done=8"
        )
        db.execute(
            "UPDATE gutenberg_catalogue SET status='ready',item_count=1"
        )
    state = service.status()
    assert state["ready"] is False
    assert state["search_ready"] is False
