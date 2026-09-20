# Copyright 2026 Aaron John Schlosser, PhD.
"""An append-only ledger of what enrichment proposed and what people decided.

Every event carries the run id, model and field, so any number of runs can write to it at once
without coordinating and every metric (acceptance, calibration, corrections, cost) is a query over
the same rows rather than a counter that can drift. Rows are only ever appended; a correction is a
new row, never an edit. Appends are single `write` calls in append mode, so concurrent writers
cannot interleave inside a line.
"""

from __future__ import annotations

import csv
import io
import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .reviewer_context import current_reviewer

# What can happen to a value. PROPOSED and AUTOFILLED are the model's doing, CALL is one model request
# (its cost), and the rest are human decisions.
PROPOSED, AUTOFILLED, CALL = "proposed", "autofilled", "call"
BLIND_LABEL = "blind_label"  # a person's value for a field whose model value they could not see
RECHECK_SEAL, RECHECK = "recheck_seal", "recheck"  # a decision set aside to be asked again, and the second answer
SUSPENDED, RESUMED = "suspended", "resumed"  # the autofill policy switching a model and field off, and back on
ACCEPTED, CORRECTED, REJECTED = "accepted", "corrected", "rejected"
REVIEW_EVENTS = {ACCEPTED, CORRECTED, REJECTED}
HUMAN_EVENTS = REVIEW_EVENTS | {BLIND_LABEL, RECHECK_SEAL, RECHECK, "second_label"}


class EnrichmentLedger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def append(self, kind: str, *, model: str, field: str, build_id: str = "", record_id: str = "", run_id: str = "", **extra: Any) -> None:
        row = {
            "at": datetime.now(UTC).isoformat(), "kind": kind, "run_id": run_id, "build_id": build_id,
            "record_id": record_id, "model": model, "field": field, **extra,
        }
        if kind in HUMAN_EVENTS and "reviewer" not in row:
            row["reviewer"] = current_reviewer.get()  # empty for background work and for tests with no request
        line = json.dumps(row, ensure_ascii=False, default=str) + "\n"
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
            try:
                os.write(fd, line.encode("utf-8"))
            finally:
                os.close(fd)

    def events(self) -> list[dict[str, Any]]:
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        rows = []
        for line in lines:
            try:
                row = json.loads(line)
            except ValueError:
                continue  # a torn line from a crash costs one event, not the ledger
            if isinstance(row, dict):
                rows.append(row)
        return rows

    def sealed_value(self, build_id: str, record_id: str, field: str, kind: str = PROPOSED, column: str = "value") -> Any:
        """A value held back from the reviewer: the model's for a blind field, their own first answer for a re-check.

        It lives only here, never in the record the browser receives.
        """
        found = None
        for row in self.events():
            if row.get("kind") == kind and (kind != PROPOSED or row.get("blind")) and (row.get("build_id"), row.get("record_id"), row.get("field")) == (build_id, record_id, field):
                found = row.get(column)
        return found

    def review_counts(self, model: str, field: str) -> tuple[int, int]:
        """(reviews, accepted) for one model on one field, across every build and run."""
        reviews = accepted = 0
        for row in self.events():
            if row.get("gold"):
                continue  # gold records are scored, never learned from
            if row.get("model") == model and row.get("field") == field and row.get("kind") in REVIEW_EVENTS:
                reviews += 1
                accepted += row["kind"] == ACCEPTED
        return reviews, accepted

    def to_csv(self) -> str:
        """One row per event, one column per key; lists and objects are JSON text so no row is ragged."""
        rows = self.events()
        lead = ["at", "kind", "run_id", "build_id", "record_id", "model", "field", "reviewer", "arm", "ablations", "gold", "model_version", "prompt_version", "code_version", "temperature", "seed"]
        columns = lead + sorted({key for row in rows for key in row} - set(lead))
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v) for k, v in row.items()})
        return out.getvalue()
