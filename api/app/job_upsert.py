# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .chroma_store import ChromaStore
from .config import settings
from .job_state import JobPayloadList, PersistentJobStateMixin, iso_now, store_job_error
from .models import UpsertJobCreate
from .persistence import job_repository


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
                    store_job_error(job, RuntimeError(f"Could not restore vector-build payload: {exc}"))
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
                records: JobPayloadList = []
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
                _ = store_job_error(job, exc)
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

    def list(self) -> JobPayloadList:
        with self._lock:
            jobs = [self._copy(job, include_results=False) for job in self._jobs.values()]
        return sorted(jobs, key=lambda job: job["created_at"], reverse=True)

    def get(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return self._copy(self._jobs[job_id], include_results=True)

    def snapshot(self) -> JobPayloadList:
        with self._lock:
            return [
                copy.deepcopy(self._copy(job, include_results=True))
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

    def clear_all(self) -> int:
        count = super().clear_all()
        shutil.rmtree(self._spool_dir, ignore_errors=True)
        self._spool_dir.mkdir(parents=True, exist_ok=True)
        return count

    @staticmethod
    def _copy(job: dict[str, Any], *, include_results: bool) -> dict[str, Any]:
        out = {key: value for key, value in job.items() if key != "results"}
        if include_results:
            out["results"] = list(job["results"])
        elif "events" in out:
            out["events"] = list(out.get("events") or [])[-12:]
        return out

