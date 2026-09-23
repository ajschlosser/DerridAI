# Copyright 2026 Aaron John Schlosser, PhD.
"""Build creation, document-manifest patching, workflow-field refresh, and record validation.

Moved verbatim out of PdfCorpusBuildManager as a mixin (see corpus_review_actions.py's
module docstring for why a mixin, not free functions, and corpus_build_lifecycle.py's for
why every mixin's mypy stub block must be wrapped in `if TYPE_CHECKING:`). These nine
methods were deferred across five earlier extraction sessions because they depend on
CORPUS_PROFILES, PROFILE_VERSION, and the response models that used to live directly in
corpus_builder.py; that circular import is now resolved by corpus_models.py.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from .config import APP_VERSION
from .corpus_llm_helpers import _stage_limits, _validate_execution_budget
from .corpus_metadata import (
    ATTRIBUTION_EVIDENCE_FIELDS,
    MANIFEST_INHERITED_FIELDS,
)
from .corpus_models import (
    CORPUS_PROFILES,
    DOCUMENT_PROMPT_VERSION,
    METADATA_PROMPT_VERSION,
    PROFILE_VERSION,
    SCHEMA_VERSION,
    SEGMENTATION_PROMPT_VERSION,
    DocumentManifestModel,
    RecordMetadataModel,
)
from .corpus_record_quality import iso_now
from .corpus_segmentation import (
    _apply_manifest_metadata,
    _normalize_text,
    _scholarly_page_range,
)
from .metadata_schema import (
    DEFAULT_SCHEMA_ID,
    MetadataSchema,
    build_group_prompt,
    edit_model,
    response_model_for,
)
from .metadata_schema_store import SchemaNotFound
from .rag import _citation_strings

if TYPE_CHECKING:
    from pydantic import BaseModel


class ManifestWorkflowMixin:
    """Mixin members declared here exist on PdfCorpusBuildManager, not on this mixin itself.

    See corpus_review_actions.py's identical block for the full explanation, including why
    everything below is wrapped in `if TYPE_CHECKING:`.
    """

    if TYPE_CHECKING:
        repo: Any
        _lock: Any
        _schemas: Any
        _runtime_requests: dict[str, dict[str, Any]]
        _executor: Any

        def _run(self, build_id: str, request: dict[str, Any], resume: bool) -> None: ...
        def _interactive_llm_request(self, build_id: str, request: dict[str, Any] | None) -> dict[str, Any]: ...
        def _chat_json(self, request: dict[str, Any], prompt: str, *, response_model: type[BaseModel], max_tokens: int = ..., schema_name: str = ..., attempts: int = ..., build_id: str = ...) -> dict[str, Any]: ...
        def _schema_for(self, build_id: str) -> MetadataSchema: ...
        def _schema_of_build(self, build: dict[str, Any]) -> MetadataSchema: ...
        def _document_manifest(self, asset: dict[str, Any], blocks: list[dict[str, Any]], request: dict[str, Any], build_id: str) -> dict[str, Any]: ...
        def _catalog_enrich_manifest(self, manifest: dict[str, Any], request: dict[str, Any], build_id: str) -> dict[str, Any]: ...
        def _write_start_page_to_layout(self, asset_id: str, start_page: Any) -> None: ...
        def _rewrite_and_validate(self, build_id: str, records: list[dict[str, Any]]) -> dict[str, Any]: ...

    def create(self, request: dict[str, Any]) -> dict[str, Any]:
        asset = self.repo.get_asset(str(request["asset_id"]))
        profile_id = str(request.get("profile_id") or PROFILE_VERSION)
        if profile_id not in CORPUS_PROFILES:
            raise ValueError(f"Unknown corpus profile: {profile_id}")
        _validate_execution_budget(request)
        try:
            schema = self._schemas.get(str(request.get("schema_id") or DEFAULT_SCHEMA_ID))
        except SchemaNotFound as exc:
            raise ValueError(f"Unknown metadata schema: {request.get('schema_id')}") from exc
        guidance = request.get("run_guidance") or {}
        if not isinstance(guidance, dict):
            raise ValueError("Run guidance must be a field-to-guidance object")
        unknown_guidance_fields = sorted(set(guidance) - set(schema.field_names()))
        if unknown_guidance_fields:
            raise ValueError("Run guidance references fields outside the selected schema: " + ", ".join(unknown_guidance_fields))
        public_request = {k: v for k, v in request.items() if k not in {"api_key", "_review_provider"}}
        build = self.repo.create_build({
            "schema": schema.model_dump(mode="json"), "schema_id": schema.id, "schema_hash": schema.content_hash(), "schema_name": schema.name,
            "asset_id": asset["asset_id"],
            "source_sha256": asset["sha256"],
            "source_filename": asset["filename"],
            "source_page_count": asset["page_count"],
            "source_block_count": asset["block_count"],
            "schema_version": SCHEMA_VERSION,
            "metadata_schema_version": schema.schema_version,
            "profile_id": profile_id,
            "profile_version": CORPUS_PROFILES[profile_id]["version"],
            "app_version": APP_VERSION,
            "document_prompt_version": DOCUMENT_PROMPT_VERSION,
            "segmentation_prompt_version": SEGMENTATION_PROMPT_VERSION,
            "metadata_prompt_version": METADATA_PROMPT_VERSION,
            "provider": request.get("provider") or "ollama",
            "model": request.get("model"),
            "request": public_request,
            "manifest": {},
        })
        with self._lock:
            self._runtime_requests[build["build_id"]] = dict(request)
        self._executor.submit(self._run, build["build_id"], request, False)
        return build


    def preview_schema_group(self, schema: MetadataSchema, group: str, text: str, request: dict[str, Any], run: bool) -> dict[str, Any]:
        """Show, and optionally run, the prompt one group of a schema produces for a passage.

        This is for trying a schema without a build. It has none of a build's context (no document manifest, editorial
        memory or neighbouring records), so a real build's prompt is this one plus that context.
        """
        if group not in {g.key for g in schema.groups}:
            raise ValueError(f"The schema has no group '{group}'.")
        # Keep the preview's context envelope identical to the enrichment
        # prompt. A preview has no build-local values, but it must not use a
        # second, simplified prompt contract.
        context = f"""Document manifest: {json.dumps({}, ensure_ascii=False)}
