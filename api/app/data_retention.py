# Copyright 2026 Aaron John Schlosser, PhD.
"""Retention for operational data stores.

Only operational history is eligible: pipeline traces (one store per feature),
pipeline benchmark results, finished job history, and saved Research
responses (the Response Library). Canonical scholarly data (corpus records,
reviews, field assertions, metadata exemplars, validated claims, response
memory, pipeline definitions, benchmark cases, users) never expires and is
not represented here.

A policy is system-wide with optional per-store overrides. Each rule keeps
everything, removes records older than N days, or caps a store at N gigabytes
(decimal: 1 GB = 1,000,000,000 bytes of stored payload) by removing the oldest
records first. Records another retained record depends on are pinned and never
removed: a Research pipeline trace stays while its Research job exists, and
active jobs are never touched. The default keeps everything.
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)

SETTING_KEY = "data_retention"
GIGABYTE = 1_000_000_000
BATCH = 500
ACTIVE_JOB_STATUSES = frozenset({"queued", "running", "cancelling"})
RESEARCH_TRACE_FEATURE = "research"

Mode = Literal["inherit", "keep", "max_age_days", "max_size_gb"]


class RetentionRule(BaseModel):
    mode: Mode = "inherit"
    value: float | None = None

    @model_validator(mode="after")
    def _check_value(self) -> RetentionRule:
        if self.mode == "max_age_days":
            if self.value is None or self.value != int(self.value) or not 1 <= self.value <= 36500:
                raise ValueError("Days must be a whole number from 1 to 36500.")
        elif self.mode == "max_size_gb":
            if self.value is None or not 0.001 <= self.value <= 100000:
                raise ValueError("Gigabytes must be between 0.001 and 100000.")
        elif self.value is not None:
            raise ValueError("Only day and size limits take a value.")
        return self


class RetentionPolicy(BaseModel):
    default: RetentionRule = Field(default_factory=lambda: RetentionRule(mode="keep"))
    stores: dict[str, RetentionRule] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_default(self) -> RetentionPolicy:
        if self.default.mode == "inherit":
            raise ValueError("The system-wide policy cannot inherit.")
        return self

    def effective(self, store_id: str) -> RetentionRule:
        rule = self.stores.get(store_id)
        return self.default if rule is None or rule.mode == "inherit" else rule


@dataclass(frozen=True)
class RetentionItem:
    key: str
    created_at: datetime | None
    size: int
    pinned: bool = False


class OperationalStore:
    """One expirable store. Subclasses list their records and delete by key."""

    store_id: str
    kind: str
    feature: str | None = None

    def items(self) -> list[RetentionItem]:
        raise NotImplementedError

    def delete(self, keys: list[str]) -> int:
        raise NotImplementedError


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _batches(keys: list[str]) -> Iterable[list[str]]:
    for start in range(0, len(keys), BATCH):
        yield keys[start:start + BATCH]


class PipelineTraceRetention(OperationalStore):
    kind = "pipeline_traces"

    def __init__(self, database: Any, feature: str, pinned_ids: Callable[[], set[str]]) -> None:
        self.database = database
        self.feature = feature
        self.store_id = f"pipeline_traces:{feature}"
        self._pinned_ids = pinned_ids

    def items(self) -> list[RetentionItem]:
        pinned = self._pinned_ids() if self.feature == RESEARCH_TRACE_FEATURE else set()
        with self.database.lock, self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT r.run_id, r.started_at,
                       LENGTH(r.payload_json) + COALESCE(
                           (SELECT SUM(LENGTH(s.payload_json)) FROM pipeline_stage_runs s
                            WHERE s.run_id = r.run_id), 0) AS size
                FROM pipeline_runs r WHERE r.feature = ?
                """,
                (self.feature,),
            ).fetchall()
        return [
            RetentionItem(str(row["run_id"]), _parse_time(row["started_at"]), int(row["size"] or 0),
                          str(row["run_id"]) in pinned)
            for row in rows
        ]

    def delete(self, keys: list[str]) -> int:
        removed = 0
        with self.database.lock, self.database.connect() as conn:
            for batch in _batches(keys):
                marks = ",".join("?" for _ in batch)
                # Stage rows cascade from their run (foreign_keys=ON).
                cursor = conn.execute(
                    f"DELETE FROM pipeline_runs WHERE feature = ? AND run_id IN ({marks})",  # noqa: S608
                    (self.feature, *batch),
                )
                removed += int(cursor.rowcount or 0)
            conn.commit()
        return removed


class BenchmarkRunRetention(OperationalStore):
    kind = "pipeline_benchmark_runs"
    store_id = "pipeline_benchmark_runs"

    def __init__(self, database: Any) -> None:
        self.database = database

    def items(self) -> list[RetentionItem]:
        with self.database.lock, self.database.connect() as conn:
            rows = conn.execute(
                "SELECT benchmark_run_id, created_at, LENGTH(payload_json) AS size FROM pipeline_benchmark_runs"
            ).fetchall()
        return [
            RetentionItem(str(row["benchmark_run_id"]), _parse_time(row["created_at"]), int(row["size"] or 0))
            for row in rows
        ]

    def delete(self, keys: list[str]) -> int:
        removed = 0
        with self.database.lock, self.database.connect() as conn:
            for batch in _batches(keys):
                marks = ",".join("?" for _ in batch)
                cursor = conn.execute(
                    f"DELETE FROM pipeline_benchmark_runs WHERE benchmark_run_id IN ({marks})",  # noqa: S608
                    batch,
                )
                removed += int(cursor.rowcount or 0)
            conn.commit()
        return removed


