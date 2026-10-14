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

"""Field scope and document-field policies in metadata schemas (format 2), and what consumes them."""
import sys
import types
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.modules.setdefault("chromadb", types.SimpleNamespace())
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import corpus_builder as cb  # noqa: E402
from app import metadata_schema as ms  # noqa: E402


def _body(**extra):
    body = ms.default_schema().model_dump(mode="json", exclude={"id"})
    body.update(extra)
    return body


def test_format_1_work_wide_flag_migrates_to_corpus_scope():
    field = ms.SchemaField.model_validate({"name": "edition_note", "label": "Edition note", "applies_to_work": True})
    assert field.scope == "corpus"
    plain = ms.SchemaField.model_validate({"name": "tone", "label": "Tone", "applies_to_work": False})
    assert plain.scope == "record"
    assert "applies_to_work" not in field.model_dump()


def test_format_1_file_imports_with_default_document_policies():
    body = _body()
    body.pop("document_fields")
    body["format_version"] = 1
    body["fields"][0]["applies_to_work"] = True
    body["fields"][0].pop("scope")
    schema = ms.import_schema({"derridai_metadata_schema": 1, "schema": body})
    assert schema.format_version == ms.FORMAT_VERSION
    assert schema.fields[0].scope == "corpus"
    assert [p.name for p in schema.document_fields] == list(ms.DOCUMENT_FIELDS)
    assert schema.required_document_fields("evidence") == ["title", "document_author"]


def test_document_policies_are_completed_in_canonical_order_and_validated():
    schema = ms.MetadataSchema.model_validate(_body(document_fields=[
        {"name": "translator", "required_for": ["publication", "publication"]},
    ]))
    assert [p.name for p in schema.document_fields] == list(ms.DOCUMENT_FIELDS)
    translator = schema.document_policy("translator")
    assert translator.required_for == ["publication"]
    assert translator.field_id == "derridai.document.translator"
    # Omitted policies take the defaults, so the author is still required.
    assert "document_author" in schema.required_document_fields("publication")
    with pytest.raises(ValidationError):
        ms.MetadataSchema.model_validate(_body(document_fields=[{"name": "shoe_size"}]))
    with pytest.raises(ValidationError):
        ms.MetadataSchema.model_validate(_body(document_fields=[{"name": "title"}, {"name": "title"}]))


def _ready_build(schema: dict | None):
    return {
        "profile_id": cb.PROFILE_VERSION, "record_count": 1, "accepted_count": 1, "rejected_count": 0,
        "needs_review_count": 0, "boundary_review_count": 0, "source_problem_count": 0,
        "metadata_total": 1, "metadata_completed": 1,
        "metadata_issue_summary": {"fields_unresolved": 0, "records_incomplete": 0},
        "manifest": {"title": "De la grammatologie", "document_author": ""},
        "validation": {"valid": True, "source_valid": True, "metadata_valid": True},
        "status": "ready", "stage": "ready", **({"schema": schema} if schema is not None else {}),
    }


def test_publication_requirements_come_from_the_build_schema():
    relaxed = _body(document_fields=[{"name": "document_author", "required_for": []}])
    build = _ready_build(relaxed)
    cb.PdfCorpusBuildManager._refresh_workflow_fields(build)
    assert build["publication_readiness"]["missing_document_fields"] == []

    # A build pinned before policies existed keeps the old requirement.
    legacy = _body()
    legacy.pop("document_fields")
    build = _ready_build(legacy)
    cb.PdfCorpusBuildManager._refresh_workflow_fields(build)
    assert build["publication_readiness"]["missing_document_fields"] == ["document_author"]
