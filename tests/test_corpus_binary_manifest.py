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

"""Binary artifact naming and checksum contract tests."""

from __future__ import annotations

import hashlib

import pytest
from app.corpus_binary_manifest import (
    executable_name,
    normalize_architecture,
    release_artifact_name,
    sha256_file,
    target_key,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("x86_64", "x86_64"),
        ("AMD64", "x86_64"),
        ("x64", "x86_64"),
        ("arm64", "arm64"),
        ("aarch64", "arm64"),
    ],
)
def test_architecture_names_are_normalized(raw, expected):
    assert normalize_architecture(raw) == expected


@pytest.mark.parametrize(
    ("system", "machine", "expected"),
    [
        ("Linux", "x86_64", "linux-x86_64"),
        ("Windows", "AMD64", "windows-x86_64"),
        ("Darwin", "arm64", "macos-arm64"),
        ("Darwin", "x86_64", "macos-x86_64"),
    ],
)
def test_supported_targets_have_stable_release_keys(system, machine, expected):
    assert target_key(system=system, machine=machine) == expected


def test_initial_linux_target_rejects_arm64():
    with pytest.raises(ValueError, match="Linux binary target is x86_64"):
        target_key(system="Linux", machine="arm64")


def test_release_artifact_names_match_installed_platform_conventions():
    assert release_artifact_name("linux-x86_64") == "derridai-linux-x86_64"
    assert release_artifact_name("macos-arm64") == "derridai-macos-arm64"
    assert release_artifact_name("windows-x86_64") == "derridai-windows-x86_64.exe"
    assert executable_name("windows-x86_64") == "derridai.exe"
    assert executable_name("macos-arm64") == "derridai"


def test_sha256_file_streams_the_exact_artifact_bytes(tmp_path):
    artifact = tmp_path / "derridai"
    payload = b"native-binary-fixture\x00\x01"
    artifact.write_bytes(payload)

    assert sha256_file(artifact) == hashlib.sha256(payload).hexdigest()
