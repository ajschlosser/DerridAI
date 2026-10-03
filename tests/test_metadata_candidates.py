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

"""Candidate-first indexing: safe NLP spans become unreviewed FieldAssertions."""

from __future__ import annotations  # noqa: I001 -- keep candidate-layer module namespaces explicit

import app.field_assertions
import app.metadata_candidates
import app.metadata_schema
import app.nlp_annotations


TEXT = "Rousseau discusses Of Grammatology and hospitality."


def _record() -> dict:
    return {
        "record_id": "r1",
        "record_revision": 1,
        "text": TEXT,
        "metadata_field_status": {},
        "nlp_candidates": {
            "status": "ok",
            "engine": "spacy",
            "engine_version": "3.8.7",
            "model": "en_core_web_lg",
            "text_sha256": app.nlp_annotations.text_digest(TEXT),
            "fields": {
                "persons": [
                    {
                        "start": 0,
                        "end": 8,
                        "text": "Rousseau",
                        "source": "ner",
                        "tag": "PERSON",
                    },
                    {
                        "start": 0,
                        "end": 8,
                        "text": "Rousseau",
                        "source": "pos",
                        "tag": "PROPN",
                    },
                ],
                "works_referenced": [
                    {
                        "start": 19,
                        "end": 34,
                        "text": "Of Grammatology",
                        "source": "ner",
                        "tag": "WORK_OF_ART",
                    }
                ],
                "topics": [
                    {
                        "start": 40,
                        "end": 51,
                        "text": "hospitality",
                        "source": "pos",
                        "tag": "NOUN",
                    }
                ],
                "concepts": [
                    {
                        "start": 40,
                        "end": 51,
                        "text": "hospitality",
                        "source": "pos",
                        "tag": "NOUN",
                    }
                ],
            },
        },
    }


def test_safe_direct_ner_indexing_candidates_become_unreviewed_assertions():
    record = _record()
    summary = app.metadata_candidates.apply_indexing_nlp_candidates(record, app.metadata_schema.default_schema())

    assert summary["resolved_fields"] == ["persons", "works_referenced"]
    assert record["persons"] == ["Rousseau"]
    assert record["works_referenced"] == ["Of Grammatology"]
    assert "topics" not in record and "concepts" not in record

    persons = app.field_assertions.current_assertion_by_name(record, "persons")
    assert persons is not None
    assert persons.derivation_method == "derridai:nlp"
    assert persons.evaluation_status == "value_supported"
    assert persons.authority_status == "unreviewed"
    assert persons.confidence is None
    assert persons.evidence == [{
        "kind": "nlp_span",
        "start": 0,
        "end": 8,
        "text": "Rousseau",
        "tag": "PERSON",
        "source": "ner",
        "text_sha256": app.nlp_annotations.text_digest(TEXT),
        "engine": "spacy",
        "engine_version": "3.8.7",
        "model": "en_core_web_lg",
    }]
    assert persons.legacy_metadata["candidate_only"] is True
    assert persons.legacy_metadata["verification_status"] == "pending_review"
    assert persons.legacy_metadata["reason_code"] == "direct_ner_indexing_candidate"


def test_crowded_direct_ner_set_is_deferred_to_semantic_indexing():
    text = "Alice Bob Carol David Eve."
    names = ["Alice", "Bob", "Carol", "David", "Eve"]
    record = {
        "record_id": "crowded",
        "record_revision": 1,
        "text": text,
        "metadata_field_status": {},
        "nlp_candidates": {
            "status": "ok",
            "engine": "spacy",
            "engine_version": "3.8.7",
            "model": "en_core_web_lg",
            "text_sha256": app.nlp_annotations.text_digest(text),
            "fields": {
                "persons": [
                    {
                        "start": text.index(name),
                        "end": text.index(name) + len(name),
                        "text": name,
                        "source": "ner",
                        "tag": "PERSON",
                    }
                    for name in names
                ]
            },
        },
    }

    summary = app.metadata_candidates.apply_indexing_nlp_candidates(record, app.metadata_schema.default_schema())

    assert summary["resolved_fields"] == []
    assert "persons" not in record
    assert "exceed the conservative candidate-only limit" in summary["deferred_fields"]["persons"]


def test_stale_nlp_projection_is_never_promoted():
    record = _record()
    record["text"] += " Revised."
    summary = app.metadata_candidates.apply_indexing_nlp_candidates(record, app.metadata_schema.default_schema())

    assert summary["resolved_fields"] == []
    assert "persons" not in record
    assert "works_referenced" not in record


def test_nlp_candidates_do_not_overwrite_present_memory_or_human_values():
    schema = app.metadata_schema.default_schema()
    record = _record()
    app.field_assertions.create_memory_assertion(
        record,
        "persons",
        ["Derrida"],
        schema=schema,
        confidence=0.9,
        reason="Reviewed precedents agree.",
        evidence=[{"block_ids": ["b1"], "confidence": 0.9}],
    )
    app.field_assertions.create_human_assertion(
        record,
        "works_referenced",
        ["Glas"],
        schema=schema,
        reason="Reviewer selected this work.",
    )
    app.field_assertions.project_record_assertions(record)

    summary = app.metadata_candidates.apply_indexing_nlp_candidates(record, schema)

    assert summary["resolved_fields"] == []
    assert record["persons"] == ["Derrida"]
    assert record["works_referenced"] == ["Glas"]
    assert app.field_assertions.current_assertion_by_name(record, "persons").derivation_method == "derridai:memory"
    assert app.field_assertions.current_assertion_by_name(record, "works_referenced").authority_status == "human_confirmed"
