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

"""Research memory: advisory steering from prior responses and validated claims.

Two optional channels feed a new Research answer, each chosen by the researcher:

* **Prior responses** ("Use prior responses as guidance"). SQLite ``response_memory``
  is authoritative. A derived Chroma projection embeds each eligible response's
  *question*, so "What did Derrida say about hospitality?" can find a prior answer to
  "How does the notion of hospitality influence Derrida?". Only responses graded at or
  above ``settings.research_memory_min_grade`` are eligible; ungraded answers never
  steer. Self-graded answers stay eligible but are labelled as such.
* **Prior claim provenance** ("Use prior claim provenance as guidance"). Only
  reviewer-validated claims (see ``claim_memory``) are used, together with the
  citations their support bindings recorded. Each cited Record is checked against the
  current evidence packet so the generator is told whether that support can be cited
  in this answer at all.

Both channels are advisory. They never enter the evidence packet, never create
citations, and every hit is re-joined to its authoritative row before use. When the
embedding service is unavailable the channel falls back to lexical matching over
eligible rows and says so in the run's memory detail.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .claim_memory import ClaimMemoryIndex, derive_entry, similar_validated_claims
from .config import settings
from .metadata_exemplar_retrieval import (
    ChromaMetadataExemplarIndex,
    _bounded_query_text,
    _distance_similarity,
)
from .pipelines.memory import MemoryPipelinePlan, classify_memory_failure

COLLECTION_NAME = "derridai_response_memory"
PROJECTION = "response_memory"
PROJECTION_VERSION = 1
RESPONSE_LIMIT = 4
CLAIM_LIMIT = 6
MIN_SIMILARITY = 0.5
ANSWER_CHARS = 2400
_LEXICAL_POOL = 200


def grade_summary(entry: dict[str, Any]) -> dict[str, Any]:
    """Compact grade provenance from a response-cache grade-history entry."""
    result = entry.get("result") if isinstance(entry.get("result"), dict) else {}
    overall = result.get("overall")
    if isinstance(overall, dict):
        overall = overall.get("score")
    try:
        score = float(overall) if overall is not None else None
    except (TypeError, ValueError):
        score = None
    return {
        "overall": score,
        "grader_provider": entry.get("provider"),
        "grader_model": entry.get("model"),
        "generation_model": entry.get("generation_model"),
        "self_graded": bool(entry.get("same_model_as_generation")),
        "graded_at": entry.get("graded_at"),
    }


def ineligibility(row: dict[str, Any], min_grade: float | None = None) -> str:
    """Why a stored response may not steer new answers ("" when it may)."""
    if not str(row.get("question") or "").strip() or not str(row.get("answer") or "").strip():
        return "missing_text"
    grade = row.get("latest_grade") if isinstance(row.get("latest_grade"), dict) else {}
    score = grade.get("overall")
    if not isinstance(score, (int, float)):
        return "ungraded"
    threshold = settings.research_memory_min_grade if min_grade is None else min_grade
    return "" if float(score) >= float(threshold) else "below_grade_threshold"


def _projection(row: dict[str, Any]) -> dict[str, Any]:
    grade = row.get("latest_grade") or {}
    return {
        "response_id": str(row["response_id"]),
        # "" is the owner of shared rows, which every user may see.
        "owner": str(row.get("owner") or ""),
        "question": str(row.get("question") or ""),
        "grade_overall": float(grade.get("overall") or 0.0),
        "self_graded": bool(grade.get("self_graded")),
    }


class ResponseMemoryIndex(ChromaMetadataExemplarIndex):
    """Derived vector projection of eligible Research responses, keyed on the question."""

    SYSTEM_KIND = "response_memory"
    SCHEMA_KEY = "derridai_response_memory_schema"
    SCHEMA_VERSION = PROJECTION_VERSION
    DESCRIPTION = "Derived memory of graded Research responses."
    TEXT_FIELD = "question"
    FILTER_FIELDS = ["owner"]

    def __init__(self, store: Any | None = None) -> None:
        super().__init__(store, collection_name=COLLECTION_NAME)

    def _put(self, rows: list[dict[str, Any]]) -> None:
        if rows:
            self.store.upsert_many(
                self.collection_name,
                [_projection(row) for row in rows],
                document_field="question",
                id_field="response_id",
            )

    def _backfill_grade(self, system_store: Any, row: dict[str, Any]) -> dict[str, Any]:
        """Copy a grade recorded only in the response cache into the durable row.

        Responses graded before grades were stored in SQLite have their grade only in
        the ``_response_cache`` projection; without this they would look ungraded.
        """
        if isinstance(row.get("latest_grade"), dict):
            return row
        try:
            cached = self.store.get_record("_response_cache", str(row.get("response_id") or ""))
        except Exception:  # noqa: BLE001 - a missing cache row just means "ungraded"
            return row
        entry = (cached or {}).get("latest_grade")
        if isinstance(entry, dict):
            summary = grade_summary(entry)
            if system_store.record_response_memory_grade(str(row["response_id"]), summary):
                row = {**row, "latest_grade": summary}
        return row

    def rebuild(self, system_store: Any) -> int:
        collection = self._ensure()
        existing = [str(value) for value in (collection.get(include=[]).get("ids") or [])]
        if existing:
            collection.delete(ids=existing)
        rows = [
            row
            for row in (self._backfill_grade(system_store, row) for row in system_store.list_response_memory(limit=1000))
            if not ineligibility(row)
        ]
        self._put(rows)
        return len(rows)

    def sync(self, system_store: Any) -> dict[str, int]:  # type: ignore[override]
        """Apply the outbox: mirror changed responses, or rebuild when the projection is new."""
        collection = self._ensure()
        dirty = system_store.list_semantic_memory_dirty(PROJECTION, limit=1000)
        if int(collection.count()) == 0 or any(not item.get("record_id") for item in dirty):
            count = self.rebuild(system_store)
            system_store.complete_semantic_memory_dirty([item["item_id"] for item in dirty])
            return {"rebuilt": count, "upserted": 0, "removed": 0}
        upserted = removed = 0
        for item in dirty:
            row = system_store.get_response_memory(str(item["record_id"]))
            if row and not ineligibility(row):
                self._put([row])
                upserted += 1
            else:
                collection.delete(ids=[str(item["record_id"])])
                removed += 1
        system_store.complete_semantic_memory_dirty([item["item_id"] for item in dirty])
        return {"rebuilt": 0, "upserted": upserted, "removed": removed}

    def similar(self, question: str, *, owner: str | None, limit: int, min_similarity: float) -> list[dict[str, Any]]:
        """Raw projection hits; callers must re-join them to authoritative rows."""
        text = _bounded_query_text(str(question or ""))
        collection = self._ensure()
        count = int(collection.count())
        if not text.strip() or not count:
            return []
        provider, model = self.store._embedding_spec(collection)
        vector = self.store.embeddings.embed_query(text, provider=provider, model=model)
        payload = collection.query(
            query_embeddings=[vector],
            n_results=min(count, max(1, int(limit)) * 2),
            where={"owner": {"$in": [str(owner), ""]}} if owner is not None else None,
            include=["distances"],
        )
        ids = (payload.get("ids") or [[]])[0]
        distances = (payload.get("distances") or [[]])[0]
        hits = []
        for index, response_id in enumerate(ids):
            similarity = _distance_similarity(distances[index] if index < len(distances) else None)
            if similarity >= min_similarity:
                hits.append({"response_id": str(response_id), "similarity": round(similarity, 4)})
        return hits


def _words(text: str) -> set[str]:
    return {word.casefold() for word in re.findall(r"\w{4,}", str(text or ""))}


def _lexical(query: str, rows: list[dict[str, Any]], key: str, limit: int) -> list[tuple[dict[str, Any], float]]:
    words = _words(query)
    if not words:
        return []
    scored = []
    for row in rows:
        overlap = len(words & _words(row.get(key) or ""))
        if overlap:
            scored.append((row, round(overlap / len(words), 4)))
    return sorted(scored, key=lambda item: item[1], reverse=True)[:limit]


def select_prior_responses(
    query: str,
    *,
    owner: str | None,
    system_store: Any,
    index_factory: Callable[[], ResponseMemoryIndex],
    limit: int = RESPONSE_LIMIT,
    plan: MemoryPipelinePlan | None = None,
) -> dict[str, Any]:
    """Eligible prior responses similar to the query, re-joined to authority."""

    warnings: list[str] = []
    observations: dict[str, dict[str, Any]] = {}
    selection_limit = max(1, int(plan.selection_limit if plan is not None else limit))
    semantic_limit = max(1, int(plan.fetch_k if plan is not None else limit))
    minimum = float(plan.min_similarity if plan is not None else MIN_SIMILARITY)
    fallback_limit = max(
        1,
        int(plan.fallback_fetch_k if plan is not None else limit),
    )
    retrieve_stage = plan.retrieve_stage_id if plan is not None else "retrieve"
    select_stage = plan.select_stage_id if plan is not None else "select"

    semantic_started = time.perf_counter()
    try:
        index = index_factory()
        index.sync(system_store)
        pairs = []
        for hit in index.similar(
            query,
            owner=owner,
            limit=semantic_limit,
            min_similarity=minimum,
        ):
            row = system_store.get_response_memory(hit["response_id"], owner=owner)
            if row and not ineligibility(row):
                pairs.append((row, hit["similarity"]))
        observations[retrieve_stage] = {
            "status": "completed",
            "elapsed_seconds": time.perf_counter() - semantic_started,
            "input_count": 1,
            "output_count": len(pairs),
            "parameters": {
                "fetch_k": semantic_limit,
                "min_similarity": minimum,
            },
        }
        mode = "semantic"
    except Exception as exc:  # noqa: BLE001 - advisory memory must degrade visibly
        failure_kind = classify_memory_failure(exc)
        status = {
            "timeout": "timed_out",
            "unavailable": "unavailable",
            "error": "failed",
        }[failure_kind]
        observations[retrieve_stage] = {
            "status": status,
            "elapsed_seconds": time.perf_counter() - semantic_started,
            "input_count": 1,
            "output_count": 0,
            "parameters": {
                "fetch_k": semantic_limit,
                "min_similarity": minimum,
            },
            "fallback_reason": str(exc)[:300],
        }
        fallback_target = (
            plan.fallback_for(failure_kind)
            if plan is not None
            else "legacy_lexical_fallback"
        )
        configured_fallback = (
            plan is None
            or (
                plan.lexical_fallback_stage_id is not None
                and fallback_target == plan.lexical_fallback_stage_id
            )
        )
        if configured_fallback:
            fallback_started = time.perf_counter()
            warnings.append(
                "Semantic response memory unavailable; used configured lexical "
                f"matching instead: {str(exc)[:200]}"
            )
            pool = [
                row
                for row in system_store.list_response_memory(
                    owner=owner,
                    limit=_LEXICAL_POOL,
                )
                if not ineligibility(row)
            ]
            pairs = _lexical(query, pool, "question", fallback_limit)
            if plan is not None and plan.lexical_fallback_stage_id is not None:
                observations[plan.lexical_fallback_stage_id] = {
                    "status": "completed",
                    "elapsed_seconds": time.perf_counter() - fallback_started,
                    "input_count": len(pool),
                    "output_count": len(pairs),
                    "parameters": {"fetch_k": fallback_limit},
                }
            mode = "lexical_fallback"
        else:
            warnings.append(
                "Semantic response memory failed and this pipeline has no configured "
                f"{failure_kind} fallback: {str(exc)[:200]}"
            )
            pairs = []
            mode = f"semantic_{failure_kind}"

    items = [
        {
            "response_id": str(row.get("response_id") or ""),
            "question": str(row.get("question") or ""),
            "answer": str(row.get("answer") or ""),
            "similarity": similarity,
            "grade": row.get("latest_grade") or {},
        }
        for row, similarity in pairs[:selection_limit]
    ]
    observations[select_stage] = {
        "status": "completed",
        "input_count": len(pairs),
        "output_count": len(items),
        "parameters": {"limit": selection_limit},
    }
    return {
        "mode": mode,
        "items": items,
        "warnings": warnings,
        "observations": observations,
    }

def _evidence_records(evidence: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in evidence or []:
        record = item.get("record") if isinstance(item.get("record"), dict) else {}
        record_id = str(record.get("record_id") or "")
        if record_id and record_id not in out:
            out[record_id] = {"evidence_id": item.get("evidence_id"), "record_revision": record.get("record_revision")}
    return out


def _support_status(support: dict[str, Any], in_evidence: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Where a validated claim's cited Record stands relative to this run's evidence."""
    current = in_evidence.get(str(support.get("record_id") or ""))
    if current is None:
        return {**support, "evidence_id": None, "status": "not_in_current_evidence"}
    bound, now = support.get("record_revision"), current.get("record_revision")
    revised = bound is not None and now is not None and int(bound) != int(now)
    return {
        **support,
        "evidence_id": current.get("evidence_id"),
        "status": "revised_since_validation" if revised else "in_current_evidence",
    }


