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

"""Synchronous, non-HTTP application service for headless corpus builds."""

from __future__ import annotations

import os
import platform
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from .corpus_cli_config import CorpusProcessingConfig
from .corpus_run_config import CorpusRunEnvelopeV2
from .corpus_output_profiles import atomic_copy, write_research_jsonl_zst
from .metadata_schema import MetadataSchema

RunProfile = Literal["research", "celf"]
ProgressCallback = Callable[[dict[str, Any]], None]
CorpusRunConfig = CorpusProcessingConfig | CorpusRunEnvelopeV2


class HeadlessCorpusError(RuntimeError):
    """Base error with a stable CLI-facing category."""

    category: Literal[
        "source",
        "capability",
        "pipeline",
        "provider",
        "validation",
        "output",
    ] = "pipeline"


class SourceInputError(HeadlessCorpusError):
    category = "source"


class PipelineExecutionError(HeadlessCorpusError):
    category = "pipeline"


class ProviderExecutionError(HeadlessCorpusError):
    category = "provider"


class PublicationExecutionError(HeadlessCorpusError):
    category = "validation"


class OutputWriteError(HeadlessCorpusError):
    category = "output"


@dataclass(frozen=True)
class HeadlessRunResult:
    status: str
    build_id: str
    source: str
    records: int
    output: str
    sha256: str
    publication_profile: RunProfile
    celf_conformant: bool | None
    workspace: str
    publication_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_cli_data_root() -> Path:
    """Return a platform-appropriate writable base for retained CLI run state."""
    explicit = os.getenv("DERRIDAI_CLI_DATA_ROOT", "").strip()
    if explicit:
        return Path(explicit).expanduser()

    system = platform.system().casefold()
    home = Path.home()
    if system == "windows":
        local = os.getenv("LOCALAPPDATA", "").strip()
        return (
            Path(local) / "DerridAI" / "cli"
            if local
            else home / "AppData" / "Local" / "DerridAI" / "cli"
        )
    if system == "darwin":
        return home / "Library" / "Application Support" / "DerridAI" / "cli"

    xdg = os.getenv("XDG_DATA_HOME", "").strip()
    return (Path(xdg) if xdg else home / ".local" / "share") / "derridai" / "cli"


def new_workspace(root: str | Path | None = None) -> Path:
    """Create a durable run workspace rather than hiding failure state in /tmp."""
    base = Path(root).expanduser() if root is not None else default_cli_data_root()
    workspace = base / "runs" / f"run-{uuid.uuid4().hex[:16]}"
    workspace.mkdir(parents=True, exist_ok=False)
    return workspace


