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

"""Local push hooks preserve browser opt-in without changing CI policy."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("browser", [None, "1"])
def test_push_hook_preserves_explicit_browser_policy(tmp_path: Path, browser: str | None) -> None:
    shell = shutil.which("sh")
    git = shutil.which("git")
    if shell is None or git is None:
        pytest.skip("The repository's shell hook requires sh and git.")
    root = tmp_path / "repo"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    preflight = scripts / "preflight.sh"
    preflight.write_text(
        '#!/bin/sh\nprintf "%s" "${DERRIDAI_PREFLIGHT_BROWSER-unset}" > "$POLICY_TEST_OUTPUT"\n',
        encoding="utf-8",
    )
    preflight.chmod(0o755)
    output = tmp_path / "policy"
    env = {
        **os.environ,
        "POLICY_TEST_OUTPUT": str(output),
    }
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(name, None)
    env.pop("DERRIDAI_SKIP_PREFLIGHT", None)
    env.pop("DERRIDAI_PREFLIGHT_BROWSER", None)
    if browser is not None:
        env["DERRIDAI_PREFLIGHT_BROWSER"] = browser
    subprocess.run([git, "init", "--quiet", str(root)], env=env, check=True, timeout=10)
    hook = Path(__file__).resolve().parents[1] / ".githooks" / "pre-push"
    result = subprocess.run(
        [shell, str(hook)],
        input="refs/heads/test abcdef refs/heads/test 000000\n",
        text=True,
        capture_output=True,
        env=env,
        cwd=root,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert output.read_text(encoding="utf-8") == (browser or "unset")