class JobHistoryRetention(OperationalStore):
    """Finished jobs, removed through each manager so memory and SQLite stay consistent.

    Managers re-save their in-memory jobs every second, so deleting rows alone
    would bring them back. Active jobs are never candidates.
    """

    kind = "job_history"
    store_id = "job_history"

    def __init__(self, managers: Callable[[], list[Any]]) -> None:
        self._managers = managers

    def items(self) -> list[RetentionItem]:
        out = []
        for manager in self._managers():
            for job_id, created_at, size, active in manager.job_footprints():
                out.append(RetentionItem(f"{manager.JOB_TYPE}:{job_id}", _parse_time(created_at), size, active))
        return out

    def delete(self, keys: list[str]) -> int:
        by_type: dict[str, list[str]] = {}
        for key in keys:
            job_type, _, job_id = key.partition(":")
            by_type.setdefault(job_type, []).append(job_id)
        removed = 0
        for manager in self._managers():
            for job_id in by_type.get(manager.JOB_TYPE, []):
                try:
                    manager.delete(job_id)
                except (KeyError, ValueError):
                    continue  # already gone, or became active since planning
                removed += 1
        return removed


class ResponseCacheRetention(OperationalStore):
    """Saved Research responses (the Response Library's ``_response_cache`` collection)."""

    kind = "response_cache"
    store_id = "response_cache"

    def __init__(self, collection: Callable[[], Any | None]) -> None:
        self._collection = collection

    def items(self) -> list[RetentionItem]:
        from .chroma_store import decode_metadata

        collection = self._collection()
        if collection is None:
            return []
        payload = collection.get(include=["documents", "metadatas"])
        ids = list(payload.get("ids") or [])
        documents = list(payload.get("documents") or [])
        metadatas = list(payload.get("metadatas") or [])
        vector_bytes = 0
        if ids:
            sample = collection.get(ids=[ids[0]], include=["embeddings"]).get("embeddings")
            if sample is not None and len(sample) and sample[0] is not None:
                vector_bytes = 4 * len(sample[0])
        out = []
        for index, chroma_id in enumerate(ids):
            raw_meta = metadatas[index] if index < len(metadatas) else {}
            meta = decode_metadata(raw_meta or {})
            document = documents[index] if index < len(documents) else ""
            size = len(str(document or "").encode()) + len(json.dumps(raw_meta or {}, default=str).encode()) + vector_bytes
            out.append(RetentionItem(str(chroma_id), _parse_time(meta.get("created_at") or meta.get("updated_at")), size))
        return out

    def delete(self, keys: list[str]) -> int:
        collection = self._collection()
        if collection is None:
            return 0
        for batch in _batches(keys):
            collection.delete(ids=batch)
        return len(keys)


def plan(items: list[RetentionItem], rule: RetentionRule, *, now: datetime) -> dict[str, Any]:
    """Which records a rule removes. Unknown ages are kept by age rules and removed last by size caps."""

    total_bytes = sum(item.size for item in items)
    report: dict[str, Any] = {
        "count": len(items),
        "bytes": total_bytes,
        "pinned_count": sum(item.pinned for item in items),
        "oldest_at": min((item.created_at for item in items if item.created_at), default=None),
        "remove_keys": [],
        "remove_bytes": 0,
        "warnings": [],
    }
    candidates = [item for item in items if not item.pinned]
    if rule.mode == "max_age_days":
        cutoff = now - timedelta(days=int(rule.value or 0))
        chosen = [item for item in candidates if item.created_at is not None and item.created_at < cutoff]
    elif rule.mode == "max_size_gb":
        cap = int(float(rule.value or 0) * GIGABYTE)
        ordered = sorted(candidates, key=lambda item: (item.created_at is None, item.created_at or now))
        chosen, remaining = [], total_bytes
        for item in ordered:
            if remaining <= cap:
                break
            chosen.append(item)
            remaining -= item.size
        if remaining > cap:
            report["warnings"].append("pinned_exceeds_cap")
    else:
        chosen = []
    report["remove_keys"] = [item.key for item in chosen]
    report["remove_bytes"] = sum(item.size for item in chosen)
    return report


