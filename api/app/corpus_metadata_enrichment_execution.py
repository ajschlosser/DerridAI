# Copyright 2026 Aaron John Schlosser, PhD.
"""Metadata-enrichment execution: per-record prompting, task scheduling, and result reconciliation.

Moved verbatim out of PdfCorpusBuildManager as a mixin (see corpus_review_actions.py's
module docstring for why a mixin, not free functions, and corpus_build_lifecycle.py's for
why every mixin's mypy stub block must be wrapped in `if TYPE_CHECKING:`).
"""

from __future__ import annotations

import json
import re
import time
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from . import experiment
from .autofill import decide as decide_autofill
from .autofill import in_audit_sample
from .config import APP_VERSION
from .corpus_llm_helpers import _context_window, _stage_limits, _stage_timeouts
from .corpus_metadata import (
    DISCOURSE_ROLES,
    PROPOSITION_STATUS_VALUES,
    REGION_TYPES,
    REVIEW_METADATA_FIELDS,
    SOURCE_BOUND_FIELDS,
    STANCE_VALUES,
    STRONG_STRUCTURAL_METHODS,
    _normalize_semantic_value,
    apply_metadata_constraints,
)
from .corpus_models import CORPUS_PROFILES, PROFILE_VERSION
from .corpus_record_quality import _metadata_source_quality_gate, iso_now
from .corpus_review_state import _sync_record_metadata_state
from .corpus_reviewer_helpers import (
    _allowed_for,
    _scrub_canonical_transport,
    _scrub_sealed_field,
)
from .corpus_segmentation import _apply_manifest_metadata
from .enrichment_ledger import (
    AUTOFILLED,
    CALL,
    PROPOSED,
)
from .field_assertions import current_assertion_by_name, migrate_record_assertions
from .metadata_adjudication_cache import suggestions as adjudication_suggestions
from .metadata_schema import (
    CORE_FIELDS,
    CORE_GROUP,
    MetadataSchema,
    build_group_prompt,
    default_schema,
    response_model_for,
)
from .rag import _citation_strings
from .run_guidance import find_guidance_matches, format_group_guidance