def select_prior_claims(
    query: str,
    *,
    owner: str | None,
    evidence: Sequence[Mapping[str, Any]],
    system_store: Any,
    index_factory: Callable[[], ClaimMemoryIndex],
    limit: int = CLAIM_LIMIT,
    plan: MemoryPipelinePlan | None = None,
) -> dict[str, Any]:
    """Validated claims similar to the query with support checked against evidence."""

    warnings: list[str] = []
    observations: dict[str, dict[str, Any]] = {}
    selection_limit = max(1, int(plan.selection_limit if plan is not None else limit))
    semantic_limit = max(1, int(plan.fetch_k if plan is not None else limit))
    minimum = float(plan.min_similarity if plan is not None else MIN_SIMILARITY)
    fallback_limit = max(
        1,
        int(plan.fallback_fetch_k if plan is not None else limit),
    )
    retrieve_stage = plan.retrieve_stage_id if plan is not None else "retrieve"
    select_stage = plan.select_stage_id if plan is not None else "select"

    semantic_started = time.perf_counter()
    try:
        index = index_factory()
        index.ensure_current(system_store)
        found = similar_validated_claims(
            index,
            system_store,
            {"claim_id": "", "claim_text": query},
            owner=owner,
            limit=semantic_limit,
            min_similarity=minimum,
        )["items"]
        observations[retrieve_stage] = {
            "status": "completed",
            "elapsed_seconds": time.perf_counter() - semantic_started,
            "input_count": 1,
            "output_count": len(found),
            "parameters": {
                "fetch_k": semantic_limit,
                "min_similarity": minimum,
            },
        }
        mode = "semantic"
    except Exception as exc:  # noqa: BLE001 - advisory memory must degrade visibly
        failure_kind = classify_memory_failure(exc)
        status = {
            "timeout": "timed_out",
            "unavailable": "unavailable",
            "error": "failed",
        }[failure_kind]
        observations[retrieve_stage] = {
            "status": status,
            "elapsed_seconds": time.perf_counter() - semantic_started,
            "input_count": 1,
            "output_count": 0,
            "parameters": {
                "fetch_k": semantic_limit,
                "min_similarity": minimum,
            },
            "fallback_reason": str(exc)[:300],
        }
        fallback_target = (
            plan.fallback_for(failure_kind)
            if plan is not None
            else "legacy_lexical_fallback"
        )
        configured_fallback = (
            plan is None
            or (
                plan.lexical_fallback_stage_id is not None
                and fallback_target == plan.lexical_fallback_stage_id
            )
        )
        if configured_fallback:
            fallback_started = time.perf_counter()
            warnings.append(
                "Semantic claim memory unavailable; used configured lexical "
                f"matching instead: {str(exc)[:200]}"
            )
            pool = system_store.list_generated_claims(
                owner=owner,
                validation_status="validated",
                limit=_LEXICAL_POOL,
            )
            found = []
            for claim, similarity in _lexical(
                query,
                pool,
                "claim_text",
                fallback_limit,
            ):
                entry = derive_entry(
                    claim,
                    system_store.list_claim_support_bindings(
                        str(claim.get("claim_id") or ""),
                        owner=owner,
                    ),
                )
                if entry is not None:
                    found.append(
                        {**entry, "similarity": similarity, "advisory": True}
                    )
            if plan is not None and plan.lexical_fallback_stage_id is not None:
                observations[plan.lexical_fallback_stage_id] = {
                    "status": "completed",
                    "elapsed_seconds": time.perf_counter() - fallback_started,
                    "input_count": len(pool),
                    "output_count": len(found),
                    "parameters": {"fetch_k": fallback_limit},
                }
            mode = "lexical_fallback"
        else:
            warnings.append(
                "Semantic claim memory failed and this pipeline has no configured "
                f"{failure_kind} fallback: {str(exc)[:200]}"
            )
            found = []
            mode = f"semantic_{failure_kind}"

    in_evidence = _evidence_records(evidence)
    items = [
        {
            **item,
            "support": [
                _support_status(support, in_evidence)
                for support in item.get("support") or []
            ],
        }
        for item in found[:selection_limit]
    ]
    observations[select_stage] = {
        "status": "completed",
        "input_count": len(found),
        "output_count": len(items),
        "parameters": {"limit": selection_limit},
    }
    return {
        "mode": mode,
        "items": items,
        "warnings": warnings,
        "observations": observations,
    }

