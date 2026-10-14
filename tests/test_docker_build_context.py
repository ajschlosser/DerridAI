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

"""Regression coverage for Docker build-context hygiene."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    """Read a repository file as UTF-8 text."""
    return (ROOT / path).read_text(encoding="utf-8")


def test_git_metadata_is_not_a_docker_build_context() -> None:
    """Builds must not transfer the repository's .git object database to BuildKit."""
    compose = read("docker-compose.yml")
    assert "gitmeta" not in compose
    assert "./.git" not in compose

    for path in ("api/Dockerfile", "web/Dockerfile"):
        dockerfile = read(path)
        assert "from=gitmeta" not in dockerfile
        assert "ARG GIT_COMMIT=" in dockerfile


def test_git_commit_build_stamp_is_host_supplied() -> None:
    """Compose may pass a commit stamp without requiring Git metadata in the image build."""
    compose = read("docker-compose.yml")
    assert compose.count("GIT_COMMIT: ${GIT_COMMIT:-}") == 2

    env_example = read(".env.example")
    assert 'export GIT_COMMIT="$(git rev-parse --short HEAD)"' in env_example
