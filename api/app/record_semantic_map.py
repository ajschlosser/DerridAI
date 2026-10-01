# Copyright 2026 Aaron John Schlosser, PhD.
"""Record-centred views of the Semantic Content Graph.

A Record semantic map is a bounded projection of the build-wide Semantic Content
Graph around one Record: the nodes that occur in it, the relations it supports,
the relations that lead out of it, and the other Records that share its nodes. A
node neighbourhood is the same projection around one node, so a reviewer can walk
node → node and node → Record → node across the corpus.

Both views also fold in the Record-level POS/NER term layer from
``nlp_annotations``. Terms that name an existing graph node are merged into it;
the rest become ``term`` (POS) or entity-type nodes that link Records only by
shared surface form. Like every other part of the graph this is derived,
rebuildable navigation state. A shared node or term is an observation, never
evidence that two Records make the same claim.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict
from typing import Any

from .nlp_annotations import current_terms
from .semantic_content_graph import _slug, document_entity_node_id
from .semantic_identity import text_key

RECORD_SEMANTIC_MAP_VERSION = 1
MAX_LOCAL_NODES = 80
MAX_NEIGHBOR_NODES = 40
MAX_LINKED_RECORDS = 24
MAX_SHARED_PER_LINK = 12
MAX_NODE_EDGES = 60
MAX_NODE_RECORDS = 50
PREVIEW_CHARS = 140

_NER_KINDS = {
    "PERSON": "person",
    "PER": "person",
    "ORG": "organization",
    "GPE": "place",
    "LOC": "place",
    "FAC": "place",
    "WORK_OF_ART": "work",
}

EPISTEMIC_NOTE = (
    "A shared node, term, or relation shows where Records meet in the derived graph. "
    "It is a navigation aid, not evidence that the Records make the same claim; "
    "POS and NER terms are exact text spans, not metadata values."
)


def _normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _preview(record: dict[str, Any]) -> str:
    text = _normalize(record.get("text"))
    return text if len(text) <= PREVIEW_CHARS else text[: PREVIEW_CHARS - 1].rstrip() + "…"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _edge_rank(edge: dict[str, Any]) -> tuple[int, int, str]:
    return (
        0 if edge.get("relation_kind") == "semantic" else 1,
        -int(edge.get("count") or 0),
        str(edge.get("id") or ""),
    )


def _node_ref(node: dict[str, Any]) -> dict[str, Any]:
    return {"id": node["id"], "label": node.get("label") or "", "type": node.get("type") or ""}


class _SemanticIndex:
    """The build graph plus Record term occurrences, indexed for traversal."""

    def __init__(self, graph: dict[str, Any], records: list[dict[str, Any]]) -> None:
        self.graph = graph
        self.records = [row for row in records if str(row.get("record_id") or "")]
        self.record_by_id = {str(row["record_id"]): row for row in self.records}
        self.record_order = {record_id: index for index, record_id in enumerate(self.record_by_id)}
        self.nodes: dict[str, dict[str, Any]] = {}
        for node in graph.get("nodes") or []:
            if isinstance(node, dict) and node.get("id"):
                self.nodes[str(node["id"])] = {
                    **node,
                    "record_ids": list(node.get("record_ids") or []),
                    "aliases": list(node.get("aliases") or []),
                }
        self.edges = [edge for edge in graph.get("edges") or [] if isinstance(edge, dict)]
        self.edges_by_node: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for edge in self.edges:
            self.edges_by_node[str(edge.get("source") or "")].append(edge)
            self.edges_by_node[str(edge.get("target") or "")].append(edge)
        for adjacent in self.edges_by_node.values():
            adjacent.sort(key=_edge_rank)
        self.term_mentions: dict[str, list[dict[str, Any]]] = {}
        self.term_state: dict[str, str] = {}
        self._fold_in_terms()

        # Build the expensive reverse indexes once per graph generation. Record
        # maps and node walks must never rescan every graph edge or every node.
        self.edges_by_record: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        self.nodes_by_record: defaultdict[str, set[str]] = defaultdict(set)
        node_record_sets: dict[str, set[str]] = {
            node_id: {
                str(value)
                for value in node.get("record_ids") or []
                if str(value) in self.record_order
            }
            for node_id, node in self.nodes.items()
        }
        for node_id, record_ids in node_record_sets.items():
            for record_id in record_ids:
                self.nodes_by_record[record_id].add(node_id)
        for edge in self.edges:
            source = str(edge.get("source") or "")
            target = str(edge.get("target") or "")
            for value in edge.get("record_ids") or []:
                record_id = str(value)
                if record_id not in self.record_order:
                    continue
                self.edges_by_record[record_id].append(edge)
                if source in self.nodes:
                    self.nodes_by_record[record_id].add(source)
                    node_record_sets.setdefault(source, set()).add(record_id)
                if target in self.nodes:
                    self.nodes_by_record[record_id].add(target)
                    node_record_sets.setdefault(target, set()).add(record_id)
        self.node_records: dict[str, list[str]] = {
            node_id: sorted(
                record_ids,
                key=lambda value: self.record_order[value],
            )
            for node_id, record_ids in node_record_sets.items()
        }

    def _fold_in_terms(self) -> None:
        # Graph nodes are ordered by mention count, so an ambiguous label resolves to
        # the most established node deterministically. A term joins a node by exact
        # surface first, then by the node's semantic identity: a person's name identity,
        # or a concept's lemma identity. A term with no safe identity stays its own node.
        by_label: dict[str, str] = {}
        by_name: dict[str, str] = {}
        by_lemma: dict[str, str] = {}
        for node_id, node in self.nodes.items():
            for value in [node.get("label"), *(node.get("aliases") or []), *(node.get("surface_forms") or [])]:
                key = text_key(str(value or ""))
                if key:
                    by_label.setdefault(key, node_id)
            parts = str(node.get("canonical_value_key") or "").split(":", 2)
            if len(parts) == 3 and parts[1] == "entity_name" and node.get("type") in {"person", "character"}:
                by_name.setdefault(parts[2], node_id)
            elif len(parts) == 3 and parts[1] == "lexical_phrase":
                by_lemma.setdefault(parts[2], node_id)
        for record_id, record in self.record_by_id.items():
            terms = current_terms(record)
            if terms is None:
                data = record.get("nlp_candidates")
                self.term_state[record_id] = (
                    "unavailable"
                    if isinstance(data, dict) and data.get("status") == "unavailable"
                    else "stale"
                    if isinstance(data, dict) and "terms" in data
                    else "missing"
                )
                continue
            self.term_state[record_id] = "ok"
            mentions: list[dict[str, Any]] = []
            for term in terms:
                surface = _normalize(term.get("text"))
                if not surface:
                    continue
                source = str(term.get("source") or "")
                tag = str(term.get("tag") or "")
                identity = str(term.get("identity_text") or "")
                node_id = by_label.get(text_key(surface)) or (
                    (by_name if source == "ner" else by_lemma).get(identity) if identity else None
                )
                if node_id:
                    node = self.nodes[node_id]
                    if record_id not in node["record_ids"]:
                        node["record_ids"].append(record_id)
                else:
                    kind = _NER_KINDS.get(tag, "entity") if source == "ner" else "term"
                    node_id = f"term:{kind}:{_slug(identity or surface)}"
                    node = self.nodes.setdefault(
                        node_id,
                        {
                            "id": node_id,
                            "type": kind,
                            "label": surface,
                            "aliases": [],
                            "record_ids": [],
                            "mention_count": 0,
                            "derivation_method": "spacy_record_terms",
                            "tags": [],
                        },
                    )
                    by_label[text_key(surface)] = node_id
                    if surface not in node["aliases"] and surface != node["label"]:
                        node["aliases"].append(surface)
                    node["mention_count"] = int(node.get("mention_count") or 0) + 1
                    if record_id not in node["record_ids"]:
                        node["record_ids"].append(record_id)
                    if tag and tag not in node["tags"]:
                        node["tags"].append(tag)
                mentions.append(
                    {
                        "start": int(term.get("start") or 0),
                        "end": int(term.get("end") or 0),
                        "text": str(term.get("text") or ""),
                        "layer": "ner" if source == "ner" else "pos",
                        "tag": tag,
                        "node_id": node_id,
                    }
                )
            self.term_mentions[record_id] = mentions

    def _resolve_id(self, node_id: str) -> str:
        return str((self.graph.get("node_aliases") or {}).get(node_id) or node_id)

    def _records_for_node(self, node_id: str) -> list[str]:
        """Every Record in which the node occurs or takes part in a relation.

        This is an indexed lookup. The previous implementation rebuilt the set by
        walking incident edges on every call, which multiplied work while ranking
        one Record and again while walking nodes.
        """
        return self.node_records.get(node_id, [])

    def _idf(self, document_frequency: int) -> float:
        total = max(1, len(self.record_order))
        return math.log((total + 1) / max(1, document_frequency))

    def _document_layer(self, record: dict[str, Any], analysis: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        local = record.get("document_intelligence")
        layer: dict[str, Any] = {
            "status": "missing",
            "provider": (local or {}).get("provider") if isinstance(local, dict) else analysis.get("provider"),
            "model": (local or {}).get("model") if isinstance(local, dict) else analysis.get("model"),
            "profile": analysis.get("profile") or ((local or {}).get("profile") if isinstance(local, dict) else None),
        }
        if analysis.get("status") == "unavailable":
            layer["status"] = "unavailable"
        if not isinstance(local, dict):
            return layer, []
        if analysis.get("stale") or local.get("record_text_sha256") != _sha256(str(record.get("text") or "")):
            layer["status"] = "stale"
            return layer, []
        layer["status"] = str(local.get("status") or "ok")
        mentions: list[dict[str, Any]] = []
        for item in local.get("entities") or []:
            if not isinstance(item, dict):
                continue
            node_id = self._resolve_id(document_entity_node_id(str(item.get("entity_id") or ""), str(item.get("label") or "")))
            mentions.append(
                {
                    "start": int(item.get("start") or 0),
                    "end": int(item.get("end") or 0),
                    "text": str(item.get("text") or ""),
                    "layer": "entity",
                    "tag": str(item.get("entity_type") or ""),
                    "mention_type": str(item.get("mention_type") or ""),
                    "node_id": node_id if node_id in self.nodes else "",
                }
            )
        for item in local.get("quotations") or []:
            if not isinstance(item, dict):
                continue
            speaker_id = str(item.get("speaker_entity_id") or "")
            speaker_node = (
                self._resolve_id(document_entity_node_id(speaker_id, str(item.get("speaker") or ""))) if speaker_id else ""
            )
            mentions.append(
                {
                    "start": int(item.get("start") or 0),
                    "end": int(item.get("end") or 0),
                    "text": str(item.get("text") or ""),
                    "layer": "quotation",
                    "tag": "QUOTE",
                    "speaker": str(item.get("speaker") or ""),
                    "node_id": speaker_node if speaker_node in self.nodes else "",
                }
            )
        return layer, mentions

    def record_map(self, record_id: str, analysis: dict[str, Any]) -> dict[str, Any]:
        record = self.record_by_id.get(record_id)
        if record is None:
            raise KeyError(record_id)
        document_layer, document_mentions = self._document_layer(record, analysis)
        term_mentions = self.term_mentions.get(record_id, [])
        text_length = len(str(record.get("text") or ""))
        mentions = sorted(
            (
                item
                for item in [*document_mentions, *term_mentions]
                if 0 <= item["start"] < item["end"] <= text_length
            ),
            key=lambda item: (item["start"], -item["end"], item["layer"]),
        )

        record_edges = self.edges_by_record.get(record_id, [])
        local_ids: set[str] = set(self.nodes_by_record.get(record_id, set()))
        local_ids.update(item["node_id"] for item in mentions if item.get("node_id"))
        local_ids &= set(self.nodes)

        in_record_degree: defaultdict[str, int] = defaultdict(int)
        for edge in record_edges:
            in_record_degree[str(edge["source"])] += 1
            in_record_degree[str(edge["target"])] += 1
        ranked_local = sorted(
            local_ids,
            key=lambda node_id: (
                self.nodes[node_id].get("type") == "term",
                -in_record_degree[node_id],
                -int(self.nodes[node_id].get("mention_count") or 0),
                str(self.nodes[node_id].get("label") or ""),
            ),
        )
        kept_local = set(ranked_local[:MAX_LOCAL_NODES])

        edges_out: list[dict[str, Any]] = [
            {**edge, "in_record": True}
            for edge in sorted(record_edges, key=_edge_rank)
            if edge["source"] in kept_local and edge["target"] in kept_local
        ]
        neighbor_ids: list[str] = []
        outward = sorted(
            (
                edge
                for node_id in ranked_local[:MAX_LOCAL_NODES]
                for edge in self.edges_by_node.get(node_id, [])
                if record_id not in (edge.get("record_ids") or [])
            ),
            key=_edge_rank,
        )
        seen_edges = {edge["id"] for edge in edges_out}
        for edge in outward:
            if edge["id"] in seen_edges:
                continue
            other = edge["target"] if edge["source"] in kept_local else edge["source"]
            if other in kept_local:
                edges_out.append({**edge, "in_record": False})
                seen_edges.add(edge["id"])
                continue
            if other not in neighbor_ids:
                if len(neighbor_ids) >= MAX_NEIGHBOR_NODES:
                    continue
                neighbor_ids.append(other)
            edges_out.append({**edge, "in_record": False})
            seen_edges.add(edge["id"])

        # Other Records are ranked by what they share with this one, weighting rare
        # nodes above ubiquitous ones and a shared semantic relation above a node.
        links: dict[str, dict[str, Any]] = {}

        def link(other: str) -> dict[str, Any]:
            return links.setdefault(
                other,
                {"record_id": other, "score": 0.0, "shared_node_ids": [], "shared_relation_ids": []},
            )

        for node_id in ranked_local:
            node_records = self._records_for_node(node_id)
            weight = self._idf(len(node_records)) * (0.5 if self.nodes[node_id].get("type") == "term" else 1.0)
            for other in node_records:
                if other == record_id:
                    continue
                row = link(other)
                row["score"] += weight
                row["shared_node_ids"].append(node_id)
        for edge in record_edges:
            if edge.get("relation_kind") != "semantic":
                continue
            others = [value for value in edge.get("record_ids") or [] if value in self.record_order]
            weight = 2 * self._idf(len(others))
            for other in others:
                if other == record_id:
                    continue
                row = link(other)
                row["score"] += weight
                row["shared_relation_ids"].append(edge["id"])
        linked = sorted(
            links.values(),
            key=lambda row: (-row["score"], self.record_order[row["record_id"]]),
        )[:MAX_LINKED_RECORDS]
        linked_records = [
            {
                "record_id": row["record_id"],
                "preview": _preview(self.record_by_id[row["record_id"]]),
                "score": round(row["score"], 3),
                "shared_node_count": len(row["shared_node_ids"]),
                "shared_nodes": [_node_ref(self.nodes[node_id]) for node_id in row["shared_node_ids"][:MAX_SHARED_PER_LINK]],
                "shared_relation_ids": row["shared_relation_ids"][:MAX_SHARED_PER_LINK],
            }
            for row in linked
        ]

        nodes_out = [
            {**self.nodes[node_id], "local": True, "record_count": len(self._records_for_node(node_id))}
            for node_id in ranked_local[:MAX_LOCAL_NODES]
        ] + [
            {**self.nodes[node_id], "local": False, "record_count": len(self._records_for_node(node_id))}
            for node_id in neighbor_ids
        ]
        for node in nodes_out:
            # The Record list is served per node through the neighbourhood read.
            node["record_ids"] = node["record_ids"][:MAX_NODE_RECORDS]
        return {
            "version": RECORD_SEMANTIC_MAP_VERSION,
            "kind": "record_semantic_map",
            "record_id": record_id,
            "record_revision": int(record.get("record_revision") or 0),
            "record_text_sha256": _sha256(str(record.get("text") or "")),
            "layers": {
                "document_intelligence": document_layer,
                "terms": {"status": self.term_state.get(record_id, "missing")},
            },
            "mentions": mentions,
            "nodes": nodes_out,
            "edges": edges_out,
            "linked_records": linked_records,
            "summary": {
                "local_nodes": len(local_ids),
                "shown_local_nodes": min(len(local_ids), MAX_LOCAL_NODES),
                "neighbor_nodes": len(neighbor_ids),
                "in_record_edges": sum(1 for edge in edges_out if edge["in_record"]),
                "outward_edges": sum(1 for edge in edges_out if not edge["in_record"]),
                "linked_records": len(links),
            },
            "epistemic_note": EPISTEMIC_NOTE,
        }

    def node_neighborhood(self, node_id: str) -> dict[str, Any]:
        # A Document Intelligence cluster merged into an identity node keeps answering to its id.
        node_id = str((self.graph.get("node_aliases") or {}).get(node_id) or node_id)
        node = self.nodes.get(node_id)
        if node is None:
            raise KeyError(node_id)
        adjacent = self.edges_by_node.get(node_id, [])
        neighbor_ids = list(
            dict.fromkeys(
                str(edge["target"] if edge["source"] == node_id else edge["source"])
                for edge in adjacent[:MAX_NODE_EDGES]
            )
        )
        record_ids = self._records_for_node(node_id)
        return {
            "version": RECORD_SEMANTIC_MAP_VERSION,
            "kind": "semantic_node_neighborhood",
            "node": {**node, "record_ids": record_ids[:MAX_NODE_RECORDS], "record_count": len(record_ids)},
            "nodes": [
                {**self.nodes[other], "record_ids": [], "record_count": len(self._records_for_node(other))}
                for other in neighbor_ids
                if other in self.nodes
            ],
            "edges": adjacent[:MAX_NODE_EDGES],
            "total_edges": len(adjacent),
            "records": [
                {"record_id": value, "preview": _preview(self.record_by_id[value])}
                for value in record_ids[:MAX_NODE_RECORDS]
            ],
            "total_records": len(record_ids),
            "epistemic_note": EPISTEMIC_NOTE,
        }

    def work_sources(self) -> dict[str, dict[str, Any]]:
        """Project canonical graph identities into the visual Work-map contract.

        The Work map keeps the established visual treatment, but its concepts,
        topics and persons now come from this same indexed semantic graph rather
        than a second browser-built semantic model.
        """
        by_work: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for record_id, record in self.record_by_id.items():
            work = _normalize(record.get("work") or record.get("document_title"))
            if not work:
                continue
            concepts: list[str] = []
            topics: list[str] = []
            persons: list[str] = []
            seen: set[tuple[str, str]] = set()
            for node_id in self.nodes_by_record.get(record_id, set()):
                node = self.nodes.get(node_id)
                if not node or node.get("type") == "term":
                    continue
                kind = str(node.get("type") or "")
                label = _normalize(node.get("label"))
                key = (kind, text_key(label))
                if not label or key in seen:
                    continue
                seen.add(key)
                if kind == "concept":
                    concepts.append(label)
                elif kind == "topic":
                    topics.append(label)
                elif kind in {"person", "character"}:
                    persons.append(label)
            by_work[work].append({
                "id": record_id,
                "work": work,
                "concepts": sorted(concepts, key=str.casefold),
                "topics": sorted(topics, key=str.casefold),
                "persons": sorted(persons, key=str.casefold),
            })
        return {
            work: {
                "version": RECORD_SEMANTIC_MAP_VERSION,
                "kind": "work_semantic_map_sources",
                "work": work,
                "sources": sources,
                "record_count": len(sources),
                "epistemic_note": EPISTEMIC_NOTE,
            }
            for work, sources in by_work.items()
        }

    def materialize(
        self,
        analysis: dict[str, Any],
    ) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        """Materialize all bounded projections from one shared index walk."""
        record_maps = {
            record_id: self.record_map(record_id, analysis)
            for record_id in self.record_by_id
        }
        node_maps = {
            node_id: self.node_neighborhood(node_id)
            for node_id in self.nodes
        }
        return record_maps, node_maps, self.work_sources()


def build_semantic_map_projections(
    graph: dict[str, Any],
    records: list[dict[str, Any]],
    *,
    analysis: dict[str, Any] | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Build Record, node, and Work projections with one shared traversal index."""
    return _SemanticIndex(graph, records).materialize(
        analysis if isinstance(analysis, dict) else {}
    )


def record_semantic_map(
    graph: dict[str, Any],
    records: list[dict[str, Any]],
    record_id: str,
    *,
    analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bounded semantic map centred on one Record; raises KeyError for an unknown Record."""
    return _SemanticIndex(graph, records).record_map(record_id, analysis if isinstance(analysis, dict) else {})


def semantic_node_neighborhood(
    graph: dict[str, Any],
    records: list[dict[str, Any]],
    node_id: str,
) -> dict[str, Any]:
    """One node, its adjacent relations, and the Records it occurs in; KeyError if unknown."""
    return _SemanticIndex(graph, records).node_neighborhood(node_id)
