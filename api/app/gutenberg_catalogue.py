# Copyright 2026 Aaron John Schlosser, PhD.
"""Durable offline Project Gutenberg catalogue and archive bookkeeping."""
from __future__ import annotations

import csv
import io
import re
import sqlite3
import tarfile
import threading
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from .config import settings
from .source_identity import PersonName, normalize_languages

CATALOGUE_URL = "https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv"
ARCHIVE_URL = "https://www.gutenberg.org/cache/epub/feeds/txt-files.tar.zip"
CHUNK_SIZE = 8 * 1024 * 1024


def _now() -> str:
    return datetime.now(UTC).isoformat()


# pg_catalog.csv "Authors": "Nietzsche, Friedrich Wilhelm, 1844-1900; Common, Thomas, 1850-1919 [Translator]".
# An entry without a bracketed role is an author; a bracketed role we do not map stays "contributor", never author.
_ROLE_MAP = {"translator": "translator", "editor": "editor", "compiler": "editor"}
_DATES = re.compile(r",\s*(?:(\d{1,4})\??\s*(BCE)?)?\s*-\s*(?:(\d{1,4})\??\s*(BCE)?)?\s*$")
CONTRIBUTOR_PARSER_VERSION = 1


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
                total_bytes INTEGER, updated_at TEXT NOT NULL, error TEXT)""")
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
        archive["ready"] = archive["status"] == "ready" and Path(archive["path"]).is_file()
        # Catalogue search and local text availability are deliberately separate:
        # users can discover titles as soon as metadata indexing finishes, while
        # import remains gated until the full collection has downloaded/unpacked.
        search_ready = catalogue["status"] == "ready"
        return {
            "catalogue": catalogue,
            "archive": archive,
            "ready": archive["ready"],
            "search_ready": search_ready,
        }

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
            raise
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
            if self.extract_root.is_dir():
                for path in self.extract_root.glob("*.txt"):
                    path.unlink(missing_ok=True)
            with sqlite3.connect(self.db_path) as db:
                db.execute("DELETE FROM gutenberg_books")
        with sqlite3.connect(self.db_path) as db:
            if action == "refetch":
                db.execute("UPDATE gutenberg_archive SET status=?,bytes_done=0,total_bytes=NULL,error=NULL,updated_at=? WHERE id=1",
                           (allowed[action], _now()))
            else:
                # Keep the known total: forgetting it made a finished download look unfinished, so the next
                # chunk asked for bytes past the end of the file and the server answered 416.
                db.execute("UPDATE gutenberg_archive SET status=?,bytes_done=?,error=NULL,updated_at=? WHERE id=1",
                           (allowed[action], self._bytes_done(), _now()))
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
        try:
            while not self._stop.is_set():
                status = str(self.status()["archive"]["status"])
                if status == "downloading":
                    self.download_chunk()
                    continue
                if status in {"downloaded", "unpacking", "complete"}:
                    with sqlite3.connect(self.db_path) as db:
                        db.execute(
                            "UPDATE gutenberg_archive SET status='unpacking',updated_at=? WHERE id=1",
                            (_now(),),
                        )
                    self.extract_catalogue()
                    with sqlite3.connect(self.db_path) as db:
                        db.execute(
                            "UPDATE gutenberg_archive SET status='ready',error=NULL,updated_at=? WHERE id=1",
                            (_now(),),
                        )
                    break
                break
        except Exception as exc:
            with sqlite3.connect(self.db_path) as db:
                db.execute(
                    "UPDATE gutenberg_archive SET status='error',error=?,updated_at=? WHERE id=1",
                    (str(exc), _now()),
                )

    def extract_catalogue(self) -> int:
        """Unpack safe text files and persist only searchable file metadata in SQLite."""

        if not self.archive_path.is_file():
            raise ValueError("Gutenberg archive is missing.")
        self.extract_root.mkdir(parents=True, exist_ok=True)
        count = 0
        with zipfile.ZipFile(self.archive_path) as outer:
            tar_name = next(
                (name for name in outer.namelist() if name.lower().endswith(".tar")),
                None,
            )
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
                    payload = extracted.read()
                    text = payload.decode("utf-8", errors="replace")
                    etext_id = int(match.group(1))
                    target = self.extract_root / f"{etext_id}.txt"
                    target.write_bytes(payload)
                    title = re.search(r"(?im)^title:\s*(.+)$", text)
                    author = re.search(r"(?im)^author:\s*(.+)$", text)
                    catalogue = db.execute(
                        """
                        SELECT title,author,language
                        FROM gutenberg_catalogue_books
                        WHERE etext_id=?
                        """,
                        (etext_id,),
                    ).fetchone()
                    resolved_title = (
                        str(catalogue[0])
                        if catalogue and catalogue[0]
                        else (title.group(1).strip() if title else "")
                    )
                    resolved_author = (
                        str(catalogue[1])
                        if catalogue and catalogue[1]
                        else (author.group(1).strip() if author else "")
                    )
                    resolved_language = str(catalogue[2]) if catalogue and catalogue[2] else ""
                    db.execute(
                        """
                        INSERT OR REPLACE INTO gutenberg_books(
                            etext_id,title,author,language,path,content,updated_at
                        ) VALUES(?,?,?,?,?,'',?)
                        """,
                        (
                            etext_id,
                            resolved_title,
                            resolved_author,
                            resolved_language,
                            str(target),
                            _now(),
                        ),
                    )
                    count += 1
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
        with sqlite3.connect(self.db_path) as db:
            row = db.execute(
                "SELECT title,author,language,path,content FROM gutenberg_books WHERE etext_id=?",
                (int(etext_id),),
            ).fetchone()
        if not row:
            return None
        content = str(row[4] or "")
        if not content:
            path = Path(str(row[3] or ""))
            if not path.is_file():
                return None
            content = path.read_text(encoding="utf-8", errors="replace")
        return content, {
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
        state = self.status()["archive"]
        if state["status"] != "downloading":
            raise ValueError("Archive is not running; start or resume it first.")
        offset = self._bytes_done()
        requested = min(chunk_size, CHUNK_SIZE)
        # Always request a bounded byte range, including the first chunk. An
        # un-ranged initial GET can otherwise stream the entire multi-gigabyte
        # archive into the API process before the size guard gets a chance to run.
        headers = {"Range": f"bytes={offset}-{offset + requested - 1}"}
        response = httpx.get(
            ARCHIVE_URL,
            headers=headers,
            timeout=60.0,
            follow_redirects=True,
        )
        if response.status_code == 416 and offset:
            return self._finish_or_explain_unsatisfiable_range(response, offset)
        response.raise_for_status()
        if response.status_code != 206:
            raise ValueError("Gutenberg server did not honor the bounded range request.")
        if len(response.content) > requested:
            raise ValueError("Gutenberg archive response exceeded the bounded chunk size.")
        # Pause/refetch may have been requested while the HTTP call was in flight.
        # Do not let a stale chunk resurrect "downloading" or recreate a refetched file.
        if self._stop.is_set() or self.status()["archive"]["status"] != "downloading":
            return self.status()
        self.archive_path.parent.mkdir(parents=True, exist_ok=True)
        with self.archive_path.open("ab" if offset else "wb") as handle:
            handle.write(response.content)
        content_range = response.headers.get("content-range", "")
        total_text = content_range.rsplit("/", 1)[-1] if "/" in content_range else response.headers.get("content-length", "0")
        total = int(total_text or 0)
        done = self._bytes_done()
        status = "downloaded" if total and done >= total else "downloading"
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE gutenberg_archive SET status=?,bytes_done=?,total_bytes=?,updated_at=? WHERE id=1", (status,done,total or None,_now()))
        return self.status()


gutenberg_offline = GutenbergOfflineService()
