# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import hashlib

from app import document_intelligence as di


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
    assert counts == {"entity_mentions": 1, "quotations": 0}
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
