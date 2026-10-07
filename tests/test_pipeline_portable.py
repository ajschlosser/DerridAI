# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

"""Portable PipelineDefinition export/import contract tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.pipelines.defaults import built_in_pipeline
from app.pipelines.manager import PipelineManager
from app.pipelines.models import PipelineDefinition
from app.pipelines.portable import (
    PipelineDocument,
    export_pipeline_document,
    parse_pipeline_document,
)
from app.pipelines.service import PipelineService, pipeline_hash
from app.pipelines.store import PipelineStore
from pydantic import ValidationError


def _built_in() -> PipelineDefinition:
    pipeline = built_in_pipeline("corpus.metadata_enrichment.current", 2)
    assert pipeline is not None
    return pipeline


def _custom() -> PipelineDefinition:
    return _built_in().model_copy(
        deep=True,
        update={
            "pipeline_id": "test.portable.metadata",
            "version": 7,
            "name": "Portable metadata test",
            "built_in": False,
            "created_at": datetime(2026, 10, 7, 0, 0, tzinfo=UTC),
            "created_by": "test",
        },
    )


def test_export_parse_round_trip_preserves_canonical_hash():
    pipeline = _built_in()

    document = export_pipeline_document(pipeline)
    parsed = parse_pipeline_document(document.model_dump(mode="json"))

    assert parsed.pipeline_hash == pipeline_hash(pipeline)
    assert pipeline_hash(parsed.pipeline) == pipeline_hash(pipeline)
    assert set(parsed.required_strategies) == {
        stage.strategy for stage in pipeline.stages
    }


def test_portable_document_rejects_unknown_execution_field():
    payload = export_pipeline_document(_built_in()).model_dump(mode="json")
    payload["pipeline"]["stages"][0]["unexpected"] = True

    with pytest.raises(ValidationError, match="Unknown pipeline stage field"):
        PipelineDocument.model_validate(payload)


def test_portable_document_rejects_hash_tampering():
    payload = export_pipeline_document(_built_in()).model_dump(mode="json")
    payload["pipeline"]["name"] = "Tampered"

    with pytest.raises(ValidationError, match="pipeline_hash does not match"):
        PipelineDocument.model_validate(payload)


def test_manager_import_preserves_hash_and_is_idempotent(tmp_path):
    manager = PipelineManager(
        service=PipelineService(),
        store=PipelineStore(tmp_path / "pipelines.sqlite3"),
    )
    pipeline = _custom()
    expected = pipeline_hash(pipeline)

    first, created = manager.import_definition(pipeline)
    second, created_again = manager.import_definition(pipeline)

    assert created is True
    assert created_again is False
    assert pipeline_hash(first) == expected
    assert pipeline_hash(second) == expected


def test_manager_import_rejects_same_id_version_with_different_content(tmp_path):
    manager = PipelineManager(
        service=PipelineService(),
        store=PipelineStore(tmp_path / "pipelines.sqlite3"),
    )
    pipeline = _custom()
    manager.import_definition(pipeline)

    conflicting = pipeline.model_copy(update={"name": "Different content"})
    with pytest.raises(ValueError, match="different canonical content"):
        manager.import_definition(conflicting)


def test_manager_import_does_not_persist_identical_code_owned_builtin(tmp_path):
    manager = PipelineManager(
        service=PipelineService(),
        store=PipelineStore(tmp_path / "pipelines.sqlite3"),
    )
    pipeline = _built_in()

    imported, created = manager.import_definition(pipeline)

    assert created is False
    assert pipeline_hash(imported) == pipeline_hash(pipeline)
    assert manager.store.get_definition(pipeline.pipeline_id, pipeline.version) is None
