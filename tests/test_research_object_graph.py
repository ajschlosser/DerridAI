# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from app.derridai_model import normative_model
from app.research_object_graph import build_record_graph


def _neighbors(graph: dict, node_id: str) -> set[str]:
    result: set[str] = set()
    for edge in graph["edges"]:
        if edge["source"] == node_id:
            result.add(edge["target"])
        if edge["target"] == node_id:
            result.add(edge["source"])
    return result


def test_normative_model_exposes_branching_record_cardinalities():
    model = normative_model()
    nodes = {node["type"] for node in model["nodes"]}
    assert {
        "SourceDocument",
        "SourceSpan",
        "Record",
        "RecordRevision",
        "FieldAssertion",
        "EvidenceRef",
        "GeneratedClaim",
        "SupportBinding",
    }.issubset(nodes)

    record_edges = [
        edge
        for edge in model["edges"]
        if edge["source_type"] == "Record" or edge["target_type"] == "Record"
    ]
    targets = {
        edge["target_type"] if edge["source_type"] == "Record" else edge["source_type"]
        for edge in record_edges
    }
    assert {"SourceDocument", "SourceSpan", "RecordRevision", "FieldAssertion"}.issubset(targets)
    span_edge = next(edge for edge in model["edges"] if edge["id"] == "record_spans")
    assert span_edge["source_cardinality"] == "1..*"
    assert span_edge["inverse_relation"] == "contributes to"


def test_record_graph_can_walk_document_assertion_and_claim_branches():
    record = {
        "record_id": "r1",
        "record_revision": 3,
        "source_document_id": "doc-1",
        "work": "Example Work",
        "page_start": 12,
        "page_end": 13,
        "source_spans": [
            {
                "source_document_id": "doc-1",
                "source_unit_id": "b1",
                "page": 12,
                "char_start": 0,
                "char_end": 120,
            }
        ],
        "field_assertions": {
            "core.position_holder": [
                {
                    "assertion_id": "fa-1",
                    "record_id": "r1",
                    "record_revision": 3,
                    "field_id": "core.position_holder",
                    "field_name": "position_holder",
                    "value": "Levinas",
                    "derivation_method": "model",
                    "evaluation_status": "value_supported",
                    "authority_status": "human_confirmed",
                    "value_status": "present",
                }
            ]
        },
    }
    claims = [
        {
            "claim_id": "claim-1",
            "run_id": "run-9",
            "claim_text": "The passage distinguishes hospitality from simple inclusion.",
            "validation_status": "validated",
        }
    ]
    bindings = [
        {
            "support_binding_id": "sb-1",
            "claim_id": "claim-1",
            "record_id": "r1",
            "record_revision": 3,
            "source_document_id": "doc-1",
            "source_spans": [
                {
                    "source_document_id": "doc-1",
                    "source_unit_ids": ["b1"],
                    "physical_page_start": 12,
                    "physical_page_end": 12,
                }
            ],
            "relation": "supports",
            "validation_status": "validated",
        }
    ]

    graph = build_record_graph(record, claims=claims, support_bindings=bindings)
    root = graph["root_id"]
    by_type = {}
    for node in graph["nodes"]:
        by_type.setdefault(node["object_type"], []).append(node["id"])

    root_neighbors = _neighbors(graph, root)
    assert by_type["SourceDocument"][0] in root_neighbors
    # The Record and persisted SupportBinding describe the same source unit in
    # different serialization shapes; the graph must show one documentary span.
    assert len(by_type["SourceSpan"]) == 1
    assert by_type["SourceSpan"][0] in root_neighbors
    assert by_type["RecordRevision"][0] in root_neighbors
    assert by_type["FieldAssertion"][0] in root_neighbors

    claim = by_type["GeneratedClaim"][0]
    binding = by_type["SupportBinding"][0]
    evidence = by_type["EvidenceRef"][0]
    assert binding in _neighbors(graph, claim)
    assert evidence in _neighbors(graph, binding)
    assert by_type["ResearchRun"][0] in _neighbors(graph, claim)

    # The same graph supports re-centering instead of enforcing one fixed chain.
    assert len(root_neighbors) >= 4
    assert len(_neighbors(graph, claim)) >= 2


def _assertion(assertion_id, value, *, supersedes=None):
    return {
        "assertion_id": assertion_id, "field_id": "f", "field_name": "speaker", "value": value,
        "record_revision": 1, "authority_status": "unreviewed", "derivation_method": "model",
        **({"supersedes_assertion_id": supersedes} if supersedes else {}),
    }


def test_graph_shows_only_current_assertions_by_default():
    record = {
        "record_id": "r1", "source_document_id": "d1", "record_revision": 1,
        "field_assertions": {"f": [_assertion("a1", "Derrida"), _assertion("a2", "Rousseau", supersedes="a1")]},
        "current_field_assertions": {"f": "a2"},
    }
    graph = build_record_graph(record)
    ids = [n["label"] for n in graph["nodes"] if n["object_type"] == "FieldAssertion"]
    assert len(ids) == 1 and graph["hidden_assertion_count"] == 1
    full = build_record_graph(record, include_assertion_history=True)
    assert len([n for n in full["nodes"] if n["object_type"] == "FieldAssertion"]) == 2
    assert full["hidden_assertion_count"] == 0
    assert any(e.get("relation") == "supersedes" for e in full["edges"])
    assert not any(e.get("relation") == "supersedes" for e in graph["edges"])
