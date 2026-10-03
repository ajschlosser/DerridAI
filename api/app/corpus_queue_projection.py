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

"""Rebuildable transactional review selection; canonical payloads remain authoritative."""
# SQL identifiers come only from the closed server-owned column/queue registry; values are bound.
# ruff: noqa: S608
from __future__ import annotations

import base64
import copy
import hashlib
import json
import sqlite3
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from .corpus_review_aggregates import record_review_aggregate
from .corpus_review_queue import (
    QueueFilter,
    _compute_observed_metadata_values,
    _disposition,
)
from .corpus_review_state import _queue_counts
from .corpus_reviewer_helpers import _present_for_reviewer, _scrub_canonical_transport
from .reviewer_context import current_reviewer

CONTRACT = "corpus-review-projection-v1"
COUNT_KEYS = tuple(_queue_counts([]))
QUEUES = {"ready", "issues", "metadata", "topology", "source", "accepted", "rejected"}


class QueueCursorError(ValueError):
    code = "BAD_REQUEST"


class StaleQueueCursor(QueueCursorError):
    code = "STALE_QUEUE_CURSOR"


def initialize(connection: sqlite3.Connection) -> None:
    incomplete = any(
        connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is None
        for table in (
            "review_queue_rows", "review_search", "review_facets", "review_facet_totals",
            "review_queue_totals", "review_metric_parts", "review_metric_totals", "review_issue_rows", "review_incomplete_rows",
        )
    )
    statements = [
        """CREATE TABLE IF NOT EXISTS review_projection_meta (
            id INTEGER PRIMARY KEY CHECK(id=1), contract TEXT NOT NULL DEFAULT '',
            schema_identity TEXT NOT NULL DEFAULT '', generation INTEGER NOT NULL DEFAULT 0,
            topology INTEGER NOT NULL DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS review_projection_dirty (record_id TEXT PRIMARY KEY)""",
        """CREATE TABLE IF NOT EXISTS review_queue_rows (
            record_id TEXT PRIMARY KEY, ordinal INTEGER NOT NULL, state_version INTEGER NOT NULL,
            needs_review INTEGER NOT NULL, metadata_incomplete INTEGER NOT NULL,
            source_problem INTEGER NOT NULL, disposition TEXT NOT NULL,
            """ + ", ".join(f"c_{key} INTEGER NOT NULL" for key in COUNT_KEYS) + ")",
        """CREATE INDEX IF NOT EXISTS idx_review_queue_order ON review_queue_rows(ordinal)""",
        """CREATE INDEX IF NOT EXISTS idx_review_queue_disposition ON review_queue_rows(disposition, ordinal)""",
        """CREATE TABLE IF NOT EXISTS review_search (
            record_id TEXT NOT NULL, scope TEXT NOT NULL, search_text TEXT NOT NULL,
            PRIMARY KEY(record_id, scope))""",
        """CREATE TABLE IF NOT EXISTS review_facets (
            record_id TEXT NOT NULL, scope TEXT NOT NULL, field TEXT NOT NULL, value TEXT NOT NULL,
            PRIMARY KEY(record_id, scope, field, value))""",
        """CREATE TABLE IF NOT EXISTS review_facet_totals (
            scope TEXT NOT NULL, field TEXT NOT NULL, value TEXT NOT NULL, n INTEGER NOT NULL,
            PRIMARY KEY(scope, field, value))""",
        """CREATE TABLE IF NOT EXISTS review_queue_totals (
            category TEXT PRIMARY KEY, n INTEGER NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS review_metric_parts (
            record_id TEXT NOT NULL, running INTEGER NOT NULL, category TEXT NOT NULL,
            metric TEXT NOT NULL, n INTEGER NOT NULL, PRIMARY KEY(record_id,running,category,metric))""",
        """CREATE TABLE IF NOT EXISTS review_metric_totals (
            running INTEGER NOT NULL, category TEXT NOT NULL, metric TEXT NOT NULL,
            n INTEGER NOT NULL, PRIMARY KEY(running,category,metric))""",
        """CREATE TABLE IF NOT EXISTS review_issue_rows (
            record_id TEXT NOT NULL, running INTEGER NOT NULL, position INTEGER NOT NULL,
            ordinal INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(record_id,running,position))""",
        """CREATE TABLE IF NOT EXISTS review_incomplete_rows (
            record_id TEXT NOT NULL, running INTEGER NOT NULL, ordinal INTEGER NOT NULL,
            payload TEXT NOT NULL, PRIMARY KEY(record_id,running))""",
        "CREATE INDEX IF NOT EXISTS idx_review_issues_order ON review_issue_rows(running,ordinal,position)",
        "CREATE INDEX IF NOT EXISTS idx_review_incomplete_order ON review_incomplete_rows(running,ordinal)",
    ]
    for statement in statements:
        connection.execute(statement)
    if connection.execute("SELECT 1 FROM review_projection_meta WHERE id=1").fetchone() is None:
        connection.execute("INSERT INTO review_projection_meta(id) VALUES(1)")
    elif incomplete:
        connection.execute("UPDATE review_projection_meta SET contract='' WHERE id=1")
    for key in QUEUES:
        connection.execute(
            f"CREATE INDEX IF NOT EXISTS idx_review_queue_{key} ON review_queue_rows(c_{key}, ordinal)"
        )
    for field in ("needs_review", "metadata_incomplete", "source_problem"):
        connection.execute(
            f"CREATE INDEX IF NOT EXISTS idx_review_queue_{field} ON review_queue_rows({field}, ordinal)"
        )
    for operation, subject in (("INSERT", "NEW"), ("UPDATE", "NEW"), ("DELETE", "OLD")):
        topology = (
            "CASE WHEN OLD.ordinal != NEW.ordinal OR OLD.record_id != NEW.record_id THEN 1 ELSE 0 END"
            if operation == "UPDATE" else "1"
        )
        old_dirty = (
            "INSERT OR IGNORE INTO review_projection_dirty VALUES(OLD.record_id);"
            if operation == "UPDATE" else ""
        )
        connection.execute(f"""
            CREATE TRIGGER IF NOT EXISTS review_projection_{operation.lower()}
            AFTER {operation} ON corpus_records BEGIN
                INSERT OR IGNORE INTO review_projection_dirty VALUES({subject}.record_id);
                {old_dirty}
                UPDATE review_projection_meta SET generation=generation+1, topology=topology+{topology}
                WHERE id=1;
            END
        """)


