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

from __future__ import annotations

from app.metadata_schema import default_schema
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


def test_numeric_document_annotations_do_not_become_semantic_entities():
    analysis = {
        "profile": "scholarly",
        "provider": "spacy",
        "record_spans": [{"record_id": "r1", "start": 0, "end": 38}],
        "entity_clusters": [
            {
                "cluster_id": "person",
                "canonical": "Jacques Derrida",
                "aliases": ["Derrida"],
                "entity_type": "PERSON",
            },
            {
                "cluster_id": "count",
                "canonical": "3",
                "aliases": ["3"],
                "entity_type": "CARDINAL",
            },
            {
                "cluster_id": "year",
                "canonical": "1972",
                "aliases": ["1972"],
                "entity_type": "DATE",
            },
        ],
        "entities": [
            {
                "cluster_id": "person",
                "start_char": 0,
                "end_char": 7,
                "text": "Derrida",
                "entity_type": "PERSON",
            },
            {
                "cluster_id": "count",
                "start_char": 18,
                "end_char": 19,
                "text": "3",
                "entity_type": "CARDINAL",
            },
            {
                "cluster_id": "year",
                "start_char": 30,
                "end_char": 34,
                "text": "1972",
                "entity_type": "DATE",
            },
        ],
    }
    records = [
        {
            "record_id": "r1",
            "record_revision": 1,
            "text": "Derrida published 3 essays in 1972.",
        }
    ]

    graph = build_semantic_content_graph(records, analysis)

    labels = {node["label"] for node in graph["nodes"]}
    assert "Jacques Derrida" in labels
    assert "3" not in labels
    assert "1972" not in labels


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


def test_aggregate_relation_authority_is_conservative():
    base = {
        "text": "Heidegger questions presence.",
        "position_holder": "Martin Heidegger",
        "target": "presence",
        "stance": "questions",
    }
    confirmed = {
        **base,
        "record_id": "r1",
        "record_revision": 1,
        "metadata_field_status": {
            "position_holder": {"status": "human_confirmed"},
            "target": {"status": "human_confirmed"},
            "stance": {"status": "human_confirmed"},
        },
    }
    unreviewed = {
        **base,
        "record_id": "r2",
        "record_revision": 1,
        "metadata_field_status": {
            "position_holder": {"status": "unresolved"},
            "target": {"status": "unresolved"},
            "stance": {"status": "unresolved"},
        },
    }
    graph = build_semantic_content_graph([confirmed, unreviewed], {"profile": "scholarly"})
    assert _edge(graph, "questions")["authority_status"] == "unreviewed"


def test_target_reuses_existing_person_entity_before_falling_back_to_concept():
    analysis = {
        "profile": "scholarly",
        "provider": "booknlp",
        "entity_clusters": [
            {
                "cluster_id": "d",
                "canonical": "Jacques Derrida",
                "aliases": ["Derrida"],
                "entity_type": "PERSON",
            }
        ],
        "entities": [],
        "record_spans": [],
    }
    record = {
        "record_id": "r1",
        "record_revision": 1,
        "text": "Heidegger addresses Derrida.",
        "position_holder": "Martin Heidegger",
        "target": "Derrida",
    }
    graph = build_semantic_content_graph([record], analysis)
    edge = _edge(graph, "addresses")
    target = next(node for node in graph["nodes"] if node["id"] == edge["target"])
    assert target["type"] == "person"
    assert target["label"] == "Jacques Derrida"


def test_document_mentions_are_not_double_counted_when_metadata_reuses_entity():
    analysis = {
        "profile": "scholarly",
        "provider": "booknlp",
        "record_spans": [{"record_id": "r1", "start": 0, "end": 17}],
        "entity_clusters": [
            {
                "cluster_id": "e",
                "canonical": "Emmanuel Levinas",
                "aliases": ["Levinas"],
                "entity_type": "PERSON",
            }
        ],
        "entities": [
            {
                "cluster_id": "e",
                "start_char": 0,
                "end_char": 7,
                "text": "Levinas",
                "entity_type": "PERSON",
            }
        ],
    }
    records = [
        {
            "record_id": "r1",
            "record_revision": 1,
            "text": "Levinas appears.",
            "persons": ["Levinas"],
            "document_intelligence": {
                "status": "ok",
                "entities": [{"entity_id": "e", "label": "Emmanuel Levinas"}],
                "quotations": [],
            },
        }
    ]
    graph = build_semantic_content_graph(records, analysis)
    node = next(node for node in graph["nodes"] if node["label"] == "Emmanuel Levinas")
    assert node["mention_count"] == 1
    assert node["record_ids"] == ["r1"]


