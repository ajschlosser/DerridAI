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

"""Headless corpus output projections.

The canonical Corpus Builder record remains authoritative. These functions only
project a validated build into a deliberately smaller research artifact or copy an
existing immutable cELF publication to the user-requested destination.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .corpus_metadata import MANIFEST_INHERITED_FIELDS
from .metadata_schema import CORE_FIELDS, MetadataSchema


@dataclass(frozen=True)
class ResearchWriteResult:
    record_count: int
    content_sha256: str
    archive_sha256: str
    uncompressed_bytes: int
    compressed_bytes: int


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def research_metadata_fields(schema: MetadataSchema) -> list[str]:
    """Return the stable metadata allow-list for the compact research profile."""
    ordered: list[str] = list(MANIFEST_INHERITED_FIELDS)
    ordered.extend(CORE_FIELDS)
    ordered.extend(
        field.name
        for field in schema.fields
        if field.role != "operational" and field.name not in ordered
    )
    return list(dict.fromkeys(ordered))


def project_research_record(
    record: dict[str, Any],
    schema: MetadataSchema,
) -> dict[str, Any]:
    """Project one canonical Record into the small research-corpus surface.

    Root-level schema/document values remain flat for downstream JSONL consumers.
    Review state, assertion history, prompt traces, NLP projections, caches, and
    other operational fields are excluded by construction rather than subtraction.
    """
    source_spans = record.get("source_spans")
    projected: dict[str, Any] = {
        "record_id": record.get("record_id"),
        "text": record.get("text"),
        "source_document_id": record.get("source_document_id"),
        "source_spans": source_spans if isinstance(source_spans, list) else [],
    }
    for name in research_metadata_fields(schema):
        projected[name] = record.get(name)
    return projected


def write_research_jsonl_zst(
    path: str | Path,
    records: Iterable[dict[str, Any]],
    *,
    schema: MetadataSchema,
    compression_level: int = 10,
) -> ResearchWriteResult:
    """Atomically write the research projection as Zstandard-compressed JSONL."""
    try:
        import zstandard as zstd
    except ImportError as exc:  # pragma: no cover - runtime dependency contract
        raise RuntimeError(
            "Writing .jsonl.zst output requires the zstandard package."
        ) from exc

    target = Path(path)
    if not target.name.endswith(".jsonl.zst"):
        raise ValueError("Research corpus output must end in .jsonl.zst")
    target.parent.mkdir(parents=True, exist_ok=True)

    content_hasher = hashlib.sha256()
    uncompressed_bytes = 0
    record_count = 0
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    temporary = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as raw:
            compressor = zstd.ZstdCompressor(
                level=int(compression_level),
                write_checksum=True,
                write_content_size=False,
            )
            with compressor.stream_writer(raw, closefd=False) as compressed:
                for record in records:
                    line = (
                        json.dumps(
                            project_research_record(record, schema),
                            ensure_ascii=False,
                            separators=(",", ":"),
                        )
                        + "\n"
                    ).encode("utf-8")
                    content_hasher.update(line)
                    uncompressed_bytes += len(line)
                    compressed.write(line)
                    record_count += 1
            raw.flush()
            os.fsync(raw.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)

    return ResearchWriteResult(
        record_count=record_count,
        content_sha256=content_hasher.hexdigest(),
        archive_sha256=_sha256_file(target),
        uncompressed_bytes=uncompressed_bytes,
        compressed_bytes=target.stat().st_size,
    )


def atomic_copy(source: str | Path, destination: str | Path) -> None:
    """Copy one completed artifact with an atomic final rename."""
    source_path = Path(source)
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    os.close(fd)
    temporary = Path(tmp_name)
    try:
        shutil.copyfile(source_path, temporary)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
