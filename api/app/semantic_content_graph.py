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


def _record_for_span(
    record_spans: list[dict[str, Any]], start: int, end: int
) -> str:
    for span in record_spans:
        try:
            span_start = int(span.get("start") or 0)
            span_end = int(span.get("end") or 0)
        except (TypeError, ValueError):
            continue
        if span_start <= start and end <= span_end:
            return str(span.get("record_id") or "")
    return ""


def _feature_summary(
    values: Any, record_spans: list[dict[str, Any]], *, limit: int = 16
) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for item in values if isinstance(values, list) else []:
        if not isinstance(item, dict):
            continue
        label = str(item.get("lemma") or item.get("text") or "").strip()
        if not label:
            continue
        key = label.casefold()
        row = buckets.setdefault(
            key,
            {"label": label, "count": 0, "record_ids": []},
        )
        row["count"] = int(row.get("count") or 0) + 1
        try:
            start = int(item.get("start_char"))
            end = int(item.get("end_char"))
        except (TypeError, ValueError):
            continue
        record_id = _record_for_span(record_spans, start, end)
        if record_id and record_id not in row["record_ids"]:
            row["record_ids"].append(record_id)
    return sorted(
        buckets.values(),
        key=lambda item: (-int(item.get("count") or 0), str(item.get("label") or "")),
    )[:limit]


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
        row["mention_count"] = int(row.get("mention_count") or 0) + max(0, count)

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
        symmetric: bool = False,
        observation: dict[str, Any] | None = None,
    ) -> None:
        if not source or not target or source == target:
            return
        # Only explicitly symmetric observations (co-occurrence/dialogue
        # proximity) canonicalize endpoint order. Agent→patient observations
        # remain directed.
        if symmetric and source > target:
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
                "observations": [],
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
        if observation and observation not in row["observations"] and len(row["observations"]) < 50:
            row["observations"].append(observation)
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

    # Attach BookNLP's character/action summaries to Fiction nodes as derived
    # observations. Referential-gender estimates are intentionally not carried
    # into the graph as character facts.
    characters_by_cluster = {
        str(item.get("cluster_id") or ""): item
        for item in (analysis.get("characters") or [])
        if isinstance(item, dict) and item.get("cluster_id")
    }
    for cluster_id, character in characters_by_cluster.items():
        node_id = cluster_nodes.get(cluster_id)
        if not node_id or graph.nodes[node_id].get("type") != "character":
            continue
        graph.nodes[node_id]["character_profile"] = {
            "actions_as_agent": _feature_summary(
                character.get("actions_as_agent"), record_spans
            ),
            "actions_as_patient": _feature_summary(
                character.get("actions_as_patient"), record_spans
            ),
            "possessions": _feature_summary(character.get("possessions"), record_spans),
            "modifiers": _feature_summary(character.get("modifiers"), record_spans),
        }
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
                graph.mention(
                    node_id,
                    record_id,
                    count=0 if node_id in cluster_nodes.values() else 1,
                )
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
                    cooccurrence_nodes.append(node_id)
        for left, right in itertools.combinations(sorted(set(cooccurrence_nodes)), 2):
            graph.edge(
                left,
                "co_occurs",
                right,
                relation_kind="observational",
                record_id=record_id,
                derivation_method="computed_cooccurrence",
                symmetric=True,
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
                    symmetric=True,
                )

    # BookNLP's .book summaries identify characters that share a verb token
    # as syntactic agent/patient. This is stronger than co-occurrence but still
    # only a model-derived linguistic observation; it is never promoted to a
    # literary relationship or evidence.
    if profile == "fiction":
        agents_by_token: defaultdict[int, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
        patients_by_token: defaultdict[int, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
        for cluster_id, character in characters_by_cluster.items():
            node_id = cluster_nodes.get(cluster_id)
            if not node_id:
                continue
            for item in character.get("actions_as_agent") or []:
                if not isinstance(item, dict):
                    continue
                try:
                    token_id = int(item.get("token_id"))
                except (TypeError, ValueError):
                    continue
                agents_by_token[token_id].append((node_id, item))
            for item in character.get("actions_as_patient") or []:
                if not isinstance(item, dict):
                    continue
                try:
                    token_id = int(item.get("token_id"))
                except (TypeError, ValueError):
                    continue
                patients_by_token[token_id].append((node_id, item))

        for token_id in sorted(set(agents_by_token) & set(patients_by_token)):
            for source, agent_item in agents_by_token[token_id]:
                for target, patient_item in patients_by_token[token_id]:
                    if source == target:
                        continue
                    item = agent_item if agent_item.get("start_char") is not None else patient_item
                    try:
                        start = int(item.get("start_char"))
                        end = int(item.get("end_char"))
                    except (TypeError, ValueError):
                        start = end = -1
                    record_id = _record_for_span(record_spans, start, end) if start >= 0 else ""
                    verb = str(
                        agent_item.get("lemma")
                        or agent_item.get("text")
                        or patient_item.get("lemma")
                        or patient_item.get("text")
                        or ""
                    ).strip()
                    graph.edge(
                        source,
                        "acts_on",
                        target,
                        relation_kind="observational",
                        record_id=record_id,
                        derivation_method="booknlp_character_syntax",
                        observation={
                            "verb": verb,
                            "token_id": token_id,
                            "record_id": record_id,
                        },
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
            "dialogue proximity, or syntactic agent/patient structure. They do not assert "
            "a stronger scholarly or literary relationship. "
            "Semantic edges preserve the authority and evidence state of the metadata that produced them."
        ),
    }


# Bounded read model -------------------------------------------------------
#
# A corpus graph can hold tens of thousands of entities and far more
# co-occurrence edges. Clients never receive the whole projection: they ask for
# a filtered, ranked, size-capped *view* (an overview or one entity's
# neighbourhood) plus a paged entity index. Truncation is always reported so a
# reviewer is never led to believe a partial map is complete.

VIEW_MAX_NODES = 250
VIEW_MAX_EDGES = 1200
INDEX_MAX_PAGE = 200
FOCUS_MAX_RELATIONS = 200
_INDEX_SORTS = {"mentions", "label", "degree", "records"}
_RELATION_KINDS = {"all", "semantic", "observational"}


def _clamp(value: Any, low: int, high: int, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def _compact_node(node: dict[str, Any], degree: int) -> dict[str, Any]:
    return {
        "id": node["id"],
        "type": node.get("type") or "entity",
        "label": node.get("label") or "",
        "aliases": list(node.get("aliases") or [])[:12],
        "mention_count": int(node.get("mention_count") or 0),
        "record_count": len(node.get("record_ids") or []),
        "degree": degree,
    }


def _compact_edge(edge: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": edge["id"],
        "source": edge["source"],
        "target": edge["target"],
        "predicate": edge.get("predicate") or "",
        "relation_kind": edge.get("relation_kind") or "observational",
        "authority_status": edge.get("authority_status") or "unreviewed",
        "count": int(edge.get("count") or 0),
    }


def _matches(node: dict[str, Any], query: str) -> bool:
    if not query:
        return True
    return any(
        query in str(value or "").casefold()
        for value in [node.get("label"), *(node.get("aliases") or [])]
    )


def semantic_content_graph_view(
    graph: dict[str, Any],
    *,
    query: str = "",
    types: list[str] | None = None,
    relation_kind: str = "all",
    focus: str = "",
    node_limit: int = 80,
    edge_limit: int = 400,
    min_mentions: int = 0,
    index_offset: int = 0,
    index_limit: int = 50,
    index_sort: str = "mentions",
) -> dict[str, Any]:
    """Return a bounded, ranked slice of ``graph`` suitable for interactive display.

    * Overview (no ``focus``): the highest-ranked matching entities and the
      strongest relations among them.
    * Focus: the entity, its strongest neighbours, and its paged relations.

    The full graph stays server-side; totals and ``truncated`` flags describe
    what was left out.
    """
    node_limit = _clamp(node_limit, 1, VIEW_MAX_NODES, 80)
    edge_limit = _clamp(edge_limit, 0, VIEW_MAX_EDGES, 400)
    index_limit = _clamp(index_limit, 1, INDEX_MAX_PAGE, 50)
    index_offset = max(0, _clamp(index_offset, 0, 10**9, 0))
    min_mentions = max(0, _clamp(min_mentions, 0, 10**9, 0))
    relation_kind = relation_kind if relation_kind in _RELATION_KINDS else "all"
    index_sort = index_sort if index_sort in _INDEX_SORTS else "mentions"
    wanted_types = {str(value) for value in (types or []) if str(value)}
    needle = re.sub(r"\s+", " ", str(query or "")).strip().casefold()

    all_nodes: list[dict[str, Any]] = [n for n in graph.get("nodes") or [] if isinstance(n, dict)]
    nodes_by_id = {str(node.get("id")): node for node in all_nodes}
    all_edges = [
        edge
        for edge in graph.get("edges") or []
        if isinstance(edge, dict)
        and edge.get("source") in nodes_by_id
        and edge.get("target") in nodes_by_id
    ]
    kind_edges = [
        edge
        for edge in all_edges
        if relation_kind == "all" or edge.get("relation_kind") == relation_kind
    ]
    degree: defaultdict[str, int] = defaultdict(int)
    for edge in kind_edges:
        degree[edge["source"]] += 1
        degree[edge["target"]] += 1

    type_counts: defaultdict[str, int] = defaultdict(int)
    for node in all_nodes:
        type_counts[str(node.get("type") or "entity")] += 1
    predicate_counts: defaultdict[tuple[str, str], int] = defaultdict(int)
    for edge in all_edges:
        predicate_counts[(str(edge.get("relation_kind")), str(edge.get("predicate")))] += 1

    def eligible(node: dict[str, Any]) -> bool:
        if wanted_types and str(node.get("type") or "entity") not in wanted_types:
            return False
        if int(node.get("mention_count") or 0) < min_mentions:
            return False
        return _matches(node, needle)

    matching = [node for node in all_nodes if eligible(node)]

    def rank(node: dict[str, Any]) -> tuple[Any, ...]:
        return (
            -int(node.get("mention_count") or 0),
            -degree.get(str(node["id"]), 0),
            str(node.get("label") or "").casefold(),
        )

    def edge_rank(edge: dict[str, Any]) -> tuple[Any, ...]:
        # Evidence-aware relations outrank computational observations at equal weight.
        return (
            -int(edge.get("count") or 0),
            0 if edge.get("relation_kind") == "semantic" else 1,
            str(edge.get("id") or ""),
        )

    focus_node = nodes_by_id.get(str(focus or "")) if focus else None
    focus_payload: dict[str, Any] | None = None
    if focus_node is not None:
        focus_id = str(focus_node["id"])
        incident = sorted(
            (e for e in kind_edges if focus_id in (e["source"], e["target"])),
            key=edge_rank,
        )
        neighbour_ids: list[str] = []
        seen: set[str] = {focus_id}
        for edge in incident:
            other = edge["target"] if edge["source"] == focus_id else edge["source"]
            if other in seen:
                continue
            node = nodes_by_id[other]
            if wanted_types and str(node.get("type") or "entity") not in wanted_types:
                continue
            seen.add(other)
            neighbour_ids.append(other)
        shown_ids = [focus_id, *neighbour_ids[: node_limit - 1]]
        candidate_total = 1 + len(neighbour_ids)
        relations = []
        for edge in incident[:FOCUS_MAX_RELATIONS]:
            other = edge["target"] if edge["source"] == focus_id else edge["source"]
            relations.append(
                {
                    **_compact_edge(edge),
                    "direction": "outgoing" if edge["source"] == focus_id else "incoming",
                    "other_id": other,
                    "other_label": nodes_by_id[other].get("label") or "",
                    "other_type": nodes_by_id[other].get("type") or "entity",
                    "record_ids": list(edge.get("record_ids") or [])[:20],
                    "record_count": len(edge.get("record_ids") or []),
                    "supporting_fields": list(edge.get("supporting_fields") or []),
                    "derivation_method": edge.get("derivation_method") or "",
                    "evidence_ref_count": len(edge.get("evidence_refs") or []),
                    "observed_verbs": list(
                        dict.fromkeys(
                            str(item.get("verb") or "").strip()
                            for item in (edge.get("observations") or [])
                            if isinstance(item, dict) and str(item.get("verb") or "").strip()
                        )
                    )[:8],
                }
            )
        focus_payload = {
            "node": {
                **_compact_node(focus_node, degree.get(focus_id, 0)),
                "aliases": list(focus_node.get("aliases") or []),
                "derivation_method": focus_node.get("derivation_method") or "",
                "record_ids": list(focus_node.get("record_ids") or [])[:50],
                "character_profile": focus_node.get("character_profile"),
            },
            "relations": relations,
            "relations_total": len(incident),
        }
    else:
        focus_id = ""
        shown_ids = [str(node["id"]) for node in sorted(matching, key=rank)[:node_limit]]
        candidate_total = len(matching)

    shown = set(shown_ids)
    induced = sorted(
        (e for e in kind_edges if e["source"] in shown and e["target"] in shown),
        key=edge_rank,
    )
    if focus_id:
        # Keep every spoke to the focus before any neighbour-to-neighbour edge.
        induced.sort(key=lambda e: 0 if focus_id in (e["source"], e["target"]) else 1)
    view_edges = induced[:edge_limit]

    if index_sort == "label":
        index_rows = sorted(matching, key=lambda n: str(n.get("label") or "").casefold())
    elif index_sort == "degree":
        index_rows = sorted(matching, key=lambda n: (-degree.get(str(n["id"]), 0), *rank(n)))
    elif index_sort == "records":
        index_rows = sorted(matching, key=lambda n: (-len(n.get("record_ids") or []), *rank(n)))
    else:
        index_rows = sorted(matching, key=rank)

    return {
        "version": 1,
        "kind": "semantic_content_graph_view",
        "profile": graph.get("profile"),
        "records_digest": graph.get("records_digest"),
        "summary": graph.get("summary") or {},
        "epistemic_note": graph.get("epistemic_note") or "",
        "facets": {
            "types": [
                {"type": key, "count": value}
                for key, value in sorted(type_counts.items(), key=lambda kv: (-kv[1], kv[0]))
            ],
            "predicates": [
                {"relation_kind": kind, "predicate": predicate, "count": value}
                for (kind, predicate), value in sorted(
                    predicate_counts.items(), key=lambda kv: (-kv[1], kv[0])
                )[:40]
            ],
        },
        "query": {
            "query": needle,
            "types": sorted(wanted_types),
            "relation_kind": relation_kind,
            "focus": focus_id,
            "node_limit": node_limit,
            "edge_limit": edge_limit,
            "min_mentions": min_mentions,
        },
        "view": {
            "nodes": [_compact_node(nodes_by_id[i], degree.get(i, 0)) for i in shown_ids],
            "edges": [_compact_edge(edge) for edge in view_edges],
            "candidate_nodes": candidate_total,
            "candidate_edges": len(induced),
            "truncated_nodes": candidate_total > len(shown_ids),
            "truncated_edges": len(induced) > len(view_edges),
        },
        "focus": focus_payload,
        "index": {
            "items": [
                _compact_node(n, degree.get(str(n["id"]), 0))
                for n in index_rows[index_offset : index_offset + index_limit]
            ],
            "total": len(matching),
            "offset": index_offset,
            "limit": index_limit,
            "sort": index_sort,
        },
    }
