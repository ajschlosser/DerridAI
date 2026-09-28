# Copyright 2026 Aaron John Schlosser, PhD.
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
from .metadata_exemplars import (
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

        def _append_warning(self, build_id: str, message: str) -> None: ...
        def _blocks_for(self, build_id: str) -> dict[str, dict[str, Any]]: ...
        def _editable_fields(self, build_id: str) -> set[str]: ...


    def _editorial_memory(
        self,
        build_id: str,
        current_record: dict[str, Any] | None = None,
        *,
        exclude_record_id: str = "",
        use_global: bool = True,
        use_progressive: bool = True,
        include_canonical: bool = False,
    ) -> dict[str, Any]:
        """Build advisory context from human decisions and the last enrichment pass.

        Only human-confirmed/overridden fields are eligible as conventions and few-shot
        examples. Repeated values become advisory conventions after two confirmations.
        ``pass_learning`` also includes last-pass LLM inferences on two or more records
        (working conventions, not confirmed) so a later pass can start before every
        record has been reviewed. Nothing here is copied as truth.

        ``include_canonical`` adds ``canonical_exemplars`` (exemplar ID -> exemplar) for callers
        that must re-verify stored precedent references; it is never part of an API response.
        """
        try:
            rows = self.repo.load_records(build_id)
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
                blocks_by_id = {
                    str(block.get("block_id") or ""): block
                    for block in self.repo.load_blocks(asset_id)
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
        # Bound the complete few-shot packet rather than only each field.  This
        # keeps progressive retrieval from trading metadata quality for prompt
        # bloat as the reviewed corpus grows.
        examples = budget_prompt_examples(examples, field_limits=field_limits or None)

        retrieval_telemetry: dict[str, Any] = {}
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
                    exclude_record_id=exclude_record_id,
                )
                if retrieval_fields
                else None
            )
            if isinstance(semantic, dict):
                retrieval_telemetry = dict(semantic.get("telemetry") or {})
                if isinstance(semantic.get("examples"), dict):
                    # Semantic evidence-bound precedents supersede lexical ordering
                    # only for fields where the vector index found valid current
                    # canonical exemplars. Other fields retain the deterministic fallback.
                    for field, items in semantic["examples"].items():
                        if isinstance(items, list) and items:
                            examples[str(field)] = items
                    examples = budget_prompt_examples(
                        examples,
                        field_limits=field_limits or None,
                    )
                if retrieval_telemetry.get("fallback_reason"):
                    warned: set[str] = getattr(
                        self,
                        "_progressive_metadata_warning_builds",
                        set(),
                    )
                    if build_id not in warned:
                        self._append_warning(
                            build_id,
                            "Progressive semantic metadata memory was unavailable; "
                            "enrichment used deterministic editorial-memory fallback "
                            f"({retrieval_telemetry['fallback_reason']}).",
                        )
                        warned.add(build_id)
                        self._progressive_metadata_warning_builds = warned

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
            "pass_learning": learn_from_pass([row for row in rows if str(row.get("record_id") or "") != exclude_record_id]),
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
        candidates = rank_candidates(items, record, blocks, embed=self._precedent_embedder())
        for item, picks in zip(items, candidates):
            item["candidate_source_units"] = picks
        return {
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
        return {"record_id": record_id, "fields": self._cached_precedents(build_id, record, kept) if kept else {}}

    def _cached_precedents(
        self,
        build_id: str,
        record: dict[str, Any],
        kept: dict[str, tuple[dict[str, Any], dict[str, Any]]],
    ) -> dict[str, dict[str, Any]]:
        record_id = str(record.get("record_id") or "")
        memory = self._editorial_memory(
            build_id,
            current_record=record,
            exclude_record_id=record_id,
            use_global=False,
            use_progressive=False,
            include_canonical=True,
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
