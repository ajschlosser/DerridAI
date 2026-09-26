# Copyright 2026 Aaron John Schlosser, PhD.
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import memory_prefill as mp  # noqa: E402
from app.corpus_metadata import DISCOURSE_ROLES  # noqa: E402
from app.field_assertions import (  # noqa: E402
    create_human_assertion,
    current_assertion_by_name,
)
from app.metadata_schema import default_schema  # noqa: E402

ROLE_A, ROLE_B = sorted(DISCOURSE_ROLES)[:2]
SPAN = "For Levinas, responsibility precedes freedom in every encounter with the other."


def meta(field, value, scope, record, kind="positive"):
    return {"field_name": field, "field_value_json": json.dumps(value), "kind": kind, "scope_id": scope, "record_id": record}


class FakeCollection:
    def __init__(self, hits):
        self.hits, self.queries = hits, []

    def count(self):
        return 10

    def query(self, *, query_embeddings, n_results, where, include):
        self.queries.append({"n": len(query_embeddings), "where": where})
        ids, metas, dists = [], [], []
        for _ in query_embeddings:
            ids.append([f"mex-{i}" for i in range(len(self.hits))])
            metas.append([h[0] for h in self.hits])
            dists.append([h[1] for h in self.hits])
        return {"ids": ids, "metadatas": metas, "distances": dists}


class FakeIndex:
    def __init__(self, hits, error=None):
        self.collection = FakeCollection(hits)
        self.error = error
        index = self

        class Embeddings:
            def embed(self, texts, records, field, *, provider=None, model=None):
                if index.error:
                    raise index.error
                return [[0.0]] * len(texts)

        class Store:
            embeddings = Embeddings()

            def _embedding_spec(self, collection):
                return "ollama", "bge-m3"

        self.store = Store()

    def _ensure(self):
        return self.collection


def records():
    return [{"record_id": "r1", "record_revision": 1, "source_document_id": "d", "text": SPAN,
             "source_block_ids": ["b1", "b2"], "source_spans": []}]


BLOCKS = [{"block_id": "b1", "text": SPAN}, {"block_id": "b2", "text": "Short."}]


def run(hits, rows=None, index=None):
    rows = rows if rows is not None else records()
    summary = mp.prefill_records(rows, BLOCKS, default_schema(), index or FakeIndex(hits), build_id="b-new")
    return rows[0], summary


def test_agreeing_precedents_prefill_the_value_with_the_matching_span_as_evidence():
    record, summary = run([(meta("discourse_role", ROLE_A, "b-old", "x1"), 0.05), (meta("discourse_role", ROLE_A, "b-old", "x2"), 0.07)])
    assert summary["status"] == "ok" and summary["prefilled"] == 1
    assert record["discourse_role"] == ROLE_A
    assertion = current_assertion_by_name(record, "discourse_role")
    assert assertion.derivation_method == "derridai:memory" and assertion.authority_status == "unreviewed"
    assert assertion.confidence <= 0.9 and "mex-0" in assertion.reason
    evidence = record["metadata_evidence"]["discourse_role"]
    assert evidence["block_ids"] == ["b1"] and evidence["reviewed_by"] == "memory"


def test_one_precedent_or_a_rival_value_is_only_a_hint():
    record, summary = run([(meta("discourse_role", ROLE_A, "b-old", "x1"), 0.05)])
    assert summary["prefilled"] == 0 and record.get("discourse_role") in (None, "")
    assert record["memory_hints"]["discourse_role"][0]["value"] == ROLE_A
    record, summary = run([
        (meta("discourse_role", ROLE_A, "b-old", "x1"), 0.05), (meta("discourse_role", ROLE_A, "b-old", "x2"), 0.06),
        (meta("discourse_role", ROLE_B, "b-old", "x3"), 0.05), (meta("discourse_role", ROLE_B, "b-old", "x4"), 0.06),
    ])
    assert summary["prefilled"] == 0 and len(record["memory_hints"]["discourse_role"]) == 2


def test_weak_similarity_is_ignored():
    record, summary = run([(meta("discourse_role", ROLE_A, "b-old", "x1"), 1.5), (meta("discourse_role", ROLE_A, "b-old", "x2"), 1.6)])
    assert summary["prefilled"] == 0 and "memory_hints" not in record


def test_the_same_earlier_record_only_votes_once():
    record, summary = run([(meta("discourse_role", ROLE_A, "b-old", "x1"), 0.05), (meta("discourse_role", ROLE_A, "b-old", "x1"), 0.05)])
    assert summary["prefilled"] == 0


def test_values_outside_the_closed_vocabulary_are_never_prefilled():
    record, summary = run([(meta("discourse_role", "invented_role", "b-old", "x1"), 0.05), (meta("discourse_role", "invented_role", "b-old", "x2"), 0.05)])
    assert summary["prefilled"] == 0 and "memory_hints" not in record


def test_confirmed_absence_is_only_a_hint():
    absent = {"field_name": "discourse_role", "kind": "absence", "scope_id": "b-old", "record_id": "x", "field_value_json": "null"}
    record, summary = run([(dict(absent, record_id="x1"), 0.05), (dict(absent, record_id="x2"), 0.05)])
    assert summary["prefilled"] == 0 and record["memory_hints"]["discourse_role"][0]["absence"] is True


def test_human_owned_or_already_filled_fields_are_left_alone():
    rows = records()
    create_human_assertion(rows[0], "discourse_role", ROLE_B, schema=default_schema())
    rows[0]["discourse_role"] = ROLE_B
    record, summary = run([(meta("discourse_role", ROLE_A, "b-old", "x1"), 0.05), (meta("discourse_role", ROLE_A, "b-old", "x2"), 0.05)], rows)
    assert record["discourse_role"] == ROLE_B and summary["prefilled"] == 0


def test_queries_exclude_this_build_and_use_the_source_spans_not_the_record_text():
    index = FakeIndex([])
    run([], index=index)
    query = index.collection.queries[0]
    assert query["n"] == 1  # "Short." is below the span-length floor; only the real span is embedded
    assert {"scope_id": {"$ne": "b-new"}} in query["where"]["$and"]


def test_an_unreachable_provider_is_reported_and_never_raises():
    record, summary = run([], index=FakeIndex([], error=RuntimeError("no route to embedding host")))
    assert summary["status"] == "unavailable" and "no route" in summary["error"]
    assert "memory_hints" not in record


def test_an_empty_memory_is_reported_as_such():
    index = FakeIndex([])
    index.collection.count = lambda: 0
    _, summary = run([], index=index)
    assert summary["status"] == "empty"


def test_the_ledger_accepts_the_namespaced_derivation_methods():
    from app.derridai_ledger import _DERIVATION_METHODS

    assert {"derridai:memory", "derridai:nlp", "derridai:computed"} <= _DERIVATION_METHODS


@pytest.mark.parametrize("value,expected", [("interrogation" if False else ROLE_A, True), ("nope", False), (None, False)])
def test_allowed_values(value, expected):
    assert mp._allowed(default_schema(), "discourse_role", value) is expected
