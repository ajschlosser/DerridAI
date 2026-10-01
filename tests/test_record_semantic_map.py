# Copyright 2026 Aaron John Schlosser, PhD.
"""Record-centred semantic maps and node walks over the derived Semantic Content Graph."""

from __future__ import annotations

import hashlib
import json
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules["chromadb"] = types.SimpleNamespace()

from app import corpus_builder as cb
from app.config import APP_VERSION
from app.nlp_annotations import text_digest
from app.record_semantic_map import record_semantic_map, semantic_node_neighborhood
from app.reviewer_context import current_reviewer
from app.semantic_content_graph import (
    build_semantic_content_graph,
    document_entity_node_id,
)


def _terms(text: str, *spans: tuple[str, str, str]) -> dict:
    terms = []
    for surface, source, tag in spans:
        start = text.index(surface)
        terms.append({"start": start, "end": start + len(surface), "text": surface, "source": source, "tag": tag})
    return {"status": "ok", "text_sha256": text_digest(text), "fields": {}, "terms": terms}


def _records():
    rows = [
        {
            "record_id": "r1",
            "text": "Heidegger questions presence and the trace.",
            "persons": ["Heidegger"],
            "concepts": ["presence", "trace"],
            "position_holder": "Heidegger",
            "target": "presence",
            "stance": "questions",
        },
        {"record_id": "r2", "text": "Presence again, with Heidegger.", "persons": ["Heidegger"], "concepts": ["presence"]},
        {"record_id": "r3", "text": "The trace is not presence.", "concepts": ["presence", "trace"]},
        {"record_id": "r4", "text": "Unrelated remark on writing.", "concepts": ["writing"]},
        {"record_id": "r5", "text": "Heidegger, briefly.", "persons": ["Heidegger"]},
    ]
    for row in rows:
        row["record_revision"] = 1
    return rows


def _map(records, record_id, analysis=None):
    graph = build_semantic_content_graph(records, analysis or {"profile": "scholarly"})
    return graph, record_semantic_map(graph, records, record_id, analysis=analysis)


def test_record_map_separates_in_record_relations_from_outward_ones_and_ranks_links():
    records = _records()
    graph, result = _map(records, "r1")
    local = {node["label"] for node in result["nodes"] if node["local"]}
    assert local == {"Heidegger", "presence", "trace"}
    in_record = [edge for edge in result["edges"] if edge["in_record"]]
    assert {edge["predicate"] for edge in in_record} == {"questions", "co_occurs"}
    semantic = next(edge for edge in in_record if edge["predicate"] == "questions")
    assert semantic["relation_kind"] == "semantic" and semantic["supporting_fields"]
    # r4 shares nothing. r3 and r2 both share "presence", but r3's other shared node
    # ("trace") is rarer than r2's ("Heidegger"), so it ranks first.
    linked = [row["record_id"] for row in result["linked_records"]]
    assert linked == ["r3", "r2", "r5"]
    assert {node["label"] for node in result["linked_records"][0]["shared_nodes"]} == {"presence", "trace"}
    assert all(row["preview"] for row in result["linked_records"])
    with pytest.raises(KeyError):
        record_semantic_map(graph, records, "missing")


def test_walking_a_node_reaches_every_record_it_takes_part_in():
    records = _records()
    # In r1 Heidegger is only the position holder, not an indexed person; the walk
    # still reaches r1 through the relation he takes part in.
    records[0].pop("persons")
    graph = build_semantic_content_graph(records, {"profile": "scholarly"})
    heidegger = next(node for node in graph["nodes"] if node["label"] == "Heidegger")
    assert "r1" not in heidegger["record_ids"]
    walk = semantic_node_neighborhood(graph, records, heidegger["id"])
    assert [row["record_id"] for row in walk["records"]] == ["r1", "r2", "r5"]
    assert walk["edges"][0]["relation_kind"] == "semantic"  # semantic relations lead
    presence = next(node for node in walk["nodes"] if node["label"] == "presence")
    onward = semantic_node_neighborhood(graph, records, presence["id"])
    assert [row["record_id"] for row in onward["records"]] == ["r1", "r2", "r3"]
    with pytest.raises(KeyError):
        semantic_node_neighborhood(graph, records, "person:missing")


