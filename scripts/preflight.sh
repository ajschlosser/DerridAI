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

#
# Change-aware merge-readiness gate. Run it by hand (`scripts/preflight.sh`) or let
# `.githooks/pre-push` run it. Browser checks are not run locally; CI runs them.
# Set DERRIDAI_SKIP_PREFLIGHT=1 to bypass (CI will still enforce everything).
set -u

ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT" || exit 1
# Hooks can supply a relative GIT_DIR; let Git rediscover this worktree after
# frontend gates change directory, rather than resolving it against web/.
unset GIT_DIR GIT_WORK_TREE
BASE_REF=${DERRIDAI_BASE_REF:-origin/master}
fail=0
say() { printf 'preflight: %s\n' "$*" >&2; }
gate() {
  name=$1
  shift
  say "running $name"
  "$@" || {
    say "$name failed"
    fail=1
  }
}
web_gate() {
  name=$1
  shift
  say "running $name"
  (cd web && "$@") || {
    say "$name failed"
    fail=1
  }
}

git fetch -q origin master 2>/dev/null || say "could not fetch origin/master; freshness check skipped"
if ! git rev-parse -q --verify "$BASE_REF" >/dev/null; then
  say "no $BASE_REF; nothing to compare against"
  exit 0
fi
MERGE_BASE=$(git merge-base HEAD "$BASE_REF")
CHANGED=$(git diff --name-only --diff-filter=d "$MERGE_BASE" HEAD)
PY=${PYTHON:-python}
PLAN=$(printf '%s\n' "$CHANGED" | "$PY" scripts/preflight_plan.py --format shell) || {
  say "could not derive the change-impact plan"
  exit 1
}
eval "$PLAN"

say "plan: backend=$BACKEND frontend=$FRONTEND unit=$FRONTEND_UNIT build=$FRONTEND_BUILD sdk=$SDK storybook=$STORYBOOK e2e=$E2E a11y=$A11Y legacy=$LEGACY contract=$CONTRACT publication=$PUBLICATION"

# 1. Freshness: CI tests the merge with master, so a stale branch is tested against a tree
#    the author never ran.
behind=$(git rev-list --count "HEAD..$BASE_REF")
if [ "$behind" -gt 0 ]; then
  say "branch is $behind commit(s) behind $BASE_REF. Merge or rebase it, then re-run the tests:"
  say "  git merge $BASE_REF"
  fail=1
fi

# 2. Files that must never be committed (build output, caches, dependencies).
bad=$(git diff --name-only --diff-filter=A "$MERGE_BASE" HEAD | grep -E '(^|/)(node_modules|dist|storybook-static|test-results|playwright-report|\.pytest_cache|__pycache__)/' || true)
if [ -n "$bad" ]; then
  say "build output or caches are committed; unstage them (git rm -r --cached <path>):"
  printf '%s\n' "$bad" | head -10 >&2
  fail=1
fi

# 3. Prettier on exactly the files CI checks (changed, supported text formats).
PRETTIER=web/node_modules/.bin/prettier
if [ "$FORMAT" = true ] && [ -x "$PRETTIER" ]; then
  unformatted=$(printf '%s\n' "$CHANGED" | grep -vE '^$' | tr '\n' '\0' |
    xargs -0 --no-run-if-empty "$PRETTIER" --list-different --config web/.prettierrc \
      --ignore-path .prettierignore --ignore-unknown 2>/dev/null || true)
  if [ -n "$unformatted" ]; then
    say "Prettier would reformat these files (run: web/node_modules/.bin/prettier --write <file>):"
    printf '%s\n' "$unformatted" | head -20 >&2
    fail=1
  fi
elif [ "$FORMAT" = true ]; then
  say "web/node_modules missing; cannot run required formatting gate (run: cd web && npm ci)"
  fail=1
fi

# 4. Generated artifacts must match their generators. Regenerate with the repo's own
#    scripts and toolchain, never by hand and never from another environment.
if [ "$GENERATED" = true ]; then
  if PYTHONPATH=api "$PY" -m pytest -q tests/test_graphql_schema_artifact.py tests/test_pipeline_catalog_fixture.py >/dev/null 2>&1; then
    :
  else
    say "generated artifacts are stale: run scripts/export_graphql_schema.py and scripts/export_pipeline_catalog_fixture.py"
    fail=1
  fi
fi

# 5. Backend gates use the same commands as CI, including the full regression suite.
if [ "$BACKEND" = true ]; then
  if command -v ruff >/dev/null 2>&1; then
    gate "backend lint" ruff check api/app tests scripts/check_frontend_api_contract.py scripts/check_frontend_graphql_contract.py
  else
    say "backend lint failed or ruff is missing (install ruff==0.16.8)"
    fail=1
  fi
  if command -v mypy >/dev/null 2>&1; then
    gate "backend types" mypy
  else
    say "backend typecheck failed or mypy is missing (install mypy==2.3.1)"
    fail=1
  fi
  gate "Python syntax" "$PY" -m compileall -q api/app
  gate "backend regression tests" "$PY" -m pytest -q -n auto --dist=worksteal \
    --ignore=tests/test_frontend_api_contract.py \
    --ignore=tests/test_frontend_graphql_contract.py
fi

# 6. Shared REST/GraphQL contracts are their own CI boundary.
if [ "$CONTRACT" = true ]; then
  gate "frontend/backend contract tests" "$PY" -m pytest -q -m contract \
    tests/test_frontend_api_contract.py tests/test_frontend_graphql_contract.py
fi

# 7. Frontend gates are selected by ownership. Expensive browser/catalogue work is not
#    useful when an SDK-only, API-client-only, or test-only change cannot affect those surfaces.
if [ "$FRONTEND" = true ]; then
  if [ ! -x web/node_modules/.bin/eslint ]; then
    say "web/node_modules missing; cannot run required frontend gates (run: cd web && npm ci)"
    fail=1
  else
    web_gate "frontend lint" npm run lint
    web_gate "application typecheck" npm run typecheck:app
    web_gate "test typecheck" npm run typecheck:tests
    if [ "$LEGACY" = true ]; then
      web_gate "legacy snapshot ownership" npm run check:legacy-snapshots
    fi
    if [ "$FRONTEND_UNIT" = true ]; then
      gate "related frontend unit tests" bash scripts/run_frontend_related_tests.sh "$MERGE_BASE" HEAD
    fi
    if [ "$FRONTEND_BUILD" = true ]; then
      web_gate "production app build" npm run build:app:ci
    fi
    if [ "$SDK" = true ]; then
      web_gate "SDK distribution and package checks" npm run build:sdk:ci
    fi
  fi
fi

# 8. Playwright (browser, accessibility and publication acceptance) suites never run locally; CI runs them.
if [ "$STORYBOOK" = true ] || [ "$LEGACY" = true ] || [ "$E2E" = true ] || [ "$A11Y" = true ] || [ "$PUBLICATION" = true ]; then
  say "browser gates are not run locally; CI runs the affected surfaces"
fi

[ "$fail" -eq 0 ] && say "ok"
exit "$fail"