def _transport_record(record: dict[str, Any]) -> dict[str, Any]:
    record = copy.deepcopy(record)
    if any(
        isinstance(status, dict) and status.get("recheck")
        for status in (record.get("metadata_field_status") or {}).values()
    ):
        _scrub_canonical_transport(record)
    return record


def _variants(record: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    owners = {
        str(item["first_reviewer"]) for item in (record.get("second_opinion") or {}).values()
        if isinstance(item, dict) and not item.get("done") and item.get("first_reviewer")
    }
    # A synthetic non-owner is only a presentation context, never a persisted reviewer.
    non_owner = "projection"
    while non_owner in owners:
        non_owner += "_"
    variants: list[tuple[str, dict[str, Any]]] = []
    for scope, reviewer in [("", ""), ("*", non_owner), *[(f"user:{owner}", owner) for owner in sorted(owners)]]:
        token = current_reviewer.set(reviewer)
        try:
            presented = copy.deepcopy(record)
            _present_for_reviewer(presented)
            variants.append((scope, presented))
        finally:
            current_reviewer.reset(token)
    return variants


def _remove_row(connection: sqlite3.Connection, record_id: str) -> None:
    previous = connection.execute(
        "SELECT " + ", ".join(f"c_{key}" for key in COUNT_KEYS) + " FROM review_queue_rows WHERE record_id=?",
        (record_id,),
    ).fetchone()
    if previous:
        connection.executemany(
            "UPDATE review_queue_totals SET n=n-? WHERE category=?",
            [(value, key) for key, value in zip(COUNT_KEYS, previous)],
        )
    connection.execute("""
        UPDATE review_facet_totals SET n=n-1 WHERE (scope, field, value) IN
        (SELECT scope, field, value FROM review_facets WHERE record_id=?)
    """, (record_id,))
    connection.execute("DELETE FROM review_facet_totals WHERE n=0")
    for running, category, metric, n in connection.execute(
        "SELECT running,category,metric,n FROM review_metric_parts WHERE record_id=?", (record_id,),
    ).fetchall():
        connection.execute(
            "UPDATE review_metric_totals SET n=n-? WHERE running=? AND category=? AND metric=?",
            (n, running, category, metric),
        )
    connection.execute("DELETE FROM review_metric_totals WHERE n=0")
    for table in ("review_queue_rows", "review_search", "review_facets", "review_metric_parts", "review_issue_rows", "review_incomplete_rows"):
        connection.execute(f"DELETE FROM {table} WHERE record_id=?", (record_id,))


def _add_metrics(connection: sqlite3.Connection, ordinal: int, record: dict[str, Any]) -> None:
    record_id = str(record["record_id"])
    for running in (False, True):
        part = record_review_aggregate(record, running)
        scalars = {
            "needs_review_count": int(bool(record.get("needs_review"))),
            "accepted_count": int(str(record.get("review_disposition") or "") == "accepted"),
            "rejected_count": int(str(record.get("review_disposition") or "") == "rejected"),
            "source_problem_count": int(bool(record.get("source_quality_issues"))),
            "metadata_completed": int(bool(record.get("metadata_complete"))),
            "records_incomplete": int(bool(part["incomplete"])),
            "auto_retry_records": int(any(row["retryable"] for row in part["rows"])),
            "human_review_records": int(any(not row["retryable"] for row in part["rows"])),
            "auto_retry_fields": sum(bool(row["retryable"]) for row in part["rows"]),
            "human_review_fields": sum(not row["retryable"] for row in part["rows"]),
            "llm_elapsed_ms": part["llm_elapsed_ms"], "llm_family_calls": part["llm_family_calls"],
        }
        groups = {"scalar": scalars, **{key: part[key] for key in ("by_field", "by_reason", "invalid_by_field", "contribution")}}
        for category, metrics in groups.items():
            for metric, n in metrics.items():
                if not n:
                    continue
                connection.execute("INSERT INTO review_metric_parts VALUES(?,?,?,?,?)", (record_id, running, category, metric, n))
                connection.execute(
                    """INSERT INTO review_metric_totals VALUES(?,?,?,?)
                       ON CONFLICT(running,category,metric) DO UPDATE SET n=n+excluded.n""",
                    (running, category, metric, n),
                )
        connection.executemany(
            "INSERT INTO review_issue_rows VALUES(?,?,?,?,?)",
            [(record_id, running, index, ordinal, json.dumps(row, ensure_ascii=False)) for index, row in enumerate(part["rows"])],
        )
        if part["incomplete"]:
            incomplete = {
                "record_id": record_id, "fields": part["incomplete"], "issues": part["rows"],
                "page_start": record.get("page_start"), "page_end": record.get("page_end"),
            }
            connection.execute(
                "INSERT INTO review_incomplete_rows VALUES(?,?,?,?)",
                (record_id, running, ordinal, json.dumps(incomplete, ensure_ascii=False)),
            )


def update_rows(
    connection: sqlite3.Connection,
    rows: list[tuple[int, dict[str, Any]]],
    *,
    removed: list[str] | None = None,
) -> None:
    generation = int(connection.execute("SELECT generation FROM review_projection_meta WHERE id=1").fetchone()[0])
    for record_id in removed or []:
        _remove_row(connection, record_id)
        connection.execute("DELETE FROM review_projection_dirty WHERE record_id=?", (record_id,))
    columns = ("record_id", "ordinal", "state_version", "needs_review", "metadata_incomplete", "source_problem", "disposition")
    columns += tuple(f"c_{key}" for key in COUNT_KEYS)
    for ordinal, raw in rows:
        record = _transport_record(raw)
        record_id = str(record["record_id"])
        _remove_row(connection, record_id)
        counts = _queue_counts([record])
        values = (
            record_id, ordinal, generation, bool(record.get("needs_review")),
            not bool(record.get("metadata_complete")), bool(record.get("source_quality_issues")),
            _disposition(record), *[counts[key] for key in COUNT_KEYS],
        )
        connection.execute(
            f"INSERT INTO review_queue_rows ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
            values,
        )
        connection.executemany(
            """INSERT INTO review_queue_totals(category,n) VALUES(?,?)
               ON CONFLICT(category) DO UPDATE SET n=n+excluded.n""",
            list(counts.items()),
        )
        _add_metrics(connection, ordinal, raw)
        for scope, presented in _variants(record):
            connection.execute(
                "INSERT INTO review_search VALUES(?,?,?)",
                (record_id, scope, json.dumps(presented, ensure_ascii=False).casefold()),
            )
            facets = _compute_observed_metadata_values([presented], present=False)
            contributions = [(record_id, scope, field, value) for field, values in facets.items() for value in values]
            connection.executemany("INSERT INTO review_facets VALUES(?,?,?,?)", contributions)
            connection.executemany(
                """INSERT INTO review_facet_totals VALUES(?,?,?,1)
                   ON CONFLICT(scope,field,value) DO UPDATE SET n=n+1""",
                [(scope, field, value) for _, scope, field, value in contributions],
            )
        connection.execute("DELETE FROM review_projection_dirty WHERE record_id=?", (record_id,))


def ensure(
    connection: sqlite3.Connection, schema_identity: str,
    decode: Callable[[str], dict[str, Any]], *, rebuild: bool = False,
) -> None:
    meta = connection.execute("SELECT contract,schema_identity FROM review_projection_meta WHERE id=1").fetchone()
    if rebuild or meta != (CONTRACT, schema_identity):
        for table in (
            "review_queue_rows", "review_search", "review_facets", "review_facet_totals", "review_queue_totals",
            "review_metric_parts", "review_metric_totals", "review_issue_rows", "review_incomplete_rows",
        ):
            connection.execute(f"DELETE FROM {table}")
        connection.execute(
            "UPDATE review_projection_meta SET contract=?,schema_identity=?,generation=generation+1,topology=topology+1 WHERE id=1",
            (CONTRACT, schema_identity),
        )
        rows = connection.execute("SELECT ordinal,payload FROM corpus_records ORDER BY ordinal").fetchall()
        update_rows(connection, [(int(ordinal), decode(payload)) for ordinal, payload in rows])
        connection.execute("DELETE FROM review_projection_dirty")
        return
    dirty = connection.execute("""
        SELECT d.record_id,c.ordinal,c.payload FROM review_projection_dirty d
        LEFT JOIN corpus_records c ON c.record_id=d.record_id
    """).fetchall()
    update_rows(
        connection, [(int(ordinal), decode(payload)) for _, ordinal, payload in dirty if payload is not None],
        removed=[record_id for record_id, _, payload in dirty if payload is None],
    )


def build_aggregates(connection: sqlite3.Connection, running: bool) -> dict[str, Any]:
    groups: dict[str, dict[str, int]] = {category: {} for category in ("scalar", "by_field", "by_reason", "invalid_by_field", "contribution")}
    for category, metric, n in connection.execute(
        "SELECT category,metric,n FROM review_metric_totals WHERE running=?", (running,),
    ):
        groups[category][metric] = int(n)
    scalar = groups["scalar"]
    summary: dict[str, Any] = {key: scalar.get(key, 0) for key in (
        "records_incomplete", "auto_retry_records", "human_review_records", "auto_retry_fields", "human_review_fields",
    )}
    summary["fields_unresolved"] = sum(groups["by_field"].values())
    for category in ("by_field", "by_reason", "invalid_by_field"):
        summary[category] = dict(sorted(groups[category].items()))
    summary["issues"] = [json.loads(row[0]) for row in connection.execute(
        "SELECT payload FROM review_issue_rows WHERE running=? ORDER BY ordinal,position LIMIT 1000", (running,),
    )]
    summary["records"] = [json.loads(row[0]) for row in connection.execute(
        "SELECT payload FROM review_incomplete_rows WHERE running=? ORDER BY ordinal LIMIT 250", (running,),
    )]
    counts = dict(connection.execute("SELECT category,n FROM review_queue_totals"))
    contribution = groups["contribution"]
    elapsed = scalar.get("llm_elapsed_ms", 0)
    useful = contribution.get("llm_fields_usable", 0) + contribution.get("llm_fields_proposed", 0)
    return {
        **{key: scalar.get(key, 0) for key in ("needs_review_count", "accepted_count", "rejected_count", "source_problem_count", "metadata_completed")},
        "record_count": counts.get("all", 0), "metadata_total": counts.get("all", 0),
        "metadata_issue_summary": summary, "review_queue_counts": {key: counts.get(key, 0) for key in COUNT_KEYS},
        "llm_contribution": {
            **contribution, "family_calls": scalar.get("llm_family_calls", 0), "elapsed_ms": elapsed,
            "useful_fields_per_minute": round(useful / max(1 / 60, elapsed / 60000), 2) if elapsed else 0.0,
        },
    }


def facets(connection: sqlite3.Connection, fields: list[str] | None = None) -> dict[str, list[str]]:
    reviewer = str(current_reviewer.get() or "")
    if not reviewer:
        rows = connection.execute("SELECT field,value FROM review_facet_totals WHERE scope='' AND n>0").fetchall()
    else:
        scope = f"user:{reviewer}"
        rows = connection.execute("""
            SELECT field,value FROM (
                SELECT field,value,n FROM review_facet_totals WHERE scope='*'
                UNION ALL SELECT field,value,n FROM review_facet_totals WHERE scope=?
                UNION ALL SELECT f.field,f.value,-1 FROM review_facets f
                    JOIN review_search s ON s.record_id=f.record_id AND s.scope=?
                    WHERE f.scope='*'
            ) GROUP BY field,value HAVING SUM(n)>0
        """, (scope, scope)).fetchall()
    result: dict[str, list[str]] = {}
    for field, value in rows:
        if not fields or field in fields:
            result.setdefault(field, []).append(value)
    return {field: sorted(values, key=str.casefold) for field, values in result.items()}


def _where(filters: QueueFilter) -> tuple[str, list[Any]]:
    terms: list[str] = []
    values: list[Any] = []
    for field in ("needs_review", "disposition", "metadata_incomplete", "source_problem"):
        value = getattr(filters, field)
        if value is not None:
            terms.append(f"q.{field}=?")
            values.append(value)
    query = filters.query.casefold().strip()
    if query:
        reviewer = str(current_reviewer.get() or "")
        scope = f"user:{reviewer}" if reviewer else ""
        default = "*" if reviewer else ""
        terms.append("""instr(COALESCE(
            (SELECT search_text FROM review_search WHERE record_id=q.record_id AND scope=?),
            (SELECT search_text FROM review_search WHERE record_id=q.record_id AND scope=?)),?)>0""")
        values.extend((scope, default, query))
    return " AND ".join(terms) or "1", values


def _membership(queue: str | None) -> str:
    if not queue or queue == "all":
        return "1"
    if queue in {"accepted", "rejected"}:
        return f"q.c_{queue}=1"
    if queue in QUEUES:
        return f"q.disposition='pending' AND q.c_{queue}=1"
    return "q.disposition='pending'"


def _context(build_id: str, filters: QueueFilter) -> str:
    data = asdict(filters)
    data["query"] = filters.query.casefold().strip()
    data["review_queue"] = filters.review_queue or "all"
    encoded = json.dumps([build_id, str(current_reviewer.get() or ""), data, CONTRACT], sort_keys=True)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _cursor(context: str, topology: int, ordinal: int) -> str:
    return base64.urlsafe_b64encode(json.dumps([context, topology, ordinal]).encode()).decode()


def _anchor(cursor: str, context: str, topology: int) -> int:
    if not isinstance(cursor, str) or len(cursor) > 512:
        raise QueueCursorError("Invalid queue cursor.")
    try:
        payload = json.loads(base64.b64decode(cursor, altchars=b"-_", validate=True))
    except (ValueError, UnicodeError) as exc:
        raise QueueCursorError("Invalid queue cursor.") from exc
    if (
        not isinstance(payload, list) or len(payload) != 3
        or not isinstance(payload[0], str) or type(payload[1]) is not int
        or type(payload[2]) is not int or payload[2] < 0
    ):
        raise QueueCursorError("Invalid queue cursor.")
    if payload[0] != context:
        raise QueueCursorError("Queue cursor context does not match this request.")
    if payload[1] != topology:
        raise StaleQueueCursor("Queue cursor topology has changed.")
    return payload[2]


def select(
    connection: sqlite3.Connection, build_id: str, filters: QueueFilter, *,
    offset: int, limit: int, cursor: str | None, direction: str,
) -> tuple[list[tuple[str, int, int]], dict[str, Any]]:
    if direction not in {"forward", "backward"}:
        raise QueueCursorError("Invalid queue cursor direction.")
    where, values = _where(filters)
    generation, topology = connection.execute(
        "SELECT generation,topology FROM review_projection_meta WHERE id=1"
    ).fetchone()
    context = _context(build_id, filters)
    if where == "1":
        counts = dict(connection.execute("SELECT category,n FROM review_queue_totals"))
        counts = {key: int(counts.get(key, 0)) for key in COUNT_KEYS}
    else:
        sums = connection.execute(
            "SELECT " + ",".join(f"COALESCE(SUM(q.c_{key}),0)" for key in COUNT_KEYS)
            + " FROM review_queue_rows q WHERE " + where, values,
        ).fetchone()
        counts = dict(zip(COUNT_KEYS, sums))
    selected_where = f"({where}) AND ({_membership(filters.review_queue)})"
    if where == "1" and filters.review_queue in {None, "", "all", "accepted", "rejected"}:
        total = counts[filters.review_queue or "all"]
    else:
        total = int(connection.execute("SELECT COUNT(*) FROM review_queue_rows q WHERE " + selected_where, values).fetchone()[0])
    start, size = max(0, offset), max(0, limit)
    selection_values = list(values)
    page_where = selected_where
    order = "ASC"
    if cursor is not None:
        anchor = _anchor(cursor, context, int(topology))
        page_where += " AND q.ordinal" + (">?" if direction == "forward" else "<?")
        selection_values.append(anchor)
        start = 0
        order = "ASC" if direction == "forward" else "DESC"
    rows = connection.execute(
        "SELECT q.record_id,q.ordinal,q.state_version FROM review_queue_rows q WHERE "
        + page_where + f" ORDER BY q.ordinal {order} LIMIT ? OFFSET ?",
        [*selection_values, size, start],
    ).fetchall()
    if order == "DESC":
        rows.reverse()
    if cursor is not None:
        boundary = rows[0][1] if rows else anchor
        start = int(connection.execute(
            "SELECT COUNT(*) FROM review_queue_rows q WHERE " + selected_where + " AND q.ordinal<?",
            [*values, boundary],
        ).fetchone()[0])
        if not rows and direction == "forward":
            start = total
    topology_row = connection.execute("SELECT n FROM review_queue_totals WHERE category='all'").fetchone()
    topology_count = int(topology_row[0]) if topology_row else 0
    page = {
        "total": total, "offset": start, "limit": limit, "queue_counts": counts,
        "topology_count": topology_count, "data_generation": int(generation), "topology_generation": int(topology),
        "has_previous_page": bool(rows and start > 0), "has_next_page": bool(rows and start + len(rows) < total),
        "previous_cursor": _cursor(context, int(topology), int(rows[0][1])) if rows and start > 0 else None,
        "next_cursor": _cursor(context, int(topology), int(rows[-1][1])) if rows and start + len(rows) < total else None,
    }
    return rows, page


def next_pending(connection: sqlite3.Connection, record_id: str, queue: str | None) -> str | None:
    row = connection.execute("SELECT ordinal FROM review_queue_rows WHERE record_id=?", (record_id,)).fetchone()
    ordinal = int(row[0]) if row else -1
    for membership in (_membership(queue), "1"):
        for ordering in (">", "<="):
            candidate = connection.execute(
                "SELECT q.record_id FROM review_queue_rows q WHERE q.disposition='pending' AND "
                + membership + " AND q.record_id!=? AND q.ordinal" + ordering + "? ORDER BY q.ordinal LIMIT 1",
                (record_id, ordinal),
            ).fetchone()
            if candidate:
                return str(candidate[0])
    return None
