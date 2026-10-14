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

"""Canonical, administrator-only construction of the experimental shadow runner.

This is a server integration boundary, never a public assignment or mutation API.
Precedent selections are references; values and evidence are rederived from current
canonical Records under the live reviewer's scope before any provider sees them.
"""

import hashlib
from collections.abc import Callable, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .. import metadata_adjudication_cache
from ..celf_queries.access import AccessContext, reviewer_scope
from ..corpus_llm_helpers import _llm_config, _stage_limits, _stage_timeouts
from ..corpus_reviewer_helpers import _second_opinion_owed
from ..metadata_exemplar_projection import derive_record_metadata_exemplars
from ..metadata_schema import MetadataSchema, default_schema
from ..semantic_identity import canonical_json
from ..structured_completion import StructuredAttemptContext
from .metadata_candidate_collection import (
    MAX_PER_FIELD,
    CandidateCollector,
    MetadataCandidate,
)
from .metadata_candidate_routing import FieldEvaluation, InferenceRequest
from .metadata_candidate_session import CandidateRoutingSession, RoutingSessionResult


@dataclass(frozen=True)
class PrecedentRecordRef:
    build_id: str
    record_id: str


def run_canonical_candidate_shadow(
    repo: Any,
    *,
    build_id: str,
    record_id: str,
    fields: Sequence[str],
    read_access: Callable[[], AccessContext],
    request_factory: Callable[
        [InferenceRequest], Callable[[StructuredAttemptContext], str]
    ],
    precedent_refs: Sequence[PrecedentRecordRef] = (),
    read_provider_configuration: Callable[[], dict[str, Any]] | None = None,
) -> RoutingSessionResult:
    """Authorize every canonical read and provider turn; return advisory review only.

    read_access must resolve the *current* authenticated server session, including
    revocation/role changes. request_factory must use the existing provider's
    capacity, health and cancellation transport. Neither callback is client data.
    Reference selections are bounded and rehydrated without consulting a derived
    vector index. No canonical Record, review decision or assignment is written.
    """
    requested = tuple(dict.fromkeys(fields))
    refs = tuple(dict.fromkeys(precedent_refs))
    if not requested or len(refs) > MAX_PER_FIELD:
        raise ValueError(
            "Shadow routing requires fields and bounded precedent references."
        )
    if any(not ref.build_id or not ref.record_id for ref in refs):
        raise ValueError("Shadow routing requires complete precedent references.")

    def load() -> CandidateCollector:
        # Authorization precedes even schema, memory or source reads. Scope is
        # resolved afresh, not inherited from a background worker's contextvar.
        access = read_access()
        access.require_admin()
        if not access.reviewer:
            raise ValueError(
                "Shadow routing requires an authenticated reviewer identity."
            )
        with reviewer_scope(access):
            build = deepcopy(repo.get_build(build_id))
            row = deepcopy(repo.get_record(build_id, record_id))
            if str(row.get("record_id") or "") != record_id:
                raise ValueError("Canonical Record identity mismatch.")
            raw_schema = build.get("schema")
            schema = (
                MetadataSchema.model_validate(raw_schema)
                if raw_schema
                else default_schema()
            )
            if set(requested) - set(schema.field_names()):
                raise ValueError("Shadow routing requested unknown schema fields.")
            blind = tuple(
                name
                for name in requested
                if _second_opinion_owed(row, name)
                or (row.get("metadata_field_status") or {}).get(name, {}).get("blind")
            )
            examples: dict[str, list[dict[str, Any]]] = {name: [] for name in requested}
            by_build: dict[str, list[str]] = {}
            for ref in refs:
                by_build.setdefault(ref.build_id, []).append(ref.record_id)
            for origin_build, record_ids in by_build.items():
                for example in derive_record_metadata_exemplars(
                    repo, origin_build, record_ids
                ):
                    name = example.get("field_name")
                    if name in examples and name not in blind:
                        examples[name].append(deepcopy(example))
            context = {
                "reviewer_scope": access.reviewer,
                "principal": {
                    "username": access.username,
                    "role": access.role,
                    "user_id": access.user_id,
                },
                "build_id": build_id,
                "blind_fields": list(blind),
                "second_opinion": deepcopy(row.get("second_opinion")),
                "configuration_hash": hashlib.sha256(
                    canonical_json(
                        {
                            "request": build.get("request"),
                            "active_provider": read_provider_configuration()
                            if read_provider_configuration
                            else None,
                            "editorial_memory_reset_at": build.get(
                                "editorial_memory_reset_at"
                            ),
                        }
                    ).encode("utf-8")
                ).hexdigest(),
            }

            def exact_lookup(**kwargs: Any) -> dict[str, Any] | None:
                return (
                    None
                    if kwargs["field"] in blind
                    else metadata_adjudication_cache.suggestions(**kwargs)
                )

            return CandidateCollector(
                row,
                schema,
                fields=requested,
                context=context,
                exemplars=examples,
                exact_lookup=exact_lookup,
            )

    owner = load()
    # Collection snapshots already validated/scoped all four origins. Live
    # binding checks rehydrate those dependencies and reject any intervening edit.
    eligible = {
        candidate.candidate_id: candidate
        for operation in (
            owner.collect_nlp,
            owner.collect_document_intelligence,
            owner.collect_exact_memory,
            owner.collect_reviewed_precedents,
        )
        for candidate in operation().candidates
    }

    def visible(candidate: MetadataCandidate) -> bool:
        return eligible.get(candidate.candidate_id) == candidate

    return CandidateRoutingSession.with_structured_provider(
        owner,
        read_current=lambda: load().binding,
        candidate_visible=visible,
        request_factory=request_factory,
        blind_fields=owner.context["blind_fields"],
    ).run()


