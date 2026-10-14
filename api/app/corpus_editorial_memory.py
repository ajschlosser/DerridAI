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

"""Editorial memory: advisory conventions and few-shot examples drawn from human decisions.

Only human-confirmed/overridden fields become eligible conventions or examples; nothing
here is copied as truth into a record, only offered as advisory context for a later LLM
pass. Moved verbatim out of PdfCorpusBuildManager as a mixin (see corpus_review_actions.py's
module docstring for why a mixin, not free functions, and corpus_build_lifecycle.py's for
why every mixin's mypy stub block must be wrapped in `if TYPE_CHECKING:`).
"""

from __future__ import annotations

import json
import re
import uuid
from typing import TYPE_CHECKING, Any

from . import experiment
from .corpus_enrichment_helpers import _editorial_tokens
from .corpus_record_quality import iso_now
from .corpus_reviewer_helpers import _second_opinion_owed
from .enrichment_cycles import learn_from_pass
from .field_assertions import (
    current_assertions,
    migrate_record_assertions,
    project_record_assertions,
)
from .metadata_exemplar_retrieval import DEFAULT_FETCH_K, DEFAULT_MMR_LAMBDA
from .metadata_exemplars import (
    DEFAULT_PROMPT_TOKEN_BUDGET,
    PROMPT_CHARS_PER_TOKEN,
    budget_prompt_examples,
    build_correction_exemplars,
    build_metadata_exemplar,
    prompt_example,
    prompt_example_token_estimate,
    reviewed_values,
)
from .metadata_precedents_cache import (
    cached_field,
    precedent_mode,
    rank_candidates,
    resolve_cached_precedents,
)
from .pipelines.precedent_remap import RemapSession
from .semantic_identity_store import registry_factory, reviewed_value_relation


