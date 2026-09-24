# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import copy
import threading
import time
import uuid
from typing import Any

from .chroma_store import ChromaStore
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
from .rag import run_rag_pipeline


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
        self._ollama_condition = threading.Condition(self._lock)
        self._ollama_active = 0
        self._ollama_max_concurrent = max(1, int(ollama_max_concurrent))
        self._provider_active: dict[str, int] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._start_persistent_state()

    def set_ollama_limit(self, limit: int) -> dict[str, Any]:
        value = max(1, min(32, int(limit)))
        with self._ollama_condition:
            self._ollama_max_concurrent = value
            self._ollama_condition.notify_all()
            return self.concurrency_status()

    def concurrency_status(self) -> dict[str, Any]:
        with self._lock:
            openai_active = sum(
                1
                for job in self._jobs.values()
                if job.get("provider") == "openai"
                and job.get("status") in {"queued", "running", "cancelling"}
            )
            ollama_waiting = sum(
                1
                for job in self._jobs.values()
                if job.get("provider") == "ollama"
                and job.get("status") == "queued"
                and not job.get("cancel_requested")
            )
            return {
                "openai_mode": "provider_profile_gates",
                "openai_active": openai_active,
                "provider_profile_active": dict(self._provider_active),
                "ollama_max_concurrent": self._ollama_max_concurrent,
                "ollama_active": self._ollama_active,
                "ollama_waiting": ollama_waiting,
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

        with self._ollama_condition:
            if requested_ollama_limit is not None:
                self._ollama_max_concurrent = max(
                    1,
                    min(32, int(requested_ollama_limit)),
                )
                self._ollama_condition.notify_all()

            profile_limit = max(1, min(64, int(body.max_concurrent_requests or 32)))
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

    def _acquire_ollama_slot(self, job_id: str) -> bool:
        with self._ollama_condition:
            waiting_event_recorded = False
            while self._ollama_active >= self._ollama_max_concurrent:
                job = self._jobs[job_id]
                if job["cancel_requested"] or job["status"] == "cancelled":
                    return False
                job["status"] = "queued"
                job["stage"] = "queued"
                job["stage_detail"] = (
                    f"Waiting for Ollama slot: {self._ollama_active} active / "
                    f"{self._ollama_max_concurrent} allowed"
                )
                if not waiting_event_recorded:
                    job["events"].append({
                        "timestamp": iso_now(),
                        "stage": "waiting_for_ollama_slot",
                        "current": self._ollama_active,
                        "total": self._ollama_max_concurrent,
                        "detail": job["stage_detail"],
                    })
                    waiting_event_recorded = True
                self._ollama_condition.wait(timeout=0.5)

            job = self._jobs[job_id]
            if job["cancel_requested"] or job["status"] == "cancelled":
                return False
            self._ollama_active += 1
            job["scheduling"]["limit"] = self._ollama_max_concurrent
            job["scheduling"]["active_when_started"] = self._ollama_active
            job["events"].append({
                "timestamp": iso_now(),
                "stage": "ollama_slot_acquired",
                "current": self._ollama_active,
                "total": self._ollama_max_concurrent,
                "detail": (
                    f"Ollama execution slot acquired "
                    f"({self._ollama_active}/{self._ollama_max_concurrent})"
                ),
            })
            return True

    def _release_ollama_slot(self, job_id: str) -> None:
        with self._ollama_condition:
            if self._ollama_active > 0:
                self._ollama_active -= 1
            job = self._jobs.get(job_id)
            if job is not None:
                job["events"].append({
                    "timestamp": iso_now(),
                    "stage": "ollama_slot_released",
                    "current": self._ollama_active,
                    "total": self._ollama_max_concurrent,
                    "detail": (
                        f"Ollama execution slot released "
                        f"({self._ollama_active}/{self._ollama_max_concurrent} active)"
                    ),
                })
            self._ollama_condition.notify_all()

    @staticmethod
    def _provider_key(body: RAGRunRequest) -> str:
        if body.provider == "ollama":
            return f"ollama|{str(body.base_url or '').rstrip('/').lower()}"
        return body.provider_profile_id or f"{body.provider}|{body.base_url or ''}|{body.model or ''}"

    def _acquire_provider_slot(self, job_id: str, body: RAGRunRequest) -> bool:
        key = self._provider_key(body)
        limit = max(1, min(64, int(body.max_concurrent_requests or 32)))
        with self._ollama_condition:
            while self._provider_active.get(key, 0) >= limit:
                job = self._jobs[job_id]
                if job["cancel_requested"] or job["status"] == "cancelled":
                    return False
                job["status"] = "queued"
                job["stage"] = "queued"
                job["stage_detail"] = (
                    f"Waiting for provider slot: {self._provider_active.get(key, 0)} active / {limit} allowed"
                )
                self._ollama_condition.wait(timeout=0.5)
            self._provider_active[key] = self._provider_active.get(key, 0) + 1
            return True

    def _release_provider_slot(self, body: RAGRunRequest) -> None:
        key = self._provider_key(body)
        with self._ollama_condition:
            current = self._provider_active.get(key, 0)
            if current <= 1:
                self._provider_active.pop(key, None)
            else:
                self._provider_active[key] = current - 1
            self._ollama_condition.notify_all()

    def _run(self, job_id: str, body: RAGRunRequest) -> None:
        ollama_slot = False
        provider_slot = False
        try:
            # Every profile receives its own concurrency gate, including Ollama.
            # Local Ollama work then passes through the process-wide GPU gate as
            # a second constraint. This makes a researcher profile's max value
            # authoritative without allowing one profile to raise the global cap.
            provider_slot = self._acquire_provider_slot(job_id, body)
            if not provider_slot:
                with self._lock:
                    job = self._jobs[job_id]
                    job["status"] = "cancelled"
                    job["finished_at"] = iso_now()
                    job["stage_detail"] = "Cancelled while waiting for provider slot"
                return

            if body.provider == "ollama":
                ollama_slot = self._acquire_ollama_slot(job_id)
                if not ollama_slot:
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

            try:
                result = run_rag_pipeline(
                    body,
                    self._store,
                    progress=progress,
                    cancelled=cancelled,
                )
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
                    job["stage_detail"] = details["message"]
                    job["finished_at"] = iso_now()
                    job["events"].append({
                        "timestamp": job["finished_at"],
                        "stage": "failed",
                        "current": job["completed"],
                        "total": job["total"],
                        "detail": str(exc),
                    })
        finally:
            if ollama_slot:
                self._release_ollama_slot(job_id)
            if provider_slot:
                self._release_provider_slot(body)
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
        with self._ollama_condition:
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
                self._ollama_condition.notify_all()
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