def test_pos_and_ner_terms_join_existing_nodes_or_link_records_by_surface_form():
    records = _records()
    records[0]["nlp_candidates"] = _terms(records[0]["text"], ("Heidegger", "ner", "PERSON"), ("trace", "pos", "NOUN"))
    records[3]["text"] = "Unrelated remark on the trace of writing."
    records[3]["nlp_candidates"] = _terms(records[3]["text"], ("remark", "pos", "NOUN"))
    graph, result = _map(records, "r1")
    mentions = {item["text"]: item for item in result["mentions"]}
    heidegger = next(node for node in result["nodes"] if node["label"] == "Heidegger")
    assert mentions["Heidegger"]["node_id"] == heidegger["id"] and mentions["Heidegger"]["layer"] == "ner"
    assert not any(node["id"].startswith("term:") for node in result["nodes"])  # merged, not duplicated
    assert result["layers"]["terms"]["status"] == "ok"
    for item in result["mentions"]:
        assert records[0]["text"][item["start"]:item["end"]] == item["text"]

    records[1]["nlp_candidates"] = _terms(records[1]["text"], ("again", "pos", "NOUN"))
    records[2]["nlp_candidates"] = _terms(records[2]["text"], ("The trace", "pos", "NOUN"))
    records[3]["nlp_candidates"] = _terms(records[3]["text"], ("remark", "pos", "NOUN"))
    records[0]["nlp_candidates"] = _terms(records[0]["text"], ("questions", "pos", "NOUN"))
    records[1]["text"] = "Heidegger questions presence, again."
    records[1]["nlp_candidates"] = _terms(records[1]["text"], ("questions", "pos", "NOUN"))
    _, result = _map(records, "r1")
    term = next(node for node in result["nodes"] if node["label"] == "questions")
    assert term["type"] == "term" and term["id"].startswith("term:term:") and term["tags"] == ["NOUN"]
    walk = semantic_node_neighborhood(build_semantic_content_graph(records, {}), records, term["id"])
    assert [row["record_id"] for row in walk["records"]] == ["r1", "r2"] and walk["edges"] == []


def test_stale_term_and_document_layers_are_reported_not_projected():
    records = _records()
    records[0]["nlp_candidates"] = _terms(records[0]["text"], ("trace", "pos", "NOUN"))
    records[0]["document_intelligence"] = {
        "status": "ok",
        "record_text_sha256": hashlib.sha256(records[0]["text"].encode("utf-8")).hexdigest(),
        "entities": [{"entity_id": "c1", "label": "Martin Heidegger", "text": "Heidegger", "entity_type": "PERSON", "start": 0, "end": 9}],
    }
    records[0]["text"] = "Heidegger questions presence and the trace, edited."
    _, result = _map(records, "r1")
    assert result["layers"]["terms"]["status"] == "stale"
    assert result["layers"]["document_intelligence"]["status"] == "stale"
    assert result["mentions"] == []
    records[1]["nlp_candidates"] = {"status": "unavailable", "reason": "model_not_installed"}
    _, other = _map(records, "r2")
    assert other["layers"]["terms"]["status"] == "unavailable"