def test_fiction_agent_patient_observation_is_directed_and_keeps_verb():
    analysis = {
        "profile": "fiction",
        "provider": "booknlp",
        "record_spans": [{"record_id": "r1", "start": 0, "end": 22}],
        "entity_clusters": [
            {
                "cluster_id": "a",
                "canonical": "Alice",
                "aliases": ["Alice"],
                "entity_type": "PERSON",
            },
            {
                "cluster_id": "b",
                "canonical": "Bob",
                "aliases": ["Bob"],
                "entity_type": "PERSON",
            },
        ],
        "entities": [],
        "characters": [
            {
                "cluster_id": "a",
                "actions_as_agent": [
                    {
                        "text": "helped",
                        "lemma": "help",
                        "token_id": 1,
                        "start_char": 6,
                        "end_char": 12,
                    }
                ],
                "actions_as_patient": [],
                "possessions": [],
                "modifiers": [],
            },
            {
                "cluster_id": "b",
                "actions_as_agent": [],
                "actions_as_patient": [
                    {
                        "text": "helped",
                        "lemma": "help",
                        "token_id": 1,
                        "start_char": 6,
                        "end_char": 12,
                    }
                ],
                "possessions": [],
                "modifiers": [],
            },
        ],
    }
    records = [
        {
            "record_id": "r1",
            "record_revision": 1,
            "text": "Alice helped Bob.",
            "document_intelligence": {"status": "ok", "entities": [], "quotations": []},
        }
    ]
    graph = build_semantic_content_graph(records, analysis)
    edge = _edge(graph, "acts_on")
    source = next(node for node in graph["nodes"] if node["id"] == edge["source"])
    target = next(node for node in graph["nodes"] if node["id"] == edge["target"])
    assert source["label"] == "Alice"
    assert target["label"] == "Bob"
    assert edge["relation_kind"] == "observational"
    assert edge["observations"][0]["verb"] == "help"
    assert edge["record_ids"] == ["r1"]
    alice = source
    assert alice["character_profile"]["actions_as_agent"][0]["label"] == "help"


def _renamed_default_schema(renames):
    schema = default_schema()
    return schema.model_copy(
        update={
            "fields": [
                field.model_copy(update={"name": renames.get(field.name, field.name)})
                for field in schema.fields
            ]
        }
    )


def test_graph_uses_semantic_identity_when_attribution_fields_are_renamed():
    schema = _renamed_default_schema(
        {
            "position_holder": "interlocutor",
            "target": "object_of_stance",
            "stance": "orientation",
        }
    )
    record = {
        "record_id": "r-semantic",
        "record_revision": 1,
        "text": "Heidegger questions presence.",
        "interlocutor": "Martin Heidegger",
        "object_of_stance": "presence",
        "orientation": "questions",
        "metadata_field_status": {
            "interlocutor": {"status": "human_confirmed"},
            "object_of_stance": {"status": "human_confirmed"},
            "orientation": {"status": "human_confirmed"},
        },
        "metadata_evidence": {
            "interlocutor": {"block_ids": ["b1"]},
            "object_of_stance": {"block_ids": ["b1"]},
            "orientation": {"block_ids": ["b1"]},
        },
    }

    graph = build_semantic_content_graph([record], {"profile": "scholarly"}, schema=schema)

    relation = _edge(graph, "questions")
    assert relation["authority_status"] == "human_confirmed"
    assert relation["supporting_fields"] == [
        "interlocutor",
        "object_of_stance",
        "orientation",
    ]
    assert {item["field"] for item in relation["evidence_refs"]} == {
        "interlocutor",
        "object_of_stance",
        "orientation",
    }


def test_graph_uses_semantic_identity_when_indexing_fields_are_renamed():
    schema = _renamed_default_schema(
        {
            "persons": "people_index",
            "concepts": "idea_index",
            "works_referenced": "work_index",
            "topics": "topic_index",
        }
    )
    record = {
        "record_id": "r-index",
        "record_revision": 1,
        "text": "Levinas discusses hospitality in Totality and Infinity.",
        "people_index": ["Emmanuel Levinas"],
        "idea_index": ["hospitality"],
        "work_index": ["Totality and Infinity"],
        "topic_index": ["ethics"],
    }

    graph = build_semantic_content_graph([record], {"profile": "scholarly"}, schema=schema)

    typed_labels = {(node["type"], node["label"]) for node in graph["nodes"]}
    assert ("person", "Emmanuel Levinas") in typed_labels
    assert ("concept", "hospitality") in typed_labels
    assert ("work", "Totality and Infinity") in typed_labels
    assert ("topic", "ethics") in typed_labels
    assert any(edge["predicate"] == "co_occurs" for edge in graph["edges"])


def test_graph_uses_semantic_identity_when_quotation_fields_are_renamed():
    schema = _renamed_default_schema(
        {
            "speaker": "textual_voice",
            "quoted_author": "citation_author",
            "quoted_work": "citation_work",
        }
    )
    record = {
        "record_id": "r-quote",
        "record_revision": 1,
        "text": "Derrida quotes Levinas's Totality and Infinity.",
        "textual_voice": "Jacques Derrida",
        "citation_author": "Emmanuel Levinas",
        "citation_work": "Totality and Infinity",
        "metadata_field_status": {
            "textual_voice": {"status": "human_confirmed"},
            "citation_author": {"status": "human_confirmed"},
            "citation_work": {"status": "human_confirmed"},
        },
    }

    graph = build_semantic_content_graph([record], {"profile": "scholarly"}, schema=schema)

    quotes = _edge(graph, "quotes")
    quoted_work = _edge(graph, "quoted_work")
    assert quotes["supporting_fields"] == ["textual_voice", "citation_author"]
    assert quoted_work["supporting_fields"] == ["citation_author", "citation_work"]


def test_schema_aware_graph_does_not_assign_builtin_semantics_to_unrelated_custom_fields():
    schema = default_schema()
    schema = schema.model_copy(
        update={
            "fields": [
                *schema.fields,
                schema.fields[0].model_copy(
                    update={
                        "field_id": "field-unrelated-person-list",
                        "name": "cast",
                        "label": "Cast",
                        "semantic_compatibility_id": None,
                    }
                ),
            ]
        }
    )
    record = {
        "record_id": "r-custom",
        "record_revision": 1,
        "text": "A custom list should remain ordinary metadata.",
        "cast": ["Not a graph person"],
    }

    graph = build_semantic_content_graph([record], {"profile": "scholarly"}, schema=schema)

    assert all(node["label"] != "Not a graph person" for node in graph["nodes"])
