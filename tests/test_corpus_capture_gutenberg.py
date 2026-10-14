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

"""Project Gutenberg enumeration for Corpus Capture is identity-aware, not a surname search.

Why: the catalogue's Authors cell flattens authors, translators and editors with life
dates. Treating a translator as the author, merging two people who share a surname,
or requiring the full offline collection to import one book were all real risks.
How: a legacy flattened catalogue database is built in tmp_path, then normalized by the
service's idempotent backfill; remote Gutenberg calls are replaced by in-process fakes.
"""
from __future__ import annotations

import sqlite3

import httpx
import pytest
from _capture_support import author, http_for, json_response, no_rate_gate
from app import source_gutenberg as sg
from app.gutenberg_catalogue import (
    GutenbergOfflineService,
    parse_gutenberg_contributors,
)
from app.source_identity import CaptureError, CaptureErrorCode, CaptureOptions
from app.source_provider import DiscoveryReport

pytestmark = pytest.mark.unit

NIETZSCHE = "Nietzsche, Friedrich Wilhelm, 1844-1900"
CATALOGUE = [
    # (etext id, title, Authors cell, Language cell, Type)
    (1998, "Also sprach Zarathustra", NIETZSCHE, "de", "Text"),
    (1999, "Thus Spake Zarathustra", f"{NIETZSCHE}; Common, Thomas, 1850-1919 [Translator]", "en", "Text"),
    (2000, "Briefwechsel", f"{NIETZSCHE}; Wagner, Richard, 1813-1883", "de; en", "Text"),
    (2001, "Gedichte", "Nietzsche, Friedrich, 1900-1980", "de", "Text"),  # a namesake: dates conflict
    (2002, "Aphorismen", "Nietzsche, Friedrich W.", "de", "Text"),  # given + surname, no dates
    (2003, "Die Welt als Wille", f"Schopenhauer, Arthur, 1788-1860; {NIETZSCHE} [Translator]", "de", "Text"),
    (2004, "Zarathustra (audio)", NIETZSCHE, "de", "Sound"),
    (2005, "Anthologie", f"Goethe, Johann Wolfgang von, 1749-1832; {NIETZSCHE} [Editor]", "de", "Text"),
]


def _legacy_catalogue(path):
    """The pre-normalization schema: one flattened row per item, no contributor/language tables, no item_type."""
    with sqlite3.connect(path) as db:
        db.execute("""CREATE TABLE gutenberg_catalogue_books (
            etext_id INTEGER PRIMARY KEY, title TEXT NOT NULL DEFAULT '', author TEXT NOT NULL DEFAULT '',
            language TEXT NOT NULL DEFAULT '', issued TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL)""")
        db.executemany(
            "INSERT INTO gutenberg_catalogue_books VALUES(?,?,?,?,'','then')",
            [(etext, title, authors, language) for etext, title, authors, language, _type in CATALOGUE],
        )


@pytest.fixture
def catalogue(tmp_path):
    db_path = tmp_path / "system.sqlite"
    _legacy_catalogue(db_path)
    service = GutenbergOfflineService(db_path, tmp_path / "archive.zip", start_worker=False)
    with sqlite3.connect(db_path) as db:
        for etext, _title, _authors, _language, item_type in CATALOGUE:
            db.execute("UPDATE gutenberg_catalogue_books SET item_type=? WHERE etext_id=?", (item_type, etext))
        db.execute("UPDATE gutenberg_catalogue SET status='ready' WHERE id=1")
    return service


def _enumerate(provider, options=None, who=None):
    report = DiscoveryReport(provider="gutenberg", projects_searched=[], identities_used=[])
    found = list(provider.enumerate_author_sources(who or author(), options or CaptureOptions(), report, lambda *_: None))
    return {c.provider_item_id: c for c in found}, report


def test_contributor_cell_parsing_keeps_roles_dates_and_expansions():
    rows = parse_gutenberg_contributors(
        "Plato, 428? BCE-348? BCE; Jowett, Benjamin, 1817-1893 [Translator]; Chesterton, G. K. (Gilbert Keith), 1874-1936; Anon. [Illustrator]"
    )
    assert [(r["name"], r["role"], r["birth_year"], r["death_year"]) for r in rows] == [
        ("Plato", "author", -428, -348),
        ("Jowett, Benjamin", "translator", 1817, 1893),
        ("Chesterton, G. K. (Gilbert Keith)", "author", 1874, 1936),
        # An unmapped bracketed role is a contributor, never an author.
        ("Anon.", "contributor", None, None),
    ]
    assert rows[2]["normalized_name"] == "g k chesterton"
    assert rows[3]["raw_role"] == "Illustrator"


