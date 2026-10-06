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

"""Headless corpus orchestration tests using a small fake shared engine."""

from __future__ import annotations

from pathlib import Path

from app.corpus_cli_config import CorpusProcessingConfig
from app.headless_corpus_runner import HeadlessCorpusRunner
from app.metadata_schema import default_schema


class FakeRepository:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.asset_calls: list[dict] = []
        self.build = {
            "build_id": "build-1",
            "status": "awaiting_review",
            "stage": "review",
            "progress": 0.9,
            "metadata_completed": 1,
            "metadata_total": 1,
            "schema": default_schema().model_dump(mode="json"),
        }
        self.records = [
            {
                "record_id": "rec-1",
                "text": "A source-bound passage.",
                "source_document_id": "doc-1",
                "source_spans": [
                    {
                        "source_document_id": "doc-1",
                        "page_start": 1,
                        "page_end": 1,
                    }
                ],
                "work": "Example Work",
                "speaker": "Derrida",
                "position_holder": "Heidegger",
                "review_disposition": "accepted",
                "accepted": True,
            }
        ]
        (root / "publications").mkdir(parents=True, exist_ok=True)

    def save_asset(self, data: bytes, **kwargs):
        self.asset_calls.append({"data": data, **kwargs})
        return {"asset_id": "asset-1"}

    def get_build(self, build_id: str):
        assert build_id == "build-1"
        return dict(self.build)

    def load_records(self, build_id: str):
        assert build_id == "build-1"
        return [dict(record) for record in self.records]

    def publication_path(self, publication_id: str) -> Path:
        return self.root / "publications" / f"{publication_id}.jsonl.zst"

    def publication_integrity_path(self, publication_id: str) -> Path:
        path = self.publication_path(publication_id)
        return path.with_name(f"{path.name}.sha512")


class FakeManager:
    def __init__(self, repository: FakeRepository) -> None:
        self.repository = repository
        self.created_request: dict | None = None
        self.autonomous_request: dict | None = None

    def create(self, request: dict):
        self.created_request = dict(request)
        return {"build_id": "build-1"}

    def run_autonomous(self, build_id: str, request: dict):
        assert build_id == "build-1"
        self.autonomous_request = dict(request)
        return {"accepted": 1, "left_for_review": 0}

    def publish(self, build_id: str, **kwargs):
        assert build_id == "build-1"
        assert kwargs == {"require_acceptance": True, "accept_unreviewed": True}
        publication_id = "publication-1"
        path = self.repository.publication_path(publication_id)
        path.write_bytes(b"celf-fixture")
        self.repository.publication_integrity_path(publication_id).write_text(
            "abc  publication-1.jsonl.zst\n",
            encoding="ascii",
        )
        return {
            "publication_id": publication_id,
            "record_count": 1,
            "archive_sha256": "celf-archive-sha",
            "celf_conformant": True,
        }

    def cancel(self, build_id: str):
        return {"build_id": build_id, "cancel_requested": True}


def _runner(tmp_path: Path) -> tuple[HeadlessCorpusRunner, FakeRepository, FakeManager]:
    repository = FakeRepository(tmp_path / "workspace")
    manager = FakeManager(repository)
    return (
        HeadlessCorpusRunner(
            workspace=repository.root,
            repository=repository,
            manager=manager,
            poll_seconds=0.01,
        ),
        repository,
        manager,
    )


def test_headless_runner_uses_shared_build_then_emits_research_projection(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("A source-bound passage.", encoding="utf-8")
    output = tmp_path / "out.jsonl.zst"
    config = CorpusProcessingConfig.model_validate({"version": 1})
    runner, repository, manager = _runner(tmp_path)

    result = runner.run(source, config, output=output)

    assert result.status == "ok"
    assert result.publication_profile == "research"
    assert result.records == 1
    assert result.celf_conformant is None
    assert output.is_file()
    assert repository.asset_calls[0]["filename"] == "source.txt"
    assert manager.created_request is not None
    assert manager.created_request["asset_id"] == "asset-1"
    assert manager.created_request["autonomous"]["enabled"] is False
    assert manager.autonomous_request is not None
    assert manager.autonomous_request["autonomous"]["enabled"] is True


def test_headless_runner_celf_profile_copies_canonical_publication_and_sidecar(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("A source-bound passage.", encoding="utf-8")
    output = tmp_path / "celf.jsonl.zst"
    config = CorpusProcessingConfig.model_validate(
        {"version": 1, "publication": {"profile": "celf"}}
    )
    runner, _repository, _manager = _runner(tmp_path)

    result = runner.run(source, config, output=output)

    assert result.publication_profile == "celf"
    assert result.celf_conformant is True
    assert result.sha256 == "celf-archive-sha"
    assert output.read_bytes() == b"celf-fixture"
    assert output.with_name("celf.jsonl.zst.sha512").is_file()
