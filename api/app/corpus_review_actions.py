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
import uuid
from functools import wraps
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ValidationError

from .corpus_enrichment_helpers import _mark_human_touch, _prepend_metadata_priority
from .corpus_metadata import MANIFEST_INHERITED_FIELDS, apply_metadata_constraints
from .corpus_record_quality import iso_now
from .corpus_record_restructure import (
    JOIN,
    assert_text_conserved,
    block_ids_for_range,
    mint_record,
    new_record_id,
    tombstone,
)
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
    _apply_manifest_metadata,
)
from .enrichment_ledger import ACCEPTED
from .field_assertions import (
    confirm_absence,
    confirm_assertion,
    create_human_assertion,
    current_assertion_by_name,
    migrate_record_assertions,
    project_record_assertions,
    replace_assertion_evidence,
)
from .metadata_adjudication_cache import remember as remember_adjudication
from .metadata_schema import MetadataSchema
from .nlp_annotations import annotate_record
from .provenance_memory import persist_record_decision
from .rag import _citation_strings
from .system_store import system_store


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
        schema = self._schema_for(build_id)
        migrate_record_assertions(target, schema)
        for key, value in changes.items():
            status = target.setdefault("metadata_field_status", {})
            prior_status = dict(status.get(key) or {}) if isinstance(status.get(key), dict) else {}
            prior_value = target.get(key)
            prior_assertion = current_assertion_by_name(target, key)
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
            if key in self._editable_fields(build_id):
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
                    overrides_existing_value = bool(
                        prior_assertion is not None
                        and prior_assertion.value_status == "present"
                        and prior_assertion.value != value
                    )
                    create_human_assertion(
                        target,
                        key,
                        value,
                        schema=schema,
                        supersedes=prior_assertion,
                        override=bool(is_manifest_override or overrides_existing_value),
                        reason=(
                            "Human record-level override of inherited document metadata."
                            if is_manifest_override
                            else "Confirmed during record review."
                        ),
                        method="human_record_override" if is_manifest_override else "human",
                    )
                project_record_assertions(target)
                decision_log.append({"field": key, "value": value, "at": iso_now(), "source": "human_override" if is_manifest_override else "human"})
        constraint_changes = apply_metadata_constraints(target, schema)
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
            schema = self._schema_for(build_id)
            migrate_record_assertions(record, schema)
            for key, value in changes.items():
                prior_status = dict(statuses.get(key) or {}) if isinstance(statuses.get(key), dict) else {}
                prior_value = record.get(key)
                prior_assertion = current_assertion_by_name(record, key)
                self._record_human_llm_feedback(build_id, key, prior_value, value, prior_status, record)
                if prior_value != value and isinstance(record.get("metadata_evidence"), dict):
                    evidence_map = dict(record.get("metadata_evidence") or {})
                    evidence_map.pop(key, None)
                    record["metadata_evidence"] = evidence_map
                override = key in MANIFEST_INHERITED_FIELDS or bool(
                    prior_assertion is not None
                    and prior_assertion.value_status == "present"
                    and prior_assertion.value != value
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
            constraint_changes = apply_metadata_constraints(record, schema)
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
    def metadata_decision(self, build_id: str, record_id: str, field: str, value: Any, expected_revision: int | None = None, confirm_no_supported_value: bool = False, evidence_block_ids: list[str] | None = None) -> dict[str, Any]:
        """Persist one human metadata decision and return authoritative review state.

        This endpoint is deliberately transactional from the UI's perspective:
        one call saves the value, marks the field human-confirmed, recomputes all
        derived metadata/queue state, and returns the updated record and build.
        """
        if field not in self._editable_fields(build_id) or field in {"needs_review", "review_reason"}:
            raise ValueError(f"Unsupported review metadata field: {field}")
        if evidence_block_ids:
            # Validate up front so a bad evidence binding cannot leave the value half-saved.
            allowed = set(map(str, self.repo.get_record(build_id, record_id).get("source_block_ids") or []))
            invalid = [b for b in dict.fromkeys(map(str, evidence_block_ids)) if b not in allowed]
            if invalid:
                raise ValueError("Evidence blocks must belong to the selected record: " + ", ".join(invalid[:10]))
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
            if evidence_block_ids:
                # Bind the reviewer's selected evidence to the value just saved, in the same request.
                self.patch_evidence(
                    build_id, record_id, field, evidence_block_ids,
                    expected_revision=int(self.repo.get_record(build_id, record_id).get("record_revision") or 1),
                )
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


    # ------------------------------------------------------------------
    # Structural edits: split, merge, create-from-selection.
    #
    # Every operation retires the affected Records and mints new ones (see
    # corpus_record_restructure). Nothing is edited in place and no ID is reused.
    # ------------------------------------------------------------------
    def _structural_context(self, build_id: str, record_id: str, expected_revision: int | None):
        self._assert_human_review_available(build_id, structural=True)
        records = self.repo.load_records(build_id)
        index = next((i for i, row in enumerate(records) if row.get("record_id") == record_id), -1)
        if index < 0:
            raise KeyError(record_id)
        self._assert_record_revision(records[index], expected_revision)
        return records, index

    def _retired_ids(self, build_id: str) -> set[str]:
        stored = self.repo.load_checkpoint(build_id, "retired_records", {})
        entries = stored.get("entries") if isinstance(stored, dict) else []
        return {str(item.get("record_id")) for item in entries or [] if isinstance(item, dict)}

    def _restructure(
        self,
        build_id: str,
        records: list[dict[str, Any]],
        lo: int,
        hi: int,
        pieces: list[dict[str, Any]],
        *,
        operation: str,
        selected_piece: int,
    ) -> dict[str, Any]:
        """Replace ``records[lo:hi+1]`` with new Records built from ``pieces``.

        Each piece is ``{"text", "block_ids", "precise", "parents"}``.
        """
        retiring = records[lo:hi + 1]
        assert_text_conserved(
            [str(row.get("text") or "") for row in retiring],
            [str(piece["text"]) for piece in pieces],
        )
        self._save_review_undo(build_id, json.loads(json.dumps(records)), action=operation, selected_record_id=str(retiring[0].get("record_id")))
        build = self.repo.get_build(build_id)
        asset = self.repo.get_asset(build["asset_id"])
        blocks = {block["block_id"]: block for block in self.repo.load_blocks(build["asset_id"])}
        manifest = build.get("manifest") or {}
        schema = self._schema_for(build_id)
        transaction_id = f"{operation}-{uuid.uuid4().hex[:12]}"
        taken = {str(row.get("record_id")) for row in records} | self._retired_ids(build_id)
        seed = str(retiring[0].get("record_id") or "pdf")

        def finish(record: dict[str, Any]) -> None:
            _apply_manifest_metadata(record, manifest)
            inline, full = _citation_strings(record)
            record["inline_citation"] = inline
            record["full_citation"] = full
            annotate_record(record, schema, language=str(manifest.get("language") or ""))

        created: list[dict[str, Any]] = []
        for piece in pieces:
            row = mint_record(
                asset=asset, blocks=blocks, block_ids=piece["block_ids"], text=piece["text"],
                record_id=new_record_id(seed, taken), parents=piece["parents"], operation=operation,
                transaction_id=transaction_id, manifest_apply=finish, precise=piece["precise"],
            )
            requeue_record_metadata(row, "Record created by a structural edit; metadata must be evaluated against its new text.", force=True)
            _mark_human_touch(row, ["__text__", "__boundary__"])
            row["review_events"] = [{"at": iso_now(), "event": operation, "transaction_id": transaction_id, "parent_record_ids": row["lineage"]["parent_record_ids"]}]
            created.append(row)
        successor_ids = [str(row["record_id"]) for row in created]
        stored = self.repo.load_checkpoint(build_id, "retired_records", {})
        entries = list(stored.get("entries") or []) if isinstance(stored, dict) else []
        # An undone edit brings its parents back to life; they are no longer retired.
        live_ids = {str(row.get("record_id")) for row in records}
        entries = [item for item in entries if str(item.get("record_id")) not in live_ids]
        entries.extend(tombstone(row, operation=operation, transaction_id=transaction_id, successors=successor_ids) for row in retiring)
        self.repo.save_checkpoint(build_id, "retired_records", {"entries": entries})
        records[lo:hi + 1] = created
        self._rewrite_and_validate(build_id, records)
        with self._lock:
            current = self.repo.get_build(build_id)
            for row in reversed(created):
                _prepend_metadata_priority(current, str(row["record_id"]))
            self.repo.save_build(current)
        if operation != "merge":
            for left_row, right_row in zip(created, created[1:]):
                self._record_boundary_editorial_example(
                    build_id, left=left_row, right=right_row,
                    action=f"human_{operation}", transaction_id=transaction_id,
                )
        for row in retiring:
            self._invalidate_metadata_exemplar_projection(build_id, record_id=str(row.get("record_id")), reason="record_retired_by_structural_edit")
        return {
            "records": created,
            "record": created[selected_piece],
            "retired_record_ids": [str(row.get("record_id")) for row in retiring],
            "transaction_id": transaction_id,
        }

    def retired_records(self, build_id: str) -> list[dict[str, Any]]:
        """Lineage tombstones for Records retired by structural edits (never reused IDs)."""
        stored = self.repo.load_checkpoint(build_id, "retired_records", {})
        live = {str(row.get("record_id")) for row in self.repo.load_records(build_id)}
        return [item for item in (stored.get("entries") if isinstance(stored, dict) else []) or [] if str(item.get("record_id")) not in live]

    def _blocks_for(self, build_id: str) -> dict[str, dict[str, Any]]:
        asset_id = self.repo.get_build(build_id)["asset_id"]
        return {block["block_id"]: block for block in self.repo.load_blocks(asset_id)}

    @_serialize_record_mutation
    def merge(self, build_id: str, record_id: str, direction: str, expected_revision: int | None = None) -> dict[str, Any]:
        """Retire two adjacent Records and mint one new Record from both."""
        if direction not in {"previous", "next"}:
            raise ValueError("Merge direction must be previous or next.")
        records, index = self._structural_context(build_id, record_id, expected_revision)
        other = index - 1 if direction == "previous" else index + 1
        if other < 0 or other >= len(records):
            raise ValueError(f"No {direction} record is available to merge.")
        lo, hi = sorted((index, other))
        first, second = records[lo], records[hi]
        piece = {
            "text": str(first.get("text") or "").rstrip() + JOIN + str(second.get("text") or "").lstrip(),
            "block_ids": [*(first.get("source_block_ids") or []), *(second.get("source_block_ids") or [])],
            "precise": True,
            "parents": [first, second],
        }
        return self._restructure(build_id, records, lo, hi, [piece], operation="merge", selected_piece=0)

    @_serialize_record_mutation
    def split(
        self, build_id: str, record_id: str, after_block_id: str | None = None,
        expected_revision: int | None = None, offset: int | None = None,
    ) -> dict[str, Any]:
        """Retire one Record and mint two new Records from its text."""
        records, index = self._structural_context(build_id, record_id, expected_revision)
        target = records[index]
        text = str(target.get("text") or "")
        block_ids = list(target.get("source_block_ids") or [])
        blocks = self._blocks_for(build_id)
        if offset is None:
            if not after_block_id or after_block_id not in block_ids:
                raise ValueError("Split point must be a source block in the selected record or a text offset.")
            cursor = 0
            offset = -1
            for bid in block_ids:
                bt = str((blocks.get(bid) or {}).get("text") or "").strip()
                if not bt:
                    continue
                found = text.find(bt, cursor)
                if found < 0:
                    raise ValueError("The record text no longer aligns with its source blocks; split by text offset instead.")
                cursor = found + len(bt)
                if bid == after_block_id:
                    offset = cursor
                    break
        left, right = text[:offset], text[offset:]
        if offset <= 0 or offset >= len(text) or not left.strip() or not right.strip():
            raise ValueError("Split point must leave non-empty text in both new records.")
        lids, lp = block_ids_for_range(text, block_ids, blocks, 0, offset)
        rids, rp = block_ids_for_range(text, block_ids, blocks, offset, len(text))
        pieces = [
            {"text": left, "block_ids": lids, "precise": lp, "parents": [target]},
            {"text": right, "block_ids": rids, "precise": rp, "parents": [target]},
        ]
        return self._restructure(build_id, records, index, index, pieces, operation="split", selected_piece=0)

    @_serialize_record_mutation
    def create_from_selection(
        self, build_id: str, record_id: str, start: int, end: int,
        left: str = "distinct", right: str = "distinct", expected_revision: int | None = None,
    ) -> dict[str, Any]:
        """Make a new Record from ``text[start:end]``.

        The text before and after the selection either joins the prior / following
        Record (``merge_prior`` / ``merge_next``) or becomes its own new Record
        (``distinct``). Every Record touched is retired and replaced.
        """
        if left not in {"distinct", "merge_prior"} or right not in {"distinct", "merge_next"}:
            raise ValueError("left must be distinct or merge_prior; right must be distinct or merge_next.")
        records, index = self._structural_context(build_id, record_id, expected_revision)
        target = records[index]
        text = str(target.get("text") or "")
        if not 0 <= start < end <= len(text) or not text[start:end].strip():
            raise ValueError("Selection must be non-empty text inside the selected record.")
        if start == 0 and end == len(text):
            raise ValueError("The selection is the whole record; nothing would change.")
        before, chosen, after = text[:start], text[start:end], text[end:]
        block_ids = list(target.get("source_block_ids") or [])
        blocks = self._blocks_for(build_id)

        def ids(lo: int, hi: int) -> tuple[list[str], bool]:
            return block_ids_for_range(text, block_ids, blocks, lo, hi)

        lo = hi = index
        pieces: list[dict[str, Any]] = []
        if before.strip():
            bids, bp = ids(0, start)
            if left == "merge_prior":
                if index == 0:
                    raise ValueError("There is no prior record to merge the leading text into.")
                prior = records[index - 1]
                lo = index - 1
                pieces.append({
                    "text": str(prior.get("text") or "").rstrip() + JOIN + before.lstrip(),
                    "block_ids": [*(prior.get("source_block_ids") or []), *bids], "precise": bp, "parents": [prior, target],
                })
            else:
                pieces.append({"text": before, "block_ids": bids, "precise": bp, "parents": [target]})
        cids, cp = ids(start, end)
        pieces.append({"text": chosen, "block_ids": cids, "precise": cp, "parents": [target]})
        selected = len(pieces) - 1
        if after.strip():
            aids, ap = ids(end, len(text))
            if right == "merge_next":
                if index >= len(records) - 1:
                    raise ValueError("There is no following record to merge the trailing text into.")
                following = records[index + 1]
                hi = index + 1
                pieces.append({
                    "text": after.rstrip() + JOIN + str(following.get("text") or "").lstrip(),
                    "block_ids": [*aids, *(following.get("source_block_ids") or [])], "precise": ap, "parents": [target, following],
                })
            else:
                pieces.append({"text": after, "block_ids": aids, "precise": ap, "parents": [target]})
        return self._restructure(build_id, records, lo, hi, pieces, operation="create_from_selection", selected_piece=selected)

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


