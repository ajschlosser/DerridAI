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

"""Durable offline Project Gutenberg catalogue and archive bookkeeping."""
from __future__ import annotations

import csv
import hashlib
import io
import re
import shutil
import sqlite3
import tarfile
import threading
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from . import operation_events
from .config import settings
from .source_identity import PersonName, fold, normalize_languages

CATALOGUE_URL = "https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv"
ARCHIVE_URL = "https://www.gutenberg.org/cache/epub/feeds/txt-files.tar.zip"
# Bound each network request so a reset loses at most one modest chunk rather
# than forcing a multi-gigabyte connection to remain healthy for hours.
CHUNK_SIZE = 32 * 1024 * 1024
_MAX_RETRY_DELAY_SECONDS = 60
_CONTENT_RANGE_RE = re.compile(r"^bytes\s+(\d+)-(\d+)/(\d+|\*)$", re.I)


def _now() -> str:
    return datetime.now(UTC).isoformat()


# pg_catalog.csv "Authors": "Nietzsche, Friedrich Wilhelm, 1844-1900; Common, Thomas, 1850-1919 [Translator]".
# An entry without a bracketed role is an author; a bracketed role we do not map stays "contributor", never author.
_ROLE_MAP = {"translator": "translator", "editor": "editor", "compiler": "editor"}
_DATES = re.compile(r",\s*(?:(\d{1,4})\??\s*(BCE)?)?\s*-\s*(?:(\d{1,4})\??\s*(BCE)?)?\s*$")
CONTRIBUTOR_PARSER_VERSION = 1
_ARCHIVE_TEXT_MEMBER = re.compile(
    r"(?:^|/)(\d+)/pg\1(?:\.txt(?:\.utf-?8)?)$",
    re.I,
)
_LEGACY_ARCHIVE_TEXT_MEMBER = re.compile(r"(?:^|/)(\d+)\.txt$", re.I)


def _archive_etext_id(name: str) -> int | None:
    """Return the eText id for a Gutenberg bulk-text archive member.

    The current feed mirrors cache/epub/<id>/pg<id>.txt. The flat <id>.txt
    form remains accepted for older local/test archives.
    """
    match = _ARCHIVE_TEXT_MEMBER.search(str(name or ""))
    if match:
        return int(match.group(1))
    legacy = _LEGACY_ARCHIVE_TEXT_MEMBER.search(str(name or ""))
    return int(legacy.group(1)) if legacy else None


