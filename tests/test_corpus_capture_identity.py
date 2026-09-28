# Copyright 2026 Aaron John Schlosser, PhD.
"""Corpus Capture author resolution: people only, never auto-chosen, identity kept exact.

Why: a capture binds every discovered source to one person. A painting or ship called
"Nietzsche", a silently picked namesake, or a lost QID would attach the wrong works to
the corpus, which is a high-severity attribution failure.
How: Wikidata answers through an ``httpx.MockTransport``; no request leaves the process.
"""
from __future__ import annotations

import httpx
import pytest
from _capture_support import http_for, json_response, no_rate_gate
from app import source_wikidata as wd
from app.source_identity import (
    CaptureError,
    CaptureErrorCode,
    PersonName,
    normalize_language,
    normalize_languages,
)

pytestmark = pytest.mark.unit


def _claim(value):
    datavalue = {"value": {"id": value}} if str(value).startswith("Q") else {"value": {"time": value}}
    return {"mainsnak": {"snaktype": "value", "datavalue": datavalue}}


def _entity(qid, label, *, human=True, description="", aliases=(), born=None, died=None, sitelinks=None, gutenberg=None):
    claims = {"P31": [_claim("Q5" if human else "Q3305213")]}
    if born:
        claims["P569"] = [_claim(born)]
    if died:
        claims["P570"] = [_claim(died)]
    if gutenberg:
        claims["P1938"] = [{"mainsnak": {"snaktype": "value", "datavalue": {"value": gutenberg}}}]
    return {
        "id": qid,
        "labels": {"en": {"value": label}},
        "descriptions": {"en": {"value": description}},
        "aliases": {"en": [{"value": alias} for alias in aliases]},
        "claims": claims,
        "sitelinks": sitelinks or {},
    }


ENTITIES = {
    "Q9358": _entity(
        "Q9358", "Friedrich Nietzsche", description="German philosopher (1844–1900)",
        aliases=("Friedrich Wilhelm Nietzsche", "F. W. Nietzsche"), born="+1844-10-15T00:00:00Z", died="+1900-08-25T00:00:00Z",
        sitelinks={"dewikisource": {"title": "Friedrich Nietzsche"}, "enwikisource": {"title": "Author:Friedrich Wilhelm Nietzsche"}, "sourceswiki": {"title": "Author:Friedrich Nietzsche"}, "enwiki": {"title": "Friedrich Nietzsche"}},
        gutenberg="779",
    ),
    "Q1000": _entity("Q1000", "Friedrich Nietzsche", description="German footballer", born="+1901-01-01T00:00:00Z"),
    "Q2000": _entity("Q2000", "Portrait of Friedrich Nietzsche", human=False, description="painting by Edvard Munch"),
    "Q7": _entity("Q7", "Plato", born="-0428-00-00T00:00:00Z", died="-0348-00-00T00:00:00Z"),
}


@pytest.fixture
def wikidata(monkeypatch):
    no_rate_gate(monkeypatch)
    requests: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "www.wikidata.org"
        params = dict(request.url.params)
        requests.append(params)
        if params["action"] == "wbsearchentities":
            hits = {"nietzsche": ["Q9358", "Q2000", "Q1000"], "plato": ["Q7"]}.get(params["search"].lower(), [])
            return json_response({"search": [{"id": qid} for qid in hits]})
        if params["action"] == "wbgetentities":
            ids = params["ids"].split("|")
            return json_response({"entities": {qid: ENTITIES.get(qid, {"id": qid, "missing": ""}) for qid in ids}})
        raise AssertionError(params)

    return http_for(handler), requests


def test_search_offers_every_matching_person_and_filters_non_humans(wikidata):
    http, _ = wikidata
    people = wd.search_authors(http, "Nietzsche")
    # Both namesakes are offered for an explicit choice; the painting is not a person.
    assert [person.wikidata_qid for person in people] == ["Q9358", "Q1000"]
    philosopher = people[0]
    assert philosopher.birth_year == 1844 and philosopher.death_year == 1900
    assert "Friedrich Wilhelm Nietzsche" in philosopher.aliases
    assert philosopher.label not in philosopher.aliases
    assert philosopher.wikisource_sitelinks == {"de": "Friedrich Nietzsche", "en": "Author:Friedrich Wilhelm Nietzsche", "mul": "Author:Friedrich Nietzsche"}


def test_search_without_a_match_is_empty_not_an_error(wikidata):
    http, _ = wikidata
    assert wd.search_authors(http, "Zzyzx Nobody") == []
    assert wd.search_authors(http, "   ") == []


def test_bce_life_dates_are_negative_years(wikidata):
    http, _ = wikidata
    [plato] = wd.search_authors(http, "Plato")
    assert (plato.birth_year, plato.death_year) == (-428, -348)


def test_resolve_preserves_the_chosen_qid_and_external_ids(wikidata):
    http, _ = wikidata
    resolved = wd.resolve_author(http, "Q9358")
    assert resolved.wikidata_qid == "Q9358"
    assert resolved.identity_id == "wikidata:Q9358"
    assert resolved.canonical_name == "Friedrich Nietzsche"
    assert resolved.external_ids == {"gutenberg_author": "779"}
    assert "Friedrich Wilhelm Nietzsche" in resolved.names()


def test_resolve_rejects_a_non_person_qid(wikidata):
    http, _ = wikidata
    with pytest.raises(CaptureError) as error:
        wd.resolve_author(http, "Q2000")
    assert error.value.code == CaptureErrorCode.IDENTITY_MISMATCH


@pytest.mark.parametrize("qid", ["Q0", "P31", "Q9358|Q1000", ""])
def test_resolve_refuses_malformed_ids_without_a_request(wikidata, qid):
    http, requests = wikidata
    with pytest.raises(CaptureError) as error:
        wd.resolve_author(http, qid)
    assert error.value.code == CaptureErrorCode.AUTHOR_NOT_FOUND
    assert requests == []


def test_resolve_reports_a_missing_entity(wikidata):
    http, _ = wikidata
    with pytest.raises(CaptureError) as error:
        wd.resolve_author(http, "Q123456")
    assert error.value.code == CaptureErrorCode.AUTHOR_NOT_FOUND


def test_person_names_compare_across_name_order_case_and_diacritics():
    assert PersonName.parse("Nietzsche, Friedrich Wilhelm") == PersonName.parse("friedrich wilhelm NIETZSCHE")
    assert PersonName.parse("Böhme, Jakob").surname == PersonName.parse("Jakob Bohme").surname == "bohme"
    chesterton = PersonName.parse("Chesterton, G. K. (Gilbert Keith)")
    assert (chesterton.surname, chesterton.first_given, chesterton.full) == ("chesterton", "g", "g k chesterton")


def test_language_codes_normalize_without_guessing():
    assert normalize_language("fre") == "fr"
    assert normalize_language("EN_us") == "en-us"
    assert normalize_language("Klingonese") is None
    assert normalize_languages("de; en, la") == ["de", "en", "la"]
