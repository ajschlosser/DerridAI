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

"""Smoke-test a compiled DerridAI CLI artifact using its generated manifest."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser()
    command.add_argument("--manifest", required=True, type=Path)
    return command


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def main() -> int:
    args = parser().parse_args()
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    binary = manifest_path.parent / str(manifest["artifact_path"])
    if not binary.is_file():
        raise FileNotFoundError(binary)

    _run([str(binary), "--version"])

    reported = _run(
        [str(binary), "pipeline", "capabilities", "--json"]
    )
    actual_contract = json.loads(reported.stdout)
    expected_contract = manifest.get("pipeline_contract")
    if actual_contract != expected_contract:
        raise RuntimeError(
            "Compiled binary pipeline capabilities differ from the source-tree "
            "catalog recorded in its build manifest."
        )

    with tempfile.TemporaryDirectory(prefix="derridai-cli-smoke-") as tmp:
        config = Path(tmp) / "corpus-processing.yaml"
        config.write_text("version: 1\n", encoding="utf-8")
        _run(
            [
                str(binary),
                "config",
                "validate",
                "--config",
                str(config),
                "--json",
            ]
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