def test_open_ended_dates_are_not_invented():
    [row] = parse_gutenberg_contributors("Somebody, Anne, 1900-")
    assert (row["birth_year"], row["death_year"]) == (1900, None)


def test_legacy_flattened_catalogue_is_backfilled_once(tmp_path):
    db_path = tmp_path / "system.sqlite"
    _legacy_catalogue(db_path)
    GutenbergOfflineService(db_path, tmp_path / "archive.zip", start_worker=False)
    with sqlite3.connect(db_path) as db:
        contributors = db.execute("SELECT COUNT(*) FROM gutenberg_item_contributors").fetchone()[0]
        languages = db.execute("SELECT language_code FROM gutenberg_item_languages WHERE etext_id=2000 ORDER BY 1").fetchall()
        columns = {row[1] for row in db.execute("PRAGMA table_info(gutenberg_catalogue_books)")}
    assert contributors == 12
    assert [row[0] for row in languages] == ["de", "en"]
    assert "item_type" in columns
    # Constructing again (a restart) neither duplicates nor drops the projection.
    GutenbergOfflineService(db_path, tmp_path / "archive.zip", start_worker=False)
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM gutenberg_item_contributors").fetchone()[0] == contributors


def test_exact_enumeration_keeps_works_coauthors_languages_and_translations(catalogue):
    found, report = _enumerate(sg.GutenbergProvider(http_for(lambda r: httpx.Response(500), "gutenberg"), catalogue=catalogue))
    assert set(found) == {"1998", "1999", "2000", "2002"}
    assert found["1998"].contribution_role == "author"
    assert found["1998"].identity_confidence == "exact"
    assert found["2000"].contribution_role == "coauthor"
    assert found["2000"].document_languages == ["de", "en"]
    # A named translator is catalogue evidence of a translation.
    assert found["1999"].relationship_to_work == "translation"
    assert found["1999"].translators == ["Thomas Common"]
    assert found["1998"].relationship_to_work == "unknown"
    assert report.endpoint == "local catalogue"
    assert any(w.startswith("non_text_items_skipped:1") for w in report.warnings or [])


def test_namesake_with_different_dates_is_rejected(catalogue):
    rows = catalogue.sources_for_author(author().names(), birth_year=1844, death_year=1900)
    assert 2001 not in {row["etext_id"] for row in rows}


def test_given_name_match_without_dates_needs_review(catalogue):
    found, _ = _enumerate(sg.GutenbergProvider(http_for(lambda r: httpx.Response(500), "gutenberg"), catalogue=catalogue))
    assert found["2002"].identity_confidence == "needs_review"
    assert found["2002"].discovery_evidence["date_evidence"] is False


def test_translator_and_editor_roles_are_excluded_unless_requested(catalogue):
    provider = sg.GutenbergProvider(http_for(lambda r: httpx.Response(500), "gutenberg"), catalogue=catalogue)
    default, _ = _enumerate(provider)
    assert "2003" not in default and "2005" not in default
    wider, _ = _enumerate(provider, CaptureOptions(roles=["author", "coauthor", "translator", "editor"]))
    assert wider["2003"].contribution_role == "translator"
    assert wider["2005"].contribution_role == "editor"
    # Translating Schopenhauer does not make the work a "translation of Nietzsche".
    assert wider["2003"].relationship_to_work == "unknown"


def test_translations_and_languages_follow_the_options(catalogue):
    provider = sg.GutenbergProvider(http_for(lambda r: httpx.Response(500), "gutenberg"), catalogue=catalogue)
    no_translations, _ = _enumerate(provider, CaptureOptions(include_translations=False))
    assert "1999" not in no_translations and "1998" in no_translations
    translations_only, _ = _enumerate(provider, CaptureOptions(include_originals=False))
    assert "1999" in translations_only and "1998" not in translations_only
    english, _ = _enumerate(provider, CaptureOptions(languages=["en"]))
    assert set(english) == {"1999", "2000"}