def _grade_label(grade: dict[str, Any]) -> str:
    score = grade.get("overall")
    label = f"graded {score:g}/10" if isinstance(score, (int, float)) else "ungraded"
    if grade.get("grader_model"):
        label += f" by {grade['grader_model']}"
    if grade.get("self_graded"):
        label += "; self-graded by the generating model"
    return label


_SUPPORT_NOTES = {
    "in_current_evidence": "cited Record is in current EVIDENCE as [{evidence_id}]",
    "revised_since_validation": "cited Record is in current EVIDENCE as [{evidence_id}] but was revised after validation; re-check it",
    "not_in_current_evidence": "cited Record is not in current EVIDENCE; this support cannot be cited in this answer",
}


def render_responses(items: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"[prior-response:{item['response_id']}] ({_grade_label(item['grade'])}; similarity {item['similarity']:g})\n"
        f"Question: {item['question'].strip()}\n"
        f"Advisory answer: {item['answer'].strip()[:ANSWER_CHARS]}"
        for item in items
    )


def render_claims(items: list[dict[str, Any]]) -> str:
    blocks = []
    for item in items:
        lines = [f"[prior-claim:{item['claim_id']}] (reviewer-validated) {str(item.get('claim_text') or '').strip()}"]
        for support in item.get("support") or []:
            citation = (support.get("citation") or {}).get("inline") or support.get("record_id")
            note = _SUPPORT_NOTES[support["status"]].format(evidence_id=support.get("evidence_id"))
            lines.append(f"  - {support.get('relation') or 'supports'}: {citation} - {note}")
        blocks.append("\n".join(lines))
    return "\n".join(blocks)


