#!/bin/sh
# Copyright 2026 Aaron John Schlosser, PhD.
#
# Pre-push preflight: catches the failures that most often turn CI red on agent-authored
# branches. Run it by hand (`scripts/preflight.sh`) or let `.githooks/pre-push` run it.
# Set DERRIDAI_SKIP_PREFLIGHT=1 to bypass (CI will still enforce everything).
set -u

ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT" || exit 1
BASE_REF=${DERRIDAI_BASE_REF:-origin/master}
fail=0
say() { printf 'preflight: %s\n' "$*" >&2; }

git fetch -q origin master 2>/dev/null || say "could not fetch origin/master; freshness check skipped"
if ! git rev-parse -q --verify "$BASE_REF" >/dev/null; then
  say "no $BASE_REF; nothing to compare against"
  exit 0
fi
MERGE_BASE=$(git merge-base HEAD "$BASE_REF")
CHANGED=$(git diff --name-only --diff-filter=d "$MERGE_BASE" HEAD)

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
if [ -x "$PRETTIER" ]; then
  unformatted=$(printf '%s\n' "$CHANGED" | grep -vE '^$' | tr '\n' '\0' |
    xargs -0 --no-run-if-empty "$PRETTIER" --list-different --config web/.prettierrc \
      --ignore-path .prettierignore --ignore-unknown 2>/dev/null || true)
  if [ -n "$unformatted" ]; then
    say "Prettier would reformat these files (run: web/node_modules/.bin/prettier --write <file>):"
    printf '%s\n' "$unformatted" | head -20 >&2
    fail=1
  fi
else
  say "web/node_modules missing; Prettier check skipped (run npm ci in web/)"
fi

# 4. Generated artifacts must match their generators. Regenerate with the repo's own
#    scripts and toolchain, never by hand and never from another environment.
if printf '%s\n' "$CHANGED" | grep -qE '^(api/app/(graphql|celf_queries|pipelines)/|web/src/api/graphql/|web/src/components/pipelines/fixtures/|scripts/export_)'; then
  PY=${PYTHON:-python}
  if PYTHONPATH=api "$PY" -m pytest -q tests/test_graphql_schema_artifact.py tests/test_pipeline_catalog_fixture.py >/dev/null 2>&1; then
    :
  else
    say "generated artifacts are stale: run scripts/export_graphql_schema.py and scripts/export_pipeline_catalog_fixture.py"
    fail=1
  fi
fi

# 5. Lint and types for frontend changes.
if printf '%s\n' "$CHANGED" | grep -qE '^web/(src|tests|sdk)/'; then
  if [ -x web/node_modules/.bin/eslint ]; then
    files=$(printf '%s\n' "$CHANGED" | grep -E '^web/(src|tests)/.*\.(ts|js|vue)$' | sed 's#^web/##' || true)
    if [ -n "$files" ]; then
      # shellcheck disable=SC2086
      (cd web && ./node_modules/.bin/eslint --max-warnings 0 $files >/dev/null 2>&1) || {
        say "eslint reports problems; run: cd web && npx eslint --max-warnings 0 <files>"
        fail=1
      }
    fi
  fi
fi

# 6. Legacy DOM baselines: if a ported dialog changed, the baseline guard must still pass.
if printf '%s\n' "$CHANGED" | grep -qE '^web/(src/domain|tests/e2e/legacy-dom)'; then
  (cd web && node scripts/check-legacy-snapshots.mjs >/dev/null 2>&1) || {
    say "legacy snapshot ownership guard fails: run 'cd web && npm run check:legacy-snapshots'"
    fail=1
  }
fi

[ "$fail" -eq 0 ] && say "ok"
exit "$fail"