class MetadataEnrichmentExecutionMixin:
    """Mixin members declared here exist on PdfCorpusBuildManager, not on this mixin itself.

    See corpus_review_actions.py's identical block for the full explanation, including why
    everything below is wrapped in `if TYPE_CHECKING:`.
    """

    if TYPE_CHECKING:
        repo: Any
        _ledger: Any

        def _adaptive_family_should_skip(self, build_id: str | None, family: str, request: dict[str, Any]) -> tuple[bool, str]: ...
        def _append_warning(self, build_id: str, message: str) -> None: ...
        def _chat_json(self, request: dict[str, Any], prompt: str, *, response_model: type[BaseModel], max_tokens: int = ..., schema_name: str = ..., attempts: int = ..., build_id: str = ...) -> dict[str, Any]: ...
        def _editorial_memory(self, build_id: str, current_record: dict[str, Any] | None = None, *, exclude_record_id: str = "", use_global: bool = True, use_progressive: bool = True) -> dict[str, Any]: ...
        def _increment_metric(self, build_id: str, key: str, amount: int = 1) -> None: ...
        def _latest_runtime_request(self, build_id: str, fallback: dict[str, Any]) -> dict[str, Any]: ...
        def _note_suspension(self, model: str, field: str, suspended: bool, reviews: int, accepted: int, build_id: str, run_id: str) -> None: ...
        def _record_family_effectiveness(self, build_id: str | None, family: str, result: dict[str, Any] | None, *, elapsed_ms: int = 0, provider_profile_id: str = "", provider: str = "", model: str = "") -> None: ...
        def _schema_for(self, build_id: str) -> MetadataSchema: ...
        def touchup_record_text(self, build_id: str, record_id: str, request: dict[str, Any], instructions: str = "", text_override: str | None = None) -> dict[str, Any]: ...

    def _enrich_record(
        self,
        record: dict[str, Any],
        manifest: dict[str, Any],
        request: dict[str, Any],
        *,
        previous_text: str = "",
        next_text: str = "",
        build_id: str = "",
        stage_callback: Callable[[dict[str, Any], str, str, str | None], None] | None = None,
    ) -> dict[str, Any]:
        """Infer interpretive metadata through several small structured tasks.

        A single all-fields JSON object proved fragile with local models: one
        truncated brace could invalidate every metadata dimension.  The staged
        design keeps output schemas small, preserves successful partial work, and
        makes retries/escalation local to the failed metadata family.
        """
        profile_id = PROFILE_VERSION
        if build_id:
            try:
                current_build = self.repo.get_build(build_id)
            except Exception as exc:
                raise RuntimeError(
                    f"Could not refresh corpus build state before metadata enrichment: {exc}"
                ) from exc
            current_manifest = current_build.get("manifest")
            if isinstance(current_manifest, dict) and current_manifest:
                manifest = current_manifest
            profile_id = str(current_build.get("profile_id") or PROFILE_VERSION)
            if not bool(request.get("_interactive_provider_override")):
                # The runtime request carries the provider; the run's own identity and experiment switches stay.
                kept: dict[str, Any] = {key: request[key] for key in ("run_id", "arms", "arm_salt", "ablations", "arm", "model_version") if key in request}
                request = {**self._latest_runtime_request(build_id, request), **kept}
        request = experiment.with_arm(request, str(record.get("record_id") or ""))
        off = experiment.disabled(request)
        _apply_manifest_metadata(record, manifest)
        apply_metadata_constraints(record, schema)
        editorial_memory = self._editorial_memory(
            build_id,
            record,
            exclude_record_id=str(record.get("record_id") or ""),
            use_global="cross_build_learning" not in off,
            use_progressive=(
                "progressive_metadata_rag" not in off
                and "reviewer_conventions" not in off
            ),
        ) if build_id else {"conventions": {}, "examples": {}}
        if "reviewer_conventions" in off:
            editorial_memory = {**editorial_memory, "conventions": {}, "examples": {}}
        if "rejection_memory" in off:
            editorial_memory = {**editorial_memory, "pass_learning": None}
        editorial_context = editorial_memory.get("conventions", {}) if isinstance(editorial_memory, dict) else {}
        editorial_examples = editorial_memory.get("examples", {}) if isinstance(editorial_memory, dict) else {}
        example_count = sum(
            len(values)
            for values in editorial_examples.values()
            if isinstance(values, list)
        )
        example_token_estimate = int(
            editorial_memory.get("example_token_estimate") or 0
        ) if isinstance(editorial_memory, dict) else 0
        progressive_retrieval = (
            editorial_memory.get("progressive_retrieval")
            if isinstance(editorial_memory, dict)
            and isinstance(editorial_memory.get("progressive_retrieval"), dict)
            else {}
        )
        record["editorial_memory_used"] = {
            "convention_fields": sorted(editorial_context.keys()),
            "example_record_ids": sorted({str(item.get("record_id") or "") for values in editorial_examples.values() if isinstance(values, list) for item in values if isinstance(item, dict) and item.get("record_id")}),
            "example_exemplar_ids": sorted({str(item.get("exemplar_id") or "") for values in editorial_examples.values() if isinstance(values, list) for item in values if isinstance(item, dict) and item.get("exemplar_id")}),
            "example_count": example_count,
            "packet_token_estimate": example_token_estimate,
            "progressive_retrieval": {
                key: progressive_retrieval[key]
                for key in (
                    "query_ms",
                    "search_ms",
                    "select_ms",
                    "sync_ms",
                    "total_ms",
                    "examples_considered",
                    "examples_used",
                    "packet_chars",
                    "fields_served",
                    "fallback_reason",
                )
                if key in progressive_retrieval
            },
        }
        if build_id and progressive_retrieval:
            numeric_metrics = {
                "metadata_rag_query_ms": progressive_retrieval.get("query_ms"),
                "metadata_rag_search_ms": progressive_retrieval.get("search_ms"),
                "metadata_rag_select_ms": progressive_retrieval.get("select_ms"),
                "metadata_rag_sync_ms": progressive_retrieval.get("sync_ms"),
                "metadata_rag_total_ms": progressive_retrieval.get("total_ms"),
                "metadata_rag_examples_considered": progressive_retrieval.get("examples_considered"),
            }
            for metric, value in numeric_metrics.items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    self._increment_metric(build_id, metric, int(value))
            fields_served = progressive_retrieval.get("fields_served")
            if isinstance(fields_served, list):
                self._increment_metric(build_id, "metadata_rag_fields_served", len(fields_served))
            if progressive_retrieval.get("fallback_reason"):
                self._increment_metric(build_id, "metadata_rag_fallbacks", 1)
        if build_id and example_count:
            self._increment_metric(build_id, "editorial_examples_used", example_count)
            self._increment_metric(build_id, "metadata_rag_examples_used", example_count)
            self._increment_metric(
                build_id,
                "metadata_rag_packet_tokens",
                example_token_estimate,
            )
        schema = self._schema_for(build_id)
        profile = {**CORPUS_PROFILES.get(profile_id, CORPUS_PROFILES[PROFILE_VERSION]), "review_metadata_fields": schema.review_fields()}
        required_metadata_fields = list(profile.get("required_metadata_fields") or [])
        if bool(request.get("llm_touchup_during_enrichment")) and "__text__" not in set(record.get("human_touched_fields") or []):
            current_text = str(record.get("text") or "")
            if current_text.strip():
                try:
                    proposal = self.touchup_record_text(
                        build_id, str(record.get("record_id") or ""), request,
                        text_override=current_text,
                    )
                    record["text_touchup_proposal"] = {
                        "proposal_id": f"touchup-{uuid.uuid4().hex[:12]}",
                        "run_id": str(request.get("run_id") or f"touchup-run-{uuid.uuid4().hex[:12]}"),
                        "status": "pending_review",
                        "source_text": proposal["source_text"],
                        "proposed_text": proposal["proposed_text"],
                        "changes": proposal["changes"],
                        "warnings": proposal["warnings"],
                        "provider": proposal["provider"],
                        "model": proposal["model"],
                        "created_at": iso_now(),
                    }
                    record["needs_review"] = True
                    record["metadata_needs_attention"] = True
                    reasons = list(record.get("metadata_attention_reasons") or [])
                    reasons.append("An LLM text touch-up proposal is available for review; reviewed text remains unchanged until approved.")
                    record["metadata_attention_reasons"] = list(dict.fromkeys(reasons))[-50:]
                except InterruptedError:
                    raise
                except Exception as exc:
                    record["text_touchup_proposal"] = {
                        "proposal_id": f"touchup-{uuid.uuid4().hex[:12]}",
                        "run_id": str(request.get("run_id") or f"touchup-run-{uuid.uuid4().hex[:12]}"),
                        "status": "failed",
                        "warnings": [f"LLM text touch-up failed: {exc}"],
                        "created_at": iso_now(),
                    }
                    self._append_warning(build_id, f"{record.get('record_id')}: LLM text touch-up failed; metadata enrichment continued.")
        if _metadata_source_quality_gate(record, required_metadata_fields, stage_callback, schema=schema):
            return migrate_record_assertions(record, schema)
        tasks, source_ids, obvious_apparatus = self._prepare_metadata_tasks(
            record, manifest, request, profile, editorial_context, editorial_examples,
            previous_text, next_text, stage_callback,
            pass_learning=editorial_memory.get("pass_learning") if isinstance(editorial_memory, dict) else None,
            schema=schema,
        )
        stage_results = self._execute_metadata_tasks(record, request, tasks, build_id, stage_callback)
        return self._reconcile_metadata_results(record, profile, source_ids, stage_results, obvious_apparatus, request=request, build_id=build_id, schema=schema)


    def _prepare_metadata_tasks(
        self, record: dict[str, Any], manifest: dict[str, Any], request: dict[str, Any],
        profile: dict[str, Any], editorial_context: dict[str, Any], editorial_examples: dict[str, Any],
        previous_text: str, next_text: str,
        stage_callback: Callable[[dict[str, Any], str, str, str | None], None] | None,
        *, pass_learning: dict[str, Any] | None = None, schema: MetadataSchema | None = None,
    ) -> tuple[list[tuple[str, str, type[BaseModel], int, str]], list[str], bool]:
        """Bound source context and select structured tasks without invoking a provider."""
        schema = schema or default_schema()
        allowed_region_types = list(profile.get("region_types") or REGION_TYPES)
        allowed_discourse_roles = list(profile.get("discourse_roles") or DISCOURSE_ROLES)
        limits = _stage_limits(request)
        neighbor_context = {
            "previous_record_tail": previous_text[-1800:] if previous_text else "",
            "next_record_head": next_text[:1800] if next_text else "",
        }
        source_ids = [str(value) for value in record.get("source_block_ids") or []]
        source_id_json = json.dumps(source_ids, ensure_ascii=False)
        # Semantic records should already be bounded. This is a context-safety
        # guard, not a segmentation rule: no source text is rewritten or split here.
        source_text = str(record.get("text") or "")
        context = _context_window(request)
        largest_metadata_output = max(limits["discourse_num_predict"], limits["quotation_num_predict"], limits["indexing_num_predict"])
        metadata_input_tokens = 9000 if not context else max(1800, min(12000, context - largest_metadata_output - 1800))
        metadata_char_budget = max(7000, metadata_input_tokens * 4)
        if len(source_text) > metadata_char_budget:
            half = max(2500, metadata_char_budget // 2)
            source_text = source_text[:half] + "\n\n[...middle retained in source record but omitted from this metadata prompt...]\n\n" + source_text[-half:]
            record["needs_review"] = True
            record["review_reason"] = "Record exceeds this model's metadata context envelope; metadata was inferred from head/tail context and requires review."

        migrate_record_assertions(record, schema)
        cached_prefills: dict[str, Any] = {}
        for field in schema.fields:
            cached = adjudication_suggestions(
                record_id=str(record.get("record_id") or ""),
                text=source_text,
                field=field.name,
                cardinality="list" if field.type == "list" else "single",
                schema_version=str(schema.schema_version or ""),
            )
            if isinstance(cached, dict) and cached.get("latest_value") not in (None, "", []):
                cached_prefills[field.name] = cached["latest_value"]
                record[field.name] = cached["latest_value"]
        if cached_prefills:
            record["metadata_adjudication_prefills"] = cached_prefills
        human_locked_fields = sorted(
            field.name
            for field in schema.fields
            if (
                (assertion := current_assertion_by_name(record, field.name)) is not None
                and assertion.authority_status in {"human_confirmed", "human_override"}
            )
        )
        def base_context_for(group_fields: list[str]) -> str:
            # Each LLM family receives only precedents for fields it can actually
            # return. This preserves the global exemplar budget while avoiding
            # repeated prompt-prefill cost from unrelated metadata families.
            relevant_examples = {
                field: editorial_examples[field]
                for field in group_fields
                if field in editorial_examples
                and isinstance(editorial_examples.get(field), list)
                and editorial_examples[field]
            }
            return f"""Document manifest: {json.dumps(manifest, ensure_ascii=False)}
Build-local editorial conventions confirmed on at least two other records (advisory context only; do not copy unless supported here): {json.dumps(editorial_context, ensure_ascii=False)}
Relevant human-confirmed examples for fields in THIS metadata family (few-shot guidance only; source evidence in THIS record remains authoritative): {json.dumps(relevant_examples, ensure_ascii=False)}
If a retrieved example has kind="correction", its value is the human-supported classification and rejected_value is a known prior model mistake. Treat rejected_value as a negative precedent only; never copy or prefer it because it appears in the example.
How earlier enrichment in this build went (advisory only; evidence in THIS record remains authoritative). Includes reviewer accepted/rejected counts when present, plus values the previous pass inferred on two or more other records (working conventions, not confirmed). Do not copy these; use them only when THIS record's evidence supports the same reading: {json.dumps(pass_learning or {}, ensure_ascii=False)}
Human-owned fields on this record (authoritative; DO NOT propose replacements): {json.dumps({field: record.get(field) for field in human_locked_fields}, ensure_ascii=False)}
Neighbor context (context only; never cite it as evidence): {json.dumps(neighbor_context, ensure_ascii=False)}
Current source block IDs: {source_id_json}
CURRENT REVIEWED RECORD TEXT:
{source_text}
"""

        enrichment_mode = str(request.get("enrichment_mode") if "enrichment_mode" in request else "deep")
        semantic_indexing = bool(request.get("semantic_indexing")) or enrichment_mode == "deep"
        region_type = str(record.get("region_type") or "")
        obvious_apparatus = region_type in {"bibliography", "index", "copyright", "front_matter", "back_matter"} or record.get("primary_text") is False
        quote_signal = any(token in source_text for token in ('“', '”', '"', '«', '»', '‘', '’')) or bool(re.search(r"\b(?:quotes?|writes?|says?|according to|cites?)\b", source_text, re.I))
        # One task per group of the build's schema: the prompt is assembled from the schema and the answer's shape is generated from it.
        all_task_specs: dict[str, tuple[str, str, type[BaseModel], int, str]] = {}
        run_guidance = request.get("run_guidance") if isinstance(request.get("run_guidance"), dict) else {}
        guidance_matches = record.get("metadata_guidance_matches")
        if not isinstance(guidance_matches, dict):
            guidance_matches = find_guidance_matches(source_text, run_guidance)
        for group in schema.groups:
            group_fields = [field.name for field in schema.fields_in(group.key)]
            if group.key == CORE_GROUP:
                group_fields = [*CORE_FIELDS, *group_fields]
            prompt = build_group_prompt(
                schema,
                group.key,
                base_context=base_context_for(group_fields),
                allowed_region_types=allowed_region_types,
                allowed_discourse_roles=allowed_discourse_roles,
            )
            guidance_prompt = format_group_guidance(group_fields, run_guidance, guidance_matches)
            if guidance_prompt:
                prompt = prompt + "\n\n" + guidance_prompt
            remembered: dict[str, Any] = {}
            for field in schema.fields_in(group.key):
                cached = adjudication_suggestions(
                    record_id=str(record.get("record_id") or ""),
                    text=source_text,
                    field=field.name,
                    cardinality="list" if field.type == "list" else "single",
                    schema_version=str(request.get("schema_version") or ""),
                )
                values = cached.get("prior_values") if isinstance(cached, dict) else None
                if isinstance(values, list) and values:
                    remembered[field.name] = {"exact_values": values}
            if remembered:
                prompt += (
                    "\n\nREVIEWER MEMORY (advisory suggestions only; do not copy without "
                    "support in THIS record): "
                    + json.dumps(remembered, ensure_ascii=False)
                )
            all_task_specs[group.key] = (
                group.key,
                prompt,
                response_model_for(schema, group.key, region_types=allowed_region_types, roles=allowed_discourse_roles),
                int(limits.get(f"{group.key}_num_predict") or limits["indexing_num_predict"]),
                f"derridai_record_{group.key}",
            )
        requested_families = request.get("families")
        if isinstance(requested_families, list) and requested_families:
            # Explicit human reruns bypass Fast-mode routing, but only for the
            # selected family/families. This prevents a text correction from
            # needlessly repeating every expensive metadata task.
            requested = {str(value) for value in requested_families}
            tasks = [spec for name, spec in all_task_specs.items() if name in requested]
        else:
            tasks = []
            # Discourse classification is the semantic corroboration layer for
            # deterministic region/primary-text rules and is therefore always
            # scheduled unless the family is already human-owned. This catches
            # bad or unreviewed main-text page ranges while also supplying the
            # high-value discourse_role proposal. Quotation and indexing keep their
            # routing; any group a schema adds runs every time.
            for name, spec in all_task_specs.items():
                if name == "quotation" and not (enrichment_mode == "deep" or quote_signal):
                    continue
                if name == "indexing" and not semantic_indexing:
                    continue
                tasks.append(spec)
        selected_names = {item[0] for item in tasks}
        # Normal Fast-mode routing settles unneeded families as skipped. An
        # explicit selective rerun must leave every unselected family's prior
        # terminal state and normalized metadata untouched.
        if not (isinstance(requested_families, list) and requested_families):
            for skipped_family in set(all_task_specs) - selected_names:
                record.setdefault("metadata_stage_status", {})[skipped_family] = "skipped"
                record.setdefault("metadata_execution_ledger", {})[skipped_family] = {
                    "state": "skipped", "finished_at": iso_now(),
                    "error": "Skipped by fast enrichment routing; no strong signal required this LLM family.",
                }
                if stage_callback:
                    stage_callback(record, skipped_family, "skipped", "Fast enrichment routing")
        return tasks, source_ids, obvious_apparatus


    def _execute_metadata_tasks(
        self, record: dict[str, Any], request: dict[str, Any],
        tasks: list[tuple[str, str, type[BaseModel], int, str]], build_id: str,
        stage_callback: Callable[[dict[str, Any], str, str, str | None], None] | None,
    ) -> list[tuple[str, dict[str, Any] | None, Exception | None]]:
        """Run unsettled families with live ownership checks and durable stage callbacks."""
        requested_families = request.get("families")
        stage_results: list[tuple[str, dict[str, Any] | None, Exception | None]] = []
        persisted_stage_results = record.setdefault("metadata_stage_results", {})
        stage_status = record.setdefault("metadata_stage_status", {})
        stage_ledger = record.setdefault("metadata_execution_ledger", {})
        for task_name, prompt, response_model, max_tokens, schema_name in tasks:
            if build_id:
                try:
                    live_rows = self.repo.load_records(build_id)
                    live_record = next((row for row in live_rows if str(row.get("record_id") or "") == str(record.get("record_id") or "")), None)
                except Exception as exc:
                    reason = (
                        f"Could not verify live reviewer ownership before {task_name} metadata enrichment: {exc}"
                    )
                    failure = RuntimeError(reason)
                    stage_status[task_name] = "needs_review"
                    stage_ledger[task_name] = {
                        "state": "needs_review", "finished_at": iso_now(),
                        "error": reason, "reason_code": "ownership_state_unavailable",
                    }
                    stage_results.append((task_name, None, failure))
                    if stage_callback:
                        stage_callback(record, task_name, "needs_review", reason)
                    self._append_warning(build_id, f"{record.get('record_id')}: {reason}")
                    continue
                if isinstance(live_record, dict):
                    touched = {str(value) for value in (live_record.get("human_touched_fields") or [])}
                    live_schema = self._schema_for(build_id)
                    migrate_record_assertions(live_record, live_schema)
                    family_fields = live_schema.family_fields().get(task_name, set())
                    all_owned = bool(family_fields) and all(
                        (
                            (assertion := current_assertion_by_name(live_record, field)) is not None
                            and (
                                assertion.authority_status in {"human_confirmed", "human_override"}
                                or assertion.derivation_method == "deterministic"
                            )
                        )
                        for field in family_fields
                        if field not in {"attribution_confidence", "semantic_classification_confidence"}
                    )
                    if "__text__" in touched or "__review__" in touched or all_owned:
                        reason = "Human reviewed this record before automatic enrichment." if {"__text__", "__review__"} & touched else "All fields in this metadata family are already human-owned or deterministic."
                        stage_status[task_name] = "skipped"
                        stage_ledger[task_name] = {"state": "skipped", "finished_at": iso_now(), "error": reason}
                        stage_results.append((task_name, {"metadata": {}, "field_evidence": {}, "review_reason": ""}, None))
                        if stage_callback:
                            stage_callback(record, task_name, "skipped", reason)
                        continue
            adaptive_skip, adaptive_reason = self._adaptive_family_should_skip(build_id, task_name, request)
            if adaptive_skip and not (isinstance(requested_families, list) and requested_families):
                stage_status[task_name] = "skipped"
                stage_ledger[task_name] = {"state": "skipped", "finished_at": iso_now(), "error": adaptive_reason, "reason_code": "adaptive_low_yield"}
                stage_results.append((task_name, {"metadata": {}, "field_evidence": {}, "review_reason": ""}, None))
                if stage_callback:
                    stage_callback(record, task_name, "skipped", adaptive_reason)
                continue
            prior = persisted_stage_results.get(task_name)
            prior_state = str(stage_status.get(task_name) or "")
            if isinstance(prior, dict):
                stage_status[task_name] = "complete"
                stage_results.append((task_name, prior, None))
                continue
            # A fully materialized family no longer needs its bulky raw response.
            # Its status is sufficient to skip the provider on crash-safe resume;
            # the normalized metadata/evidence already lives on the record. Failed
            # and user-skipped families are also terminal until an explicit retry.
            if prior_state == "complete":
                stage_results.append((task_name, {"metadata": {}, "field_evidence": {}, "review_reason": ""}, None))
                continue
            if prior_state in {"failed", "needs_review", "skipped"}:
                prior_error = RuntimeError(f"{task_name} metadata previously settled as {prior_state}.")
                stage_results.append((task_name, None, prior_error))
                continue
            if build_id:
                try:
                    if bool(self.repo.get_build(build_id).get("metadata_settle_requested")):
                        exc = RuntimeError("Automatic metadata was settled as unresolved by the user.")
                        stage_status[task_name] = "skipped"
                        stage_ledger[task_name] = {"state": "skipped", "finished_at": iso_now(), "error": str(exc)}
                        stage_results.append((task_name, None, exc))
                        if stage_callback:
                            stage_callback(record, task_name, "skipped", str(exc))
                        continue
                except KeyError as exc:
                    raise RuntimeError(
                        "Could not verify metadata-settle state because the corpus build no longer exists."
                    ) from exc
            # Resolve the active build profile at task start. A profile switch does
            # not interrupt an in-flight request, but the next family/record picks
            # up the newly selected profile.
            active_request = self._latest_runtime_request(build_id, request) if build_id else request
            started_at = iso_now()
            ledger_context = {
                "provider_profile_id": active_request.get("provider_profile_id"),
                "provider": active_request.get("provider"),
                "model": active_request.get("model"),
                "attempts_allowed": 2,
                "input_chars": len(prompt),
                "max_output_tokens": max_tokens,
                "timeout_seconds": _stage_timeouts(active_request).get(task_name),
            }
            stage_status[task_name] = "running"
            stage_ledger[task_name] = {**ledger_context, "state": "running", "started_at": started_at, "finished_at": None, "error": None}
            if stage_callback:
                stage_callback(record, task_name, "running", None)
            started_clock = time.monotonic()
            try:
                result = self._chat_json(
                    active_request,
                    prompt,
                    response_model=response_model,
                    max_tokens=max_tokens,
                    schema_name=schema_name,
                    build_id=build_id,
                )
                persisted_stage_results[task_name] = result
                stage_status[task_name] = "complete"
                stage_ledger[task_name] = {
                    **ledger_context, "state": "complete", "started_at": started_at, "finished_at": iso_now(),
                    "elapsed_ms": int((time.monotonic() - started_clock) * 1000), "error": None,
                }
                stage_results.append((task_name, result, None))
                self._ledger.append(CALL, model=str(active_request.get("model") or ""), field=task_name, build_id=build_id, record_id=str(record.get("record_id") or ""), run_id=str(request.get("run_id") or (f"build-{build_id}" if build_id else "")), elapsed_ms=stage_ledger[task_name].get("elapsed_ms", 0), ok=True, **experiment.context(request, model=str(active_request.get("model") or ""), record_id=str(record.get("record_id") or ""), code_version=APP_VERSION, prompt_version=PROFILE_VERSION))
                self._record_family_effectiveness(
                    build_id, task_name, result, elapsed_ms=stage_ledger[task_name].get("elapsed_ms", 0),
                    provider_profile_id=str(ledger_context.get("provider_profile_id") or ""),
                    provider=str(ledger_context.get("provider") or ""), model=str(ledger_context.get("model") or ""),
                )
                if stage_callback:
                    stage_callback(record, task_name, "complete", None)
            except InterruptedError:
                raise
            except Exception as exc:
                stage_status[task_name] = "failed"
                stage_ledger[task_name] = {
                    **ledger_context, "state": "failed", "started_at": started_at, "finished_at": iso_now(),
                    "elapsed_ms": int((time.monotonic() - started_clock) * 1000), "error": str(exc)[:1200],
                }
                stage_results.append((task_name, None, exc))
                self._ledger.append(CALL, model=str(active_request.get("model") or ""), field=task_name, build_id=build_id, record_id=str(record.get("record_id") or ""), run_id=str(request.get("run_id") or (f"build-{build_id}" if build_id else "")), elapsed_ms=int((time.monotonic() - started_clock) * 1000), ok=False, **experiment.context(request, model=str(active_request.get("model") or ""), record_id=str(record.get("record_id") or ""), code_version=APP_VERSION, prompt_version=PROFILE_VERSION))
                if stage_callback:
                    stage_callback(record, task_name, "failed", str(exc))
                if build_id:
                    self._append_warning(build_id, f"{record.get('record_id')}: {task_name} metadata requires review ({exc})")

        return stage_results


    def _reconcile_metadata_results(
        self, record: dict[str, Any], profile: dict[str, Any], source_ids: list[str],
        stage_results: list[tuple[str, dict[str, Any] | None, Exception | None]],
        obvious_apparatus: bool,
        request: dict[str, Any] | None = None,
        build_id: str = "",
        schema: MetadataSchema | None = None,
    ) -> dict[str, Any]:
        """Bind proposals to source evidence while retaining reviewer-owned values."""
        schema = schema or default_schema()
        run_guidance = (
            request.get("run_guidance")
            if isinstance(request, dict) and isinstance(request.get("run_guidance"), dict)
            else {}
        )
        # What may be proposed, cited and reviewed comes from the build's schema, not from a fixed list.
        allowed_fields = _allowed_for(schema)
        attribution_fields = schema.attribution_fields()
        evidence_required_fields = schema.evidence_fields()
        assessment_required_fields = set(CORE_FIELDS) | {field.name for field in schema.fields if field.assess}
        cached_prefills = (
            record.get("metadata_adjudication_prefills")
            if isinstance(record.get("metadata_adjudication_prefills"), dict)
            else {}
        )
        model = str((request or {}).get("model") or "")
        run_id = str((request or {}).get("run_id") or (f"build-{build_id}" if build_id else ""))
        off = experiment.disabled(request)
        conditions = experiment.context(request, model=model, record_id=str(record.get("record_id") or ""), code_version=APP_VERSION, prompt_version=PROFILE_VERSION)

        def autofill(field: str, value: Any, confidence: float | None, evidence_info: dict[str, Any]) -> dict[str, Any] | None:
            """The status for a value the model is sure enough about to fill in, or None.

            The blended confidence (see autofill.py) outranks the model's own needs_review flag, but
            never the absence of a cited source block or a self-report at or below the profile floor.
            """
            if "autofill" in off or conditions["blind"] or value in (None, "", []) or confidence is None or confidence <= minimum or not evidence_info.get("block_ids"):
                return None
            reviews, accepted = (0, 0) if "blended_confidence" in off else self._ledger.review_counts(model, field)
            decision = decide_autofill(confidence, reviews, accepted)
            self._note_suspension(model, field, bool(decision["suspended"]), reviews, accepted, build_id, run_id)
            if not decision["autofill"]:
                return None
            audit = in_audit_sample(str(record.get("record_id") or ""), field)
            filled_confidence = decision["confidence"] or 0.0
            self._ledger.append(AUTOFILLED, model=model, field=field, build_id=build_id, record_id=str(record.get("record_id") or ""), run_id=run_id, confidence=filled_confidence, self_reported=confidence, audit=audit, **conditions)
            return {
                "status": "model_inferred", "method": "llm", "model": model, "confidence": filled_confidence,
                "self_reported_confidence": confidence, "auto_populated": True, "autofilled": True, "audit_sample": audit,
                "proposed_value": value, "reason_code": "resolved",
                "reason": f"Filled in automatically at {round(filled_confidence * 100)}% confidence, with cited evidence.",
            }
        allowed_region_types = list(profile.get("region_types") or REGION_TYPES)
        allowed_discourse_roles = list(profile.get("discourse_roles") or DISCOURSE_ROLES)
        required_metadata_fields = list(profile.get("required_metadata_fields") or [])
        stage_status = record.setdefault("metadata_stage_status", {})
        stage_ledger = record.setdefault("metadata_execution_ledger", {})
        # Expose whether the semantic reader actually evaluated deterministic
        # structural fields. A final value alone must never imply corroboration.
        discourse_state = str(stage_status.get("discourse") or "")
        discourse_ledger = stage_ledger.get("discourse") if isinstance(stage_ledger.get("discourse"), dict) else {}
        if discourse_state in {"skipped", "failed", "needs_review"}:
            skip_reason = str(discourse_ledger.get("error") or f"Discourse metadata stage was {discourse_state}.")
            for structural_field in ("region_type", "primary_text"):
                assertion = current_assertion_by_name(record, structural_field)
                structural_status = record.setdefault("metadata_field_status", {}).get(structural_field)
                if (
                    assertion is not None
                    and assertion.derivation_method == "deterministic"
                    and isinstance(structural_status, dict)
                    and "llm_checked" not in structural_status
                ):
                    structural_status["llm_checked"] = False
                    structural_status["llm_skip_reason"] = skip_reason

        minimum = float(profile.get("min_metadata_confidence") or 0.65)
        clean_evidence: dict[str, Any] = dict(record.get("metadata_evidence") or {})
        valid_ids = set(source_ids)
        review_reasons: list[str] = []
        evidence_confidences: list[float] = []
        attribution_confidences: list[float] = []
        model_review_reasons: list[str] = []
        field_assessments: dict[str, dict[str, Any]] = {}
        llm_populated_fields: set[str] = set()
        raw_llm_values: dict[str, Any] = {}
        # Presence in the required metadata object means the field was requested,
        # not that the model supplied an assessment. Keep those facts separate.
        llm_requested_fields: set[str] = set()
        llm_value_returned_fields: set[str] = set()
        llm_checked_fields: set[str] = set()  # compatibility alias: actually assessed
        successful_tasks = 0

        for task_name, result, failure in stage_results:
            if failure is not None or not isinstance(result, dict):
                review_reasons.append(f"{task_name} metadata extraction could not be validated: {failure}")
                continue
            successful_tasks += 1
            metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
            if isinstance(result.get("field_assessments"), dict):
                assessed = {str(key): value for key, value in result.get("field_assessments", {}).items() if isinstance(value, dict)}
                field_assessments.update(assessed)
                llm_checked_fields.update(key for key in assessed if key in allowed_fields)
            field_status = record.setdefault("metadata_field_status", {})
            for key, value in metadata.items():
                if key not in allowed_fields or key in SOURCE_BOUND_FIELDS:
                    continue
                llm_requested_fields.add(key)
                value, raw_llm_value = _normalize_semantic_value(key, value)
                if value not in (None, "", []):
                    llm_value_returned_fields.add(key)
                if raw_llm_value is not None:
                    raw_llm_values[key] = raw_llm_value
                existing_status = field_status.get(key) if isinstance(field_status.get(key), dict) else {}
                # Human decisions are authoritative. Background/retry enrichment
                # may add evidence, but it must never resurrect an already
                # confirmed review issue or overwrite a human value.
                existing_assertion = current_assertion_by_name(record, key)
                if (
                    existing_assertion is not None
                    and existing_assertion.authority_status in {"human_confirmed", "human_override"}
                ):
                    continue
                prefilled = cached_prefills.get(key)
                if prefilled not in (None, "", []) and value not in (None, "", []) and value != prefilled:
                    field_status[key] = {
                        "status": "unresolved",
                        "method": "human_cache+llm",
                        "confidence": None,
                        "value_source": "human_adjudication_cache",
                        "prefilled_candidate": "human",
                        "prefilled_value": prefilled,
                        "llm_value": value,
                        "llm_confidence": None,
                        "proposed_value": value,
                        "reason_code": "human_llm_disagreement",
                        "reason": "A previously human-confirmed value differs from this run's blind model judgment.",
                    }
                    record[key] = prefilled
                    continue
                if prefilled not in (None, "", []):
                    record[key] = prefilled
                    existing_status = {
                        **existing_status,
                        "status": "human_confirmed",
                        "method": "human_adjudication_cache",
                        "value_source": "human_adjudication_cache",
                        "prefilled_value": prefilled,
                        "llm_value": value,
                        "llm_checked": True,
                    }
                    field_status[key] = existing_status
                    continue
                if key in {"region_type", "primary_text"} and existing_status.get("status") == "deterministic":
                    # Structural classifications remain selected. The semantic
                    # reader may corroborate or dispute them, but reviewer-owned
                    # document structure is never replaced by an LLM proposal.
                    assessment = field_assessments.get(key) if isinstance(field_assessments.get(key), dict) else {}
                    result_evidence = result.get("field_evidence") if isinstance(result.get("field_evidence"), dict) else {}
                    key_evidence = result_evidence.get(key) if isinstance(result_evidence.get(key), dict) else {}
                    confidence = assessment.get("confidence") if isinstance(assessment.get("confidence"), (int, float)) else (key_evidence.get("confidence") if isinstance(key_evidence.get("confidence"), (int, float)) else None)
                    deterministic_value = record.get(key)
                    deterministic_method = str(existing_status.get("method") or "")
                    strong_structure = deterministic_method in STRONG_STRUCTURAL_METHODS
                    existing_status = dict(existing_status)
                    existing_status["llm_requested"] = True
                    existing_status["llm_value_returned"] = value not in (None, "", [])
                    existing_status["llm_assessed"] = bool(assessment)
                    existing_status["llm_checked"] = bool(assessment)  # backward-compatible UI/API key
                    existing_status["llm_value"] = value
                    existing_status["llm_confidence"] = confidence
                    if value is None:
                        existing_status["llm_corroborates"] = None
                        existing_status["llm_skip_reason"] = "Semantic LLM returned no supported value for this field."
                    else:
                        corroborates = value == deterministic_value
                        existing_status["llm_corroboration"] = value
                        existing_status["llm_corroborates"] = corroborates
                        existing_status["corroboration_method"] = "llm"
                        if not corroborates:
                            deterministic_strength = float(existing_status.get("confidence") or 0.0)
                            existing_status["status"] = "unresolved"
                            existing_status["method"] = "deterministic+llm"
                            existing_status["reason_code"] = "deterministic_llm_disagreement"
                            existing_status["deterministic_value"] = deterministic_value
                            existing_status["deterministic_reason"] = str(existing_status.get("reason") or f"Deterministic inference selected {deterministic_value!r}.")
                            existing_status["llm_reason"] = str(assessment.get("reason") or "Semantic LLM check selected a different value.")
                            if strong_structure:
                                existing_status["reason"] = (
                                    f"Reviewer-defined document structure requires {deterministic_value!r}; semantic LLM check suggests {value!r}"
                                    + (f" at {round(float(confidence)*100)}% confidence" if confidence is not None else "")
                                    + ". The structural value remains selected; the disagreement is retained for review."
                                )
                                existing_status["prefilled_candidate"] = "deterministic"
                                existing_status["auto_populated"] = False
                            else:
                                existing_status["reason"] = (
                                    f"Deterministic inference suggests {deterministic_value!r}; semantic LLM check suggests {value!r}"
                                    + (f" at {round(float(confidence)*100)}% confidence" if confidence is not None else "")
                                    + ". Review both candidates."
                                )
                                weak_manifest_range = deterministic_method == "manifest_page_range"
                                if key != "primary_text" and confidence is not None and float(confidence) > minimum and (weak_manifest_range or deterministic_strength < 0.9):
                                    record[key] = value
                                    existing_status["prefilled_candidate"] = "llm"
                                    existing_status["auto_populated"] = True
                                elif key != "primary_text":
                                    existing_status["prefilled_candidate"] = "deterministic"
                                    existing_status["auto_populated"] = False
                                else:
                                    existing_status["prefilled_candidate"] = "deterministic"
                    field_status[key] = existing_status
                    continue
                if key == "region_type" and value is not None and value not in allowed_region_types:
                    field_status[key] = {"status": "invalid", "method": "llm", "reason_code": "invalid_value", "reason": f"Model returned an unsupported region type: {value}"}
                    continue
                if key == "discourse_role" and value is not None and value not in allowed_discourse_roles:
                    field_status[key] = {"status": "invalid", "method": "llm", "reason_code": "invalid_value", "reason": f"Model returned an unsupported discourse role: {value}"}
                    continue
                if key == "primary_text" and value is not None and not isinstance(value, bool):
                    field_status[key] = {"status": "invalid", "method": "llm", "reason_code": "invalid_value", "reason": "Model returned a non-boolean primary_text value."}
                    continue
                if key == "proposition_status" and value is not None and value not in PROPOSITION_STATUS_VALUES:
                    field_status[key] = {"status": "invalid", "method": "llm", "reason_code": "invalid_value", "proposed_value": value, "reason": f"Model returned an unsupported proposition status: {value}"}
                    continue
                if key == "stance" and value is not None and value not in STANCE_VALUES:
                    field_status[key] = {"status": "invalid", "method": "llm", "reason_code": "invalid_value", "proposed_value": value, "raw_llm_value": raw_llm_value or value, "llm_checked": True, "reason": f"Model returned an unsupported stance: {value}"}
                    continue
                # A valid model value is a proposal and should be visible to the reviewer
                # regardless of confidence. Confidence/evidence determine whether it is
                # auto-resolved, not whether the record is populated.
                record[key] = value
                if value not in (None, "", []):
                    llm_populated_fields.add(key)
            evidence = result.get("field_evidence") if isinstance(result.get("field_evidence"), dict) else {}
            for field, info in evidence.items():
                if field not in allowed_fields or not isinstance(info, dict):
                    continue
                block_ids = [str(value) for value in info.get("block_ids") or [] if str(value) in valid_ids]
                raw_confidence = info.get("confidence")
                try:
                    confidence = max(0.0, min(1.0, float(raw_confidence))) if isinstance(raw_confidence, (int, float)) else None
                except (TypeError, ValueError):
                    confidence = None
                clean_evidence[field] = {
                    "block_ids": block_ids,
                    "confidence": confidence,
                    "reason": str(info.get("reason") or ""),
                }
                if confidence is not None:
                    evidence_confidences.append(confidence)
                    if field in attribution_fields:
                        attribution_confidences.append(confidence)
            reason = str(result.get("review_reason") or "").strip()
            if reason:
                model_review_reasons.append(reason)

        for field in sorted(evidence_required_fields):
            value = record.get(field)
            if value in (None, "", []):
                continue
            existing_assertion = current_assertion_by_name(record, field)
            if existing_assertion is not None and existing_assertion.derivation_method == "deterministic":
                continue
            info = clean_evidence.get(field)
            if not isinstance(info, dict):
                review_reasons.append(f"{field} has no bound source evidence")
                continue
            if not info.get("block_ids"):
                review_reasons.append(f"{field} evidence does not identify a current-record source block")
            evidence_confidence = info.get("confidence")
            if not isinstance(evidence_confidence, (int, float)):
                review_reasons.append(f"{field} evidence confidence was not reported")
            elif float(evidence_confidence) <= minimum:
                review_reasons.append(f"{field} evidence confidence is below {minimum:.2f}")

        record["metadata_evidence"] = clean_evidence
        field_status = record.setdefault("metadata_field_status", {})
        # Every model-populated field gets explicit provenance/confidence, not only
        # the publication-critical discourse fields. This keeps quotation/indexing
        # suggestions reviewable and prevents later records from appearing as if the
        # LLM suddenly stopped supplying metadata merely because those fields were
        # outside REVIEW_METADATA_FIELDS.
        for field in sorted(llm_populated_fields):
            current = field_status.get(field) if isinstance(field_status.get(field), dict) else {}
            current_assertion = current_assertion_by_name(record, field)
            if (
                (
                    current_assertion is not None
                    and (
                        current_assertion.authority_status in {"human_confirmed", "human_override"}
                        or current_assertion.derivation_method in {"deterministic", "inherited"}
                    )
                )
                or current.get("reason_code") in {"deterministic_llm_disagreement", "human_llm_disagreement"}
            ):
                continue
            assessment = field_assessments.get(field) if isinstance(field_assessments.get(field), dict) else {}
            evidence_info = clean_evidence.get(field) if isinstance(clean_evidence.get(field), dict) else {}
            assessment_confidence = assessment.get("confidence") if isinstance(assessment.get("confidence"), (int, float)) else None
            evidence_confidence = evidence_info.get("confidence") if isinstance(evidence_info.get("confidence"), (int, float)) else None
            confidence = float(assessment_confidence if assessment_confidence is not None else evidence_confidence) if (assessment_confidence is not None or evidence_confidence is not None) else None
            needs_human = bool(assessment.get("needs_review"))
            requires_confidence = field in assessment_required_fields or field in evidence_required_fields
            evidence_failed = field in evidence_required_fields and (
                not evidence_info.get("block_ids")
                or not isinstance(evidence_info.get("confidence"), (int, float))
                or float(evidence_info.get("confidence")) <= minimum
            )
            auto = autofill(field, record.get(field), confidence, evidence_info)
            if auto:
                auto["value_source"] = "llm"
                auto["verification_status"] = "auto_resolved"
                field_status[field] = auto
                continue
            if needs_human or (requires_confidence and confidence is None) or (requires_confidence and confidence <= minimum) or evidence_failed:
                if needs_human:
                    reason_code = "ambiguous"
                elif requires_confidence and confidence is None:
                    reason_code = "confidence_missing"
                elif requires_confidence and confidence <= minimum:
                    reason_code = "low_confidence"
                else:
                    reason_code = "evidence_failed"
                field_status[field] = {
                    "status": "unresolved",
                    "method": "llm",
                    "confidence": confidence,
                    # The value is populated; it simply has not been verified.
                    "auto_populated": True,
                    "autofilled": False,
                    "value_source": "llm",
                    "verification_status": "pending_review",
                    "proposed_value": record.get(field),
                    "reason_code": reason_code,
                    "reason": str(assessment.get("reason") or evidence_info.get("reason") or "Model proposal requires reviewer confirmation."),
                }
                continue
            field_status[field] = {
                "status": "unresolved",
                "method": "llm",
                "confidence": confidence,
                "auto_populated": True,
                "autofilled": False,
                "value_source": "llm",
                "verification_status": "pending_review",
                "proposed_value": record.get(field),
                "reason_code": "autofill_not_approved",
                "reason": str(
                    assessment.get("reason")
                    or evidence_info.get("reason")
                    or "Model value was populated, but calibrated autofill did not approve automatic verification."
                ),
            }
        # Run guidance is intentionally scoped to this execution, but a required
        # field must still enter the same review queue as schema review fields.
        required_guidance_fields = {
            str(field)
            for field, item in run_guidance.items()
            if isinstance(item, dict) and bool(item.get("required"))
        }
        review_metadata_fields = list(dict.fromkeys([
            *(profile.get("review_metadata_fields") or REVIEW_METADATA_FIELDS),
            *required_guidance_fields,
        ]))
        for field in review_metadata_fields:
            value = record.get(field)
            current = field_status.get(field) if isinstance(field_status.get(field), dict) else {}
            current_assertion = current_assertion_by_name(record, field)
            if (
                (
                    current_assertion is not None
                    and (
                        current_assertion.authority_status in {"human_confirmed", "human_override"}
                        or current_assertion.derivation_method in {"deterministic", "inherited"}
                        or current_assertion.value_status == "invalid"
                    )
                )
                or current.get("reason_code") in {
                    "deterministic_llm_disagreement",
                    "human_llm_disagreement",
                    "low_confidence",
                    "confidence_missing",
                }
            ):
                continue
            evidence_info = clean_evidence.get(field) if isinstance(clean_evidence.get(field), dict) else {}
            assessment = field_assessments.get(field) if isinstance(field_assessments.get(field), dict) else {}
            guidance_item = run_guidance.get(field) if isinstance(run_guidance.get(field), dict) else {}
            required_placeholder = str(guidance_item.get("default_placeholder") or "").strip()
            if bool(guidance_item.get("required")) and value in (None, "", []):
                if required_placeholder:
                    record[field] = required_placeholder
                    field_status[field] = {
                        "status": "unresolved",
                        "method": "run_guidance",
                        "confidence": None,
                        "auto_populated": True,
                        "autofilled": False,
                        "value_source": "run_guidance",
                        "verification_status": "pending_review",
                        "proposed_value": None,
                        "placeholder": True,
                        "reason_code": "required_placeholder",
                        "reason": "The run required a value, but the model could not establish one. Replace this placeholder during review.",
                    }
                    continue
            assessment_confidence = assessment.get("confidence") if isinstance(assessment.get("confidence"), (int, float)) else None
            evidence_confidence = evidence_info.get("confidence") if isinstance(evidence_info.get("confidence"), (int, float)) else None
            confidence = float(assessment_confidence if assessment_confidence is not None else evidence_confidence) if (assessment_confidence is not None or evidence_confidence is not None) else None
            reason = str(assessment.get("reason") or evidence_info.get("reason") or "Model assessment.")
            needs_human = bool(assessment.get("needs_review"))
            outcome = str(assessment.get("outcome") or "")
            if field not in required_metadata_fields and value in (None, "", []) and not assessment:
                # Backward compatibility for old persisted model output that had no
                # assessment object at all. New structured output requires one.
                continue
            if field not in required_metadata_fields and value in (None, "", []) and outcome == "no_supported_value":
                if confidence is not None and confidence > minimum and not needs_human:
                    field_status[field] = {
                        "status": "model_inferred", "method": "llm", "confidence": confidence,
                        "auto_populated": False, "autofilled": False, "value_source": "llm",
                        "verification_status": "auto_resolved", "proposed_value": None,
                        "reason_code": "no_supported_value", "reason": reason or "Model found no supported value for this field.",
                    }
                else:
                    field_status[field] = {
                        "status": "unresolved", "method": "llm", "confidence": confidence,
                        "auto_populated": False, "autofilled": False, "value_source": "llm",
                        "verification_status": "pending_review", "proposed_value": None,
                        "reason_code": "ambiguous" if needs_human else ("confidence_missing" if confidence is None else "low_confidence"),
                        "reason": reason or "Model proposed that no supported value applies; reviewer confirmation is required.",
                    }
                continue
            if value in (None, "", []) and outcome == "uncertain":
                field_status[field] = {
                    "status": "unresolved", "method": "llm", "confidence": confidence,
                    "auto_populated": False, "autofilled": False, "value_source": "llm",
                    "verification_status": "pending_review", "proposed_value": None,
                    "reason_code": "ambiguous", "reason": reason or "The model could not determine a supported value.",
                }
                continue
            auto = autofill(field, value, confidence, evidence_info)
            if auto:
                auto["value_source"] = "llm"
                auto["verification_status"] = "auto_resolved"
                field_status[field] = auto
            elif field in required_metadata_fields and value in (None, "", []):
                field_status[field] = {"status": "unresolved", "method": "hybrid", "confidence": confidence, "auto_populated": False, "value_source": "llm", "verification_status": "pending_review", "proposed_value": value, "reason_code": "ambiguous", "reason": reason}
            elif (confidence is None or confidence <= minimum) and value not in (None, "", []):
                # The proposal is already populated. Missing/low confidence blocks
                # automatic resolution, not visibility of the value.
                field_status[field] = {
                    "status": "unresolved", "method": "llm", "confidence": confidence,
                    "auto_populated": True, "autofilled": False, "value_source": "llm",
                    "verification_status": "pending_review", "proposed_value": value,
                    "reason_code": "confidence_missing" if confidence is None else "low_confidence",
                    "reason": reason or ("Model confidence was not reported." if confidence is None else f"Model confidence is below {minimum:.2f}."),
                }
            elif value in (None, "", []) and field in evidence_required_fields and confidence is not None and confidence > minimum and not needs_human:
                # A confident assessment with no value cannot be shown as an
                # inference: there is nothing to display, populate, or cite. Keep it
                # in the review queue (one click confirms a genuine absence).
                field_status[field] = {
                    "status": "unresolved", "method": "llm", "confidence": confidence, "auto_populated": False,
                    "proposed_value": None, "reason_code": "no_value_returned",
                    "reason": f"The model reported {round(confidence * 100)}% confidence but returned no value. {reason}".strip(),
                }
            elif needs_human or (value not in (None, "", []) and field in evidence_required_fields and (not evidence_info.get("block_ids") or not isinstance(evidence_info.get("confidence"), (int, float)) or float(evidence_info.get("confidence")) <= minimum)):
                field_status[field] = {
                    "status": "unresolved", "method": "llm", "confidence": confidence,
                    "auto_populated": value not in (None, "", []), "autofilled": False, "value_source": "llm",
                    "verification_status": "pending_review", "proposed_value": value,
                    "reason_code": "ambiguous" if needs_human else "evidence_failed", "reason": reason,
                }
            else:
                field_status[field] = {
                    "status": "unresolved", "method": "llm", "confidence": confidence,
                    "auto_populated": value not in (None, "", []), "autofilled": False, "value_source": "llm",
                    "verification_status": "pending_review", "proposed_value": value,
                    "reason_code": "autofill_not_approved",
                    "reason": reason or "Model value was populated, but calibrated autofill did not approve automatic verification.",
                }

        apply_metadata_constraints(record, schema)
        for requested_field in llm_requested_fields:
            requested_status = field_status.get(requested_field)
            if isinstance(requested_status, dict):
                requested_status.setdefault("llm_requested", True)
                requested_status.setdefault("llm_value_returned", requested_field in llm_value_returned_fields)
                requested_status.setdefault("llm_assessed", requested_field in llm_checked_fields)
                # Kept for API/UI compatibility; it now means "the model returned a
                # field assessment", not merely "metadata JSON contained this key".
                requested_status.setdefault("llm_checked", requested_field in llm_checked_fields)
                if requested_field in raw_llm_values:
                    requested_status.setdefault("raw_llm_value", raw_llm_values[requested_field])

        shown: dict[str, Any] = {}
        for field in sorted(llm_populated_fields):
            proposed_status = field_status.get(field) if isinstance(field_status.get(field), dict) else {}
            shown[field] = record.get(field)
            if conditions["blind"] and proposed_status.get("method") == "llm" and proposed_status.get("status") in {"model_inferred", "unresolved"}:
                # Blind review: the model's value is sealed in the ledger and the reviewer sees an empty field.
                record[field] = [] if isinstance(shown[field], list) else None
                field_status[field] = proposed_status = {
                    "status": "unresolved", "method": "llm", "blind": True, "reason_code": "blind_review", "auto_populated": False,
                    "reason": "",
                }
                _scrub_sealed_field(record, field)
            if proposed_status.get("method") == "llm":
                # Later human decisions on this value are attributed to the model and conditions that produced it.
                proposed_status.setdefault("model", model)
                proposed_status["conditions"] = conditions
            assessed = field_assessments.get(field) if isinstance(field_assessments.get(field), dict) else {}
            self._ledger.append(
                PROPOSED, model=model, field=field, build_id=build_id, record_id=str(record.get("record_id") or ""), run_id=run_id,
                value=shown.get(field), self_reported=assessed.get("confidence"),
                grounded=bool((clean_evidence.get(field) or {}).get("block_ids")), outcome=proposed_status.get("status"),
                supported=experiment.supported_in_text(shown.get(field), str(record.get("text") or "")) if field in experiment.FREE_TEXT_FIELDS else None, **conditions,
            )
        record["semantic_classification_confidence"] = round(sum(evidence_confidences) / len(evidence_confidences), 4) if evidence_confidences else None
        record["attribution_confidence"] = round(min(attribution_confidences), 4) if attribution_confidences else 1.0
        if any(isinstance(info, dict) and info.get("blind") for info in field_status.values()):
            # These aggregates are the model's own confidence in a record whose values are sealed.
            record["semantic_classification_confidence"] = None
            record["attribution_confidence"] = None
        review_reasons.extend(model_review_reasons)
        if review_reasons:
            record["metadata_needs_attention"] = True
            record["metadata_attention_reasons"] = list(dict.fromkeys(value for value in review_reasons if value))[:50]
        else:
            record["metadata_needs_attention"] = False
            record["metadata_attention_reasons"] = []
        state_profile = {
            **profile,
            "required_metadata_fields": list(dict.fromkeys([
                *(profile.get("required_metadata_fields") or []),
                *required_guidance_fields,
            ])),
            "review_metadata_fields": review_metadata_fields,
        }
        _sync_record_metadata_state(record, state_profile, schema)
        incomplete_fields = list(record.get("metadata_incomplete_fields") or [])
        review_fields = list(record.get("metadata_review_fields") or [])
        # Optional indexing/quotation failures remain visible but do not make a structurally
        # valid record permanently unpublishable. Required hybrid classifications and
        # the discourse task are the publication-critical metadata gate.
        discourse_ok = any(name == "discourse" and failure is None for name, _result, failure in stage_results)
        if not discourse_ok and str(record.get("metadata_stage_status", {}).get("discourse") or "") == "skipped":
            required_discourse = [field for field in required_metadata_fields if field in schema.family_fields()[CORE_GROUP]]
            human_or_deterministic = all(
                (
                    (assertion := current_assertion_by_name(record, field)) is not None
                    and assertion.value_status in {"present", "confirmed_absent"}
                    and (
                        assertion.authority_status in {"human_confirmed", "human_override"}
                        or assertion.derivation_method in {"deterministic", "inherited", "model"}
                    )
                )
                for field in required_discourse
            ) if required_discourse else True
            discourse_ok = obvious_apparatus or human_or_deterministic
        record["metadata_complete"] = discourse_ok and not incomplete_fields and not review_fields
        # Preserve exact terminal states (complete/failed/skipped) from execution
        # instead of flattening every exception into a generic needs_review state.
        # After normalization the raw successful response objects are redundant;
        # stage_status plus normalized record fields are enough to resume without
        # re-running already settled families.
        record["metadata_stage_status"] = dict(stage_status)
        record.pop("metadata_stage_results", None)
        inline, full = _citation_strings(record)
        record["inline_citation"] = inline
        record["full_citation"] = full
        normalized = migrate_record_assertions(record, schema)
        # Preserve compatibility-only audit markers that were attached after
        # the canonical assertion was selected (for example blind, llm_checked,
        # and raw_llm_value). The next migration pass persists them on the
        # assertion's legacy metadata without changing canonical authority.
        normalized_status = normalized.get("metadata_field_status")
        if isinstance(normalized_status, dict):
            canonical_keys = {
                "status", "method", "reason", "confidence", "assertion_id",
                "field_id", "derivation_method", "evaluation_status",
                "authority_status", "value_status",
            }
            for field_name, source_status in field_status.items():
                target_status = normalized_status.get(field_name)
                if not isinstance(source_status, dict) or not isinstance(target_status, dict):
                    continue
                for key, value in source_status.items():
                    if key not in canonical_keys:
                        target_status.setdefault(key, value)
            if any(
                isinstance(status, dict) and status.get("blind")
                for status in normalized_status.values()
            ):
                _scrub_canonical_transport(normalized)
                for status in normalized_status.values():
                    if not isinstance(status, dict) or not status.get("blind"):
                        continue
                    for key in (
                        "confidence", "proposed_value", "llm_value", "raw_llm_value",
                        "llm_confidence", "llm_corroboration", "conditions",
                    ):
                        status.pop(key, None)
                    status["reason"] = ""
        return normalized
