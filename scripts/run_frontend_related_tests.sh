#!/usr/bin/env bash
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

# Run only frontend unit tests that are directly changed or related to changed app sources.
set -euo pipefail

ROOT=$(git rev-parse --show-toplevel)
BASE_REF=${1:-origin/master}
HEAD_REF=${2:-HEAD}
cd "$ROOT"

if ! git rev-parse -q --verify "$BASE_REF" >/dev/null; then
  echo "frontend-related-tests: base $BASE_REF is unavailable; running the full unit suite" >&2
  (cd web && npm run test:unit)
  exit $?
fi

mapfile -t CHANGED < <(git diff --name-only --diff-filter=ACMRTUXB "$BASE_REF" "$HEAD_REF")
FULL=false
for path in "${CHANGED[@]}"; do
  case "$path" in
    web/package.json|web/package-lock.json|web/vitest.config.ts|web/tests/frontend/setup.ts|web/tsconfig.tests.json)
      FULL=true
      ;;
  esac
done

if [ "$FULL" = true ]; then
  echo "frontend-related-tests: test infrastructure changed; running the full unit suite" >&2
  (cd web && npm run test:unit)
  exit $?
fi

tests=()
sources=()
for path in "${CHANGED[@]}"; do
  case "$path" in
    web/tests/frontend/*.test.ts|web/tests/frontend/**/*.test.ts)
      tests+=("${path#web/}")
      ;;
    web/src/*.ts|web/src/*.vue|web/src/*.js|web/src/**/*.ts|web/src/**/*.vue|web/src/**/*.js)
      case "$path" in
        *.stories.ts|*.stories.js) ;;
        *) sources+=("${path#web/}") ;;
      esac
      ;;
    web/sdk/*.ts|web/sdk/**/*.ts)
      sources+=("${path#web/}")
      ;;
  esac
done

if [ "${#tests[@]}" -eq 0 ] && [ "${#sources[@]}" -eq 0 ]; then
  echo "frontend-related-tests: no unit-test-owned files changed" >&2
  exit 0
fi

cd web
if [ "${#tests[@]}" -gt 0 ]; then
  echo "frontend-related-tests: running ${#tests[@]} directly changed test file(s)" >&2
  npx vitest run --passWithNoTests "${tests[@]}"
fi

if [ "${#sources[@]}" -gt 0 ]; then
  echo "frontend-related-tests: resolving tests related to ${#sources[@]} changed source file(s)" >&2
  npx vitest related --run --passWithNoTests "${sources[@]}"
fi
