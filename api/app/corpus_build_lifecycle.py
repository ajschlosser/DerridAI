# Copyright 2026 Aaron John Schlosser, PhD.
"""Build lifecycle and provider session management: create/resume, second opinions, recheck, autonomous runs.

Starting, resuming, and switching the LLM provider profile of a build; second-opinion
and recheck workflows for blind review; transport-error retry with backoff; and
autonomous (unattended) run start/settle. Moved verbatim out of PdfCorpusBuildManager
as a mixin (see corpus_review_actions.py's module docstring for why a mixin, not free
functions, is the right tool for a cluster that calls a dozen-plus other self.*
members).

`create` and `preview_schema_group` were NOT moved here despite being part of the same
originally-planned cluster: both reference CORPUS_PROFILES/PROFILE_VERSION (`create`)
or build_group_prompt/response_model_for/SchemaNotFound in a way still entangled with
corpus_builder.py's own module-level constants -- left in place for the same
circular-import reason documented during the 0.70 decomposition for validate_records/
_refresh_workflow_fields.
"""

from __future__ import annotations

import json
import time
import urllib.request
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from . import experiment
from .autonomous import Policy as AutonomousPolicy
from .autonomous import may_accept, settle_record
from .config import settings
from .corpus_llm_helpers import (
    _is_transport_error,
    _validate_execution_budget,
)
from .corpus_record_quality import iso_now
from .corpus_review_actions import _serialize_record_mutation
from .corpus_review_state import _sync_record_metadata_state
from .corpus_reviewer_helpers import _human_touched
from .enrichment_ledger import RECHECK, RECHECK_SEAL
from .error_severity import severity as error_severity
from .field_assertions import (
    current_assertion_by_name,
    migrate_record_assertions,
    project_record_assertions,
    reopen_assertion,
)
from .reviewer_context import current_reviewer


def _same_label(a: Any, b: Any) -> bool:
    return json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)


