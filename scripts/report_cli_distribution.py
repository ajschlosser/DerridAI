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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""Evaluate the measured onefile artifacts against the repository binary budget."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PER_TARGET_LIMIT = 10 * 1024 * 1024
TOTAL_LIMIT = 50 * 1024 * 1024
EXPECTED_TARGETS = {
    "linux-x86_64",
    "windows-x86_64",
    "macos-arm64",
    "macos-x86_64",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def _load_manifests(root: Path) -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []
    for path in sorted(root.rglob("binary-manifest-*-onefile.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("mode") != "onefile":
            continue
        payload["_manifest_path"] = str(path)
        manifests.append(payload)
    return manifests


def main() -> int:
    args = _parser().parse_args()
    manifests = _load_manifests(args.root.resolve())
    targets = {str(item.get("target") or "") for item in manifests}
    missing = sorted(EXPECTED_TARGETS - targets)
    if missing:
        raise RuntimeError(
            "Cannot make a repository-binary decision; missing onefile manifests for: "
            + ", ".join(missing)
        )

    rows = []
    for item in sorted(manifests, key=lambda value: str(value["target"])):
        size = int(item.get("size_bytes") or 0)
        rows.append(
            {
                "target": item["target"],
                "size_bytes": size,
                "limit_bytes": PER_TARGET_LIMIT,
                "within_per_target_budget": size <= PER_TARGET_LIMIT,
                "sha256": item.get("sha256"),
                "source_commit": item.get("source_commit"),
            }
        )

    total = sum(row["size_bytes"] for row in rows)
    eligible = all(row["within_per_target_budget"] for row in rows) and total <= TOTAL_LIMIT
    decision = {
        "schema_version": 1,
        "decision": "repository_eligible" if eligible else "release_assets_only",
        "reason": (
            "All measured onefile artifacts fit the 10 MiB per-target and 50 MiB total "
            "repository budgets."
            if eligible
            else "Measured onefile artifacts exceed the repository binary budget; "
            "publish them as release assets instead of committing generated binaries."
        ),
        "per_target_limit_bytes": PER_TARGET_LIMIT,
        "total_limit_bytes": TOTAL_LIMIT,
        "total_size_bytes": total,
        "within_total_budget": total <= TOTAL_LIMIT,
        "artifacts": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
