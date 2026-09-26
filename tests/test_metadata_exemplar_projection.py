# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from app import corpus_builder as cb
from app import metadata_exemplar_projection as projection
from app.field_assertions import (
    confirm_assertion,
    create_model_assertion,
    project_record_assertions,
)


class FakeRepo:
    def __init__(self):
        self.build = {
            "build_id": "build-1",
            "asset_id": "asset-1",
            "source_document_id": "asset-1",
            "schema": {
                "id": "schema-1",
                "schema_version": "1.0.0",
                "fields": [{"name": "position_holder", "field_id": "schema-1.position_holder"}],
            },
        }
        self.records = [
            {
                "record_id": "r1",
                "record_revision": 3,
                "source_document_id": "asset-1",
                "source_block_ids": ["b1", "b2", "b3"],
                "source_spans": [{"block_id": "b2", "page": 12}],
                "position_holder": "Levinas",
                "metadata_reviewed_at": "2026-09-24T00:00:00Z",
                "metadata_field_status": {
                    "position_holder": {
                        "status": "human_confirmed",
                        "method": "human_review_of_llm_proposal",
                    }
                },
                "metadata_evidence": {
                    "position_holder": {
                        "block_ids": ["b2"],
                        "confidence": 1.0,
                        "reason": "Explicit attribution.",
                    }
                },
            }
        ]
        self.blocks = [
            {"block_id": "b1", "page": 12, "text": "Context before."},
            {"block_id": "b2", "page": 12, "text": "For Levinas, responsibility precedes freedom."},
            {"block_id": "b3", "page": 12, "text": "Context after."},
        ]

    def get_build(self, build_id):
        assert build_id == "build-1"
        return self.build

    def load_records(self, build_id):
        assert build_id == "build-1"
        return self.records

    def load_blocks(self, asset_id):
        assert asset_id == "asset-1"
        return self.blocks

    def list_builds(self, *, offset=0, limit=1000):
        return {"items": [self.build]}


class FakeIndex:
    def __init__(self):
        self.calls = []

    def rebuild_scope(self, scope_id, exemplars):
        self.calls.append((scope_id, exemplars))
        return {"desired": len(exemplars), "upserted": len(exemplars), "deleted": 0}


def test_derivation_embeds_evidence_context_not_whole_record(monkeypatch):
    repo = FakeRepo()
    monkeypatch.setattr(projection.experiment, "is_gold", lambda record_id: False)
    monkeypatch.setattr(projection, "_second_opinion_owed", lambda row, field: False)

    rows = projection.derive_build_metadata_exemplars(repo, "build-1")

    assert len(rows) == 1
    exemplar = rows[0]
    assert exemplar["field_name"] == "position_holder"
    assert exemplar["field_value"] == "Levinas"
    assert exemplar["evidence_ref"]["block_ids"] == ["b2"]
    assert exemplar["evidence_text"] == "For Levinas, responsibility precedes freedom."
    assert exemplar["context_text"] == (
        "Context before.\n\n"
        "For Levinas, responsibility precedes freedom.\n\n"
        "Context after."
    )




def test_confirmed_model_assertion_remains_eligible_without_rewriting_method(monkeypatch):
    repo = FakeRepo()
    record = repo.records[0]
    record.pop("metadata_field_status", None)
    record.pop("metadata_evidence", None)
    record.pop("position_holder", None)
    model = create_model_assertion(
        record,
        "position_holder",
        "Levinas",
        confidence=0.87,
        method="llm",
        evidence=[{
            "block_ids": ["b2"],
            "confidence": 0.87,
            "reason": "Explicit attribution.",
        }],
    )
    confirmed = confirm_assertion(record, model, actor="reviewer")
    project_record_assertions(record)
    assert confirmed.method == "llm"
    assert confirmed.derivation_method == "model"
    assert confirmed.authority_status == "human_confirmed"

    monkeypatch.setattr(projection.experiment, "is_gold", lambda record_id: False)
    monkeypatch.setattr(projection, "_second_opinion_owed", lambda row, field: False)
    rows = projection.derive_build_metadata_exemplars(repo, "build-1")

    assert len(rows) == 1
    assert rows[0]["field_value"] == "Levinas"
    assert rows[0]["evidence_ref"]["block_ids"] == ["b2"]


def test_derivation_includes_evidence_bound_confirmed_absence(monkeypatch):
    repo = FakeRepo()
    repo.records[0]["position_holder"] = None
    repo.records[0]["metadata_field_status"]["position_holder"] = {
        "status": "confirmed_absent",
        "method": "human",
    }
    repo.records[0]["metadata_evidence"]["position_holder"].update(
        {"reviewed_by": "human", "reviewed_at": "2026-09-24T00:00:00Z"}
    )
    monkeypatch.setattr(projection.experiment, "is_gold", lambda record_id: False)
    monkeypatch.setattr(projection, "_second_opinion_owed", lambda row, field: False)

    rows = projection.derive_build_metadata_exemplars(repo, "build-1")

    assert len(rows) == 1
    assert rows[0]["kind"] == "absence"
    assert rows[0]["field_value"] is None
    assert rows[0]["evidence_ref"]["block_ids"] == ["b2"]


