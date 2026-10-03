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

from __future__ import annotations

import copy
import re
import threading
import time
import uuid
from typing import Any

from . import operation_events
from .chroma_store import ChromaStore
from .concurrency import (
    CapacityCancelled,
    CapacityPermit,
    capacity_coordinator,
    provider_capacity_key,
    provider_limit,
)
from .config import settings
from .job_state import (
    JobPayloadList,
    PersistentJobStateMixin,
    error_details,
    iso_now,
    store_job_error,
)
from .llm_tools import run_rag_grade
from .models import RAGGradeRequest, RAGRunRequest
from .persistence import job_repository
from .pipelines.store import pipeline_store
from .pipelines.tracing import build_research_trace
from .rag import extract_evidence_ids, run_rag_pipeline, strip_evidence_markers


def _optional_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None and str(value).strip() else None
    except (TypeError, ValueError):
        return None


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


class RAGJobManager(PersistentJobStateMixin):
    JOB_TYPE = "rag"
    """
    RAG scheduling uses provider-profile concurrency gates.

    * Ollama retains a runtime GPU-oriented gate and also receives the selected
      profile's requested maximum.
    * OpenAI-compatible / FreeLLM jobs receive independent daemon threads but
      wait behind the selected provider profile's max_concurrent_requests gate.
      Large limits preserve high parallelism without forcing unrelated provider
      profiles to share one global bottleneck.
    """

    def __init__(
        self,
        store: ChromaStore,
        ollama_max_concurrent: int = 1,
    ) -> None:
        self._store = store
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._ollama_max_concurrent = max(1, int(ollama_max_concurrent))
        capacity_coordinator.set_limit(
            "ollama_runtime", "global", self._ollama_max_concurrent
        )
        self._threads: dict[str, threading.Thread] = {}
        self._start_persistent_state()

    def set_ollama_limit(self, limit: int) -> dict[str, Any]:
        value = max(1, min(32, int(limit)))
        with self._lock:
            self._ollama_max_concurrent = value
        capacity_coordinator.set_limit("ollama_runtime", "global", value)
        return self.concurrency_status()

    def concurrency_status(self) -> dict[str, Any]:
        with self._lock:
            openai_active = sum(
                1
                for job in self._jobs.values()
                if job.get("provider") == "openai"
                and job.get("status") in {"queued", "running", "cancelling"}
            )
            ollama_limit = self._ollama_max_concurrent
        ollama = capacity_coordinator.snapshot(
            "ollama_runtime", "global", limit=ollama_limit
        )
        provider_active = {
            snapshot.key: snapshot.active
            for snapshot in capacity_coordinator.snapshots()
            if snapshot.resource == "provider_generation" and snapshot.active
        }
        return {
            "openai_mode": "shared_provider_profile_gate",
            "openai_active": openai_active,
            "provider_profile_active": provider_active,
            "ollama_max_concurrent": ollama_limit,
            "ollama_active": ollama.active,
            "ollama_waiting": ollama.waiting,
        }

    def create(self, body: RAGRunRequest, *, owner: str | None = None) -> dict[str, Any]:
        job_id = str(uuid.uuid4())
        request_summary = body.model_dump(
            exclude={"api_key", "auto_grade_api_key", "selected_evidence"}
        )
        request_summary["selected_evidence"] = [
            {
                "collection": item.collection,
                "chroma_id": item.chroma_id,
                "record_id": (item.record or {}).get("record_id"),
                "work": (item.record or {}).get("work"),
            }
            for item in body.selected_evidence
        ]
        requested_ollama_limit = (
            body.ollama_concurrency_limit
            if body.provider == "ollama"
            else None
        )

        with self._lock:
            if requested_ollama_limit is not None:
                self._ollama_max_concurrent = max(
                    1,
                    min(32, int(requested_ollama_limit)),
                )
                capacity_coordinator.set_limit(
                    "ollama_runtime", "global", self._ollama_max_concurrent
                )

            profile_limit = provider_limit(
                body.max_concurrent_requests, default=32, maximum=64
            )
            scheduling = {
                "mode": "provider_profile_and_ollama_gate" if body.provider == "ollama" else "provider_profile_gate",
                "limit": profile_limit,
                "profile_id": body.provider_profile_id,
            }
            if body.provider == "ollama":
                scheduling["ollama_global_limit"] = self._ollama_max_concurrent
            job = {
                "id": job_id,
                "type": "rag",
                "mode": "rag",
                "provider": body.provider,
                "model": body.model,
                "provider_profile_id": body.provider_profile_id,
                "source_collection": body.source_collection,
                "prompt": body.prompt,
                "owner": owner,
                "status": "queued",
                "created_at": iso_now(),
                "started_at": None,
                "finished_at": None,
                "total": 9 if body.auto_grade else 8,
                "completed": 0,
                "failed": 0,
                "cancel_requested": False,
                "cancel_requested_at": None,
                "stage": "queued",
                "stage_detail": (
                    f"Waiting for provider/Ollama capacity "
                    f"(profile limit {profile_limit}; global Ollama limit {self._ollama_max_concurrent})"
                    if body.provider == "ollama"
                    else (
                        "Waiting for provider capacity if needed "
                        f"(limit {max(1, min(64, int(body.max_concurrent_requests or 32)))})"
                    )
                ),
                "request": request_summary,
                "scheduling": scheduling,
                "events": [{
                    "timestamp": iso_now(),
                    "stage": "queued",
                    "current": 0,
                    "total": 1,
                    "detail": (
                        f"RAG job queued for Ollama; profile limit {profile_limit}; "
                        f"global limit {self._ollama_max_concurrent}"
                        if body.provider == "ollama"
                        else f"RAG job submitted with provider concurrency limit "
                             f"{max(1, min(64, int(body.max_concurrent_requests or 32)))}"
                    ),
                }],
                "result": None,
            }
            self._jobs[job_id] = job
        self._persist_job(job_id)

        # Each RAG job receives its own daemon thread. Provider-profile gates
        # control actual concurrent pipeline execution; Ollama also retains the
        # local GPU concurrency gate.
        thread = threading.Thread(
            target=self._run,
            args=(job_id, body),
            daemon=True,
            name=f"derridai-rag-{body.provider}-{job_id[:8]}",
        )
        with self._lock:
            self._threads[job_id] = thread
        thread.start()
        return self.get(job_id)

    @staticmethod
    def _persist_response_provenance(
        result: dict[str, Any],
        *,
        run_id: str,
        response_record_id: str,
        owner: str | None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Persist only citation-marked sentences as conservatively derived claims."""
        from .provenance_memory import (
            GeneratedClaim,
            SupportBinding,
            persist_generated_claim,
            persist_support_binding,
        )

        # Persist support from the structured/raw generation before citation
        # rendering removes evidence markers. Fall back to the rendered answer
        # only for historical or externally supplied results without raw_answer.
        answer = str(result.get("raw_answer") or result.get("answer") or "")
        evidence_by_id = {
            str(item.get("evidence_id") or ""): item
            for item in result.get("evidence") or []
            if isinstance(item, dict) and item.get("evidence_id")
        }
        claims: list[dict[str, Any]] = []
        bindings: list[dict[str, Any]] = []
        for match in re.finditer(r"(?P<sentence>[^.!?]+(?:[.!?]|$))", answer):
            sentence = match.group("sentence").strip()
            evidence_ids = extract_evidence_ids(sentence)
            if not evidence_ids:
                continue
            claim = persist_generated_claim(GeneratedClaim(
                run_id=run_id,
                response_record_id=response_record_id or None,
                owner=owner,
                claim_text=strip_evidence_markers(sentence),
                answer_start=match.start(),
                answer_end=match.end(),
            ))
            claims.append(claim.model_dump(mode="json"))
            for evidence_id in evidence_ids:
                item = evidence_by_id.get(evidence_id) or {}
                record = item.get("record") if isinstance(item.get("record"), dict) else {}
                if not record.get("record_id"):
                    continue
                source_document_id = str(
                    record.get("source_document_id") or record.get("source_asset_id") or ""
                ).strip()
                source_spans = []
                if source_document_id:
                    from .provenance_memory import EvidenceSpan

                    for span in record.get("source_spans") or []:
                        if not isinstance(span, dict):
                            continue
                        unit_ids = list(span.get("source_unit_ids") or [])
                        for key in ("source_unit_id", "block_id"):
                            if span.get(key):
                                unit_ids.append(span[key])
                        source_spans.append(EvidenceSpan(
                            source_document_id=source_document_id,
                            source_unit_ids=list(
                                dict.fromkeys(
                                    str(value)
                                    for value in unit_ids
                                    if str(value).strip()
                                )
                            ),
                            physical_page_start=_optional_int(
                                _first_present(span.get("pdf_page"), span.get("page"))
                            ),
                            physical_page_end=_optional_int(
                                _first_present(span.get("pdf_page"), span.get("page"))
                            ),
                            printed_page_start=span.get("printed_page_label"),
                            printed_page_end=span.get("printed_page_label"),
                            character_start=_optional_int(
                                _first_present(span.get("char_start"), span.get("start"))
                            ),
                            character_end=_optional_int(
                                _first_present(span.get("char_end"), span.get("end"))
                            ),
                        ))
                binding = persist_support_binding(SupportBinding(
                    claim_id=claim.claim_id,
                    owner=owner,
                    record_id=str(record["record_id"]),
                    record_revision=int(record.get("record_revision") or 1),
                    source_document_id=source_document_id or None,
                    source_spans=source_spans,
                    relation="supports",
                    citation={
                        "inline": item.get("inline_citation"),
                        "full": item.get("full_citation"),
                        "evidence_marker": evidence_id,
                    },
                ))
                bindings.append(binding.model_dump(mode="json"))
        return {"claims": claims, "support_bindings": bindings}

    def _acquire_ollama_slot(self, job_id: str) -> CapacityPermit | None:
        with self._lock:
            limit = self._ollama_max_concurrent

        def cancelled() -> bool:
            with self._lock:
                job = self._jobs.get(job_id)
                return bool(
                    job is None
                    or job.get("cancel_requested")
                    or job.get("status") == "cancelled"
                )

        def waiting(snapshot) -> None:  # noqa: ANN001 - operational callback
            with self._lock:
                job = self._jobs.get(job_id)
                if job is None:
                    return
                job["status"] = "queued"
                job["stage"] = "queued"
                job["stage_detail"] = (
                    f"Waiting for Ollama slot: {snapshot.active} active / "
                    f"{snapshot.limit} allowed"
                )
                job["events"].append({
                    "timestamp": iso_now(),
                    "stage": "waiting_for_ollama_slot",
                    "current": snapshot.active,
                    "total": snapshot.limit,
                    "detail": job["stage_detail"],
                })

        try:
            permit = capacity_coordinator.acquire(
                "ollama_runtime",
                "global",
                limit,
                cancelled=cancelled,
                on_wait=waiting,
                priority="foreground",
            )
        except CapacityCancelled:
            return None

        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job["scheduling"]["ollama_global_limit"] = permit.limit
                job["scheduling"]["ollama_active_when_started"] = permit.active_when_acquired
                job["scheduling"]["ollama_wait_ms"] = int(
                    round(permit.waited_seconds * 1000)
                )
                job["events"].append({
                    "timestamp": iso_now(),
                    "stage": "ollama_slot_acquired",
                    "current": permit.active_when_acquired,
                    "total": permit.limit,
                    "detail": (
                        f"Ollama execution slot acquired "
                        f"({permit.active_when_acquired}/{permit.limit})"
                    ),
                })
        return permit

    def _release_ollama_slot(self, job_id: str, permit: CapacityPermit) -> None:
        permit.release()
        snapshot = capacity_coordinator.snapshot(
            "ollama_runtime", "global", limit=permit.limit
        )
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job["events"].append({
                    "timestamp": iso_now(),
                    "stage": "ollama_slot_released",
                    "current": snapshot.active,
                    "total": permit.limit,
                    "detail": (
                        f"Ollama execution slot released "
                        f"({snapshot.active}/{permit.limit} active)"
                    ),
                })

    @staticmethod
    def _provider_key(body: RAGRunRequest) -> str:
        return provider_capacity_key(
            provider_profile_id=body.provider_profile_id,
            provider=body.provider,
            base_url=body.base_url,
            model=body.model,
        )

    def _acquire_provider_slot(self, job_id: str, body: RAGRunRequest) -> CapacityPermit | None:
        key = self._provider_key(body)
        limit = provider_limit(body.max_concurrent_requests, default=32, maximum=64)

        def cancelled() -> bool:
            with self._lock:
                job = self._jobs.get(job_id)
                return bool(
                    job is None
                    or job.get("cancel_requested")
                    or job.get("status") == "cancelled"
                )

        def waiting(snapshot) -> None:  # noqa: ANN001 - operational callback
            with self._lock:
                job = self._jobs.get(job_id)
                if job is None:
                    return
                job["status"] = "queued"
                job["stage"] = "queued"
                job["stage_detail"] = (
                    f"Waiting for provider slot: {snapshot.active} active / "
                    f"{snapshot.limit} allowed"
                )

        try:
            permit = capacity_coordinator.acquire(
                "provider_generation",
                key,
                limit,
                cancelled=cancelled,
                on_wait=waiting,
                priority="foreground",
            )
        except CapacityCancelled:
            return None

        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job["scheduling"]["provider_wait_ms"] = int(
                    round(permit.waited_seconds * 1000)
                )
                job["scheduling"]["provider_active_when_started"] = permit.active_when_acquired
                job["scheduling"]["provider_limit"] = permit.limit
        return permit

    def _run(self, job_id: str, body: RAGRunRequest) -> None:
        ollama_permit: CapacityPermit | None = None
        provider_permit: CapacityPermit | None = None
        try:
            # Every profile receives its own concurrency gate, including Ollama.
            # Local Ollama work then passes through the process-wide GPU gate as
            # a second constraint. This makes a researcher profile's max value
            # authoritative without allowing one profile to raise the global cap.
            provider_permit = self._acquire_provider_slot(job_id, body)
            if provider_permit is None:
                with self._lock:
                    job = self._jobs[job_id]
                    job["status"] = "cancelled"
                    job["finished_at"] = iso_now()
                    job["stage_detail"] = "Cancelled while waiting for provider slot"
                return

            if body.provider == "ollama":
                ollama_permit = self._acquire_ollama_slot(job_id)
                if ollama_permit is None:
                    with self._lock:
                        job = self._jobs[job_id]
                        if not job["finished_at"]:
                            job["status"] = "cancelled"
                            job["finished_at"] = iso_now()
                            job["stage_detail"] = "Cancelled while waiting for Ollama slot"
                            job["events"].append({
                                "timestamp": job["finished_at"],
                                "stage": "cancelled",
                                "current": job["completed"],
                                "total": job["total"],
                                "detail": job["stage_detail"],
                            })
                    return

            with self._lock:
                job = self._jobs[job_id]
                if job["cancel_requested"] or job["status"] == "cancelled":
                    if not job["finished_at"]:
                        job["status"] = "cancelled"
                        job["finished_at"] = iso_now()
                        job["events"].append({
                            "timestamp": job["finished_at"],
                            "stage": "cancelled",
                            "current": job["completed"],
                            "total": job["total"],
                            "detail": "Cancelled before execution began",
                        })
                    return
                job["status"] = "running"
                job["started_at"] = iso_now()
                job["stage"] = "starting"
                job["stage_detail"] = (
                    "RAG pipeline started"
                    if body.provider == "ollama"
                    else "RAG pipeline started in provider-profile concurrency slot"
                )
                job["events"].append({
                    "timestamp": job["started_at"],
                    "stage": "running",
                    "current": job["completed"],
                    "total": job["total"],
                    "detail": job["stage_detail"],
                })

            stage_order = {
                "query_metadata": 0,
                "retrieval": 1,
                "deduplicate": 2,
                "rerank": 3,
                "context": 4,
                "generation": 5,
                "bind_sources": 6,
                "response_cache": 7,
                "auto_grade": 8,
            }

            def progress(stage: str, current: int, total: int, detail: str) -> None:
                with self._lock:
                    job = self._jobs[job_id]
                    job["stage"] = stage
                    job["stage_detail"] = detail
                    base = stage_order.get(stage, 0)
                    stage_done = 1 if total and current >= total else 0
                    job["completed"] = min(job["total"] - 1, base + stage_done)
                    event = {
                        "timestamp": iso_now(),
                        "stage": stage,
                        "current": current,
                        "total": total,
                        "detail": detail,
                    }
                    if not job["events"] or (
                        job["events"][-1].get("stage"),
                        job["events"][-1].get("current"),
                        job["events"][-1].get("total"),
                        job["events"][-1].get("detail"),
                    ) != (stage, current, total, detail):
                        job["events"].append(event)

            def cancelled() -> bool:
                with self._lock:
                    return bool(self._jobs[job_id]["cancel_requested"])

            job_owner = str(self._jobs[job_id].get("owner") or "") or None

            def generation_delta(text: str) -> None:
                # Live draft only: never stored on the job, never persisted token by token.
                operation_events.note_generation_delta(job_id, text, owner=job_owner)

            try:
                result = run_rag_pipeline(
                    body,
                    self._store,
                    progress=progress,
                    cancelled=cancelled,
                    owner=job_owner,
                    on_generation_delta=generation_delta,
                )
                operation_events.note_generation_finished(job_id, owner=job_owner)
                cache_info = None
                cache_error = None
                if not cancelled():
                    progress(
                        "response_cache",
                        0,
                        1,
                        "Saving RAG answer to _response_cache",
                    )
                    try:
                        cache_info = self._store.cache_rag_response(
                            job_id=job_id,
                            request=body.model_dump(exclude={"api_key", "auto_grade_api_key"}),
                            result=result,
                            created_at=iso_now(),
                        )
                        result["response_cache"] = cache_info
                        progress(
                            "response_cache",
                            1,
                            1,
                            f"Saved {cache_info['record_id']} to _response_cache",
                        )
                    except Exception as exc:
                        cache_error = str(exc)
                        result.setdefault("warnings", []).append(
                            f"Response cache write failed: {cache_error}"
                        )
                        progress(
                            "response_cache",
                            1,
                            1,
                            f"Response cache write failed: {cache_error}",
                        )

                    # Durable Research memory is independent of the
                    # rebuildable response-cache projection.
                    response_id = str((cache_info or {}).get("record_id") or job_id)
                    try:
                        from .system_store import system_store
                        system_store.put_response_memory({
                            "response_id": response_id,
                            "owner": str(self._jobs[job_id].get("owner") or "") or None,
                            "question": str(result.get("prompt") or body.prompt),
                            "answer": str(result.get("answer") or ""),
                            "evidence": list(result.get("evidence") or []),
                            "provider": result.get("provider"),
                            "model": result.get("model"),
                            "created_at": iso_now(),
                        })
                        system_store.mark_semantic_memory_dirty(
                            "response_memory",
                            record_id=response_id,
                            reason="completed_research_response",
                        )
                    except Exception as memory_error:
                        result.setdefault("warnings", []).append(
                            f"Response memory persistence failed: {memory_error}"
                        )
                    try:
                        provenance = self._persist_response_provenance(
                            result,
                            run_id=job_id,
                            response_record_id=response_id,
                            owner=str(self._jobs[job_id].get("owner") or "") or None,
                        )
                        result["claim_provenance"] = provenance
                    except Exception as provenance_error:
                        result.setdefault("warnings", []).append(
                            f"Claim provenance persistence failed: {provenance_error}"
                        )

                auto_grade_result = None
                auto_grade_error = None
                if body.auto_grade and not cancelled():
                    auto_grade_started = time.perf_counter()
                    progress(
                        "auto_grade",
                        0,
                        1,
                        "Grading final RAG response",
                    )
                    try:
                        grade_provider = body.auto_grade_provider or body.provider
                        grade_model = body.auto_grade_model or body.model
                        grade_body = RAGGradeRequest(
                            question=str(result.get("prompt") or body.prompt),
                            answer=str(result.get("answer") or ""),
                            evidence=list(result.get("evidence") or []),
                            provider=grade_provider,
                            model=grade_model,
                            base_url=body.auto_grade_base_url or body.base_url,
                            api_key=(
                                body.auto_grade_api_key
                                if body.auto_grade_provider is not None
                                else body.api_key
                            ),
                            generation=body.auto_grade_generation or body.generation,
                            response_record_id=(
                                cache_info.get("record_id")
                                if isinstance(cache_info, dict)
                                else None
                            ),
                            generation_provider=body.provider,
                            generation_model=body.model,
                        )
                        grade_payload = None
                        grade_attempts = max(1, int(settings.rag_auto_grade_max_attempts))
                        for grade_attempt in range(1, grade_attempts + 1):
                            try:
                                grade_payload = run_rag_grade(
                                    grade_body,
                                    self._store,
                                    cancelled=cancelled,
                                )
                                break
                            except InterruptedError:
                                raise
                            except Exception as grade_exc:
                                failure = error_details(grade_exc)
                                message_lc = str(failure.get("message") or "").casefold()
                                transient = (
                                    failure.get("http_status") in {408, 425, 429, 500, 502, 503, 504}
                                    or "provider_error" in message_lc
                                    or "upstream" in message_lc
                                    or "temporarily unavailable" in message_lc
                                    or "retry time budget" in message_lc
                                )
                                if not transient or grade_attempt >= grade_attempts:
                                    raise
                                status_label = (
                                    f"HTTP {failure['http_status']}"
                                    if failure.get("http_status")
                                    else "provider error"
                                )
                                progress(
                                    "auto_grade",
                                    0,
                                    1,
                                    f"Grader temporarily unavailable ({status_label}); "
                                    f"retrying {grade_attempt + 1}/{grade_attempts}",
                                )
                                delay = max(0.1, float(settings.rag_auto_grade_retry_delay_seconds))
                                deadline = time.monotonic() + delay
                                while time.monotonic() < deadline:
                                    if cancelled():
                                        raise InterruptedError() from None
                                    time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))
                        if grade_payload is None:
                            raise RuntimeError("Auto-grade did not return a result.")
                        auto_grade_result = grade_payload.get("grade")
                        result["auto_grade"] = auto_grade_result
                        result["auto_grade_provider"] = grade_provider
                        result["auto_grade_model"] = grade_model
                        result["auto_grade_response_cache"] = grade_payload.get("response_cache")
                        if grade_payload.get("response_cache_error"):
                            result["auto_grade_response_cache_error"] = grade_payload["response_cache_error"]
                            result.setdefault("warnings", []).append(
                                "Auto-grade completed, but saving the grade to the response cache failed: "
                                + str(grade_payload["response_cache_error"])
                            )
                        result.setdefault("stages", []).append({
                            "name": "auto_grade",
                            "seconds": time.perf_counter() - auto_grade_started,
                            "detail": {
                                "provider": grade_provider,
                                "model": grade_model,
                                "overall": auto_grade_result.get("overall")
                                if isinstance(auto_grade_result, dict)
                                else None,
                            },
                        })
                        progress(
                            "auto_grade",
                            1,
                            1,
                            f"Auto-grade complete · overall {auto_grade_result.get('overall', '—')}/10"
                            if isinstance(auto_grade_result, dict)
                            else "Auto-grade complete",
                        )
                    except InterruptedError:
                        raise
                    except Exception as exc:
                        failure = error_details(exc)
                        status_label = (
                            f"HTTP {failure['http_status']}"
                            if failure.get("http_status")
                            else "provider error"
                        )
                        auto_grade_error = (
                            f"Auto-grade provider unavailable ({status_label}). "
                            "The Research answer is complete; retry grading from the Response Library."
                        )
                        result["auto_grade_error"] = auto_grade_error
                        result["auto_gradeerror_details"] = failure
                        result.setdefault("stages", []).append({
                            "name": "auto_grade",
                            "seconds": time.perf_counter() - auto_grade_started,
                            "detail": {
                                "error": auto_grade_error,
                                "http_status": failure.get("http_status"),
                                "retryable": failure.get("http_status") in {408, 425, 429, 500, 502, 503, 504},
                            },
                        })
                        result.setdefault("warnings", []).append(auto_grade_error)
                        progress(
                            "auto_grade",
                            1,
                            1,
                            auto_grade_error,
                        )

                trace_finished_at = iso_now()
                with self._lock:
                    trace_started_at = self._jobs[job_id].get("started_at")
                    trace_cancelled = bool(self._jobs[job_id].get("cancel_requested"))
                try:
                    pipeline_trace = build_research_trace(
                        run_id=job_id,
                        owner=job_owner,
                        request=body,
                        result=result,
                        started_at=trace_started_at,
                        finished_at=trace_finished_at,
                        status="cancelled" if trace_cancelled else "completed",
                    )
                    pipeline_store.put_run(pipeline_trace)
                    result["pipeline_trace"] = pipeline_trace.model_dump(mode="json")
                except Exception as trace_error:
                    # Telemetry is important but must never destroy a completed
                    # scholarly answer. Surface the failure on the run so an
                    # administrator can repair observability independently.
                    result.setdefault("warnings", []).append(
                        f"Pipeline trace persistence failed: {trace_error}"
                    )

                with self._lock:
                    job = self._jobs[job_id]
                    if job["cancel_requested"]:
                        job["status"] = "cancelled"
                        job["stage_detail"] = "RAG pipeline cancelled"
                    else:
                        job["status"] = "completed"
                        job["completed"] = job["total"]
                        job["stage"] = "completed"
                        if auto_grade_error:
                            job["stage_detail"] = "RAG pipeline complete; auto-grade failed"
                        elif cache_error:
                            job["stage_detail"] = "RAG pipeline complete; response-cache write failed"
                        elif body.auto_grade:
                            job["stage_detail"] = "RAG pipeline and auto-grade complete"
                        else:
                            job["stage_detail"] = "RAG pipeline complete"
                        job["result"] = result
                        job["response_cache"] = cache_info
                    job["finished_at"] = iso_now()
                    job["events"].append({
                        "timestamp": job["finished_at"],
                        "stage": job["status"],
                        "current": job["completed"],
                        "total": job["total"],
                        "detail": job["stage_detail"],
                    })
            except InterruptedError:
                with self._lock:
                    job = self._jobs[job_id]
                    job["status"] = "cancelled"
                    job["stage_detail"] = "RAG job cancelled"
                    job["finished_at"] = iso_now()
                    job["events"].append({
                        "timestamp": job["finished_at"],
                        "stage": "cancelled",
                        "current": job["completed"],
                        "total": job["total"],
                        "detail": job["stage_detail"],
                    })
            except Exception as exc:
                with self._lock:
                    job = self._jobs[job_id]
                    job["status"] = "failed"
                    job["failed"] = 1
                    details = store_job_error(job, exc)
                    stage = str(job.get("stage") or "unknown")
                    job["stage_detail"] = (
                        f"{details['message']} (failed during {stage}; "
                        f"last update {job.get('stage_detail') or 'none'})"
                    )
                    job["finished_at"] = iso_now()
                    job["events"].append({
                        "timestamp": job["finished_at"],
                        "stage": "failed",
                        "current": job["completed"],
                        "total": job["total"],
                        "detail": job["stage_detail"],
                    })
        finally:
            if ollama_permit is not None:
                self._release_ollama_slot(job_id, ollama_permit)
            if provider_permit is not None:
                provider_permit.release()
            with self._lock:
                self._threads.pop(job_id, None)
            self._persist_job(job_id)

    def list(self) -> JobPayloadList:
        with self._lock:
            jobs = [self._copy(job, include_result=False) for job in self._jobs.values()]
        return sorted(jobs, key=lambda job: job["created_at"], reverse=True)

    def get(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return self._copy(self._jobs[job_id], include_result=True)

    def snapshot(self) -> JobPayloadList:
        with self._lock:
            return [
                copy.deepcopy(self._copy(job, include_result=True))
                for job in self._jobs.values()
                if job.get("status") not in {"queued", "running", "cancelling"}
            ]

    def restore_snapshot(self, jobs: JobPayloadList) -> int:
        restored = 0
        with self._lock:
            self._jobs = {
                job_id: job
                for job_id, job in self._jobs.items()
                if job.get("status") in {"queued", "running", "cancelling"}
            }
            for raw in jobs or []:
                if not isinstance(raw, dict):
                    continue
                job_id = str(raw.get("id") or "").strip()
                if not job_id or raw.get("status") in {"queued", "running", "cancelling"}:
                    continue
                job = copy.deepcopy(raw)
                job.setdefault("result", None)
                job.setdefault("events", [])
                self._jobs[job_id] = job
                restored += 1
        retained = [copy.deepcopy(job) for job in self._jobs.values() if job.get("status") not in {"queued", "running", "cancelling"}]
        job_repository.replace_finished(self.JOB_TYPE, retained)
        return restored

    def cancel(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            job = self._jobs[job_id]
            if job["status"] == "queued":
                job["cancel_requested"] = True
                job["cancel_requested_at"] = iso_now()
                job["status"] = "cancelled"
                job["finished_at"] = job["cancel_requested_at"]
                job["stage_detail"] = "Cancelled while queued"
                job["events"].append({
                    "timestamp": job["cancel_requested_at"],
                    "stage": "cancelled",
                    "current": job["completed"],
                    "total": job["total"],
                    "detail": job["stage_detail"],
                })
            elif job["status"] == "running" and not job["cancel_requested"]:
                job["cancel_requested"] = True
                job["cancel_requested_at"] = iso_now()
                job["status"] = "cancelling"
                job["events"].append({
                    "timestamp": job["cancel_requested_at"],
                    "stage": "cancellation_requested",
                    "current": job["completed"],
                    "total": job["total"],
                    "detail": (
                        "Cancellation requested; active model streaming is being "
                        "interrupted and vector/rerank work stops at the next safe "
                        "pipeline checkpoint."
                    ),
                })
            job_repository.upsert(copy.deepcopy(job))
            return self._copy(job, include_result=True)

    def delete(self, job_id: str) -> None:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            job = self._jobs[job_id]
            if job["status"] in {"queued", "running", "cancelling"}:
                raise ValueError(
                    "Running jobs must be cancelled before they can be removed."
                )
            del self._jobs[job_id]
            job_repository.delete(job_id)

    def active_count(self) -> int:
        with self._lock:
            return sum(
                1
                for job in self._jobs.values()
                if job["status"] in {"queued", "running", "cancelling"}
            )

    def clear_finished(self) -> int:
        with self._lock:
            ids = [
                job_id
                for job_id, job in self._jobs.items()
                if job["status"] not in {"queued", "running", "cancelling"}
            ]
            for job_id in ids:
                del self._jobs[job_id]
            job_repository.clear_finished(self.JOB_TYPE)
            return len(ids)

    @staticmethod
    def _copy(job: dict[str, Any], *, include_result: bool) -> dict[str, Any]:
        out = {
            key: value
            for key, value in job.items()
            if key != "result"
        }
        if include_result:
            out["result"] = job["result"]
        elif "events" in out:
            out["events"] = list(out.get("events") or [])[-12:]
        return out
