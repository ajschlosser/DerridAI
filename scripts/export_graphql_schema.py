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

"""Write ``web/src/api/graphql/schema.graphql`` from the live Strawberry schema.

Introspection is force-enabled for the export regardless of ``GRAPHQL_INTROSPECTION_ENABLED``:
the SDL artifact is a build-time contract, not a runtime capability. ``--check`` fails (exit 1)
without writing when the checked-in file is stale, so CI catches a root/field added without
regenerating the frontend contract.
"""
from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "web" / "src" / "api" / "graphql" / "schema.graphql"

GRAPHQL_HEADER = """# This file is part of DerridAI, a cELF-compliant research workspace
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

"""


def _display(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def rendered_schema() -> str:
    sys.path.insert(0, str(ROOT / "api"))
    from app.graphql.schema import build_schema
    from strawberry.printer import print_schema

    return GRAPHQL_HEADER + print_schema(build_schema(introspection=True)) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if the checked-in file is stale; write nothing.")
    args = parser.parse_args()

    rendered = rendered_schema()
    current = SCHEMA_PATH.read_text(encoding="utf-8") if SCHEMA_PATH.exists() else None

    if args.check:
        if current != rendered:
            print(f"{_display(SCHEMA_PATH)} is stale. Run: python scripts/export_graphql_schema.py")
            diff = difflib.unified_diff(
                (current or "").splitlines(),
                rendered.splitlines(),
                fromfile=f"{_display(SCHEMA_PATH)} (checked in)",
                tofile=f"{_display(SCHEMA_PATH)} (generated)",
                lineterm="",
            )
            print("\n".join(diff))
            return 1
        return 0

    if current != rendered:
        SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
        SCHEMA_PATH.write_text(rendered, encoding="utf-8")
        print(f"Wrote {_display(SCHEMA_PATH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