def test_gutendex_fallback_when_the_catalogue_is_not_indexed(tmp_path, monkeypatch):
    no_rate_gate(monkeypatch)
    service = GutenbergOfflineService(tmp_path / "empty.sqlite", tmp_path / "archive.zip", start_worker=False)
    seen: list[str] = []

    def handler(request):
        seen.append(str(request.url))
        return json_response({"next": None, "results": [
            {"id": 1998, "title": "Also sprach Zarathustra", "media_type": "Text", "languages": ["de"], "copyright": False,
             "authors": [{"name": "Nietzsche, Friedrich Wilhelm", "birth_year": 1844, "death_year": 1900}], "translators": []},
            {"id": 3000, "title": "Other", "media_type": "Text", "languages": ["de"],
             "authors": [{"name": "Nietzsche, Friedrich Wilhelm", "birth_year": 1950}], "translators": []},
            {"id": 3001, "title": "Recording", "media_type": "Sound", "languages": ["de"],
             "authors": [{"name": "Nietzsche, Friedrich Wilhelm", "birth_year": 1844}], "translators": []},
        ]})

    found, report = _enumerate(sg.GutenbergProvider(http_for(handler, "gutenberg"), catalogue=service))
    assert set(found) == {"1998"}
    assert found["1998"].identity_confidence == "exact"
    assert found["1998"].rights_status == "provider_not_copyrighted_us"
    assert "gutenberg_catalogue_not_indexed_used_gutendex" in (report.warnings or [])
    assert seen[0].startswith("https://gutendex.com/books")


class _Meta:
    url = "https://gutendex.com/books/1998/"

    def __init__(self, text_url):
        self.text_url = text_url

    def raise_for_status(self):
        pass

    def json(self):
        return {"id": 1998, "title": "Also sprach Zarathustra", "authors": [{"name": NIETZSCHE}], "languages": ["de"],
                "formats": {"text/plain; charset=utf-8": self.text_url}}


class _Stream:
    def __init__(self, url, body):
        self.url = httpx.URL(url)
        self.body = body
        self.is_redirect = False
        self.headers = {}

    def raise_for_status(self):
        pass

    def iter_bytes(self):
        yield self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _remote(monkeypatch, text_url, body=b"Also sprach Zarathustra."):
    from app import gutenberg_catalogue

    local_reads: list[int] = []
    monkeypatch.setattr(gutenberg_catalogue.gutenberg_offline, "status", lambda: {"ready": False, "search_ready": True})
    monkeypatch.setattr(gutenberg_catalogue.gutenberg_offline, "text", lambda etext: local_reads.append(etext))
    monkeypatch.setattr(sg.httpx, "get", lambda url, **kw: _Meta(text_url))
    monkeypatch.setattr(sg.httpx, "stream", lambda method, url, **kw: _Stream(url, body))
    return local_reads


def test_one_verified_download_when_the_catalogue_is_indexed_but_the_collection_is_not(monkeypatch):
    local_reads = _remote(monkeypatch, "https://www.gutenberg.org/cache/epub/1998/pg1998.txt")
    candidate = sg.candidate_from_catalogue_row({"etext_id": 1998, "title": "Also sprach Zarathustra", "languages": ["de"], "identity_confidence": "exact"}, author())
    acquired = sg.GutenbergProvider(http_for(lambda r: httpx.Response(500), "gutenberg"), catalogue=object()).fetch_source(candidate, max_bytes=10_000)
    assert acquired.data == b"Also sprach Zarathustra."
    assert acquired.catalog_metadata["gutenberg_id"] == 1998
    assert acquired.catalog_metadata["provider"] == "gutenberg"
    assert len(acquired.catalog_metadata["source_sha256"]) == 64
    assert "catalog_record" not in acquired.catalog_metadata
    assert local_reads == []  # the full local collection is never required


def test_a_download_url_for_another_etext_is_an_identity_mismatch(monkeypatch):
    _remote(monkeypatch, "https://www.gutenberg.org/cache/epub/999/pg999.txt")
    candidate = sg.candidate_from_catalogue_row({"etext_id": 1998, "title": "Also sprach Zarathustra"}, author())
    with pytest.raises(CaptureError) as error:
        sg.GutenbergProvider(http_for(lambda r: httpx.Response(500), "gutenberg"), catalogue=object()).fetch_source(candidate, max_bytes=10_000)
    assert error.value.code == CaptureErrorCode.IDENTITY_MISMATCH


def test_an_oversize_text_is_refused(monkeypatch):
    _remote(monkeypatch, "https://www.gutenberg.org/cache/epub/1998/pg1998.txt", body=b"x" * 5000)
    candidate = sg.candidate_from_catalogue_row({"etext_id": 1998, "title": "Also sprach Zarathustra"}, author())
    with pytest.raises(CaptureError) as error:
        sg.GutenbergProvider(http_for(lambda r: httpx.Response(500), "gutenberg"), catalogue=object()).fetch_source(candidate, max_bytes=1000)
    assert error.value.code == CaptureErrorCode.SOURCE_TOO_LARGE
