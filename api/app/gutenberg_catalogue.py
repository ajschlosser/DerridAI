# Copyright 2026 Aaron John Schlosser, PhD.
"""Durable offline Project Gutenberg catalogue and archive bookkeeping."""
from __future__ import annotations

import re
import sqlite3
import json
import threading
import zipfile
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from .config import settings

CATALOGUE_URL = "https://www.gutenberg.org/ebooks/offline_catalogs.html"
ARCHIVE_URL = "https://www.gutenberg.org/cache/epub/feeds/txt-files.tar.zip"
CHUNK_SIZE = 8 * 1024 * 1024


def _now() -> str:
    return datetime.now(UTC).isoformat()


class GutenbergOfflineService:
    def __init__(
        self,
        db_path: str | Path | None = None,
        archive_path: str | Path | None = None,
        *,
        start_worker: bool = True,
    ):
        self.db_path = Path(db_path or settings.system_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.archive_path = Path(archive_path or getattr(settings, "gutenberg_archive_path", "/data/gutenberg/txt-files.tar.zip"))
        self._worker: threading.Thread | None = None
        self._stop = threading.Event()
        self._start_worker_enabled = start_worker
        self._init()

    def _init(self) -> None:
        with sqlite3.connect(self.db_path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS gutenberg_catalogue (
                id INTEGER PRIMARY KEY CHECK (id=1), source_url TEXT NOT NULL,
                refreshed_at TEXT, item_count INTEGER NOT NULL DEFAULT 0,
                payload_json TEXT NOT NULL DEFAULT '[]', status TEXT NOT NULL DEFAULT 'never',
                error TEXT)""")
            db.execute("""CREATE TABLE IF NOT EXISTS gutenberg_archive (
                id INTEGER PRIMARY KEY CHECK (id=1), url TEXT NOT NULL, path TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'not_started', bytes_done INTEGER NOT NULL DEFAULT 0,
                total_bytes INTEGER, updated_at TEXT NOT NULL, error TEXT)""")
            db.execute("""CREATE TABLE IF NOT EXISTS gutenberg_books (
                etext_id INTEGER PRIMARY KEY, title TEXT NOT NULL DEFAULT '',
                author TEXT NOT NULL DEFAULT '', language TEXT NOT NULL DEFAULT '',
                path TEXT NOT NULL, content TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL)""")
            columns = {row[1] for row in db.execute("PRAGMA table_info(gutenberg_books)")}
            if "content" not in columns:
                db.execute("ALTER TABLE gutenberg_books ADD COLUMN content TEXT NOT NULL DEFAULT ''")
            db.execute("INSERT OR IGNORE INTO gutenberg_catalogue(id,source_url) VALUES(1,?)", (CATALOGUE_URL,))
            db.execute("INSERT OR IGNORE INTO gutenberg_archive(id,url,path,updated_at) VALUES(1,?,?,?)", (ARCHIVE_URL,str(self.archive_path),_now()))

    def status(self) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            catalogue = dict(db.execute("SELECT * FROM gutenberg_catalogue WHERE id=1").fetchone())
            archive = dict(db.execute("SELECT * FROM gutenberg_archive WHERE id=1").fetchone())
        archive["ready"] = archive["status"] == "complete" and Path(archive["path"]).is_file()
        search_ready = catalogue["status"] == "ready" and archive["ready"]
        return {"catalogue": catalogue, "archive": archive, "ready": archive["ready"], "search_ready": search_ready}

    def refresh_catalogue(self) -> dict[str, Any]:
        try:
            response = httpx.get(CATALOGUE_URL, timeout=30.0, follow_redirects=True)
            response.raise_for_status()
            links = sorted(set(re.findall(r'href=["\']([^"\']+\.(?:zip|csv|json))["\']', response.text, re.I)))
            with sqlite3.connect(self.db_path) as db:
                db.execute("UPDATE gutenberg_catalogue SET refreshed_at=?,item_count=?,payload_json=?,status='ready',error=NULL WHERE id=1",
                           (_now(), len(links), json.dumps(links)))
        except (httpx.HTTPError, OSError, ValueError) as exc:
            with sqlite3.connect(self.db_path) as db:
                db.execute("UPDATE gutenberg_catalogue SET status='error',error=? WHERE id=1", (str(exc),))
            raise
        return self.status()

    def set_archive_status(self, action: str) -> dict[str, Any]:
        action = action.lower()
        allowed = {"start": "downloading", "resume": "downloading", "pause": "paused", "refetch": "not_started"}
        if action not in allowed:
            raise ValueError("Unsupported archive action.")
        if action in {"pause", "refetch"}:
            self._stop.set()
        if action == "refetch":
            self.archive_path.unlink(missing_ok=True)
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE gutenberg_archive SET status=?,bytes_done=?,total_bytes=NULL,error=NULL,updated_at=? WHERE id=1",
                       (allowed[action], 0 if action == "refetch" else self._bytes_done(), _now()))
        if action in {"start", "resume"} and self._start_worker_enabled:
            self._start_worker()
        elif action == "pause":
            self._stop.set()
        return self.status()

    def _start_worker(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._stop.clear()
        self._worker = threading.Thread(target=self._run_worker, name="gutenberg-archive", daemon=True)
        self._worker.start()

    def _run_worker(self) -> None:
        try:
            while not self._stop.is_set() and self.status()["archive"]["status"] == "downloading":
                state = self.download_chunk()
                if state["archive"]["status"] == "complete":
                    self.extract_catalogue()
                    break
        except Exception as exc:
            with sqlite3.connect(self.db_path) as db:
                db.execute("UPDATE gutenberg_archive SET status='error',error=?,updated_at=? WHERE id=1", (str(exc), _now()))

    def extract_catalogue(self) -> int:
        if not self.archive_path.is_file():
            raise ValueError("Gutenberg archive is missing.")
        count = 0
        with zipfile.ZipFile(self.archive_path) as outer:
            tar_name = next((name for name in outer.namelist() if name.lower().endswith(".tar")), None)
            if not tar_name:
                raise ValueError("Gutenberg archive does not contain a tar payload.")
            with outer.open(tar_name, "r") as tar_stream, tarfile.open(
                fileobj=tar_stream, mode="r|*"
            ) as archive, sqlite3.connect(self.db_path) as db:
                for info in archive:
                    match = re.search(r"(?:^|/)(\d+)\.txt$", info.name, re.I)
                    if not match or not info.isfile() or info.size > 5_000_000:
                        continue
                    extracted = archive.extractfile(info)
                    if extracted is None:
                        continue
                    text = extracted.read().decode("utf-8", errors="replace")
                    title = re.search(r"(?im)^title:\s*(.+)$", text)
                    author = re.search(r"(?im)^author:\s*(.+)$", text)
                    db.execute("INSERT OR REPLACE INTO gutenberg_books VALUES(?,?,?,?,?,?,?)",
                               (int(match.group(1)), (title.group(1).strip() if title else ""),
                                (author.group(1).strip() if author else ""), "", info.name, text, _now()))
                    count += 1
        return count

    def search(self, query: str, limit: int = 12) -> list[dict[str, Any]]:
        term = f"%{str(query or '').strip()}%"
        with sqlite3.connect(self.db_path) as db:
            rows = db.execute("SELECT etext_id,title,author,language FROM gutenberg_books WHERE title LIKE ? OR author LIKE ? ORDER BY etext_id LIMIT ?",
                              (term, term, max(1, min(30, int(limit))))).fetchall()
        return [{"etext_id": row[0], "title": row[1], "author": row[2], "language": row[3]} for row in rows]

    def text(self, etext_id: int) -> tuple[str, dict[str, Any]] | None:
        with sqlite3.connect(self.db_path) as db:
            row = db.execute(
                "SELECT title,author,language,content FROM gutenberg_books WHERE etext_id=?",
                (int(etext_id),),
            ).fetchone()
        if not row or not row[3]:
            return None
        return row[3], {
            "gutenberg_id": int(etext_id),
            "title": row[0],
            "document_author": row[1],
            "language": row[2],
            "publisher": "Project Gutenberg",
            "document_type": "book",
            "edition": f"Project Gutenberg eBook #{int(etext_id)}",
            "source_url": f"https://www.gutenberg.org/ebooks/{int(etext_id)}",
            "retrieved_at": _now(),
        }

    def _bytes_done(self) -> int:
        return self.archive_path.stat().st_size if self.archive_path.is_file() else 0

    def download_chunk(self, chunk_size: int = CHUNK_SIZE) -> dict[str, Any]:
        state = self.status()["archive"]
        if state["status"] != "downloading":
            raise ValueError("Archive is not running; start or resume it first.")
        offset = self._bytes_done()
        headers = {"Range": f"bytes={offset}-{offset + min(chunk_size, CHUNK_SIZE) - 1}"} if offset else {}
        response = httpx.get(ARCHIVE_URL, headers=headers, timeout=60.0, follow_redirects=True)
        response.raise_for_status()
        if offset and response.status_code != 206:
            raise ValueError("Gutenberg server did not honor the resume range request.")
        if len(response.content) > min(chunk_size, CHUNK_SIZE):
            raise ValueError("Gutenberg archive response exceeded the bounded chunk size.")
        self.archive_path.parent.mkdir(parents=True, exist_ok=True)
        with self.archive_path.open("ab" if offset else "wb") as handle:
            handle.write(response.content)
        content_range = response.headers.get("content-range", "")
        total_text = content_range.rsplit("/", 1)[-1] if "/" in content_range else response.headers.get("content-length", "0")
        total = int(total_text or 0)
        done = self._bytes_done()
        status = "complete" if total and done >= total else "downloading"
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE gutenberg_archive SET status=?,bytes_done=?,total_bytes=?,updated_at=? WHERE id=1", (status,done,total or None,_now()))
        return self.status()


gutenberg_offline = GutenbergOfflineService()