class HeadlessCorpusRunner:
    """Run Corpus Builder from a local source to one finished artifact.

    The existing manager still owns pipeline behavior. This service supplies a
    synchronous boundary for the CLI: it registers the source directly, waits for
    the shared build worker to settle, runs autonomous policy synchronously, then
    publishes through the canonical publication code.
    """

    def __init__(
        self,
        *,
        workspace: str | Path | None = None,
        repository: Any | None = None,
        manager: Any | None = None,
        poll_seconds: float = 0.25,
    ) -> None:
        if (repository is None) != (manager is None):
            raise ValueError("repository and manager must be supplied together")
        self.workspace = (
            Path(workspace).expanduser().resolve()
            if workspace is not None
            else new_workspace().resolve()
        )
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._repository = repository
        self._manager = manager
        self.poll_seconds = max(0.01, float(poll_seconds))

    def _engine(self) -> tuple[Any, Any]:
        if self._repository is not None and self._manager is not None:
            return self._repository, self._manager
        from .corpus_builder import PdfCorpusBuildManager, PdfCorpusRepository

        repository = PdfCorpusRepository(self.workspace)
        manager = PdfCorpusBuildManager(repository, max_workers=1)
        self._repository = repository
        self._manager = manager
        return repository, manager

    @staticmethod
    def _validated_request(
        config: CorpusRunConfig,
        asset_id: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        from .models import PdfCorpusBuildCreate

        request = config.build_request()
        request["asset_id"] = asset_id
        desired_autonomous = {
            **(request.get("autonomous") or {}),
            "enabled": True,
        }
        # The CLI owns the synchronization boundary. Let the ordinary build worker
        # stop at review, then run the same autonomous policy directly below.
        request["autonomous"] = {**desired_autonomous, "enabled": False}
        validated = PdfCorpusBuildCreate.model_validate(request).model_dump(
            mode="json",
            exclude_none=True,
        )
        return validated, desired_autonomous

    def _wait_for_build(
        self,
        build_id: str,
        *,
        progress: ProgressCallback | None,
    ) -> dict[str, Any]:
        repository, manager = self._engine()
        last_signature: tuple[Any, ...] | None = None
        try:
            while True:
                build = repository.get_build(build_id)
                signature = (
                    build.get("status"),
                    build.get("stage"),
                    build.get("progress"),
                    build.get("metadata_completed"),
                    build.get("metadata_total"),
                )
                if progress is not None and signature != last_signature:
                    progress(dict(build))
                    last_signature = signature

                status = str(build.get("status") or "")
                if status in {"failed", "cancelled"}:
                    self._raise_failed_build(build)
                if status not in {"queued", "running"}:
                    return build
                time.sleep(self.poll_seconds)
        except KeyboardInterrupt:
            try:
                manager.cancel(build_id)
            finally:
                raise

    @staticmethod
    def _raise_failed_build(build: dict[str, Any]) -> None:
        error = str(build.get("error") or "Corpus build failed.")
        stage = str(build.get("interrupted_stage") or build.get("stage") or "")
        if stage in {"enriching", "metadata_retry", "metadata_enrichment_rerun"}:
            raise ProviderExecutionError(error)
        raise PipelineExecutionError(error)

    @staticmethod
    def _source_output_path(
        source: Path,
        output: str | Path | None,
    ) -> Path:
        if output is not None:
            return Path(output).expanduser().resolve()
        return source.with_suffix("").with_name(f"{source.stem}.jsonl.zst").resolve()

    def run(
        self,
        source: str | Path,
        config: CorpusRunConfig,
        *,
        output: str | Path | None = None,
        force_profile: RunProfile | None = None,
        progress: ProgressCallback | None = None,
    ) -> HeadlessRunResult:
        source_path = Path(source).expanduser().resolve()
        if not source_path.is_file():
            raise SourceInputError(f"Source file does not exist: {source_path}")

        # A v2 file names the pipeline it expects to execute. Validate that
        # identity before reading or extracting a potentially large source. The
        # current Corpus Builder still resolves this pipeline through its shared
        # assignment registry, so a mismatch must fail rather than be ignored.
        if isinstance(config, CorpusRunEnvelopeV2):
            from .pipelines.manager import pipeline_manager

            try:
                config.validate_current_headless_execution(pipeline_manager)
            except ValueError as exc:
                raise PipelineExecutionError(str(exc)) from exc

        try:
            source_bytes = source_path.read_bytes()
        except OSError as exc:
            raise SourceInputError(f"Unable to read source {source_path}: {exc}") from exc
        if not source_bytes:
            raise SourceInputError(f"Source file is empty: {source_path}")

        repository, manager = self._engine()
        try:
            asset = repository.save_asset(
                source_bytes,
                filename=source_path.name,
                ocr_mode=config.source.ocr_mode,
                ocr_languages=config.source.ocr_languages,
                detect_page_numbers=config.source.detect_page_numbers,
                audio_diarization=config.source.audio_diarization,
            )
        except (OSError, ValueError) as exc:
            raise SourceInputError(str(exc)) from exc

        request, desired_autonomous = self._validated_request(
            config,
            str(asset["asset_id"]),
        )
        try:
            build = manager.create(request)
        except ValueError as exc:
            raise PipelineExecutionError(str(exc)) from exc

        build_id = str(build["build_id"])
        build = self._wait_for_build(build_id, progress=progress)

        # Run policy synchronously so publication cannot race the background worker's
        # transition from review to autonomous settlement.
        try:
            manager.run_autonomous(
                build_id,
                {
                    **request,
                    "autonomous": desired_autonomous,
                },
            )
        except ValueError as exc:
            raise ProviderExecutionError(str(exc)) from exc

        try:
            publication = manager.publish(
                build_id,
                require_acceptance=True,
                accept_unreviewed=True,
            )
        except ValueError as exc:
            raise PublicationExecutionError(str(exc)) from exc

        target = self._source_output_path(source_path, output)
        profile: RunProfile = force_profile or config.publication.profile
        publication_id = str(publication.get("publication_id") or "")
        if not target.name.endswith(".jsonl.zst"):
            raise OutputWriteError("Corpus output must end in .jsonl.zst")
        if profile == "celf" and publication.get("celf_conformant") is not True:
            conformance = publication.get("celf_conformance")
            detail = (
                str(conformance)
                if conformance not in (None, {})
                else "no conformance detail was recorded"
            )
            raise PublicationExecutionError(
                "cELF output was requested but the canonical publication did not "
                f"pass cELF conformance: {detail}"
            )
        try:
            if profile == "celf":
                published = repository.publication_path(publication_id)
                atomic_copy(published, target)
                integrity = repository.publication_integrity_path(publication_id)
                if integrity.is_file():
                    atomic_copy(integrity, target.with_name(f"{target.name}.sha512"))
                archive_sha256 = str(publication.get("archive_sha256") or "")
                record_count = int(publication.get("record_count") or 0)
                celf_conformant: bool | None = bool(
                    publication.get("celf_conformant")
                )
            else:
                from .corpus_publication import publishable_records

                build = repository.get_build(build_id)
                schema = MetadataSchema.model_validate(build["schema"])
                records = publishable_records(repository.load_records(build_id))
                written = write_research_jsonl_zst(
                    target,
                    records,
                    schema=schema,
                )
                archive_sha256 = written.archive_sha256
                record_count = written.record_count
                celf_conformant = None
        except (OSError, RuntimeError, ValueError) as exc:
            raise OutputWriteError(str(exc)) from exc

        return HeadlessRunResult(
            status="ok",
            build_id=build_id,
            source=str(source_path),
            records=record_count,
            output=str(target),
            sha256=archive_sha256,
            publication_profile=profile,
            celf_conformant=celf_conformant,
            workspace=str(self.workspace),
            publication_id=publication_id or None,
        )
