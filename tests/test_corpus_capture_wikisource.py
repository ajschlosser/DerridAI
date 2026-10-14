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

"""Wikisource discovery for Corpus Capture: every project, every linked work, roles from headings.

Why: an author page lists the person's works next to translations they made and works
about them. Reading a "Works about" link as authorship, dropping links past the first
API page, or letting one missing project end discovery would misstate coverage.
How: MediaWiki answers through ``httpx.MockTransport`` keyed by host and action.
"""
from __future__ import annotations

import httpx
import pytest
from _capture_support import author, http_for, json_response, no_rate_gate
from app import source_wikisource as ws
from app.source_identity import CaptureOptions
from app.source_provider import DiscoveryReport
from app.source_text import html_to_text

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _fast(monkeypatch):
    no_rate_gate(monkeypatch)


SITEMATRIX = {
    "sitematrix": {
        "count": 4,
        "0": {"code": "de", "name": "Deutsch", "localname": "German", "site": [
            {"url": "https://de.wikipedia.org", "code": "wiki", "lang": "de"},
            {"url": "https://de.wikisource.org", "code": "wikisource", "lang": "de"},
        ]},
        "1": {"code": "fr", "name": "français", "localname": "French", "site": [{"url": "https://fr.wikisource.org", "code": "wikisource", "lang": "fr"}]},
        "2": {"code": "ang", "name": "Englisc", "localname": "Old English", "site": [{"url": "https://ang.wikisource.org", "code": "wikisource", "lang": "ang", "closed": True}]},
        "specials": [{"dbname": "sourceswiki", "code": "sources", "url": "https://wikisource.org"}, {"dbname": "metawiki", "code": "meta"}],
    }
}


def test_sitematrix_lists_open_projects_and_the_multilingual_one():
    projects = ws.parse_sitematrix(SITEMATRIX)
    assert [p["code"] for p in projects] == ["de", "fr", "mul"]
    assert projects[0]["name"] == "German"


def test_project_discovery_is_cached_and_its_fallback_is_labelled(monkeypatch):
    monkeypatch.setitem(ws._PROJECT_CACHE, "projects", None)
    calls: list[str] = []

    def down(request):
        calls.append(str(request.url))
        return httpx.Response(503)

    fallback = ws.discover_projects(http_for(down), now=1000.0)
    assert fallback["authoritative"] is False
    assert fallback["warning"]
    assert {p["code"] for p in fallback["projects"]} >= {"en", "fr", "de"}

    monkeypatch.setitem(ws._PROJECT_CACHE, "projects", None)
    live = ws.discover_projects(http_for(lambda r: json_response(SITEMATRIX)), now=2000.0)
    assert live["authoritative"] is True
    # Within the TTL the cached list is served without another request.
    assert ws.discover_projects(http_for(down), now=2001.0) is live


def test_localized_namespaces_are_read_from_siteinfo():
    def handler(request):
        return json_response({"query": {
            "namespaces": {"0": {"name": ""}, "102": {"name": "Auteur", "canonical": "Author"}, "104": {"name": "Page", "canonical": "Page"}},
            "namespacealiases": [{"id": 102, "alias": "Autor"}],
            "proofreadnamespaces": {"page": {"id": 104}, "index": {"id": 106}},
        }})

    provider = ws.WikisourceProvider(http_for(handler))
    info = provider.namespaces("fr")
    assert info["by_name"]["auteur"] == info["by_name"]["author"] == info["by_name"]["autor"] == 102
    assert (info["page"], info["index"]) == (104, 106)


def test_link_collection_follows_continuation_to_the_end():
    pages = [
        {"query": {"pages": [{"title": "A", "links": [{"title": "W1"}, {"title": "W2"}]}]}, "continue": {"plcontinue": "1|0|W3", "continue": "||"}},
        {"query": {"pages": [{"title": "A", "links": [{"title": "W3"}, {"title": "W1"}]}]}},
    ]
    seen: list[dict[str, str]] = []

    def handler(request):
        seen.append(dict(request.url.params))
        return json_response(pages[len(seen) - 1])

    titles, complete = ws.collect_links(http_for(handler), "https://en.wikisource.org", "Author:A")
    assert titles == ["W1", "W2", "W3"]
    assert complete is True
    assert seen[1]["plcontinue"] == "1|0|W3"


@pytest.mark.parametrize(
    ("heading", "role"),
    [
        ("Works", "author"),
        ("Œuvres", "author"),
        ("Werke", "author"),
        ("Translations", "translator"),
        ("Übersetzungen", "translator"),
        ("Works about Nietzsche", "about_author"),
        ("Sur Nietzsche", "about_author"),
        ("Miscellany", "unknown"),
        ("", "unknown"),
    ],
)
def test_section_headings_classify_roles_deterministically(heading, role):
    assert ws.classify_section(heading) == role


AUTHOR_PAGE = """
<h2>Works</h2><ul><li><a href="/wiki/Thus_Spake_Zarathustra">TSZ</a></li>
<li><a href="/wiki/Thus_Spake_Zarathustra/Prologue">Prologue</a></li>
<li><a href="/wiki/Encyclopedia/Nietzsche">Entry</a></li></ul>
<h2>Translations</h2><ul><li><a href="/wiki/Some_Greek_Poem">Poem</a></li></ul>
<h2>Works about Nietzsche</h2><ul><li><a href="/wiki/The_Philosophy_of_Nietzsche">About</a></li></ul>
<h2>Miscellany</h2><ul><li><a href="/wiki/Letter_to_a_friend">Letter</a></li></ul>
"""
LINKS = ["Thus Spake Zarathustra", "Thus Spake Zarathustra/Prologue", "Encyclopedia/Nietzsche", "Some Greek Poem", "The Philosophy of Nietzsche", "Letter to a friend"]


