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

"""Build/runtime identity helpers for target-native DerridAI CLI artifacts."""

from __future__ import annotations

import hashlib
import platform
from pathlib import Path
from typing import Literal

BinaryTarget = Literal[
    "linux-x86_64",
    "windows-x86_64",
    "macos-arm64",
    "macos-x86_64",
]


def normalize_architecture(machine: str) -> Literal["x86_64", "arm64"]:
    """Normalize platform architecture names to DerridAI artifact vocabulary."""
    normalized = str(machine or "").strip().casefold().replace("-", "_")
    if normalized in {"x86_64", "amd64", "x64"}:
        return "x86_64"
    if normalized in {"arm64", "aarch64"}:
        return "arm64"
    raise ValueError(f"Unsupported CLI architecture: {machine!r}")


def target_key(*, system: str | None = None, machine: str | None = None) -> BinaryTarget:
    """Return the release artifact target key for one supported native platform."""
    system_name = str(system or platform.system()).strip().casefold()
    arch = normalize_architecture(machine or platform.machine())

    if system_name == "linux":
        if arch != "x86_64":
            raise ValueError("The initial Linux binary target is x86_64 only")
        return "linux-x86_64"
    if system_name == "windows":
        if arch != "x86_64":
            raise ValueError("The initial Windows binary target is x86_64 only")
        return "windows-x86_64"
    if system_name == "darwin":
        return "macos-arm64" if arch == "arm64" else "macos-x86_64"
    raise ValueError(f"Unsupported CLI operating system: {system or platform.system()!r}")


def executable_name(target: BinaryTarget) -> str:
    """Return the installed command filename for a target."""
    return "derridai.exe" if target.startswith("windows-") else "derridai"


def release_artifact_name(target: BinaryTarget) -> str:
    """Return the stable per-release asset filename.

    The Git tag carries the version, so a stable asset name lets the installer use
    the GitHub releases/latest/download path without querying the API.
    """
    suffix = ".exe" if target.startswith("windows-") else ""
    return f"derridai-{target}{suffix}"


def sha256_file(path: str | Path) -> str:
    """Hash a built artifact without reading it all into memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