def test_document_intelligence_mentions_resolve_to_their_cluster_nodes():
    text = "Levinas speaks. Derrida answers."
    records = [{"record_id": "r1", "record_revision": 1, "text": text}]
    analysis = {
        "status": "ok",
        "profile": "scholarly",
        "provider": "booknlp",
        "record_spans": [{"record_id": "r1", "start": 0, "end": len(text)}],
        "entity_clusters": [{"cluster_id": "c1", "canonical": "Emmanuel Levinas", "aliases": ["Levinas"], "entity_type": "PERSON"}],
        "entities": [{"cluster_id": "c1", "start_char": 0, "end_char": 7, "text": "Levinas"}],
    }
    records[0]["document_intelligence"] = {
        "status": "ok",
        "provider": "booknlp",
        "record_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "entities": [{"entity_id": "c1", "label": "Emmanuel Levinas", "text": "Levinas", "entity_type": "PERSON", "start": 0, "end": 7}],
        "quotations": [{"start": 0, "end": 15, "speaker_entity_id": "c1", "speaker": "Emmanuel Levinas", "text": "Levinas speaks."}],
    }
    _, result = _map(records, "r1", analysis)
    node_id = document_entity_node_id("c1", "Emmanuel Levinas")
    assert result["layers"]["document_intelligence"]["status"] == "ok"
    assert {(item["layer"], item["node_id"]) for item in result["mentions"]} == {("entity", node_id), ("quotation", node_id)}
    assert next(node for node in result["nodes"] if node["id"] == node_id)["local"] is True


def _manager(tmp_path: Path):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = repo.create_build({
        "asset_id": "a", "source_sha256": "x", "source_filename": "x.pdf", "source_page_count": 1, "source_block_count": 1,
        "schema_version": cb.SCHEMA_VERSION, "profile_id": cb.PROFILE_VERSION, "profile_version": 11, "app_version": APP_VERSION,
        "provider": "ollama", "model": "m", "request": {},
    })
    return cb.PdfCorpusBuildManager(repo), repo, build["build_id"]


def test_a_second_reviewer_cannot_read_a_sealed_value_through_the_record_map(tmp_path):
    manager, repo, build_id = _manager(tmp_path)
    rows = _records()
    rows[0]["second_opinion"] = {"position_holder": {"first_reviewer": "user-1"}}
    rows[0]["position_holder"] = "Sealed Holder"
    rows[1]["persons"] = ["Heidegger"]
    repo.save_records(build_id, rows)
    token = current_reviewer.set("user-2")
    try:
        theirs = manager.record_semantic_map(build_id, "r1")
        heidegger = next(node for node in theirs["nodes"] if node["label"] == "Heidegger")
        walked = manager.semantic_graph_node(build_id, heidegger["id"])
    finally:
        current_reviewer.reset(token)
    assert "Sealed Holder" not in json.dumps(theirs) and "Sealed Holder" not in json.dumps(walked)
    token = current_reviewer.set("user-1")
    try:
        mine = manager.record_semantic_map(build_id, "r1")
    finally:
        current_reviewer.reset(token)
    assert "Sealed Holder" in json.dumps(mine)
    with pytest.raises(KeyError):
        manager.record_semantic_map(build_id, "nope")


def test_persisted_projection_hydrates_without_reloading_the_full_corpus(tmp_path, monkeypatch):
    manager, repo, build_id = _manager(tmp_path)
    repo.save_records(build_id, _records())

    projections: dict[str, dict] = {}

    def get_projection(key: str):
        return projections.get(key)

    def put_projection(key: str, **kwargs):
        projections[key] = {
            "projection_key": key,
            "scope_kind": kwargs["scope_kind"],
            "scope_id": kwargs["scope_id"],
            "build_id": kwargs.get("build_id"),
            "generation": kwargs["generation"],
            "status": kwargs.get("status", "ready"),
            "payload": kwargs.get("payload"),
        }

    monkeypatch.setattr(cb.system_store, "get_semantic_map_projection", get_projection)
    monkeypatch.setattr(cb.system_store, "put_semantic_map_projection", put_projection)

    first = manager.record_semantic_map(build_id, "r1")
    assert first["record_id"] == "r1"
    assert any(key.startswith("semantic-index:") for key in projections)
    assert any(key.startswith("semantic-record:") for key in projections)

    # A fresh manager simulates an API restart. The persisted traversal index and
    # Record projection must make the unchanged hot read independent of load_records.
    restarted = cb.PdfCorpusBuildManager(repo)
    monkeypatch.setattr(
        repo,
        "load_records",
        lambda _build_id: (_ for _ in ()).throw(
            AssertionError("cached semantic-map read loaded the full corpus")
        ),
    )
    second = restarted.record_semantic_map(build_id, "r1")
    assert second == first