def test_author_links_group_subpages_under_their_work_once():
    classified = {title: role for title, role, _section in ws.classify_author_links(LINKS, ws.link_sections(AUTHOR_PAGE))}
    assert classified["Thus Spake Zarathustra"] == "author"
    assert "Thus Spake Zarathustra/Prologue" not in classified
    # An entry inside someone else's collection is not a work by the person.
    assert classified["Encyclopedia/Nietzsche"] == "unknown"
    assert classified["The Philosophy of Nietzsche"] == "about_author"


def _wikisource(missing: set[str]):
    def handler(request):
        host = request.url.host
        code = host.split(".")[0] if host != "wikisource.org" else "mul"
        params = dict(request.url.params)
        if code in missing:
            return json_response({"query": {"pages": [{"title": params.get("titles"), "missing": True}]}})
        if params.get("prop") == "links":
            return json_response({"query": {"pages": [{"title": params["titles"], "links": [{"title": t} for t in LINKS]}]}})
        if params.get("action") == "parse":
            return json_response({"parse": {"title": params["page"], "text": AUTHOR_PAGE, "pageid": 7, "revid": 70}})
        raise AssertionError(params)

    return handler


def _discover(provider, options=None, sitelinks=None):
    report = DiscoveryReport(provider="wikisource", projects_searched=[], identities_used=[])
    who = author(wikisource_sitelinks=sitelinks or {"de": "Friedrich Nietzsche", "en": "Author:Friedrich Nietzsche", "fr": "Auteur:Friedrich Nietzsche"})
    return list(provider.enumerate_author_sources(who, options or CaptureOptions(), report, lambda *_: None)), report


def test_about_author_and_translator_links_are_excluded_by_default_but_unknowns_stay_for_review():
    found, report = _discover(ws.WikisourceProvider(http_for(_wikisource(set()))), sitelinks={"en": "Author:Friedrich Nietzsche"})
    by_title = {c.title: c for c in found}
    assert set(by_title) == {"Thus Spake Zarathustra", "Encyclopedia/Nietzsche", "Letter to a friend"}
    tsz = by_title["Thus Spake Zarathustra"]
    assert (tsz.contribution_role, tsz.identity_confidence, tsz.document_author) == ("author", "exact", "Friedrich Nietzsche")
    assert tsz.provider_item_id == "en:Thus Spake Zarathustra"
    assert tsz.document_languages == ["en"] and tsz.original_language is None
    assert tsz.discovery_evidence["section"] == "Works"
    assert by_title["Letter to a friend"].identity_confidence == "needs_review"
    assert report.projects_searched == ["en"]


def test_about_author_is_included_only_when_requested():
    found, _ = _discover(ws.WikisourceProvider(http_for(_wikisource(set()))), CaptureOptions(roles=["author", "about_author"]), sitelinks={"en": "A"})
    assert "The Philosophy of Nietzsche" in {c.title for c in found}


def test_a_missing_author_page_on_one_project_does_not_stop_the_others():
    found, report = _discover(ws.WikisourceProvider(http_for(_wikisource({"fr"}))))
    assert report.projects_searched == ["de", "en"]
    assert [(e["project"], e["code"]) for e in report.errors or []] == [("fr", "source_not_found")]
    assert {c.source_project_language for c in found} == {"de", "en"}


def test_language_option_limits_projects():
    found, report = _discover(ws.WikisourceProvider(http_for(_wikisource(set()))), CaptureOptions(languages=["de"]))
    assert report.projects_searched == ["de"]
    assert {c.document_languages[0] for c in found} == {"de"}


def test_subpages_are_deduplicated_and_bounded():
    links = "".join(f'<a href="/wiki/Big_Work/Part_{i}">{i}</a><a href="/wiki/Big_Work/Part_{i}">again</a>' for i in range(ws.MAX_WIKISOURCE_SUBPAGES + 50))
    titles = ws.wikisource_subpage_titles(links + '<a href="/wiki/Other/Part_1">x</a>', "Big Work")
    assert len(titles) == ws.MAX_WIKISOURCE_SUBPAGES
    assert len(set(titles)) == len(titles)
    assert all(t.startswith("Big Work/") for t in titles)


def test_script_in_fetched_html_is_stored_as_inert_data_and_never_becomes_text():
    pages = {
        "Work": '<p>Only a guest can say.</p><script>alert("x"); window.location="https://evil.example"</script><a href="/wiki/Work/I">I</a>',
        "Work/I": '<p>It was not the first time.</p><script src="https://evil.example/x.js"></script>',
    }

    def handler(request):
        params = dict(request.url.params)
        if params.get("action") == "parse":
            return json_response({"parse": {"title": params["page"], "text": pages[params["page"]], "pageid": 1, "revid": 2}})
        return json_response({"query": {"namespaces": {}}})

    provider = ws.WikisourceProvider(http_for(handler))
    from _capture_support import candidate

    acquired = provider.fetch_source(candidate("en:Work", "Work", provider="wikisource", source_project_language="en"), max_bytes=100_000)
    assert acquired.content_type.startswith("text/html")
    assert [page["title"] for page in acquired.catalog_metadata["wikisource_pages"]] == ["Work", "Work/I"]
    text, _ = html_to_text(acquired.data.decode("utf-8"))
    assert "Only a guest can say." in text and "It was not the first time." in text
    assert "alert" not in text and "evil.example" not in text
