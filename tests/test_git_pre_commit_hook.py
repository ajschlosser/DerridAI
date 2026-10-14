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

"""Staged quality checks cover every file without oversized native invocations."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def hook_repo(tmp_path):
    bash = shutil.which("bash")
    git = shutil.which("git")
    if bash is None or git is None:
        pytest.skip("pre-commit integration requires Bash and Git")
    subprocess.run([git, "init", "--quiet", str(tmp_path)], check=True, capture_output=True)
    hook = tmp_path / ".githooks" / "pre-commit"
    hook.parent.mkdir()
    hook.write_bytes((ROOT / ".githooks" / "pre-commit").read_bytes())
    log = tmp_path / "checks.jsonl"
    recorder = tmp_path / "record_checks.py"
    recorder.write_text(
        """import json
import os
import sys

tool = sys.argv[1]
args = sys.argv[2:]
with open(os.environ["HOOK_TEST_LOG"], "a", encoding="utf-8") as output:
    output.write(json.dumps({"tool": tool, "args": args, "cwd": os.getcwd()}) + "\\n")
if tool == "eslint" and "src/api/graphql/generated.ts" in args and "--no-warn-ignored" not in args:
    sys.exit(1)
if tool == os.environ.get("HOOK_TEST_FAIL_TOOL") and (
    tool == "copyright" or os.environ.get("HOOK_TEST_FAIL_PATH") in args
):
    sys.exit(23)
""",
        encoding="utf-8",
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for relative, tool in [
        ("bin/hook-python", "copyright"),
        ("bin/ruff", "ruff"),
        ("web/node_modules/.bin/prettier", "prettier"),
        ("web/node_modules/.bin/eslint", "eslint"),
    ]:
        executable = tmp_path / relative
        executable.parent.mkdir(parents=True, exist_ok=True)
        executable.write_text(
            '#!/usr/bin/env bash\n'
            f'exec python "$HOOK_TEST_RECORDER" {tool} "$@"\n',
            encoding="utf-8",
        )
        executable.chmod(0o755)
    env = {
        **os.environ,
        "PYTHON": "hook-python",
        "PATH": os.pathsep.join([str(bin_dir), str(Path(sys.executable).parent), os.environ["PATH"]]),
        "HOOK_TEST_RECORDER": str(recorder),
        "HOOK_TEST_LOG": str(log),
        "DERRIDAI_SKIP_PREFLIGHT": "",
    }

    def stage(paths):
        for relative in paths:
            path = tmp_path / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture\n", encoding="utf-8")
        if paths:
            subprocess.run(
                [git, "add", "--", "docs", "api", "web/src"],
                cwd=tmp_path, check=True, capture_output=True,
            )

    def run(**overrides):
        result = subprocess.run(
            [bash, ".githooks/pre-commit"], cwd=tmp_path,
            env={**env, **overrides}, capture_output=True, text=True, timeout=60,
        )
        checks = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
        return result, checks

    return tmp_path, stage, run


def staged_paths():
    directory = "long-staged-path-" + "x" * 40
    return sorted(
        f"{prefix}/{directory}/record {index:03d} [review].{extension}"
        for prefix, extension in [("docs", "md"), ("api/app", "py"), ("web/src", "ts")]
        for index in range(97)
    )


def tool_files(checks, tool):
    prefix = {
        "prettier": ["--check", "--config", "web/.prettierrc", "--ignore-path", ".prettierignore", "--ignore-unknown"],
        "ruff": ["check"],
        "eslint": ["--max-warnings", "0", "--no-warn-ignored"],
    }[tool]
    batches = [check for check in checks if check["tool"] == tool]
    files = []
    for check in batches:
        assert check["args"][:len(prefix)] == prefix
        batch = check["args"][len(prefix):]
        assert 1 <= len(batch) <= 32
        files.extend(batch)
    return files, batches


def test_large_staged_set_checks_every_file_in_bounded_batches(hook_repo):
    root, stage, run = hook_repo
    paths = staged_paths()
    stage(paths)
    result, checks = run()
    assert result.returncode == 0, result.stdout + result.stderr
    assert checks[0]["tool"] == "copyright"
    expected = {
        "prettier": [path for path in paths if path.endswith((".md", ".ts"))],
        "ruff": [path for path in paths if path.endswith(".py")],
        "eslint": [path.removeprefix("web/") for path in paths if path.endswith(".ts")],
    }
    for tool, expected_paths in expected.items():
        files, batches = tool_files(checks, tool)
        assert files == expected_paths
        assert len(batches) > 1
        assert all(Path(check["cwd"]) == (root / "web" if tool == "eslint" else root) for check in batches)


@pytest.mark.parametrize("tool", ["copyright", "prettier", "ruff", "eslint"])
def test_failed_check_blocks_later_batches_and_tools(hook_repo, tool):
    _root, stage, run = hook_repo
    paths = staged_paths()
    stage(paths)
    selected = {
        "copyright": [".githooks/copyright_headers.py"],
        "prettier": [path for path in paths if path.endswith((".md", ".ts"))],
        "ruff": [path for path in paths if path.endswith(".py")],
        "eslint": [path.removeprefix("web/") for path in paths if path.endswith(".ts")],
    }[tool]
    failed_path = selected[40] if tool != "copyright" else selected[0]
    result, checks = run(HOOK_TEST_FAIL_TOOL=tool, HOOK_TEST_FAIL_PATH=failed_path)
    assert result.returncode == 23, result.stdout + result.stderr
    assert checks[-1]["tool"] == tool
    if tool != "copyright":
        _files, batches = tool_files(checks, tool)
        assert len(batches) == 2
        assert failed_path in batches[-1]["args"]


def test_no_staged_files_skips_quality_tools(hook_repo):
    _root, _stage, run = hook_repo
    result, checks = run()
    assert result.returncode == 0, result.stdout + result.stderr
    assert [check["tool"] for check in checks] == ["copyright"]


def test_intentionally_ignored_eslint_file_does_not_create_warning_failure(hook_repo):
    _root, stage, run = hook_repo
    stage(["docs/fixture.md", "api/app/fixture.py", "web/src/api/graphql/generated.ts"])
    result, checks = run()
    assert result.returncode == 0, result.stdout + result.stderr
    files, _batches = tool_files(checks, "eslint")
    assert files == ["src/api/graphql/generated.ts"]
