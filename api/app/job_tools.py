# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import copy
import re
import threading
import uuid
from typing import Any

from .chroma_store import ChromaStore
from .content_policy_generation import generate_policy_for_installed_language
from .i18n_translation import (
    LanguageTranslationError,
    LanguageTranslationInterrupted,
    translate_english_dictionary,
)
from .job_state import JobPayloadList, PersistentJobStateMixin, iso_now, store_job_error
from .llm_tools import run_pdf_llm, run_rag_grade, run_work_metadata_batch
from .models import LLMToolJobCreate, RAGGradeRequest
from .persistence import job_repository
from .system_store import normalize_locale_code, system_store


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
        if body.task == "language_content_policy" and body.language is None:
            raise ValueError("Researcher text policy jobs require a language payload.")

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
        elif body.task == "language_content_policy":
            total = 1

        job_id = str(uuid.uuid4())
        label = body.label or {
            "pdf_clean_text": "PDF · clean text",
            "pdf_draft_record": "PDF · draft record",
            "pdf_link_record": "PDF · link record",
            "rag_grade": "RAG · grade response",
            "rag_grade_batch": "RAG · grade response cache",
            "work_metadata": "Works · populate metadata",
            "language_dictionary": "Languages · translate dictionary",
            "language_content_policy": "Languages · researcher text policy",
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

    @staticmethod
    def _language_provider(body: LLMToolJobCreate) -> tuple[str, str, str | None, str | None]:
        """Choose the provider, model, endpoint, and API key for a language job.

        Two places can hold the OpenAI key. An administrator's profile keeps it in
        the browser and sends it on the request. A profile published for researchers
        keeps it on the server, and the browser never receives it. A key on the
        request wins. When the request omits the key, the stored profile is used.
        An empty browser value must not hide a stored key.
        """
        config = body.language
        assert config is not None
        stored = {}
        if body.provider_profile_id:
            stored = system_store.researcher_profile(body.provider_profile_id) or {}
        provider = str(stored.get("type") or config.provider)
        model = str(config.model or stored.get("model") or "").strip()
        base_url = config.base_url or stored.get("base_url")
        api_key = config.api_key or stored.get("api_key")
        return provider, model, base_url, api_key

    def _run_language_dictionary(self, job_id: str, body: LLMToolJobCreate) -> dict[str, Any]:
        assert body.language is not None
        config = body.language
        code = normalize_locale_code(config.code)
        if system_store.get_language(code) is not None:
            raise ValueError(f"Locale {code} is already installed. Edit the existing dictionary or remove it before reinstalling.")
        base = system_store.get_language("en-US") or {"dictionary": {}}
        dictionary = dict(base.get("dictionary") or {})

        provider, model, base_url, api_key = self._language_provider(body)
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
        policy_result = self._generate_language_content_policy(
            job_id,
            code=code,
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
            generation=config.generation,
            cancelled=cancelled,
        )
        return {
            "code": str(saved.get("code") or code),
            "name": str(saved.get("name") or config.name or code),
            "flag": str(saved.get("flag") or config.flag or "🌐"),
            **stats,
            **policy_result,
        }

    def _generate_language_content_policy(
        self,
        job_id: str,
        *,
        code: str,
        provider: str,
        model: str,
        base_url: str | None,
        api_key: str | None,
        generation: Any,
        cancelled: Any,
    ) -> dict[str, Any]:
        with self._lock:
            job = self._jobs[job_id]
            job["stage"] = "content_policy"
            job["stage_detail"] = f"Generating researcher text policy for {code}"
            job["events"].append({
                "timestamp": iso_now(),
                "stage": "content_policy",
                "detail": f"Generating researcher text policy for {code}",
            })
        try:
            policy = generate_policy_for_installed_language(
                code=code,
                provider=provider,
                model=model,
                base_url=base_url,
                api_key=api_key,
                generation=generation,
                cancelled=cancelled,
            )
            saved = system_store.put_content_policy(code, policy)
        except Exception as exc:
            return {
                "content_policy_ready": False,
                "content_policy_error": str(exc),
                "term_count": 0,
                "contextual_count": 0,
            }
        return {
            "content_policy_ready": True,
            "term_count": len(saved.get("blocked_terms") or []),
            "contextual_count": len(saved.get("contextual_terms") or []),
        }

    def _run_language_content_policy(self, job_id: str, body: LLMToolJobCreate) -> dict[str, Any]:
        assert body.language is not None
        config = body.language
        code = normalize_locale_code(config.code)
        if system_store.get_language(code) is None:
            raise ValueError(f"Locale {code} is not installed. Install the dictionary before generating its researcher text policy.")
        provider, model, base_url, api_key = self._language_provider(body)
        if not model:
            raise ValueError("Select a model to generate the researcher text policy.")

        def cancelled() -> bool:
            with self._lock:
                return bool(self._jobs[job_id]["cancel_requested"])

        policy_result = self._generate_language_content_policy(
            job_id,
            code=code,
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
            generation=config.generation,
            cancelled=cancelled,
        )
        if not policy_result.get("content_policy_ready"):
            raise ValueError(policy_result.get("content_policy_error") or "Researcher text policy generation failed.")
        language = system_store.get_language(code) or {}
        return {
            "code": code,
            "name": str(language.get("name") or config.name or code),
            "flag": str(language.get("flag") or config.flag or "🌐"),
            **policy_result,
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
                elif body.task == "language_content_policy":
                    result = self._run_language_content_policy(job_id, body)
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
                        if body.task not in {"rag_grade_batch", "work_metadata", "language_dictionary", "language_content_policy"}:
                            job["completed"] = 1
                        elif body.task in {"work_metadata", "language_dictionary", "language_content_policy"}:
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
                    details = store_job_error(job, exc)
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

    def list(self) -> JobPayloadList:
        with self._lock:
            jobs = [self._copy(job, False) for job in self._jobs.values()]
        return sorted(jobs, key=lambda job: job["created_at"], reverse=True)

    def get(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return self._copy(self._jobs[job_id], True)

    def snapshot(self) -> JobPayloadList:
        # Raw copies intentionally retain hidden language-translation checkpoints
        # so a full backup can restore an incomplete/resumable dictionary job.
        with self._lock:
            return [
                copy.deepcopy(job)
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

