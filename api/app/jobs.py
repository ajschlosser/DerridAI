# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .llm import TouchupFailure, propose_touchup
from .chroma_store import ChromaStore
from .config import settings
from .models import LLMJobCreate, LLMToolJobCreate, RAGGradeRequest, RAGRunRequest, UpsertJobCreate
from .rag import run_rag_pipeline
from .llm_tools import run_pdf_llm, run_rag_grade, run_work_metadata_batch
from .system_store import system_store, normalize_locale_code
from .i18n_translation import LanguageTranslationError, LanguageTranslationInterrupted, translate_english_dictionary
from .persistence import job_repository


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _error_details(exc: Exception | dict[str, Any]) -> dict[str, Any]:
    """Persist actionable failure details, including embedded upstream HTTP errors."""
    if isinstance(exc, dict):
        message = str(exc.get("message") or exc.get("error") or exc)
        status = exc.get("status_code") or exc.get("http_status")
        diagnostic = exc.get("diagnostic")
    else:
        response = getattr(exc, "response", None)
        status = getattr(exc, "status_code", None) or getattr(exc, "status", None) or getattr(response, "status_code", None)
        message = str(getattr(exc, "message", None) or str(exc) or exc.__class__.__name__)
        diagnostic = getattr(exc, "diagnostic", None)
        if not diagnostic and response is not None:
            try:
                diagnostic = str(getattr(response, "text", "") or "").strip()[:2000] or None
            except Exception:
                diagnostic = None
    match = re.search(r"(?:returned\s+HTTP|HTTP(?:Error)?\s*[: ]?|status(?:_code)?[=: ]+)([45]\d\d)", message, re.I)
    if match:
        embedded = int(match.group(1))
        if status is None or int(status) == 502 or embedded != 502:
            status = embedded
    try:
        status = int(status) if status is not None else None
    except (TypeError, ValueError):
        status = None
    return {"message": message, "http_status": status, "diagnostic": str(diagnostic)[:12000] if diagnostic else None}


def _store_job_error(job: dict[str, Any], exc: Exception) -> dict[str, Any]:
    details = _error_details(exc)
    job["fatal_error"] = details["message"]
    job["error_message"] = details["message"]
    job["http_status"] = details["http_status"]
    job["error_diagnostic"] = details["diagnostic"]
    return details


class PersistentJobStateMixin:
    """Mirror live worker state into the durable SQLite operation ledger.

    Workers still keep a small in-process working copy for low-latency progress
    updates, but SQLite is now the durable source across restarts. A lightweight
    checkpoint loop captures nested progress/event mutations without forcing a
    database transaction for every token or record-field update.
    """

    JOB_TYPE = "operation"

    def _start_persistent_state(self) -> None:
        persisted = job_repository.load(self.JOB_TYPE)
        with self._lock:
            self._jobs = {str(job["id"]): copy.deepcopy(job) for job in persisted if job.get("id")}
        thread = threading.Thread(
            target=self._persistence_loop,
            daemon=True,
            name=f"derridai-{self.JOB_TYPE}-sqlite-checkpoint",
        )
        self._persistence_thread = thread
        thread.start()

    def _persistence_loop(self) -> None:
        while True:
            time.sleep(1.0)
            try:
                with self._lock:
                    jobs = [copy.deepcopy(job) for job in self._jobs.values()]
                if jobs:
                    job_repository.upsert_many(jobs)
            except Exception as exc:
                # Keep workers alive, but make durability degradation visible in
                # every live operation. When SQLite recovers, the next checkpoint
                # persists this warning together with the current job state.
                detail = f"Durable job checkpoint failed and will be retried: {exc}"
                with self._lock:
                    for job in self._jobs.values():
                        if job.get("status") in {"queued", "running", "cancelling"}:
                            warnings = job.setdefault("warnings", [])
                            if detail not in warnings[-3:]:
                                warnings.append(detail)
                continue

    def _persist_job(self, job_id: str) -> None:
        with self._lock:
            job = copy.deepcopy(self._jobs.get(job_id))
        if job is not None:
            job_repository.upsert(job)

    def _persist_all_jobs(self) -> None:
        with self._lock:
            jobs = [copy.deepcopy(job) for job in self._jobs.values()]
        job_repository.upsert_many(jobs)


