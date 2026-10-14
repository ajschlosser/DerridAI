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

"""Provenance linking a published Record back to the build whose Document Intelligence covers it.

Why: the semantic map (Document Intelligence / Semantic Content Graph) is derived,
build-scoped storage that is never rebuilt from the published corpus. A published
Record's row never carries `build_id` (see corpus_publication.serialize_public_record),
so the Record and Works views need another way to find the build behind a Record's or
a Work's semantic map once it has been published.
How: publishing a build now records record_id -> build_id (and work) provenance in the
system store; a REST resolution endpoint reads it back by record_id or by work.
"""

import json
import sys
import types
from pathlib import Path

sys.modules.setdefault("chromadb", types.SimpleNamespace())
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
from app import corpus_builder as cb
from app.system_store import system_store


def _install_publishable(repo: cb.PdfCorpusRepository, *, build_id_hint: str, work: str):
    asset = {
        "asset_id": f"pdf-{build_id_hint}",
        "sha256": "source-sha",
        "filename": "test.pdf",
        "page_count": 1,
        "block_count": 1,
        "ocr_pages": 0,
        "warnings": [],
        "metadata": {},
        "pages": [],
    }
    cb._json_write(repo.asset_meta_path(asset["asset_id"]), asset)
    repo.asset_blocks_path(asset["asset_id"]).write_text(
        json.dumps(
            {
                "block_id": "b1",
                "page": 1,
                "bbox": [0, 0, 1, 1],
                "type": "paragraph",
                "text": "Record text",
                "extraction_method": "native",
                "confidence": 1.0,
            }
        )
        + "\n"
    )
    build = repo.create_build(
        {
            "asset_id": asset["asset_id"],
            "source_sha256": "source-sha",
            "source_filename": "test.pdf",
            "schema_version": cb.SCHEMA_VERSION,
            "profile_id": cb.PROFILE_VERSION,
            "profile_version": 8,
            "app_version": "0.60.0",
            "document_prompt_version": cb.DOCUMENT_PROMPT_VERSION,
            "segmentation_prompt_version": cb.SEGMENTATION_PROMPT_VERSION,
            "metadata_prompt_version": cb.METADATA_PROMPT_VERSION,
            "provider": "ollama",
            "model": "profile-model",
            "request": {"provider_profile_id": "primary", "record_sizing": {"preferred_record_chars": 1750}},
            "manifest": {"title": work, "document_author": "Test Author"},
            "validation": {"valid": True},
        }
    )
    record = {
        "record_id": f"r-{build_id_hint}",
        "record_revision": 1,
        "text": "Record text",
        "text_length": 11,
        "work": work,
        "source_asset_id": asset["asset_id"],
        "source_block_ids": ["b1"],
        "source_spans": [{"block_id": "b1", "page": 1}],
        "accepted": True,
        "review_disposition": "accepted",
        "needs_review": False,
        "region_type": "main_text",
        "primary_text": True,
        "discourse_role": "assertion",
        "metadata_complete": True,
        "metadata_incomplete_fields": [],
        "metadata_field_status": {
            "region_type": {"status": "human_confirmed"},
            "primary_text": {"status": "human_confirmed"},
            "discourse_role": {"status": "human_confirmed"},
        },
    }
    repo.save_records(build["build_id"], [record])
    build.update(
        {
            "record_count": 1,
            "accepted_count": 1,
            "rejected_count": 0,
            "needs_review_count": 0,
            "validation": {"valid": True},
            "status": "ready",
            "stage": "ready",
            "progress": 0.98,
        }
    )
    repo.save_build(build)
    return build, record["record_id"]


def test_publish_records_build_provenance_for_the_record_and_its_work(tmp_path: Path):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    build, record_id = _install_publishable(repo, build_id_hint="a", work="Of Grammatology")

    assert system_store.get_record_build_id(record_id) is None

    manager.publish(build["build_id"])

    assert system_store.get_record_build_id(record_id) == build["build_id"]
    assert system_store.list_build_ids_for_work("Of Grammatology") == [build["build_id"]]
    assert system_store.list_records_for_work("Of Grammatology") == [
        {"record_id": record_id, "build_id": build["build_id"]}
    ]
    assert system_store.list_records_for_work("Unknown work") == []


def test_republishing_the_same_record_id_from_a_newer_build_overwrites_provenance(tmp_path: Path):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    build_one, record_id = _install_publishable(repo, build_id_hint="b", work="Of Grammatology")
    manager.publish(build_one["build_id"])
    assert system_store.get_record_build_id(record_id) == build_one["build_id"]

    build_two = repo.create_build(
        {
            "asset_id": "pdf-b",
            "source_sha256": "source-sha",
            "source_filename": "test.pdf",
            "schema_version": cb.SCHEMA_VERSION,
            "profile_id": cb.PROFILE_VERSION,
            "profile_version": 8,
            "app_version": "0.60.0",
            "document_prompt_version": cb.DOCUMENT_PROMPT_VERSION,
            "segmentation_prompt_version": cb.SEGMENTATION_PROMPT_VERSION,
            "metadata_prompt_version": cb.METADATA_PROMPT_VERSION,
            "provider": "ollama",
            "model": "profile-model",
            "request": {"provider_profile_id": "primary", "record_sizing": {"preferred_record_chars": 1750}},
            "manifest": {"title": "Of Grammatology", "document_author": "Test Author"},
            "validation": {"valid": True},
        }
    )
    record = {
        "record_id": record_id,
        "record_revision": 1,
        "text": "Revised record text",
        "text_length": 20,
        "work": "Of Grammatology",
        "source_asset_id": "pdf-b",
        "source_block_ids": ["b1"],
        "source_spans": [{"block_id": "b1", "page": 1}],
        "accepted": True,
        "review_disposition": "accepted",
        "needs_review": False,
        "region_type": "main_text",
        "primary_text": True,
        "discourse_role": "assertion",
        "metadata_complete": True,
        "metadata_incomplete_fields": [],
        "metadata_field_status": {
            "region_type": {"status": "human_confirmed"},
            "primary_text": {"status": "human_confirmed"},
            "discourse_role": {"status": "human_confirmed"},
        },
    }
    repo.save_records(build_two["build_id"], [record])
    build_two.update(
        {
            "record_count": 1,
            "accepted_count": 1,
            "rejected_count": 0,
            "needs_review_count": 0,
            "validation": {"valid": True},
            "status": "ready",
            "stage": "ready",
            "progress": 0.98,
        }
    )
    repo.save_build(build_two)

    manager.publish(build_two["build_id"])

    assert system_store.get_record_build_id(record_id) == build_two["build_id"]
