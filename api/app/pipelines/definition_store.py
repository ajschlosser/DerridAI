# Copyright 2026 Aaron John Schlosser, PhD.
"""Persistence for immutable pipeline definitions and feature assignments."""

from __future__ import annotations

import sqlite3

from .models import PipelineAssignment, PipelineDefinition
from .storage import PipelineDatabase, dump_json, load_json


class PipelineDefinitionStore:
    def __init__(self, database: PipelineDatabase) -> None:
        self.database = database

    def list_definitions(
        self,
        *,
        purpose: str | None = None,
        status: str | None = None,
    ) -> list[PipelineDefinition]:
        with self.database.lock, self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM pipeline_definitions
                WHERE (? IS NULL OR purpose=?)
                  AND (? IS NULL OR status=?)
                ORDER BY purpose, pipeline_id, version DESC
                """,
                (purpose, purpose, status, status),
            ).fetchall()
        result: list[PipelineDefinition] = []
        for row in rows:
            payload = load_json(row["payload_json"], {})
            if not isinstance(payload, dict):
                continue
            try:
                result.append(PipelineDefinition.model_validate(payload))
            except ValueError:
                continue
        return result

    def get_definition(
        self,
        pipeline_id: str,
        version: int | None = None,
    ) -> PipelineDefinition | None:
        with self.database.lock, self.database.connect() as conn:
            if version is None:
                row = conn.execute(
                    """
                    SELECT payload_json
                    FROM pipeline_definitions
                    WHERE pipeline_id=?
                    ORDER BY version DESC
                    LIMIT 1
                    """,
                    (str(pipeline_id),),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT payload_json
                    FROM pipeline_definitions
                    WHERE pipeline_id=? AND version=?
                    """,
                    (str(pipeline_id), int(version)),
                ).fetchone()
        if row is None:
            return None
        payload = load_json(row["payload_json"], {})
        try:
            return PipelineDefinition.model_validate(payload)
        except ValueError:
            return None

    def put_definition(self, definition: PipelineDefinition) -> PipelineDefinition:
        """Persist one immutable custom pipeline version."""

        if definition.built_in:
            raise ValueError(
                "Built-in pipeline definitions are code-owned and cannot be persisted."
            )
        payload = definition.model_dump(mode="json")
        created_at = str(payload.get("created_at") or "")
        if not created_at:
            raise ValueError("Custom pipeline definitions require created_at.")

        with self.database.lock, self.database.connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO pipeline_definitions
                        (pipeline_id,version,name,purpose,status,created_at,created_by,payload_json)
                    VALUES(?,?,?,?,?,?,?,?)
                    """,
                    (
                        definition.pipeline_id,
                        definition.version,
                        definition.name,
                        definition.purpose,
                        definition.status,
                        created_at,
                        definition.created_by,
                        dump_json(payload),
                    ),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                raise ValueError(
                    f"Pipeline {definition.pipeline_id}@{definition.version} already exists; "
                    "create a new version."
                ) from exc
        return definition

    def list_assignments(self) -> list[PipelineAssignment]:
        with self.database.lock, self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM pipeline_assignments
                ORDER BY feature, scope, scope_id
                """
            ).fetchall()
        result: list[PipelineAssignment] = []
        for row in rows:
            payload = load_json(row["payload_json"], {})
            if not isinstance(payload, dict):
                continue
            try:
                result.append(PipelineAssignment.model_validate(payload))
            except ValueError:
                continue
        return result

    def get_assignment(
        self,
        feature: str,
        *,
        scope: str = "system",
        scope_id: str | None = None,
    ) -> PipelineAssignment | None:
        with self.database.lock, self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM pipeline_assignments
                WHERE feature=? AND scope=? AND scope_id=?
                """,
                (str(feature), str(scope), str(scope_id or "")),
            ).fetchone()
        if row is None:
            return None
        payload = load_json(row["payload_json"], {})
        try:
            return PipelineAssignment.model_validate(payload)
        except ValueError:
            return None

    def put_assignment(
        self,
        assignment: PipelineAssignment,
        *,
        updated_at: str,
    ) -> PipelineAssignment:
        payload = assignment.model_dump(mode="json")
        with self.database.lock, self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO pipeline_assignments
                    (feature,scope,scope_id,pipeline_id,pipeline_version,
                     override_allowed,source,updated_at,payload_json)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(feature,scope,scope_id) DO UPDATE SET
                    pipeline_id=excluded.pipeline_id,
                    pipeline_version=excluded.pipeline_version,
                    override_allowed=excluded.override_allowed,
                    source=excluded.source,
                    updated_at=excluded.updated_at,
                    payload_json=excluded.payload_json
                """,
                (
                    assignment.feature,
                    assignment.scope,
                    str(assignment.scope_id or ""),
                    assignment.pipeline_id,
                    assignment.pipeline_version,
                    int(assignment.override_allowed),
                    assignment.source,
                    str(updated_at),
                    dump_json(payload),
                ),
            )
            conn.commit()
        return assignment

    def delete_assignment(
        self,
        feature: str,
        *,
        scope: str = "system",
        scope_id: str | None = None,
    ) -> bool:
        with self.database.lock, self.database.connect() as conn:
            cursor = conn.execute(
                "DELETE FROM pipeline_assignments WHERE feature=? AND scope=? AND scope_id=?",
                (str(feature), str(scope), str(scope_id or "")),
            )
            conn.commit()
            return bool(cursor.rowcount)

    def snapshot(self) -> dict[str, list[dict]]:
        with self.database.lock, self.database.connect() as conn:
            definitions = [
                load_json(row["payload_json"], {})
                for row in conn.execute(
                    "SELECT payload_json FROM pipeline_definitions ORDER BY pipeline_id,version"
                )
            ]
            assignments = [
                load_json(row["payload_json"], {})
                for row in conn.execute(
                    "SELECT payload_json FROM pipeline_assignments ORDER BY feature,scope,scope_id"
                )
            ]
        return {
            "definitions": [item for item in definitions if isinstance(item, dict)],
            "assignments": [item for item in assignments if isinstance(item, dict)],
        }

    def clear(self) -> dict[str, int]:
        with self.database.lock, self.database.connect() as conn:
            counts = {
                "pipeline_assignments": int(
                    conn.execute("SELECT COUNT(*) FROM pipeline_assignments").fetchone()[0]
                ),
                "pipeline_definitions": int(
                    conn.execute("SELECT COUNT(*) FROM pipeline_definitions").fetchone()[0]
                ),
            }
            conn.execute("DELETE FROM pipeline_assignments")
            conn.execute("DELETE FROM pipeline_definitions")
            conn.commit()
        return counts
