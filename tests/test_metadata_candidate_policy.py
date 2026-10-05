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

"""Canonical access, rehydration and retry gates for advisory shadow routing."""

from copy import deepcopy

import pytest
from app.celf_queries.access import AccessContext
from app.metadata_schema import default_schema
from app.pipelines.graph_execution import GraphExecutionError
from app.pipelines.metadata_candidate_policy import (
    PrecedentRecordRef,
    run_canonical_candidate_shadow,
)
from app.pipelines.metadata_candidate_session import CandidateRoutingSession
from app.reviewer_context import current_reviewer
from test_metadata_candidate_collection import collector, record
from test_metadata_candidate_routing import unsupported


class Repo:
    def __init__(self):
        self.row = record()
        self.build = {
            "schema": default_schema().model_dump(mode="json"),
            "request": {"model": "test"},
        }
        self.reads = []

    def get_build(self, build_id):
        self.reads.append(("build", current_reviewer.get()))
        return deepcopy(self.build)

    def get_record(self, build_id, record_id):
        self.reads.append(("record", current_reviewer.get()))
        return deepcopy(self.row)


def run(repo, monkeypatch, *, access=None, factory=None, fields=("stance",), refs=()):
    monkeypatch.setattr(
        "app.pipelines.metadata_candidate_policy.metadata_adjudication_cache.suggestions",
        lambda **kw: None,
    )
    return run_canonical_candidate_shadow(
        repo,
        build_id="build-1",
        record_id="r1",
        fields=fields,
        read_access=access or (lambda: AccessContext("admin", "admin", 2)),
        request_factory=factory
        or (lambda task: lambda ctx: unsupported(task).model_dump_json()),
        precedent_refs=refs,
    )


@pytest.mark.parametrize(
    "access",
    [AccessContext("reader", "researcher", 2), AccessContext("admin", "admin")],
)
def test_denial_precedes_all_source_and_memory_reads(monkeypatch, access):
    repo = Repo()
    with pytest.raises(Exception):
        run(repo, monkeypatch, access=lambda: access)
    assert not repo.reads


def test_canonical_shadow_scopes_reads_and_preserves_authority(monkeypatch):
    repo = Repo()
    before = deepcopy(repo.row)
    token = current_reviewer.set("unrelated-worker")
    try:
        result = run(repo, monkeypatch)
        assert current_reviewer.get() == "unrelated-worker"
    finally:
        current_reviewer.reset(token)
    assert set(scope for _, scope in repo.reads) == {"user-2"}
    assert repo.row == before
    assert result.reviewer_packet.proposals[0].support == "unresolved"
    assert result.reviewer_packet.proposals[0].proposal.authority == "advisory"
    assert result.reviewer_packet.proposals[0].proposal.needs_review


def test_blind_policy_is_derived_before_memory_reads(monkeypatch):
    repo = Repo()
    repo.row["second_opinion"] = {
        "persons": {"first_reviewer": "user-1", "done": False}
    }
    calls = []
    monkeypatch.setattr(
        "app.pipelines.metadata_candidate_policy.metadata_adjudication_cache.suggestions",
        lambda **kw: calls.append(kw) or None,
    )
    result = run_canonical_candidate_shadow(
        repo,
        build_id="build-1",
        record_id="r1",
        fields=["persons"],
        read_access=lambda: AccessContext("admin", "admin", 2),
        request_factory=lambda task: pytest.fail(
            "Exact mentions require no model call"
        ),
    )
    assert not calls
    assert not result.reviewer_packet.proposals
    assert result.reviewer_packet.withheld_fields == ("persons",)


@pytest.mark.parametrize(
    "change",
    ["text", "revision", "ownership", "configuration", "reviewer", "role", "memory"],
)
def test_live_dependency_changes_discard_provider_output(monkeypatch, change):
    repo = Repo()
    access = [AccessContext("admin", "admin", 2)]
    memory = [None]
    monkeypatch.setattr(
        "app.pipelines.metadata_candidate_policy.metadata_adjudication_cache.suggestions",
        lambda **kw: deepcopy(memory[0]),
    )
    calls = []

    def factory(task):
        def attempt(ctx):
            calls.append(ctx.attempt)
            if change == "text":
                repo.row["text"] += " changed"
            elif change == "revision":
                repo.row["record_revision"] += 1
            elif change == "ownership":
                repo.row["human_touched_fields"] = ["stance"]
            elif change == "configuration":
                repo.build["request"]["model"] = "changed"
            elif change == "reviewer":
                access[0] = AccessContext("other", "admin", 3)
            elif change == "role":
                access[0] = AccessContext("admin", "researcher", 2)
            else:
                memory[0] = {"latest_value": "PRIVATE_CHANGED_MEMORY"}
            return unsupported(task).model_dump_json()

        return attempt

    with pytest.raises(GraphExecutionError) as error:
        run_canonical_candidate_shadow(
            repo,
            build_id="build-1",
            record_id="r1",
            fields=["stance"],
            read_access=lambda: access[0],
            request_factory=factory,
        )
    assert calls == [1]
    assert not error.value.result.terminal_outputs
    assert "PRIVATE_CHANGED_MEMORY" not in str(error.value)


