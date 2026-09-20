# Copyright 2026 Aaron John Schlosser, PhD.
"""An append-only ledger of what enrichment proposed and what people decided.

Every event carries the run id, model and field, so any number of runs can write to it at once
without coordinating and every metric (acceptance, calibration, corrections, cost) is a query over
the same rows rather than a counter that can drift. Rows are only ever appended; a correction is a
new row, never an edit. Appends are single `write` calls in append mode, so concurrent writers
cannot interleave inside a line.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# What can happen to a value. The first two are the model's doing, the rest are human decisions.
PROPOSED, AUTOFILLED = "proposed", "autofilled"
ACCEPTED, CORRECTED, REJECTED = "accepted", "corrected", "rejected"
REVIEW_EVENTS = {ACCEPTED, CORRECTED, REJECTED}


class EnrichmentLedger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def append(self, kind: str, *, model: str, field: str, build_id: str = "", record_id: str = "", run_id: str = "", **extra: Any) -> None:
        row = {
            "at": datetime.now(timezone.utc).isoformat(), "kind": kind, "run_id": run_id, "build_id": build_id,
            "record_id": record_id, "model": model, "field": field, **extra,
        }
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

    def review_counts(self, model: str, field: str) -> tuple[int, int]:
        """(reviews, accepted) for one model on one field, across every build and run."""
        reviews = accepted = 0
        for row in self.events():
            if row.get("model") == model and row.get("field") == field and row.get("kind") in REVIEW_EVENTS:
                reviews += 1
                accepted += row["kind"] == ACCEPTED
        return reviews, accepted