Build-local editorial conventions confirmed on at least two other records (advisory context only; do not copy unless supported here): {json.dumps({}, ensure_ascii=False)}
Relevant human-confirmed examples retrieved from this build (few-shot guidance only; source evidence in THIS record remains authoritative): {json.dumps({}, ensure_ascii=False)}
How earlier enrichment in this build went (advisory only; evidence in THIS record remains authoritative). Includes reviewer accepted/rejected counts when present, plus values the previous pass inferred on two or more other records (working conventions, not confirmed). Do not copy these; use them only when THIS record's evidence supports the same reading: {json.dumps({}, ensure_ascii=False)}
Human-owned fields on this record (authoritative; DO NOT propose replacements): {json.dumps({}, ensure_ascii=False)}
Neighbor context (context only; never cite it as evidence): {json.dumps({"previous_record_tail": "", "next_record_head": ""}, ensure_ascii=False)}
Current source block IDs: ["preview-1"]
CURRENT REVIEWED RECORD TEXT:
{text}
"""
        profile = CORPUS_PROFILES[PROFILE_VERSION]
        prompt = build_group_prompt(schema, group, base_context=context, allowed_region_types=list(profile.get("region_types") or []), allowed_discourse_roles=list(profile.get("discourse_roles") or []))
        model_cls = response_model_for(schema, group, region_types=list(profile.get("region_types") or []) or None, roles=list(profile.get("discourse_roles") or []) or None)
        out: dict[str, Any] = {"prompt": prompt, "answer_schema": model_cls.model_json_schema(), "ran": False}
        if not run:
            return out
        started = time.monotonic()
        active = self._interactive_llm_request("", request or None)
        result = self._chat_json(active, prompt, response_model=model_cls, max_tokens=int(_stage_limits(active).get("indexing_num_predict", 1200)), schema_name=f"derridai_record_{group}", build_id="")
        return {**out, "ran": True, "answer": result, "seconds": round(time.monotonic() - started, 1)}


    def _edit_model(self, build_id: str) -> type[BaseModel]:
        return edit_model(self._schema_for(build_id), RecordMetadataModel)


    def _profile_of_build(self, build: dict[str, Any]) -> dict[str, Any]:
        """The build's profile, with the fields a person must review taken from its schema."""
        base = CORPUS_PROFILES.get(str(build.get("profile_id") or PROFILE_VERSION), CORPUS_PROFILES[PROFILE_VERSION])
        schema = self._schema_of_build(build)
        return {**base, "review_metadata_fields": schema.review_fields(), "attribution_evidence_fields": sorted(schema.attribution_fields()), "schema_field_names": schema.field_names()}


    def _profile_for(self, build_id: str) -> dict[str, Any]:
        return self._profile_of_build(self.repo.get_build(build_id))


    @classmethod
    def _refresh_workflow_fields(cls, build: dict[str, Any]) -> dict[str, Any]:
        """Persist one coherent, machine-readable corpus workflow/readiness model.

        UI stages are derived from independent facts rather than one overloaded
        status string. This keeps refreshes, retries, review completion and
        publication snapshots consistent.
        """
        record_count = int(build.get("record_count") or 0)
        accepted = int(build.get("accepted_count") or 0)
        rejected = int(build.get("rejected_count") or 0)
        reviewed = min(record_count, accepted + rejected)
        pending = max(0, record_count - reviewed)
        metadata_total = int(build.get("metadata_total") or record_count or 0)
        metadata_completed = int(build.get("metadata_completed") or 0)
        issue_summary_present = isinstance(build.get("metadata_issue_summary"), dict)
        issue_summary = build.get("metadata_issue_summary") if issue_summary_present else {}
        unresolved_fields = int(issue_summary.get("fields_unresolved") or 0)
        # Once the issue summary exists it is the authoritative publication-facing
        # metadata state. A stale worker counter must never manufacture blockers.
        metadata_remaining = int(issue_summary.get("records_incomplete") or 0) if issue_summary_present else max(0, metadata_total - metadata_completed)
        validation = build.get("validation") if isinstance(build.get("validation"), dict) else {}
        _ = build.get("source_quality") if isinstance(build.get("source_quality"), dict) else {}
        publication = build.get("publication") if isinstance(build.get("publication"), dict) else None
        running = str(build.get("status") or "") in {"queued", "running"}
        stage = str(build.get("stage") or "")
        profile = CORPUS_PROFILES.get(str(build.get("profile_id") or PROFILE_VERSION), CORPUS_PROFILES.get(PROFILE_VERSION, {}))
        required_fields = list(profile.get("publication_required_metadata_fields") or profile.get("required_metadata_fields") or [])
        required_document_fields = list(profile.get("publication_required_document_fields") or [])
        manifest = build.get("manifest") if isinstance(build.get("manifest"), dict) else {}
        missing_document_fields = [field for field in required_document_fields if manifest.get(field) in (None, "", [])]

        blockers: list[dict[str, Any]] = []
        no_publishable_records = bool(record_count and rejected == record_count and accepted == 0 and pending == 0)
        if no_publishable_records:
            blockers.append({"code": "no_publishable_records", "count": rejected})
        if pending:
            blockers.append({"code": "review_pending", "count": pending})
        # Rejected records are intentionally excluded from the publishable corpus.
        # They remain recoverable in review, but do not block publication of
        # accepted records. An all-rejected build is handled as a terminal
        # "no publishable records" outcome above.
        if int(build.get("needs_review_count") or 0):
            blockers.append({"code": "record_attention", "count": int(build.get("needs_review_count") or 0)})
        if int(build.get("boundary_review_count") or 0):
            blockers.append({"code": "boundary_attention", "count": int(build.get("boundary_review_count") or 0)})
        if (metadata_remaining or unresolved_fields) and not no_publishable_records:
            blockers.append({"code": "required_metadata", "count": max(metadata_remaining, int(issue_summary.get("records_incomplete") or 0)), "fields": required_fields})
        if missing_document_fields:
            blockers.append({"code": "required_document_metadata", "count": len(missing_document_fields), "fields": missing_document_fields})
        if validation and not bool(validation.get("source_valid", validation.get("valid", True))):
            blockers.append({"code": "source_validation", "count": len(validation.get("missing_block_ids") or []) + len(validation.get("text_fidelity_errors") or []) + len(validation.get("source_order_errors") or [])})
        if validation and not bool(validation.get("metadata_valid", validation.get("valid", True))):
            blockers.append({"code": "metadata_validation", "count": sum(len(validation.get(key) or []) for key in ("metadata_evidence_errors", "metadata_schema_errors", "citation_errors", "relationship_errors", "human_ownership_errors", "record_content_errors"))})
        # Raw PDF extraction findings remain in build.source_quality for audit,
        # but a reviewer may resolve a record-level extraction problem by
        # correcting the reviewed text while preserving source_extracted_text.
        # Publication is therefore gated by unresolved record source issues, not
        # forever by the immutable raw-page diagnostic.
        if int(build.get("source_problem_count") or 0):
            blockers.append({"code": "source_quality", "count": int(build.get("source_problem_count") or 0)})

        can_publish = bool(accepted > 0 and pending == 0 and not blockers and bool(validation.get("valid", True)) and accepted + rejected == record_count)
        if publication:
            next_action = "download_publication"
        elif no_publishable_records:
            next_action = "no_publishable_records"
        elif running:
            next_action = "wait"
        elif pending or int(build.get("needs_review_count") or 0) or int(build.get("boundary_review_count") or 0) or metadata_remaining or unresolved_fields:
            next_action = "review_records"
        elif missing_document_fields:
            next_action = "resolve_document_metadata"
        elif blockers:
            next_action = "resolve_validation"
        elif can_publish:
            next_action = "publish"
        else:
            next_action = "inspect"

        extraction_state = "complete" if int(build.get("source_block_count") or 0) else ("active" if running and stage in {"structure", "document_review"} else "waiting")
        construction_state = "complete" if record_count else ("active" if running and stage in {"segmenting", "reconciling"} else "waiting")
        enrichment_state = "complete" if metadata_total and metadata_remaining == 0 else ("active" if running and stage in {"enriching", "metadata_retry"} else "attention" if record_count else "waiting")
        review_state = "complete" if record_count and pending == 0 else ("attention" if record_count else "waiting")
        validation_state = "complete" if validation.get("valid") else ("blocked" if validation else "waiting")
        publication_state = "complete" if publication else ("active" if can_publish else "blocked" if record_count else "waiting")
        build["pipeline_state"] = {
            "current": next_action,
            "stages": {
                "extraction": {"state": extraction_state},
                "construction": {"state": construction_state},
                "enrichment": {"state": enrichment_state, "remaining_records": metadata_remaining, "unresolved_fields": unresolved_fields},
                "review": {"state": review_state, "reviewed": reviewed, "pending": pending, "accepted": accepted, "rejected": rejected},
                "validation": {"state": validation_state},
                "publication": {"state": publication_state},
            },
        }
        build["publication_readiness"] = {
            "can_publish": can_publish,
            "next_action": next_action,
            "blockers": blockers,
            "required_metadata_fields": required_fields,
            "required_document_fields": required_document_fields,
            "missing_document_fields": missing_document_fields,
            "records_total": record_count,
            "records_reviewed": reviewed,
            "records_accepted": accepted,
            "records_rejected": rejected,
            "records_pending": pending,
            "metadata_records_remaining": metadata_remaining,
            "metadata_fields_unresolved": unresolved_fields,
            "source_valid": bool(validation.get("source_valid", validation.get("valid", False))) if validation else False,
            "metadata_valid": bool(validation.get("metadata_valid", validation.get("valid", False))) if validation else False,
            "published": bool(publication),
            "no_publishable_records": no_publishable_records,
        }
        return build


    @staticmethod
    def validate_records(blocks: list[dict[str, Any]], records: list[dict[str, Any]], profile: dict[str, Any]) -> dict[str, Any]:
        source_ids = [block["block_id"] for block in blocks]
        source_index = {block_id: index for index, block_id in enumerate(source_ids)}
        used_ids = [block_id for record in records for block_id in record.get("source_block_ids") or []]
        missing = [block_id for block_id in source_ids if block_id not in used_ids]
        usage_counts = Counter(used_ids)
        duplicates = sorted(block_id for block_id, count in usage_counts.items() if count > 1)
        block_map = {block["block_id"]: block for block in blocks}
        fidelity_errors: list[str] = []
        order_errors: list[str] = []
        page_errors: list[str] = []
        printed_page_errors: list[str] = []
        evidence_errors: list[dict[str, str]] = []
        citation_errors: list[str] = []
        metadata_schema_errors: list[dict[str, str]] = []
        relationship_errors: list[dict[str, str]] = []
        human_ownership_errors: list[dict[str, str]] = []
        record_content_errors: list[dict[str, str]] = []
        suspicious: list[dict[str, Any]] = []
        previous_last = -1
        min_conf = float(profile.get("min_metadata_confidence") or 0.65)

        for record in records:
            record_id = str(record.get("record_id") or "")
            ids = [str(value) for value in record.get("source_block_ids") or []]
            expected = "\n\n".join(
                block_map[block_id]["text"].strip()
                for block_id in ids
                if block_id in block_map and block_map[block_id]["text"].strip()
            )
            # Reviewed/cleaned text is allowed to differ from the immutable PDF
            # extraction. Source fidelity validates the preserved extraction, not
            # the editorial layer that intentionally repairs layout/OCR noise.
            fidelity_text = record.get("source_extracted_text") if record.get("source_extracted_text") is not None else record.get("text")
            if _normalize_text(expected) != _normalize_text(fidelity_text or ""):
                fidelity_errors.append(record_id)

            indexes = [source_index[value] for value in ids if value in source_index]
            if indexes:
                if indexes != sorted(indexes) or any(b != a + 1 for a, b in zip(indexes, indexes[1:])):
                    order_errors.append(record_id)
                if indexes[0] <= previous_last:
                    order_errors.append(record_id)
                previous_last = max(previous_last, indexes[-1])

            expected_pdf_pages = sorted({int(block_map[value]["page"]) for value in ids if value in block_map})
            actual_pdf_pages = sorted(int(value) for value in record.get("pdf_pages") or [] if isinstance(value, int))
            if expected_pdf_pages != actual_pdf_pages:
                page_errors.append(record_id)
            group = [block_map[value] for value in ids if value in block_map]
            expected_start, expected_end = _scholarly_page_range(group)
            if record.get("page_start") != expected_start or record.get("page_end") != expected_end:
                page_errors.append(record_id)
            source_labels = [str(block.get("printed_page_label") or "").strip() for block in group]
            disposition = str(record.get("review_disposition") or ("accepted" if record.get("accepted") else "rejected" if record.get("rejected") else "pending"))
            if disposition == "rejected":
                # Keep rejected records in topology/source validation so the workspace
                # remains auditable, but exclude them from publication-facing
                # metadata/content requirements.
                continue
            if ids and not any(source_labels):
                printed_page_errors.append(record_id)

            try:
                RecordMetadataModel.model_validate({
                    key: record.get(key)
                    for key in RecordMetadataModel.model_fields
                    if key in record
                })
            except ValidationError as exc:
                metadata_schema_errors.append({"record_id": record_id, "reason": str(exc)[:1200]})

            if not str(record.get("text") or "").strip():
                record_content_errors.append({"record_id": record_id, "reason": "record text is empty"})
            if str(record.get("discourse_role") or "") == "reported_position" and "position_holder" in (profile.get("schema_field_names") or ["position_holder"]) and not record.get("position_holder"):
                relationship_errors.append({"record_id": record_id, "reason": "reported_position requires a position_holder"})
            touched = {str(value) for value in (record.get("human_touched_fields") or [])}
            status_map = record.get("metadata_field_status") if isinstance(record.get("metadata_field_status"), dict) else {}
            for field in touched:
                if field.startswith("__"):
                    continue
                info = status_map.get(field) if isinstance(status_map.get(field), dict) else {}
                if str(info.get("status") or "") == "model_inferred":
                    human_ownership_errors.append({"record_id": record_id, "reason": f"{field} is human-touched but still marked model_inferred"})

            evidence = record.get("metadata_evidence") if isinstance(record.get("metadata_evidence"), dict) else {}
            valid_ids = set(ids)
            for field in (profile.get("attribution_evidence_fields") or ATTRIBUTION_EVIDENCE_FIELDS):
                value = record.get(field)
                if value in (None, "", []):
                    continue
                info = evidence.get(field) if isinstance(evidence.get(field), dict) else None
                if not info:
                    evidence_errors.append({"record_id": record_id, "field": field, "reason": "missing evidence"})
                    continue
                bound = [str(v) for v in info.get("block_ids") or [] if str(v) in valid_ids]
                try:
                    confidence = float(info.get("confidence") or 0)
                except (TypeError, ValueError):
                    confidence = 0.0
                if not bound:
                    evidence_errors.append({"record_id": record_id, "field": field, "reason": "no valid source block"})
                elif confidence < min_conf:
                    evidence_errors.append({"record_id": record_id, "field": field, "reason": f"confidence {confidence:.2f} below {min_conf:.2f}"})

            if record.get("work") and record.get("document_author"):
                if not str(record.get("inline_citation") or "").strip() or not str(record.get("full_citation") or "").strip():
                    citation_errors.append(record_id)

            length = len(record.get("text") or "")
            if length < int(profile.get("soft_min_chars") or 0) or length > int(profile.get("soft_max_chars") or 10**9):
                suspicious.append({
                    "record_id": record_id,
                    "text_length": length,
                    "reason": "Length is an audit warning only; it did not create or change a semantic boundary.",
                })

        source_valid = not missing and not duplicates and not fidelity_errors and not order_errors and not page_errors
        metadata_valid = not evidence_errors and not citation_errors and not printed_page_errors and not metadata_schema_errors and not relationship_errors and not human_ownership_errors and not record_content_errors
        return {
            "source_block_count": len(source_ids),
            "used_block_count": len(used_ids),
            "coverage": (len(set(used_ids) & set(source_ids)) / len(source_ids)) if source_ids else 1.0,
            "missing_block_ids": missing,
            "duplicate_block_ids": duplicates,
            "text_fidelity_errors": fidelity_errors,
            "source_order_errors": sorted(set(order_errors)),
            "page_mapping_errors": sorted(set(page_errors)),
            "printed_page_label_errors": sorted(set(printed_page_errors)),
            "metadata_evidence_errors": evidence_errors,
            "metadata_schema_errors": metadata_schema_errors,
            "relationship_errors": relationship_errors,
            "human_ownership_errors": human_ownership_errors,
            "record_content_errors": record_content_errors,
            "citation_errors": sorted(set(citation_errors)),
            "suspicious_record_sizes": suspicious,
            "source_valid": source_valid,
            "metadata_valid": metadata_valid,
            "valid": source_valid and metadata_valid,
        }


    def regenerate_manifest(self, build_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Ask the model for the document analysis again and fill only what is still empty.

        A build whose first analysis failed (a model that was still loading, a restart) falls back to the PDF's own
        properties. This tries again with the current provider without touching anything a person has entered or
        that an earlier analysis already found; values that are missing are added through the ordinary manifest save,
        so records inherit them and the affected ones are reopened as for any manifest edit.
        """
        build = self.repo.get_build(build_id)
        if build.get("status") in {"queued", "running"}:
            raise ValueError("Wait for the active corpus operation to finish before analysing the document again.")
        if build.get("status") == "published":
            raise ValueError("Published builds are immutable.")
        asset = self.repo.get_asset(str(build.get("asset_id") or ""))
        blocks = self.repo.load_blocks(str(build.get("asset_id") or ""))
        active_request = self._interactive_llm_request(build_id, request or None)
        fresh = self._document_manifest(asset, blocks, active_request, build_id)
        if bool(active_request.get("auto_enrich_work_metadata", True)):
            fresh = self._catalog_enrich_manifest(fresh, active_request, build_id)
        current = dict(build.get("manifest") or {})
        empty: tuple[object, ...] = (None, "", [])
        filled = {
            key: fresh[key] for key in DocumentManifestModel.model_fields
            if current.get(key) in empty and fresh.get(key) not in empty
        }
        if not filled:
            return {"build": build, "filled": []}
        return {"build": self.patch_manifest(build_id, filled), "filled": sorted(filled)}


    def patch_manifest(self, build_id: str, changes: dict[str, Any], expected_revision: int | None = None) -> dict[str, Any]:
        # Serialized with enrichment's own record writes: this rewrites every record's inherited fields, and a
        # pass merging results at the same moment must not have its results overwritten by a stale copy.
        build = self.repo.get_build(build_id)
        if build.get("status") in {"queued", "running"}:
            stage = str(build.get("stage") or "")
            if stage not in {"enriching", "metadata_retry", "metadata_enrichment_rerun"}:
                raise ValueError("Document metadata becomes editable after segmentation is complete.")
            if {"main_text_start_page", "main_text_end_page"} & set(changes):
                raise ValueError("Main-text page boundaries are structural and cannot change while background enrichment is running.")
        current_revision = int(build.get("manifest_revision") or 1)
        if expected_revision is not None and int(expected_revision) != current_revision:
            raise ValueError("This document manifest changed after it was opened. Reload it before saving.")
        allowed = set(DocumentManifestModel.model_fields)
        unknown = sorted(set(changes) - allowed)
        if unknown:
            raise ValueError(f"Unknown document manifest field(s): {', '.join(unknown)}")
        current = dict(build.get("manifest") or {})
        candidate = {key: current.get(key) for key in allowed}
        candidate.update(changes)
        validated = DocumentManifestModel.model_validate(candidate).model_dump(mode="json")
        manifest = {**current, **validated}
        manifest["source_asset_id"] = build.get("asset_id")
        start_changed = "main_text_start_page" in changes and validated.get("main_text_start_page") != current.get("main_text_start_page")
        if start_changed:
            manifest.pop("main_text_start_inference", None)  # its clues describe a value that is no longer the one in use
            self._write_start_page_to_layout(str(build.get("asset_id") or ""), validated.get("main_text_start_page"))
        build["manifest"] = manifest
        build["manifest_revision"] = current_revision + 1
        build["manifest_reviewed_at"] = iso_now()
        self.repo.save_checkpoint(build_id, "manifest", manifest)
        self.repo.save_build(build)

        records = self.repo.load_records(build_id)
        if records:
            for record in records:
                # The page range also classifies the record (main text, front matter, back matter), so a change to it
                # must count as a change here even though those fields are not inherited from the manifest.
                before = ({field: record.get(field) for field in MANIFEST_INHERITED_FIELDS}, record.get("inline_citation"), record.get("full_citation"), record.get("primary_text"), record.get("region_type"))
                field_status = record.get("metadata_field_status") if isinstance(record.get("metadata_field_status"), dict) else {}
                if start_changed:
                    # The layout plan labelled these records from the old start page; the new one relabels them.
                    for field in ("region_type", "primary_text"):
                        info = field_status.get(field)
                        if isinstance(info, dict) and info.get("method") == "human_document_layout":
                            field_status.pop(field, None)
                for field in MANIFEST_INHERITED_FIELDS:
                    info = field_status.get(field) if isinstance(field_status.get(field), dict) else {}
                    if str(info.get("status") or "") in {"human_override", "human_confirmed"}:
                        continue
                    record.pop(field, None)
                    if str(info.get("status") or "") == "inherited":
                        field_status.pop(field, None)
                record["metadata_field_status"] = field_status
                _apply_manifest_metadata(record, manifest)
                inline, full = _citation_strings(record)
                record["inline_citation"] = inline
                record["full_citation"] = full
                after = ({field: record.get(field) for field in MANIFEST_INHERITED_FIELDS}, inline, full, record.get("primary_text"), record.get("region_type"))
                # A record whose inherited values did not actually change has nothing new to review: leave its
                # acceptance alone instead of reopening every record for an edit that did not touch it.
                if after == before:
                    continue
                record["accepted"] = False
                record["needs_review"] = True
                record["review_reason"] = "Document manifest changed during human review; inherited metadata and citations were regenerated."
                record["record_revision"] = int(record.get("record_revision") or 1) + 1
            self._rewrite_and_validate(build_id, records)
            build = self.repo.get_build(build_id)
        return build