def parse_gutenberg_contributors(raw: str) -> list[dict[str, Any]]:
    """Split the catalogue's Authors cell into contributor rows without inventing roles or dates."""
    rows: list[dict[str, Any]] = []
    for position, part in enumerate(p.strip() for p in str(raw or "").split(";")):
        if not part:
            continue
        role_match = re.search(r"\[([^\]]+)\]\s*$", part)
        raw_role = role_match.group(1).strip() if role_match else ""
        name = part[: role_match.start()].strip() if role_match else part
        birth = death = None
        dates = _DATES.search(name)
        if dates:
            birth = int(dates.group(1)) * (-1 if dates.group(2) else 1) if dates.group(1) else None
            death = int(dates.group(3)) * (-1 if dates.group(4) else 1) if dates.group(3) else None
            name = name[: dates.start()].strip()
        parsed = PersonName.parse(name)
        rows.append({
            "position": position,
            "name": name,
            "normalized_name": parsed.full,
            "surname_key": parsed.surname,
            "given_key": parsed.first_given,
            "role": _ROLE_MAP.get(raw_role.lower(), "contributor") if raw_role else "author",
            "raw_role": raw_role,
            "birth_year": birth,
            "death_year": death,
        })
    return rows


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
        # The downloaded archive is disposable transport. The installed collection lives in
        # its own SQLite file so the system database does not grow by tens of gigabytes.
        self.library_db_path = self.archive_path.parent / "gutenberg.sqlite3"
        self.staging_library_db_path = self.archive_path.parent / "gutenberg.sqlite3.next"
        self._worker: threading.Thread | None = None
        self._catalogue_worker: threading.Thread | None = None
        self._stop = threading.Event()
        self._start_worker_enabled = start_worker
        self.extract_root = self.archive_path.parent / "texts"
        self._init()
        if self._start_worker_enabled:
            state = self.status()
            if state["archive"]["status"] in {"downloading", "downloaded", "unpacking", "complete"}:
                # Durable state outlives the browser and the API process. Resume the
                # worker from the persisted byte offset or extraction phase.
                self._start_worker()
            if state["catalogue"]["status"] in {"refreshing", "indexing"}:
                self._start_catalogue_worker()

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
                total_bytes INTEGER, updated_at TEXT NOT NULL, error TEXT,
                etag TEXT, last_modified TEXT, retry_count INTEGER NOT NULL DEFAULT 0,
                next_retry_at TEXT)""")
            archive_columns = {
                row[1] for row in db.execute("PRAGMA table_info(gutenberg_archive)")
            }
            for column, ddl in (
                ("etag", "TEXT"),
                ("last_modified", "TEXT"),
                ("retry_count", "INTEGER NOT NULL DEFAULT 0"),
                ("next_retry_at", "TEXT"),
            ):
                if column not in archive_columns:
                    db.execute(f"ALTER TABLE gutenberg_archive ADD COLUMN {column} {ddl}")
            db.execute("""CREATE TABLE IF NOT EXISTS gutenberg_books (
                etext_id INTEGER PRIMARY KEY, title TEXT NOT NULL DEFAULT '',
                author TEXT NOT NULL DEFAULT '', language TEXT NOT NULL DEFAULT '',
                path TEXT NOT NULL, content TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS gutenberg_catalogue_books (
                etext_id INTEGER PRIMARY KEY, title TEXT NOT NULL DEFAULT '',
                author TEXT NOT NULL DEFAULT '', language TEXT NOT NULL DEFAULT '',
                issued TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL)""")
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_gutenberg_catalogue_title "
                "ON gutenberg_catalogue_books(title)"
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_gutenberg_catalogue_author "
                "ON gutenberg_catalogue_books(author)"
            )
            # Normalized, rebuildable projections of the catalogue for identity-aware author enumeration.
            db.execute("""CREATE TABLE IF NOT EXISTS gutenberg_item_contributors (
                etext_id INTEGER NOT NULL, position INTEGER NOT NULL, name TEXT NOT NULL,
                normalized_name TEXT NOT NULL, surname_key TEXT NOT NULL, given_key TEXT NOT NULL,
                role TEXT NOT NULL, raw_role TEXT NOT NULL DEFAULT '',
                birth_year INTEGER, death_year INTEGER, PRIMARY KEY(etext_id, position))""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_gutenberg_contrib_surname ON gutenberg_item_contributors(surname_key)")
            db.execute("""CREATE TABLE IF NOT EXISTS gutenberg_item_languages (
                etext_id INTEGER NOT NULL, language_code TEXT NOT NULL, PRIMARY KEY(etext_id, language_code))""")
            catalogue_columns = {row[1] for row in db.execute("PRAGMA table_info(gutenberg_catalogue_books)")}
            if "item_type" not in catalogue_columns:
                db.execute("ALTER TABLE gutenberg_catalogue_books ADD COLUMN item_type TEXT NOT NULL DEFAULT ''")
            columns = {row[1] for row in db.execute("PRAGMA table_info(gutenberg_books)")}
            if "content" not in columns:
                db.execute("ALTER TABLE gutenberg_books ADD COLUMN content TEXT NOT NULL DEFAULT ''")
            db.execute(
                "INSERT OR IGNORE INTO gutenberg_catalogue(id,source_url) VALUES(1,?)",
                (CATALOGUE_URL,),
            )
            db.execute(
                "UPDATE gutenberg_catalogue SET source_url=? WHERE id=1",
                (CATALOGUE_URL,),
            )
            db.execute(
                "INSERT OR IGNORE INTO gutenberg_archive(id,url,path,updated_at) VALUES(1,?,?,?)",
                (ARCHIVE_URL, str(self.archive_path), _now()),
            )
            db.execute(
                "UPDATE gutenberg_archive SET url=?,path=? WHERE id=1",
                (ARCHIVE_URL, str(self.archive_path)),
            )
            self._backfill_normalized(db)
        self._migrate_legacy_books()

    @staticmethod
    def _init_library_db(path: Path, *, staging: bool = False) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as db:
            if staging:
                # A staging database is disposable until the final atomic rename.
                db.execute("PRAGMA journal_mode=OFF")
                db.execute("PRAGMA synchronous=OFF")
            db.execute("""CREATE TABLE IF NOT EXISTS gutenberg_texts (
                etext_id INTEGER PRIMARY KEY,
                content TEXT NOT NULL,
                content_sha256 TEXT NOT NULL,
                byte_length INTEGER NOT NULL,
                archive_member TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS gutenberg_meta (
                id INTEGER PRIMARY KEY CHECK(id=1),
                status TEXT NOT NULL DEFAULT 'empty',
                item_count INTEGER NOT NULL DEFAULT 0,
                installed_at TEXT
            )""")
            db.execute("INSERT OR IGNORE INTO gutenberg_meta(id) VALUES(1)")

    def _library_count(self, path: Path | None = None) -> int:
        target = path or self.library_db_path
        if not target.is_file():
            return 0
        try:
            with sqlite3.connect(target) as db:
                return int(db.execute("SELECT COUNT(*) FROM gutenberg_texts").fetchone()[0])
        except sqlite3.Error:
            return 0

    def _library_state(self) -> tuple[str, int, int]:
        if not self.library_db_path.is_file():
            return ("empty", 0, 0)
        try:
            with sqlite3.connect(self.library_db_path) as db:
                row = db.execute("SELECT status,item_count FROM gutenberg_meta WHERE id=1").fetchone()
                count = int(db.execute("SELECT COUNT(*) FROM gutenberg_texts").fetchone()[0])
            return (str(row[0]) if row else "empty", int(row[1]) if row else 0, count)
        except sqlite3.Error:
            return ("error", 0, 0)

    def _migrate_legacy_books(self) -> None:
        """One-time migration from the old extracted-file cache into the local text database."""
        if self._library_count():
            return
        with sqlite3.connect(self.db_path) as db:
            rows = db.execute("SELECT etext_id,path,content FROM gutenberg_books ORDER BY etext_id").fetchall()
        if not rows:
            return
        self._init_library_db(self.library_db_path)
        imported = 0
        with sqlite3.connect(self.library_db_path) as library:
            for etext_id, raw_path, stored in rows:
                text = str(stored or "")
                member = "legacy-db"
                if not text and raw_path:
                    source = Path(str(raw_path))
                    if source.is_file():
                        text = source.read_text(encoding="utf-8", errors="replace")
                        member = str(source)
                if not text:
                    continue
                payload = text.encode("utf-8")
                library.execute(
                    "INSERT OR REPLACE INTO gutenberg_texts VALUES(?,?,?,?,?,?)",
                    (int(etext_id), text, hashlib.sha256(payload).hexdigest(), len(payload), member, _now()),
                )
                imported += 1
                if imported % 500 == 0:
                    library.commit()
            if imported:
                library.execute(
                    "UPDATE gutenberg_meta SET status='legacy',item_count=?,installed_at=? WHERE id=1",
                    (imported, _now()),
                )

    @staticmethod
    def _index_rows(db: sqlite3.Connection, rows: list[tuple[int, str, str]]) -> None:
        """(Re)build normalized contributor/language rows for (etext_id, authors, language) triples."""
        contributors = []
        languages: list[tuple[int, str]] = []
        for etext_id, authors, language in rows:
            for item in parse_gutenberg_contributors(authors):
                contributors.append((
                    etext_id, item["position"], item["name"], item["normalized_name"], item["surname_key"],
                    item["given_key"], item["role"], item["raw_role"], item["birth_year"], item["death_year"],
                ))
            languages.extend((etext_id, code) for code in normalize_languages(language))
        db.executemany("INSERT OR REPLACE INTO gutenberg_item_contributors VALUES(?,?,?,?,?,?,?,?,?,?)", contributors)
        db.executemany("INSERT OR REPLACE INTO gutenberg_item_languages VALUES(?,?)", languages)

    def _backfill_normalized(self, db: sqlite3.Connection) -> None:
        """Idempotent migration: installations indexed before normalization keep working without a re-download.

        The flattened table stores the catalogue's raw Authors/Language cells, so the normalized
        projection can be rebuilt locally. It runs only when the projection is empty or outdated.
        """
        has_books = db.execute("SELECT 1 FROM gutenberg_catalogue_books LIMIT 1").fetchone()
        has_contrib = db.execute("SELECT 1 FROM gutenberg_item_contributors LIMIT 1").fetchone()
        marker = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='gutenberg_normalization_version'"
        ).fetchone()
        current = None
        if marker:
            got = db.execute("SELECT version FROM gutenberg_normalization_version WHERE id=1").fetchone()
            current = got[0] if got else None
        if has_books and (not has_contrib or current != CONTRIBUTOR_PARSER_VERSION):
            db.execute("DELETE FROM gutenberg_item_contributors")
            db.execute("DELETE FROM gutenberg_item_languages")
            self._index_rows(db, [tuple(row) for row in db.execute("SELECT etext_id,author,language FROM gutenberg_catalogue_books")])
        db.execute("CREATE TABLE IF NOT EXISTS gutenberg_normalization_version (id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL)")
        db.execute("INSERT OR REPLACE INTO gutenberg_normalization_version(id,version) VALUES(1,?)", (CONTRIBUTOR_PARSER_VERSION,))

    def status(self) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            catalogue = dict(db.execute("SELECT * FROM gutenberg_catalogue WHERE id=1").fetchone())
            archive = dict(db.execute("SELECT * FROM gutenberg_archive WHERE id=1").fetchone())
            catalogue_rows = int(db.execute("SELECT COUNT(*) FROM gutenberg_catalogue_books").fetchone()[0])
        # Readiness belongs to the installed database, not the disposable ZIP.
        # This keeps a verified local collection usable during updates and after the archive is deleted.
        library_status, installed_count, installed_texts = self._library_state()
        staging_texts = self._library_count(self.staging_library_db_path) if self.staging_library_db_path.is_file() else 0
        archive["imported_texts"] = staging_texts if archive["status"] == "unpacking" else installed_texts
        archive["ready"] = (
            library_status == "ready"
            and installed_texts > 0
            and installed_texts == installed_count
        )
        declared_count = int(catalogue.get("item_count") or 0)
        search_ready = (
            catalogue["status"] == "ready"
            and catalogue_rows > 0
            and (declared_count == 0 or catalogue_rows == declared_count)
        )
        return {
            "catalogue": catalogue,
            "archive": archive,
            "ready": archive["ready"],
            "search_ready": search_ready,
        }

    def realtime_summary(self) -> dict[str, Any]:
        """Bounded public state for ``activity:gutenberg``: no paths, URLs or error text."""
        status = self.status()
        catalogue, archive = status["catalogue"], status["archive"]
        return {
            "catalogue_status": str(catalogue.get("status") or ""),
            "archive_status": str(archive.get("status") or ""),
            "bytes_done": int(archive.get("bytes_done") or 0),
            "total_bytes": int(archive.get("total_bytes") or 0) or None,
            "ready": bool(status["ready"]),
            "search_ready": bool(status["search_ready"]),
            "has_error": bool(catalogue.get("error") or archive.get("error")),
        }

    def _changed(self) -> None:
        """Tell watching clients the offline collection changed (never raises)."""
        try:
            operation_events.note_activity("gutenberg", self.realtime_summary())
        except Exception:  # noqa: BLE001, S110 - notifications must never break the download
            pass

    @staticmethod
    def _catalogue_value(row: dict[str, str], *names: str) -> str:
        for name in names:
            value = str(row.get(name) or "").strip()
            if value:
                return value
        return ""

    def refresh_catalogue(self) -> dict[str, Any]:
        """Fetch Project Gutenberg's machine-readable catalogue into SQLite."""

        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "UPDATE gutenberg_catalogue SET status='refreshing',error=NULL WHERE id=1"
            )
        self._changed()
        try:
            response = httpx.get(CATALOGUE_URL, timeout=120.0, follow_redirects=True)
            response.raise_for_status()
            text = response.content.decode("utf-8-sig", errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            rows: list[tuple[int, str, str, str, str, str, str]] = []
            now = _now()
            for raw in reader:
                if not isinstance(raw, dict):
                    continue
                id_text = self._catalogue_value(
                    raw,
                    "Text#",
                    "EBook-No.",
                    "EBook No.",
                    "ebook_id",
                    "id",
                )
                try:
                    etext_id = int(id_text)
                except (TypeError, ValueError):
                    continue
                title = self._catalogue_value(raw, "Title", "title")
                if not title:
                    continue
                rows.append(
                    (
                        etext_id,
                        title,
                        self._catalogue_value(raw, "Authors", "Author", "author"),
                        self._catalogue_value(raw, "Language", "Languages", "language"),
                        self._catalogue_value(raw, "Issued", "issued"),
                        now,
                        self._catalogue_value(raw, "Type", "type"),
                    )
                )

            if not rows:
                raise ValueError("Project Gutenberg catalogue contained no readable book rows.")

            with sqlite3.connect(self.db_path) as db:
                db.execute("UPDATE gutenberg_catalogue SET status='indexing' WHERE id=1")
                db.execute("DELETE FROM gutenberg_catalogue_books")
                db.execute("DELETE FROM gutenberg_item_contributors")
                db.execute("DELETE FROM gutenberg_item_languages")
                db.executemany(
                    """
                    INSERT INTO gutenberg_catalogue_books(
                        etext_id,title,author,language,issued,updated_at,item_type
                    ) VALUES(?,?,?,?,?,?,?)
                    """,
                    rows,
                )
                self._index_rows(db, [(row[0], row[2], row[3]) for row in rows])
                db.execute(
                    """
                    UPDATE gutenberg_catalogue
                    SET refreshed_at=?,item_count=?,payload_json='[]',
                        status='ready',error=NULL
                    WHERE id=1
                    """,
                    (now, len(rows)),
                )
        except (httpx.HTTPError, OSError, ValueError, csv.Error) as exc:
            with sqlite3.connect(self.db_path) as db:
                db.execute(
                    "UPDATE gutenberg_catalogue SET status='error',error=? WHERE id=1",
                    (str(exc),),
                )
            self._changed()
            raise
        self._changed()
        return self.status()

    def _run_catalogue_worker(self) -> None:
        try:
            self.refresh_catalogue()
        except Exception:
            # refresh_catalogue persisted the actionable error for status/UI.
            return

    def _start_catalogue_worker(self) -> None:
        if self._catalogue_worker and self._catalogue_worker.is_alive():
            return
        self._catalogue_worker = threading.Thread(
            target=self._run_catalogue_worker,
            name="gutenberg-catalogue",
            daemon=True,
        )
        self._catalogue_worker.start()

    def start_catalogue_refresh(self) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "UPDATE gutenberg_catalogue SET status='refreshing',error=NULL WHERE id=1"
            )
        self._changed()
        if self._start_worker_enabled:
            self._start_catalogue_worker()
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
            self._chunk_path().unlink(missing_ok=True)
            self.staging_library_db_path.unlink(missing_ok=True)
            # Keep the last verified local database available while a replacement downloads.
            # Legacy extracted files are no longer part of the active collection.
            if self.extract_root.is_dir():
                for path in self.extract_root.glob("*.txt"):
                    path.unlink(missing_ok=True)
        with sqlite3.connect(self.db_path) as db:
            if action == "refetch":
                db.execute(
                    """
                    UPDATE gutenberg_archive
                    SET status=?,bytes_done=0,total_bytes=NULL,error=NULL,etag=NULL,
                        last_modified=NULL,retry_count=0,next_retry_at=NULL,updated_at=?
                    WHERE id=1
                    """,
                    (allowed[action], _now()),
                )
            else:
                # Keep the known total and remote validators while a partial file exists.
                # A zero-byte start cannot safely reuse identity from a previous transport.
                offset = self._bytes_done()
                if action in {"start", "resume"} and offset == 0:
                    db.execute(
                        """
                        UPDATE gutenberg_archive
                        SET status=?,bytes_done=0,total_bytes=NULL,error=NULL,etag=NULL,
                            last_modified=NULL,retry_count=0,next_retry_at=NULL,updated_at=?
                        WHERE id=1
                        """,
                        (allowed[action], _now()),
                    )
                else:
                    db.execute(
                        """
                        UPDATE gutenberg_archive
                        SET status=?,bytes_done=?,error=NULL,retry_count=0,
                            next_retry_at=NULL,updated_at=?
                        WHERE id=1
                        """,
                        (allowed[action], offset, _now()),
                    )
        self._changed()
        if action in {"start", "resume"} and self._start_worker_enabled:
            self._start_worker()
        elif action == "pause":
            self._stop.set()
        return self.status()

    def _start_worker(self) -> None:
        # Clear pause before checking the worker. A quick pause→resume may reuse
        # the still-alive worker instead of accidentally leaving it stopped.
        self._stop.clear()
        if self._worker and self._worker.is_alive():
            return
        self._worker = threading.Thread(
            target=self._run_worker,
            name="gutenberg-archive",
            daemon=True,
        )
        self._worker.start()

    def _run_worker(self) -> None:
        """Run the durable archive state machine outside the request lifecycle.

        Each network operation is a bounded byte range. Transient transport and
        upstream failures keep durable state in downloading and retry automatically
        with capped exponential backoff. Validation and local I/O failures remain
        terminal and require explicit user action.
        """
        try:
            while not self._stop.is_set():
                archive = self.status()["archive"]
                status = str(archive["status"])
                if status == "downloading":
                    if self._wait_for_saved_retry(archive):
                        break
                    try:
                        self.download_chunk()
                    except Exception as exc:
                        if not self._archive_error_retryable(exc):
                            self._mark_archive_error(exc)
                            break
                        if self._schedule_archive_retry(exc):
                            break
                    continue
                if status in {"downloaded", "unpacking", "complete"}:
                    with sqlite3.connect(self.db_path) as db:
                        db.execute(
                            """
                            UPDATE gutenberg_archive
                            SET status='unpacking',retry_count=0,next_retry_at=NULL,updated_at=?
                            WHERE id=1
                            """,
                            (_now(),),
                        )
                    self._changed()
                    self.extract_catalogue()
                    with sqlite3.connect(self.db_path) as db:
                        db.execute(
                            """
                            UPDATE gutenberg_archive
                            SET status='ready',error=NULL,retry_count=0,next_retry_at=NULL,updated_at=?
                            WHERE id=1
                            """,
                            (_now(),),
                        )
                    # The archive is only installation transport. The verified SQLite collection
                    # is authoritative and survives independently of this file.
                    self.archive_path.unlink(missing_ok=True)
                    self._chunk_path().unlink(missing_ok=True)
                    self._changed()
                    break
                break
        except Exception as exc:
            self._mark_archive_error(exc)

    def extract_catalogue(self) -> int:
        """Stream the archive into a staging SQLite database, then atomically install it."""

        if not self.archive_path.is_file():
            raise ValueError("Gutenberg archive is missing.")
        self.staging_library_db_path.unlink(missing_ok=True)
        self._init_library_db(self.staging_library_db_path, staging=True)
        count = 0
        seen_ids: set[int] = set()
        try:
            with zipfile.ZipFile(self.archive_path) as outer:
                tar_name = next((name for name in outer.namelist() if name.lower().endswith(".tar")), None)
                if not tar_name:
                    raise ValueError("Gutenberg archive does not contain a tar payload.")
                with outer.open(tar_name, "r") as tar_stream, tarfile.open(
                    fileobj=tar_stream, mode="r|*"
                ) as archive, sqlite3.connect(self.staging_library_db_path) as library:
                    for info in archive:
                        etext_id = _archive_etext_id(info.name)
                        if etext_id is None or not info.isfile():
                            continue
                        extracted = archive.extractfile(info)
                        if extracted is None:
                            continue
                        payload = extracted.read()
                        text = payload.decode("utf-8", errors="replace")
                        library.execute(
                            "INSERT OR REPLACE INTO gutenberg_texts VALUES(?,?,?,?,?,?)",
                            (
                                etext_id,
                                text,
                                hashlib.sha256(payload).hexdigest(),
                                len(payload),
                                info.name,
                                _now(),
                            ),
                        )
                        if etext_id not in seen_ids:
                            seen_ids.add(etext_id)
                            count += 1
                        if count % 250 == 0:
                            library.commit()
                            with sqlite3.connect(self.db_path) as state:
                                state.execute(
                                    "UPDATE gutenberg_archive SET status='unpacking',updated_at=? WHERE id=1",
                                    (_now(),),
                                )
                            self._changed()
            if count <= 0 or self._library_count(self.staging_library_db_path) != count:
                raise ValueError("Gutenberg archive contained no installable plain-text books.")
            with sqlite3.connect(self.staging_library_db_path) as library:
                library.execute(
                    "UPDATE gutenberg_meta SET status='ready',item_count=?,installed_at=? WHERE id=1",
                    (count, _now()),
                )
            # Readers opening after this rename see either the previous complete collection
            # or the new complete collection; never a half-populated database.
            self.staging_library_db_path.replace(self.library_db_path)
        except Exception:
            self.staging_library_db_path.unlink(missing_ok=True)
            raise
        return count

    def search(self, query: str, limit: int = 12) -> list[dict[str, Any]]:
        term = f"%{str(query or '').strip()}%"
        with sqlite3.connect(self.db_path) as db:
            rows = db.execute(
                """
                SELECT etext_id,title,author,language
                FROM gutenberg_catalogue_books
                WHERE title LIKE ? OR author LIKE ?
                ORDER BY etext_id
                LIMIT ?
                """,
                (term, term, max(1, min(30, int(limit)))),
            ).fetchall()
        return [
            {
                "etext_id": row[0],
                "title": row[1],
                "author": row[2],
                "language": row[3],
            }
            for row in rows
        ]

    def search_authors(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search distinct catalogue authors locally; no provider network is required."""
        raw = str(query or "").strip()
        if not raw:
            return []
        term = f"%{raw}%"
        folded = f"%{fold(raw)}%"
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                """
                SELECT * FROM gutenberg_item_contributors
                WHERE role='author' AND (name LIKE ? OR normalized_name LIKE ?)
                ORDER BY etext_id,position
                LIMIT ?
                """,
                (term, folded, max(100, min(1000, int(limit) * 40))),
            ).fetchall()
        found: list[dict[str, Any]] = []
        seen: set[tuple[str, int | None, int | None]] = set()
        for row in rows:
            key = (str(row["normalized_name"]), row["birth_year"], row["death_year"])
            if key in seen:
                continue
            seen.add(key)
            name = str(row["name"])
            parsed = PersonName.parse(name)
            label = name
            if "," in name:
                surname, rest = name.split(",", 1)
                label = f"{rest.strip()} {surname.strip()}".strip()
            found.append({
                "identity_id": f"gutenberg:{int(row['etext_id'])}:{int(row['position'])}",
                "identity_source": "gutenberg",
                "wikidata_qid": None,
                "label": label,
                "description": "Project Gutenberg catalogue author",
                "aliases": [],
                "birth_year": row["birth_year"],
                "death_year": row["death_year"],
                "wikisource_sitelinks": {},
                "original_languages": [],
                "languages": [],
                "normalized_name": parsed.full,
            })
            if len(found) >= max(1, min(20, int(limit))):
                break
        return found

    def resolve_author(self, identity_id: str) -> Any:
        """Resolve a previously offered local author identity without Wikidata."""
        match = re.fullmatch(r"gutenberg:(\d+):(\d+)", str(identity_id or ""))
        if not match:
            raise ValueError("Choose a Project Gutenberg author from the local search results.")
        etext_id, position = (int(match.group(1)), int(match.group(2)))
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute(
                "SELECT * FROM gutenberg_item_contributors WHERE etext_id=? AND position=? AND role='author'",
                (etext_id, position),
            ).fetchone()
            if row is None:
                raise ValueError("The selected local Gutenberg author no longer exists in the catalogue.")
            variants = db.execute(
                """
                SELECT DISTINCT name FROM gutenberg_item_contributors
                WHERE role='author' AND normalized_name=?
                  AND birth_year IS ? AND death_year IS ?
                ORDER BY name
                """,
                (row["normalized_name"], row["birth_year"], row["death_year"]),
            ).fetchall()
            language_rows = db.execute(
                """
                SELECT DISTINCT l.language_code
                FROM gutenberg_item_contributors c
                JOIN gutenberg_item_languages l ON l.etext_id=c.etext_id
                WHERE c.role='author' AND c.normalized_name=?
                  AND c.birth_year IS ? AND c.death_year IS ?
                ORDER BY l.language_code
                """,
                (row["normalized_name"], row["birth_year"], row["death_year"]),
            ).fetchall()
        from .source_identity import ResolvedAuthor

        canonical = str(row["name"])
        if "," in canonical:
            surname, rest = canonical.split(",", 1)
            canonical = f"{rest.strip()} {surname.strip()}".strip()
        aliases = [str(item[0]) for item in variants if str(item[0]) != str(row["name"])]
        return ResolvedAuthor(
            identity_id=str(identity_id),
            canonical_name=canonical,
            wikidata_qid=None,
            aliases=aliases,
            description="Project Gutenberg catalogue author",
            birth_year=row["birth_year"],
            death_year=row["death_year"],
            languages=[str(item[0]) for item in language_rows],
            external_ids={"gutenberg_local": str(identity_id)},
        )

    def sources_for_author(
        self, names: list[str], *, birth_year: int | None = None, death_year: int | None = None
    ) -> list[dict[str, Any]]:
        """Every indexed item with a contributor matching the resolved person, with match evidence.

        Identity-aware, not a full-text search: rows are looked up by surname key, then each
        contributor is compared deterministically against the person's names and life dates.

        * ``exact``      — full name equals an alias, or given name + surname match and life dates agree.
        * ``needs_review`` — given name + surname match but neither side can confirm dates.
        * rejected      — dates present on both sides and different: a different person, never included.
        """
        wanted = [PersonName.parse(name) for name in names if str(name or "").strip()]
        surnames = sorted({name.surname for name in wanted if name.surname})
        if not surnames:
            return []
        full_names = {name.full for name in wanted}
        placeholders = ",".join("?" for _ in surnames)
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            matches = db.execute(
                # Placeholders are only "?" (one per surname key).
                f"SELECT * FROM gutenberg_item_contributors WHERE surname_key IN ({placeholders})",  # noqa: S608
                surnames,
            ).fetchall()
            by_item: dict[int, dict[str, Any]] = {}
            for row in matches:
                person = PersonName(row["normalized_name"], row["surname_key"], row["given_key"])
                exact_name = person.full in full_names
                given_match = any(
                    person.surname == name.surname and person.first_given and person.first_given == name.first_given
                    for name in wanted
                )
                if not (exact_name or given_match):
                    continue
                dates_known = row["birth_year"] is not None and birth_year is not None
                if dates_known and row["birth_year"] != birth_year:
                    continue
                if row["death_year"] is not None and death_year is not None and row["death_year"] != death_year:
                    continue
                confidence = "exact" if (dates_known or exact_name) else "needs_review"
                current = by_item.get(int(row["etext_id"]))
                if current and current["identity_confidence"] == "exact":
                    continue
                by_item[int(row["etext_id"])] = {
                    "etext_id": int(row["etext_id"]),
                    "matched_contributor": dict(row),
                    "identity_confidence": confidence,
                    "date_evidence": dates_known,
                }
            if not by_item:
                return []
            ids = sorted(by_item)
            results = []
            for start in range(0, len(ids), 500):
                chunk = ids[start : start + 500]
                marks = ",".join("?" for _ in chunk)
                # Placeholders are only "?" (one per id in this chunk).
                items = db.execute(f"SELECT * FROM gutenberg_catalogue_books WHERE etext_id IN ({marks})", chunk).fetchall()  # noqa: S608
                contributors = db.execute(
                    f"SELECT * FROM gutenberg_item_contributors WHERE etext_id IN ({marks}) ORDER BY etext_id,position",  # noqa: S608
                    chunk,
                ).fetchall()
                languages = db.execute(
                    f"SELECT * FROM gutenberg_item_languages WHERE etext_id IN ({marks})", chunk  # noqa: S608
                ).fetchall()
                people: dict[int, list[dict[str, Any]]] = {}
                for row in contributors:
                    people.setdefault(int(row["etext_id"]), []).append(dict(row))
                langs: dict[int, list[str]] = {}
                for row in languages:
                    langs.setdefault(int(row["etext_id"]), []).append(str(row["language_code"]))
                for item in items:
                    etext_id = int(item["etext_id"])
                    results.append({
                        **by_item[etext_id],
                        "title": item["title"],
                        "issued": item["issued"],
                        "item_type": item["item_type"] if "item_type" in item.keys() else "",
                        "authors_raw": item["author"],
                        "languages": sorted(langs.get(etext_id, [])),
                        "contributors": people.get(etext_id, []),
                    })
        return sorted(results, key=lambda row: row["etext_id"])

    def text(self, etext_id: int) -> tuple[str, dict[str, Any]] | None:
        if not self.library_db_path.is_file():
            return None
        with sqlite3.connect(self.library_db_path) as library:
            row = library.execute(
                "SELECT content,content_sha256,byte_length,archive_member FROM gutenberg_texts WHERE etext_id=?",
                (int(etext_id),),
            ).fetchone()
        if not row:
            return None
        with sqlite3.connect(self.db_path) as db:
            meta = db.execute(
                "SELECT title,author,language FROM gutenberg_catalogue_books WHERE etext_id=?",
                (int(etext_id),),
            ).fetchone()
        title, author, language = meta if meta else ("", "", "")
        return str(row[0]), {
            "gutenberg_id": int(etext_id),
            "title": title,
            "document_author": author,
            "language": language,
            "publisher": "Project Gutenberg",
            "document_type": "book",
            "edition": f"Project Gutenberg eBook #{int(etext_id)}",
            "source_url": f"https://www.gutenberg.org/ebooks/{int(etext_id)}",
            "source_sha256": str(row[1]),
            "byte_length": int(row[2]),
            "archive_member": str(row[3]),
            "retrieved_at": _now(),
        }

    def _bytes_done(self) -> int:
        return self.archive_path.stat().st_size if self.archive_path.is_file() else 0

    def _chunk_path(self) -> Path:
        """Return the disposable path used while receiving one verified range."""
        return self.archive_path.with_name(f"{self.archive_path.name}.chunk")

    @staticmethod
    def _if_range_validator(state: dict[str, Any]) -> str:
        """Prefer a strong ETag, then Last-Modified, for safe range resumption."""
        etag = str(state.get("etag") or "").strip()
        if etag and not etag.startswith("W/"):
            return etag
        return str(state.get("last_modified") or "").strip()

    @staticmethod
    def _parse_content_range(value: str) -> tuple[int, int, int] | None:
        match = _CONTENT_RANGE_RE.fullmatch(str(value or "").strip())
        if not match or match.group(3) == "*":
            return None
        return int(match.group(1)), int(match.group(2)), int(match.group(3))

    @staticmethod
    def _archive_error_retryable(exc: Exception) -> bool:
        if isinstance(exc, httpx.TransportError):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            status = int(exc.response.status_code)
            return status in {408, 425, 429} or status >= 500
        return False

    @staticmethod
    def _retry_delay_seconds(retry_count: int) -> int:
        return min(_MAX_RETRY_DELAY_SECONDS, 2 ** min(max(0, retry_count - 1), 6))

    def _wait_for_saved_retry(self, archive: dict[str, Any]) -> bool:
        raw = str(archive.get("next_retry_at") or "").strip()
        if not raw:
            return False
        try:
            deadline = datetime.fromisoformat(raw)
            delay = max(0.0, (deadline - datetime.now(UTC)).total_seconds())
        except ValueError:
            delay = 0.0
        return bool(delay and self._stop.wait(delay))

    def _schedule_archive_retry(self, exc: Exception) -> bool:
        """Persist a transient failure and wait without turning it into a failed install."""
        archive = self.status()["archive"]
        retry_count = int(archive.get("retry_count") or 0) + 1
        delay = self._retry_delay_seconds(retry_count)
        next_retry = datetime.now(UTC) + timedelta(seconds=delay)
        message = (
            f"Connection interrupted; retrying automatically in {delay}s "
            f"(attempt {retry_count}): {str(exc) or exc.__class__.__name__}"
        )
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                """
                UPDATE gutenberg_archive
                SET status='downloading',error=?,bytes_done=?,retry_count=?,
                    next_retry_at=?,updated_at=?
                WHERE id=1
                """,
                (message, self._bytes_done(), retry_count, next_retry.isoformat(), _now()),
            )
        self._changed()
        return self._stop.wait(delay)

    def _mark_archive_error(self, exc: Exception) -> None:
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                """
                UPDATE gutenberg_archive
                SET status='error',error=?,bytes_done=?,retry_count=0,
                    next_retry_at=NULL,updated_at=?
                WHERE id=1
                """,
                (str(exc) or exc.__class__.__name__, self._bytes_done(), _now()),
            )
        self._changed()

    def _restart_for_changed_archive(self, response: Any) -> dict[str, Any]:
        """Discard only disposable transport when Gutenberg replaces the weekly archive."""
        self.archive_path.unlink(missing_ok=True)
        self._chunk_path().unlink(missing_ok=True)
        length = int(response.headers.get("content-length") or 0)
        etag = str(response.headers.get("etag") or "").strip() or None
        last_modified = str(response.headers.get("last-modified") or "").strip() or None
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                """
                UPDATE gutenberg_archive
                SET status='downloading',bytes_done=0,total_bytes=?,etag=?,
                    last_modified=?,retry_count=0,next_retry_at=NULL,
                    error='The Gutenberg archive changed during download; restarting the disposable archive from byte 0.',
                    updated_at=?
                WHERE id=1
                """,
                (length or None, etag, last_modified, _now()),
            )
        self._changed()
        return self.status()

    def download_archive(self) -> dict[str, Any]:
        """Download the archive as bounded resumable ranges.

        This whole-download entry point intentionally opens a fresh HTTP request
        for each chunk rather than holding one multi-gigabyte connection open.
        """
        while self.status()["archive"]["status"] == "downloading":
            self.download_chunk()
        return self.status()

    def _finish_or_explain_unsatisfiable_range(self, response: Any, offset: int) -> dict[str, Any]:
        """A 416 after some bytes: the file on disk may already be the whole archive.

        The server states the archive's length ("Content-Range: bytes */N", or a HEAD request's Content-Length when the
        416 omits it). When the file on disk has exactly that
        length the download is complete and unpacking can start; any other length is reported with the way out.
        """
        match = re.search(r"/\s*(\d+)\s*$", str(response.headers.get("content-range", "")))
        total = int(match.group(1)) if match else 0
        if not total:
            # gutenberg.org answers 416 without Content-Range; its HEAD response gives the length.
            head = httpx.head(ARCHIVE_URL, timeout=60.0, follow_redirects=True)
            head.raise_for_status()
            total = int(head.headers.get("content-length") or 0)
        if total and offset == total:
            with sqlite3.connect(self.db_path) as db:
                db.execute("UPDATE gutenberg_archive SET status='downloaded',bytes_done=?,total_bytes=?,error=NULL,updated_at=? WHERE id=1",
                           (offset, total, _now()))
            self._changed()
            return self.status()
        if total and offset > total:
            raise ValueError(
                f"The downloaded file ({offset:,} bytes) is larger than the Gutenberg archive ({total:,} bytes). "
                "Use Redownload to fetch it again."
            )
        raise ValueError(
            "The Gutenberg server could not resume the download at the current position. Use Redownload to start over."
        )

    def download_chunk(self, chunk_size: int = CHUNK_SIZE) -> dict[str, Any]:
        """Stream one bounded byte range into durable transport storage."""
        state = self.status()["archive"]
        if state["status"] != "downloading":
            raise ValueError("Archive is not running; start or resume it first.")

        offset = self._bytes_done()
        requested = min(max(1, int(chunk_size)), CHUNK_SIZE)
        headers = {"Range": f"bytes={offset}-{offset + requested - 1}"}
        if_range = self._if_range_validator(state)
        if offset and if_range:
            headers["If-Range"] = if_range

        chunk_path = self._chunk_path()
        chunk_path.unlink(missing_ok=True)
        try:
            with httpx.stream(
                "GET",
                ARCHIVE_URL,
                headers=headers,
                timeout=httpx.Timeout(120.0, connect=20.0),
                follow_redirects=True,
            ) as response:
                if response.status_code == 416 and offset:
                    return self._finish_or_explain_unsatisfiable_range(response, offset)

                # If-Range intentionally converts a changed object into a 200.
                # Do not consume that multi-gigabyte body; restart from byte zero.
                if offset and if_range and response.status_code == 200:
                    return self._restart_for_changed_archive(response)

                response.raise_for_status()
                if response.status_code != 206:
                    raise ValueError(
                        "Gutenberg server did not honor the bounded range request."
                    )

                parsed = self._parse_content_range(
                    str(response.headers.get("content-range") or "")
                )
                if parsed is None:
                    raise ValueError(
                        "Gutenberg range response omitted a usable Content-Range."
                    )
                range_start, range_end, total = parsed
                if range_start != offset:
                    raise ValueError(
                        f"Gutenberg returned byte {range_start:,} while {offset:,} was requested."
                    )
                expected = range_end - range_start + 1
                if expected <= 0 or expected > requested:
                    raise ValueError("Gutenberg returned an invalid byte range.")

                known_total = int(state.get("total_bytes") or 0)
                if offset and known_total and total != known_total:
                    return self._restart_for_changed_archive(response)

                response_etag = str(response.headers.get("etag") or "").strip()
                response_modified = str(
                    response.headers.get("last-modified") or ""
                ).strip()
                known_etag = str(state.get("etag") or "").strip()
                known_modified = str(state.get("last_modified") or "").strip()
                if offset and known_etag and response_etag and response_etag != known_etag:
                    return self._restart_for_changed_archive(response)
                if (
                    offset
                    and not known_etag
                    and known_modified
                    and response_modified
                    and response_modified != known_modified
                ):
                    return self._restart_for_changed_archive(response)

                received = 0
                with chunk_path.open("wb") as chunk_file:
                    for payload in response.iter_bytes(chunk_size=1024 * 1024):
                        if (
                            self._stop.is_set()
                            or self.status()["archive"]["status"] != "downloading"
                        ):
                            chunk_path.unlink(missing_ok=True)
                            return self.status()
                        received += len(payload)
                        if received > expected:
                            raise ValueError(
                                "Gutenberg archive response exceeded the requested byte range."
                            )
                        chunk_file.write(payload)
                    chunk_file.flush()

                if received != expected:
                    raise ValueError(
                        f"Gutenberg archive range ended at {received:,} bytes; expected {expected:,}."
                    )

            # Re-check durable state after the network request. A pause/refetch
            # while the request was in flight must not append stale bytes.
            if (
                self._stop.is_set()
                or self.status()["archive"]["status"] != "downloading"
            ):
                chunk_path.unlink(missing_ok=True)
                return self.status()

            self.archive_path.parent.mkdir(parents=True, exist_ok=True)
            with self.archive_path.open("ab" if offset else "wb") as destination:
                with chunk_path.open("rb") as source:
                    shutil.copyfileobj(source, destination, length=1024 * 1024)
                destination.flush()
            chunk_path.unlink(missing_ok=True)

            done = self._bytes_done()
            if done != offset + received:
                raise OSError(
                    f"Gutenberg archive size changed unexpectedly: {done:,} bytes on disk."
                )
            status = "downloaded" if done >= total else "downloading"
            with sqlite3.connect(self.db_path) as db:
                db.execute(
                    """
                    UPDATE gutenberg_archive
                    SET status=?,bytes_done=?,total_bytes=?,etag=?,last_modified=?,
                        error=NULL,retry_count=0,next_retry_at=NULL,updated_at=?
                    WHERE id=1
                    """,
                    (
                        status,
                        done,
                        total,
                        response_etag or state.get("etag"),
                        response_modified or state.get("last_modified"),
                        _now(),
                    ),
                )
            self._changed()
            return self.status()
        except Exception:
            chunk_path.unlink(missing_ok=True)
            raise



gutenberg_offline = GutenbergOfflineService()
