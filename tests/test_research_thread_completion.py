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

"""Threaded pipeline configuration and legacy migration boundaries."""
import sys
import types

import pytest

sys.modules.setdefault("chromadb", types.SimpleNamespace())
from app import research_threads
from app.chroma_store import ChromaStore
from app.models import RAGRunRequest
from app.pipelines.defaults import built_in_pipeline
from app.pipelines.overrides import resolve_pipeline_config
from app.pipelines.registry import strategy_registry
from app.pipelines.research import compile_research_pipeline
from app.research_thread_store import ResearchThreadStore, ThreadNotFound
from app.research_turn_results import saved_turn_result
from app.route_policy import non_admin_route_allowed


def test_threaded_pipeline_versions_ports_and_effective_budget():
    old = built_in_pipeline("research.current", 1)
    new = built_in_pipeline("research.current", 2)
    assert old.entry_stage_ids == ["query"]
    assert compile_research_pipeline(old).thread_context_stage_id is None
    assert compile_research_pipeline(new).thread_context_stage_id == "thread_context"
    body = RAGRunRequest(prompt="What about Levinas?", run_pipeline_overrides={
        "pipeline_id": new.pipeline_id, "pipeline_version": 2,
        "stages": {"thread_context": {"max_turns": 1, "include_answers": False}},
    })
    effective = resolve_pipeline_config(new, run_overrides=body.run_pipeline_overrides).effective
    config = compile_research_pipeline(effective).stage_configs["thread_context"]
    assert config["max_turns"] == 1 and config["include_answers"] is False
    assert any(port.data_type == "thread_context" for port in strategy_registry.require("context.research_thread").outputs)
    assert any(port.data_type == "thread_context" for port in strategy_registry.require("query.research_contextualize").inputs)
    changed = new.model_copy(deep=True)
    changed.stages[0].next = ["dense"]
    with pytest.raises(ValueError):
        compile_research_pipeline(changed)


def test_metadata_scan_is_bounded_owner_filtered_and_does_not_decode_evidence():
    calls = []
    class Collection:
        def get(self, **kwargs):
            calls.append(kwargs)
            return {"ids": ["r1", "r2", "r3"], "metadatas": [
                {"record_id": "r1", "question": "Q", "owner": "alice", "response_id": "run1", "evidence": "invalid JSON"},
                {"record_id": "r2", "question": "Other", "owner": "bob", "response_id": "run2"},
                {"record_id": "r3", "question": "New", "owner": "alice", "response_id": "run3", "research_thread": "__json__:{}"},
            ]}
    cache = ChromaStore.__new__(ChromaStore)
    cache._client = types.SimpleNamespace(get_collection=lambda **_: Collection())
    page = cache.get_legacy_response_summaries("alice", offset=400)
    assert calls == [{"where": {"owner": "alice"}, "include": ["metadatas"], "limit": 200, "offset": 400}]
    assert page["scanned"] == 3 and [item["record_id"] for item in page["records"]] == ["r1"]
    assert "evidence" not in page["records"][0]


def test_legacy_import_recovery_idempotence_tombstone_and_authorization(tmp_path, monkeypatch):
    store = ResearchThreadStore(tmp_path / "system.sqlite3")
    monkeypatch.setattr(research_threads, "thread_store", lambda: store)
    monkeypatch.setattr(research_threads, "notify_changed", lambda: None)
    record = {"record_id": "legacy", "response_id": "run1", "owner": "alice", "question": "Old question",
              "text": "Old answer", "instructions": "Preserve negation", "evidence": []}
    cache = types.SimpleNamespace(
        get_legacy_response_summaries=lambda owner, **_: {"records": [{"record_id": "legacy", "run_id": "run1", "question": "Old question", "instructions": record["instructions"]}], "scanned": 1},
        get_record=lambda *_: record,
    )
    assert research_threads.import_legacy_responses("alice", cache)["created"] == 1
    assert research_threads.import_legacy_responses("alice", cache)["created"] == 0
    thread = store.get_thread(store.list_threads("alice")[0]["thread_id"], "alice")
    turn = thread["turns"][0]
    assert turn["user_instructions"] == record["instructions"]
    assert saved_turn_result(turn, "alice", cache)["result"]["answer"] == "Old answer"
    record["owner"] = "bob"
    with pytest.raises(ThreadNotFound):
        saved_turn_result(turn, "alice", cache)
    record["owner"] = "alice"
    record["question"] = "Different question"
    with pytest.raises(ThreadNotFound):
        saved_turn_result(turn, "alice", cache)
    store.delete_thread(thread["thread_id"], "alice")
    assert research_threads.import_legacy_responses("alice", cache)["created"] == 0
    assert record["text"] == "Old answer"
    assert non_admin_route_allowed("researcher", "/api/research/threads/import-legacy", "POST")
