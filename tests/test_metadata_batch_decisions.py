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

"""Batch reviewer metadata decisions ("Save all suggestions").

Why: accepting several suggestions at once is a set of reviewer decisions, not a plain
edit. It must resolve open disputes, record adjudication memory with the decision kind,
save as one record revision, report fields held for a blind second opinion instead of
claiming they were saved, and never let a derived-memory failure make a saved decision
look unsaved.
How: reuse the temp-repository helpers from the review-decision tests and stub the
provenance side effects that need a system store.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import corpus_builder as cb  # noqa: E402
from app import corpus_review_actions as review_actions  # noqa: E402
from app.field_assertions import (  # noqa: E402
    create_model_assertion,
    current_assertion_by_name,
    project_record_assertions,
)
from test_review_decisions import install_repo, rec  # noqa: E402


def _manager(tmp_path, record, monkeypatch, remembered: list):
    repo, build = install_repo(tmp_path, [record])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    monkeypatch.setattr(review_actions, "persist_record_decision", lambda **kwargs: None)
    monkeypatch.setattr(manager, "_schedule_metadata_exemplar_projection", lambda build_id: None)
    monkeypatch.setattr(review_actions, "remember_adjudication", lambda **kwargs: remembered.append(kwargs))
    return repo, build, manager


def _disputed_record():
    record = rec("r1", "b1")
    record["metadata_disputes"] = [
        {"field": "position_holder", "values": ["Levinas", "Derrida"]},
        {"field": "discourse_role", "values": ["analysis", "exposition"]},
    ]
    return record


def test_batch_decisions_resolve_disputes_and_record_value_decisions(tmp_path, monkeypatch):
    remembered: list = []
    repo, build, manager = _manager(tmp_path, _disputed_record(), monkeypatch, remembered)

    result = manager.apply_metadata_decisions(
        build["build_id"], "r1", {"position_holder": "Levinas", "discourse_role": "exposition"}, expected_revision=1
    )

    assert result["applied"] is True
    assert sorted(result["changed_fields"]) == ["discourse_role", "position_holder"]
    assert result["deferred_fields"] == [] and result["warnings"] == []
    saved = repo.get_record(build["build_id"], "r1")
    assert saved["record_revision"] == 2, "a batch is one reviewer revision"
    assert saved["position_holder"] == "Levinas"
    resolved = {d["field"]: d for d in saved["metadata_disputes"]}
    assert resolved["position_holder"]["resolution_source"] == "human"
    assert resolved["discourse_role"]["resolved_value"] == "exposition"
    assert {(item["field"], item["decision"]) for item in remembered} == {
        ("position_holder", "value"),
        ("discourse_role", "value"),
    }


def test_batch_can_confirm_model_suggested_absence_and_values_in_one_revision(tmp_path, monkeypatch):
    remembered: list = []
    record = _disputed_record()
    create_model_assertion(
        record,
        "position_holder",
        None,
        outcome="no_supported_value",
        confidence=0.91,
        model="test-model",
    )
    project_record_assertions(record)
    repo, build, manager = _manager(tmp_path, record, monkeypatch, remembered)

    result = manager.apply_metadata_decisions(
        build["build_id"],
        "r1",
        {"position_holder": None, "discourse_role": "exposition"},
        expected_revision=1,
        confirmed_absent_fields=["position_holder"],
    )

    assert result["applied"] is True
    assert sorted(result["changed_fields"]) == ["discourse_role", "position_holder"]
    saved = repo.get_record(build["build_id"], "r1")
    assert saved["record_revision"] == 2
    absence = current_assertion_by_name(saved, "position_holder")
    assert absence is not None
    assert absence.derivation_method == "model"
    assert absence.evaluation_status == "no_supported_value"
    assert absence.authority_status == "human_confirmed"
    assert absence.value_status == "confirmed_absent"
    assert {(item["field"], item["decision"]) for item in remembered} == {
        ("position_holder", "absence"),
        ("discourse_role", "value"),
    }


def test_batch_rejects_unsupported_fields_before_changing_anything(tmp_path, monkeypatch):
    remembered: list = []
    repo, build, manager = _manager(tmp_path, rec("r1", "b1"), monkeypatch, remembered)

    with pytest.raises(ValueError, match="needs_review"):
        manager.apply_metadata_decisions(
            build["build_id"], "r1", {"position_holder": "Levinas", "needs_review": False}, expected_revision=1
        )

    assert repo.get_record(build["build_id"], "r1")["record_revision"] == 1
    assert remembered == []


def test_adjudication_memory_failure_is_reported_not_raised(tmp_path, monkeypatch):
    repo, build, manager = _manager(tmp_path, rec("r1", "b1"), monkeypatch, [])

    def broken(**kwargs):
        raise RuntimeError("store offline")

    monkeypatch.setattr(review_actions, "remember_adjudication", broken)
    result = manager.apply_metadata_decisions(build["build_id"], "r1", {"position_holder": "Levinas"}, expected_revision=1)

    assert repo.get_record(build["build_id"], "r1")["position_holder"] == "Levinas"
    assert result["changed_fields"] == ["position_holder"]
    assert result["warnings"] and "store offline" in result["warnings"][0]


def test_fields_owed_a_second_opinion_are_deferred_not_decided(tmp_path, monkeypatch):
    remembered: list = []
    repo, build, manager = _manager(tmp_path, _disputed_record(), monkeypatch, remembered)
    monkeypatch.setattr(
        review_actions,
        "_second_opinion_owed",
        lambda record, field: {"field": field} if field == "position_holder" else None,
    )
    monkeypatch.setattr(manager, "_log_second_opinion", lambda *args, **kwargs: True)

    result = manager.apply_metadata_decisions(
        build["build_id"], "r1", {"position_holder": "Derrida", "discourse_role": "exposition"}, expected_revision=1
    )

    assert result["changed_fields"] == ["discourse_role"]
    assert result["deferred_fields"] == ["position_holder"]
    saved = repo.get_record(build["build_id"], "r1")
    assert saved.get("position_holder") != "Derrida"
    open_disputes = [d for d in saved["metadata_disputes"] if not d.get("resolved_at")]
    assert [d["field"] for d in open_disputes] == ["position_holder"]
    assert [item["field"] for item in remembered] == ["discourse_role"]


def test_single_decision_shares_the_batch_contract(tmp_path, monkeypatch):
    remembered: list = []
    _repo, build, manager = _manager(tmp_path, _disputed_record(), monkeypatch, remembered)

    result = manager.metadata_decision(build["build_id"], "r1", "position_holder", "Levinas", expected_revision=1)

    assert result["changed_fields"] == ["position_holder"]
    assert result["deferred_fields"] == []
    assert remembered[0]["decision"] == "value"


def test_precedents_are_read_only_and_exclude_the_record_itself(tmp_path, monkeypatch):
    first, second = rec("r1", "b1"), rec("r2", "b2")
    for record in (first, second):
        record["metadata_field_status"]["discourse_role"] = {"status": "human_confirmed", "method": "human"}
    repo, build = install_repo(tmp_path, [first, second])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    manager._progressive_metadata_index = None  # lexical path: no embedding service in tests

    result = manager.metadata_precedents(build["build_id"], "r1", "discourse_role")

    assert result["field"] == "discourse_role"
    assert all(item["record_id"] != "r1" for item in result["items"])
    assert repo.get_record(build["build_id"], "r1")["record_revision"] == 1
    with pytest.raises(ValueError):
        manager.metadata_precedents(build["build_id"], "r1", "needs_review_not_a_field")


def _write_block_text(repo, text: str) -> None:
    path = repo.asset_blocks_path("a")
    block = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    path.write_text(json.dumps({**block, "text": text}) + "\n", encoding="utf-8")


def test_accepting_an_unbound_value_runs_evidence_recovery_without_an_llm(tmp_path, monkeypatch):
    from app.pipelines import evidence_recovery as evidence_pipeline

    remembered: list = []
    repo, build, manager = _manager(tmp_path, rec("r1", "b1"), monkeypatch, remembered)
    _write_block_text(repo, "Here Levinas argues that the face precedes ontology.")
    calls: list = []
    real_recovery = evidence_pipeline.execute_evidence_recovery

    def spy(**kwargs):
        calls.append(kwargs)
        return real_recovery(**kwargs)

    monkeypatch.setattr(evidence_pipeline, "execute_evidence_recovery", spy)

    result = manager.apply_metadata_decisions(build["build_id"], "r1", {"position_holder": "Levinas"}, expected_revision=1)

    assert [call["field"] for call in calls] == ["position_holder"]
    assert calls[0]["llm_choice"] is None, "accepting a value must never spend a model call"
    entry = result["record"]["metadata_evidence"]["position_holder"]
    assert entry["block_ids"] == ["b1"]
    assert entry["pipeline"]["feature"] == "evidence_recovery"
    # Advisory, exactly as during enrichment: never counted as reviewed evidence.
    assert entry["backfilled"] is True and entry["confidence"] is None
    saved = repo.get_record(build["build_id"], "r1")
    assert saved["metadata_evidence"]["position_holder"]["block_ids"] == ["b1"]
    assert saved["position_holder"] == "Levinas"


def test_accepting_a_value_keeps_evidence_the_reviewer_already_bound(tmp_path, monkeypatch):
    from app.pipelines import evidence_recovery as evidence_pipeline

    remembered: list = []
    repo, build, manager = _manager(tmp_path, rec("r1", "b1"), monkeypatch, remembered)
    monkeypatch.setattr(
        evidence_pipeline, "execute_evidence_recovery",
        lambda **k: pytest.fail("bound evidence must not be re-adjudicated"),
    )

    result = manager.metadata_decision(
        build["build_id"], "r1", "position_holder", "Levinas", expected_revision=1,
        evidence_source="reviewer_knowledge", evidence_note="Known from the preface.",
    )

    entry = result["record"]["metadata_evidence"]["position_holder"]
    assert entry["source_kind"] == "reviewer_knowledge" and not entry.get("backfilled")