def test_reference_values_are_rehydrated_and_hidden_origins_removed(monkeypatch):
    repo = Repo()
    canonical = []
    reads = []

    def derive(source, build_id, ids):
        reads.append((build_id, ids, current_reviewer.get()))
        return deepcopy(canonical)

    monkeypatch.setattr(
        "app.pipelines.metadata_candidate_policy.derive_record_metadata_exemplars",
        derive,
    )
    result = run(
        repo,
        monkeypatch,
        fields=["persons"],
        refs=[PrecedentRecordRef("origin-build", "r2")],
    )
    assert reads and all(item == ("origin-build", ["r2"], "user-2") for item in reads)
    assert result.reviewer_packet.proposals[0].support == "mention_only"


def test_canonical_precedent_removal_prevents_stale_delivery(monkeypatch):
    from test_metadata_candidate_collection import exemplar

    repo = Repo()
    examples = [exemplar(default_schema()) | {"field_name": "persons"}]
    monkeypatch.setattr(
        "app.pipelines.metadata_candidate_policy.derive_record_metadata_exemplars",
        lambda *args: deepcopy(examples),
    )

    def factory(task):
        def attempt(ctx):
            examples.clear()
            return unsupported(task).model_dump_json()

        return attempt

    with pytest.raises(GraphExecutionError) as error:
        run(
            repo,
            monkeypatch,
            fields=["persons"],
            refs=[PrecedentRecordRef("origin", "r2")],
            factory=factory,
        )
    assert not error.value.result.terminal_outputs


def test_invalid_scope_stops_before_memory_or_provider(monkeypatch):
    with pytest.raises(ValueError, match="unknown schema fields"):
        run(Repo(), monkeypatch, fields=["unknown"])
    with pytest.raises(ValueError, match="bounded"):
        run(
            Repo(),
            monkeypatch,
            refs=[PrecedentRecordRef("b", str(i)) for i in range(33)],
        )


def test_shared_structured_retry_keeps_attempt_prompt_and_budget():
    owner = collector(fields=["stance"])
    attempts = []

    def factory(task):
        def attempt(ctx):
            attempts.append(ctx)
            return "{}" if ctx.attempt == 1 else unsupported(task).model_dump_json()

        return attempt

    result = CandidateRoutingSession.with_structured_provider(
        owner,
        read_current=lambda: owner.binding,
        candidate_visible=lambda c: True,
        request_factory=factory,
    ).run()
    assert [ctx.attempt for ctx in attempts] == [1, 2]
    assert "SCHEMA CORRECTION" in attempts[1].prompt
    assert attempts[1].max_tokens > attempts[0].max_tokens
    assert result.reviewer_packet.proposals[0].support == "unresolved"


def test_structured_cancellation_never_retries_or_delivers():
    owner = collector(fields=["stance"])
    calls = []

    def factory(task):
        def attempt(ctx):
            calls.append(ctx.attempt)
            raise InterruptedError("PRIVATE_CANCEL")

        return attempt

    with pytest.raises(InterruptedError):
        CandidateRoutingSession.with_structured_provider(
            owner,
            read_current=lambda: owner.binding,
            candidate_visible=lambda c: True,
            request_factory=factory,
        ).run()
    assert calls == [1]


