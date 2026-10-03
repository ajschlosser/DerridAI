#!/usr/bin/env python3
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

"""Count FieldAssertions per record: how many are current, superseded, or non-schema.

Usage: scripts/assertion_histogram.py path/to/records.jsonl [--top N]
Helps tell legitimate per-field evaluation records from accumulated history.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records")
    parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args()
    rows = []
    with open(args.records, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    totals = []
    for row in rows:
        buckets = row.get("field_assertions") or {}
        current = row.get("current_field_assertions") or {}
        total = sum(len(v) for v in buckets.values())
        legacy = sum(len(v) for k, v in buckets.items() if str(k).startswith("legacy."))
        versions = collections.Counter(len(v) for v in buckets.values())
        methods = collections.Counter(a.get("derivation_method") for v in buckets.values() for a in v)
        totals.append((total, row.get("record_id"), len(buckets), len(current), legacy, versions, methods))
    totals.sort(key=lambda item: item[0], reverse=True)
    for total, rid, fields, current, legacy, versions, methods in totals[: args.top]:
        print(f"{rid}: {total} assertions over {fields} fields; {current} current; {total - current} not current; {legacy} legacy.*")
        print(f"   versions-per-field histogram: {dict(sorted(versions.items()))}")
        print(f"   by derivation method: {dict(methods)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