class EditorialMemoryMixin:
    """Mixin members declared here exist on PdfCorpusBuildManager, not on this mixin itself.

    See corpus_review_actions.py's identical block for the full explanation, including why
    everything below is wrapped in `if TYPE_CHECKING:`.
    """

    if TYPE_CHECKING:
        repo: Any
        _lock: Any
        _global_learning: Any
        _progressive_metadata_index: Any
        _progressive_metadata_warning_builds: set[str]
        _cache_lock: Any

        def _append_warning(self, build_id: str, message: str) -> None: ...
        def _blocks_for(self, build_id: str) -> dict[str, dict[str, Any]]: ...
        def _editable_fields(self, build_id: str) -> set[str]: ...
        def _schema_for(self, build_id: str) -> Any: ...


    def _editorial_memory(
        self,
        build_id: str,
        current_record: dict[str, Any] | None = None,
        *,
        exclude_record_id: str = "",
        use_global: bool = True,
        use_progressive: bool = True,
        include_canonical: bool = False,
        field_filter: set[str] | None = None,
        record_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build advisory context from human decisions and the last enrichment pass.

        Only human-confirmed/overridden fields are eligible as conventions and few-shot
        examples. Repeated values become advisory conventions after two confirmations.
        ``pass_learning`` also includes last-pass LLM inferences on two or more records
        (working conventions, not confirmed) so a later pass can start before every
        record has been reviewed. Nothing here is copied as truth.

        ``include_canonical`` adds ``canonical_exemplars`` (exemplar ID -> exemplar) for callers
        that must re-verify stored precedent references; it is never part of an API response.
        ``field_filter`` lets latency-sensitive callers retrieve only the metadata fields that
        are actually scheduled for this Record.
        """
        try:
            rows = (
                self.repo.load_records(build_id) if record_ids is None
                else [row for row in self.repo.get_records(build_id, record_ids) if row is not None]
            )
            build = self.repo.get_build(build_id)
        except Exception as exc:
            # Editorial memory only supplies advisory few-shot context; records
            # are never altered by it. Proceed without it but say so on the build.
            self._append_warning(build_id, f"Editorial memory was unavailable; enrichment ran without reviewer examples ({exc}).")
            return {"conventions": {}, "examples": {}, "pass_learning": {}}
        reset_at = str(build.get("editorial_memory_reset_at") or "")
        # Exact source blocks let reviewed field evidence become a provenance-bound
        # exemplar. Builds without resolvable blocks keep the existing record-excerpt
        # fallback; progressive memory must never make enrichment unavailable.
        blocks_by_id: dict[str, dict[str, Any]] = {}
        asset_id = str(build.get("asset_id") or "")
        if asset_id:
            try:
                selected_ids = list(dict.fromkeys(
                    str(block_id) for row in rows
                    for block_id in (row.get("source_unit_ids") or row.get("source_block_ids") or [])
                ))
                blocks = (
                    self.repo.load_blocks(asset_id) if record_ids is None
                    else self.repo.load_selected_blocks(asset_id, selected_ids)
                )
                blocks_by_id = {
                    str(block.get("block_id") or ""): block
                    for block in blocks
                    if isinstance(block, dict) and str(block.get("block_id") or "")
                }
            except Exception:  # noqa: BLE001 - lexical editorial memory remains the safe fallback
                blocks_by_id = {}
        schema_payload = build.get("schema") if isinstance(build.get("schema"), dict) else {}
        schema_id = str(schema_payload.get("id") or build.get("schema_id") or "")
        # Do not use build["schema_version"] here: that is the corpus/publication
        # schema version on older builds, not the metadata-schema contract.
        schema_version = str(
            schema_payload.get("schema_version")
            or build.get("metadata_schema_version")
            or ""
        )
        try:
            # Equivalence policy for corrections and precedent identity keys; without a
            # readable schema, values compare exactly as before.
            metadata_schema: Any = self._schema_for(build_id)
        except Exception:  # noqa: BLE001 - advisory memory must not fail enrichment
            metadata_schema = None
        registry_for = registry_factory(self.repo, build_id, metadata_schema)
        schema_fields = {
            str(item.get("name") or ""): item
            for item in schema_payload.get("fields") or []
            if isinstance(item, dict) and str(item.get("name") or "")
        }
        group_profiles = {
            str(item.get("key") or ""): item.get("retrieval_profile")
            for item in schema_payload.get("groups") or []
            if isinstance(item, dict)
            and str(item.get("key") or "")
            and isinstance(item.get("retrieval_profile"), dict)
        }
        core_field_ids = {
            "region_type": "derridai.region_type",
            "primary_text": "derridai.primary_text",
            "discourse_role": "derridai.discourse_role",
        }
        field_ids = {
            field: str(item.get("field_id") or core_field_ids.get(field) or "")
            for field, item in schema_fields.items()
        }
        field_ids.update(core_field_ids)
        if not schema_fields:
            # Older builds did not persist the copied schema. Canonicalize their
            # legacy status maps once, then recover stable compatibility identities
            # from the selected assertions instead of treating the status map as
            # scholarly authority.
            for row in rows:
                migrate_record_assertions(row)
            for row in rows:
                for assertion in current_assertions(row):
                    field = str(assertion.field_name or "")
                    if field and field not in field_ids:
                        field_ids[field] = str(assertion.field_id or f"legacy.{field}")
        field_limits: dict[str, int] = {}
        field_min_similarity: dict[str, float] = {}
        field_correction_limits: dict[str, int] = {}
        field_match_ids: dict[str, list[str]] = {}
        enabled_fields: set[str] = set()
        correction_fields: set[str] = set()
        confirmed_absence_fields: set[str] = set()
        for field, _field_id in field_ids.items():
            if field_filter is not None and field not in field_filter:
                continue
            item = schema_fields.get(field, {})
            profile = item.get("retrieval_profile") if isinstance(item, dict) else None
            if not isinstance(profile, dict):
                group_key = (
                    "discourse"
                    if field in core_field_ids
                    else str(item.get("group") or "")
                )
                profile = group_profiles.get(group_key)
            if isinstance(profile, dict) and (
                not bool(profile.get("enabled", True))
                # Preserve the meaning of already-copied legacy schemas while
                # new schemas no longer serialize this redundant routing flag.
                or profile.get("use_for_metadata_enrichment") is False
            ):
                continue
            enabled_fields.add(field)
            if profile is None or bool(profile.get("include_corrections", True)):
                correction_fields.add(field)
            if profile is None or bool(profile.get("include_confirmed_absence", True)):
                confirmed_absence_fields.add(field)
            if profile is not None:
                field_limits[field] = int(profile.get("max_items", 2) or 0)
                field_min_similarity[field] = float(profile.get("min_similarity", 0) or 0)
                field_correction_limits[field] = int(profile.get("max_corrections", 2) or 0)
                field_match_ids[field] = [str(item) for item in profile.get("match_field_ids") or []]
        # Policies name analogy fields by stable identity; exemplars are compared by
        # name inside this build's schema. Core fields have both "core." and
        # "derridai." identities in circulation, so both resolve.
        name_by_id: dict[str, str] = {}
        for name, identity in field_ids.items():
            name_by_id[identity] = name
            name_by_id[f"core.{name}"] = name
        field_match_fields = {
            field: [name_by_id[item] for item in ids if item in name_by_id]
            for field, ids in field_match_ids.items()
            if ids
        }
        source_document_id = str(build.get("source_document_id") or asset_id or "")

        counts: dict[str, dict[str, tuple[Any, int]]] = {}
        eligible: list[tuple[dict[str, Any], str, Any]] = []
        trusted_rows: dict[str, dict[str, Any]] = {}
        canonical_exemplars: list[dict[str, Any]] = []
        exemplar_by_record_field: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            record_id = str(row.get("record_id") or "")
            if exclude_record_id and record_id == exclude_record_id:
                continue
            if reset_at and str(row.get("human_touched_at") or "") <= reset_at:
                continue
            if experiment.is_gold(record_id):
                continue  # the frozen gold set is scored, never learned from
            migrate_record_assertions(row)
            project_record_assertions(row)
            for assertion in current_assertions(row):
                field = str(assertion.field_name or "")
                if field not in enabled_fields:
                    continue
                if assertion.value_status == "confirmed_absent":
                    if field not in confirmed_absence_fields or _second_opinion_owed(row, field):
                        continue
                    exemplar = build_metadata_exemplar(
                        row,
                        field,
                        blocks_by_id,
                        schema_id=schema_id,
                        schema_version=schema_version,
                        source_document_id=source_document_id,
                        field_id=str(assertion.field_id or field_ids.get(field, "")),
                        schema=metadata_schema,
                        registry=registry_for(row),
                    )
                    if exemplar is not None:
                        canonical_exemplars.append(exemplar)
                        trusted_rows[record_id or str(id(row))] = row
                    continue
                if assertion.authority_status not in {"human_confirmed", "human_override"}:
                    continue
                if _second_opinion_owed(row, field):
                    continue
                value = row.get(field)
                if value in (None, "", []):
                    continue
                key = json.dumps(value, ensure_ascii=False, sort_keys=True)
                prior = counts.setdefault(field, {}).get(key)
                counts[field][key] = (value, (prior[1] if prior else 0) + 1)
                trusted_rows[record_id or str(id(row))] = row
                exemplar = build_metadata_exemplar(
                    row,
                    field,
                    blocks_by_id,
                    schema_id=schema_id,
                    schema_version=schema_version,
                    source_document_id=source_document_id,
                    field_id=str(assertion.field_id or field_ids.get(field, "")),
                    schema=metadata_schema,
                    registry=registry_for(row),
                )
                if exemplar is not None:
                    canonical_exemplars.append(exemplar)
                    exemplar_by_record_field[(record_id, field)] = exemplar

                # Lexical examples follow the schema's retrieval policy (enabled_fields),
                # not a fixed list of field names.
                eligible.append((row, field, value))
        conventions: dict[str, Any] = {}
        for field, values in counts.items():
            ranked = sorted(values.values(), key=lambda item: item[1], reverse=True)
            if ranked and ranked[0][1] >= 2:
                conventions[field] = {"value": ranked[0][0], "confirmed_records": ranked[0][1]}

        current_text = str((current_record or {}).get("text") or "")
        current_tokens = _editorial_tokens(current_text)
        by_field: dict[str, list[dict[str, Any]]] = {}
        for row, field, value in eligible:
            row_tokens = _editorial_tokens(str(row.get("text") or ""))
            union = current_tokens | row_tokens
            similarity = (len(current_tokens & row_tokens) / len(union)) if union else 0.0
            # Region agreement is a useful but non-authoritative tie breaker.
            if current_record and row.get("region_type") and row.get("region_type") == current_record.get("region_type"):
                similarity += 0.08
            similarity = min(1.0, similarity)
            exemplar = exemplar_by_record_field.get(
                (str(row.get("record_id") or ""), field)
            )
            if exemplar is not None:
                example = prompt_example(exemplar, similarity=similarity)
            else:
                # Older builds and decisions without reviewed evidence keep the
                # original behavior. Marking the fallback prevents downstream
                # semantic indexing from mistaking a whole-record excerpt for exact evidence.
                example = {
                    "record_id": str(row.get("record_id") or ""),
                    "value": value,
                    "similarity": round(similarity, 4),
                    "evidence_bound": False,
                    "excerpt": re.sub(r"\s+", " ", str(row.get("text") or "")).strip()[:420],
                }
            by_field.setdefault(field, []).append(example)
        # A human correction is more informative than an ordinary confirmation:
        # it identifies both the supported value and a concrete model failure.
        # Keep that rejected value negative; never flatten it into a positive example.
        for row in trusted_rows.values():
            for correction in build_correction_exemplars(
                row,
                blocks_by_id,
                schema_id=schema_id,
                schema_version=schema_version,
                source_document_id=source_document_id,
                field_ids=field_ids,
                schema=metadata_schema,
                registry_for=registry_for,
            ):
                field = str(correction.get("field_name") or "")
                if (
                    field
                    and field in correction_fields
                    and not _second_opinion_owed(row, field)
                ):
                    canonical_exemplars.append(correction)
        canonical_exemplars = list({
            str(item.get("metadata_exemplar_id") or ""): item
            for item in canonical_exemplars
            if str(item.get("metadata_exemplar_id") or "")
        }.values())

        examples: dict[str, list[dict[str, Any]]] = {}
        for field, items in by_field.items():
            ranked = sorted(items, key=lambda item: float(item.get("similarity") or 0), reverse=True)
            # Keep prompts compact. Include up to four field-specific examples;
            # zero-overlap examples are still useful only for discourse role when
            # a repeated build convention exists.
            configured_limit = field_limits.get(field)
            prelimit = max(4, int(configured_limit)) if configured_limit is not None else 4
            kept = [
                item for item in ranked
                if float(item.get("similarity") or 0) > 0
            ][:prelimit]
            if not kept and field == "discourse_role" and conventions.get(field):
                kept = ranked[:max(2, prelimit)]
            if kept:
                examples[field] = kept
        # Resolve the exact computational pipeline independently from the
        # metadata schema. The schema still owns field eligibility, similarity
        # floors, analogy fields, and positive/correction quotas.
        metadata_pipeline_plan = None
        metadata_pipeline_definition = None
        metadata_pipeline_info: dict[str, Any] = {}
        metadata_pipeline_trace: dict[str, Any] | None = None
        if use_progressive:
            try:
                from .pipelines.execution_resolution import (
                    resolve_execution_pipeline,
                )
                from .pipelines.metadata_precedents import (
                    compile_metadata_precedent_pipeline,
                )
                from .pipelines.models import PipelineDefinition

                resolved_pipeline = resolve_execution_pipeline(
                    "metadata_precedents",
                    build.get("request") if isinstance(build.get("request"), dict) else None,
                )
                resolved_definition = PipelineDefinition.model_validate(
                    resolved_pipeline["pipeline"]
                )
                metadata_pipeline_plan = compile_metadata_precedent_pipeline(
                    resolved_definition
                )
                metadata_pipeline_definition = resolved_definition
                metadata_pipeline_info = {
                    "pipeline_id": resolved_definition.pipeline_id,
                    "pipeline_version": resolved_definition.version,
                    "pipeline_hash": resolved_pipeline.get("pipeline_hash"),
                }
            except Exception as exc:  # noqa: BLE001 - editorial memory remains advisory
                self._append_warning(
                    build_id,
                    "Metadata precedent pipeline could not be resolved; "
                    "progressive semantic precedents were skipped and deterministic "
                    f"editorial memory remained available ({type(exc).__name__}: {exc}).",
                )
                use_progressive = False

        # Bound the complete few-shot packet rather than only each field. This
        # keeps progressive retrieval from trading metadata quality for prompt
        # bloat as the reviewed corpus grows. A pipeline may tighten or expand
        # this computational packet budget; it cannot override schema quotas.
        prompt_budget_kwargs: dict[str, Any] = {
            "field_limits": field_limits or None,
        }
        if (
            metadata_pipeline_plan is not None
            and metadata_pipeline_plan.packet_char_budget is not None
        ):
            prompt_budget_kwargs["token_budget"] = max(
                1,
                int(metadata_pipeline_plan.packet_char_budget)
                // PROMPT_CHARS_PER_TOKEN,
            )
        examples = budget_prompt_examples(examples, **prompt_budget_kwargs)

        retrieval_telemetry: dict[str, Any] = dict(metadata_pipeline_info)
        progressive_index = getattr(self, "_progressive_metadata_index", None)
        if use_progressive and current_record and canonical_exemplars and progressive_index is not None:
            retrieval_fields = sorted({
                str(item.get("field_name") or "")
                for item in canonical_exemplars
                if (
                    str(item.get("field_name") or "") in enabled_fields
                    and int(field_limits.get(str(item.get("field_name") or ""), 1)) > 0
                )
            })
            semantic = (
                progressive_index.retrieve(
                    scope_id=build_id,
                    query_text=current_text,
                    exemplars=canonical_exemplars,
                    fields=retrieval_fields,
                    schema_id=schema_id,
                    schema_version=schema_version,
                    language=str(current_record.get("language") or ""),
                    field_limits=field_limits or None,
                    field_min_similarity=field_min_similarity or None,
                    field_include_corrections={field: field in correction_fields for field in enabled_fields},
                    field_correction_limits=field_correction_limits or None,
                    field_match_fields=field_match_fields or None,
                    current_values=reviewed_values(current_record),
                    value_relation=reviewed_value_relation(
                        self.repo, build_id, metadata_schema, str(current_record.get("language") or "")
                    ),
                    packet_char_budget=(
                        metadata_pipeline_plan.packet_char_budget
                        if metadata_pipeline_plan is not None
                        and metadata_pipeline_plan.packet_char_budget is not None
                        else DEFAULT_PROMPT_TOKEN_BUDGET * PROMPT_CHARS_PER_TOKEN
                    ),
                    fetch_k=(
                        metadata_pipeline_plan.fetch_k
                        if metadata_pipeline_plan is not None
                        and metadata_pipeline_plan.fetch_k is not None
                        else DEFAULT_FETCH_K
                    ),
                    semantic_weight=(
                        metadata_pipeline_plan.semantic_weight
                        if metadata_pipeline_plan is not None
                        else 0.8
                    ),
                    lexical_weight=(
                        metadata_pipeline_plan.lexical_weight
                        if metadata_pipeline_plan is not None
                        else 0.2
                    ),
                    mmr_lambda=(
                        metadata_pipeline_plan.mmr_lambda
                        if metadata_pipeline_plan is not None
                        else DEFAULT_MMR_LAMBDA
                    ),
                    cross_encoder_enabled=(
                        None
                        if metadata_pipeline_plan is not None
                        and metadata_pipeline_plan.rerank_stage_id
                        else False
                    ),
                    cross_encoder_top_k=(
                        metadata_pipeline_plan.cross_encoder_top_k
                        if metadata_pipeline_plan is not None
                        else None
                    ),
                    cross_encoder_model=(
                        metadata_pipeline_plan.cross_encoder_model
                        if metadata_pipeline_plan is not None
                        else None
                    ),
                    cross_encoder_timeout_seconds=(
                        metadata_pipeline_plan.cross_encoder_timeout_seconds
                        if metadata_pipeline_plan is not None
                        else None
                    ),
                    allow_lexical_fallback=bool(
                        metadata_pipeline_plan
                        and metadata_pipeline_plan.lexical_fallback_stage_id
                    ),
                    exclude_record_id=exclude_record_id,
                )
                if retrieval_fields
                else None
            )
            if isinstance(semantic, dict):
                retrieval_telemetry = {
                    **metadata_pipeline_info,
                    **dict(semantic.get("telemetry") or {}),
                }
                if (
                    metadata_pipeline_definition is not None
                    and metadata_pipeline_info.get("pipeline_hash")
                ):
                    try:
                        from .pipelines.metadata_precedent_tracing import (
                            build_metadata_precedent_trace,
                        )
                        from .pipelines.store import pipeline_store

                        trace = build_metadata_precedent_trace(
                            run_id=(
                                f"metadata-precedents-{build_id}-"
                                f"{str(current_record.get('record_id') or 'record')}-"
                                f"{uuid.uuid4().hex[:12]}"
                            ),
                            pipeline=metadata_pipeline_definition,
                            resolved_hash=str(
                                metadata_pipeline_info["pipeline_hash"]
                            ),
                            telemetry=retrieval_telemetry,
                        )
                        pipeline_store.put_run(trace)
                        metadata_pipeline_trace = trace.model_dump(mode="json")
                        retrieval_telemetry["pipeline_run_id"] = trace.run_id
                    except Exception as exc:  # noqa: BLE001 - trace persistence is advisory
                        self._append_warning(
                            build_id,
                            "Metadata precedent retrieval completed, but its pipeline "
                            f"trace could not be persisted ({type(exc).__name__}: {exc}).",
                        )
                if isinstance(semantic.get("examples"), dict):
                    if (
                        semantic.get("ok") is False
                        and metadata_pipeline_plan is not None
                        and metadata_pipeline_plan.lexical_fallback_stage_id is None
                    ):
                        # A custom pipeline may deliberately omit lexical degradation.
                        # In that case do not silently retain the deterministic precedent
                        # packet assembled before semantic retrieval.
                        examples = {}
                    else:
                        # Semantic evidence-bound precedents supersede lexical ordering
                        # only for fields where the vector index found valid current
                        # canonical exemplars. Other fields retain the deterministic fallback.
                        for field, items in semantic["examples"].items():
                            if isinstance(items, list) and items:
                                examples[str(field)] = items
                    examples = budget_prompt_examples(
                        examples,
                        **prompt_budget_kwargs,
                    )
                if retrieval_telemetry.get("fallback_reason"):
                    with self._cache_lock:
                        warned = self._progressive_metadata_warning_builds
                        first_warning = build_id not in warned
                        warned.add(build_id)
                    if first_warning:
                        try:
                            self._append_warning(
                                build_id,
                                "Progressive semantic metadata memory was unavailable; "
                                "enrichment used deterministic editorial-memory fallback "
                                f"({retrieval_telemetry['fallback_reason']}).",
                            )
                        except Exception:
                            with self._cache_lock:
                                warned.discard(build_id)
                            raise

        example_token_estimate = prompt_example_token_estimate(examples)

        # Conventions confirmed in other builds fill gaps only; this build's own
        # reviewers always take precedence over the shared ones.
        for field, convention in (self._global_learning.conventions(exclude_build_id=build_id).items() if use_global else []):
            conventions.setdefault(field, convention)
        memory: dict[str, Any] = {
            "conventions": conventions,
            "examples": examples,
            "example_token_estimate": example_token_estimate,
            "progressive_retrieval": retrieval_telemetry,
            "pipeline_trace": metadata_pipeline_trace,
            # When enrichment scopes precedent work to scheduled metadata families,
            # preserve that scope so its kept cache cannot masquerade as a completed
            # lookup for fields that were deliberately never searched.
            "requested_fields": sorted(field_filter) if field_filter is not None else None,
            "pass_learning": learn_from_pass([row for row in rows if str(row.get("record_id") or "") != exclude_record_id], metadata_schema, registry_for),
        }
        if include_canonical:
            memory["canonical_exemplars"] = {
                str(item["metadata_exemplar_id"]): item for item in canonical_exemplars
            }
        return memory


    def metadata_precedents(
        self, build_id: str, record_id: str, field: str, *, refresh: bool = False
    ) -> dict[str, Any]:
        """Reviewed precedents for one field of one record, as the enrichment prompt saw them.

        Read-only and advisory: this is the selection metadata enrichment used (schema
        retrieval policy, separate correction quota, declared analogy conditions), shown to
        the reviewer beside the source evidence. Nothing here can set a value; the record under
        review is excluded from its own precedents. When the last enrichment kept its retrieval
        on the record, those references are re-verified against the current reviewed records
        (see metadata_precedents_cache) instead of repeating the search; ``refresh`` or a record
        enriched before that was kept searches live. Each precedent may carry
        ``candidate_source_units``: blocks of *this* record ranked against the precedent's
        evidence, for the reviewer to check. They never bind evidence.
        """
        if field not in self._editable_fields(build_id):
            raise ValueError(f"Unsupported review metadata field: {field}")
        record = self.repo.get_record(build_id, record_id)
        cached = None if refresh else cached_field(record, field)
        if cached is not None:
            return self._cached_precedents(build_id, record, {field: cached})[field]
        memory = self._editorial_memory(
            build_id, current_record=record, exclude_record_id=record_id, use_global=False
        )
        items = [dict(item) for item in (memory.get("examples") or {}).get(field) or []]
        retrieval = memory.get("progressive_retrieval") or {}
        try:
            blocks = self._blocks_for(build_id) if items else {}
        except (KeyError, OSError):  # candidates are advisory; precedents still show without them
            blocks = {}
        session = RemapSession.open()
        candidates = rank_candidates(items, record, blocks, embed=self._precedent_embedder(), session=session)
        for item, picks in zip(items, candidates):
            item["candidate_source_units"] = picks
        candidate_pipeline = session.finish() if session is not None else None
        return {
            **({"candidate_pipeline": candidate_pipeline} if candidate_pipeline else {}),
            "field": field,
            "record_id": record_id,
            "source": "live",
            "computed_at": iso_now(),
            "mode": precedent_mode(field, items, retrieval),
            "fallback_reason": str(retrieval.get("fallback_reason") or ""),
            "stale_count": 0,
            "items": items,
        }

    def record_precedents(self, build_id: str, record_id: str) -> dict[str, Any]:
        """Every field's kept precedents for one record, re-verified with one memory rebuild.

        Fields the last enrichment did not keep are absent; the panel loads those one at a
        time through metadata_precedents when a reviewer opens them.
        """
        record = self.repo.get_record(build_id, record_id)
        kept = {
            field: cached
            for field in sorted(self._editable_fields(build_id))
            if (cached := cached_field(record, field)) is not None
        }
        return {"record_id": record_id, "fields": self._cached_precedents(build_id, record, kept, include_candidates=False) if kept else {}}

    def _cached_precedents(
        self,
        build_id: str,
        record: dict[str, Any],
        kept: dict[str, tuple[dict[str, Any], dict[str, Any]]],
        *,
        include_candidates: bool = True,
    ) -> dict[str, dict[str, Any]]:
        """Resolve kept precedent refs and lazily rank this Record's possible evidence.

        Enrichment retains the exact precedent identities/similarities it supplied to the
        model, but source-unit remapping is reviewer assistance rather than enrichment input.
        Running the remap here keeps that potentially embedding-backed work off the build's
        critical path while preserving the same suggestions when the panel is actually used.
        """
        record_id = str(record.get("record_id") or "")
        refs = [
            ref for entry, _cache in kept.values() for ref in entry.get("refs") or []
            if isinstance(ref, dict)
        ]
        # Version 2 references lack Record identity and retain their legacy resolution path.
        selected_ids = (
            list(dict.fromkeys(str(ref["record_id"]) for ref in refs))
            if all(ref.get("record_id") for ref in refs) else None
        )
        memory = self._editorial_memory(
            build_id,
            current_record=record,
            exclude_record_id=record_id,
            use_global=False,
            use_progressive=False,
            include_canonical=True,
            field_filter=set(kept),
            record_ids=selected_ids,
        )
        canonical = memory.get("canonical_exemplars") or {}
        out: dict[str, dict[str, Any]] = {}
        for field, (entry, cache) in kept.items():
            items, stale = resolve_cached_precedents(entry, canonical, record)
            out[field] = {
                "field": field,
                "record_id": record_id,
                "source": "enrichment",
                "computed_at": str(cache.get("computed_at") or ""),
                "mode": str(entry.get("mode") or "none"),
                "fallback_reason": str(cache.get("fallback_reason") or ""),
                "stale_count": stale,
                "items": items,
            }

        fields_with_items = [field for field, payload in out.items() if payload["items"]]
        if not include_candidates:
            for field in fields_with_items:
                for item in out[field]["items"]:
                    item.pop("candidate_source_units", None)
                out[field]["candidates_pending"] = True
            return out
        if not fields_with_items:
            return out
        try:
            build = self.repo.get_build(build_id)
            unit_ids = list(dict.fromkeys(map(str, record.get("source_unit_ids") or record.get("source_block_ids") or [])))
            blocks = {
                str(block["block_id"]): block
                for block in self.repo.load_selected_blocks(str(build.get("asset_id") or ""), unit_ids)
            }
        except (KeyError, OSError):
            blocks = {}
        if not blocks:
            return out
        try:
            session = RemapSession.open()
        except Exception:  # noqa: BLE001 - candidates are advisory; precedents still render
            session = None
        if session is None:
            return out

        try:
            embed = self._precedent_embedder()
            for field in fields_with_items:
                items = out[field]["items"]
                candidates = rank_candidates(
                    items, record, blocks, embed=embed, session=session,
                )
                for item, picks in zip(items, candidates):
                    item["candidate_source_units"] = picks
        finally:
            identity = session.finish()
        if identity is not None:
            for field in fields_with_items:
                out[field]["candidate_pipeline"] = identity
        return out

    def _precedent_embedder(self) -> Any:
        """Embedding callable for ranking source blocks, or None to rank lexically."""
        index: Any = getattr(self, "_progressive_metadata_index", None)
        if index is None or index.disabled_reason or not callable(getattr(index, "embed_texts", None)):
            return None
        return index.embed_texts

    def _editorial_context(self, build_id: str, *, exclude_record_id: str = "") -> dict[str, Any]:
        # Retained as the small conventions-only API used by older internal tests;
        # new enrichment calls use _editorial_memory for retrieved examples too.
        return self._editorial_memory(build_id, None, exclude_record_id=exclude_record_id).get("conventions", {})


    def editorial_memory(self, build_id: str) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        memory = self._editorial_memory(build_id, None)
        return {
            **memory,
            "reset_at": build.get("editorial_memory_reset_at"),
            "convention_count": len(memory.get("conventions") or {}),
            "example_count": sum(len(items) for items in (memory.get("examples") or {}).values() if isinstance(items, list)),
        }


    def reset_editorial_memory(self, build_id: str) -> dict[str, Any]:
        with self._lock:
            build = self.repo.get_build(build_id)
            build["editorial_memory_reset_at"] = iso_now()
            self.repo.save_build(build)
        return self.editorial_memory(build_id)
