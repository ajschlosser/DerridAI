# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from app.semantic_content_graph import build_semantic_content_graph


def _edge(graph, predicate):
    return next(edge for edge in graph["edges"] if edge["predicate"] == predicate)


def test_scholarly_graph_projects_existing_attribution_with_authority_and_evidence():
    record = {
        "record_id": "r1",
        "record_revision": 2,
        "text": "Heidegger questions presence while discussing Derrida.",
        "position_holder": "Martin Heidegger",
        "target": "presence",
        "stance": "questions",
        "persons": ["Martin Heidegger", "Jacques Derrida"],
        "concepts": ["presence"],
        "metadata_field_status": {
            "position_holder": {"status": "human_confirmed", "method": "llm"},
            "target": {"status": "human_confirmed", "method": "llm"},
            "stance": {"status": "human_confirmed", "method": "llm"},
        },
        "metadata_evidence": {
            "position_holder": {"block_ids": ["b1"]},
            "target": {"block_ids": ["b1"]},
            "stance": {"block_ids": ["b1"]},
        },
    }
    graph = build_semantic_content_graph([record], {"profile": "scholarly"})
    relation = _edge(graph, "questions")
    assert relation["relation_kind"] == "semantic"
    assert relation["authority_status"] == "human_confirmed"
    assert relation["record_ids"] == ["r1"]
    assert {item["field"] for item in relation["evidence_refs"]} == {
        "position_holder",
        "target",
        "stance",
    }


def test_cooccurrence_is_observational_not_a_claimed_relationship():
    record = {
        "record_id": "r1",
        "record_revision": 1,
        "text": "Derrida, Levinas, hospitality.",
        "persons": ["Jacques Derrida", "Emmanuel Levinas"],
        "concepts": ["hospitality"],
    }
    graph = build_semantic_content_graph([record], {"profile": "scholarly"})
    observed = [edge for edge in graph["edges"] if edge["predicate"] == "co_occurs"]
    assert observed
    assert all(edge["relation_kind"] == "observational" for edge in observed)
    assert all(edge["evidence_refs"] == [] for edge in observed)
    assert "Observational edges" in graph["epistemic_note"]


def test_fiction_profile_turns_person_clusters_into_characters_and_maps_dialogue_proximity():
    text = "Elizabeth speaks.\n\nDarcy replies."
    analysis = {
        "profile": "fiction",
        "provider": "booknlp",
        "text_sha256": "abc",
        "record_spans": [
            {"record_id": "r1", "start": 0, "end": 17},
            {"record_id": "r2", "start": 19, "end": len(text)},
        ],
        "entity_clusters": [
            {"cluster_id": "e", "canonical": "Elizabeth", "aliases": ["Elizabeth"], "entity_type": "PERSON"},
            {"cluster_id": "d", "canonical": "Darcy", "aliases": ["Darcy"], "entity_type": "PERSON"},
        ],
        "entities": [
            {"cluster_id": "e", "start_char": 0, "end_char": 9, "text": "Elizabeth"},
            {"cluster_id": "d", "start_char": 19, "end_char": 24, "text": "Darcy"},
        ],
    }
    records = [
        {
            "record_id": "r1",
            "record_revision": 1,
            "text": "Elizabeth speaks.",
            "document_intelligence": {
                "status": "ok",
                "entities": [{"entity_id": "e", "label": "Elizabeth"}],
                "quotations": [
                    {"speaker_entity_id": "e", "speaker": "Elizabeth"},
                    {"speaker_entity_id": "d", "speaker": "Darcy"},
                ],
            },
        },
        {
            "record_id": "r2",
            "record_revision": 1,
            "text": "Darcy replies.",
            "document_intelligence": {
                "status": "ok",
                "entities": [{"entity_id": "d", "label": "Darcy"}],
                "quotations": [],
            },
        },
    ]
    graph = build_semantic_content_graph(records, analysis)
    assert graph["summary"]["characters"] == 2
    dialogue = _edge(graph, "dialogue_proximity")
    assert dialogue["relation_kind"] == "observational"
    labels = {node["label"] for node in graph["nodes"] if node["type"] == "character"}
    assert labels == {"Elizabeth", "Darcy"}