@pytest.mark.parametrize("sealed", [False, True])
def test_real_repository_rehydrates_reviewed_precedents_without_mutation(
    tmp_path, monkeypatch, sealed
):
    import json
    import sqlite3

    from test_review_queues import install_repo

    current = record() | {"source_block_ids": ["b1"]}
    origin = record() | {
        "record_id": "r2",
        "record_revision": 4,
        "source_block_ids": ["b2"],
        "source_spans": [{"block_id": "b2", "page": 1}],
        "persons": ["Rousseau"],
        "metadata_reviewed_at": "2026-10-04T00:00:00Z",
        "metadata_field_status": {
            "persons": {"status": "human_confirmed", "method": "human"}
        },
        "metadata_evidence": {
            "persons": {"block_ids": ["b2"], "confidence": 1.0, "reviewed_by": "human"}
        },
    }
    from app.field_assertions import create_human_assertion

    create_human_assertion(
        origin,
        "persons",
        ["Rousseau"],
        schema=default_schema(),
        actor="user-1",
        evidence=[{"block_ids": ["b2"], "reviewed_by": "human"}],
    )
    if sealed:
        origin["second_opinion"] = {
            "persons": {"first_reviewer": "user-1", "done": False}
        }
    repo, build = install_repo(tmp_path, [current, origin])
    build["schema"] = default_schema().model_dump(mode="json")
    repo.save_build(build)
    repo.asset_blocks_path("a").write_text(
        "".join(
            json.dumps(
                {
                    "block_id": block,
                    "page": 1,
                    "text": current["text"],
                    "type": "paragraph",
                    "extraction_method": "native",
                }
            )
            + "\n"
            for block in ("b1", "b2")
        ),
        encoding="utf-8",
    )

    def stored():
        with sqlite3.connect(
            repo.build_records_db_path(build["build_id"])
        ) as connection:
            return connection.execute(
                "SELECT payload FROM corpus_records ORDER BY ordinal"
            ).fetchall()

    before = stored()
    calls = []
    monkeypatch.setattr(
        "app.pipelines.metadata_candidate_policy.metadata_adjudication_cache.suggestions",
        lambda **kw: None,
    )

    def factory(task):
        calls.append(
            (task.route, tuple(candidate.origin for candidate in task.candidates))
        )
        return lambda ctx: unsupported(task).model_dump_json()

    result = run_canonical_candidate_shadow(
        repo,
        build_id=build["build_id"],
        record_id="r1",
        fields=["persons"],
        read_access=lambda: AccessContext("admin", "admin", 2),
        request_factory=factory,
        precedent_refs=[PrecedentRecordRef(build["build_id"], "r2")],
    )
    assert stored() == before
    if sealed:
        assert not calls
        assert result.reviewer_packet.proposals[0].support == "mention_only"
    else:
        assert calls == [("VERIFY", ("nlp", "reviewed_precedent")), ("INFER", ())]
        assert result.reviewer_packet.proposals[0].support == "unresolved"


@pytest.mark.parametrize("switch", [False, True])
def test_build_adapter_reuses_one_turn_transport_and_rejects_live_provider_switch(
    monkeypatch, switch
):
    from app.pipelines.metadata_candidate_policy import run_build_candidate_shadow

    class Manager:
        def __init__(self):
            self.repo = Repo()
            self.active = {
                "provider": "ollama",
                "model": "existing",
                "api_key": "PRIVATE_KEY",
            }
            self.calls = []

        def _latest_runtime_request(self, build_id, fallback):
            return deepcopy(self.active)

        def _structured_metadata_invoker(
            self, request, prompt, response_model, max_tokens, schema_name, build_id
        ):
            def invoke(role, attempts, escalated):
                self.calls.append(
                    (
                        deepcopy(request),
                        prompt,
                        {
                            "attempts": attempts,
                            "roles": (role,),
                            "escalated": escalated,
                            "build_id": build_id,
                            "max_tokens": max_tokens,
                        },
                    )
                )
                if switch:
                    self.active["model"] = "changed"
                return {
                    "field_name": "stance",
                    "outcome": "uncertain",
                    "confidence": None,
                    "reason": "Unresolved",
                }

            return invoke

    manager = Manager()
    monkeypatch.setattr(
        "app.pipelines.metadata_candidate_policy.metadata_adjudication_cache.suggestions",
        lambda **kw: None,
    )

    def invoke():
        return run_build_candidate_shadow(
            manager,
            build_id="b1",
            record_id="r1",
            fields=["stance"],
            read_access=lambda: AccessContext("admin", "admin", 2),
        )

    if switch:
        with pytest.raises(GraphExecutionError) as error:
            invoke()
        assert not error.value.result.terminal_outputs
    else:
        result = invoke()
        assert result.reviewer_packet.proposals[0].support == "unresolved"
        assert "PRIVATE_KEY" not in result.reviewer_packet.model_dump_json()
        assert "PRIVATE_KEY" not in str([stage.model_dump() for stage in result.stages])
    assert len(manager.calls) == 1
    active, prompt, kwargs = manager.calls[0]
    assert active["model"] == "existing"
    assert kwargs["attempts"] == 1 and kwargs["roles"] == ("primary",)
    assert kwargs["build_id"] == "b1" and kwargs["max_tokens"] == 4096
    assert kwargs["escalated"] is False
    assert "metadata-candidate-routing-v1" in prompt
