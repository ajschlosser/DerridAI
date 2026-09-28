# Copyright 2026 Aaron John Schlosser, PhD.
"""Write ``web/src/api/graphql/schema.graphql`` from the live Strawberry schema.

Introspection is force-enabled for the export regardless of ``GRAPHQL_INTROSPECTION_ENABLED``:
the SDL artifact is a build-time contract, not a runtime capability. ``--check`` fails (exit 1)
without writing when the checked-in file is stale, so CI catches a root/field added without
regenerating the frontend contract.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "web" / "src" / "api" / "graphql" / "schema.graphql"


def _display(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def rendered_schema() -> str:
    sys.path.insert(0, str(ROOT / "api"))
    from app.graphql.schema import build_schema
    from strawberry.printer import print_schema

    return print_schema(build_schema(introspection=True)) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if the checked-in file is stale; write nothing.")
    args = parser.parse_args()

    rendered = rendered_schema()
    current = SCHEMA_PATH.read_text(encoding="utf-8") if SCHEMA_PATH.exists() else None

    if args.check:
        if current != rendered:
            print(f"{_display(SCHEMA_PATH)} is stale. Run: python scripts/export_graphql_schema.py")
            return 1
        return 0

    if current != rendered:
        SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
        SCHEMA_PATH.write_text(rendered, encoding="utf-8")
        print(f"Wrote {_display(SCHEMA_PATH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
