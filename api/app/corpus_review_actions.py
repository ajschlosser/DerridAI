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
from .corpus_llm_helpers import _provider_roles
from .corpus_metadata import MANIFEST_INHERITED_FIELDS, apply_metadata_constraints
from .corpus_record_quality import iso_now
from .corpus_record_restructure import (
    JOIN,
    assert_active_source_unit_ownership,
    assert_text_conserved,
    block_ids_for_range,
    mint_record,
    new_record_id,
    reconcile_source_units,
    remap_evidence_bindings,
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
    FieldAssertion,
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
from .pipelines.corpus_reviewer_evidence_choice import ReviewerEvidenceChoiceSession
from .provenance_memory import persist_record_decision
from .rag import _citation_strings
from .reviewer_context import current_reviewer
from .semantic_identity import ValueEquivalenceResult, canonical_value_key
from .semantic_identity_registry import compare_field_values
from .semantic_identity_store import (
    alias_sources,
    create_alias_set,
    import_alias_sets,
    list_alias_sets,
    retire_alias_set,
    review_registry,
)
from .system_store import system_store


def _metadata_enrichment_active(
    build: dict[str, Any],
    record: dict[str, Any] | None = None,
) -> bool:
    """Whether reviewer edits can race or invalidate pending metadata work.

    The build-level operation is authoritative when it is available. Record-level
    queue/running state is also treated as active because review can occur after the
    scheduler has snapshotted a Record but before the build summary reflects that
    handoff. In either case, a reviewer edit must force the current revision back
    through enrichment instead of relying on a stale worker snapshot.
    """
    stage = str(build.get("stage") or "")
    build_active = str(build.get("status") or "") in {"queued", "running"} and (
        stage in {"enriching", "metadata_retry", "metadata_enrichment_rerun"}
        or stage.startswith("metadata_enrichment:")
    )
    if build_active or record is None:
        return build_active
    state = str(record.get("metadata_enrichment_state") or "")
    stage_status = (
        record.get("metadata_stage_status")
        if isinstance(record.get("metadata_stage_status"), dict)
        else {}
    )
    return state in {"queued", "running", "stale"} or any(
        str(value) in {"queued", "running"} for value in stage_status.values()
    )


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


def _equivalent_evidence(prior: FieldAssertion | None, equivalence: ValueEquivalenceResult) -> list[dict[str, Any]] | None:
    """Evidence an equivalent surface edit keeps, with its authority unchanged.

    Restating the same value does not invalidate the source that supports it, and it does
    not review that source either: model-selected evidence stays model-selected. A value
    that is different, or not known to be the same, starts without evidence as before.
    """
    if prior is None or equivalence.relation != "equivalent" or not prior.evidence:
        return None
    return [
        {**item, "carried_from_assertion_id": prior.assertion_id}
        for item in prior.evidence
        if isinstance(item, dict)
    ]


def _identity_key_for(schema: MetadataSchema, field: str, record: dict[str, Any], registry: Any) -> Any:
    """A value's semantic identity key under ``field``'s policy, for derived memory."""
    try:
        profile = schema.equivalence_profile_for(field)
    except KeyError:
        return None
    language = str(record.get("language") or "")
    return lambda value: canonical_value_key(value, profile=profile, language=language, registry=registry)


def _equivalence_audit(prior_value: Any, equivalence: ValueEquivalenceResult) -> dict[str, Any]:
    """Audit fields for a review decision that replaced a different surface form."""
    if equivalence.relation == "exact" or prior_value in (None, "", []):
        return {}
    return {"prior_value": prior_value, **equivalence.audit()}


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
        _progressive_metadata_index: Any

        def _rewrite_and_validate(self, build_id: str, records: list[dict[str, Any]], *, persist_records: bool = True) -> dict[str, Any]: ...
        def _rewrite_targeted_record(self, build_id: str, record: dict[str, Any], previous: dict[str, Any], *, validate_record: bool = True) -> dict[str, Any]: ...
        def _profile_for(self, build_id: str) -> dict[str, Any]: ...
        def _profile_of_build(self, build: dict[str, Any]) -> dict[str, Any]: ...
        def _schema_for(self, build_id: str) -> MetadataSchema: ...
        def _chat_json(self, request: dict[str, Any], prompt: str, *, response_model: type[BaseModel], max_tokens: int = 4096, schema_name: str = "derridai_corpus", attempts: int = 2, build_id: str = "", roles: tuple[str, ...] = ..., escalated: bool = ...) -> dict[str, Any]: ...
        def _editable_fields(self, build_id: str) -> set[str]: ...
        def _edit_model(self, build_id: str) -> type[BaseModel]: ...
        def _refresh_workflow_fields(self, build: dict[str, Any]) -> dict[str, Any]: ...
        def _interactive_llm_request(self, build_id: str, override: dict[str, Any] | None = None) -> dict[str, Any]: ...
        def _record_human_llm_feedback(self, build_id: str, field: str, prior_value: Any, new_value: Any, prior_status: dict[str, Any] | None, record: dict[str, Any] | None = None, equivalence: ValueEquivalenceResult | None = None) -> None: ...
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
            *,
            session: Any = ...,
        ) -> dict[str, Any]: ...

    def _assert_human_review_available(self, build_id: str, record: dict[str, Any] | None = None, *, structural: bool = False, text_only: bool = False) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        if str(build.get("status") or "") in {"queued", "running"}:
            stage = str(build.get("stage") or "")
            if (
                text_only and not structural
                and stage in {"constructing_records", "document_intelligence"}
                and build.get("text_review_available_at")
                and (build.get("topology_validation") or {}).get("valid") is True
            ):
                return build
            if stage in {"enriching", "metadata_retry", "metadata_enrichment_rerun", "finalizing_review", "review"}:
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
            "source_units": json.loads(json.dumps(self.repo.load_source_units(build_id))),
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
        self._rewrite_targeted_record(build_id, target, previous_record, validate_record=False)
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
        # One decision touches one Record: read it by id, record-local history/validation, and a
        # single-row write. Whole-corpus snapshots/validation here made every click scale with
        # corpus size (and kept up to 40 full-corpus undo copies).
        target = self.repo.get_record(build_id, record_id)
        self._assert_human_review_available(build_id, target)
        profile = self._profile_for(build_id)
        previous_record = json.loads(json.dumps(target))
        _sync_record_metadata_state(target, profile)
        blocking_fields = list(dict.fromkeys([str(v) for v in (target.get("metadata_review_fields") or []) + (target.get("metadata_incomplete_fields") or [])]))
        if disposition == "accepted" and (target.get("source_quality_issues") or blocking_fields):
            counts, _ = self.repo.review_queue_summary(build_id, record_id, review_queue)
            return {
                "applied": False, "blocked": True,
                "blocker": "source_problem" if target.get("source_quality_issues") else "metadata_decision_required",
                "blocking_fields": [] if target.get("source_quality_issues") else blocking_fields,
                "record": _decorate_review_state(target), "next_record": None,
                "build": self._refresh_workflow_fields(self.repo.get_build(build_id)),
                "queue_counts": counts,
            }
        current_revision = self._assert_record_revision(target, expected_revision)
        self._push_record_review_history(build_id, action=f"review_{disposition}", record_id=record_id, previous_record=previous_record)
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
        build = self._rewrite_targeted_record(build_id, target, previous_record, validate_record=False)
        if promoted_fields:
            self._persist_review_audit_bindings(
                build_id,
                {record_id: promoted_fields},
            )
        counts, next_record = self.repo.review_queue_summary(build_id, record_id, review_queue)
        return {"applied": True, "blocked": False, "record": _decorate_review_state(target), "next_record": next_record, "build": build, "queue_counts": counts}


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
            "source_units": json.loads(json.dumps(self.repo.load_source_units(build_id))),
        })
        records = entry["records"]
        if isinstance(entry.get("source_units"), list):
            self.repo.save_source_units(build_id, json.loads(json.dumps(entry["source_units"])))
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
            "source_units": json.loads(json.dumps(self.repo.load_source_units(build_id))),
        })
        records = entry["records"]
        if isinstance(entry.get("source_units"), list):
            self.repo.save_source_units(build_id, json.loads(json.dumps(entry["source_units"])))
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
        self._assert_human_review_available(build_id, target, text_only=True)
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
        # Both projections are bound to the old text hash. Remove the local copy
        # immediately; the retained document-level run remains available for audit
        # and reports itself stale until Document Intelligence is rerun.
        target.pop("nlp_candidates", None)
        target.pop("document_intelligence", None)
        target["text_review_status"] = "human_corrected"
        target["text_reviewed_at"] = iso_now()
        target["text_review_source"] = "human"
        _mark_human_touch(target, ["__text__"])
        target["human_touched_fields"] = [
            field
            for field in (target.get("human_touched_fields") or [])
            if str(field) != "__review__"
        ]
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
        build = self.repo.get_build(build_id)
        enrichment_active = _metadata_enrichment_active(build, target)
        if enrichment_active:
            # A worker may already hold the pre-edit Record snapshot. Its stale
            # completion will be rejected by the source/revision guard; this
            # marker guarantees a fresh pass against the reviewed text instead
            # of leaving the Record stranded in a queued/skipped state.
            requeue_record_metadata(
                target,
                "Reviewed text changed during metadata enrichment; rerun against the current text.",
                force=True,
            )
        target["record_revision"] = current_revision + 1
        self._rewrite_targeted_record(build_id, target, previous_record)
        if enrichment_active:
            latest_build = self.repo.get_build(build_id)
            _prepend_metadata_priority(latest_build, record_id)
            self.repo.save_build(latest_build)
        _decorate_review_state(target)
        return target


    @_serialize_record_mutation
    def patch_metadata(self, build_id: str, record_id: str, changes: dict[str, Any], expected_revision: int | None = None) -> dict[str, Any]:
        record, _skipped = self._patch_metadata(build_id, record_id, changes, expected_revision)
        return record

    def _patch_metadata(
        self,
        build_id: str,
        record_id: str,
        changes: dict[str, Any],
        expected_revision: int | None = None,
        *,
        confirmed_absent_fields: set[str] | None = None,
    ) -> tuple[dict[str, Any], set[str]]:
        """Apply reviewer metadata edits; return the persisted record and the fields left unapplied.

        A field owed a blind second opinion is compared with the first answer and left
        unchanged, so callers must not treat it as decided.
        """
        confirmed_absent_fields = set(confirmed_absent_fields or ())
        unknown_absences = sorted(confirmed_absent_fields - set(changes))
        if unknown_absences:
            raise ValueError(
                "Confirmed-absence fields must also appear in the metadata decision batch: "
                + ", ".join(unknown_absences)
            )
        forbidden = sorted(set(changes) - self._editable_fields(build_id))
        if forbidden:
            raise ValueError(
                "Source-bound fields cannot be edited as record metadata. These system/source-bound fields are protected: "
                + ", ".join(forbidden)
            )
        # Validate the editable interpretive schema before modifying the persisted record.
        edit = self._edit_model(build_id)
        schema_input = {
            key: value
            for key, value in changes.items()
            if key in edit.model_fields and key not in confirmed_absent_fields
        }
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
            if key in confirmed_absent_fields:
                self._record_human_llm_feedback(
                    build_id,
                    key,
                    prior_value,
                    None,
                    prior_status,
                    target,
                )
                confirm_absence(
                    target,
                    key,
                    schema=schema,
                    prior=prior_assertion,
                    reason="Reviewer confirmed that no supported value applies to this record.",
                )
                project_record_assertions(target)
                decision_log.append(
                    {
                        "field": key,
                        "value": None,
                        "at": iso_now(),
                        "source": "confirmed_absent",
                    }
                )
                continue
            owed = _second_opinion_owed(target, key)
            if owed:
                # This is the independent second opinion, not an edit: it is compared with the first answer and the record is left alone.
                self._log_second_opinion(build_id, target, key, value, owed)
                skipped.add(key)
                continue
            answered_again = self._score_recheck(build_id, target, key, value, prior_status)
            # Decided once here and passed on: feedback, evidence and the audit trail agree.
            equivalence = compare_field_values(schema, key, prior_value, value, record=target, registry=review_registry(self.repo, build_id, target, schema))
            if not answered_again:
                self._record_human_llm_feedback(build_id, key, prior_value, value, prior_status, target, equivalence=equivalence)
                self._schedule_recheck(build_id, target, key, value)
                self._request_second_opinion(build_id, target, key, value)
            if not equivalence.same and isinstance(target.get("metadata_evidence"), dict):
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
                        and equivalence.relation != "equivalent"
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
                        evidence=_equivalent_evidence(prior_assertion, equivalence),
                    )
                project_record_assertions(target)
                decision_log.append({"field": key, "value": value, "at": iso_now(), "source": "human_override" if is_manifest_override else "human", **_equivalence_audit(prior_value, equivalence)})
        constraint_changes = apply_metadata_constraints(target, schema)
        for item in constraint_changes:
            decision_log.append({"field": item["field"], "value": item["value"], "at": iso_now(), "source": "deterministic_constraint", "reason": item["reason"]})
        target["metadata_decisions"] = decision_log[-100:]
        target["metadata_reviewed_at"] = iso_now()
        _mark_human_touch(target, [key for key in changes if key not in skipped])
        build = self.repo.get_build(build_id)
        review_frozen = "__review__" in {
            str(field) for field in (target.get("human_touched_fields") or [])
        }
        enrichment_active = _metadata_enrichment_active(build, target) and not review_frozen
        if enrichment_active and any(key not in skipped for key in changes):
            requeue_record_metadata(
                target,
                "Reviewer metadata changed during automatic enrichment; rerun against current human authority.",
                force=True,
            )
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
        if enrichment_active and any(key not in skipped for key in changes):
            latest_build = self.repo.get_build(build_id)
            _prepend_metadata_priority(latest_build, record_id)
            self.repo.save_build(latest_build)
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
                    decision_kind="absence" if key in confirmed_absent_fields else "value",
                    scope_id=build_id,
                )
        if any(key not in skipped for key in changes):
            self._schedule_metadata_exemplar_projection(build_id)
        _decorate_review_state(persisted)
        _present_for_reviewer(persisted)
        return persisted, skipped


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
                equivalence = compare_field_values(schema, key, prior_value, value, record=record, registry=review_registry(self.repo, build_id, record, schema))
                self._record_human_llm_feedback(build_id, key, prior_value, value, prior_status, record, equivalence=equivalence)
                if not equivalence.same and isinstance(record.get("metadata_evidence"), dict):
                    evidence_map = dict(record.get("metadata_evidence") or {})
                    evidence_map.pop(key, None)
                    record["metadata_evidence"] = evidence_map
                override = key in MANIFEST_INHERITED_FIELDS or bool(
                    prior_assertion is not None
                    and prior_assertion.value_status == "present"
                    and prior_assertion.value != value
                    and equivalence.relation != "equivalent"
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
                        evidence=_equivalent_evidence(prior_assertion, equivalence),
                    )
                project_record_assertions(record)
                decisions.append({"field": key, "value": value, "at": iso_now(), "source": "human_bulk", **_equivalence_audit(prior_value, equivalence)})
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


    def record_view(self, build_id: str, record_id: str) -> dict[str, Any]:
        """Deprecated compatibility read; navigation no longer records canonical activity."""
        target = self.repo.get_record(build_id, record_id)
        activity = dict(target.get("activity") or {})
        return {"record_id": record_id, "activity": activity}


    @_serialize_record_mutation
    def semantic_aliases(self, build_id: str, *, include_retired: bool = False) -> dict[str, Any]:
        """Reviewed alias sets for the build, and the identity kinds its schema compares."""
        schema = self._schema_for(build_id)
        kinds: dict[str, dict[str, Any]] = {}
        for name in schema.field_names():
            try:
                profile = schema.equivalence_profile_for(name)
            except KeyError:
                continue
            if profile.identity_kind and profile.mode in {"entity_name", "text", "lexical_phrase", "controlled"}:
                entry = kinds.setdefault(profile.identity_kind, {"kind": profile.identity_kind, "mode": profile.mode, "fields": []})
                entry["fields"].append(name)
        return {
            "items": list_alias_sets(self.repo, build_id, include_retired=include_retired),
            "kinds": sorted(kinds.values(), key=lambda item: str(item["kind"])),
        }

    def save_semantic_alias(self, build_id: str, *, kind: str, canonical_label: str, aliases: list[str], reason: str = "", replaces: str | None = None) -> dict[str, Any]:
        self._assert_human_review_available(build_id)
        entry = create_alias_set(
            self.repo, build_id, kind=kind, canonical_label=canonical_label, aliases=aliases,
            reason=reason, reviewer=current_reviewer.get(), replaces=replaces,
        )
        # Correction precedents are re-derived under the new identities.
        self._schedule_metadata_exemplar_projection(build_id)
        return entry

    @_serialize_record_mutation
    def update_voice_assignments(self, asset_id: str, assignments: dict[str, str]) -> dict[str, Any]:
        """Project reviewed diarized-voice names into every extant record."""
        reviewer = current_reviewer.get()
        asset = self.repo.update_voice_assignments(asset_id, assignments, reviewer=reviewer)
        resolved = {
            voice_id: str(item.get("display_name") or "").strip()
            for voice_id, item in (asset.get("voice_assignments") or {}).items()
            if isinstance(item, dict)
        }
        changed_records = 0
        builds: list[dict[str, Any]] = []
        offset = 0
        while True:
            page = self.repo.list_builds(offset=offset, limit=200, asset_id=asset_id)
            items = list(page.get("items") or [])
            builds.extend(items)
            if len(items) < 200:
                break
            offset += len(items)
        for build in builds:
            build_id = str(build.get("build_id") or "")
            records = self.repo.load_records(build_id)
            changed = False
            schema = self._schema_for(build_id)
            for record in records:
                if str(record.get("source_asset_id") or record.get("source_document_id") or "") != asset_id:
                    continue
                spans = list(record.get("source_spans") or [])
                voices: list[str] = []
                for span in spans:
                    voice_id = str(span.get("speaker") or "").strip()
                    if not voice_id:
                        continue
                    voices.append(voice_id)
                    name = resolved.get(voice_id, "")
                    if name:
                        span["resolved_speaker"] = name
                    else:
                        span.pop("resolved_speaker", None)
                if not voices or len(voices) != len(spans) or len(set(voices)) != 1:
                    continue
                voice_id = voices[0]
                value = resolved.get(voice_id) or voice_id
                prior = current_assertion_by_name(record, "speaker")
                create_human_assertion(
                    record,
                    "speaker",
                    value,
                    schema=schema,
                    supersedes=prior,
                    override=True,
                    actor=reviewer,
                    method="human_voice_assignment",
                    reason=f"Reviewer assigned the diarized voice {voice_id}.",
                )
                project_record_assertions(record)
                record["record_revision"] = int(record.get("record_revision") or 0) + 1
                record["updated_at"] = iso_now()
                changed = True
                changed_records += 1
            if changed:
                self.repo.save_records(build_id, records)
        return {"asset": asset, "records_updated": changed_records}

    def semantic_alias_sources(self, build_id: str) -> list[dict[str, Any]]:
        """Other corpus builds whose reviewed identities can be imported here."""
        return alias_sources(self.repo, build_id)

    def import_semantic_aliases(self, build_id: str, source_build_id: str, alias_set_ids: list[str] | None = None) -> dict[str, Any]:
        self._assert_human_review_available(build_id)
        result = import_alias_sets(
            self.repo, build_id, source_build_id, alias_set_ids=alias_set_ids, reviewer=current_reviewer.get(),
        )
        if result["imported"]:
            self._schedule_metadata_exemplar_projection(build_id)
        return result

    def retire_semantic_alias(self, build_id: str, alias_set_id: str) -> dict[str, Any]:
        self._assert_human_review_available(build_id)
        entry = retire_alias_set(self.repo, build_id, alias_set_id, reviewer=current_reviewer.get())
        self._schedule_metadata_exemplar_projection(build_id)
        return entry

    def metadata_decision(self, build_id: str, record_id: str, field: str, value: Any, expected_revision: int | None = None, confirm_no_supported_value: bool = False, evidence_block_ids: list[str] | None = None, evidence_source: str | None = None, evidence_note: str = "", external_evidence_block_ids: list[str] | None = None) -> dict[str, Any]:
        """Persist one human metadata decision and return authoritative review state.

        This endpoint is deliberately transactional from the UI's perspective:
        one call saves the value, marks the field human-confirmed, recomputes all
        derived metadata/queue state, and returns the updated record and build.
        """
        self._validate_decision_fields(build_id, [field])
        if evidence_block_ids:
            # Validate up front so a bad evidence binding cannot leave the value half-saved.
            selected = self.repo.get_record(build_id, record_id)
            allowed = set(map(str, selected.get("source_unit_ids") or []))
            allowed.update(map(str, selected.get("source_block_ids") or []))
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
            target["metadata_reviewed_at"] = iso_now()
            _mark_human_touch(target, [field])
            build = self.repo.get_build(build_id)
            review_frozen = "__review__" in {
                str(touched) for touched in (target.get("human_touched_fields") or [])
            }
            enrichment_active = _metadata_enrichment_active(build, target) and not review_frozen
            if enrichment_active:
                requeue_record_metadata(
                    target,
                    "Reviewer confirmed metadata absence during automatic enrichment; rerun against current human authority.",
                    force=True,
                )
            profile = self._profile_for(build_id)
            _sync_record_metadata_state(target, profile)
            target["record_revision"] = current_revision + 1
            self._rewrite_targeted_record(build_id, target, previous_record)
            if enrichment_active:
                latest_build = self.repo.get_build(build_id)
                _prepend_metadata_priority(latest_build, record_id)
                self.repo.save_build(latest_build)
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
            _record, skipped = self._patch_metadata(build_id, record_id, {field: value}, expected_revision)
            if field in skipped:
                return self._metadata_decision_result(build_id, record_id, applied=[], deferred=[field])
            if evidence_block_ids or external_evidence_block_ids or evidence_source == "reviewer_knowledge":
                # Bind the reviewer's selected evidence (or their own say-so) to the value just saved, in the same request.
                self.patch_evidence(
                    build_id, record_id, field, evidence_block_ids or [],
                    reason=evidence_note,
                    expected_revision=int(self.repo.get_record(build_id, record_id).get("record_revision") or 1),
                    source_kind="reviewer_knowledge" if evidence_source == "reviewer_knowledge" else "source_span",
                    external_block_ids=external_evidence_block_ids,
                )
        return self._finish_metadata_decisions(
            build_id,
            record_id,
            {field: None if confirm_no_supported_value else value},
            decision="absence" if confirm_no_supported_value else "value",
        )

    @_serialize_record_mutation
    def apply_metadata_decisions(
        self,
        build_id: str,
        record_id: str,
        decisions: dict[str, Any],
        expected_revision: int | None = None,
        confirmed_absent_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Persist several reviewer value decisions on one record as one revision.

        This is the single authoritative operation behind "Save all suggestions": every
        field goes through the same path as a one-field decision (human assertion,
        dispute resolution, reviewed-decision provenance, adjudication memory), so a
        batch accept is recorded as reviewer decisions rather than as a plain edit.
        """
        if not decisions:
            raise ValueError("Choose at least one metadata decision to save.")
        absence_fields = set(map(str, confirmed_absent_fields or []))
        missing_absences = sorted(absence_fields - set(decisions))
        if missing_absences:
            raise ValueError(
                "Confirmed-absence fields must also appear in the metadata decision batch: "
                + ", ".join(missing_absences)
            )
        non_null_absences = sorted(
            name for name in absence_fields if decisions.get(name) is not None
        )
        if non_null_absences:
            raise ValueError(
                "Confirmed-absence decisions must use null values: "
                + ", ".join(non_null_absences)
            )
        self._validate_decision_fields(build_id, decisions)
        _record, skipped = self._patch_metadata(
            build_id,
            record_id,
            decisions,
            expected_revision,
            confirmed_absent_fields=absence_fields,
        )
        applied = {name: value for name, value in decisions.items() if name not in skipped}
        if not applied:
            return self._metadata_decision_result(build_id, record_id, applied=[], deferred=sorted(skipped))
        return self._finish_metadata_decisions(
            build_id,
            record_id,
            applied,
            decision="value",
            deferred=sorted(skipped),
            absence_fields=absence_fields - skipped,
        )

    def _validate_decision_fields(self, build_id: str, fields: Any) -> None:
        editable = self._editable_fields(build_id)
        unsupported = [name for name in fields if name not in editable or name in {"needs_review", "review_reason"}]
        if unsupported:
            raise ValueError("Unsupported review metadata field: " + ", ".join(map(str, unsupported)))

    def _finish_metadata_decisions(
        self,
        build_id: str,
        record_id: str,
        decisions: dict[str, Any],
        *,
        decision: str,
        deferred: list[str] | None = None,
        absence_fields: set[str] | None = None,
    ) -> dict[str, Any]:
        """Settle disputes and adjudication memory for decisions that are already persisted."""
        current_record = self.repo.get_record(build_id, record_id, include_queue_version=True)
        previous_record = json.loads(json.dumps(current_record))
        warnings: list[str] = []
        absence_fields = set(absence_fields or (decisions if decision == "absence" else ()))
        value_decisions = {
            name: value for name, value in decisions.items() if name not in absence_fields
        }
        if value_decisions:
            warnings.extend(
                self._cascade_evidence_for_accepted(
                    build_id,
                    current_record,
                    value_decisions,
                )
            )
        disputes = current_record.get("metadata_disputes") if isinstance(current_record.get("metadata_disputes"), list) else []
        for dispute in disputes:
            name = dispute.get("field") if isinstance(dispute, dict) else None
            if name in decisions and not dispute.get("resolved_at"):
                dispute["resolved_at"] = iso_now()
                dispute["resolved_value"] = decisions[name]
                dispute["resolution_source"] = "human"
        current_record["metadata_disputes"] = disputes[-100:]
        _sync_record_metadata_state(current_record, self._profile_for(build_id))
        _settle_enrichment_review_reason(current_record)
        _decorate_review_state(current_record)
        if current_record != previous_record:
            self._rewrite_targeted_record(build_id, current_record, previous_record)
        build = self.repo.get_build(build_id)
        self._refresh_workflow_fields(build)
        self.repo.save_build(build)
        # Adjudication memory is derived, best-effort suggestion state. It is written
        # only after the authoritative record is saved; a failure is reported rather
        # than raised so it can never make a saved decision look unsaved.
        schema = self._schema_for(build_id)
        for name, value in decisions.items():
            try:
                remember_adjudication(
                    record_id=record_id,
                    text=str(current_record.get("text") or ""),
                    field=name,
                    value=value,
                    schema_version=str(build.get("schema_version") or ""),
                    decision="absence" if name in absence_fields else decision,
                    field_id=schema.field_id(name),
                    value_key=_identity_key_for(schema, name, current_record, review_registry(self.repo, build_id, current_record, schema)),
                )
            except Exception as exc:  # noqa: BLE001 - derived memory must not fail a saved decision
                warnings.append(f"Adjudication memory was not updated for {name}: {exc}")
        return self._metadata_decision_result(
            build_id,
            record_id,
            applied=list(decisions),
            deferred=deferred or [],
            warnings=warnings,
            record=current_record,
            build=build,
        )

    def _metadata_decision_result(
        self,
        build_id: str,
        record_id: str,
        *,
        applied: list[str],
        deferred: list[str],
        warnings: list[str] | None = None,
        record: dict[str, Any] | None = None,
        build: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = record if record is not None else self.repo.get_record(build_id, record_id, include_queue_version=True)
        build = build if build is not None else self.repo.get_build(build_id)
        _decorate_review_state(record)
        return {
            "applied": bool(applied),
            "changed_fields": applied,
            # Fields owed a blind second opinion: the answer was logged, the record unchanged.
            "deferred_fields": deferred,
            "warnings": warnings or [],
            "record": record,
            "build": build,
        }


    @_serialize_record_mutation
    def _evidence_candidates(self, build_id: str, record_id: str, field: str) -> tuple[Any, list[dict[str, Any]]]:
        target = self.repo.get_record(build_id, record_id)
        assertion = current_assertion_by_name(target, field)
        value = assertion.value if assertion is not None else target.get(field)
        blocks_by_id = self._blocks_for(build_id)
        unit_ids = target.get("source_unit_ids") or target.get("source_block_ids") or []
        return value, [blocks_by_id[b] for b in map(str, unit_ids) if b in blocks_by_id]

    def _evidence_field_metadata(self, build_id: str, field: str) -> dict[str, Any]:
        schema = self._schema_for(build_id)
        field_spec = schema.by_name().get(field)
        if field_spec is not None:
            field_metadata: dict[str, Any] = field_spec.model_dump(mode="json")
            field_metadata["group_label"] = schema.group(field_spec.group).label
            return field_metadata
        # Core/fixed fields do not have SchemaField rows; their owning group
        # still supplies schema-authored context without field-name rules.
        field_group = next(
            (group for group, names in schema.family_fields().items() if field in names),
            "",
        )
        return {
            "name": field,
            "group_label": schema.group(field_group).label if field_group else "",
            "instruction": schema.group(field_group).intro if field_group else "",
        }

    def _evidence_document_id(self, build_id: str, record: dict[str, Any]) -> str:
        return str(
            record.get("source_document_id")
            or record.get("source_asset_id")
            or self.repo.get_build(build_id).get("asset_id")
            or ""
        )

    def _cascade_evidence_for_accepted(
        self, build_id: str, record: dict[str, Any], fields: Any
    ) -> list[str]:
        """Run automatic evidence recovery, without its LLM stage, for accepted values nothing has bound yet.

        A reviewer can accept a value enrichment never looked at (a hint, a dropdown
        suggestion, a typed value). Recovery executes the assigned
        ``evidence_recovery`` pipeline, and the result stays advisory
        exactly as it would during enrichment (``backfilled``, no confidence): it
        points the reviewer at supporting spans but never counts as reviewed
        evidence. Returns warnings.
        """
        from .pipelines.evidence_recovery import (
            MISSING_SOURCE_DOCUMENT,
            execute_evidence_recovery,
        )
        from .source_embeddings import SourceEmbeddingProjection

        evidence = record.get("metadata_evidence") if isinstance(record.get("metadata_evidence"), dict) else {}
        pending = [
            name for name in fields
            if (assertion := current_assertion_by_name(record, name)) is not None
            and assertion.value not in (None, "", [])
            and not evidence.get(name)
        ]
        if not pending:
            return []
        blocks_by_id = self._blocks_for(build_id)
        unit_ids = record.get("source_unit_ids") or record.get("source_block_ids") or []
        blocks = [blocks_by_id[b] for b in map(str, unit_ids) if b in blocks_by_id]
        if not blocks:
            return []
        projection = SourceEmbeddingProjection(self._progressive_metadata_index.store)
        source_document_id = self._evidence_document_id(build_id, record)
        warnings: list[str] = []
        for name in pending:
            assertion = current_assertion_by_name(record, name)
            try:
                recovery = execute_evidence_recovery(
                    value=assertion.value, blocks=blocks, field=name,
                    field_metadata=self._evidence_field_metadata(build_id, name),
                    source_document_id=source_document_id, projection=projection,
                    llm_choice=None,
                    llm_skip_reason="Accepting a value never spends a model call on evidence recovery.",
                )
            except Exception as exc:  # noqa: BLE001 - advisory evidence must not fail a saved decision
                warnings.append(f"Evidence recovery did not run for {name}: {exc}")
                continue
            if recovery.status.get("skipped") == MISSING_SOURCE_DOCUMENT:
                warnings.append(recovery.status["reason"])
            entry = recovery.entry
            if entry:
                replace_assertion_evidence(record, assertion, [entry], reason=entry["reason"])
        project_record_assertions(record)
        return warnings

    def suggest_evidence(self, build_id: str, record_id: str, field: str, limit: int = 5) -> list[dict[str, Any]]:
        """Advisory, read-only ranking of the record's source blocks for a field's current value."""
        return self.suggest_evidence_result(build_id, record_id, field, limit=limit)["items"]

    def suggest_evidence_result(
        self, build_id: str, record_id: str, field: str, limit: int = 5
    ) -> dict[str, Any]:
        """Execute the assigned reviewer evidence pipeline and return advisory suggestions."""
        from .pipelines.evidence import execute_reviewer_evidence_pipeline
        from .pipelines.manager import pipeline_manager
        from .pipelines.models import PipelineDefinition
        from .pipelines.store import pipeline_store
        from .source_embeddings import SourceEmbeddingProjection

        value, blocks = self._evidence_candidates(build_id, record_id, field)
        record = self.repo.get_record(build_id, record_id)
        projection = SourceEmbeddingProjection(self._progressive_metadata_index.store)
        resolved = pipeline_manager.resolve("evidence_suggestion.reviewer")
        pipeline = PipelineDefinition.model_validate(resolved["pipeline"])
        execution = execute_reviewer_evidence_pipeline(
            pipeline=pipeline,
            resolved_hash=str(resolved.get("pipeline_hash") or ""),
            value=value,
            blocks=blocks,
            field_metadata=self._evidence_field_metadata(build_id, field),
            source_document_id=self._evidence_document_id(build_id, record),
            projection=projection,
            limit=limit,
        )
        status = dict(execution.status)
        try:
            pipeline_store.put_run(execution.trace)
        except Exception:  # noqa: BLE001 - telemetry must never block advisory review
            status["trace_warning"] = "Pipeline trace persistence failed."
        return {"items": execution.items, "status": status}

    def suggest_evidence_llm(
        self, build_id: str, record_id: str, field: str, request: dict[str, Any], limit: int = 5
    ) -> list[dict[str, Any]]:
        """Ask a model which of the record's blocks support the value; the answer is validated, never trusted."""
        from .corpus_models import EvidenceChoiceModel
        from .evidence_suggestions import LLM_METHOD, llm_prompt, validate_llm_choice

        value, blocks = self._evidence_candidates(build_id, record_id, field)
        if not blocks:
            return []
        prompt = llm_prompt(field, value, blocks)

        def invoke(role: str, attempts: int, escalated: bool) -> dict[str, Any]:
            if role not in _provider_roles(request):
                raise LookupError("No review provider is configured for this build.")
            return self._chat_json(
                request, prompt, response_model=EvidenceChoiceModel, max_tokens=800,
                schema_name="evidence_choice", attempts=attempts, build_id=build_id,
                roles=(role,), escalated=escalated,
            )

        # One trace per reviewer request. Without a resolvable pipeline no model is asked and
        # the request fails with the reason.
        try:
            session = ReviewerEvidenceChoiceSession.open()
        except RuntimeError as exc:
            raise ValueError(str(exc)) from exc
        try:
            result = session.run(invoke, response_contract="evidence_choice", providers=_provider_roles(request))
        except InterruptedError:
            session.finish(cancelled=True)
            raise
        except Exception:
            session.finish()
            raise
        session.finish()
        identity = session.identity()
        return [
            {**item, "method": LLM_METHOD, "model": str(request.get("model") or ""), "pipeline": identity}
            for item in validate_llm_choice(result, blocks, value, limit=limit)
        ]

    def patch_evidence(
        self,
        build_id: str,
        record_id: str,
        field: str,
        block_ids: list[str],
        confidence: float = 1.0,
        reason: str = "",
        expected_revision: int | None = None,
        source_kind: str = "source_span",
        external_block_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        if field not in self._schema_for(build_id).attribution_fields() and field not in self._edit_model(build_id).model_fields:
            raise ValueError(f"Unsupported metadata evidence field: {field}")
        if source_kind not in {"source_span", "reviewer_knowledge"}:
            raise ValueError(f"Unsupported evidence source kind: {source_kind}")
        target = self.repo.get_record(build_id, record_id)
        previous_record = json.loads(json.dumps(target))
        self._assert_human_review_available(build_id, target)
        current_revision = int(target.get("record_revision") or 1)
        if expected_revision is not None and current_revision != int(expected_revision):
            raise ValueError("This record changed after it was opened. Reload it before editing evidence.")
        self._push_record_review_history(build_id, action="evidence_edit", record_id=record_id, previous_record=previous_record)
        allowed_ids = set(map(str, target.get("source_unit_ids") or []))
        allowed_ids.update(map(str, target.get("source_block_ids") or []))
        unique_ids = list(dict.fromkeys(map(str, block_ids)))
        invalid = [block_id for block_id in unique_ids if block_id not in allowed_ids]
        if invalid:
            raise ValueError("Evidence blocks must belong to the selected record: " + ", ".join(invalid[:10]))
        # Spans a reviewer found elsewhere in the same source (another record). They are kept apart from the
        # record's own spans so exports and audits can always tell which is which.
        external_ids = [i for i in dict.fromkeys(map(str, external_block_ids or [])) if i not in allowed_ids]
        if external_ids:
            asset_ids = {str(b.get("block_id")) for b in self.repo.load_blocks(str(self.repo.get_build(build_id).get("asset_id") or ""))}
            unknown = [i for i in external_ids if i not in asset_ids]
            if unknown:
                raise ValueError("Evidence blocks must come from this build's source: " + ", ".join(unknown[:10]))
        knowledge = source_kind == "reviewer_knowledge"
        if knowledge:
            # The reviewer answers from their own knowledge: no span is cited, and the entry says so plainly.
            unique_ids, external_ids = [], []
        evidence = dict(target.get("metadata_evidence") or {})
        if unique_ids or external_ids or knowledge:
            entry: dict[str, Any] = {
                "block_ids": unique_ids,
                "confidence": max(0.0, min(1.0, float(confidence))),
                "reason": str(reason or ("Reviewer's own knowledge; no source span cited." if knowledge else "Human-reviewed evidence binding.")),
                "reviewed_by": "human",
                "reviewed_at": iso_now(),
                "source_kind": source_kind,
            }
            if external_ids:
                entry["external_block_ids"] = external_ids
            evidence[field] = entry
        else:
            evidence.pop(field, None)
        target["metadata_evidence"] = evidence
        schema = self._schema_for(build_id)
        migrate_record_assertions(target, schema)
        assertion = current_assertion_by_name(target, field)
        if assertion is not None:
            assertion_evidence = [dict(evidence[field])] if field in evidence else []
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
        source_units = self.repo.load_source_units(build_id)
        source_units, _replacement_ids = reconcile_source_units(
            source_units,
            retiring,
            pieces,
            created,
            source_document_id=str(build["asset_id"]),
            operation=operation,
            transaction_id=transaction_id,
        )
        remapped_evidence, pending_evidence = remap_evidence_bindings(
            retiring, created, source_units
        )
        for index, evidence in remapped_evidence.items():
            created[int(index)]["metadata_evidence"] = evidence
        if pending_evidence:
            prior_pending = self.repo.load_checkpoint(build_id, "evidence_remap_pending", {})
            pending_entries = list(prior_pending.get("entries") or []) if isinstance(prior_pending, dict) else []
            self.repo.save_checkpoint(
                build_id,
                "evidence_remap_pending",
                {"entries": [*pending_entries, *pending_evidence][-200:]},
            )
        for row in records:
            if not row.get("source_unit_ids"):
                row["source_unit_ids"] = list(row.get("source_block_ids") or [])
        successor_ids = [str(row["record_id"]) for row in created]
        stored = self.repo.load_checkpoint(build_id, "retired_records", {})
        entries = list(stored.get("entries") or []) if isinstance(stored, dict) else []
        # An undone edit brings its parents back to life; they are no longer retired.
        live_ids = {str(row.get("record_id")) for row in records}
        entries = [item for item in entries if str(item.get("record_id")) not in live_ids]
        entries.extend(tombstone(row, operation=operation, transaction_id=transaction_id, successors=successor_ids) for row in retiring)
        self.repo.save_checkpoint(build_id, "retired_records", {"entries": entries})
        records[lo:hi + 1] = created
        assert_active_source_unit_ownership(records, source_units)
        self.repo.save_source_units(build_id, source_units)
        current_build = self.repo.get_build(build_id)
        projection_state = dict(current_build.get("source_unit_embedding_projection") or {})
        projection_state.update({"status": "dirty", "dirty": True, "updated_at": iso_now()})
        current_build["source_unit_embedding_projection"] = projection_state
        self.repo.save_build(current_build)
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
            "new_source_unit_ids": [
                str(unit.get("source_unit_id") or unit.get("unit_id"))
                for unit in source_units
                if str(unit.get("transaction_id") or "") == transaction_id and unit.get("active")
            ],
            "retired_source_unit_ids": [
                str(unit.get("source_unit_id") or unit.get("unit_id"))
                for unit in source_units
                if str(unit.get("retired_transaction_id") or "") == transaction_id
            ],
            "evidence_remap_pending": pending_evidence,
            "source_unit_projection": projection_state,
            "transaction_id": transaction_id,
        }

    def retired_records(self, build_id: str) -> list[dict[str, Any]]:
        """Lineage tombstones for Records retired by structural edits (never reused IDs)."""
        stored = self.repo.load_checkpoint(build_id, "retired_records", {})
        live = {str(row.get("record_id")) for row in self.repo.load_records(build_id)}
        return [item for item in (stored.get("entries") if isinstance(stored, dict) else []) or [] if str(item.get("record_id")) not in live]

    def _blocks_for(self, build_id: str) -> dict[str, dict[str, Any]]:
        asset_id = self.repo.get_build(build_id)["asset_id"]
        blocks = {
            block["block_id"]: block
            for block in self.repo.load_blocks(asset_id)
            if block.get("block_id")
        }
        for unit in self.repo.load_source_units(build_id):
            if not unit.get("active", True):
                continue
            unit_id = str(unit.get("source_unit_id") or unit.get("unit_id") or "")
            if not unit_id:
                continue
            blocks[unit_id] = {
                **unit,
                "block_id": unit_id,
                "source_unit_id": unit_id,
            }
        return blocks

    @staticmethod
    def _unit_ranges(text: str, block_ids: list[str], blocks: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        """Locate compatibility blocks in reviewed text for unit reconciliation."""
        cursor = 0
        ranges: list[dict[str, Any]] = []
        for block_id in block_ids:
            block_text = str((blocks.get(block_id) or {}).get("text") or "").strip()
            if not block_text:
                continue
            found = text.find(block_text, cursor)
            if found < 0:
                return [{"unit_id": str(value), "start": 0, "end": len(text)} for value in block_ids]
            source = blocks.get(block_id) or {}
            ranges.append({
                "unit_id": str(block_id),
                "start": found,
                "end": found + len(block_text),
                "text": block_text,
                "type": source.get("type"),
                "locator_kind": source.get("locator_kind"),
                "page": source.get("page"),
                "locator_start": source.get("start"),
                "locator_end": source.get("end"),
            })
            cursor = found + len(block_text)
        return ranges

    @classmethod
    def _unit_ranges_for_slice(
        cls, text: str, block_ids: list[str], blocks: dict[str, dict[str, Any]], start: int, end: int
    ) -> list[dict[str, Any]]:
        spans = cls._unit_ranges(text, block_ids, blocks)
        selected: list[dict[str, Any]] = []
        for span in spans:
            lo, hi = int(span["start"]), int(span["end"])
            overlap_lo, overlap_hi = max(start, lo), min(end, hi)
            if overlap_lo >= overlap_hi:
                continue
            selected.append({
                **{
                    key: span[key]
                    for key in ("type", "locator_kind", "page", "locator_start", "locator_end")
                    if key in span
                },
                "unit_id": str(span["unit_id"]),
                "start": overlap_lo - lo,
                "end": overlap_hi - lo,
                "text": text[overlap_lo:overlap_hi],
            })
        return selected

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
            "unit_ranges": [
                *self._unit_ranges(str(first.get("text") or ""), list(first.get("source_unit_ids") or first.get("source_block_ids") or []), self._blocks_for(build_id)),
                *self._unit_ranges(str(second.get("text") or ""), list(second.get("source_unit_ids") or second.get("source_block_ids") or []), self._blocks_for(build_id)),
            ],
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
        unit_ids = list(target.get("source_unit_ids") or block_ids)
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
            {"text": left, "block_ids": lids, "precise": lp, "parents": [target],
             "unit_ranges": self._unit_ranges_for_slice(text, unit_ids, blocks, 0, offset)},
            {"text": right, "block_ids": rids, "precise": rp, "parents": [target],
             "unit_ranges": self._unit_ranges_for_slice(text, unit_ids, blocks, offset, len(text))},
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
        unit_ids = list(target.get("source_unit_ids") or block_ids)
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
                    "unit_ranges": [
                        *self._unit_ranges(str(prior.get("text") or ""), list(prior.get("source_unit_ids") or prior.get("source_block_ids") or []), blocks),
                        *self._unit_ranges_for_slice(text, unit_ids, blocks, 0, start),
                    ],
                })
            else:
                pieces.append({"text": before, "block_ids": bids, "precise": bp, "parents": [target],
                               "unit_ranges": self._unit_ranges_for_slice(text, unit_ids, blocks, 0, start)})
        cids, cp = ids(start, end)
        pieces.append({"text": chosen, "block_ids": cids, "precise": cp, "parents": [target],
                       "unit_ranges": self._unit_ranges_for_slice(text, unit_ids, blocks, start, end)})
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
                    "unit_ranges": [
                        *self._unit_ranges_for_slice(text, unit_ids, blocks, end, len(text)),
                        *self._unit_ranges(str(following.get("text") or ""), list(following.get("source_unit_ids") or following.get("source_block_ids") or []), blocks),
                    ],
                })
            else:
                pieces.append({"text": after, "block_ids": aids, "precise": ap, "parents": [target],
                               "unit_ranges": self._unit_ranges_for_slice(text, unit_ids, blocks, end, len(text))})
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