class BuildLifecycleMixin:
    """Mixin members declared here exist on PdfCorpusBuildManager, not on this mixin itself.

    See corpus_review_actions.py's identical block for the full explanation of why these
    stubs exist. The method stubs are wrapped in `if TYPE_CHECKING:` deliberately: a bare
    `def name(self): ...` at class-body level (not guarded) would be a real, empty method
    at runtime, and since Python's MRO resolves left-to-right across
    PdfCorpusBuildManager's base classes, a stub here for a name whose REAL implementation
    lives in a mixin listed LATER in `class PdfCorpusBuildManager(BuildLifecycleMixin,
    ReviewActionsMixin, EnrichmentRerunsMixin):` would silently shadow it -- exactly what
    happened to `rerun_metadata_enrichment` (real implementation in EnrichmentRerunsMixin)
    the first time this file was written without the guard: calling it silently no-opped
    instead of running, breaking 7 tests with no import error or type error to catch it.
    `TYPE_CHECKING` is always False at runtime, so these defs never execute and never
    become real attributes; mypy still evaluates them (it treats TYPE_CHECKING as True)
    and gets the same signatures as before. Bare attribute annotations (`repo: Any`, with
    no `=` assignment) do not have this problem -- they never create a runtime attribute
    either way -- but are kept inside the same guard for consistency.
    """

    if TYPE_CHECKING:
        repo: Any
        _lock: Any
        _executor: Any
        _ledger: Any
        _cancel: set[str]
        _runtime_requests: dict[str, dict[str, Any]]
        _llm_inflight: dict[str, dict[int, dict[str, Any]]]
        _llm_call_sequence: int
        _loaded_models_cache: tuple[float, str, set[str]]
        _provider_epoch: dict[str, int]
        _schemas: Any

        def _cancelled(self, build_id: str) -> bool: ...
        def _update(self, build_id: str, **changes: Any) -> dict[str, Any]: ...
        def _increment_metric(self, build_id: str, key: str, amount: int = 1) -> None: ...
        def _rewrite_and_validate(self, build_id: str, records: list[dict[str, Any]], *, persist_records: bool = True) -> dict[str, Any]: ...
        def _profile_for(self, build_id: str) -> dict[str, Any]: ...
        def _run(self, build_id: str, request: dict[str, Any], resume: bool = False) -> None: ...
        def publish(self, build_id: str, *, require_acceptance: bool = True) -> dict[str, Any]: ...
        def rerun_metadata_enrichment(self, build_id: str, request: dict[str, Any]) -> dict[str, Any]: ...
        def _chat_json(
            self,
            request: dict[str, Any],
            prompt: str,
            *,
            response_model: type[BaseModel],
            max_tokens: int = 4096,
            schema_name: str = "derridai_corpus",
            attempts: int = 2,
            build_id: str = "",
        ) -> dict[str, Any]: ...


    def reset_in_memory_state(self) -> None:
        """Drop live cancel/runtime maps after the corpus tree has been deleted."""
        with self._lock:
            self._cancel.clear()
            self._runtime_requests.clear()


    def _mark_interrupted(self) -> None:
        listing = self.repo.list_builds(offset=0, limit=10000)
        for build in listing["items"]:
            if build.get("status") in {"queued", "running"}:
                build["status"] = "interrupted"
                build["stage"] = "interrupted"
                build["resumable"] = True
                build["error"] = "Build execution was interrupted by an API restart. Completed checkpoints were preserved; resume to continue."
                build["finished_at"] = iso_now()
                self.repo.save_build(build)


    def _latest_runtime_request(self, build_id: str, fallback: dict[str, Any]) -> dict[str, Any]:
        if not build_id:
            return dict(fallback)
        with self._lock:
            current = self._runtime_requests.get(build_id)
            return dict(current) if isinstance(current, dict) and current else dict(fallback)


    def _interactive_llm_request(self, build_id: str, override: dict[str, Any] | None = None) -> dict[str, Any]:
        """Resolve a user-triggered LLM call without replacing it with build runtime state.

        Build workers intentionally follow the latest build-level provider switch. Interactive
        actions are different: the provider/model selected in the dialog is authoritative for
        that invocation. Build policy/budgets are inherited only for keys the action did not
        provide.
        """
        build = self.repo.get_build(build_id) if build_id else {}
        base = self._latest_runtime_request(build_id, dict(build.get("request") or {})) if build_id else {}
        chosen = {k: v for k, v in dict(override or {}).items() if v is not None}
        if not chosen:
            return dict(base)
        merged = dict(base)
        merged.update(chosen)
        return merged


    def switch_provider_profile(self, build_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Change the provider used by metadata tasks scheduled after this point.

        In-flight requests are intentionally not interrupted. The execution ledger
        records the actual provider/model for every family, so mixed-model builds
        remain auditable. Resolved credentials are kept only in memory.
        """
        build = self.repo.get_build(build_id)
        if build.get("status") == "published":
            raise ValueError("Published builds are immutable; create a new build instead.")
        profile_id = str(request.get("provider_profile_id") or "").strip()
        if not profile_id:
            raise ValueError("Choose an LLM provider profile.")
        with self._lock:
            prior = dict(self._runtime_requests.get(build_id) or {})
            # Preserve corpus-build policy/budgets while replacing only provider
            # configuration and optional escalation provider.
            merged = dict(prior) if prior else dict(build.get("request") or {})
            for key in ("provider", "model", "base_url", "api_key", "generation", "provider_profile_id", "review_provider_profile_id", "_review_provider"):
                if key in request:
                    merged[key] = request[key]
                elif key in {"review_provider_profile_id", "_review_provider"} and key in merged and key not in request:
                    merged.pop(key, None)
            self._runtime_requests[build_id] = merged
            self._provider_epoch[build_id] = self._provider_epoch.get(build_id, 0) + 1
            public = dict(build.get("request") or {})
            for key in ("provider", "model", "base_url", "generation", "provider_profile_id", "review_provider_profile_id"):
                if key in merged:
                    public[key] = merged[key]
                elif key in {"review_provider_profile_id"} and key in public:
                    public.pop(key, None)
            public.pop("api_key", None)
            public.pop("_review_provider", None)
            build["request"] = public
            build["provider"] = merged.get("provider") or build.get("provider")
            build["model"] = merged.get("model") or build.get("model")
            history = list(build.get("provider_profile_history") or [])
            history.append({
                "at": iso_now(), "provider_profile_id": profile_id,
                "provider": build.get("provider"), "model": build.get("model"),
                "metadata_completed": int(build.get("metadata_completed") or 0),
                "note": "Applies to newly scheduled metadata tasks; in-flight requests continue unchanged.",
            })
            build["provider_profile_history"] = history[-50:]
            self.repo.save_build(build)
        return build


    def resume(self, build_id: str, request: dict[str, Any]) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        if build.get("status") in {"queued", "running"}:
            # Resume is intentionally idempotent while work is active. Stale
            # clients can safely repeat the action without creating a second
            # worker or surfacing an HTTP 422 for an operation already underway.
            return build
        if build.get("status") in {"published"}:
            raise ValueError("Published builds are immutable; create a new build instead.")
        _validate_execution_budget(request)

        # A resume is also the supported way to recover a blocked build with a
        # better model, larger context, or different stage budgets. Persist the
        # new public execution contract so Operations and provenance describe the
        # run that actually completed, while keeping secrets out of build.json.
        public_request = {k: v for k, v in request.items() if k not in {"api_key", "_review_provider"}}
        build["provider"] = request.get("provider") or build.get("provider") or "ollama"
        build["model"] = request.get("model") or build.get("model")
        build["request"] = public_request
        build["status"] = "queued"
        build["stage"] = "resuming"
        build["error"] = None
        build["resumable"] = True
        build["finished_at"] = None
        build["cancel_requested"] = False
        build["metadata_settle_requested"] = False
        build["operation_hidden"] = False
        with self._lock:
            self._cancel.discard(build_id)

        # If the previous attempt reached a topology guard (for example, a long
        # book returned valid-but-empty boundary arrays), successful-window caches
        # are not useful: retry the segmentation topology with the new settings.
        unresolved = list(build.get("segmentation_unresolved_regions") or [])
        build["retrying_segmentation"] = bool(build.get("segmentation_blocked"))
        if any(str(item.get("kind") or "").startswith("topology_guard") for item in unresolved if isinstance(item, dict)):
            self.repo.save_checkpoint(build_id, "segmentation_state", {})
            self.repo.save_checkpoint(build_id, "reconciliation_state", {})
            self.repo.save_checkpoint(build_id, "boundaries_partial", [])
        self.repo.save_build(build)
        with self._lock:
            self._runtime_requests[build_id] = dict(request)
        self._executor.submit(self._run, build_id, request, True)
        return build


    def confirm_manifest(self, build_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Confirm the document-level contract and continue into segmentation.

        Book-level bibliographic/page structure is deliberately reviewed before it
        can influence hundreds of records. Confirmation records the exact manifest
        revision and then resumes from the persisted manifest checkpoint.
        """
        build = self.repo.get_build(build_id)
        if build.get("status") in {"queued", "running"}:
            raise ValueError("Wait for the document-analysis stage to finish before confirming its manifest.")
        if build.get("status") == "published":
            raise ValueError("Published builds are immutable.")
        manifest = build.get("manifest")
        if not isinstance(manifest, dict) or not manifest:
            manifest = self.repo.load_checkpoint(build_id, "manifest")
        if not isinstance(manifest, dict) or not manifest:
            raise ValueError("This build does not yet have a document manifest to confirm.")
        build["manifest_confirmed_at"] = iso_now()
        build["manifest_confirmed_revision"] = int(build.get("manifest_revision") or 1)
        build["status"] = "awaiting_manifest_review"
        build["stage"] = "document_review"
        self.repo.save_build(build)
        return self.resume(build_id, request)


    def _request_second_opinion(self, build_id: str, record: dict[str, Any], field: str, value: Any) -> None:
        """Mark some decisions to be labelled again by a different reviewer, who will not see this answer."""
        reviewer = current_reviewer.get()
        if not reviewer or value in (None, "", []) or not experiment.needs_second_opinion(str(record.get("record_id") or ""), field, self._experiment_rate(build_id, "iaa_rate")):
            return
        # A later edit by the first reviewer replaces the answer, so an earlier second opinion no longer compares like with like.
        record.setdefault("second_opinion", {})[field] = {"first_reviewer": reviewer}


    def pending_second_opinions(self, build_id: str) -> list[dict[str, Any]]:
        """Fields the current reviewer is asked to label without seeing the first reviewer's answer."""
        me = current_reviewer.get()
        if not me:
            return []
        out = []
        for record in self.repo.load_records(build_id):
            for field, item in (record.get("second_opinion") or {}).items():
                if isinstance(item, dict) and not item.get("done") and item.get("first_reviewer") and item["first_reviewer"] != me:
                    out.append({"record_id": record.get("record_id"), "field": field, "text": record.get("text"), "page_start": record.get("page_start"), "page_end": record.get("page_end")})
        return out


    @_serialize_record_mutation
    def submit_second_opinion(self, build_id: str, record_id: str, field: str, value: Any) -> dict[str, Any]:
        me = current_reviewer.get()
        records = self.repo.load_records(build_id)
        record = next((r for r in records if r.get("record_id") == record_id), None)
        if record is None:
            raise KeyError(record_id)
        item = (record.get("second_opinion") or {}).get(field)
        if not isinstance(item, dict) or item.get("done") or not me or item.get("first_reviewer") == me:
            raise ValueError("There is no second opinion for you to give on this field.")
        agreed = self._log_second_opinion(build_id, record, field, value, item)
        self.repo.save_records(build_id, records)
        return {"record_id": record_id, "field": field, "agreed": agreed}


    def _log_second_opinion(self, build_id: str, record: dict[str, Any], field: str, value: Any, item: dict[str, Any]) -> bool:
        first = record.get(field)
        agreed = _same_label(first, value)
        self._ledger.append(
            "second_label", model="", field=field, build_id=build_id, record_id=str(record.get("record_id") or ""), value=first, new_value=value,
            agreed=agreed, first_reviewer=item["first_reviewer"], severity=None if agreed else error_severity(first, value),
        )
        item["done"] = True
        item["agreed"] = agreed
        return agreed


    def _experiment_rate(self, build_id: str, key: str) -> float:
        build = self.repo.get_build(build_id)
        for source in (build.get("experiment"), build.get("request")):
            if isinstance(source, dict) and source.get(key):
                return float(source[key])
        return 0.0


    def _recheck_rate(self, build_id: str) -> float:
        return self._experiment_rate(build_id, "recheck_rate")


    def _schedule_recheck(self, build_id: str, record: dict[str, Any], field: str, value: Any) -> None:
        """Pick some of a reviewer's decisions to be asked again later, blind."""
        if value in (None, "", []) or not experiment.is_recheck(str(record.get("record_id") or ""), field, self._recheck_rate(build_id)):
            return
        build = self.repo.get_build(build_id)
        due = int(build.get("human_decision_count") or 0) + experiment.RECHECK_SPACING
        record.setdefault("recheck_scheduled", {})[field] = {"due": due, "reviewer": current_reviewer.get()}


    def _reopen_due_rechecks(self, build_id: str, records: list[dict[str, Any]], just_decided: dict[str, Any], profile: dict[str, Any]) -> None:
        """Count this decision, then reopen, blind, any earlier decision whose turn has come."""
        build = self.repo.get_build(build_id)
        count = int(build.get("human_decision_count") or 0) + 1
        build["human_decision_count"] = count
        self.repo.save_build(build)
        for record in records:
            scheduled = record.get("recheck_scheduled")
            if record is just_decided or not isinstance(scheduled, dict):
                continue
            for field, item in list(scheduled.items()):
                if not isinstance(item, dict) or int(item.get("due") or 0) > count:
                    continue
                self._ledger.append(RECHECK_SEAL, model="", field=field, build_id=build_id, record_id=str(record.get("record_id") or ""), value=record.get(field), reviewer=str(item.get("reviewer") or ""))
                for entry in record.get("metadata_decisions") or []:
                    if isinstance(entry, dict) and entry.get("field") == field:
                        entry["value"] = None  # the earlier answer must not travel with the record
                        entry["sealed"] = True
                migrate_record_assertions(record)
                prior_assertion = current_assertion_by_name(record, field)
                record[field] = [] if isinstance(record.get(field), list) else None
                record.setdefault("metadata_field_status", {})[field] = {
                    "status": "unresolved", "method": "human_recheck", "recheck": True, "reason_code": "recheck", "auto_populated": False,
                    "reason": "",
                }
                if prior_assertion is not None:
                    reopen_assertion(
                        record,
                        prior_assertion,
                        reason="Reopened blind for a scheduled human recheck.",
                    )
                    project_record_assertions(record)
                    record[field] = [] if isinstance(prior_assertion.value, list) else None
                del scheduled[field]
                record["accepted"] = False
                record["needs_review"] = True
                _sync_record_metadata_state(record, profile)


    def _score_recheck(self, build_id: str, record: dict[str, Any], field: str, value: Any, prior_status: dict[str, Any]) -> bool:
        """If this decision answers a re-check, log whether it matches the first answer and reveal that answer."""
        if not prior_status.get("recheck"):
            return False
        record_id = str(record.get("record_id") or "")
        first = self._ledger.sealed_value(build_id, record_id, field, RECHECK_SEAL)
        agreed = first == value
        first_reviewer = self._ledger.sealed_value(build_id, record_id, field, RECHECK_SEAL, column="reviewer")
        # Self-consistency only means something when the same person answers both times.
        self._ledger.append(RECHECK, model="", field=field, build_id=build_id, record_id=record_id, value=first, new_value=value, agreed=agreed, first_reviewer=first_reviewer or "", same_reviewer=(first_reviewer or "") == current_reviewer.get(), severity=None if agreed else error_severity(first, value))
        record.setdefault("recheck_results", {})[field] = {"first": first, "second": value, "agreed": agreed}
        return True


    _TRANSPORT_PAUSES = (3.0, 8.0, 15.0)


    def _with_transport_retry(self, build_id: str, call: Callable[..., str], **kwargs: Any) -> str:
        """Run a model call, retrying with a growing pause when the connection itself fails.

        Restarting Ollama, or a model load being abandoned by whoever asked for it, drops every request waiting on
        it. Trying at once meets the same closed door, so wait a few seconds; a build should not fall back to a
        degraded result because a server was busy starting.
        """
        pauses = self._TRANSPORT_PAUSES
        for attempt in range(len(pauses) + 1):
            try:
                return call(**kwargs)
            except Exception as exc:  # noqa: BLE001 - classified below; anything else is re-raised untouched
                if attempt >= len(pauses) or not _is_transport_error(exc):
                    raise
                if build_id:
                    self._increment_metric(build_id, "transport_retries")
                deadline = time.monotonic() + pauses[attempt]
                while time.monotonic() < deadline:
                    if build_id and self._cancelled(build_id):
                        raise InterruptedError("Corpus build cancelled") from exc
                    time.sleep(0.25)
        raise RuntimeError("unreachable")  # pragma: no cover


    def _note_llm_call_start(self, build_id: str, task: str, provider: str, model: str, base_url: str) -> int:
        token = time.monotonic_ns()
        if build_id:
            with self._lock:
                self._llm_call_sequence += 1
                sequence = self._llm_call_sequence
                token = sequence
                self._llm_inflight.setdefault(build_id, {})[token] = {
                    "since": time.monotonic(),
                    "started_token": sequence,
                    "task": task,
                    "provider": provider,
                    "model": model,
                    "base_url": base_url,
                }
        return token


    def _note_llm_call_end(self, build_id: str, token: int) -> None:
        if build_id:
            with self._lock:
                calls = self._llm_inflight.get(build_id)
                if calls is not None:
                    calls.pop(token, None)
                    if not calls:
                        self._llm_inflight.pop(build_id, None)


    def _ollama_loaded_models(self, base_url: str) -> set[str] | None:
        """Names Ollama has in memory right now (its /api/ps), cached for a few seconds. None if it cannot be asked."""
        now = time.monotonic()
        cached_at, cached_url, cached = self._loaded_models_cache
        if cached_url == base_url and now - cached_at < 3.0:
            return cached
        try:
            with urllib.request.urlopen(base_url.rstrip("/") + "/api/ps", timeout=1.5) as response:  # noqa: S310 - the operator's configured Ollama URL
                names = {str(m.get("name") or m.get("model") or "") for m in json.loads(response.read()).get("models", []) if isinstance(m, dict)}
        except Exception:  # noqa: BLE001 - the status line is a courtesy; never let it break a build read
            return None
        self._loaded_models_cache = (now, base_url, names)
        return names


    def llm_activity(self, build_id: str) -> dict[str, Any] | None:
        """What the build is waiting on, for the status line: the oldest model call in flight and whether the model is loaded."""
        with self._lock:
            calls = list(self._llm_inflight.get(build_id, {}).values())
        if not calls:
            return None
        oldest = min(calls, key=lambda call: call["started_token"])
        state = "working"
        if oldest["provider"] == "ollama":
            loaded = self._ollama_loaded_models(str(oldest["base_url"] or settings.ollama_base_url))
            if loaded is None:
                state = "unknown"
            elif not any(oldest["model"] == name or name.startswith(oldest["model"] + ":") for name in loaded):
                state = "loading_model"
        return {
            "state": state, "task": oldest["task"], "model": oldest["model"], "provider": oldest["provider"],
            "seconds": round(time.monotonic() - oldest["since"], 1), "calls_in_flight": len(calls),
        }


    def start_autonomous(self, build_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Run hands-free mode on an existing build, in the background."""
        build = self.repo.get_build(build_id)
        if build.get("status") in {"queued", "running"}:
            raise ValueError("Wait for the active corpus operation to finish before running hands-free mode.")
        if build.get("status") == "published":
            raise ValueError("Published builds are immutable.")
        self._update(build_id, status="running", stage="autonomous", error=None, autonomous_report=None, resumable=False)

        def work() -> None:
            try:
                self.run_autonomous(build_id, request)
            except InterruptedError as exc:
                self._update(build_id, status="cancelled", stage="cancelled", finished_at=iso_now(), error=str(exc), resumable=True)
            except Exception as exc:  # noqa: BLE001 - reported on the build, like any other stage failure
                self._update(build_id, status="failed", stage="failed", finished_at=iso_now(), error=str(exc), resumable=True)

        self._executor.submit(work)
        return self.repo.get_build(build_id)


    def run_autonomous(self, build_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Hands-free finish: more enrichment passes, then settle what is waiting by policy, accept, optionally publish.

        Blocks until done, so it runs on a worker thread. Every decision is the policy's and is recorded as such (see
        autonomous.py); what it could not settle is left for a person and listed in the report on the build.
        """
        policy = AutonomousPolicy.from_request({"autonomous": {**(request.get("autonomous") or {}), "enabled": True}})
        notes: list[str] = []
        passes_run = 0
        if policy.passes and request.get("model"):
            try:
                self.rerun_metadata_enrichment(build_id, {**request, "passes": policy.passes})
                passes_run = policy.passes
                while True:  # the passes run on another worker; wait for them, honouring cancellation
                    if self._cancelled(build_id):
                        raise InterruptedError("Corpus build cancelled")
                    current = self.repo.get_build(build_id)
                    if not (current.get("status") in {"queued", "running"} and current.get("stage") == "metadata_enrichment_rerun"):
                        break
                    time.sleep(2.0)
            except ValueError as exc:
                notes.append(f"Extra enrichment passes were skipped: {exc}")
        report = self._autonomous_settle(build_id, policy)
        report.update({"passes_run": passes_run, "notes": notes, "policy": policy.public(), "ran_at": iso_now()})
        if policy.publish:
            try:
                if report["left_for_review"] == 0:
                    self.publish(build_id)
                    report["published"] = True
                else:
                    report["published"] = False
                    notes.append("Not published: some records still need a person.")
            except ValueError as exc:
                report["published"] = False
                notes.append(f"Not published: {exc}")
        self._update(build_id, autonomous_report=report)
        return report


    @_serialize_record_mutation
    def _autonomous_settle(self, build_id: str, policy: AutonomousPolicy) -> dict[str, Any]:
        records = self.repo.load_records(build_id)
        profile = self._profile_for(build_id)
        filled_total = accepted = 0
        exceptions: list[dict[str, Any]] = []
        for record in records:
            if str(record.get("review_disposition") or "") in {"accepted", "rejected"} or _human_touched(record):
                continue  # a person already decided this record
            outcome = settle_record(record, policy)
            filled_total += len(outcome["filled"])
            _sync_record_metadata_state(record, profile)
            ok, reasons = may_accept(record)
            if policy.accept_records and ok:
                record["review_disposition"] = "accepted"
                record["accepted"] = True
                record["rejected"] = False
                record["needs_review"] = False
                record["review_reason"] = ""
                record["accepted_by"] = "autonomous"
                record["autonomous_decision"] = {"at": iso_now(), "filled": [f["field"] for f in outcome["filled"]]}
                record["record_revision"] = int(record.get("record_revision") or 1) + 1
                accepted += 1
            else:
                exceptions.append({"record_id": record.get("record_id"), "reasons": (reasons or [item["reason"] for item in outcome["left"]] or ["left for review by policy"])[:6]})
        self._rewrite_and_validate(build_id, records)
        return {"records": len(records), "fields_filled": filled_total, "accepted": accepted, "left_for_review": len(exceptions), "exceptions": exceptions[:200]}


    def enrichment_ledger_csv(self) -> str:
        return self._ledger.to_csv()
