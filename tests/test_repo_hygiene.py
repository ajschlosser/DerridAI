# Copyright 2026 Aaron John Schlosser, PhD.
"""Build output and caches must never be tracked; they made CI fail on agent branches."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = re.compile(
    r"(^|/)(node_modules|dist|storybook-static|test-results|playwright-report|\.pytest_cache|__pycache__)/"
)


def test_no_build_output_or_caches_are_tracked():
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    offenders = [path for path in tracked if FORBIDDEN.search(path)]
    assert not offenders, f"tracked build output or caches: {offenders[:10]}"