class RetentionService:
    def __init__(
        self,
        *,
        settings_repository: Any,
        pipeline_database: Any,
        job_managers: Callable[[], list[Any]],
        response_cache_collection: Callable[[], Any | None],
        known_trace_features: Callable[[], list[str]],
    ) -> None:
        self.settings = settings_repository
        self.database = pipeline_database
        self.job_managers = job_managers
        self.response_cache_collection = response_cache_collection
        self.known_trace_features = known_trace_features
        self._apply_lock = threading.Lock()

    def policy(self) -> RetentionPolicy:
        raw = self.settings.get_setting(SETTING_KEY)
        if not isinstance(raw, dict):
            return RetentionPolicy()
        try:
            return RetentionPolicy.model_validate(raw)
        except ValueError:
            logger.warning("Stored data-retention policy is invalid; keeping all operational data.")
            return RetentionPolicy()

    def save_policy(self, policy: RetentionPolicy) -> RetentionPolicy:
        known = {store.store_id for store in self.stores()}
        unknown = sorted(set(policy.stores) - known)
        if unknown:
            raise ValueError("Unknown data store(s): " + ", ".join(unknown))
        stores = {key: rule for key, rule in policy.stores.items() if rule.mode != "inherit"}
        clean = RetentionPolicy(default=policy.default, stores=stores)
        self.settings.put_setting(SETTING_KEY, clean.model_dump(mode="json"))
        return clean

    def _research_job_ids(self) -> set[str]:
        return {
            str(job_id)
            for manager in self.job_managers()
            if getattr(manager, "JOB_TYPE", "") == "rag"
            for job_id, *_ in manager.job_footprints()
        }

    def stores(self) -> list[OperationalStore]:
        with self.database.lock, self.database.connect() as conn:
            present = [str(row[0]) for row in conn.execute("SELECT DISTINCT feature FROM pipeline_runs")]
        features = sorted(set(present) | set(self.known_trace_features()))
        return [
            *(PipelineTraceRetention(self.database, feature, self._research_job_ids) for feature in features),
            BenchmarkRunRetention(self.database),
            JobHistoryRetention(self.job_managers),
            ResponseCacheRetention(self.response_cache_collection),
        ]

    def overview(self, *, now: datetime | None = None) -> dict[str, Any]:
        """Policy plus each store's size and what its effective rule would remove now."""
        return self._run(dry_run=True, now=now)

    def apply(self, *, now: datetime | None = None, store_ids: set[str] | None = None) -> dict[str, Any]:
        with self._apply_lock:
            return self._run(dry_run=False, now=now, store_ids=store_ids)

    def _run(self, *, dry_run: bool, now: datetime | None = None, store_ids: set[str] | None = None) -> dict[str, Any]:
        policy = self.policy()
        moment = now or datetime.now(UTC)
        rows = []
        for store in self.stores():
            if store_ids is not None and store.store_id not in store_ids:
                continue
            rule = policy.effective(store.store_id)
            row: dict[str, Any] = {
                "store_id": store.store_id,
                "kind": store.kind,
                "feature": store.feature,
                "rule": (policy.stores.get(store.store_id) or RetentionRule()).model_dump(mode="json"),
                "effective_rule": rule.model_dump(mode="json"),
            }
            try:
                report = plan(store.items(), rule, now=moment)
            except Exception as exc:  # noqa: BLE001 - one unreadable store must not hide the others
                logger.warning("Could not read data store %s for retention: %s", store.store_id, exc)
                rows.append({**row, "error": f"{type(exc).__name__}: {exc}"[:300]})
                continue
            keys = report.pop("remove_keys")
            report["remove_count"] = len(keys)
            if report["oldest_at"] is not None:
                report["oldest_at"] = report["oldest_at"].isoformat()
            if not dry_run and keys:
                try:
                    report["removed_count"] = store.delete(keys)
                except Exception as exc:  # noqa: BLE001 - reported per store
                    logger.warning("Could not apply retention to %s: %s", store.store_id, exc)
                    report["error"] = f"{type(exc).__name__}: {exc}"[:300]
                else:
                    logger.info("Data retention removed %s record(s) from %s.", report["removed_count"], store.store_id)
            rows.append({**row, **report})
        return {
            "policy": policy.model_dump(mode="json"),
            "evaluated_at": moment.isoformat(),
            "applied": not dry_run,
            "stores": rows,
        }

    def reclaim_disk_space(self) -> dict[str, Any]:
        """VACUUM the system database so removed rows give their space back to the disk."""
        path = self.database.path

        def on_disk() -> int:
            # WAL mode keeps recent writes beside the main file until a checkpoint.
            return sum(
                candidate.stat().st_size
                for candidate in (path, path.with_name(path.name + "-wal"))
                if candidate.exists()
            )

        before = on_disk()
        with self._apply_lock, self.database.lock, self.database.connect() as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.execute("VACUUM")
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        return {"bytes_before": before, "bytes_after": on_disk()}


class RetentionScheduler:
    """Apply the stored policy shortly after startup and then hourly."""

    def __init__(self, service: Callable[[], RetentionService], *, interval: float = 3600.0, delay: float = 60.0) -> None:
        self._service = service
        self.interval = interval
        self.delay = delay
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="derridai-data-retention")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._thread = None

    def tick(self) -> None:
        service = self._service()
        policy = service.policy()
        if policy.default.mode == "keep" and all(rule.mode in {"keep", "inherit"} for rule in policy.stores.values()):
            return
        service.apply()

    def _run(self) -> None:
        if self._stop.wait(self.delay):
            return
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:
                logger.exception("Scheduled data retention failed; will retry")
            self._stop.wait(self.interval)
