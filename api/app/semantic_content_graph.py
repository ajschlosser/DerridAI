# Copyright 2026 Aaron John Schlosser, PhD.
"""Derived semantic-content graph for corpus navigation and analysis.

This graph is intentionally distinct from DerridAI's cELF ResearchObjectGraph.  It
models people/characters, concepts, works, topics, and relationships *within* the
document.  Nodes and edges are projections over document intelligence and canonical
Record metadata; they are rebuildable and must never be treated as documentary
evidence by themselves.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import re
from collections import defaultdict
from typing import Any

from .field_assertions import current_assertion_by_name, migrate_record_assertions


def _slug(value: str) -> str:
    normalized = re.sub(r"\s+", " ", str(value or "")).strip().casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _node_id(kind: str, label: str) -> str:
    return f"{kind}:{_slug(label)}"


def _values(value: Any) -> list[str]:
    if value in (None, "", []):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _authority(record: dict[str, Any], fields: list[str]) -> str:
    statuses: list[str] = []
    for field in fields:
        assertion = current_assertion_by_name(record, field)
        if assertion is not None:
            statuses.append(str(assertion.authority_status or "unreviewed"))
            continue
        info = (record.get("metadata_field_status") or {}).get(field)
        if isinstance(info, dict):
            state = str(info.get("status") or "")
            statuses.append(
                "human_confirmed"
                if state == "human_confirmed"
                else "human_override"
                if state == "human_override"
                else "unreviewed"
            )
    if statuses and all(value in {"human_confirmed", "human_override"} for value in statuses):
        return "human_confirmed"
    if "disputed" in statuses:
        return "disputed"
    return "unreviewed"


def _evidence(record: dict[str, Any], fields: list[str]) -> list[dict[str, Any]]:
    by_field = record.get("metadata_evidence")
    refs: list[dict[str, Any]] = []
    if not isinstance(by_field, dict):
        return refs
    for field in fields:
        info = by_field.get(field)
        if not isinstance(info, dict):
            continue
        block_ids = [str(value) for value in (info.get("block_ids") or []) if value]
        external = [str(value) for value in (info.get("external_block_ids") or []) if value]
        if block_ids or external:
            refs.append(
                {
                    "record_id": str(record.get("record_id") or ""),
                    "record_revision": int(record.get("record_revision") or 0),
                    "field": field,
                    "block_ids": block_ids,
                    "external_block_ids": external,
                }
            )
    return refs


def _records_digest(records: list[dict[str, Any]]) -> str:
    material = [
        {
            "record_id": record.get("record_id"),
            "revision": record.get("record_revision"),
            "text": hashlib.sha256(str(record.get("text") or "").encode("utf-8")).hexdigest(),
            "speaker": record.get("speaker"),
            "position_holder": record.get("position_holder"),
            "target": record.get("target"),
            "stance": record.get("stance"),
            "persons": record.get("persons"),
            "concepts": record.get("concepts"),
            "works_referenced": record.get("works_referenced"),
            "topics": record.get("topics"),
            "quoted_speaker": record.get("quoted_speaker"),
            "quoted_author": record.get("quoted_author"),
            "quoted_work": record.get("quoted_work"),
        }
        for record in records
    ]
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


class _Graph:
    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: dict[tuple[str, str, str, str], dict[str, Any]] = {}

    def node(
        self,
        kind: str,
        label: str,
        *,
        aliases: list[str] | None = None,
        derivation_method: str = "metadata_projection",
        entity_id: str = "",
    ) -> str:
        label = re.sub(r"\s+", " ", str(label or "")).strip()
        if not label:
            return ""
        node_id = entity_id or _node_id(kind, label)
        row = self.nodes.setdefault(
            node_id,
            {
                "id": node_id,
                "type": kind,
                "label": label,
                "aliases": [],
                "record_ids": [],
                "mention_count": 0,
                "derivation_method": derivation_method,
            },
        )
        known = list(row.get("aliases") or [])
        row["aliases"] = list(
            dict.fromkeys(
                [*known, *[str(value) for value in (aliases or []) if str(value).strip()]]
            )
        )
        return node_id

    def mention(self, node_id: str, record_id: str, count: int = 1) -> None:
        if not node_id or node_id not in self.nodes:
            return
        row = self.nodes[node_id]
        if record_id and record_id not in row["record_ids"]:
            row["record_ids"].append(record_id)
        row["mention_count"] = int(row.get("mention_count") or 0) + max(1, count)

    def edge(
        self,
        source: str,
        predicate: str,
        target: str,
        *,
        relation_kind: str,
        record_id: str,
        derivation_method: str,
        authority_status: str = "unreviewed",
        evidence_refs: list[dict[str, Any]] | None = None,
        supporting_fields: list[str] | None = None,
    ) -> None:
        if not source or not target or source == target:
            return
        # Observational relations are symmetric.  Canonicalize their endpoint
        # order so repeated Records increment one edge rather than producing two.
        if relation_kind == "observational" and source > target:
            source, target = target, source
        key = (source, predicate, target, relation_kind)
        row = self.edges.setdefault(
            key,
            {
                "id": f"relation:{hashlib.sha256('|'.join(key).encode('utf-8')).hexdigest()[:20]}",
                "source": source,
                "target": target,
                "predicate": predicate,
                "relation_kind": relation_kind,
                "derivation_method": derivation_method,
                "authority_status": authority_status,
                "record_ids": [],
                "evidence_refs": [],
                "supporting_fields": [],
                "count": 0,
            },
        )
        prior_count = int(row.get("count") or 0)
        row["count"] = prior_count + 1
        if record_id and record_id not in row["record_ids"]:
            row["record_ids"].append(record_id)
        for ref in evidence_refs or []:
            if ref not in row["evidence_refs"]:
                row["evidence_refs"].append(ref)
        row["supporting_fields"] = list(
            dict.fromkeys([*row["supporting_fields"], *(supporting_fields or [])])
        )
        # An aggregate edge must never look more authoritative than all of
        # its supporting occurrences. One unreviewed occurrence therefore
        # downgrades a previously confirmed aggregate; any dispute dominates.
        incoming = (
            "human_confirmed"
            if authority_status in {"human_confirmed", "human_override"}
            else authority_status
        )
        existing = str(row.get("authority_status") or "unreviewed")
        if prior_count == 0:
            row["authority_status"] = incoming
        elif "disputed" in {existing, incoming}:
            row["authority_status"] = "disputed"
        elif existing == "human_confirmed" and incoming == "human_confirmed":
            row["authority_status"] = "human_confirmed"
        else:
            row["authority_status"] = "unreviewed"


def build_semantic_content_graph(
    records: list[dict[str, Any]],
    analysis: dict[str, Any] | None = None,
    *,
    schema: Any = None,
) -> dict[str, Any]:
    """Build a current graph from canonical Records and optional NLP annotations."""
    analysis = analysis if isinstance(analysis, dict) else {}
    graph = _Graph()
    cluster_nodes: dict[str, str] = {}
    profile = str(analysis.get("profile") or "scholarly")

    for cluster in analysis.get("entity_clusters") or []:
        if not isinstance(cluster, dict):
            continue
        entity_type = str(cluster.get("entity_type") or "").upper()
        label = str(cluster.get("canonical") or "")
        if not label:
            continue
        kind = (
            "character"
            if profile == "fiction" and entity_type in {"PER", "PERSON"}
            else "person"
            if entity_type in {"PER", "PERSON"}
            else "organization"
            if entity_type == "ORG"
            else "place"
            if entity_type in {"LOC", "GPE", "FAC"}
            else "entity"
        )
        cluster_id = str(cluster.get("cluster_id") or "")
        stable_id = f"document_entity:{_slug(cluster_id + ':' + label)}"
        node_id = graph.node(
            kind,
            label,
            aliases=[str(value) for value in (cluster.get("aliases") or [])],
            derivation_method=str(analysis.get("provider") or "document_nlp"),
            entity_id=stable_id,
        )
        if cluster_id:
            cluster_nodes[cluster_id] = node_id

    # Project document-level mentions onto node occurrence counts.
    record_spans = [
        span for span in (analysis.get("record_spans") or []) if isinstance(span, dict)
    ]
    for mention in analysis.get("entities") or []:
        if not isinstance(mention, dict):
            continue
        node_id = cluster_nodes.get(str(mention.get("cluster_id") or ""))
        if not node_id:
            continue
        try:
            start, end = int(mention.get("start_char")), int(mention.get("end_char"))
        except (TypeError, ValueError):
            continue
        owning = next(
            (
                span
                for span in record_spans
                if int(span.get("start") or 0) <= start
                and end <= int(span.get("end") or 0)
            ),
            None,
        )
        graph.mention(node_id, str((owning or {}).get("record_id") or ""))

    labels_to_nodes: defaultdict[str, list[str]] = defaultdict(list)
    for node_id, node in graph.nodes.items():
        labels_to_nodes[str(node.get("label") or "").casefold()].append(node_id)
        for alias in node.get("aliases") or []:
            labels_to_nodes[str(alias).casefold()].append(node_id)

    def metadata_node(kind: str, label: str, *, prefer_existing: bool = False) -> str:
        existing = labels_to_nodes.get(label.casefold())
        if existing and (prefer_existing or kind in {"person", "character"}):
            return existing[0]
        node_id = graph.node(kind, label)
        labels_to_nodes[label.casefold()].append(node_id)
        return node_id

    for record in records:
        migrate_record_assertions(record, schema)
        record_id = str(record.get("record_id") or "")
        field_nodes: dict[str, list[str]] = {}
        for field, kind in (
            ("persons", "person"),
            ("concepts", "concept"),
            ("works_referenced", "work"),
            ("topics", "topic"),
        ):
            ids: list[str] = []
            for label in _values(record.get(field)):
                node_id = metadata_node(kind, label)
                graph.mention(node_id, record_id)
                ids.append(node_id)
            field_nodes[field] = ids

        # Co-occurrence is an observational relation only.  It never means the
        # nodes agree, influence one another, converse, or stand in any stronger
        # semantic relationship.
        cooccurrence_nodes = list(
            dict.fromkeys(
                [
                    *field_nodes["persons"],
                    *field_nodes["concepts"],
                    *field_nodes["works_referenced"],
                    *field_nodes["topics"],
                ]
            )
        )
        local_doc = record.get("document_intelligence")
        if isinstance(local_doc, dict):
            for mention in local_doc.get("entities") or []:
                if not isinstance(mention, dict):
                    continue
                node_id = cluster_nodes.get(str(mention.get("entity_id") or ""))
                if node_id:
                    graph.mention(node_id, record_id)
                    cooccurrence_nodes.append(node_id)
        for left, right in itertools.combinations(sorted(set(cooccurrence_nodes)), 2):
            graph.edge(
                left,
                "co_occurs",
                right,
                relation_kind="observational",
                record_id=record_id,
                derivation_method="computed_cooccurrence",
            )

        # The existing scholarly attribution fields can project stronger directed
        # relations without another model call.  Their assertion/evidence state is
        # carried onto the graph edge.
        holders = _values(record.get("position_holder"))
        targets = _values(record.get("target"))
        stance = str(record.get("stance") or "").strip()
        if holders and targets:
            supporting = ["position_holder", "target"] + (["stance"] if stance else [])
            predicate = stance or "addresses"
            for holder in holders:
                source = metadata_node("person", holder)
                for target in targets:
                    # target is polymorphic in scholarly prose: it may be a
                    # person, work, concept, institution, etc. Reuse an entity
                    # already established by the document/indexing layer before
                    # falling back to a concept node.
                    target_id = metadata_node("concept", target, prefer_existing=True)
                    graph.edge(
                        source,
                        predicate,
                        target_id,
                        relation_kind="semantic",
                        record_id=record_id,
                        derivation_method="field_assertion_projection",
                        authority_status=_authority(record, supporting),
                        evidence_refs=_evidence(record, supporting),
                        supporting_fields=supporting,
                    )

        speakers = _values(record.get("speaker"))
        quoted_speakers = _values(record.get("quoted_speaker"))
        quoted_authors = _values(record.get("quoted_author"))
        quoted_works = _values(record.get("quoted_work"))
        for speaker in speakers:
            source = metadata_node("person", speaker)
            for quoted in [*quoted_speakers, *quoted_authors]:
                target = metadata_node("person", quoted)
                graph.edge(
                    source,
                    "quotes",
                    target,
                    relation_kind="semantic",
                    record_id=record_id,
                    derivation_method="field_assertion_projection",
                    authority_status=_authority(record, ["speaker", "quoted_speaker"]),
                    evidence_refs=_evidence(record, ["speaker", "quoted_speaker", "quoted_author"]),
                    supporting_fields=["speaker", "quoted_speaker", "quoted_author"],
                )
        for author in quoted_authors:
            source = metadata_node("person", author)
            for work in quoted_works:
                target = metadata_node("work", work)
                graph.edge(
                    source,
                    "quoted_work",
                    target,
                    relation_kind="semantic",
                    record_id=record_id,
                    derivation_method="field_assertion_projection",
                    authority_status=_authority(record, ["quoted_author", "quoted_work"]),
                    evidence_refs=_evidence(record, ["quoted_author", "quoted_work"]),
                    supporting_fields=["quoted_author", "quoted_work"],
                )

        # BookNLP speaker clusters support a useful dialogue-proximity observation
        # without pretending to know the addressee.
        if isinstance(local_doc, dict):
            quote_speakers_local = []
            for quote in local_doc.get("quotations") or []:
                if not isinstance(quote, dict):
                    continue
                entity_id = str(quote.get("speaker_entity_id") or "")
                node_id = cluster_nodes.get(entity_id)
                if node_id:
                    quote_speakers_local.append(node_id)
            for left, right in itertools.combinations(sorted(set(quote_speakers_local)), 2):
                graph.edge(
                    left,
                    "dialogue_proximity",
                    right,
                    relation_kind="observational",
                    record_id=record_id,
                    derivation_method="booknlp_quote_projection",
                )

    nodes = sorted(
        graph.nodes.values(),
        key=lambda item: (-int(item.get("mention_count") or 0), str(item.get("label") or "")),
    )
    edges = sorted(
        graph.edges.values(),
        key=lambda item: (-int(item.get("count") or 0), str(item.get("predicate") or "")),
    )
    return {
        "version": 1,
        "kind": "semantic_content_graph",
        "records_digest": _records_digest(records),
        "document_intelligence_sha256": analysis.get("text_sha256"),
        "profile": profile,
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "nodes": len(nodes),
            "edges": len(edges),
            "semantic_edges": sum(1 for edge in edges if edge["relation_kind"] == "semantic"),
            "observational_edges": sum(
                1 for edge in edges if edge["relation_kind"] == "observational"
            ),
            "characters": sum(1 for node in nodes if node["type"] == "character"),
            "persons": sum(1 for node in nodes if node["type"] == "person"),
            "concepts": sum(1 for node in nodes if node["type"] == "concept"),
            "works": sum(1 for node in nodes if node["type"] == "work"),
        },
        "epistemic_note": (
            "Observational edges report bounded computational patterns such as co-occurrence "
            "or dialogue proximity. They do not assert a stronger scholarly relationship. "
            "Semantic edges preserve the authority and evidence state of the metadata that produced them."
        ),
    }