def test_projector_rebuilds_dirty_scope_then_acknowledges(monkeypatch):
    repo = FakeRepo()
    index = FakeIndex()
    dirty = [
        {
            "item_id": "dirty-1",
            "projection": "metadata_exemplars",
            "scope_id": "build-1",
            "record_id": "r1",
            "status": "dirty",
        }
    ]
    monkeypatch.setattr(projection.experiment, "is_gold", lambda record_id: False)
    monkeypatch.setattr(projection, "_second_opinion_owed", lambda row, field: False)
    monkeypatch.setattr(
        projection.system_store,
        "list_semantic_memory_dirty",
        lambda name, limit=1000: list(dirty),
    )
    acknowledged = []
    monkeypatch.setattr(
        projection.system_store,
        "complete_semantic_memory_dirty",
        lambda item_ids: acknowledged.extend(item_ids) or len(item_ids),
    )

    result = projection.project_build_metadata_exemplars(repo, "build-1", index)

    assert result["skipped"] is False
    assert result["desired"] == 1
    assert result["acknowledged"] == 1
    assert acknowledged == ["dirty-1"]
    assert index.calls[0][0] == "build-1"
    assert index.calls[0][1][0]["record_id"] == "r1"


def test_projector_does_not_acknowledge_if_chroma_rebuild_fails(monkeypatch):
    repo = FakeRepo()

    class BrokenIndex:
        def rebuild_scope(self, scope_id, exemplars):
            raise RuntimeError("chroma unavailable")

    monkeypatch.setattr(projection.experiment, "is_gold", lambda record_id: False)
    monkeypatch.setattr(projection, "_second_opinion_owed", lambda row, field: False)
    monkeypatch.setattr(
        projection.system_store,
        "list_semantic_memory_dirty",
        lambda name, limit=1000: [
            {"item_id": "dirty-1", "scope_id": "build-1", "record_id": "r1"}
        ],
    )
    acknowledged = []
    monkeypatch.setattr(
        projection.system_store,
        "complete_semantic_memory_dirty",
        lambda item_ids: acknowledged.extend(item_ids) or len(item_ids),
    )

    try:
        projection.project_build_metadata_exemplars(repo, "build-1", BrokenIndex())
        raise AssertionError("projection failure should propagate")
    except RuntimeError as exc:
        assert "chroma unavailable" in str(exc)
    assert acknowledged == []


def test_best_effort_projection_never_makes_review_depend_on_chroma():
    manager = object.__new__(cb.PdfCorpusBuildManager)
    warnings: list[tuple[str, str]] = []

    def fail_projection(build_id: str, *, force: bool = False):
        raise RuntimeError("chroma unavailable")

    manager._project_metadata_exemplars = fail_projection  # type: ignore[method-assign]
    manager._append_warning = lambda build_id, message: warnings.append((build_id, message))  # type: ignore[method-assign]

    result = manager._project_metadata_exemplars_best_effort("build-1")

    assert result["projected"] is False
    assert result["error"] == "chroma unavailable"
    assert warnings and warnings[0][0] == "build-1"
    assert "projection is pending" in warnings[0][1]


def _patch_quiet(monkeypatch):
    monkeypatch.setattr(projection.experiment, "is_gold", lambda record_id: False)
    monkeypatch.setattr(projection, "_second_opinion_owed", lambda row, field: False)


def test_diagnosis_counts_a_derivable_exemplar(monkeypatch):
    _patch_quiet(monkeypatch)
    report = projection.diagnose_build_metadata_exemplars(FakeRepo(), "build-1")
    assert report["outcomes"].get("exemplar") == 1
    assert "no_evidence" not in report["outcomes"]


def test_diagnosis_explains_missing_evidence_even_though_a_value_was_confirmed(monkeypatch):
    _patch_quiet(monkeypatch)
    repo = FakeRepo()
    repo.records[0]["metadata_evidence"] = {}
    report = projection.diagnose_build_metadata_exemplars(repo, "build-1")
    assert report["outcomes"] == {"no_evidence": 1}
    assert report["examples"]["no_evidence"][0]["field"] == "position_holder"


def test_diagnosis_reports_evidence_outside_the_record(monkeypatch):
    _patch_quiet(monkeypatch)
    repo = FakeRepo()
    repo.records[0]["metadata_evidence"]["position_holder"]["block_ids"] = ["elsewhere"]
    report = projection.diagnose_build_metadata_exemplars(repo, "build-1")
    assert report["outcomes"] == {"evidence_not_in_record": 1}


def test_diagnosis_reports_unconfirmed_values(monkeypatch):
    _patch_quiet(monkeypatch)
    repo = FakeRepo()
    repo.records[0]["metadata_field_status"]["position_holder"]["status"] = "model_inferred"
    report = projection.diagnose_build_metadata_exemplars(repo, "build-1")
    assert report["outcomes"] == {"not_human_confirmed": 1}


def test_backlog_reports_dirty_rows_and_the_last_failure(monkeypatch):
    rows = [{"scope_id": "build-1", "item_id": "i1"}, {"scope_id": "build-1", "item_id": "i2"}]
    monkeypatch.setattr(projection.system_store, "list_semantic_memory_dirty", lambda *a, **k: rows)
    projection.record_projection_result("build-1", "ConnectError: no route to embedding host")
    backlog = projection.projection_backlog()
    assert backlog["dirty"] == 2 and backlog["scopes"] == ["build-1"]
    assert "ConnectError" in backlog["errors"]["build-1"]
    projection.record_projection_result("build-1")
    assert projection.projection_backlog()["errors"] == {}
