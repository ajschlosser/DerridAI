#!/bin/sh
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

# Point this repository (and all its worktrees) at the tracked hooks in .githooks/.
set -eu
cd "$(git rev-parse --show-toplevel)"
chmod +x .githooks/* scripts/preflight.sh
git config core.hooksPath .githooks
echo "Git hooks enabled: pre-commit applies copyright headers and checks staged files; pre-push runs scripts/preflight.sh"