class LLMJobManager(PersistentJobStateMixin):
    JOB_TYPE = "llm"
    def __init__(self, max_workers: int = 64) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._provider_condition = threading.Condition(self._lock)
        self._provider_active: dict[str, int] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=max(4, min(64, int(max_workers))),
            thread_name_prefix="derridai-llm",
        )
        self._start_persistent_state()

    def create(self, body: LLMJobCreate, *, owner: str | None = None) -> dict[str, Any]:
        job_id = str(uuid.uuid4())
        request_summary = {
            "mode": body.mode,
            "owner": owner,
            "provider": body.provider,
            "model": body.model,
            "base_url": body.base_url,
            "provider_profile_id": body.provider_profile_id,
            "max_concurrent_requests": body.max_concurrent_requests,
            "fields": list(body.fields),
            "instructions": body.instructions,
            "generation": (
                body.ollama.model_dump(exclude_none=True)
                if body.ollama is not None
                else {}
            ),
            "records": [
                {
                    "key": item.key,
                    "record_id": item.record.get("record_id"),
                    "work": item.record.get("work"),
                    "pages": [
                        item.record.get("page_start"),
                        item.record.get("page_end"),
                    ],
                }
                for item in body.items
            ],
        }
        job = {
            "id": job_id,
            "type": "llm",
            "mode": body.mode,
            "owner": owner,
            "provider": body.provider,
            "model": body.model,
            "provider_profile_id": body.provider_profile_id,
            "max_concurrent_requests": body.max_concurrent_requests,
            "fields": list(body.fields),
            "status": "queued",
            "created_at": iso_now(),
            "started_at": None,
            "finished_at": None,
            "total": len(body.items),
            "completed": 0,
            "failed": 0,
            "cancel_requested": False,
            "cancel_requested_at": None,
            "current_record_id": None,
            "request": request_summary,
            "events": [{
                "timestamp": iso_now(),
                "stage": "queued",
                "detail": f"{len(body.items)} records queued",
            }],
            "results": [],
            "accepted_results": 0,
            "accepted_fields": 0,
            "rejected_results": 0,
            "rejected_fields": 0,
            "resolution_state": "pending",
            "dismissed": False,
            "last_resolution_at": None,
        }
        # LLM jobs are intentionally not spooled to disk: request bodies may
        # contain provider API keys. Provider-specific concurrency gates below
        # already bound parallel work safely, so keep the sensitive request only
        # in the executor closure for the lifetime of the job. Persisted job
        # state contains the redacted request summary, never credentials.
        with self._lock:
            self._jobs[job_id] = job
        self._persist_job(job_id)
        self._executor.submit(self._run, job_id, body)
        return self.get(job_id)

    @staticmethod
    def _provider_key(body: LLMJobCreate) -> str:
        if body.provider == "ollama":
            return f"ollama|{str(body.base_url or '').rstrip('/').lower()}"
        return body.provider_profile_id or f"{body.provider}|{body.base_url or ''}|{body.model or ''}"

    def _acquire_provider_slot(self, job_id: str, body: LLMJobCreate) -> bool:
        key = self._provider_key(body)
        limit = max(1, min(64, int(body.max_concurrent_requests or 1)))
        with self._provider_condition:
            while self._provider_active.get(key, 0) >= limit:
                job = self._jobs[job_id]
                if job.get("cancel_requested"):
                    return False
                job["status"] = "queued"
                job["stage_detail"] = (
                    f"Waiting for provider slot "
                    f"({self._provider_active.get(key, 0)}/{limit} active)"
                )
                self._provider_condition.wait(timeout=0.5)
            self._provider_active[key] = self._provider_active.get(key, 0) + 1
            return True

    def _release_provider_slot(self, body: LLMJobCreate) -> None:
        key = self._provider_key(body)
        with self._provider_condition:
            current = self._provider_active.get(key, 0)
            if current <= 1:
                self._provider_active.pop(key, None)
            else:
                self._provider_active[key] = current - 1
            self._provider_condition.notify_all()

    def _run(self, job_id: str, body: LLMJobCreate) -> None:
        if not self._acquire_provider_slot(job_id, body):
            with self._lock:
                job = self._jobs[job_id]
                job["status"] = "cancelled"
                job["finished_at"] = iso_now()
            self._persist_job(job_id)
            return
        try:
            self._run_with_provider_slot(job_id, body)
        finally:
            self._release_provider_slot(body)
            self._persist_job(job_id)

    def _run_with_provider_slot(self, job_id: str, body: LLMJobCreate) -> None:
        with self._lock:
            job = self._jobs[job_id]
            if job["cancel_requested"] or job["status"] == "cancelled":
                if not job["finished_at"]:
                    job["status"] = "cancelled"
                    job["finished_at"] = iso_now()
                    job["events"].append({
                        "timestamp": job["finished_at"],
                        "stage": "cancelled",
                        "detail": "Cancelled before execution began",
                    })
                return
            job["status"] = "running"
            job["started_at"] = iso_now()
            job["events"].append({
                "timestamp": job["started_at"],
                "stage": "running",
                "detail": "Background LLM review started",
            })

        try:
            for item in body.items:
                with self._lock:
                    job = self._jobs[job_id]
                    if job["cancel_requested"]:
                        job["status"] = "cancelled"
                        break

                with self._lock:
                    job = self._jobs[job_id]
                    job["current_record_id"] = item.record.get("record_id")
                    job["events"].append({
                        "timestamp": iso_now(),
                        "stage": "reviewing",
                        "detail": str(item.record.get("record_id") or item.key),
                    })

                result: dict[str, Any] = {
                    "key": item.key,
                    "fingerprint": item.fingerprint,
                    "record_id": item.record.get("record_id"),
                    "proposal": None,
                    "error": None,
                    "completed_at": None,
                }
                try:
                    result["proposal"] = propose_touchup(
                        item.record,
                        body.fields,
                        body.instructions,
                        body.model,
                        body.ollama,
                        provider=body.provider,
                        base_url=body.base_url,
                        api_key=body.api_key,
                        cancelled=lambda: self._is_cancel_requested(job_id),
                    )
                except InterruptedError:
                    with self._lock:
                        job = self._jobs[job_id]
                        job["status"] = "cancelled"
                        job["events"].append({
                            "timestamp": iso_now(),
                            "stage": "cancelled",
                            "detail": "Current model request was interrupted by cancellation.",
                        })
                    break
                except TouchupFailure as exc:
                    result["error"] = {
                        "status_code": exc.status_code,
                        "message": exc.message,
                        "diagnostic": exc.diagnostic,
                    }
                except Exception as exc:
                    result["error"] = {
                        "status_code": 500,
                        "message": "Unexpected LLM job failure.",
                        "diagnostic": str(exc),
                    }

                result["completed_at"] = iso_now()
                with self._lock:
                    job = self._jobs[job_id]
                    job["results"].append(result)
                    job["completed"] += 1
                    if result["error"]:
                        job["failed"] += 1
                    job["events"].append({
                        "timestamp": iso_now(),
                        "stage": "record_complete",
                        "detail": (
                            f"{result['record_id'] or item.key}: failed"
                            if result["error"]
                            else f"{result['record_id'] or item.key}: complete"
                        ),
                    })

            with self._lock:
                job = self._jobs[job_id]
                if job["cancel_requested"] or job["status"] in {"cancelled", "cancelling"}:
                    job["status"] = "cancelled"
                else:
                    job["status"] = "completed"
                unresolved = [
                    result
                    for result in (job.get("results") or [])
                    if not result.get("error") and result.get("proposal")
                ]
                if not unresolved:
                    if job.get("resolution_state") == "partially_accepted":
                        job["resolution_state"] = "accepted"
                    elif job.get("resolution_state") == "partially_rejected":
                        job["resolution_state"] = "rejected"
                job["current_record_id"] = None
                job["finished_at"] = iso_now()
                job["events"].append({
                    "timestamp": job["finished_at"],
                    "stage": job["status"],
                    "detail": f"{job['completed']} of {job['total']} records processed",
                })
        except Exception as exc:
            with self._lock:
                job = self._jobs[job_id]
                job["status"] = "failed"
                _store_job_error(job, exc)
                job["finished_at"] = iso_now()

    def _is_cancel_requested(self, job_id: str) -> bool:
        with self._lock:
            return bool(self._jobs.get(job_id, {}).get("cancel_requested"))

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            jobs = [
                self._copy(job, include_results=False)
                for job in self._jobs.values()
                if not job.get("dismissed")
            ]
        return sorted(jobs, key=lambda job: job["created_at"], reverse=True)

    def get(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return self._copy(self._jobs[job_id], include_results=True)

    def resolve_results(
        self,
        job_id: str,
        *,
        action: str,
        items: list[dict[str, Any]],
        dismiss_job: bool = False,
    ) -> dict[str, Any]:
        if action not in {"accept", "reject"}:
            raise ValueError("action must be accept or reject")
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            job = self._jobs[job_id]
            requested = {str(item.get("key")): item for item in items if item.get("key")}
            if not requested:
                return self._copy(job, include_results=True)

            kept: list[dict[str, Any]] = []
            resolved_records = 0
            resolved_fields = 0
            for result in job["results"]:
                key = str(result.get("key"))
                spec = requested.get(key)
                if not spec:
                    kept.append(result)
                    continue

                proposal = result.get("proposal") or {}
                changes = dict(proposal.get("changes") or {})
                rationale = dict(proposal.get("rationale") or {})
                requested_fields = spec.get("fields")
                resolve_record = bool(spec.get("resolve_record"))

                if resolve_record or requested_fields is None:
                    field_names = list(changes)
                    resolved_fields += len(field_names)
                    resolved_records += 1
                    continue

                field_set = {str(field) for field in requested_fields}
                removed = [field for field in list(changes) if field in field_set]
                for field in removed:
                    changes.pop(field, None)
                    rationale.pop(field, None)
                resolved_fields += len(removed)

                if changes:
                    next_result = dict(result)
                    next_proposal = dict(proposal)
                    next_proposal["changes"] = changes
                    next_proposal["rationale"] = rationale
                    next_result["proposal"] = next_proposal
                    kept.append(next_result)
                else:
                    resolved_records += 1

            job["results"] = kept
            if action == "accept":
                job["accepted_results"] += resolved_records
                job["accepted_fields"] += resolved_fields
            else:
                job["rejected_results"] += resolved_records
                job["rejected_fields"] += resolved_fields
            job["last_resolution_at"] = iso_now()

            pending = sum(
                1
                for result in job["results"]
                if not result.get("error") and result.get("proposal")
            )
            if action == "accept":
                if job["status"] in {"completed", "cancelled", "failed"} and pending == 0:
                    job["resolution_state"] = "accepted"
                else:
                    job["resolution_state"] = "partially_accepted"
            else:
                if job["status"] in {"completed", "cancelled", "failed"} and pending == 0:
                    job["resolution_state"] = "rejected"
                else:
                    job["resolution_state"] = "partially_rejected"

            job["events"].append({
                "timestamp": job["last_resolution_at"],
                "stage": f"results_{action}ed",
                "detail": (
                    f"{resolved_records} result record(s), {resolved_fields} field change(s) "
                    f"{action}ed; {pending} pending result record(s)"
                ),
            })
            if dismiss_job:
                job["dismissed"] = True
            job_repository.upsert(copy.deepcopy(job))
            return self._copy(job, include_results=True)

    def reject_and_dismiss(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            job = self._jobs[job_id]
            pending_records = len(job["results"])
            pending_fields = sum(
                len(((result.get("proposal") or {}).get("changes") or {}))
                for result in job["results"]
            )
            job["results"] = []
            job["rejected_results"] += pending_records
            job["rejected_fields"] += pending_fields
            job["resolution_state"] = "rejected"
            job["dismissed"] = True
            job["last_resolution_at"] = iso_now()
            job["events"].append({
                "timestamp": job["last_resolution_at"],
                "stage": "job_rejected",
                "detail": (
                    f"Rejected {pending_records} pending result record(s) / "
                    f"{pending_fields} proposed field change(s) and dismissed operation"
                ),
            })
            if job["status"] == "queued":
                job["cancel_requested"] = True
                job["cancel_requested_at"] = job["last_resolution_at"]
                job["status"] = "cancelled"
                job["finished_at"] = job["finished_at"] or job["last_resolution_at"]
            elif job["status"] == "running":
                job["cancel_requested"] = True
                job["cancel_requested_at"] = job["last_resolution_at"]
                job["status"] = "cancelling"
            job_repository.upsert(copy.deepcopy(job))
            return self._copy(job, include_results=True)

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                copy.deepcopy(self._copy(job, include_results=True))
                for job in self._jobs.values()
                if job.get("status") not in {"queued", "running", "cancelling"}
                and not job.get("dismissed")
            ]

    def restore_snapshot(self, jobs: list[dict[str, Any]]) -> int:
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
                job.setdefault("results", [])
                job.setdefault("events", [])
                job.setdefault("accepted_results", 0)
                job.setdefault("accepted_fields", 0)
                job.setdefault("rejected_results", 0)
                job.setdefault("rejected_fields", 0)
                job.setdefault("resolution_state", "pending")
                job.setdefault("dismissed", False)
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
                job["events"].append({
                    "timestamp": job["cancel_requested_at"],
                    "stage": "cancelled",
                    "detail": "Cancelled while queued",
                })
            elif job["status"] == "running" and not job["cancel_requested"]:
                job["cancel_requested"] = True
                job["cancel_requested_at"] = iso_now()
                job["status"] = "cancelling"
                job["events"].append({
                    "timestamp": job["cancel_requested_at"],
                    "stage": "cancellation_requested",
                    "detail": (
                        "Cancellation requested; the current model stream is being "
                        "interrupted. Providers that cannot abort immediately stop at "
                        "the next safe checkpoint."
                    ),
                })
            job_repository.upsert(copy.deepcopy(job))
            return self._copy(job, include_results=True)

    def delete(self, job_id: str) -> None:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            job = self._jobs[job_id]
            if job["status"] in {"queued", "running", "cancelling"}:
                raise ValueError("Running jobs must be cancelled before they can be removed.")
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
    def _copy(job: dict[str, Any], *, include_results: bool) -> dict[str, Any]:
        out = {
            key: value
            for key, value in job.items()
            if key != "results"
        }
        all_results = list(job.get("results") or [])
        pending_results = [
            result
            for result in all_results
            if not result.get("error") and result.get("proposal")
        ]
        out["pending_result_count"] = len(pending_results)
        out["pending_change_count"] = sum(
            len(((result.get("proposal") or {}).get("changes") or {}))
            for result in pending_results
        )
        out["failure_result_count"] = sum(
            1 for result in all_results if result.get("error")
        )
        out["remaining_record_count"] = max(
            0,
            int(job.get("total") or 0) - int(job.get("completed") or 0),
        )
        if include_results:
            out["results"] = all_results
        elif "events" in out:
            out["events"] = list(out.get("events") or [])[-12:]
        return out


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
                                failure = _error_details(grade_exc)
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
                                        raise InterruptedError()
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
                        failure = _error_details(exc)
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
                        result["auto_grade_error_details"] = failure
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
                    details = _store_job_error(job, exc)
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

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            jobs = [self._copy(job, include_result=False) for job in self._jobs.values()]
        return sorted(jobs, key=lambda job: job["created_at"], reverse=True)

    def get(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return self._copy(self._jobs[job_id], include_result=True)

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                copy.deepcopy(self._copy(job, include_result=True))
                for job in self._jobs.values()
                if job.get("status") not in {"queued", "running", "cancelling"}
            ]

    def restore_snapshot(self, jobs: list[dict[str, Any]]) -> int:
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


class LLMToolJobManager(PersistentJobStateMixin):
    JOB_TYPE = "llm_tool"
    """Runs one-off LLM tools and cache-wide RAG grading jobs.

    Tool jobs share a provider-profile concurrency gate. A cache-wide grading
    request is deliberately represented as one job instead of N independent
    jobs; that keeps the operations UI small and prevents a bulk re-grade from
    overwhelming Ollama or an OpenAI-compatible endpoint.
    """

    def __init__(self, store: ChromaStore) -> None:
        self._store = store
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self._active: dict[str, int] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._start_persistent_state()

    @staticmethod
    def _payload(body: LLMToolJobCreate):
        return body.pdf or body.grade or body.grade_batch or body.work_metadata or body.language

    @classmethod
    def _provider_key(cls, body: LLMToolJobCreate) -> str:
        payload = cls._payload(body)
        assert payload is not None
        if payload.provider == "ollama":
            return f"ollama|{str(payload.base_url or '').rstrip('/').lower()}"
        return body.provider_profile_id or getattr(payload, "provider_profile_id", None) or f"{payload.provider}|{payload.base_url or ''}|{payload.model or ''}"

    def create(self, body: LLMToolJobCreate, *, owner: str | None = None) -> dict[str, Any]:
        if body.task.startswith("pdf_") and body.pdf is None:
            raise ValueError("PDF LLM jobs require a pdf payload.")
        if body.task == "rag_grade" and body.grade is None:
            raise ValueError("RAG grading jobs require a grade payload.")
        if body.task == "rag_grade_batch" and body.grade_batch is None:
            raise ValueError("Cache-wide RAG grading requires a grade_batch payload.")
        if body.task == "work_metadata" and body.work_metadata is None:
            raise ValueError("Work metadata jobs require a work_metadata payload.")
        if body.task == "language_dictionary" and body.language is None:
            raise ValueError("Language dictionary jobs require a language payload.")

        payload = self._payload(body)
        assert payload is not None
        total = 1
        if body.task == "rag_grade_batch":
            total = int(self._store.get_response_cache_records(limit=1_000_000).get("total") or 0)
            if total <= 0:
                raise ValueError("The response cache does not contain any RAG responses to grade.")
        elif body.task == "work_metadata":
            total = len(body.work_metadata.works)
        elif body.task == "language_dictionary":
            base = system_store.get_language("en-US") or {"dictionary": {}}
            total = len(base.get("dictionary") or {})

        job_id = str(uuid.uuid4())
        label = body.label or {
            "pdf_clean_text": "PDF · clean text",
            "pdf_draft_record": "PDF · draft record",
            "pdf_link_record": "PDF · link record",
            "rag_grade": "RAG · grade response",
            "rag_grade_batch": "RAG · grade response cache",
            "work_metadata": "Works · populate metadata",
            "language_dictionary": "Languages · translate dictionary",
        }.get(body.task, body.task)
        job = {
            "id": job_id,
            "type": "llm_tool",
            "mode": body.task,
            "tool": body.task,
            "label": label,
            "owner": owner,
            "provider": payload.provider,
            "model": payload.model,
            "provider_profile_id": body.provider_profile_id or getattr(payload, "provider_profile_id", None),
            "max_concurrent_requests": body.max_concurrent_requests,
            "status": "queued",
            "created_at": iso_now(),
            "started_at": None,
            "finished_at": None,
            "total": total,
            "completed": 0,
            "failed": 0,
            "cancel_requested": False,
            "cancel_requested_at": None,
            "stage": "queued",
            "stage_detail": "Waiting to start",
            "request": payload.model_dump(exclude={"api_key"}),
            "events": [],
            "result": None,
        }
        with self._lock:
            self._jobs[job_id] = job
        self._persist_job(job_id)

        thread = threading.Thread(
            target=self._run,
            args=(job_id, body),
            daemon=True,
            name=f"derridai-tool-{job_id[:8]}",
        )
        with self._lock:
            self._threads[job_id] = thread
        thread.start()
        return self.get(job_id)

    def _run_grade_batch(self, job_id: str, body: LLMToolJobCreate) -> dict[str, Any]:
        assert body.grade_batch is not None
        config = body.grade_batch
        cache = self._store.get_response_cache_records(limit=1_000_000)
        records = list(cache.get("records") or [])
        errors: list[dict[str, str]] = []
        graded = 0

        for index, record in enumerate(records, start=1):
            with self._lock:
                job = self._jobs[job_id]
                if job["cancel_requested"]:
                    raise InterruptedError()
                question = str(record.get("question") or "Untitled cached RAG question")
                job["stage"] = "grading"
                job["stage_detail"] = f"Grading {index} of {len(records)} · {question[:120]}"

            try:
                grade_body = RAGGradeRequest(
                    question=str(record.get("question") or ""),
                    answer=str(record.get("text") or ""),
                    evidence=list(record.get("evidence") or []),
                    provider=config.provider,
                    model=config.model,
                    base_url=config.base_url,
                    api_key=config.api_key,
                    generation=config.generation,
                    response_record_id=str(record.get("record_id") or "") or None,
                    generation_provider=record.get("provider"),
                    generation_model=record.get("model"),
                )
                run_rag_grade(
                    grade_body,
                    self._store,
                    cancelled=lambda: bool(self._jobs[job_id]["cancel_requested"]),
                )
                graded += 1
            except InterruptedError:
                raise
            except Exception as exc:
                errors.append({
                    "record_id": str(record.get("record_id") or ""),
                    "question": str(record.get("question") or "")[:240],
                    "error": str(exc),
                })
            finally:
                with self._lock:
                    job = self._jobs[job_id]
                    job["completed"] = index
                    job["failed"] = len(errors)
                    # Keep event history useful without recording hundreds of
                    # near-identical rows for large response caches.
                    if index == 1 or index == len(records) or index % 10 == 0:
                        job["events"].append({
                            "timestamp": iso_now(),
                            "stage": "grading",
                            "detail": f"Processed {index} of {len(records)} cached responses",
                        })

        return {
            "graded": graded,
            "failed": len(errors),
            "total": len(records),
            "errors": errors[:100],
        }

    def _run_language_dictionary(self, job_id: str, body: LLMToolJobCreate) -> dict[str, Any]:
        assert body.language is not None
        config = body.language
        code = normalize_locale_code(config.code)
        if system_store.get_language(code) is not None:
            raise ValueError(f"Locale {code} is already installed. Edit the existing dictionary or remove it before reinstalling.")
        base = system_store.get_language("en-US") or {"dictionary": {}}
        dictionary = dict(base.get("dictionary") or {})

        # Provider profiles keep API keys write-only in the browser. Resolve the
        # selected profile again on the server so translation jobs can use a
        # stored secret without ever sending it back to the client.
        stored_profile = system_store.researcher_profile(body.provider_profile_id) if body.provider_profile_id else None
        provider = str((stored_profile or {}).get("type") or config.provider)
        model = str(config.model or (stored_profile or {}).get("model") or "").strip()
        base_url = config.base_url or (stored_profile or {}).get("base_url")
        api_key = config.api_key or (stored_profile or {}).get("api_key")
        if not model:
            raise ValueError("Select a model to translate the language dictionary.")

        def cancelled() -> bool:
            with self._lock:
                return bool(self._jobs[job_id]["cancel_requested"])

        def translation_progress(completed: int, total: int, detail: str) -> None:
            with self._lock:
                job = self._jobs[job_id]
                job["completed"] = completed
                job["total"] = total
                job["stage"] = "translation"
                job["stage_detail"] = detail
                if completed == 0 or completed == total or completed % 250 == 0:
                    job["events"].append({
                        "timestamp": iso_now(),
                        "stage": "translation",
                        "detail": detail,
                    })

        def translation_checkpoint(
            partial: dict[str, str],
            failed_keys: list[str],
            failures: list[dict[str, str]],
            stats: dict[str, Any],
        ) -> None:
            # Keep validated translations durable while the pipeline is still
            # running. A restart therefore loses at most the current model call,
            # not the entire dictionary operation. Hidden checkpoint payloads are
            # not returned by the public job API.
            with self._lock:
                current = self._jobs[job_id]
                current["_resume_dictionary"] = dict(partial)
                current["_resume_failed_keys"] = list(failed_keys)
                current["result"] = {
                    "code": code,
                    "name": config.name or code,
                    "flag": config.flag or "🌐",
                    "partial_key_count": len(partial),
                    "failed_count": len(failed_keys),
                    "failure_samples": list(failures)[:20],
                    "resumable": True,
                    "checkpoint_at": iso_now(),
                    **{key: value for key, value in stats.items() if key not in {"failed_keys", "failures"}},
                }
            self._persist_job(job_id)

        resume_dictionary: dict[str, str] | None = None
        retry_keys: list[str] | None = None
        if config.resume_job_id:
            with self._lock:
                prior = copy.deepcopy(self._jobs.get(config.resume_job_id))
            if not prior:
                raise ValueError("The translation job selected for resume no longer exists.")
            if prior.get("mode") != "language_dictionary":
                raise ValueError("Only language dictionary jobs can be resumed here.")
            prior_result = prior.get("result") if isinstance(prior.get("result"), dict) else {}
            prior_request = prior.get("request") if isinstance(prior.get("request"), dict) else {}
            prior_code = normalize_locale_code(str(prior_result.get("code") or prior_request.get("code") or ""))
            if prior_code != code:
                raise ValueError(f"The incomplete translation belongs to {prior_code or 'another locale'}, not {code}.")
            resume_dictionary = dict(prior.get("_resume_dictionary") or prior_result.get("partial_dictionary") or {})
            retry_keys = [str(key) for key in (prior.get("_resume_failed_keys") or prior_result.get("failed_keys") or [])]

        try:
            clean, stats = translate_english_dictionary(
                code=code,
                dictionary=dictionary,
                provider=provider,
                model=model,
                base_url=base_url,
                api_key=api_key,
                generation=config.generation,
                cancelled=cancelled,
                progress=translation_progress,
                checkpoint=translation_checkpoint,
                resume_dictionary=resume_dictionary,
                retry_keys=retry_keys,
            )
        except (LanguageTranslationError, LanguageTranslationInterrupted) as exc:
            public_stats = {
                key: value
                for key, value in exc.stats.items()
                if key not in {"failed_keys", "failures"}
            }
            partial_result = {
                "code": code,
                "name": config.name or code,
                "flag": config.flag or "🌐",
                "partial_key_count": len(exc.partial_dictionary),
                "failed_count": len(exc.failed_keys),
                "failure_samples": exc.failures[:20],
                "resumable": bool(exc.partial_dictionary or exc.failed_keys),
                **public_stats,
            }
            with self._lock:
                current = self._jobs[job_id]
                current["_resume_dictionary"] = dict(exc.partial_dictionary)
                current["_resume_failed_keys"] = list(exc.failed_keys)
                current["result"] = partial_result
            raise

        translation_report = {
            "status": "completed_with_fallbacks" if int(stats.get("fallback_count") or 0) else "complete",
            "source_locale": "en-US",
            "provider": provider,
            "model": model,
            "completed_at": iso_now(),
            "failed_count": int(stats.get("failed_count") or 0),
            "fallback_count": int(stats.get("fallback_count") or 0),
            "failed_keys": list(stats.get("failed_keys") or []),
            "failures": list(stats.get("failures") or [])[:250],
            "translated_count": int(stats.get("translated_count") or 0),
            "key_count": int(stats.get("key_count") or len(dictionary)),
        }
        saved = system_store.put_language(
            code,
            name=config.name or code,
            flag=config.flag or "🌐",
            dictionary=clean,
            translation_report=translation_report,
        )
        return {
            "code": str(saved.get("code") or code),
            "name": str(saved.get("name") or config.name or code),
            "flag": str(saved.get("flag") or config.flag or "🌐"),
            **stats,
        }

    def _run(self, job_id: str, body: LLMToolJobCreate) -> None:
        key = self._provider_key(body)
        limit = max(1, min(64, int(body.max_concurrent_requests or 1)))
        with self._condition:
            while self._active.get(key, 0) >= limit:
                job = self._jobs[job_id]
                if job["cancel_requested"]:
                    job["status"] = "cancelled"
                    job["finished_at"] = iso_now()
                    return
                job["stage_detail"] = (
                    f"Waiting for provider slot ({self._active.get(key, 0)}/{limit} active)"
                )
                self._condition.wait(timeout=0.5)
            self._active[key] = self._active.get(key, 0) + 1

        try:
            with self._lock:
                job = self._jobs[job_id]
                if job["cancel_requested"]:
                    job["status"] = "cancelled"
                    job["finished_at"] = iso_now()
                    return
                job["status"] = "running"
                job["started_at"] = iso_now()
                job["stage"] = "generation"
                job["stage_detail"] = f"Running {job['label']}"

            def cancelled() -> bool:
                with self._lock:
                    return bool(self._jobs[job_id]["cancel_requested"])

            try:
                if body.task.startswith("pdf_"):
                    result = run_pdf_llm(body.pdf, cancelled=cancelled)
                elif body.task == "rag_grade_batch":
                    result = self._run_grade_batch(job_id, body)
                elif body.task == "language_dictionary":
                    result = self._run_language_dictionary(job_id, body)
                elif body.task == "work_metadata":
                    def metadata_progress(completed: int, total: int, detail: str) -> None:
                        with self._lock:
                            current = self._jobs[job_id]
                            current["completed"] = completed
                            current["stage"] = "catalogue_lookup"
                            current["stage_detail"] = detail
                            if completed == 0 or completed == total or completed % 5 == 0:
                                current["events"].append({"timestamp": iso_now(), "stage": "catalogue_lookup", "detail": detail})
                    result = run_work_metadata_batch(
                        body.work_metadata,
                        cancelled=cancelled,
                        progress=metadata_progress,
                    )
                else:
                    result = run_rag_grade(body.grade, self._store, cancelled=cancelled)

                with self._lock:
                    job = self._jobs[job_id]
                    if job["cancel_requested"]:
                        job["status"] = "cancelled"
                        job["stage_detail"] = "Cancelled"
                    else:
                        job["status"] = "completed"
                        if body.task not in {"rag_grade_batch", "work_metadata", "language_dictionary"}:
                            job["completed"] = 1
                        elif body.task in {"work_metadata", "language_dictionary"}:
                            job["completed"] = job["total"]
                        job["stage"] = "completed"
                        if body.task == "rag_grade_batch":
                            job["stage_detail"] = f"Completed · {result.get('graded', 0)} graded, {result.get('failed', 0)} failed"
                        elif body.task == "work_metadata":
                            job["stage_detail"] = f"Completed · {result.get('total', 0)} works, {result.get('failed', 0)} failed"
                        else:
                            job["stage_detail"] = "Completed"
                        job["result"] = result
                        if body.task == "language_dictionary":
                            # The installed locale is now the durable copy; drop
                            # the temporary server-side resume payload to keep
                            # the operation ledger compact.
                            job.pop("_resume_dictionary", None)
                            job.pop("_resume_failed_keys", None)
                    job["finished_at"] = iso_now()
            except InterruptedError:
                with self._lock:
                    job = self._jobs[job_id]
                    job["status"] = "cancelled"
                    job["stage_detail"] = "Cancelled"
                    job["finished_at"] = iso_now()
            except Exception as exc:
                with self._lock:
                    job = self._jobs[job_id]
                    job["status"] = "failed"
                    job["failed"] = max(1, int(job.get("failed") or 0))
                    details = _store_job_error(job, exc)
                    job["stage_detail"] = details["message"]
                    job["finished_at"] = iso_now()
        finally:
            with self._condition:
                current = self._active.get(key, 0)
                if current <= 1:
                    self._active.pop(key, None)
                else:
                    self._active[key] = current - 1
                self._condition.notify_all()
            with self._lock:
                self._threads.pop(job_id, None)
            self._persist_job(job_id)

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            jobs = [self._copy(job, False) for job in self._jobs.values()]
        return sorted(jobs, key=lambda job: job["created_at"], reverse=True)

    def get(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return self._copy(self._jobs[job_id], True)

    def snapshot(self) -> list[dict[str, Any]]:
        # Raw copies intentionally retain hidden language-translation checkpoints
        # so a full backup can restore an incomplete/resumable dictionary job.
        with self._lock:
            return [
                copy.deepcopy(job)
                for job in self._jobs.values()
                if job.get("status") not in {"queued", "running", "cancelling"}
            ]

    def restore_snapshot(self, jobs: list[dict[str, Any]]) -> int:
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
                job.setdefault("type", "llm_tool")
                self._jobs[job_id] = job
                restored += 1
        retained = [
            copy.deepcopy(job)
            for job in self._jobs.values()
            if job.get("status") not in {"queued", "running", "cancelling"}
        ]
        job_repository.replace_finished(self.JOB_TYPE, retained)
        return restored

    def cancel(self, job_id: str) -> dict[str, Any]:
        with self._condition:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            job = self._jobs[job_id]
            if job["status"] == "queued":
                job["cancel_requested"] = True
                job["cancel_requested_at"] = iso_now()
                job["status"] = "cancelled"
                job["finished_at"] = job["cancel_requested_at"]
            elif job["status"] == "running":
                job["cancel_requested"] = True
                job["cancel_requested_at"] = iso_now()
                job["status"] = "cancelling"
            self._condition.notify_all()
            job_repository.upsert(copy.deepcopy(job))
            return self._copy(job, True)

    def delete(self, job_id: str) -> None:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            if self._jobs[job_id]["status"] in {"queued", "running", "cancelling"}:
                raise ValueError("Running jobs must be cancelled first.")
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
    def _copy(job: dict[str, Any], include_result: bool) -> dict[str, Any]:
        out = {
            key: copy.deepcopy(value)
            for key, value in job.items()
            if key != "result" and not str(key).startswith("_")
        }
        if include_result:
            out["result"] = copy.deepcopy(job["result"])
        elif "events" in out:
            out["events"] = list(out.get("events") or [])[-12:]
        return out


class UpsertJobManager(PersistentJobStateMixin):
    JOB_TYPE = "upsert"
    def __init__(self, store: ChromaStore, max_workers: int = 1) -> None:
        self._store = store
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="derridai-upsert",
        )
        spool_default = Path(settings.system_db_path).expanduser().parent / "upsert-jobs"
        self._spool_dir = Path(os.getenv("UPSERT_JOB_SPOOL_PATH", str(spool_default))).expanduser()
        self._spool_dir.mkdir(parents=True, exist_ok=True)
        self._start_persistent_state()
        self._resume_spooled_jobs()

    def _spool_path(self, job_id: str) -> Path:
        return self._spool_dir / f"{job_id}.json"

    def _write_spool(self, job_id: str, body: UpsertJobCreate) -> None:
        target = self._spool_path(job_id)
        temp = target.with_suffix(".json.tmp")
        temp.write_text(
            json.dumps(body.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        temp.replace(target)

    def _remove_spool(self, job_id: str) -> None:
        try:
            self._spool_path(job_id).unlink(missing_ok=True)
        except OSError:
            # Terminal job state lives in SQLite. Spool deletion is cleanup only;
            # a stale file is ignored unless the durable job ledger says to resume.
            pass

    def _run_from_spool(self, job_id: str) -> None:
        # A queued job may be cancelled before its executor slot starts. In
        # that case cancellation removes the spool intentionally; do not turn
        # the already-terminal job into a payload-restoration failure.
        with self._lock:
            existing = self._jobs.get(job_id)
            if existing is None or existing.get("status") == "cancelled":
                self._remove_spool(job_id)
                return
        try:
            payload = json.loads(self._spool_path(job_id).read_text(encoding="utf-8"))
            body = UpsertJobCreate.model_validate(payload)
        except Exception as exc:
            with self._lock:
                job = self._jobs.get(job_id)
                if job is not None:
                    job["status"] = "failed"
                    job["finished_at"] = iso_now()
                    _store_job_error(job, RuntimeError(f"Could not restore vector-build payload: {exc}"))
                    job.setdefault("events", []).append({
                        "timestamp": job["finished_at"],
                        "stage": "failed",
                        "detail": "Vector-build payload could not be restored from the durable spool.",
                    })
            self._persist_job(job_id)
            return
        self._run(job_id, body)

    def _resume_spooled_jobs(self) -> None:
        to_resume: list[str] = []
        with self._lock:
            for job_id, job in self._jobs.items():
                if job.get("status") not in {"queued", "running", "cancelling"}:
                    continue
                if job.get("cancel_requested"):
                    job["status"] = "cancelled"
                    job["finished_at"] = iso_now()
                    job.setdefault("events", []).append({
                        "timestamp": job["finished_at"],
                        "stage": "cancelled",
                        "detail": "Cancellation completed during application restart.",
                    })
                    self._remove_spool(job_id)
                    continue
                if not self._spool_path(job_id).exists():
                    job["status"] = "failed"
                    job["finished_at"] = iso_now()
                    job["fatal_error"] = "Durable vector-build payload is missing after restart."
                    job.setdefault("events", []).append({
                        "timestamp": job["finished_at"],
                        "stage": "failed",
                        "detail": job["fatal_error"],
                    })
                    continue
                job["status"] = "queued"
                job["started_at"] = None
                job.setdefault("events", []).append({
                    "timestamp": iso_now(),
                    "stage": "resumed",
                    "detail": "Vector build restored from durable server-side spool after restart.",
                })
                to_resume.append(job_id)
        self._persist_all_jobs()
        for job_id in to_resume:
            self._executor.submit(self._run_from_spool, job_id)

    def create(self, body: UpsertJobCreate, *, owner: str | None = None) -> dict[str, Any]:
        # Large corpus syncs are durable background operations. Admit only one
        # full-record payload at a time so a queue of huge browser submissions
        # cannot retain several corpora in process memory simultaneously.
        with self._lock:
            active = next((
                job for job in self._jobs.values()
                if job.get("status") in {"queued", "running", "cancelling"}
            ), None)
            if active is not None:
                raise ValueError(
                    f"Another vector sync is already active ({active.get('label') or active.get('id')}). "
                    "Wait for it to finish or cancel it before starting another sync."
                )
        job_id = str(uuid.uuid4())
        snapshot_hasher = hashlib.sha256()
        source_works = list(dict.fromkeys([*(body.source_works or []), *[
            str(item.record.get("work") or "").strip()
            for item in body.items if str(item.record.get("work") or "").strip()
        ]]))
        for item in sorted(body.items, key=lambda value: str(value.chroma_id or value.key)):
            snapshot_hasher.update(str(item.chroma_id or item.key).encode("utf-8", errors="replace"))
            snapshot_hasher.update(b"\0")
            snapshot_hasher.update(str(item.fingerprint or "").encode("utf-8", errors="replace"))
            snapshot_hasher.update(b"\n")
        source_snapshot_hash = snapshot_hasher.hexdigest()
        job = {
            "id": job_id,
            "type": "upsert",
            "mode": "upsert",
            "owner": owner,
            "provider": "chroma",
            "model": None,
            "store_name": body.store_name,
            "label": body.label or "records",
            "source_kind": body.source_kind,
            "source_label": body.source_label,
            "source_works": source_works,
            "source_snapshot_hash": source_snapshot_hash,
            "status": "queued",
            "created_at": iso_now(),
            "started_at": None,
            "finished_at": None,
            "total": len(body.items),
            "completed": 0,
            "failed": 0,
            "cancel_requested": False,
            "cancel_requested_at": None,
            "current_record_id": None,
            "request": {
                "store_name": body.store_name,
                "label": body.label,
                "records": len(body.items),
                "batch_size": body.batch_size,
                "mirror_languages": body.mirror_languages,
                "document_field": body.document_field,
                "embedding_field": body.embedding_field,
                "source_kind": body.source_kind,
                "source_label": body.source_label,
                "source_works": source_works,
                "source_snapshot_hash": source_snapshot_hash,
            },
            "events": [{
                "timestamp": iso_now(),
                "stage": "queued",
                "detail": f"{len(body.items)} records queued for {body.store_name}",
            }],
            "results": [],
            "mirrored": {},
        }
        # Persist the full request body to disk before scheduling the worker.
        # The in-memory job record intentionally keeps only a compact request
        # summary, while the spool makes large builds restart-resumable without
        # retaining an entire corpus payload in the executor closure.
        self._write_spool(job_id, body)
        try:
            self._store.set_build_status(body.store_name, "queued")
            with self._lock:
                self._jobs[job_id] = job
            self._persist_job(job_id)
            self._executor.submit(self._run_from_spool, job_id)
        except Exception as exc:
            self._remove_spool(job_id)
            try:
                self._store.fail_sync(body.store_name, "Vector build could not be queued.")
            except Exception as sync_exc:
                raise RuntimeError(
                    f"Vector build could not be queued ({exc}); collection failure status "
                    f"could not be persisted ({sync_exc})."
                ) from exc
            raise
        return self.get(job_id)

    def _run(self, job_id: str, body: UpsertJobCreate) -> None:
        with self._lock:
            job = self._jobs[job_id]
            if job["cancel_requested"] or job["status"] == "cancelled":
                self._remove_spool(job_id)
                return
            job["status"] = "running"
            job["started_at"] = iso_now()
            job["events"].append({
                "timestamp": job["started_at"],
                "stage": "running",
                "detail": f"Upsert into {body.store_name} started",
            })

        try:
            build = self._store.begin_sync(
                body.store_name,
                source_kind=body.source_kind,
                source_label=body.source_label or body.label,
                source_record_count=len(body.items),
                source_works=list(job.get("source_works") or []),
                source_snapshot_hash=job.get("source_snapshot_hash"),
            )
            with self._lock:
                job = self._jobs[job_id]
                job["build_id"] = build.get("build_id")
                job["events"].append({
                    "timestamp": iso_now(),
                    "stage": "preflight",
                    "detail": f"Embedding contract validated · build {job.get('build_id') or ''}",
                })
            for start in range(0, len(body.items), body.batch_size):
                with self._lock:
                    job = self._jobs[job_id]
                    if job["cancel_requested"]:
                        job["status"] = "cancelled"
                        break

                batch_items = body.items[start:start + body.batch_size]
                records: list[dict[str, Any]] = []
                audit_entries_by_id: dict[str, list[dict[str, Any]]] = {}
                replace_updates_by_id: dict[str, list[dict[str, Any]]] = {}
                for item in batch_items:
                    record = dict(item.record)
                    record.pop("updates", None)
                    if item.fingerprint:
                        record[ChromaStore._RECORD_FINGERPRINT_KEY] = str(item.fingerprint)
                    if item.chroma_id:
                        record["_chroma_id"] = item.chroma_id
                    chroma_id = item.chroma_id or str(record.get("_chroma_id") or record.get("record_id") or "")
                    if item.audit_entries and chroma_id:
                        audit_entries_by_id[chroma_id] = [dict(entry) for entry in item.audit_entries]
                    if item.replace_updates is not None and chroma_id:
                        replace_updates_by_id[chroma_id] = [dict(entry) for entry in item.replace_updates]
                    records.append(record)

                first_id = batch_items[0].record.get("record_id") if batch_items else None
                last_id = batch_items[-1].record.get("record_id") if batch_items else None
                with self._lock:
                    job = self._jobs[job_id]
                    job["current_record_id"] = first_id
                    job["events"].append({
                        "timestamp": iso_now(),
                        "stage": "upserting",
                        "detail": f"Batch {start + 1}-{start + len(batch_items)}: {first_id or ''} … {last_id or ''}",
                    })

                result = self._store.upsert_with_language_sync(
                    body.store_name,
                    records,
                    document_field=body.document_field,
                    id_field="_chroma_id",
                    embedding_field=body.embedding_field,
                    mirror_languages=body.mirror_languages,
                    audit_entries_by_id=audit_entries_by_id,
                    replace_updates_by_id=replace_updates_by_id,
                )
                routes = result.get("language_sync", {}).get("record_routes", {})
                mirrored = result.get("language_sync", {}).get("mirrored", {})

                completed_at = iso_now()
                with self._lock:
                    job = self._jobs[job_id]
                    for name, count in mirrored.items():
                        job["mirrored"][name] = job["mirrored"].get(name, 0) + int(count or 0)
                    for item in batch_items:
                        chroma_id = item.chroma_id or str(item.record.get("record_id") or "")
                        job["results"].append({
                            "key": item.key,
                            "record_id": item.record.get("record_id"),
                            "fingerprint": item.fingerprint,
                            "chroma_id": chroma_id,
                            "store_name": body.store_name,
                            "mirrored_stores": list(routes.get(chroma_id, [])),
                            "completed_at": completed_at,
                            "updates_count": item.updates_count,
                            "audit_entries_appended": len(item.audit_entries or []),
                        })
                    job["completed"] += len(batch_items)
                    job["events"].append({
                        "timestamp": completed_at,
                        "stage": "batch_complete",
                        "detail": f"Committed {job['completed']} of {job['total']} records",
                    })

            with self._lock:
                job = self._jobs[job_id]
                cancelled = bool(job["cancel_requested"] or job["status"] == "cancelled")
                if not cancelled:
                    job["events"].append({
                        "timestamp": iso_now(),
                        "stage": "validating",
                        "detail": "Validating collection count and finalizing build manifest",
                    })
            if cancelled:
                self._store.finish_sync(body.store_name, status="stale")
            else:
                self._store.set_build_status(body.store_name, "validating")
                final_store = self._store.finish_sync(body.store_name, status="ready")
            with self._lock:
                job = self._jobs[job_id]
                job["status"] = "cancelled" if cancelled else "completed"
                job["current_record_id"] = None
                job["finished_at"] = iso_now()
                if not cancelled:
                    job["collection_manifest"] = final_store
                job["events"].append({
                    "timestamp": job["finished_at"],
                    "stage": job["status"],
                    "detail": f"{job['completed']} of {job['total']} records committed",
                })
        except Exception as exc:
            with self._lock:
                job = self._jobs[job_id]
                job["status"] = "failed"
                job["failed"] += 1
                _ = _store_job_error(job, exc)
                job["finished_at"] = iso_now()
            try:
                self._store.fail_sync(body.store_name, str(exc))
            except Exception as sync_exc:
                with self._lock:
                    job = self._jobs[job_id]
                    job["collection_status_sync_error"] = str(sync_exc)
                    job.setdefault("warnings", []).append(
                        f"Vector build failed, and the collection failure status could not be persisted: {sync_exc}"
                    )
            with self._lock:
                job = self._jobs[job_id]
                job["events"].append({
                    "timestamp": job["finished_at"],
                    "stage": "failed",
                    "detail": str(exc),
                })
        finally:
            self._persist_job(job_id)
            with self._lock:
                terminal = self._jobs.get(job_id, {}).get("status") not in {"queued", "running", "cancelling"}
            if terminal:
                self._remove_spool(job_id)

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            jobs = [self._copy(job, include_results=False) for job in self._jobs.values()]
        return sorted(jobs, key=lambda job: job["created_at"], reverse=True)

    def get(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return self._copy(self._jobs[job_id], include_results=True)

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                copy.deepcopy(self._copy(job, include_results=True))
                for job in self._jobs.values()
                if job.get("status") not in {"queued", "running", "cancelling"}
            ]

    def restore_snapshot(self, jobs: list[dict[str, Any]]) -> int:
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
                job.setdefault("results", [])
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
                job["events"].append({
                    "timestamp": job["cancel_requested_at"],
                    "stage": "cancelled",
                    "detail": "Cancelled while queued",
                })
            elif job["status"] == "running" and not job["cancel_requested"]:
                job["cancel_requested"] = True
                job["cancel_requested_at"] = iso_now()
                job["status"] = "cancelling"
                job["events"].append({
                    "timestamp": job["cancel_requested_at"],
                    "stage": "cancellation_requested",
                    "detail": "Cancellation requested; the current Chroma batch will finish, then the operation will stop.",
                })
            job_repository.upsert(copy.deepcopy(job))
            result = self._copy(job, include_results=True)
        if result.get("status") == "cancelled":
            self._remove_spool(job_id)
        return result

    def delete(self, job_id: str) -> None:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            if self._jobs[job_id]["status"] in {"queued", "running", "cancelling"}:
                raise ValueError("Running jobs must be cancelled before they can be removed.")
            del self._jobs[job_id]
            job_repository.delete(job_id)
        self._remove_spool(job_id)

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for job in self._jobs.values() if job["status"] in {"queued", "running", "cancelling"})

    def clear_finished(self) -> int:
        with self._lock:
            ids = [job_id for job_id, job in self._jobs.items() if job["status"] not in {"queued", "running", "cancelling"}]
            for job_id in ids:
                del self._jobs[job_id]
            job_repository.clear_finished(self.JOB_TYPE)
        for job_id in ids:
            self._remove_spool(job_id)
        return len(ids)

    @staticmethod
    def _copy(job: dict[str, Any], *, include_results: bool) -> dict[str, Any]:
        out = {key: value for key, value in job.items() if key != "results"}
        if include_results:
            out["results"] = list(job["results"])
        elif "events" in out:
            out["events"] = list(out.get("events") or [])[-12:]
        return out
