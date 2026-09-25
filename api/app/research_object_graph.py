# Copyright 2026 Aaron John Schlosser, PhD.
"""Build walkable instance graphs over DERRIDAI research objects."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from .derridai_model import relationship_for


def _stable_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()[:12]


def _node_id(object_type: str, object_id: str) -> str:
    return f"{object_type}:{object_id}"


def _present(value: Any, *, limit: int = 120) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


class ObjectGraphBuilder:
    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: dict[str, dict[str, Any]] = {}

    def add_node(
        self,
        object_type: str,
        object_id: str,
        *,
        label: str,
        summary: str = "",
        materialization: str = "materialized",
        status: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> str:
        graph_id = _node_id(object_type, object_id)
        self.nodes[graph_id] = {
            "id": graph_id,
            "object_type": object_type,
            "object_id": object_id,
            "label": label,
            "summary": summary,
            "materialization": materialization,
            "status": status,
            "details": details or {},
        }
        return graph_id

    def add_edge(
        self,
        source: str,
        target: str,
        *,
        relation: str | None = None,
        inverse_relation: str | None = None,
        normative: bool | None = None,
        source_cardinality: str | None = None,
        target_cardinality: str | None = None,
        profile: str | None = None,
        status: str | None = None,
    ) -> None:
        source_type = self.nodes[source]["object_type"]
        target_type = self.nodes[target]["object_type"]
        registry = relationship_for(source_type, target_type)
        resolved_relation = relation or (registry or {}).get("relation") or "related to"
        resolved_inverse = inverse_relation or (registry or {}).get("inverse_relation") or "related from"
        edge_id = f"{source}|{resolved_relation}|{target}"
        self.edges[edge_id] = {
            "id": edge_id,
            "source": source,
            "target": target,
            "relation": resolved_relation,
            "inverse_relation": resolved_inverse,
            "normative": bool((registry or {}).get("normative")) if normative is None else normative,
            "source_cardinality": source_cardinality or (registry or {}).get("source_cardinality"),
            "target_cardinality": target_cardinality or (registry or {}).get("target_cardinality"),
            "profile": profile or (registry or {}).get("profile"),
            "status": status,
        }

    def payload(self, root_id: str) -> dict[str, Any]:
        return {
            "specification_version": "1.0",
            "root_id": root_id,
            "nodes": list(self.nodes.values()),
            "edges": list(self.edges.values()),
        }


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _span_locator(span: dict[str, Any], source_document_id: str) -> dict[str, Any]:
    return {
        "source_document_id": str(span.get("source_document_id") or source_document_id),
        "source_span_id": span.get("source_span_id"),
        "source_unit_id": span.get("source_unit_id") or span.get("block_id"),
        "source_unit_ids": span.get("source_unit_ids") or [],
        "physical_page_start": _first_present(span.get("physical_page_start"), span.get("pdf_page"), span.get("page")),
        "physical_page_end": _first_present(span.get("physical_page_end"), span.get("pdf_page"), span.get("page")),
        "printed_page_start": _first_present(span.get("printed_page_start"), span.get("printed_page_label")),
        "printed_page_end": _first_present(span.get("printed_page_end"), span.get("printed_page_label")),
        "character_start": _first_present(span.get("character_start"), span.get("char_start"), span.get("start")),
        "character_end": _first_present(span.get("character_end"), span.get("char_end"), span.get("end")),
    }


def _add_span(
    graph: ObjectGraphBuilder,
    span: dict[str, Any],
    *,
    source_document_id: str,
    materialization: str,
) -> str:
    locator = _span_locator(span, source_document_id)
    span_id = str(locator.get("source_span_id") or "").strip() or _stable_digest(locator)
    pages = locator.get("printed_page_start") or locator.get("physical_page_start")
    summary = f"Page {pages}" if pages not in (None, "") else "Documentary source region"
    return graph.add_node(
        "SourceSpan",
        span_id,
        label=f"Source span {span_id}",
        summary=summary,
        materialization=materialization,
        details={k: v for k, v in locator.items() if v not in (None, "", [])},
    )


def build_record_graph(
    record: dict[str, Any],
    *,
    claims: list[dict[str, Any]] | None = None,
    support_bindings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a finite graph that can be re-centered client-side without losing branches."""
    record_id = str(record.get("record_id") or "").strip()
    if not record_id:
        raise ValueError("A traceability graph requires record_id.")

    graph = ObjectGraphBuilder()
    revision = int(record.get("record_revision") or 1)
    work = str(record.get("work") or record.get("document_title") or "").strip()
    page_start = record.get("page_start")
    page_end = record.get("page_end")
    page = ""
    if page_start not in (None, ""):
        page = str(page_start) if page_end in (None, "", page_start) else f"{page_start}–{page_end}"
    root = graph.add_node(
        "Record",
        record_id,
        label=f"Record {record_id}",
        summary=" · ".join(value for value in (work, f"pp. {page}" if page else "") if value),
        details={"record_revision": revision, "work": work or None, "page_span": page or None},
    )

    source_document_id = str(
        record.get("source_document_id") or record.get("source_asset_id") or ""
    ).strip()
    source_document_node: str | None = None
    if source_document_id:
        source_document_node = graph.add_node(
            "SourceDocument",
            source_document_id,
            label=str(record.get("document_title") or record.get("work") or source_document_id),
            summary=_present(record.get("document_author")),
            details={
                "source_document_id": source_document_id,
                "document_author": record.get("document_author"),
                "edition": record.get("edition"),
                "publication_year": record.get("publication_year"),
            },
        )
        graph.add_edge(source_document_node, root)

    revision_node = graph.add_node(
        "RecordRevision",
        f"{record_id}@{revision}",
        label=f"Revision {revision}",
        summary=f"State of {record_id}",
        details={"record_id": record_id, "record_revision": revision},
    )
    graph.add_edge(root, revision_node)

    span_nodes: dict[str, str] = {}
    for span in record.get("source_spans") or []:
        if not isinstance(span, dict):
            continue
        node = _add_span(
            graph,
            span,
            source_document_id=source_document_id,
            materialization="embedded",
        )
        span_nodes[node] = node
        if source_document_node:
            graph.add_edge(source_document_node, node)
        graph.add_edge(root, node)

    assertion_by_id: dict[str, str] = {}
    buckets = record.get("field_assertions")
    if isinstance(buckets, dict):
        for values in buckets.values():
            if not isinstance(values, list):
                continue
            for assertion in values:
                if not isinstance(assertion, dict):
                    continue
                assertion_id = str(assertion.get("assertion_id") or "").strip()
                if not assertion_id:
                    continue
                field_name = str(assertion.get("field_name") or assertion.get("field_id") or "field")
                value = assertion.get("value")
                node = graph.add_node(
                    "FieldAssertion",
                    assertion_id,
                    label=field_name,
                    summary=_present(value),
                    status=str(assertion.get("authority_status") or assertion.get("evaluation_status") or "") or None,
                    details={
                        key: assertion.get(key)
                        for key in (
                            "field_id",
                            "field_name",
                            "derivation_method",
                            "evaluation_status",
                            "authority_status",
                            "value_status",
                            "confidence",
                            "method",
                            "model",
                            "run_id",
                            "supersedes_assertion_id",
                        )
                        if key in assertion
                    },
                )
                assertion_by_id[assertion_id] = node
                graph.add_edge(root, node)
                if int(assertion.get("record_revision") or revision) == revision:
                    graph.add_edge(revision_node, node)

        for values in buckets.values():
            if not isinstance(values, list):
                continue
            for assertion in values:
                if not isinstance(assertion, dict):
                    continue
                current = assertion_by_id.get(str(assertion.get("assertion_id") or ""))
                previous = assertion_by_id.get(str(assertion.get("supersedes_assertion_id") or ""))
                if current and previous:
                    graph.add_edge(
                        current,
                        previous,
                        relation="supersedes",
                        inverse_relation="superseded by",
                        normative=False,
                        profile="DerridAI",
                    )

    claim_map = {
        str(item.get("claim_id") or ""): item
        for item in claims or []
        if isinstance(item, dict) and item.get("claim_id")
    }
    claim_nodes: dict[str, str] = {}
    research_run_nodes: dict[str, str] = {}

    def ensure_claim(claim_id: str) -> str:
        if claim_id in claim_nodes:
            return claim_nodes[claim_id]
        claim = claim_map.get(claim_id) or {}
        node = graph.add_node(
            "GeneratedClaim",
            claim_id,
            label="Generated claim",
            summary=_present(claim.get("claim_text") or claim_id, limit=180),
            materialization="materialized" if claim else "reference",
            status=str(claim.get("validation_status") or "") or None,
            details={
                key: claim.get(key)
                for key in ("run_id", "response_record_id", "answer_start", "answer_end", "validation_status")
                if claim.get(key) is not None
            },
        )
        claim_nodes[claim_id] = node
        run_id = str(claim.get("run_id") or "").strip()
        if run_id:
            run_node = research_run_nodes.get(run_id)
            if not run_node:
                run_node = graph.add_node(
                    "ResearchRun",
                    run_id,
                    label=f"Research run {run_id}",
                    summary="Retained run reference from generated-claim provenance",
                    materialization="reference",
                )
                research_run_nodes[run_id] = run_node
            graph.add_edge(
                run_node,
                node,
                relation="contains generated claim",
                inverse_relation="generated in research run",
                normative=False,
                profile="DerridAI",
            )
        return node

    for binding in support_bindings or []:
        if not isinstance(binding, dict):
            continue
        binding_id = str(binding.get("support_binding_id") or "").strip()
        claim_id = str(binding.get("claim_id") or "").strip()
        if not binding_id or not claim_id:
            continue
        claim_node = ensure_claim(claim_id)
        binding_node = graph.add_node(
            "SupportBinding",
            binding_id,
            label=f"Support binding {binding_id}",
            summary=str(binding.get("relation") or "support"),
            status=str(binding.get("validation_status") or "") or None,
            details={
                "relation": binding.get("relation"),
                "record_id": binding.get("record_id"),
                "record_revision": binding.get("record_revision"),
                "citation": binding.get("citation"),
            },
        )
        graph.add_edge(claim_node, binding_node)

        evidence_id = str(binding.get("evidence_ref_id") or "").strip() or f"binding:{binding_id}"
        evidence_node = graph.add_node(
            "EvidenceRef",
            evidence_id,
            label=f"Evidence reference {evidence_id}",
            summary=f"Record-backed evidence for {record_id}",
            materialization="materialized" if binding.get("evidence_ref_id") else "embedded",
            status=str(binding.get("validation_status") or "") or None,
            details={
                "locator_kind": "record",
                "record_id": binding.get("record_id") or record_id,
                "record_revision": binding.get("record_revision") or revision,
                "source_document_id": binding.get("source_document_id") or source_document_id,
            },
        )
        graph.add_edge(binding_node, evidence_node)

        binding_revision = int(binding.get("record_revision") or revision)
        if binding_revision == revision:
            graph.add_edge(
                evidence_node,
                revision_node,
                relation="locates revision",
                inverse_relation="referenced by evidence",
                normative=True,
                source_cardinality="1",
                target_cardinality="0..*",
                profile="Evidence",
            )
        else:
            historical = graph.add_node(
                "RecordRevision",
                f"{record_id}@{binding_revision}",
                label=f"Revision {binding_revision}",
                summary=f"Historical state of {record_id}",
                materialization="reference",
                status="stale" if binding.get("validation_status") == "stale" else None,
                details={"record_id": record_id, "record_revision": binding_revision},
            )
            graph.add_edge(root, historical)
            graph.add_edge(
                evidence_node,
                historical,
                relation="locates revision",
                inverse_relation="referenced by evidence",
                normative=True,
                source_cardinality="1",
                target_cardinality="0..*",
                profile="Evidence",
            )

        for span in binding.get("source_spans") or []:
            if not isinstance(span, dict):
                continue
            node = _add_span(
                graph,
                span,
                source_document_id=str(binding.get("source_document_id") or source_document_id),
                materialization="embedded",
            )
            if source_document_node:
                graph.add_edge(source_document_node, node)
            graph.add_edge(
                evidence_node,
                node,
                relation="locates source span",
                inverse_relation="referenced by evidence",
                normative=True,
                source_cardinality="0..*",
                target_cardinality="0..*",
                profile="Evidence",
            )

    return graph.payload(root)
