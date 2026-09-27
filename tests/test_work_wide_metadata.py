# Copyright 2026 Aaron John Schlosser, PhD.
"""Schema fields flagged 'applies to the work as a whole' can be filled once, before segmentation."""
import sys
import types
from pathlib import Path

import pytest

sys.modules.setdefault("chromadb", types.SimpleNamespace())
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app.corpus_manifest_workflow import _validated_work_metadata  # noqa: E402
from app.corpus_segmentation import _apply_manifest_metadata  # noqa: E402
from app.metadata_schema import SchemaField, default_schema  # noqa: E402


def _schema():
    schema = default_schema()
    extra = [
        SchemaField(name="edition_note", label="Edition note", group="discourse", applies_to_work=True),
        SchemaField(name="period", label="Period", group="discourse", applies_to_work=True, type="list"),
        SchemaField(name="tone", label="Tone", group="discourse"),
    ]
    return schema.model_copy(update={"fields": [*schema.fields, *extra]})


def test_only_work_wide_fields_are_accepted_and_values_are_normalised():
    schema = _schema()
    assert _validated_work_metadata(schema, {"edition_note": " Corrected ", "period": "early, late"}) == {
        "edition_note": "Corrected", "period": ["early", "late"],
    }
    with pytest.raises(ValueError):
        _validated_work_metadata(schema, {"tone": "ironic"})
    with pytest.raises(ValueError):
        _validated_work_metadata(schema, {"unknown": "x"})
    assert _validated_work_metadata(schema, None) == {}


def test_every_record_inherits_the_work_wide_value_unless_a_human_owns_it():
    record = {"record_id": "r1", "text": "Some text."}
    _apply_manifest_metadata(record, {"work_metadata": {"edition_note": "Corrected"}})
    assert record["edition_note"] == "Corrected"
