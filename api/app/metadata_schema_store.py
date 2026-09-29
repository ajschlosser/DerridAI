# Copyright 2026 Aaron John Schlosser, PhD.
"""Where saved metadata schemas live: one JSON file each, next to the corpus builds.

Built-in schemas are not files. The historical scholarly default is always listed first and remains the fallback when
no other profile is chosen. All built-ins are read-only; users can duplicate them into editable saved schemas.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from pathlib import Path
from typing import Any

from .metadata_schema import (
    DEFAULT_SCHEMA_ID,
    MetadataSchema,
    export_schema,
    import_schema,
)
from .metadata_schema_profiles import (
    BUILTIN_SCHEMA_IDS,
    builtin_schema,
    builtin_schemas,
)


class SchemaNotFound(KeyError):
    pass


class SchemaLocked(ValueError):
    pass


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")[:40] or "schema"


class SchemaStore:
    def __init__(self, root: Path) -> None:
        self.dir = root / "schemas"
        self.dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, schema_id: str) -> Path:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", schema_id):
            raise SchemaNotFound(schema_id)
        return self.dir / f"{schema_id}.json"

    def get(self, schema_id: str) -> MetadataSchema:
        built_in = builtin_schema(schema_id)
        if built_in is not None:
            return built_in
        try:
            return MetadataSchema.model_validate({**json.loads(self._path(schema_id).read_text(encoding="utf-8")), "id": schema_id})
        except (OSError, ValueError) as exc:
            raise SchemaNotFound(schema_id) from exc

    def list(self) -> list[dict[str, Any]]:
        schemas = list(builtin_schemas())
        for path in sorted(self.dir.glob("*.json")):
            if path.stem in BUILTIN_SCHEMA_IDS:
                continue  # built-ins cannot be shadowed by stale or manually copied files
            try:
                schemas.append(self.get(path.stem))
            except SchemaNotFound:
                continue  # a damaged file must not hide the others
        return [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "schema_version": s.schema_version,
                "builtin": s.id in BUILTIN_SCHEMA_IDS,
                "field_count": len(s.field_names()),
                "groups": [g.label for g in s.groups],
                "hash": s.content_hash(),
            }
            for s in schemas
        ]

    def save(self, schema: MetadataSchema, schema_id: str | None = None) -> MetadataSchema:
        """Create a schema (a new id) or replace an existing saved one. Built-in profiles cannot be replaced."""
        with self._lock:
            if schema_id in BUILTIN_SCHEMA_IDS:
                raise SchemaLocked("Built-in schemas cannot be changed. Duplicate the profile and edit the copy.")
            creating = schema_id is None
            if creating:
                base = _slug(schema.name)
                schema_id = "schema" if base == DEFAULT_SCHEMA_ID else base
                n = 2
                while self._path(schema_id).exists() or schema_id in BUILTIN_SCHEMA_IDS:
                    schema_id = f"{base}-{n}"
                    n += 1
            else:
                self._path(schema_id)  # validates the id
                if not self._path(schema_id).exists():
                    raise SchemaNotFound(schema_id)
            if creating:
                saved = schema.model_copy(update={"id": schema_id, "schema_version": "1.0.0"})
            else:
                previous = self.get(schema_id)
                saved = schema.model_copy(update={
                    "id": schema_id,
                    "schema_version": self._next_version(previous, schema),
                })
            fd, tmp = tempfile.mkstemp(dir=self.dir, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(saved.model_dump(mode="json", exclude={"id"}), handle, ensure_ascii=False, indent=1)
            os.replace(tmp, self._path(schema_id))
            return saved

    @staticmethod
    def _next_version(previous: MetadataSchema, proposed: MetadataSchema) -> str:
        old = previous.model_dump(mode="json", exclude={"id", "schema_version"})
        new = proposed.model_dump(mode="json", exclude={"id", "schema_version"})
        if old == new:
            return previous.schema_version
        # A deliberate rename that retains field_id is a compatible edit.
        old_fields = {field.field_id for field in previous.fields}
        new_fields = {field.field_id for field in proposed.fields}
        major, minor, patch = (int(value) for value in previous.schema_version.split("."))
        if old_fields - new_fields:
            return f"{major + 1}.0.0"
        if new_fields - old_fields:
            return f"{major}.{minor + 1}.0"
        return f"{major}.{minor}.{patch + 1}"

    def delete(self, schema_id: str) -> None:
        if schema_id in BUILTIN_SCHEMA_IDS:
            raise SchemaLocked("Built-in schemas cannot be deleted.")
        path = self._path(schema_id)
        if not path.exists():
            raise SchemaNotFound(schema_id)
        path.unlink()

    def export(self, schema_id: str) -> dict[str, Any]:
        return export_schema(self.get(schema_id))

    def import_(self, payload: Any) -> MetadataSchema:
        return self.save(import_schema(payload))
