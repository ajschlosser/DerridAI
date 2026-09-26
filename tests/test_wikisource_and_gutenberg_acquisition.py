# Copyright 2026 Aaron John Schlosser, PhD.
"""Wikisource and Project Gutenberg imports bring in the whole work, and only the work.

Why: a Wikisource work's main page is usually its title page and contents; the text lives on subpages. Importing it
brought in only the contents, so a whole book became about four records. Wikisource page chrome (header, navigation
arrows, maintenance notices, the hidden ws-data string) was also extracted as if it were the author's text. And
Gutendex/Gutenberg now answer with a redirect, so imports through the catalogue failed.
How: stubs the MediaWiki parse call and the Gutenberg HTTP calls; checks the extracted text directly.
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app import source_gutenberg as sg  # noqa: E402
from app.source_text import html_to_text  # noqa: E402

CONTENTS = """
<div class="ws-noexport ws-header noprint"><a href="/wiki/Prev">←</a> The Book by An Author <a>→</a></div>
<table class="plainlinks metadata ambox"><tr><td>This work is not backed by a scanned copy.</td></tr></table>
<div id="ws-data" class="ws-noexport" style="speak:none">184350The Book1921An Author</div>
<p>THE BOOK</p>
<ul>
  <li><a href="/wiki/The_Book/Chapter_I">Chapter I</a></li>
  <li><a href="/wiki/The_Book/Chapter_II#top">Chapter II</a></li>
  <li><a href="/wiki/The_Book/Chapter_I">Chapter I again</a></li>
  <li><a href="/wiki/Author:An_Author">An Author</a></li>
</ul>
"""
PAGES = {
    "The Book": CONTENTS,
    "The Book/Chapter I": "<p>It was not the first time the city had refused.</p>",
    "The Book/Chapter II": "<p>Only a guest can say whether he was welcomed.</p>",
}


@pytest.fixture
def wikisource(monkeypatch):
    fetched: list[str] = []

    def parse(parsed, title):
        fetched.append(title)
        return title, PAGES[title]

    monkeypatch.setattr(sg, "_wikisource_parse", parse)
    return fetched


def test_a_works_contents_page_brings_in_its_chapters_in_order(wikisource):
    data, name, content_type = sg.fetch_source_url(
        "https://en.wikisource.org/wiki/The_Book", max_bytes=1_000_000
    )
    assert wikisource == ["The Book", "The Book/Chapter I", "The Book/Chapter II"]
    text, _ = html_to_text(data.decode("utf-8"))
    assert text.index("THE BOOK") < text.index("the first time") < text.index("Only a guest")
    # Each chapter keeps the page it came from in the stored source.
    assert 'data-wikisource-page="The Book/Chapter II"' in data.decode("utf-8")
    assert name == "The_Book.html" and content_type.startswith("text/html")


def test_wikisource_page_chrome_is_not_extracted_as_text(wikisource):
    data, _, _ = sg.fetch_source_url("https://en.wikisource.org/wiki/The_Book", max_bytes=1_000_000)
    text, _ = html_to_text(data.decode("utf-8"))
    for chrome in ("←", "not backed by a scanned copy", "184350"):
        assert chrome not in text


def test_a_work_too_large_for_the_limit_fails_explicitly(wikisource):
    with pytest.raises(ValueError, match="subpages"):
        sg.fetch_source_url("https://en.wikisource.org/wiki/The_Book", max_bytes=len(CONTENTS) + 40)


def test_hidden_chrome_is_skipped_but_nested_body_text_survives():
    text, _ = html_to_text(
        '<div class="noprint"><div>nav <span>links</span></div></div>'
        "<p>Before <span style='display: none'>hidden</span>after.</p>"
        '<div class="metadata">A generic class is kept.</div>'
    )
    assert "nav" not in text and "hidden" not in text
    assert "Before after." in text
    assert "A generic class is kept." in text


class _Stream:
    def __init__(self, url, status, location="", body=b""):
        self.url, self.status_code, self.headers, self._body = url, status, {"location": location}, body

    @property
    def is_redirect(self):
        return 300 <= self.status_code < 400

    def raise_for_status(self):
        if self.status_code >= 300:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_bytes(self):
        yield self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _gutenberg(monkeypatch, redirect_to):
    import httpx

    class _Meta:
        url = "https://gutendex.com/books/1342/"

        def raise_for_status(self):
            pass

        def json(self):
            return {"id": 1342, "title": "Pride and Prejudice", "authors": [{"name": "Austen, Jane"}],
                    "formats": {"text/plain; charset=utf-8": "https://www.gutenberg.org/ebooks/1342.txt.utf-8"}}

    requested: list[str] = []
    monkeypatch.setattr(sg.httpx, "get", lambda url, **kw: requested.append(url) or _Meta())

    def stream(method, url, **kw):
        assert kw.get("follow_redirects") is False
        requested.append(url)
        if url.endswith(".txt.utf-8"):
            return _Stream(httpx.URL(url), 302, redirect_to)
        return _Stream(httpx.URL(url), 200, body=b"It is a truth universally acknowledged.")

    monkeypatch.setattr(sg.httpx, "stream", stream)
    return requested


def test_gutenberg_follows_its_one_redirect_to_the_same_editions_cache_file(monkeypatch):
    requested = _gutenberg(monkeypatch, "http://www.gutenberg.org/cache/epub/1342/pg1342.txt")
    text, catalog = sg._gutendex_etext(1342)
    assert "universally acknowledged" in text
    assert requested[0] == "https://gutendex.com/books/1342/"
    assert urlparse(requested[-1]).scheme == "https"
    assert catalog["title"] == "Pride and Prejudice"


def test_gutenberg_refuses_a_redirect_to_another_edition_or_site(monkeypatch):
    _gutenberg(monkeypatch, "https://www.gutenberg.org/cache/epub/99/pg99.txt")
    with pytest.raises(ValueError, match="does not identify"):
        sg._gutendex_etext(1342)
    _gutenberg(monkeypatch, "https://mirror.example/cache/epub/1342/pg1342.txt")
    with pytest.raises(ValueError, match="Unsupported"):
        sg._gutendex_etext(1342)
