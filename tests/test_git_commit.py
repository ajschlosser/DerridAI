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

"""The displayed app version can include the git commit that built this process."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.config import app_version_label, resolve_git_commit


def test_app_version_label_includes_release_codename_and_commit():
    assert (
        app_version_label("1.2.3", "abc1234", "Test Release")
        == "1.2.3 - Test Release (abc1234)"
    )
    assert (
        app_version_label("1.2.3", "", "Test Release") == "1.2.3 - Test Release"
    )
    assert app_version_label("1.2.3", "  ", "") == "1.2.3"


def test_git_commit_prefers_environment(monkeypatch):
    monkeypatch.setenv("GIT_COMMIT", "deadbeefcafebabe")
    assert resolve_git_commit() == "deadbeefcafebabe"
    monkeypatch.delenv("GIT_COMMIT")
    monkeypatch.setenv("SOURCE_COMMIT", "abc1234 extra")
    assert resolve_git_commit() == "abc1234"


def test_git_commit_reads_baked_docker_file(monkeypatch, tmp_path: Path):
    baked = tmp_path / "git-commit"
    baked.write_text("cafed00d\n", encoding="utf-8")
    monkeypatch.delenv("GIT_COMMIT", raising=False)
    monkeypatch.delenv("SOURCE_COMMIT", raising=False)
    monkeypatch.setattr("app.config._GIT_COMMIT_FILE", baked)
    assert resolve_git_commit() == "cafed00d"


def test_empty_git_commit_env_does_not_override_baked_file(monkeypatch, tmp_path: Path):
    baked = tmp_path / "git-commit"
    baked.write_text("cafed00d\n", encoding="utf-8")
    monkeypatch.setenv("GIT_COMMIT", "")
    monkeypatch.delenv("SOURCE_COMMIT", raising=False)
    monkeypatch.setattr("app.config._GIT_COMMIT_FILE", baked)
    assert resolve_git_commit() == "cafed00d"
