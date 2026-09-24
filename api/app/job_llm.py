# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import copy
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .job_state import JobPayloadList, PersistentJobStateMixin, iso_now, store_job_error
from .llm import TouchupFailure, propose_touchup
from .models import LLMJobCreate
from .persistence import job_repository


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
                store_job_error(job, exc)
                job["finished_at"] = iso_now()

    def _is_cancel_requested(self, job_id: str) -> bool:
        with self._lock:
            return bool(self._jobs.get(job_id, {}).get("cancel_requested"))

    def list(self) -> JobPayloadList:
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
        items: JobPayloadList,
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

            kept: JobPayloadList = []
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
                len((result.get("proposal") or {}).get("changes") or {})
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

    def snapshot(self) -> JobPayloadList:
        with self._lock:
            return [
                copy.deepcopy(self._copy(job, include_results=True))
                for job in self._jobs.values()
                if job.get("status") not in {"queued", "running", "cancelling"}
                and not job.get("dismissed")
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
            len((result.get("proposal") or {}).get("changes") or {})
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

