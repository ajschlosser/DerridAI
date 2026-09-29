# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import hashlib

from app import document_intelligence as di
from app.corpus_publication import serialize_public_record


def test_document_text_offsets_and_projection_are_bound_to_record_text():
    records = [
        {"record_id": "r1", "record_revision": 1, "text": "Derrida cites Levinas."},
        {"record_id": "r2", "record_revision": 1, "text": "He then qualifies the claim."},
    ]
    text, spans = di.document_text_for_records(records)
    assert text == "Derrida cites Levinas.\n\nHe then qualifies the claim."
    assert spans[0]["start"] == 0 and spans[0]["end"] == len(records[0]["text"])
    assert spans[1]["start"] == spans[0]["end"] + 2

    levinas_start = text.index("Levinas")
    analysis = {
        "status": "ok",
        "profile": "scholarly",
        "provider": "booknlp",
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "record_spans": spans,
        "entity_clusters": [
            {
                "cluster_id": "c1",
                "canonical": "Emmanuel Levinas",
                "aliases": ["Levinas", "Emmanuel Levinas"],
                "entity_type": "PERSON",
            }
        ],
        "entities": [
            {
                "cluster_id": "c1",
                "start_char": levinas_start,
                "end_char": levinas_start + len("Levinas"),
                "text": "Levinas",
                "mention_type": "PROP",
                "entity_type": "PERSON",
            }
        ],
        "quotations": [],
    }
    counts = di.project_annotations_to_records(records, analysis)
    assert counts == {"entity_mentions": 1, "quotations": 0, "events": 0}
    projected = records[0]["document_intelligence"]
    assert projected["entities"][0]["label"] == "Emmanuel Levinas"
    assert projected["entities"][0]["start"] == records[0]["text"].index("Levinas")
    assert records[1]["document_intelligence"]["entities"] == []


def test_document_intelligence_hints_are_advisory_and_go_stale_after_text_edit():
    record = {"record_id": "r1", "text": "Derrida quotes Levinas."}
    digest = hashlib.sha256(record["text"].encode("utf-8")).hexdigest()
    record["document_intelligence"] = {
        "status": "ok",
        "record_text_sha256": digest,
        "entities": [
            {
                "entity_id": "c1",
                "label": "Emmanuel Levinas",
                "entity_type": "PERSON",
            }
        ],
        "quotations": [
            {
                "speaker_entity_id": "c1",
                "speaker": "Emmanuel Levinas",
                "text": "quoted text",
            }
        ],
    }
    hints = di.prompt_hints(record, ["persons", "quoted_speaker"])
    assert hints["person_candidates"] == ["Emmanuel Levinas"]
    assert hints["quotation_speaker_candidates"] == ["Emmanuel Levinas"]

    record["text"] += " Revised."
    assert di.prompt_hints(record, ["persons", "quoted_speaker"]) == {}


def test_normalization_keeps_provider_clusters_replaceable():
    normalized = di._normalize_provider_result(
        {
            "status": "ok",
            "provider": "booknlp",
            "entities": [
                {
                    "cluster_id": "7",
                    "start_char": 2,
                    "end_char": 9,
                    "text": "Levinas",
                    "mention_type": "PROP",
                    "entity_type": "PER",
                },
                {
                    "cluster_id": "7",
                    "start_char": 20,
                    "end_char": 37,
                    "text": "Emmanuel Levinas",
                    "mention_type": "PROP",
                    "entity_type": "PER",
                },
            ],
            "quotations": [],
            "characters": [],
        }
    )
    cluster = normalized["entity_clusters"][0]
    assert cluster["cluster_id"] == "7"
    assert cluster["canonical"] == "Emmanuel Levinas"
    assert set(cluster["aliases"]) == {"Levinas", "Emmanuel Levinas"}


def test_none_profile_is_explicitly_skipped():
    analysis = di.analyze_document(
        [{"record_id": "r1", "text": "Text."}],
        source_document_id="doc",
        language="English",
        request={"document_intelligence_profile": "none"},
    )
    assert analysis["status"] == "skipped"
    assert analysis["profile"] == "none"


def test_document_intelligence_stays_out_of_canonical_publication_records():
    record = {
        "record_id": "r1",
        "record_revision": 1,
        "source_document_id": "doc",
        "text": "Text.",
        "nlp_candidates": {"status": "ok"},
        "document_intelligence": {"status": "ok", "entities": [{"label": "X"}]},
    }
    public = serialize_public_record(record)
    assert "document_intelligence" not in public
    assert "nlp_candidates" not in public


