#!/bin/sh
# Copyright 2026 Aaron John Schlosser, PhD.
# Point this repository (and all its worktrees) at the tracked hooks in .githooks/.
set -eu
cd "$(git rev-parse --show-toplevel)"
chmod +x .githooks/* scripts/preflight.sh
git config core.hooksPath .githooks
echo "Git hooks enabled: pre-push now runs scripts/preflight.sh"
