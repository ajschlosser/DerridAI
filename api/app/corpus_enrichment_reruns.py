# Copyright 2026 Aaron John Schlosser, PhD.
"""Metadata enrichment reruns: retry, multi-pass rerun, and per-record enrichment worker.

Started as background operations against a build already past segmentation, these
methods orchestrate retrying, rerunning, and merging metadata enrichment passes across
records. Moved verbatim out of PdfCorpusBuildManager as a mixin (see
corpus_review_actions.py's module docstring for why a mixin, not free functions, is
the right tool when a cluster calls a dozen-plus other self.* members).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any

from .config import settings
from .corpus_enrichment_feedback import enrichment_informational_event
from .corpus_enrichment_helpers import (
    _enrichment_pass_indices,
    _prepend_metadata_priority,
)
from .corpus_llm_helpers import _validate_execution_budget
from .corpus_record_quality import iso_now
from .corpus_review_actions import _serialize_record_mutation
from .corpus_review_state import _sync_record_metadata_state
from .corpus_reviewer_helpers import _metadata_issue_type
from .enrichment_cycles import (
    CONFIDENCE_FIELDS,
    HUMAN_OWNED_STATUSES,
    MAX_PASSES,
    resolve_conflict,
    same_value,
)
from .field_assertions import (
    current_assertion_by_name,
    migrate_record_assertions,
    project_record_assertions,
    reopen_assertion,
    reset_fields_for_evaluation,
    store_assertion,
)
from .metadata_schema import MetadataSchema, default_schema


class EnrichmentRerunsMixin:
    """Mixin members declared here exist on PdfCorpusBuildManager, not on this mixin itself.

    See corpus_review_actions.py's identical block for the full explanation, including why
    everything below is wrapped in `if TYPE_CHECKING:` (an unguarded stub method is a real,
    empty method at runtime and can silently shadow another mixin's real implementation
    depending on base-class order). Attributes typed Any (repo, _lock, _executor,
    _global_learning, _provider_epoch, _cancel) would otherwise need their real classes
    imported from corpus_builder.py, which is circular.
    """

    if TYPE_CHECKING:
        repo: Any
        _lock: Any
        _executor: ThreadPoolExecutor
        _global_learning: Any
        _provider_epoch: dict[str, int]
        _cancel: set[str]

        def active_enrichment_runs(self) -> int: ...
        def _cancelled(self, build_id: str) -> bool: ...
        def _update(self, build_id: str, **changes: Any) -> dict[str, Any]: ...
        def _rewrite_and_validate(self, build_id: str, records: list[dict[str, Any]], *, persist_records: bool = True) -> dict[str, Any]: ...
        def _refresh_workflow_fields(self, build: dict[str, Any]) -> dict[str, Any]: ...
        def _schema_for(self, build_id: str) -> MetadataSchema: ...
        def _schema_of_build(self, build: dict[str, Any]) -> MetadataSchema: ...
        def _profile_of_build(self, build: dict[str, Any]) -> dict[str, Any]: ...
        def _latest_runtime_request(self, build_id: str, fallback: dict[str, Any]) -> dict[str, Any]: ...
        def _editorial_memory(self, build_id: str, current_record: dict[str, Any] | None = None, *, exclude_record_id: str = "", use_global: bool = True, use_progressive: bool = True) -> dict[str, Any]: ...
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
        ) -> dict[str, Any]: ...


    def retry_incomplete_metadata(self, build_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Retry only automatically-retryable metadata issues.

        This is deliberately separate from ``resume``: a metadata retry never
        re-enters document analysis, segmentation, or topology construction.
        """
        build = self.repo.get_build(build_id)
        if build.get("status") in {"queued", "running"}:
            return build
        records = self.repo.load_records(build_id)
        retryable_types = {"not_run", "llm_failed", "evidence_failed", "invalid_value", "unresolved"}
        target_indices: list[int] = []
        target_fields: dict[str, list[str]] = {}
        for index, record in enumerate(records):
            incomplete = [str(value) for value in record.get("metadata_incomplete_fields") or []]
            statuses = record.get("metadata_field_status") if isinstance(record.get("metadata_field_status"), dict) else {}
            retry_fields = [field for field in incomplete if _metadata_issue_type(statuses.get(field) if isinstance(statuses.get(field), dict) else {}, record) in retryable_types]
            if retry_fields:
                target_indices.append(index)
                target_fields[str(record.get("record_id") or index)] = retry_fields
        if not target_indices:
            raise ValueError("No automatically retryable metadata fields remain. Review the human-resolution queue instead.")
        _validate_execution_budget(request)
        public_request = {k: v for k, v in request.items() if k not in {"api_key", "_review_provider"}}
        build["provider"] = request.get("provider") or build.get("provider") or "ollama"
        build["model"] = request.get("model") or build.get("model")
        build["request"] = {**(build.get("request") or {}), **public_request}
        operation_id = f"metadata-retry-{uuid.uuid4().hex[:10]}"
        operation = {
            "operation_id": operation_id, "kind": "metadata_retry", "state": "queued",
            "started_at": iso_now(), "finished_at": None,
            "records_total": len(target_indices), "records_processed": 0,
            "fields_total": sum(len(fields) for fields in target_fields.values()),
            "fields_resolved": 0, "fields_remaining": sum(len(fields) for fields in target_fields.values()),
            "provider_profile_id": public_request.get("provider_profile_id"),
            "provider": build.get("provider"), "model": build.get("model"),
            "target_fields": target_fields,
        }
        build["metadata_operation"] = operation
        self.repo.save_build(build)
        self._update(build_id, status="running", stage="metadata_retry", progress=max(0.96, float(build.get("progress") or 0.0)), error=None, resumable=False, metadata_operation=operation)
        self._executor.submit(self._retry_metadata_worker, build_id, request, operation_id, target_indices, target_fields)
        return self.repo.get_build(build_id)


    def _retry_metadata_worker(self, build_id: str, request: dict[str, Any], operation_id: str, target_indices: list[int], target_fields: dict[str, list[str]]) -> None:
        try:
            build = self.repo.get_build(build_id)
            records = self.repo.load_records(build_id)
            manifest = build.get("manifest") or {}
            total = max(1, len(target_indices))
            max_workers = max(1, min(16, int(request.get("max_concurrent_requests") or 1)))
            operation = dict(build.get("metadata_operation") or {})
            operation["state"] = "running"
            self._update(build_id, metadata_operation=operation)
            with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="pdf-corpus-meta-retry") as pool:
                futures = {}
                for index in target_indices:
                    record = dict(records[index])
                    previous_text = str(records[index - 1].get("text") or "") if index > 0 else ""
                    next_text = str(records[index + 1].get("text") or "") if index + 1 < len(records) else ""
                    before = list(record.get("metadata_incomplete_fields") or [])
                    future = pool.submit(self._enrich_record, record, manifest, request, previous_text=previous_text, next_text=next_text, build_id=build_id)
                    futures[future] = (index, before)
                processed = 0
                resolved = 0
                for future in as_completed(futures):
                    index, before = futures[future]
                    try:
                        updated = future.result()
                    except Exception as exc:
                        updated = dict(records[index])
                        schema = self._schema_for(build_id)
                        reset_fields_for_evaluation(
                            updated,
                            target_fields.get(str(updated.get("record_id") or index), []),
                            schema=schema,
                            discard_history=False,
                            method="metadata_retry_failed",
                            reason=f"Metadata retry failed: {exc}",
                        )
                        updated["metadata_needs_attention"] = True
                        updated["metadata_attention_reasons"] = [f"Metadata retry failed: {exc}"]
                    records[index] = updated
                    after = set(updated.get("metadata_incomplete_fields") or [])
                    resolved += sum(1 for field in before if field not in after)
                    processed += 1
                    self.repo.save_records(build_id, records)
                    op = dict(self.repo.get_build(build_id).get("metadata_operation") or {})
                    op.update({
                        "state": "running", "records_processed": processed,
                        "fields_resolved": resolved,
                        "fields_remaining": max(0, int(op.get("fields_total") or 0) - resolved),
                    })
                    self._update(build_id, status="running", stage="metadata_retry", progress=min(0.979, 0.96 + 0.019 * (processed / total)), metadata_operation=op)
            final_build = self._rewrite_and_validate(build_id, records)
            target_remaining = 0
            for record in records:
                rid = str(record.get("record_id") or "")
                if rid not in target_fields:
                    continue
                incomplete_now = set(str(value) for value in record.get("metadata_incomplete_fields") or [])
                target_remaining += sum(1 for field in target_fields[rid] if field in incomplete_now)
            unresolved_after = int((final_build.get("metadata_issue_summary") or {}).get("fields_unresolved") or 0)
            op = dict(final_build.get("metadata_operation") or {})
            op.update({
                "state": "completed", "finished_at": iso_now(),
                "records_processed": len(target_indices),
                "fields_remaining": target_remaining,
                "fields_resolved": max(0, int(op.get("fields_total") or 0) - target_remaining),
                "unresolved_fields_after": unresolved_after,
            })
            final_build["metadata_operation"] = op
            self._refresh_workflow_fields(final_build)
            self.repo.save_build(final_build)
        except Exception as exc:
            build = self.repo.get_build(build_id)
            op = dict(build.get("metadata_operation") or {})
            op.update({"state": "failed", "finished_at": iso_now(), "error": str(exc)})
            build["metadata_operation"] = op
            build["status"] = "awaiting_review"
            build["stage"] = "review"
            build["error"] = None
            warnings = list(build.get("warnings") or [])
            warnings.append(f"Metadata retry failed: {exc}")
            build["warnings"] = warnings[-200:]
            self._refresh_workflow_fields(build)
            self.repo.save_build(build)


    def rerun_metadata_enrichment(self, build_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Start one enrichment pass, or a chain of up to ``passes`` passes.

        The build stays open for review while passes run. A chain ends early once a
        pass changes nothing, because a further pass could only repeat itself.
        """
        build = self.repo.get_build(build_id)
        if build.get("status") in {"queued", "running"}:
            raise ValueError("Wait for the active corpus operation to finish before starting metadata enrichment.")
        _validate_execution_budget(request)
        limit = max(1, int(settings.enrichment_max_concurrent_runs))
        working = self.active_enrichment_runs()
        if working >= limit:
            raise ValueError(f"{working} metadata enrichment run(s) are already working (the limit is {limit}). Wait for one to finish.")
        scope = str(request.get("scope") or "all")
        groups = self._schema_of_build(build).family_fields()
        families = [str(v) for v in request.get("families") or [] if str(v) in groups] or list(groups)
        passes = max(1, min(MAX_PASSES, int(request.get("passes") or 1)))
        record_ids = [str(value) for value in request.get("record_ids") or [] if str(value)]
        if scope == "selected" and not record_ids:
            raise ValueError("Select at least one record for selected-record enrichment.")
        indices = _enrichment_pass_indices(self.repo.load_records(build_id), scope, record_ids)
        if not indices:
            raise ValueError("No records match the selected metadata enrichment scope.")
        public_request = {k: v for k, v in request.items() if k not in {"api_key", "_review_provider"}}
        operation_id = f"metadata-enrichment-{uuid.uuid4().hex[:10]}"
        run = {
            "operation_id": operation_id, "kind": "metadata_enrichment_rerun", "state": "queued",
            "started_at": iso_now(), "finished_at": None,
            "records_total": len(indices), "records_processed": 0, "records_unchanged": 0, "records_enriched": 0,
            "records_disputed": 0, "records_reopened": 0, "records_skipped": 0, "fields_replaced": 0, "fields_kept": 0,
            "provider_profile_id": public_request.get("provider_profile_id"),
            "provider": request.get("provider") or build.get("provider"), "model": request.get("model") or build.get("model"),
            "families": families, "scope": scope,
            "passes_requested": passes, "passes_completed": 0, "current_pass": 0, "converged": False, "pass_results": [],
            "record_ids": record_ids, "active_tasks": [], "current_record_id": None, "current_task": None,
        }
        for key in ("recheck_rate", "iaa_rate"):
            if request.get(key) is not None:
                build["experiment"] = {**(build.get("experiment") or {}), key: float(request[key])}
        runs = list(build.get("metadata_enrichment_runs") or []) + [run.copy()]
        build["metadata_enrichment_runs"] = runs[-30:]
        build["metadata_operation"] = run.copy()
        self.repo.save_build(build)
        self._update(build_id, status="running", stage="metadata_enrichment_rerun", error=None, resumable=False, metadata_operation=run)
        # The operation id tags every ledger event this run writes, so runs never blur together.
        self._executor.submit(self._metadata_enrichment_rerun_worker, build_id, {**request, "run_id": operation_id}, operation_id, scope, families, passes)
        return self.repo.get_build(build_id)


    def _share_generalizable_learning(self, build_id: str) -> None:
        """Offer this build's reviewer-confirmed conventions to the cross-build store."""
        build = self.repo.get_build(build_id)
        if build.get("editorial_memory_reset_at"):
            return
        local = {field: value for field, value in self._editorial_memory(build_id).get("conventions", {}).items() if value.get("scope") != "global"}
        self._global_learning.observe(build_id, local)


    def _merge_enrichment_candidate(
        self, live: dict[str, Any], candidate: dict[str, Any], families: list[str], run_id: str, request: dict[str, Any], profile: dict[str, Any],
        schema: MetadataSchema | None = None, pass_number: int = 1,
    ) -> dict[str, Any]:
        """Fold one pass's candidate into the live record. Human-owned fields are never touched."""
        groups = (schema or default_schema()).family_fields()

        def candidate_id(field: str, value: Any, source: str, model: str = "", pass_no: int | None = None) -> str:
            payload = json.dumps(
                {"field": field, "value": value, "source": source, "model": model, "run_id": run_id, "pass": pass_no},
                ensure_ascii=False, sort_keys=True, default=str,
            )
            return "cand-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        live_status = live.setdefault("metadata_field_status", {})
        cand_status = candidate.get("metadata_field_status") if isinstance(candidate.get("metadata_field_status"), dict) else {}
        cand_evidence = candidate.get("metadata_evidence") if isinstance(candidate.get("metadata_evidence"), dict) else {}
        live_evidence = live.setdefault("metadata_evidence", {})
        added: list[str] = []
        replaced: list[dict[str, Any]] = []
        kept: list[str] = []
        disputes: list[dict[str, Any]] = []
        history_disputes: list[dict[str, Any]] = []
        informational: list[dict[str, Any]] = []
        known = {(d.get("field"), json.dumps(d.get("proposed"), sort_keys=True, default=str)) for d in live.get("metadata_disputes") or [] if isinstance(d, dict)}
        model_name = str(request.get("model") or "")

        for family in families:
            for field in groups[family]:
                new, old = candidate.get(field), live.get(field)
                old_info = live_status.get(field) if isinstance(live_status.get(field), dict) else {}
                new_info = cand_status.get(field) if isinstance(cand_status.get(field), dict) else {}
                if new in (None, "", []):
                    continue
                if str(old_info.get("status") or "") in HUMAN_OWNED_STATUSES:
                    informational.append(enrichment_informational_event(
                        "agreement" if same_value(old, new) else "protected_suggestion",
                        field,
                        run_id=run_id,
                        pass_number=pass_number,
                        model=model_name,
                        authoritative=old,
                        proposed=new,
                        confidence=new_info.get("confidence"),
                        reason=(
                            "The model agreed with the human-owned value."
                            if same_value(old, new)
                            else "The model proposed a different value, but the human-owned value remains authoritative."
                        ),
                    ))
                    continue
                if old in (None, "", []):
                    live[field] = new
                    live_status[field] = new_info
                    if field in cand_evidence:
                        live_evidence[field] = cand_evidence[field]
                    added.append(field)
                    continue
                if field in CONFIDENCE_FIELDS:
                    continue
                if same_value(old, new):
                    informational.append(enrichment_informational_event(
                        "agreement",
                        field,
                        run_id=run_id,
                        pass_number=pass_number,
                        model=model_name,
                        authoritative=old,
                        proposed=new,
                        confidence=new_info.get("confidence"),
                        reason="The model found no new supported value.",
                    ))
                    if field in cand_evidence:
                        live_evidence[field] = cand_evidence[field]
                    continue
                if (field, json.dumps(new, sort_keys=True, default=str)) in known:
                    informational.append(enrichment_informational_event(
                        "duplicate",
                        field,
                        run_id=run_id,
                        pass_number=pass_number,
                        model=model_name,
                        authoritative=old,
                        proposed=new,
                        confidence=new_info.get("confidence"),
                        reason="The model repeated an existing unresolved candidate.",
                    ))
                    continue
                # PR #83 permits a valid LLM proposal to occupy the record while
                # remaining pending human review. PR #81's generic resolver treats
                # an unresolved existing value as replaceable; doing that here would
                # discard the first unverified proposal. When both values are
                # pending LLM proposals, retain both for reviewer adjudication.
                both_pending_llm = (
                    old_info.get("verification_status") == "pending_review"
                    and new_info.get("verification_status") == "pending_review"
                    and (old_info.get("value_source") == "llm" or old_info.get("method") == "llm")
                    and (new_info.get("value_source") == "llm" or new_info.get("method") == "llm")
                )
                decision = "keep_both" if both_pending_llm else resolve_conflict(old_info, new_info)
                if decision == "replace":
                    replaced.append({"field": field, "previous": old, "value": new, "confidence": new_info.get("confidence")})
                    live[field] = new
                    live_status[field] = new_info
                    if field in cand_evidence:
                        live_evidence[field] = cand_evidence[field]
                elif decision == "keep_existing":
                    kept.append(field)
                else:
                    known.add((field, json.dumps(new, sort_keys=True, default=str)))
                    existing_source = (
                        "llm"
                        if (
                            old_info.get("verification_status") == "pending_review"
                            and (old_info.get("value_source") == "llm" or old_info.get("method") == "llm")
                        )
                        else "current"
                    )
                    existing_model = str(old_info.get("model") or "")
                    existing_pass = old_info.get("pass") if isinstance(old_info.get("pass"), int) else None
                    existing_candidate = {
                        "candidate_id": candidate_id(field, old, existing_source, existing_model, existing_pass),
                        "value": old, "source": existing_source, "model": existing_model or None,
                        "run_id": old_info.get("run_id"), "pass": existing_pass,
                        "created_at": old_info.get("updated_at") or old_info.get("created_at"),
                    }
                    if isinstance(old_info.get("confidence"), (int, float)):
                        existing_candidate["confidence"] = old_info.get("confidence")
                    if old_info.get("verification_status"):
                        existing_candidate["verification_status"] = old_info.get("verification_status")

                    model_name = str(request.get("model") or new_info.get("model") or "")
                    candidate_entry = {
                        "candidate_id": candidate_id(field, new, "llm", model_name, pass_number),
                        "value": new, "source": "llm", "model": model_name or None,
                        "run_id": run_id, "pass": pass_number, "created_at": iso_now(),
                    }
                    if isinstance(new_info.get("confidence"), (int, float)):
                        candidate_entry["confidence"] = new_info.get("confidence")
                    if new_info.get("verification_status"):
                        candidate_entry["verification_status"] = new_info.get("verification_status")

                    prior_dispute = next(
                        (item for item in live.get("metadata_disputes") or []
                         if isinstance(item, dict) and item.get("field") == field and not item.get("resolved_at")),
                        None,
                    )
                    if prior_dispute is not None:
                        fallback_existing = dict(existing_candidate)
                        fallback_existing["value"] = prior_dispute.get("existing")
                        candidates = list(prior_dispute.get("candidates") or [fallback_existing])
                        if not any(same_value(item.get("value"), new) for item in candidates if isinstance(item, dict)):
                            candidates.append(candidate_entry)
                            prior_dispute["candidates"] = candidates[-12:]
                            prior_dispute["proposed"] = new
                            prior_dispute["run_id"] = run_id
                            prior_dispute["pass"] = pass_number
                            prior_dispute["updated_at"] = iso_now()
                            history_disputes.append(json.loads(json.dumps(prior_dispute)))
                    else:
                        dispute = {
                            "field": field, "existing": old, "proposed": new,
                            "candidates": [existing_candidate, candidate_entry],
                            "confidence": new_info.get("confidence"), "reason": new_info.get("reason"),
                            "run_id": run_id, "pass": pass_number, "created_at": iso_now(),
                        }
                        disputes.append(dispute)
                        history_disputes.append(json.loads(json.dumps(dispute)))
                    live_status[field] = {**old_info, "status": "unresolved", "reason_code": "llm_disagreement", "reason": "A later metadata enrichment pass proposed a different value and neither was confident enough to decide."}
        live["metadata_disputes"] = (list(live.get("metadata_disputes") or []) + disputes)[-100:]
        outcome = "enriched" if added or replaced else "disputed" if history_disputes else "unchanged"
        history = list(live.get("metadata_enrichment_history") or [])
        history.append({
            "run_id": run_id, "pass": pass_number, "at": iso_now(), "state": "complete", "outcome": outcome, "added_fields": added,
            "replaced": replaced, "kept_existing": kept, "disputes": history_disputes,
            "informational": informational,
            "provider_profile_id": request.get("provider_profile_id"), "model": request.get("model"),
        })
        live["metadata_enrichment_history"] = history[-30:]
        activity = dict(live.get("activity") or {})
        activity["llm_review_count"] = int(activity.get("llm_review_count") or 0) + 1
        activity["enrichment_pass_count"] = int(activity.get("enrichment_pass_count") or 0) + 1
        activity["last_llm_reviewed_at"] = iso_now()
        activity["last_enrichment_at"] = activity["last_llm_reviewed_at"]
        activity["last_enrichment_provider"] = request.get("provider")
        activity["last_enrichment_model"] = request.get("model")
        live["activity"] = activity
        if added or replaced or history_disputes:
            live["review_disposition"] = "pending"
            live["accepted"] = False
            live["rejected"] = False
            live["needs_review"] = True
            live["review_reason"] = "Metadata enrichment added, replaced, or disputed metadata; review the highlighted changes."
            _sync_record_metadata_state(live, profile)
        return {"outcome": outcome, "added": len(added), "replaced": len(replaced), "kept": len(kept), "disputed": len(history_disputes)}


    def _run_enrichment_pass(
        self, build_id: str, request: dict[str, Any], run_id: str, scope: str, families: list[str],
        on_progress: Callable[[dict[str, int], int], None], pass_number: int = 1,
    ) -> dict[str, int]:
        """Run one pass over the records currently in scope, merging results into live state."""
        build = self.repo.get_build(build_id)
        manifest = build.get("manifest") or {}
        profile = self._profile_of_build(build)
        snapshot = self.repo.load_records(build_id)
        indices = _enrichment_pass_indices(snapshot, scope, [str(value) for value in request.get("record_ids") or []])
        priority = [str(value) for value in build.get("metadata_priority_record_ids") or []]
        priority_indices = [index for value in priority for index, row in enumerate(snapshot) if str(row.get("record_id") or "") == value and index in indices]
        indices = priority_indices + [index for index in indices if index not in priority_indices]
        max_workers = max(1, min(16, int(request.get("max_concurrent_requests") or 1)))
        totals: Counter[str] = Counter()
        pass_schema = self._schema_for(build_id)
        epoch_at_start = self._provider_epoch.get(build_id, 0)
        provider_keys = ("provider", "model", "base_url", "api_key", "generation", "provider_profile_id", "review_provider_profile_id", "_review_provider")

        def effective_request() -> dict[str, Any]:
            """This run's request, with the provider the reviewer switched to since it started, if they did.

            A switch applies to records not yet started; requests already in flight finish on the old model.
            Each event in the ledger names the model that actually answered, so the metrics show both.
            """
            if self._provider_epoch.get(build_id, 0) == epoch_at_start:
                return request
            live = self._latest_runtime_request(build_id, request)
            return {**request, **{key: live[key] for key in provider_keys if key in live}}

        def operation_stage_callback(record: dict[str, Any], task_name: str, state: str, _error: str | None) -> None:
            self._update_enrichment_operation_task(
                build_id,
                run_id,
                str(record.get("record_id") or ""),
                task_name,
                state,
            )

        def candidate_for(index: int) -> tuple[dict[str, Any], dict[str, Any]]:
            candidate = json.loads(json.dumps(snapshot[index]))
            reset_fields = {
                field
                for family in families
                for field in pass_schema.family_fields()[family]
            }
            reset_fields_for_evaluation(
                candidate,
                reset_fields,
                schema=pass_schema,
                discard_history=True,
                method="metadata_rerun_worker",
            )
            for family in families:
                candidate.setdefault("metadata_stage_status", {}).pop(family, None)
                candidate.setdefault("metadata_execution_ledger", {}).pop(family, None)
            neighbors = {
                "previous_text": str(snapshot[index - 1].get("text") or "") if index > 0 else "",
                "next_text": str(snapshot[index + 1].get("text") or "") if index + 1 < len(snapshot) else "",
            }
            request_used = {**effective_request(), "families": families, "_interactive_provider_override": True}
            return self._enrich_record(
                candidate,
                manifest,
                request_used,
                build_id=build_id,
                previous_text=neighbors["previous_text"],
                next_text=neighbors["next_text"],
                stage_callback=operation_stage_callback,
            ), request_used

        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="pdf-corpus-meta-enrich") as pool:
            futures = {pool.submit(candidate_for, index): index for index in indices}
            for future in as_completed(futures):
                if self._cancelled(build_id):
                    for outstanding in futures:
                        outstanding.cancel()
                    break
                index = futures[future]
                record_id = str(snapshot[index].get("record_id") or "")
                try:
                    candidate, request_used = future.result()
                except Exception as exc:
                    candidate = None
                    request_used = request
                    failure = {"run_id": run_id, "at": iso_now(), "state": "failed", "error": str(exc)}
                # Merge into the live copy, never the snapshot: the reviewer may have
                # edited this or any other record while the model was thinking.
                result: dict[str, Any]
                with self._lock:
                    live_records = self.repo.load_records(build_id)
                    live = next((row for row in live_records if str(row.get("record_id") or "") == record_id), None)
                    if live is None:
                        continue
                    if candidate is None:
                        live["metadata_enrichment_history"] = (list(live.get("metadata_enrichment_history") or []) + [failure])[-30:]
                        result = {"outcome": "failed"}
                    elif live.get("text") != snapshot[index].get("text"):
                        result = {"outcome": "skipped"}
                    else:
                        was_accepted = str(live.get("review_disposition") or "pending") == "accepted"
                        result = self._merge_enrichment_candidate(live, candidate, families, run_id, request_used, profile, schema=pass_schema, pass_number=pass_number)
                        if was_accepted and result["outcome"] != "unchanged":
                            totals["records_reopened"] += 1
                    self.repo.save_records(build_id, live_records)
                totals["records_processed"] += 1
                for key, name in (("added", "fields_added"), ("replaced", "fields_replaced"), ("kept", "fields_kept"), ("disputed", "fields_disputed")):
                    totals[name] += result.get(key, 0)
                totals[f"records_{result['outcome']}"] += 1
                on_progress(dict(totals), len(indices))
        return dict(totals)


    def _update_enrichment_operation_task(
        self, build_id: str, operation_id: str, record_id: str, task_name: str, state: str,
    ) -> None:
        """Expose the active rerun family without changing the aggregate counters."""
        with self._lock:
            build = self.repo.get_build(build_id)
            operation = dict(build.get("metadata_operation") or {})
            if operation.get("operation_id") != operation_id:
                return
            active = [
                item for item in operation.get("active_tasks") or []
                if isinstance(item, dict)
                and not (str(item.get("record_id") or "") == record_id and str(item.get("task") or "") == task_name)
            ]
            if state == "running":
                active.append({
                    "record_id": record_id,
                    "task": task_name,
                    "state": state,
                    "started_at": iso_now(),
                })
            operation["active_tasks"] = active[:32]
            current = active[0] if active else {}
            operation["current_record_id"] = current.get("record_id")
            operation["current_task"] = current.get("task")
            self._update(build_id, metadata_operation=operation)


    def _metadata_enrichment_rerun_worker(self, build_id: str, request: dict[str, Any], operation_id: str, scope: str, families: list[str], passes: int) -> None:
        op = dict(self.repo.get_build(build_id).get("metadata_operation") or {})
        try:
            counter_keys = ("records_processed", "records_enriched", "records_disputed", "records_unchanged", "records_skipped", "records_reopened", "fields_replaced", "fields_kept")
            for pass_number in range(1, passes + 1):
                if self._cancelled(build_id):
                    op["state"] = "cancelled"
                    break
                # Each pass starts from what reviewers and earlier passes settled,
                # and the editorial memory it reads reflects both.
                self._share_generalizable_learning(build_id)
                before = {key: int(op.get(key) or 0) for key in counter_keys}

                def on_progress(totals: dict[str, int], pass_total: int, pass_number: int = pass_number, before: dict[str, int] = before) -> None:
                    op.update({key: before[key] + totals.get(key, 0) for key in counter_keys})
                    live_operation = self.repo.get_build(build_id).get("metadata_operation")
                    if isinstance(live_operation, dict):
                        for key in ("active_tasks", "current_record_id", "current_task"):
                            op[key] = live_operation.get(key)
                    op.update({"state": "running", "current_pass": pass_number, "records_total": max(int(op.get("records_total") or 0), pass_total)})
                    fraction = ((pass_number - 1) + totals.get("records_processed", 0) / max(1, pass_total)) / passes
                    self._update(build_id, metadata_operation=dict(op), progress=min(0.995, 0.78 + 0.20 * fraction))

                op.update({"state": "running", "current_pass": pass_number})
                totals = self._run_enrichment_pass(build_id, request, operation_id, scope, families, on_progress, pass_number=pass_number)
                changed = totals.get("fields_added", 0) + totals.get("fields_replaced", 0) + totals.get("fields_disputed", 0)
                op["passes_completed"] = pass_number
                op["pass_results"] = list(op.get("pass_results") or []) + [{"pass": pass_number, "changed_fields": changed, **totals}]
                self._update(build_id, metadata_operation=dict(op))
                if self._cancelled(build_id):
                    op["state"] = "cancelled"
                    break
                if changed == 0:
                    # A pass that changes nothing has converged; more would repeat it.
                    op["converged"] = True
                    break
            self._share_generalizable_learning(build_id)
            with self._lock:
                final = self._rewrite_and_validate(build_id, self.repo.load_records(build_id))
                op.update({"state": op["state"] if op.get("state") == "cancelled" else "completed", "finished_at": iso_now()})
                final["metadata_operation"] = op
                final["metadata_enrichment_runs"] = [({**r, **op} if r.get("operation_id") == operation_id else r) for r in final.get("metadata_enrichment_runs") or []]
                final.update({"status": "awaiting_review", "stage": "review", "progress": 1.0, "cancel_requested": False})
                self._cancel.discard(build_id)
                self._refresh_workflow_fields(final)
                self.repo.save_build(final)
        except Exception as exc:
            build = self.repo.get_build(build_id)
            op.update({"state": "failed", "finished_at": iso_now(), "error": str(exc)})
            build.update({"metadata_operation": op, "status": "awaiting_review", "stage": "review", "cancel_requested": False})
            self._cancel.discard(build_id)
            self.repo.save_build(build)


    @_serialize_record_mutation
    def rerun_metadata(self, build_id: str, record_id: str, request: dict[str, Any]) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        records = self.repo.load_records(build_id)
        target = next((record for record in records if record.get("record_id") == record_id), None)
        if target is None:
            raise KeyError(record_id)
        metadata_operation = build.get("metadata_operation")
        metadata_active = (
            str(build.get("stage") or "").startswith("metadata_enrichment")
            or (
                build.get("status") == "running"
                and isinstance(metadata_operation, dict)
                and metadata_operation.get("state") == "running"
            )
            or "metadata_priority_record_ids" in build
        )
        if metadata_active:
            _prepend_metadata_priority(build, record_id)
            feedback = list(build.get("metadata_review_feedback") or [])
            feedback.append({
                "record_id": record_id,
                "at": iso_now(),
                "source": "human_requeue",
                "human_decisions": list(target.get("metadata_decisions") or [])[-20:],
                "metadata": {
                    key: target.get(key)
                    for fields in self._schema_for(build_id).family_fields().values()
                    for key in fields
                    if key in target
                },
            })
            build["metadata_review_feedback"] = feedback[-100:]
            self.repo.save_build(build)
            return build
        requested_families = request.get("families")
        rerun_groups = self._schema_for(build_id).family_fields()
        families = [str(value) for value in requested_families or [] if str(value) in rerun_groups]
        if not families:
            families = list(rerun_groups)
        # Clear only non-authoritative fields in the selected families. Human,
        # inherited, and deterministic assertions survive reruns.
        schema = self._schema_for(build_id)
        migrate_record_assertions(target, schema)
        fields_to_reset: set[str] = set()
        for family in families:
            for key in rerun_groups[family]:
                assertion = current_assertion_by_name(target, key)
                if assertion is not None and (
                    assertion.authority_status in {"human_confirmed", "human_override"}
                    or assertion.derivation_method in {"inherited", "deterministic"}
                ):
                    continue
                fields_to_reset.add(key)
            target.setdefault("metadata_stage_status", {}).pop(family, None)
            target.setdefault("metadata_stage_results", {}).pop(family, None)
            target.setdefault("metadata_execution_ledger", {}).pop(family, None)
        reset_fields_for_evaluation(
            target,
            fields_to_reset,
            schema=schema,
            discard_history=False,
            method="human_requeue",
            reason="Reviewer requested a fresh metadata evaluation.",
        )
        rerun_request = dict(request)
        rerun_request["families"] = families
        rerun_request["_interactive_provider_override"] = True
        index = records.index(target)
        self._enrich_record(
            target,
            build.get("manifest") or {},
            rerun_request,
            previous_text=str(records[index - 1].get("text") or "") if index > 0 else "",
            next_text=str(records[index + 1].get("text") or "") if index + 1 < len(records) else "",
            build_id=build_id,
        )
        self._rewrite_and_validate(build_id, records)
        return target
