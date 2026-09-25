# Copyright 2026 Aaron John Schlosser, PhD.
"""Human review actions: disposition, undo/redo, patch text/metadata/evidence, boundary edits.

Human review is an authority event: a reviewer's decision on a record's disposition,
text, metadata, or evidence must be atomic, reversible, and auditable. These methods
were moved verbatim out of PdfCorpusBuildManager as a mixin, not as free functions --
unlike this effort's other extractions, they call many different self.* members
across the manager (self.repo, self._chat_json, self._profile_for, self._rewrite_and_validate,
self._ledger, ...), so turning them into free functions would need a dozen-plus
injected dependencies each, a much larger and riskier change than a verbatim class-body
move. A mixin keeps every self.* call resolving exactly as it always did through
Python's normal method resolution order; PdfCorpusBuildManager inherits from
ReviewActionsMixin, so no call site anywhere (application code, tests, monkeypatch)
needs to change.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import uuid
from functools import wraps
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ValidationError

from .corpus_enrichment_helpers import _mark_human_touch, _prepend_metadata_priority
from .corpus_metadata import MANIFEST_INHERITED_FIELDS, apply_metadata_constraints
from .corpus_record_quality import iso_now
from .corpus_review_mutations import requeue_record_metadata
from .corpus_review_state import (
    _decorate_review_state,
    _matches_review_queue,
    _queue_counts,
    _settle_enrichment_review_reason,
    _sync_record_metadata_state,
)
from .corpus_reviewer_helpers import _present_for_reviewer, _second_opinion_owed
from .corpus_segmentation import (
    _apply_boundary_adjudication_to_records,
    _scholarly_page_range,
)
from .enrichment_ledger import ACCEPTED
from .field_assertions import (
    confirm_absence,
    confirm_assertion,
    confirm_model_assertions,
    create_human_assertion,
    current_assertion_by_name,
    migrate_record_assertions,
    project_record_assertions,
    replace_assertion_evidence,
)
from .metadata_adjudication_cache import remember as remember_adjudication
from .metadata_schema import MetadataSchema
from .provenance_memory import persist_record_decision
from .rag import _citation_strings
from .system_store import system_store


def _unreviewed_model_fields(
    record: dict[str, Any],
    schema: MetadataSchema,
    fields: list[str] | tuple[str, ...] | set[str],
) -> list[str]:
    """Return schema fields whose current canonical assertion is an unreviewed model proposal."""
    migrate_record_assertions(record, schema)
    result: list[str] = []
    for field in fields:
        assertion = current_assertion_by_name(record, str(field))
        if (
            assertion is not None
            and assertion.derivation_method == "model"
            and assertion.authority_status == "unreviewed"
            and assertion.value_status == "present"
        ):
            result.append(str(field))
    return result


def _serialize_record_mutation(method):
    """Serialize manager-level read/modify/write record transactions.

    Progressive enrichment and human review intentionally overlap. Any command
    that reads the whole JSONL, mutates it, then rewrites it must hold the same
    manager lock as metadata checkpoint persistence or a stale reviewer snapshot
    can overwrite a newer metadata checkpoint.
    """
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return wrapped


class ReviewActionsMixin:
    """Mixin members declared here exist on PdfCorpusBuildManager, not on this mixin itself.

    mypy checks a mixin's body in isolation, so it cannot see that PdfCorpusBuildManager
    (which inherits this mixin, alongside its own __init__ and every other method) provides
    these at runtime. The stubs below give mypy the same signatures without re-importing
    PdfCorpusBuildManager itself, which would be circular. `repo`/`_lock`/`_ledger` are typed
    Any rather than their real classes (PdfCorpusRepository, threading.RLock, EnrichmentLedger)
    for the same reason: PdfCorpusRepository is defined in corpus_builder.py.

    Everything below is wrapped in `if TYPE_CHECKING:` deliberately -- an unguarded
    `def name(self): ...` is a real, empty method at runtime, and since Python's MRO
    resolves left-to-right across PdfCorpusBuildManager's base classes, a stub here for a
    name whose real implementation lives in a DIFFERENT mixin would silently shadow it
    if that mixin happens to be listed after this one. `TYPE_CHECKING` is always False at
    runtime, so these lines never execute and never become real attributes; mypy still
    sees them (it evaluates TYPE_CHECKING as True). See corpus_build_lifecycle.py's
    identical block for the concrete bug this once caused.
    """

    if TYPE_CHECKING:
        repo: Any
        _lock: Any
        _ledger: Any

        def _rewrite_and_validate(self, build_id: str, records: list[dict[str, Any]], *, persist_records: bool = True) -> dict[str, Any]: ...
        def _rewrite_targeted_record(self, build_id: str, record: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]: ...
        def _profile_for(self, build_id: str) -> dict[str, Any]: ...
        def _profile_of_build(self, build: dict[str, Any]) -> dict[str, Any]: ...
        def _schema_for(self, build_id: str) -> MetadataSchema: ...
        def _editable_fields(self, build_id: str) -> set[str]: ...
        def _edit_model(self, build_id: str) -> type[BaseModel]: ...
        def _refresh_workflow_fields(self, build: dict[str, Any]) -> dict[str, Any]: ...
        def _interactive_llm_request(self, build_id: str, override: dict[str, Any] | None = None) -> dict[str, Any]: ...
        def _record_human_llm_feedback(self, build_id: str, field: str, prior_value: Any, new_value: Any, prior_status: dict[str, Any] | None, record: dict[str, Any] | None = None) -> None: ...
        def _request_second_opinion(self, build_id: str, record: dict[str, Any], field: str, value: Any) -> None: ...
        def _log_second_opinion(self, build_id: str, record: dict[str, Any], field: str, value: Any, item: dict[str, Any]) -> bool: ...
        def _schedule_recheck(self, build_id: str, record: dict[str, Any], field: str, value: Any) -> None: ...
        def _score_recheck(self, build_id: str, record: dict[str, Any], field: str, value: Any, prior_status: dict[str, Any]) -> bool: ...
        def _reopen_due_rechecks(self, build_id: str, records: list[dict[str, Any]], just_decided: dict[str, Any], profile: dict[str, Any]) -> None: ...
        def _schedule_metadata_exemplar_projection(self, build_id: str) -> None: ...
        def _record_boundary_editorial_example(
            self,
            build_id: str,
            *,
            left: dict[str, Any],
            right: dict[str, Any],
            action: str,
            transaction_id: str,
        ) -> None: ...
        def _adjudicate_record_boundary_pair(
            self,
            left: dict[str, Any],
            right: dict[str, Any],
            manifest: dict[str, Any],
            request: dict[str, Any],
            build_id: str,
        ) -> dict[str, Any]: ...

    def _assert_human_review_available(self, build_id: str, record: dict[str, Any] | None = None, *, structural: bool = False) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        if str(build.get("status") or "") in {"queued", "running"}:
            stage = str(build.get("stage") or "")
            # Once segmentation has persisted the authoritative record topology,
            # non-structural review operations are available immediately. Bulk
            # review actions do not target one record object, so record=None must
            # not accidentally turn them into structural operations.
            if stage in {"enriching", "metadata_retry", "metadata_enrichment_rerun", "review"}:
                return build
            raise ValueError("Records are not editable until segmentation is complete.")
        return build


    def _assert_record_revision(self, record: dict[str, Any], expected_revision: int | None) -> int:
        current_revision = int(record.get("record_revision") or 1)
        if expected_revision is not None and current_revision != int(expected_revision):
            raise ValueError("This record changed after it was opened. Reload it before continuing.")
        return current_revision


    def _push_review_history(self, build_id: str, records: list[dict[str, Any]], *, action: str, selected_record_id: str) -> None:
        """Persist a reversible human-edit snapshot.

        Review history is intentionally separate from the append-only scholarly
        audit fields carried on each record.  The stack stores authoritative
        record-set snapshots so multi-record boundary operations can be undone
        atomically.  Any new human edit clears redo history.
        """
        checkpoint = self.repo.load_checkpoint(build_id, "review_history", {})
        undo = list(checkpoint.get("undo") or []) if isinstance(checkpoint, dict) else []
        undo.append({
            "action": action, "selected_record_id": selected_record_id,
            "created_at": iso_now(), "records": json.loads(json.dumps(records)),
        })
        self.repo.save_checkpoint(build_id, "review_history", {"undo": undo[-40:], "redo": []})


    def _save_review_undo(self, build_id: str, records: list[dict[str, Any]], *, action: str, selected_record_id: str) -> None:
        self._push_review_history(build_id, records, action=action, selected_record_id=selected_record_id)

    def _push_record_review_history(
        self,
        build_id: str,
        *,
        action: str,
        record_id: str,
        previous_record: dict[str, Any],
    ) -> None:
        checkpoint = self.repo.load_checkpoint(build_id, "review_history", {})
        undo = list(checkpoint.get("undo") or []) if isinstance(checkpoint, dict) else []
        undo.append({
            "action": action,
            "selected_record_id": record_id,
            "record_id": record_id,
            "previous_record": json.loads(json.dumps(previous_record)),
            "created_at": iso_now(),
        })
        self.repo.save_checkpoint(build_id, "review_history", {"undo": undo[-40:], "redo": []})


    def _persist_review_audit_bindings(
        self,
        build_id: str,
        promoted: dict[str, list[str]],
    ) -> None:
        """Persist durable audit bindings for review-confirmed metadata.

        SQLite audit bindings are durable provenance. Chroma remains a derived,
        rebuildable projection and is scheduled only after the reviewed record
        has been persisted successfully.
        """

        if not promoted:
            return
        schema = self._schema_for(build_id)
        wrote = False
        for record_id, fields in promoted.items():
            try:
                record = self.repo.get_record(build_id, record_id)
            except KeyError:
                continue
            migrate_record_assertions(record, schema)
            for field in dict.fromkeys(str(item) for item in fields if str(item)):
                assertion = current_assertion_by_name(record, field)
                decision_kind: Literal["value", "absence"] = (
                    "absence"
                    if assertion is not None and assertion.value_status == "confirmed_absent"
                    else "value"
                )
                persist_record_decision(
                    record=record,
                    schema=schema,
                    field_name=field,
                    value=record.get(field),
                    decision_kind=decision_kind,
                    scope_id=build_id,
                )
                wrote = True
        if wrote:
            self._schedule_metadata_exemplar_projection(build_id)

    def _invalidate_metadata_exemplar_projection(
        self,
        build_id: str,
        *,
        record_id: str | None = None,
        reason: str,
    ) -> None:
        """Mark the derived metadata exemplar index stale after review-state changes."""

        system_store.mark_semantic_memory_dirty(
            "metadata_exemplars",
            scope_id=build_id,
            record_id=record_id,
            reason=reason,
        )
        self._schedule_metadata_exemplar_projection(build_id)


    @_serialize_record_mutation
    def set_disposition(self, build_id: str, record_id: str, disposition: str, reason: str = "", expected_revision: int | None = None) -> dict[str, Any]:
        if disposition not in {"pending", "accepted", "rejected"}:
            raise ValueError("Unsupported review disposition.")
        target = self.repo.get_record(build_id, record_id)
        previous_record = json.loads(json.dumps(target))
        self._assert_human_review_available(build_id, target)
        current_revision = self._assert_record_revision(target, expected_revision)
        self._push_record_review_history(build_id, action="disposition", record_id=record_id, previous_record=previous_record)
        profile = self._profile_for(build_id)
        _sync_record_metadata_state(target, profile)
        if disposition == "accepted" and target.get("source_quality_issues"):
            raise ValueError("Resolve the source extraction problem before accepting this record.")
        if disposition == "accepted" and (list(target.get("metadata_review_fields") or []) or list(target.get("metadata_incomplete_fields") or [])):
            raise ValueError("Resolve the queued record metadata before accepting this record.")
        promoted_fields: list[str] = []
        if disposition == "accepted":
            schema = self._schema_for(build_id)
            migrate_record_assertions(target, schema)
            status_map = target.get("metadata_field_status") if isinstance(target.get("metadata_field_status"), dict) else {}
            for field in schema.review_fields():
                assertion = current_assertion_by_name(target, field)
                if assertion is None or assertion.derivation_method != "model" or assertion.authority_status != "unreviewed":
                    continue
                info = status_map.get(field) if isinstance(status_map.get(field), dict) else {}
                if assertion.model or info.get("model"):
                    self._ledger.append(
                        ACCEPTED,
                        model=str(assertion.model or info.get("model") or ""),
                        field=field,
                        build_id=build_id,
                        record_id=str(target.get("record_id") or ""),
                        confidence=assertion.confidence,
                        autofilled=bool(info.get("autofilled")),
                        value=target.get(field),
                        new_value=target.get(field),
                        **(info.get("conditions") or {}),
                    )
                confirm_assertion(
                    target,
                    assertion,
                    reason="Confirmed when the reviewer accepted the record.",
                )
                promoted_fields.append(field)
            project_record_assertions(target)
            target["metadata_reviewed_at"] = iso_now()
        target["review_disposition"] = disposition
        target["accepted"] = disposition == "accepted"
        target["rejected"] = disposition == "rejected"
        if disposition == "accepted":
            target["needs_review"] = False
            target["review_reason"] = ""
        elif disposition == "rejected":
            target["needs_review"] = False
            target["review_reason"] = str(reason or "Rejected during human review.")
        else:
            target["needs_review"] = True
            target["review_reason"] = str(reason or target.get("review_reason") or "Pending human review.")
        _mark_human_touch(target, ["__review__"])
        target["record_revision"] = current_revision + 1
        self._rewrite_targeted_record(build_id, target, previous_record)
        if promoted_fields:
            self._persist_review_audit_bindings(
                build_id,
                {record_id: promoted_fields},
            )
        return target


    @_serialize_record_mutation
    def review_decision(self, build_id: str, record_id: str, disposition: str, reason: str = "", expected_revision: int | None = None, review_queue: str | None = None) -> dict[str, Any]:
        """Apply one review decision and return the authoritative next step atomically.

        This is the UI-facing review command. It avoids the previous client-side
        accept -> refresh build -> refresh queue race that could look like a no-op.
        """
        if disposition not in {"accepted", "rejected"}:
            raise ValueError("Unsupported review decision.")
        records = self.repo.load_records(build_id)
        index = next((i for i, row in enumerate(records) if row.get("record_id") == record_id), -1)
        if index < 0:
            raise KeyError(record_id)
        target = records[index]
        self._assert_human_review_available(build_id, target)
        profile = self._profile_for(build_id)
        _sync_record_metadata_state(target, profile)
        blocking_fields = list(dict.fromkeys([str(v) for v in (target.get("metadata_review_fields") or []) + (target.get("metadata_incomplete_fields") or [])]))
        if disposition == "accepted" and target.get("source_quality_issues"):
            return {
                "applied": False, "blocked": True, "blocker": "source_problem",
                "blocking_fields": [], "record": target, "next_record": None,
                "build": self._refresh_workflow_fields(self.repo.get_build(build_id)),
                "queue_counts": _queue_counts(records),
            }
        if disposition == "accepted" and blocking_fields:
            return {
                "applied": False, "blocked": True, "blocker": "metadata_decision_required",
                "blocking_fields": blocking_fields, "record": target, "next_record": None,
                "build": self._refresh_workflow_fields(self.repo.get_build(build_id)),
                "queue_counts": _queue_counts(records),
            }
        self._assert_record_revision(target, expected_revision)
        current_revision = int(target.get("record_revision") or 1)
        self._push_review_history(build_id, records, action=f"review_{disposition}", selected_record_id=record_id)
        promoted_fields: list[str] = []
        if disposition == "accepted":
            schema = self._schema_for(build_id)
            migrate_record_assertions(target, schema)
            for field in schema.review_fields():
                assertion = current_assertion_by_name(target, field)
                if assertion is None or assertion.derivation_method != "model" or assertion.authority_status != "unreviewed":
                    continue
                confirm_assertion(
                    target,
                    assertion,
                    reason="Confirmed when the reviewer accepted the record.",
                )
                promoted_fields.append(field)
            project_record_assertions(target)
            target["metadata_reviewed_at"] = iso_now()
        target["review_disposition"] = disposition
        target["accepted"] = disposition == "accepted"
        target["rejected"] = disposition == "rejected"
        target["needs_review"] = False
        target["review_reason"] = "" if disposition == "accepted" else str(reason or "Rejected during human review.")
        _mark_human_touch(target, ["__review__"])
        target["record_revision"] = current_revision + 1
        build = self._rewrite_and_validate(build_id, records)
        if promoted_fields:
            self._persist_review_audit_bindings(
                build_id,
                {record_id: promoted_fields},
            )
        # Prefer the next *pending* record in the active review queue.  `all` is
        # intentionally special: `_matches_review_queue(..., "all")` includes
        # already-reviewed records, which previously let Accept & next advance to
        # an accepted/rejected row and made the primary action look like a no-op.
        ordered = records[index + 1:] + records[:index]
        def pending(candidate: dict[str, Any]) -> bool:
            return str(candidate.get("review_disposition") or "pending") == "pending"
        if review_queue and review_queue != "all":
            next_record = next((candidate for candidate in ordered if pending(candidate) and _matches_review_queue(candidate, review_queue)), None)
        else:
            next_record = next((candidate for candidate in ordered if pending(candidate)), None)
        if next_record is None:
            next_record = next((candidate for candidate in ordered if pending(candidate)), None)
        return {"applied": True, "blocked": False, "record": target, "next_record": next_record, "build": build, "queue_counts": _queue_counts(records)}


    def accept_record(self, build_id: str, record_id: str, accepted: bool = True, expected_revision: int | None = None) -> dict[str, Any]:
        return self.set_disposition(build_id, record_id, "accepted" if accepted else "pending", expected_revision=expected_revision)


    @_serialize_record_mutation
    def bulk_disposition(self, build_id: str, disposition: str, reason: str = "", needs_review: bool | None = None, query: str = "", filter_disposition: str | None = None, review_queue: str | None = None, record_ids: list[str] | None = None) -> dict[str, Any]:
        self._assert_human_review_available(build_id, structural=False)
        if disposition not in {"pending", "accepted", "rejected"}:
            raise ValueError("Unsupported review disposition.")
        records = self.repo.load_records(build_id)
        self._push_review_history(build_id, records, action=f"bulk_{disposition}", selected_record_id="")
        q = str(query or "").casefold().strip()
        selected_ids = {str(value) for value in (record_ids or []) if str(value).strip()}
        changed = 0
        blocked_metadata = 0
        blocked_record_ids: list[str] = []
        promoted_by_record: dict[str, list[str]] = {}
        for record in records:
            if selected_ids and str(record.get("record_id") or "") not in selected_ids:
                continue
            if needs_review is not None and bool(record.get("needs_review")) is not needs_review:
                continue
            current_disposition = str(record.get("review_disposition") or ("accepted" if record.get("accepted") else "rejected" if record.get("rejected") else "pending"))
            profile = self._profile_for(build_id)
            _sync_record_metadata_state(record, profile)
            if filter_disposition is not None and current_disposition != filter_disposition:
                continue
            if review_queue and not _matches_review_queue(record, review_queue):
                continue
            if q and q not in json.dumps(record, ensure_ascii=False).casefold():
                continue
            if disposition == "accepted" and (record.get("source_quality_issues") or list(record.get("metadata_review_fields") or []) or list(record.get("metadata_incomplete_fields") or [])):
                blocked_metadata += 1
                if len(blocked_record_ids) < 100:
                    blocked_record_ids.append(str(record.get("record_id") or ""))
                continue
            current_revision = int(record.get("record_revision") or 1)
            if disposition == "accepted":
                schema = self._schema_for(build_id)
                migrate_record_assertions(record, schema)
                promoted_fields: list[str] = []
                for field in schema.review_fields():
                    assertion = current_assertion_by_name(record, field)
                    if assertion is None or assertion.derivation_method != "model" or assertion.authority_status != "unreviewed":
                        continue
                    confirm_assertion(
                        record,
                        assertion,
                        reason="Confirmed when the reviewer accepted the record.",
                    )
                    promoted_fields.append(field)
                project_record_assertions(record)
                if promoted_fields:
                    promoted_by_record[str(record.get("record_id") or "")] = promoted_fields
                record["metadata_reviewed_at"] = iso_now()
            record["review_disposition"] = disposition
            record["accepted"] = disposition == "accepted"
            record["rejected"] = disposition == "rejected"
            # Bulk review is still a human decision. Freeze later automatic
            # enrichment from overwriting the reviewed record exactly as the
            # single-record review path does.
            _mark_human_touch(record, ["__review__"])
            if disposition == "accepted":
                record["needs_review"] = False; record["review_reason"] = ""
            elif disposition == "rejected":
                record["needs_review"] = False; record["review_reason"] = str(reason or "Rejected during human review.")
            else:
                record["needs_review"] = True; record["review_reason"] = str(reason or record.get("review_reason") or "Pending human review.")
            record["record_revision"] = current_revision + 1
            changed += 1
        self._rewrite_and_validate(build_id, records)
        self._persist_review_audit_bindings(build_id, promoted_by_record)
        persisted = self.repo.load_records(build_id)
        return {"changed": changed, "disposition": disposition, "blocked_metadata": blocked_metadata, "blocked_record_ids": blocked_record_ids, "queue_counts": _queue_counts(persisted)}


    @_serialize_record_mutation
    def undo_last_review_edit(self, build_id: str) -> dict[str, Any]:
        checkpoint = self.repo.load_checkpoint(build_id, "review_history", {})
        undo = list(checkpoint.get("undo") or []) if isinstance(checkpoint, dict) else []
        redo = list(checkpoint.get("redo") or []) if isinstance(checkpoint, dict) else []
        if not undo:
            raise KeyError(build_id)
        entry = undo.pop()
        if entry.get("previous_record") is not None and entry.get("record_id"):
            current = self.repo.get_record(build_id, str(entry["record_id"]))
            redo.append({
                "action": entry.get("action"),
                "selected_record_id": entry.get("selected_record_id"),
                "record_id": entry["record_id"],
                "previous_record": json.loads(json.dumps(current)),
                "created_at": iso_now(),
            })
            restored = json.loads(json.dumps(entry["previous_record"]))
            restored["record_revision"] = int(current.get("record_revision") or 1) + 1
            self._rewrite_targeted_record(build_id, restored, current)
            self.repo.save_checkpoint(build_id, "review_history", {"undo": undo, "redo": redo[-40:]})
            self._invalidate_metadata_exemplar_projection(
                build_id,
                record_id=str(entry["record_id"]),
                reason="review_history_undo",
            )
            return {"restored": True, "action": entry.get("action"), "selected_record_id": entry.get("selected_record_id"), "record_count": int(self.repo.get_build(build_id).get("record_count") or 0), "can_undo": bool(undo), "can_redo": True}
        current = self.repo.load_records(build_id)
        redo.append({
            "action": entry.get("action"), "selected_record_id": entry.get("selected_record_id"),
            "created_at": iso_now(), "records": json.loads(json.dumps(current)),
        })
        records = entry["records"]
        self._rewrite_and_validate(build_id, records)
        self.repo.save_checkpoint(build_id, "review_history", {"undo": undo, "redo": redo[-40:]})
        self._invalidate_metadata_exemplar_projection(
            build_id,
            reason="review_history_undo",
        )
        return {"restored": True, "action": entry.get("action"), "selected_record_id": entry.get("selected_record_id"), "record_count": len(records), "can_undo": bool(undo), "can_redo": True}


    @_serialize_record_mutation
    def redo_last_review_edit(self, build_id: str) -> dict[str, Any]:
        checkpoint = self.repo.load_checkpoint(build_id, "review_history", {})
        undo = list(checkpoint.get("undo") or []) if isinstance(checkpoint, dict) else []
        redo = list(checkpoint.get("redo") or []) if isinstance(checkpoint, dict) else []
        if not redo:
            raise KeyError(build_id)
        entry = redo.pop()
        if entry.get("previous_record") is not None and entry.get("record_id"):
            current = self.repo.get_record(build_id, str(entry["record_id"]))
            undo.append({
                "action": entry.get("action"),
                "selected_record_id": entry.get("selected_record_id"),
                "record_id": entry["record_id"],
                "previous_record": json.loads(json.dumps(current)),
                "created_at": iso_now(),
            })
            restored = json.loads(json.dumps(entry["previous_record"]))
            restored["record_revision"] = int(current.get("record_revision") or 1) + 1
            self._rewrite_targeted_record(build_id, restored, current)
            self.repo.save_checkpoint(build_id, "review_history", {"undo": undo[-40:], "redo": redo})
            self._invalidate_metadata_exemplar_projection(
                build_id,
                record_id=str(entry["record_id"]),
                reason="review_history_redo",
            )
            return {"restored": True, "action": entry.get("action"), "selected_record_id": entry.get("selected_record_id"), "record_count": int(self.repo.get_build(build_id).get("record_count") or 0), "can_undo": True, "can_redo": bool(redo)}
        current = self.repo.load_records(build_id)
        undo.append({
            "action": entry.get("action"), "selected_record_id": entry.get("selected_record_id"),
            "created_at": iso_now(), "records": json.loads(json.dumps(current)),
        })
        records = entry["records"]
        self._rewrite_and_validate(build_id, records)
        self.repo.save_checkpoint(build_id, "review_history", {"undo": undo[-40:], "redo": redo})
        self._invalidate_metadata_exemplar_projection(
            build_id,
            reason="review_history_redo",
        )
        return {"restored": True, "action": entry.get("action"), "selected_record_id": entry.get("selected_record_id"), "record_count": len(records), "can_undo": True, "can_redo": bool(redo)}


    @_serialize_record_mutation
    def patch_record_text(
        self, build_id: str, record_id: str, text: str, expected_revision: int | None = None,
        resolve_source_issues: bool = False,
    ) -> dict[str, Any]:
        """Save reviewer-corrected corpus text without destroying extraction provenance."""
        target = self.repo.get_record(build_id, record_id)
        previous_record = json.loads(json.dumps(target))
        self._assert_human_review_available(build_id, target)
        current_revision = self._assert_record_revision(target, expected_revision)
        self._push_record_review_history(build_id, action="text_edit", record_id=record_id, previous_record=previous_record)
        cleaned = str(text or "").strip()
        if not cleaned:
            raise ValueError("Reviewed record text cannot be empty.")
        if "source_extracted_text" not in target:
            target["source_extracted_text"] = str(target.get("text") or "")
        previous = str(target.get("text") or "")
        unchanged = cleaned == previous
        if unchanged and not resolve_source_issues:
            target["text_review_status"] = "human_reviewed"
            target["text_reviewed_at"] = iso_now()
            target["text_review_source"] = "human"
            _mark_human_touch(target, ["__text_reviewed__"])
            review_events = list(target.get("review_events") or [])
            review_events.append({"at": iso_now(), "event": "text_reviewed", "changed": False})
            target["review_events"] = review_events[-100:]
            target["record_revision"] = current_revision + 1
            self._rewrite_targeted_record(build_id, target, previous_record)
            _decorate_review_state(target)
            return target
        history = list(target.get("text_revision_history") or [])
        history.append({
            "at": iso_now(), "source": "human",
            "previous_sha256": hashlib.sha256(previous.encode("utf-8")).hexdigest(),
            "text_sha256": hashlib.sha256(cleaned.encode("utf-8")).hexdigest(),
            "previous_length": len(previous), "text_length": len(cleaned),
            "diff": "\n".join(difflib.unified_diff(
                previous.splitlines(), cleaned.splitlines(),
                fromfile="previous reviewed text", tofile="reviewed text", lineterm="",
            )),
            "resolved_source_issues": bool(resolve_source_issues),
        })
        target["text_revision_history"] = history[-20:]
        target["text"] = cleaned
        target["text_length"] = len(cleaned)
        target["text_review_status"] = "human_corrected"
        target["text_reviewed_at"] = iso_now()
        target["text_review_source"] = "human"
        _mark_human_touch(target, ["__text__"])
        # Any text correction invalidates a prior record-level acceptance. The
        # reviewer may accept again after deciding whether selective metadata
        # reruns are warranted; automatic metadata is never silently treated as
        # newly human-approved merely because the text editor saved.
        target["review_disposition"] = "pending"
        target["accepted"] = False
        target["rejected"] = False
        target["needs_review"] = True
        target["review_reason"] = "Reviewed record text changed; verify the correction and rerun any affected metadata families before acceptance."
        review_events = list(target.get("review_events") or [])
        review_events.append({"at": iso_now(), "event": "text_corrected", "resolve_source_issues": bool(resolve_source_issues)})
        target["review_events"] = review_events[-100:]
        if resolve_source_issues:
            target["resolved_source_quality_issues"] = list(target.get("source_quality_issues") or [])
            target["source_quality_issues"] = []
            target["source_quality_resolved_at"] = iso_now()
        target["metadata_needs_attention"] = True
        reasons = list(target.get("metadata_attention_reasons") or [])
        reasons.append("Reviewed text changed; rerun only the metadata families that need reconsideration.")
        target["metadata_attention_reasons"] = list(dict.fromkeys(reasons))[-50:]
        target["record_revision"] = current_revision + 1
        self._rewrite_targeted_record(build_id, target, previous_record)
        _decorate_review_state(target)
        return target


    @_serialize_record_mutation
    def patch_metadata(self, build_id: str, record_id: str, changes: dict[str, Any], expected_revision: int | None = None) -> dict[str, Any]:
        forbidden = sorted(set(changes) - self._editable_fields(build_id))
        if forbidden:
            raise ValueError(
                "Source-bound fields cannot be edited as record metadata. These system/source-bound fields are protected: "
                + ", ".join(forbidden)
            )
        # Validate the editable interpretive schema before modifying the persisted record.
        edit = self._edit_model(build_id)
        schema_input = {key: value for key, value in changes.items() if key in edit.model_fields}
        try:
            edit.model_validate(schema_input)
        except ValidationError as exc:
            raise ValueError(f"Invalid interpretive metadata: {exc}") from exc

        target = self.repo.get_record(build_id, record_id)
        previous_record = json.loads(json.dumps(target))
        self._assert_human_review_available(build_id, target)
        current_revision = int(target.get("record_revision") or 1)
        if expected_revision is not None and current_revision != int(expected_revision):
            raise ValueError("This record changed after it was opened. Reload it before saving metadata.")
        self._push_record_review_history(build_id, action="metadata_edit", record_id=record_id, previous_record=previous_record)
        decision_log = list(target.get("metadata_decisions") or [])
        skipped: set[str] = set()
        for key, value in changes.items():
            status = target.setdefault("metadata_field_status", {})
            prior_status = dict(status.get(key) or {}) if isinstance(status.get(key), dict) else {}
            prior_value = target.get(key)
            owed = _second_opinion_owed(target, key)
            if owed:
                # This is the independent second opinion, not an edit: it is compared with the first answer and the record is left alone.
                self._log_second_opinion(build_id, target, key, value, owed)
                skipped.add(key)
                continue
            answered_again = self._score_recheck(build_id, target, key, value, prior_status)
            if not answered_again:
                self._record_human_llm_feedback(build_id, key, prior_value, value, prior_status, target)
                self._schedule_recheck(build_id, target, key, value)
                self._request_second_opinion(build_id, target, key, value)
            if prior_value != value and isinstance(target.get("metadata_evidence"), dict):
                evidence_map = dict(target.get("metadata_evidence") or {})
                evidence_map.pop(key, None)
                target["metadata_evidence"] = evidence_map
            target[key] = value
            if key in self._editable_fields(build_id):
                schema = self._schema_for(build_id)
                migrate_record_assertions(target, schema)
                prior_assertion = current_assertion_by_name(target, key)
                is_manifest_override = key in MANIFEST_INHERITED_FIELDS
                if (
                    prior_assertion is not None
                    and prior_assertion.derivation_method == "model"
                    and prior_assertion.value == value
                    and not is_manifest_override
                ):
                    confirm_assertion(
                        target,
                        prior_assertion,
                        reason="Confirmed during record review.",
                    )
                else:
                    create_human_assertion(
                        target,
                        key,
                        value,
                        schema=schema,
                        supersedes=prior_assertion,
                        override=bool(is_manifest_override or (prior_assertion is not None and prior_assertion.value != value)),
                        reason=(
                            "Human record-level override of inherited document metadata."
                            if is_manifest_override
                            else "Confirmed during record review."
                        ),
                        method="human_record_override" if is_manifest_override else "human",
                    )
                project_record_assertions(target)
                decision_log.append({"field": key, "value": value, "at": iso_now(), "source": "human_override" if is_manifest_override else "human"})
        constraint_changes = apply_metadata_constraints(target)
        for item in constraint_changes:
            decision_log.append({"field": item["field"], "value": item["value"], "at": iso_now(), "source": "deterministic_constraint", "reason": item["reason"]})
        target["metadata_decisions"] = decision_log[-100:]
        target["metadata_reviewed_at"] = iso_now()
        _mark_human_touch(target, [key for key in changes if key not in skipped])
        profile = self._profile_for(build_id)
        # A due blind recheck reopens an *earlier* decision, so scheduled records
        # other than the target must be considered and persisted when they change.
        scheduled_others = [
            other for other in self.repo.load_records(build_id)
            if other.get("record_id") != target.get("record_id") and isinstance(other.get("recheck_scheduled"), dict)
        ]
        before_others = {str(other.get("record_id")): json.dumps(other, sort_keys=True, default=str) for other in scheduled_others}
        self._reopen_due_rechecks(build_id, [target, *scheduled_others], target, profile)
        for other in scheduled_others:
            if json.dumps(other, sort_keys=True, default=str) != before_others[str(other.get("record_id"))]:
                other["record_revision"] = int(other.get("record_revision") or 1) + 1
                self.repo.update_record(build_id, other)
        _sync_record_metadata_state(target, profile)
        _settle_enrichment_review_reason(target)
        target["record_revision"] = current_revision + 1
        self._rewrite_targeted_record(build_id, target, previous_record)
        # Return the record as persisted after authoritative state derivation.
        persisted = target
        schema = self._schema_for(build_id)
        for key, value in changes.items():
            if key not in skipped:
                persist_record_decision(
                    record=persisted,
                    schema=schema,
                    field_name=key,
                    value=value,
                    scope_id=build_id,
                )
        if any(key not in skipped for key in changes):
            self._schedule_metadata_exemplar_projection(build_id)
        _decorate_review_state(persisted)
        _present_for_reviewer(persisted)
        return persisted


    @_serialize_record_mutation
    def bulk_patch_metadata(
        self, build_id: str, changes: dict[str, Any], *, record_ids: list[str] | None = None,
        apply_to_all: bool = False, review_queue: str | None = None, query: str = "",
    ) -> dict[str, Any]:
        if not changes:
            raise ValueError("Choose at least one metadata field to update.")
        forbidden = sorted(set(changes) - self._editable_fields(build_id))
        if forbidden:
            raise ValueError("Unsupported bulk metadata field(s): " + ", ".join(forbidden))
        edit = self._edit_model(build_id)
        schema_input = {key: value for key, value in changes.items() if key in edit.model_fields}
        try:
            edit.model_validate(schema_input)
        except ValidationError as exc:
            raise ValueError(f"Invalid bulk metadata: {exc}") from exc
        build = self.repo.get_build(build_id)
        records = self.repo.load_records(build_id)
        self._push_review_history(build_id, records, action="bulk_metadata_edit", selected_record_id=(str(record_ids[0]) if record_ids else ""))
        wanted = {str(value) for value in (record_ids or []) if str(value)}
        query_l = str(query or "").strip().casefold()
        changed_ids: list[str] = []
        profile = self._profile_of_build(build)
        for record in records:
            if wanted:
                selected = str(record.get("record_id") or "") in wanted
            elif apply_to_all:
                selected = True
            else:
                selected = _matches_review_queue(record, review_queue) if review_queue else False
            if not selected:
                continue
            if query_l and query_l not in (str(record.get("record_id") or "") + " " + str(record.get("text") or "")).casefold():
                continue
            self._assert_human_review_available(build_id, record)
            decisions = list(record.get("metadata_decisions") or [])
            statuses = record.setdefault("metadata_field_status", {})
            for key, value in changes.items():
                prior_status = dict(statuses.get(key) or {}) if isinstance(statuses.get(key), dict) else {}
                prior_value = record.get(key)
                self._record_human_llm_feedback(build_id, key, prior_value, value, prior_status, record)
                if prior_value != value and isinstance(record.get("metadata_evidence"), dict):
                    evidence_map = dict(record.get("metadata_evidence") or {})
                    evidence_map.pop(key, None)
                    record["metadata_evidence"] = evidence_map
                record[key] = value
                schema = self._schema_for(build_id)
                migrate_record_assertions(record, schema)
                prior_assertion = current_assertion_by_name(record, key)
                override = key in MANIFEST_INHERITED_FIELDS or (
                    prior_assertion is not None and prior_assertion.value != value
                )
                if (
                    prior_assertion is not None
                    and prior_assertion.derivation_method == "model"
                    and prior_assertion.value == value
                    and key not in MANIFEST_INHERITED_FIELDS
                ):
                    confirm_assertion(
                        record,
                        prior_assertion,
                        reason="Confirmed through bulk record metadata editing.",
                    )
                else:
                    create_human_assertion(
                        record,
                        key,
                        value,
                        schema=schema,
                        supersedes=prior_assertion,
                        override=override,
                        reason="Applied through bulk record metadata editing.",
                        method="human_bulk_override" if override else "human_bulk",
                    )
                project_record_assertions(record)
                decisions.append({"field": key, "value": value, "at": iso_now(), "source": "human_bulk"})
            constraint_changes = apply_metadata_constraints(record)
            for item in constraint_changes:
                decisions.append({"field": item["field"], "value": item["value"], "at": iso_now(), "source": "deterministic_constraint", "reason": item["reason"]})
            record["metadata_decisions"] = decisions[-100:]
            record["metadata_reviewed_at"] = iso_now()
            _mark_human_touch(record, list(changes))
            record["record_revision"] = int(record.get("record_revision") or 1) + 1
            _sync_record_metadata_state(record, profile)
            inline, full = _citation_strings(record)
            record["inline_citation"] = inline; record["full_citation"] = full
            changed_ids.append(str(record.get("record_id") or ""))
        if not changed_ids:
            raise ValueError("No records matched the bulk metadata selection.")
        self._rewrite_and_validate(build_id, records)
        persisted = self.repo.load_records(build_id)
        schema = self._schema_for(build_id)
        by_id = {str(row.get("record_id") or ""): row for row in persisted}
        for record_id in changed_ids:
            record = by_id.get(record_id)
            if record:
                for key, value in changes.items():
                    persist_record_decision(
                        record=record,
                        schema=schema,
                        field_name=key,
                        value=value,
                        scope_id=build_id,
                    )
        self._schedule_metadata_exemplar_projection(build_id)
        return {"changed": len(changed_ids), "record_ids": changed_ids, "queue_counts": _queue_counts(persisted)}


    @_serialize_record_mutation
    def record_view(self, build_id: str, record_id: str) -> dict[str, Any]:
        records = self.repo.load_records(build_id)
        target = next((row for row in records if str(row.get("record_id") or "") == record_id), None)
        if target is None:
            raise KeyError(record_id)
        activity = dict(target.get("activity") or {})
        activity["human_view_count"] = int(activity.get("human_view_count") or 0) + 1
        activity["last_human_viewed_at"] = iso_now()
        target["activity"] = activity
        target["human_view_count"] = activity["human_view_count"]
        self._rewrite_and_validate(build_id, records)
        return {"record_id": record_id, "activity": activity}


    @_serialize_record_mutation
    def metadata_decision(self, build_id: str, record_id: str, field: str, value: Any, expected_revision: int | None = None, confirm_no_supported_value: bool = False) -> dict[str, Any]:
        """Persist one human metadata decision and return authoritative review state.

        This endpoint is deliberately transactional from the UI's perspective:
        one call saves the value, marks the field human-confirmed, recomputes all
        derived metadata/queue state, and returns the updated record and build.
        """
        if field not in self._editable_fields(build_id) or field in {"needs_review", "review_reason"}:
            raise ValueError(f"Unsupported review metadata field: {field}")
        if confirm_no_supported_value:
            target = self.repo.get_record(build_id, record_id)
            previous_record = json.loads(json.dumps(target))
            self._assert_human_review_available(build_id, target)
            current_revision = self._assert_record_revision(target, expected_revision)
            self._push_record_review_history(build_id, action="metadata_confirm_absent", record_id=record_id, previous_record=previous_record)
            prior_status = dict((target.get("metadata_field_status") or {}).get(field) or {})
            self._record_human_llm_feedback(build_id, field, target.get(field), None, prior_status, target)
            schema = self._schema_for(build_id)
            migrate_record_assertions(target, schema)
            prior_assertion = current_assertion_by_name(target, field)
            confirm_absence(
                target,
                field,
                schema=schema,
                prior=prior_assertion,
                reason="Reviewer confirmed that no supported value applies to this record.",
            )
            project_record_assertions(target)
            target.setdefault("metadata_decisions", []).append({"field":field,"value":None,"at":iso_now(),"source":"confirmed_absent"})
            target["metadata_decisions"] = target["metadata_decisions"][-100:]
            target["metadata_reviewed_at"] = iso_now(); _mark_human_touch(target,[field])
            profile = self._profile_for(build_id)
            _sync_record_metadata_state(target, profile); target["record_revision"] = current_revision + 1
            self._rewrite_targeted_record(build_id, target, previous_record)
            record = target
            persist_record_decision(
                record=record,
                schema=self._schema_for(build_id),
                field_name=field,
                value=None,
                decision_kind="absence",
                scope_id=build_id,
            )
            self._schedule_metadata_exemplar_projection(build_id)
        else:
            record = self.patch_metadata(build_id, record_id, {field: value}, expected_revision)
        current_record = self.repo.get_record(build_id, record_id)
        previous_record = json.loads(json.dumps(current_record))
        disputes = current_record.get("metadata_disputes") if isinstance(current_record.get("metadata_disputes"), list) else []
        for dispute in disputes:
            if isinstance(dispute, dict) and dispute.get("field") == field and not dispute.get("resolved_at"):
                dispute["resolved_at"] = iso_now()
                dispute["resolved_value"] = value
                dispute["resolution_source"] = "human"
        current_record["metadata_disputes"] = disputes[-100:]
        _sync_record_metadata_state(current_record, self._profile_for(build_id))
        _settle_enrichment_review_reason(current_record)
        _decorate_review_state(current_record)
        if current_record != previous_record:
            self._rewrite_targeted_record(build_id, current_record, previous_record)
        record = current_record
        build = self.repo.get_build(build_id)
        self._refresh_workflow_fields(build)
        self.repo.save_build(build)
        remaining_fields = list(dict.fromkeys([
            str(v) for v in (record.get("metadata_incomplete_fields") or []) + (record.get("metadata_review_fields") or [])
        ]))
        remember_adjudication(
            record_id=record_id,
            text=str(record.get("text") or ""),
            field=field,
            value=value,
            schema_version=str(build.get("schema_version") or ""),
            decision="absence" if confirm_no_supported_value else "value",
            field_id=self._schema_for(build_id).field_id(field),
        )
        return {
            "applied": True,
            "record": record,
            "build": build,
            "queue_counts": _queue_counts(self.repo.load_records(build_id)),
            "remaining_fields": remaining_fields,
            "ready_for_acceptance": bool(record.get("can_accept")),
            "review_state": str(record.get("review_state") or "ready"),
        }


    @_serialize_record_mutation
    def patch_evidence(
        self,
        build_id: str,
        record_id: str,
        field: str,
        block_ids: list[str],
        confidence: float = 1.0,
        reason: str = "",
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        if field not in self._schema_for(build_id).attribution_fields() and field not in self._edit_model(build_id).model_fields:
            raise ValueError(f"Unsupported metadata evidence field: {field}")
        target = self.repo.get_record(build_id, record_id)
        previous_record = json.loads(json.dumps(target))
        self._assert_human_review_available(build_id, target)
        current_revision = int(target.get("record_revision") or 1)
        if expected_revision is not None and current_revision != int(expected_revision):
            raise ValueError("This record changed after it was opened. Reload it before editing evidence.")
        self._push_record_review_history(build_id, action="evidence_edit", record_id=record_id, previous_record=previous_record)
        allowed_ids = set(map(str, target.get("source_block_ids") or []))
        unique_ids = list(dict.fromkeys(map(str, block_ids)))
        invalid = [block_id for block_id in unique_ids if block_id not in allowed_ids]
        if invalid:
            raise ValueError("Evidence blocks must belong to the selected record: " + ", ".join(invalid[:10]))
        evidence = dict(target.get("metadata_evidence") or {})
        if unique_ids:
            evidence[field] = {
                "block_ids": unique_ids,
                "confidence": max(0.0, min(1.0, float(confidence))),
                "reason": str(reason or "Human-reviewed evidence binding."),
                "reviewed_by": "human",
                "reviewed_at": iso_now(),
            }
        else:
            evidence.pop(field, None)
        target["metadata_evidence"] = evidence
        schema = self._schema_for(build_id)
        migrate_record_assertions(target, schema)
        assertion = current_assertion_by_name(target, field)
        if assertion is not None:
            assertion_evidence = (
                [{
                    "block_ids": unique_ids,
                    "confidence": max(0.0, min(1.0, float(confidence))),
                    "reason": str(reason or "Human-reviewed evidence binding."),
                    "reviewed_by": "human",
                    "reviewed_at": iso_now(),
                }]
                if unique_ids
                else []
            )
            replace_assertion_evidence(
                target,
                assertion,
                assertion_evidence,
                reason=str(reason or "Human-reviewed evidence binding changed."),
            )
            project_record_assertions(target)
        target["metadata_needs_attention"] = True
        target["metadata_attention_reasons"] = ["Source evidence binding changed and metadata validation must be rerun."]
        target["record_revision"] = current_revision + 1
        self._rewrite_targeted_record(build_id, target, previous_record)
        current = current_assertion_by_name(target, field)
        if (
            unique_ids
            and current is not None
            and current.authority_status in {"human_confirmed", "human_override"}
        ):
            self._persist_review_audit_bindings(
                build_id,
                {record_id: [field]},
            )
        else:
            # Evidence is part of the derived exemplar. Removing or changing
            # evidence must invalidate any older vector projection.
            self._invalidate_metadata_exemplar_projection(
                build_id,
                record_id=record_id,
                reason="reviewed_metadata_evidence_changed",
            )
        return target


    @_serialize_record_mutation
    def slice_to_neighbor(
        self, build_id: str, record_id: str, direction: str, offset: int, expected_revision: int | None = None, keep_end: int | None = None,
    ) -> dict[str, Any]:
        """Move reviewed text across an existing record boundary without creating a record.

        ``previous`` moves text before ``offset`` to the end of the previous record.
        ``next`` moves text after ``offset`` to the start of the next record.  The
        immutable extraction is retained on both records; this operation edits the
        reviewed corpus layer and records an atomic two-record revision.
        """
        if direction not in {"previous", "next", "keep", "new"}:
            raise ValueError("Slice direction must be previous or next.")
        records = self.repo.load_records(build_id)
        index = next((i for i, row in enumerate(records) if row.get("record_id") == record_id), -1)
        if index < 0:
            raise KeyError(record_id)
        target = records[index]
        self._assert_human_review_available(build_id, target, structural=False)
        self._assert_record_revision(target, expected_revision)
        text = str(target.get("text") or "")
        create_new = direction == "new"
        if direction in {"keep", "new"}:
            if index == 0 or index == len(records) - 1:
                raise ValueError("Keeping a selected chunk requires both neighboring records.")
            if keep_end is None or offset >= keep_end or keep_end > len(text):
                raise ValueError("Keep selection must be inside the selected record text.")
            previous, following = records[index - 1], records[index + 1]
            prefix, retained, suffix = text[:offset].strip(), text[offset:keep_end].strip(), text[keep_end:].strip()
            if not prefix or not retained or not suffix:
                raise ValueError("Keep selection must leave non-empty text in all three records.")
            original_texts = {
                str(target.get("record_id")): text,
                str(previous.get("record_id")): str(previous.get("text") or ""),
                str(following.get("record_id")): str(following.get("text") or ""),
            }
            neighbors = (previous, following)
        else:
            neighbor_index = index - 1 if direction == "previous" else index + 1
            if neighbor_index < 0 or neighbor_index >= len(records):
                raise ValueError(f"No {direction} record is available for this slice.")
            neighbor = records[neighbor_index]
            neighbors = (neighbor,)
        neighbor = neighbors[0]
        if direction != "keep":
            neighbor_index = index - 1 if direction == "previous" else index + 1
            neighbor = records[neighbor_index]
        if direction != "keep":
            original_texts = {str(target.get("record_id")): text, str(neighbor.get("record_id")): str(neighbor.get("text") or "")}
        if offset <= 0 or offset >= len(text):
            raise ValueError("Slice point must be inside the selected record text.")
        self._push_review_history(build_id, records, action=f"slice_{direction}", selected_record_id=record_id)
        if direction == "keep":
            previous, following = records[index - 1], records[index + 1]
            previous["text"] = (str(previous.get("text") or "").rstrip() + "\n\n" + prefix).strip()
            target["text"] = retained
            following["text"] = (suffix + "\n\n" + str(following.get("text") or "").lstrip()).strip()
        elif direction == "previous":
            moved, retained = text[:offset].strip(), text[offset:].lstrip()
            if not moved or not retained:
                raise ValueError("Slice must leave non-empty text in both records.")
            neighbor["text"] = (str(neighbor.get("text") or "").rstrip() + "\n\n" + moved).strip()
            target["text"] = retained
        else:
            retained, moved = text[:offset].rstrip(), text[offset:].strip()
            if not moved or not retained:
                raise ValueError("Slice must leave non-empty text in both records.")
            neighbor["text"] = (moved + "\n\n" + str(neighbor.get("text") or "").lstrip()).strip()
            target["text"] = retained
        now = iso_now()
        transaction_id = f"slice-{uuid.uuid4().hex[:12]}"
        created_record: dict[str, Any] | None = None
        if create_new:
            new_record = json.loads(json.dumps(target))
            new_record["record_id"] = f"{record_id}-split-{uuid.uuid4().hex[:10]}"
            new_record["text"] = retained
            new_record["text_length"] = len(retained)
            new_record["record_revision"] = 1
            new_record["review_events"] = []
            new_record["slice_lineage"] = {
                "transaction_id": transaction_id,
                "source_record_id": record_id,
                "role": "created",
                "at": now,
            }
            target["text"] = prefix
            records.insert(index + 1, new_record)
            created_record = new_record
            affected_rows = (target, new_record, following)
        else:
            affected_rows = (target, *neighbors)
        for row in affected_rows:
            if "source_extracted_text" not in row:
                row["source_extracted_text"] = original_texts.get(str(row.get("record_id")), str(row.get("text") or ""))
            row["text_length"] = len(str(row.get("text") or ""))
            row["text_review_status"] = "human_corrected"
            row["text_reviewed_at"] = now
            row["text_review_source"] = "human_boundary_slice"
            row["review_disposition"] = "pending"
            row["accepted"] = False
            row["rejected"] = False
            row["needs_review"] = True
            row["review_reason"] = "Record boundary adjusted during human review; verify neighboring text and affected metadata."
            requeue_record_metadata(
                row,
                "Record boundary changed; metadata whose interpretation depends on moved text may need review.",
            )
            lineage = dict(row.get("slice_lineage") or {})
            lineage.update({
                "transaction_id": transaction_id,
                "source_record_id": record_id,
                "affected_record_ids": [str(item.get("record_id") or "") for item in affected_rows],
                "direction": direction,
                "role": "source" if str(row.get("record_id")) == record_id else "neighbor",
                "at": now,
            })
            row["slice_lineage"] = lineage
            row["record_revision"] = int(row.get("record_revision") or 1) + 1
            _mark_human_touch(row, ["__text__", "__boundary__"])
            events = list(row.get("review_events") or [])
            events.append({"at": now, "event": "boundary_slice", "transaction_id": transaction_id, "direction": direction, "source_record_id": record_id, "affected_record_ids": [str(item.get("record_id") or "") for item in affected_rows]})
            row["review_events"] = events[-100:]
        left_row, right_row = (neighbors[0], target) if direction in {"previous", "keep"} else (target, neighbor)
        self._record_boundary_editorial_example(
            build_id, left=left_row, right=right_row,
            action=f"human_slice_{direction}", transaction_id=transaction_id,
        )
        self._rewrite_and_validate(build_id, records)
        result = {"record": target, "neighbor": neighbor, "direction": direction, "transaction_id": transaction_id}
        if created_record is not None:
            result["new_record"] = created_record
        if direction == "keep":
            result["left_neighbor"] = neighbors[0]
            result["right_neighbor"] = records[index + 1]
        return result


    @_serialize_record_mutation
    def adjudicate_record_boundary(self, build_id: str, record_id: str, direction: str, request_override: dict[str, Any] | None = None) -> dict[str, Any]:
        if direction not in {"previous", "next"}:
            raise ValueError("Boundary direction must be previous or next.")
        records = self.repo.load_records(build_id)
        index = next((i for i, row in enumerate(records) if row.get("record_id") == record_id), -1)
        if index < 0:
            raise KeyError(record_id)
        neighbor_index = index - 1 if direction == "previous" else index + 1
        if neighbor_index < 0 or neighbor_index >= len(records):
            raise ValueError(f"No {direction} record is available for boundary adjudication.")
        left, right = (records[neighbor_index], records[index]) if direction == "previous" else (records[index], records[neighbor_index])
        build = self.repo.get_build(build_id)
        request = self._interactive_llm_request(build_id, request_override)
        if not request.get("provider") and not request.get("provider_profile_id"):
            raise ValueError("No LLM provider is available for boundary adjudication.")
        decision = self._adjudicate_record_boundary_pair(left, right, build.get("manifest") or {}, request, build_id)
        profile = self._profile_of_build(build)
        _apply_boundary_adjudication_to_records(left, right, decision, threshold=float(profile.get("min_boundary_confidence") or 0.72))
        self._rewrite_and_validate(build_id, records)
        current_build = self.repo.get_build(build_id)
        history = list(current_build.get("boundary_second_reader_history") or [])
        history.append({**decision, "requested_by": "human", "direction": direction})
        current_build["boundary_second_reader_history"] = history[-100:]
        self.repo.save_build(current_build)
        return {"decision": decision, "left_record": left, "right_record": right, "build": current_build}


    @_serialize_record_mutation
    def merge(self, build_id: str, record_id: str, direction: str, expected_revision: int | None = None) -> dict[str, Any]:
        self._assert_human_review_available(build_id, structural=True)
        records = self.repo.load_records(build_id)
        index = next((i for i, record in enumerate(records) if record.get("record_id") == record_id), -1)
        if index < 0:
            raise KeyError(record_id)
        self._assert_record_revision(records[index], expected_revision)
        self._save_review_undo(build_id, json.loads(json.dumps(records)), action="merge", selected_record_id=record_id)
        other_index = index - 1 if direction == "previous" else index + 1
        if other_index < 0 or other_index >= len(records):
            raise ValueError(f"No {direction} record is available to merge.")
        first_index, second_index = sorted((index, other_index))
        first, second = records[first_index], records[second_index]
        merged_ids = list(first.get("source_block_ids") or []) + list(second.get("source_block_ids") or [])
        blocks = {block["block_id"]: block for block in self.repo.load_blocks(self.repo.get_build(build_id)["asset_id"])}
        group = [blocks[block_id] for block_id in merged_ids if block_id in blocks]
        text = "\n\n".join(block["text"].strip() for block in group if block.get("text", "").strip())
        pages = sorted({int(block["page"]) for block in group})
        page_start, page_end = _scholarly_page_range(group)
        merged_evidence: dict[str, Any] = {}
        for evidence_map in (first.get("metadata_evidence") or {}, second.get("metadata_evidence") or {}):
            for field, info in evidence_map.items():
                existing = merged_evidence.setdefault(field, {"block_ids": [], "confidence": 1.0, "reason": "Preserved across human merge.", "reviewed_by": "human", "reviewed_at": iso_now()})
                existing["block_ids"] = list(dict.fromkeys(list(existing.get("block_ids") or []) + list(info.get("block_ids") or [])))
                existing["confidence"] = min(float(existing.get("confidence") or 1.0), float(info.get("confidence") or 1.0))
        merged = {**first, "text": text, "text_length": len(text), "page_start": page_start, "page_end": page_end, "pdf_pages": pages, "source_unit_ids": merged_ids, "source_block_ids": merged_ids, "source_spans": list(first.get("source_spans") or []) + list(second.get("source_spans") or []), "needs_review": True, "accepted": False, "rejected": False, "review_disposition": "pending", "review_reason": "Record boundaries were merged during human review.", "metadata_evidence": merged_evidence, "record_revision": max(int(first.get("record_revision") or 1), int(second.get("record_revision") or 1)) + 1}
        # Keep the first record's immutable identity. Unrelated downstream IDs never change.
        merged["record_id"] = first.get("record_id")
        requeue_record_metadata(
            merged,
            "Record boundaries were merged during human review; metadata enrichment must rerun against the merged text.",
        )
        records[first_index:second_index + 1] = [merged]
        self._rewrite_and_validate(build_id, records)
        with self._lock:
            build = self.repo.get_build(build_id)
            _prepend_metadata_priority(build, str(merged.get("record_id") or ""))
            self.repo.save_build(build)
        return merged


    @_serialize_record_mutation
    def split(self, build_id: str, record_id: str, after_block_id: str, expected_revision: int | None = None) -> dict[str, Any]:
        self._assert_human_review_available(build_id, structural=True)
        records = self.repo.load_records(build_id)
        index = next((i for i, record in enumerate(records) if record.get("record_id") == record_id), -1)
        if index < 0:
            raise KeyError(record_id)
        target = records[index]
        self._assert_record_revision(target, expected_revision)
        self._save_review_undo(build_id, json.loads(json.dumps(records)), action="split", selected_record_id=record_id)
        ids = list(target.get("source_block_ids") or [])
        if after_block_id not in ids or ids.index(after_block_id) >= len(ids) - 1:
            raise ValueError("Split point must be a non-final source block in the selected record.")
        cut = ids.index(after_block_id) + 1
        block_map = {block["block_id"]: block for block in self.repo.load_blocks(self.repo.get_build(build_id)["asset_id"])}
        pieces = []
        for piece_ids in (ids[:cut], ids[cut:]):
            group = [block_map[block_id] for block_id in piece_ids if block_id in block_map]
            text = "\n\n".join(block["text"].strip() for block in group if block.get("text", "").strip())
            pages = sorted({int(block["page"]) for block in group})
            page_start, page_end = _scholarly_page_range(group)
            piece_evidence: dict[str, Any] = {}
            for field, info in (target.get("metadata_evidence") or {}).items():
                kept = [block_id for block_id in (info.get("block_ids") or []) if block_id in piece_ids]
                if kept:
                    piece_evidence[field] = {**info, "block_ids": kept, "reason": str(info.get("reason") or "") + " Preserved across human split."}
            pieces.append({**target, "text": text, "text_length": len(text), "page_start": page_start, "page_end": page_end, "pdf_pages": pages, "source_unit_ids": piece_ids, "source_block_ids": piece_ids, "source_spans": [span for span in target.get("source_spans") or [] if span.get("block_id") in piece_ids], "needs_review": True, "accepted": False, "rejected": False, "review_disposition": "pending", "review_reason": "Record boundary was split during human review.", "metadata_evidence": piece_evidence, "record_revision": int(target.get("record_revision") or 1) + 1})
        pieces[0]["record_id"] = target.get("record_id")
        pieces[1]["record_id"] = f"{re.sub(r'-[0-9a-f]{8}$', '', str(target.get('record_id') or 'pdf'))}-s{uuid.uuid4().hex[:8]}"
        records[index:index + 1] = pieces
        self._rewrite_and_validate(build_id, records)
        return {"records": pieces}
