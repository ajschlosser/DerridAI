# Copyright 2026 Aaron John Schlosser, PhD.
import time

from app.semantic_content_graph import (
    VIEW_MAX_EDGES,
    VIEW_MAX_NODES,
    build_semantic_content_graph,
    semantic_content_graph_view,
)


def _large_graph(n_nodes: int = 12000, fanout: int = 6) -> dict:
    nodes = [
        {
            "id": f"concept:{i}",
            "type": "person" if i % 5 == 0 else "concept",
            "label": f"Entity {i}",
            "aliases": [f"alias-{i}"],
            "record_ids": [f"r{i}"],
            "mention_count": n_nodes - i,
        }
        for i in range(n_nodes)
    ]
    edges = []
    for i in range(n_nodes):
        for step in range(1, fanout + 1):
            j = (i + step * 7) % n_nodes
            edges.append(
                {
                    "id": f"relation:{i}-{j}",
                    "source": f"concept:{i}",
                    "target": f"concept:{j}",
                    "predicate": "co_occurs" if step > 1 else "critiques",
                    "relation_kind": "observational" if step > 1 else "semantic",
                    "authority_status": "unreviewed",
                    "record_ids": [f"r{i}"],
                    "count": step,
                }
            )
    return {"nodes": nodes, "edges": edges, "summary": {"nodes": len(nodes), "edges": len(edges)}}


def test_overview_is_bounded_ranked_and_reports_truncation_for_large_graphs():
    graph = _large_graph()
    started = time.perf_counter()
    view = semantic_content_graph_view(graph, node_limit=10_000, edge_limit=10_000)
    assert time.perf_counter() - started < 5
    assert len(view["view"]["nodes"]) == VIEW_MAX_NODES
    assert len(view["view"]["edges"]) <= VIEW_MAX_EDGES
    assert view["view"]["truncated_nodes"] is True
    assert view["view"]["candidate_nodes"] == 12000
    # Highest-mention entities come first; edges stay inside the displayed set.
    assert view["view"]["nodes"][0]["id"] == "concept:0"
    shown = {node["id"] for node in view["view"]["nodes"]}
    assert all(e["source"] in shown and e["target"] in shown for e in view["view"]["edges"])
    # Compact payload: no per-record lists in overview nodes.
    assert "record_ids" not in view["view"]["nodes"][0]
    assert view["index"]["total"] == 12000 and len(view["index"]["items"]) == 50


def test_filters_by_type_query_relation_kind_and_pages_the_index():
    graph = _large_graph(500)
    view = semantic_content_graph_view(
        graph, types=["person"], query="ALIAS-1", relation_kind="semantic", index_limit=5, index_offset=5
    )
    assert all(node["type"] == "person" for node in view["view"]["nodes"])
    assert all("1" in node["label"] for node in view["index"]["items"])
    assert all(edge["relation_kind"] == "semantic" for edge in view["view"]["edges"])
    assert view["index"]["offset"] == 5 and len(view["index"]["items"]) <= 5
    facet_types = {row["type"]: row["count"] for row in view["facets"]["types"]}
    assert facet_types == {"person": 100, "concept": 400}


def test_focus_returns_neighbourhood_with_spokes_first_and_paged_relations():
    graph = _large_graph(2000)
    view = semantic_content_graph_view(graph, focus="concept:100", node_limit=4, edge_limit=3)
    ids = [node["id"] for node in view["view"]["nodes"]]
    assert ids[0] == "concept:100" and len(ids) == 4
    assert view["view"]["truncated_nodes"] is True
    assert all("concept:100" in (e["source"], e["target"]) for e in view["view"]["edges"])
    focus = view["focus"]
    assert focus["node"]["id"] == "concept:100"
    assert focus["relations_total"] == 12
    # Strongest relation first, direction preserved rather than symmetrised.
    first = focus["relations"][0]
    assert first["count"] == 6
    assert {rel["direction"] for rel in focus["relations"]} == {"incoming", "outgoing"}


def test_view_preserves_edge_authority_and_relation_kind_from_projection():
    record = {
        "record_id": "r1",
        "record_revision": 1,
        "text": "Derrida reads Husserl.",
        "persons": ["Husserl"],
        "concepts": ["presence"],
        "position_holder": "Derrida",
        "target": "Husserl",
        "stance": "critiques",
        "metadata_field_status": {
            "position_holder": {"status": "human_confirmed"},
            "target": {"status": "human_confirmed"},
            "stance": {"status": "human_confirmed"},
        },
    }
    graph = build_semantic_content_graph([record], {"profile": "scholarly"})
    derrida = next(n for n in graph["nodes"] if n["label"] == "Derrida")
    view = semantic_content_graph_view(graph, focus=derrida["id"])
    relation = next(r for r in view["focus"]["relations"] if r["predicate"] == "critiques")
    assert relation["relation_kind"] == "semantic"
    assert relation["authority_status"] == "human_confirmed"
    assert relation["supporting_fields"] == ["position_holder", "target", "stance"]
    observational = semantic_content_graph_view(graph, relation_kind="observational")
    assert all(e["predicate"] == "co_occurs" for e in observational["view"]["edges"])


def test_unknown_focus_falls_back_to_overview_and_invalid_params_are_clamped():
    graph = _large_graph(50)
    view = semantic_content_graph_view(
        graph, focus="missing", node_limit=-3, relation_kind="bogus", index_sort="nope"
    )
    assert view["focus"] is None
    assert len(view["view"]["nodes"]) == 1
    assert view["query"]["relation_kind"] == "all"
    assert view["index"]["sort"] == "mentions"


def test_manager_reuses_graph_until_records_change(tmp_path, monkeypatch):
    import sys
    import types

    try:
        import chromadb  # type: ignore  # noqa: F401
    except ModuleNotFoundError:
        sys.modules["chromadb"] = types.SimpleNamespace()
    from app import corpus_builder as cb

    manager = cb.PdfCorpusBuildManager(cb.PdfCorpusRepository(tmp_path / "repo"))
    manager.repo.get_asset = lambda asset_id: {"asset_id": asset_id, "sha256": "s", "filename": "f.pdf", "page_count": 1, "block_count": 1}  # type: ignore[method-assign]
    monkeypatch.setattr(manager._executor, "submit", lambda *args, **kwargs: None)
    build = manager.create({"asset_id": "a"})
    records = [{"record_id": "r1", "record_revision": 1, "text": "x", "concepts": ["trace", "différance"]}]
    manager.repo.save_records(build["build_id"], records)
    durable_writes = []
    monkeypatch.setattr(manager.repo, "save_checkpoint", lambda *args, **kwargs: durable_writes.append("checkpoint"))
    monkeypatch.setattr(manager.repo, "save_build", lambda *args, **kwargs: durable_writes.append("build"))
    calls = []
    real = cb.build_semantic_content_graph
    monkeypatch.setattr(cb, "build_semantic_content_graph", lambda *a, **k: calls.append(1) or real(*a, **k))

    first = manager.semantic_content_graph_view(build["build_id"], node_limit=1)
    manager.semantic_content_graph_view(build["build_id"], query="trace")
    assert len(calls) == 1
    assert durable_writes == []
    assert len(first["view"]["nodes"]) == 1 and first["view"]["truncated_nodes"] is True

    records.append({"record_id": "r2", "record_revision": 1, "text": "y", "concepts": ["supplement"]})
    manager.repo.save_records(build["build_id"], records)
    refreshed = manager.semantic_content_graph_view(build["build_id"])
    assert len(calls) == 2
    assert refreshed["view"]["candidate_nodes"] == 3
