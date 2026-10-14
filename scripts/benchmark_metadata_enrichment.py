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

"""Run a private fixed case through real providers; emit only safe measurements."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline-commit", required=True)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    case = json.loads(args.case.read_text(encoding="utf-8"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
    with tempfile.TemporaryDirectory(
        prefix="derridai-metadata-benchmark-"
    ) as temporary:
        root = Path(temporary)
        # Set these before app configuration imports; never touch production stores.
        os.environ.update(
            {
                "AUTH_DB_PATH": str(root / "auth.sqlite3"),
                "SYSTEM_DB_PATH": str(root / "system.sqlite3"),
                "CHROMA_DATA_ROOT": str(root),
                "CHROMA_PATH": str(root / "chroma"),
            }
        )
        from app.metadata_enrichment_benchmark import run_fixed_case

        report = run_fixed_case(
            case,
            root=root / "corpus",
            baseline_commit=args.baseline_commit,
            repeats=args.repeats,
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