def test_explicit_booknlp_request_without_worker_is_unavailable_not_spacy(monkeypatch):
    monkeypatch.delenv("DOCUMENT_NLP_BASE_URL", raising=False)
    monkeypatch.setattr(di, "_spacy_document_annotations", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("spaCy ran")))
    records = [{"record_id": "r1", "text": "Derrida wrote this."}]
    analysis = di.analyze_document(
        records, source_document_id="doc", language="English",
        request={"document_nlp_provider": "booknlp"},
    )
    assert (analysis["status"], analysis["provider"], analysis["reason"]) == (
        "unavailable", "booknlp", "provider_not_configured",
    )
    assert analysis["warnings"]

    monkeypatch.setenv("DOCUMENT_NLP_BASE_URL", "http://document-nlp:8090")
    monkeypatch.delenv("DOCUMENT_NLP_BASE_URL_FR", raising=False)
    french = di.analyze_document(
        records, source_document_id="doc", language="French",
        request={"document_nlp_provider": "booknlp"},
    )
    assert (french["status"], french["reason"]) == ("unavailable", "language_unsupported")


def test_booknlp_requests_route_each_language_to_its_own_worker(monkeypatch):
    calls: list[tuple[str, str]] = []

    def fake_call(text, *, language, base_url, **_kwargs):
        calls.append((language, base_url))
        return {"provider": "booknlp", "entities": [], "entity_clusters": [], "quotations": []}

    monkeypatch.setattr(di, "_call_booknlp", fake_call)
    monkeypatch.setattr(di, "_spacy_document_annotations", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("spaCy ran")))
    monkeypatch.setenv("DOCUMENT_NLP_BASE_URL", "http://document-nlp:8090")
    monkeypatch.setenv("DOCUMENT_NLP_BASE_URL_FR", "http://document-nlp-fr:8090")
    records = [{"record_id": "r1", "text": "Derrida wrote this."}]

    booknlp = {"document_nlp_provider": "booknlp"}
    english = di.analyze_document(records, source_document_id="doc", language="English", request=booknlp)
    french = di.analyze_document(records, source_document_id="doc", language="French", request=booknlp)

    assert english["selected_provider"] == "booknlp"
    assert (english["status"], french["status"]) == ("ok", "ok")
    monkeypatch.setenv("DOCUMENT_NLP_BASE_URL_ES", "http://document-nlp-es:8090")
    spanish = di.analyze_document(records, source_document_id="doc", language="es-MX", request=booknlp)
    assert spanish["status"] == "ok"
    assert calls == [
        ("en", "http://document-nlp:8090"),
        ("fr", "http://document-nlp-fr:8090"),
        ("es", "http://document-nlp-es:8090"),
    ]


def test_generic_worker_serves_only_its_declared_languages(monkeypatch):
    monkeypatch.setenv("DOCUMENT_NLP_BASE_URL", "http://document-nlp:8090")
    monkeypatch.delenv("DOCUMENT_NLP_BASE_URL_DE", raising=False)
    monkeypatch.delenv("DOCUMENT_NLP_LANGUAGES", raising=False)
    assert di.booknlp_url_for("en") == "http://document-nlp:8090"
    assert di.booknlp_url_for("de") == ""
    monkeypatch.setenv("DOCUMENT_NLP_LANGUAGES", "en, de")
    assert di.booknlp_url_for("de") == "http://document-nlp:8090"


def test_automatic_is_the_default_and_uses_spacy_where_booknlp_has_no_worker(monkeypatch):
    monkeypatch.setenv("DOCUMENT_NLP_BASE_URL", "http://document-nlp:8090")
    monkeypatch.delenv("DOCUMENT_NLP_BASE_URL_IT", raising=False)
    monkeypatch.delenv("DOCUMENT_NLP_LANGUAGES", raising=False)
    monkeypatch.setattr(di, "_call_booknlp", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("BookNLP called")))
    monkeypatch.setattr(
        di, "_spacy_document_annotations",
        lambda text, language: {"status": "ok", "provider": "spacy", "entities": [], "entity_clusters": []},
    )

    italian = di.analyze_document(
        [{"record_id": "r1", "text": "Machiavelli scrisse questo."}],
        source_document_id="doc", language="Italian", request={},
    )

    assert italian["selected_provider"] == "auto"
    assert (italian["status"], italian["provider"]) == ("ok", "spacy")
    assert italian["warnings"] == []