def run_build_candidate_shadow(
    manager: Any,
    *,
    build_id: str,
    record_id: str,
    fields: Sequence[str],
    read_access: Callable[[], AccessContext],
    precedent_refs: Sequence[PrecedentRecordRef] = (),
) -> RoutingSessionResult:
    """Bind live build provider settings and reuse its admitted single-turn transport.

    This explicit server call remains outside historical production assignments.
    The manager owns capacity, health, cancellation and provider metrics; the
    candidate adapter owns structured retries and current-evidence validation.
    """

    def request() -> dict[str, Any]:
        build = manager.repo.get_build(build_id)
        return deepcopy(
            manager._latest_runtime_request(build_id, dict(build.get("request") or {}))
        )

    def configuration() -> dict[str, Any]:
        active = request()
        provider, model, endpoint, credential, generation = _llm_config(active)
        # Credentials affect the binding but only its digest survives the load.
        return {
            "provider": provider,
            "model": model,
            "endpoint": endpoint,
            "credential": credential,
            "generation": generation.model_dump(mode="json") if generation else None,
            "profile": active.get("provider_profile_id"),
            "limits": _stage_limits(active),
            "timeouts": _stage_timeouts(active),
            "priority": active.get("_capacity_priority"),
        }

    def factory(_task: InferenceRequest) -> Callable[[StructuredAttemptContext], str]:
        active = request()

        def attempt(context: StructuredAttemptContext) -> str:
            invoke = manager._structured_metadata_invoker(
                active,
                context.prompt,
                FieldEvaluation,
                context.max_tokens,
                "metadata_candidate_shadow",
                build_id,
            )
            answer = invoke("primary", 1, False)
            return FieldEvaluation.model_validate(answer).model_dump_json()

        return attempt

    return run_canonical_candidate_shadow(
        manager.repo,
        build_id=build_id,
        record_id=record_id,
        fields=fields,
        read_access=read_access,
        request_factory=factory,
        precedent_refs=precedent_refs,
        read_provider_configuration=configuration,
    )
