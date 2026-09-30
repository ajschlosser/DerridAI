# Copyright 2026 Aaron John Schlosser, PhD.
"""Write the Pipeline Studio catalog fixture from the live pipeline contracts.

Storybook stories and Vitest read ``web/src/components/pipelines/fixtures/pipelineCatalogContract.json``
instead of hand-written purposes, vocabularies and strategies, so they exercise exactly what
``GET /api/system/pipelines`` serves. Regenerate it after changing a purpose, a strategy or a
workflow vocabulary. ``--check`` fails (exit 1) without writing when the checked-in file is stale.
"""
from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = (
    ROOT / "web" / "src" / "components" / "pipelines" / "fixtures" / "pipelineCatalogContract.json"
)
COMMAND = "python scripts/export_pipeline_catalog_fixture.py"


def _display(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def rendered_fixture() -> str:
    sys.path.insert(0, str(ROOT / "api"))
    from app.pipelines.purposes import workflow_vocabulary
    from app.pipelines.service import PipelineService
    from app.pipelines.workflows import purpose_catalog

    contract = {
        "purposes": purpose_catalog(),
        "vocabulary": workflow_vocabulary(),
        "strategies": PipelineService().strategies(),
    }
    return json.dumps(contract, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if the checked-in file is stale; write nothing.")
    args = parser.parse_args()

    rendered = rendered_fixture()
    current = FIXTURE_PATH.read_text(encoding="utf-8") if FIXTURE_PATH.exists() else None

    if args.check:
        if current != rendered:
            print(f"{_display(FIXTURE_PATH)} is stale. Run: {COMMAND}")
            diff = difflib.unified_diff(
                (current or "").splitlines(),
                rendered.splitlines(),
                fromfile=f"{_display(FIXTURE_PATH)} (checked in)",
                tofile=f"{_display(FIXTURE_PATH)} (generated)",
                lineterm="",
            )
            print("\n".join(diff))
            return 1
        return 0

    if current != rendered:
        FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE_PATH.write_text(rendered, encoding="utf-8")
        print(f"Wrote {_display(FIXTURE_PATH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
