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

"""Build the target-native DerridAI CLI with Nuitka.

Run this script on the operating system that will receive the artifact. The default
is the debuggable standalone distribution; pass --onefile only after standalone has
passed the same smoke/integration tests on that platform.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser()
    command.add_argument("--onefile", action="store_true")
    command.add_argument("--output-dir", type=Path, default=Path("dist/cli"))
    return command


def main() -> int:
    args = parser().parse_args()
    root = Path(__file__).resolve().parents[1]
    api = root / "api"
    output_dir = (root / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    mode = "onefile" if args.onefile else "standalone"
    command = [
        sys.executable,
        "-m",
        "nuitka",
        f"--mode={mode}",
        f"--output-dir={output_dir}",
        "--output-filename=derridai",
        "--python-flag=isolated",
        str(api / "derridai_cli.py"),
    ]
    completed = subprocess.run(command, cwd=api, check=False)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