def _resolve_memory_runtime(
    feature: str,
    *,
    resolver: Callable[[str], dict[str, Any]] | None = None,
) -> tuple[MemoryPipelinePlan | None, dict[str, Any], list[str]]:
    """Resolve one advisory-memory assignment without making memory mandatory."""

    try:
        if resolver is None:
            from .pipelines.manager import pipeline_manager

            resolver = pipeline_manager.resolve
        from .pipelines.memory import compile_memory_pipeline
        from .pipelines.models import PipelineDefinition

        resolved = resolver(feature)
        pipeline = PipelineDefinition.model_validate(resolved["pipeline"])
        plan = compile_memory_pipeline(pipeline)
        return (
            plan,
            {
                "pipeline_id": pipeline.pipeline_id,
                "pipeline_version": pipeline.version,
                "pipeline_hash": resolved.get("pipeline_hash"),
            },
            [],
        )
    except Exception as exc:  # noqa: BLE001 - advisory memory may be skipped
        return (
            None,
            {},
            [
                f"{feature} pipeline could not be resolved; that advisory memory "
                f"channel was skipped ({type(exc).__name__}: {str(exc)[:200]})."
            ],
        )


def memory_guidance(
    query: str,
    *,
    use_responses: bool,
    use_claims: bool,
    owner: str | None,
    evidence: Sequence[Mapping[str, Any]],
    system_store: Any,
    response_index_factory: Callable[[], ResponseMemoryIndex],
    claim_index_factory: Callable[[], ClaimMemoryIndex],
    pipeline_resolver: Callable[[str], dict[str, Any]] | None = None,
    excluded_response_ids: Sequence[str] = (),
) -> tuple[str, str, dict[str, Any]]:
    """Prompt blocks for selected memory channels plus a reproducibility record."""

    off: dict[str, Any] = {
        "mode": "off",
        "items": [],
        "warnings": [],
        "observations": {},
    }
    response_plan = claim_plan = None
    response_pipeline: dict[str, Any] = {}
    claim_pipeline: dict[str, Any] = {}
    resolution_warnings: list[str] = []

    if use_responses:
        response_plan, response_pipeline, warnings = _resolve_memory_runtime(
            "response_memory",
            resolver=pipeline_resolver,
        )
        resolution_warnings.extend(warnings)
    if use_claims:
        claim_plan, claim_pipeline, warnings = _resolve_memory_runtime(
            "claim_memory",
            resolver=pipeline_resolver,
        )
        resolution_warnings.extend(warnings)

    responses: dict[str, Any]
    if use_responses and response_plan is not None:
        responses = select_prior_responses(
            query,
            owner=owner,
            system_store=system_store,
            index_factory=response_index_factory,
            plan=response_plan,
        )
    elif use_responses:
        responses = {
            **off,
            "mode": "pipeline_unavailable",
            "warnings": list(resolution_warnings),
        }
    else:
        responses = off

    claims: dict[str, Any]
    if use_claims and claim_plan is not None:
        claims = select_prior_claims(
            query,
            owner=owner,
            evidence=evidence,
            system_store=system_store,
            index_factory=claim_index_factory,
            plan=claim_plan,
        )
    elif use_claims:
        claims = {
            **off,
            "mode": "pipeline_unavailable",
            "warnings": list(resolution_warnings),
        }
    else:
        claims = off

    excluded = set(excluded_response_ids)
    responses["items"] = [item for item in responses["items"] if item["response_id"] not in excluded]
    detail = {
        "owner_scope": owner,
        "thread_response_ids_excluded": list(excluded_response_ids),
        # Response eligibility remains an application quality rule, not a tunable
        # retrieval-pipeline parameter.
        "min_grade": settings.research_memory_min_grade,
        "response_pipeline": response_pipeline or None,
        "claim_pipeline": claim_pipeline or None,
        "response_mode": responses["mode"],
        "claim_mode": claims["mode"],
        "response_count": len(responses["items"]),
        "claim_count": len(claims["items"]),
        "response_ids": [item["response_id"] for item in responses["items"]],
        "claim_ids": [item["claim_id"] for item in claims["items"]],
        "responses": [
            {
                "response_id": item["response_id"],
                "similarity": item["similarity"],
                "grade": item["grade"],
            }
            for item in responses["items"]
        ],
        "claims": [
            {
                "claim_id": item["claim_id"],
                "similarity": item.get("similarity"),
                "support": [
                    {
                        key: support.get(key)
                        for key in (
                            "record_id",
                            "record_revision",
                            "evidence_id",
                            "status",
                        )
                    }
                    for support in item.get("support") or []
                ],
            }
            for item in claims["items"]
        ],
        "response_pipeline_observations": responses.get("observations") or {},
        "claim_pipeline_observations": claims.get("observations") or {},
        "warnings": list(
            dict.fromkeys(
                resolution_warnings
                + responses["warnings"]
                + claims["warnings"]
            )
        ),
    }
    return (
        render_responses(responses["items"]),
        render_claims(claims["items"]),
        json.loads(json.dumps(detail, default=str)),
    )

