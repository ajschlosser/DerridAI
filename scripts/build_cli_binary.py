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

"""Build a target-native DerridAI CLI with Nuitka and emit artifact metadata.

Run this script on the operating system that will receive the artifact. Standalone
is the default because dependency closure is easier to inspect. Onefile candidates
are produced only after standalone acceptance for the same target.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.config import APP_VERSION, resolve_git_commit  # noqa: E402
from app.corpus_binary_manifest import (  # noqa: E402
    executable_name,
    release_artifact_name,
    sha256_file,
    target_key,
)
from app.pipelines.compatibility import pipeline_contract_identity  # noqa: E402


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description="Compile the DerridAI headless CLI with Nuitka."
    )
    command.add_argument("--onefile", action="store_true")
    command.add_argument("--output-dir", type=Path, default=Path("dist/cli"))
    command.add_argument(
        "--target",
        help="Expected target key; defaults to detected OS/architecture and fails on mismatch.",
    )
    return command


def _nuitka_version() -> str:
    completed = subprocess.run(
        [sys.executable, "-m", "nuitka", "--version"],
        cwd=API_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.splitlines()[0].strip() if completed.stdout else ""


def _directory_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _primary_executable(output_dir: Path, target: str) -> Path:
    expected = executable_name(target)  # type: ignore[arg-type]
    candidates = [
        path
        for path in output_dir.rglob(expected)
        if path.is_file() and ".build" not in path.parts
    ]
    if not candidates:
        raise FileNotFoundError(
            f"Nuitka completed but {expected!r} was not found under {output_dir}"
        )
    candidates.sort(
        key=lambda path: (
            0 if path.parent == output_dir else 1,
            0 if path.parent.name.endswith(".dist") else 1,
            len(path.parts),
        )
    )
    return candidates[0]


def _write_manifest(
    *,
    output_dir: Path,
    primary: Path,
    target: str,
    mode: str,
    nuitka_version: str,
) -> Path:
    distribution_root = primary.parent if mode == "standalone" else primary
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "app_version": APP_VERSION,
        "git_commit": resolve_git_commit(),
        "target": target,
        "packaging": f"nuitka-{mode}",
        "python": sys.version.split()[0],
        "nuitka": nuitka_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "artifact": primary.name,
        "artifact_path": str(primary.relative_to(output_dir)),
        "sha256": sha256_file(primary),
        "size_bytes": primary.stat().st_size,
        "distribution_size_bytes": (
            _directory_size(distribution_root)
            if distribution_root.is_dir()
            else distribution_root.stat().st_size
        ),
        "pipeline_contract": pipeline_contract_identity(),
    }
    manifest_path = output_dir / f"binary-manifest-{target}-{mode}.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def _promote_onefile(primary: Path, output_dir: Path, target: str) -> Path:
    release_name = release_artifact_name(target)  # type: ignore[arg-type]
    promoted = output_dir / release_name
    if primary.resolve() != promoted.resolve():
        promoted.unlink(missing_ok=True)
        shutil.move(str(primary), promoted)
    if not target.startswith("windows-"):
        promoted.chmod(promoted.stat().st_mode | 0o111)
    checksum = sha256_file(promoted)
    (output_dir / f"{release_name}.sha256").write_text(
        f"{checksum}  {release_name}\n",
        encoding="utf-8",
    )
    return promoted


def main() -> int:
    args = parser().parse_args()
    output_dir = (ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    detected_target = target_key()
    if args.target and args.target != detected_target:
        print(
            f"Requested target {args.target!r} does not match build host "
            f"{detected_target!r}.",
            file=sys.stderr,
        )
        return 2
    target = detected_target
    mode = "onefile" if args.onefile else "standalone"

    command = [
        sys.executable,
        "-m",
        "nuitka",
        f"--mode={mode}",
        f"--output-dir={output_dir}",
        "--output-filename=derridai",
        "--python-flag=isolated",
        "--assume-yes-for-downloads",
        str(API_ROOT / "derridai_cli.py"),
    ]
    completed = subprocess.run(command, cwd=API_ROOT, check=False)
    if completed.returncode != 0:
        return int(completed.returncode)

    try:
        primary = _primary_executable(output_dir, target)
        if mode == "onefile":
            primary = _promote_onefile(primary, output_dir, target)
        manifest = _write_manifest(
            output_dir=output_dir,
            primary=primary,
            target=target,
            mode=mode,
            nuitka_version=_nuitka_version(),
        )
    except (OSError, ValueError) as exc:
        print(f"Binary packaging failed: {exc}", file=sys.stderr)
        return 1

    relative = primary.relative_to(output_dir)
    print(f"Built {relative}")
    print(f"Manifest {manifest.relative_to(output_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
