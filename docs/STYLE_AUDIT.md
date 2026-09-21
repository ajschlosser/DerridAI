# `web/src/style.css` audit

Scope: how the global stylesheet relates to the Vue components and to the legacy runtime's HTML-string renderers,
and what can be cleaned up safely while the runtime is being decomposed. Numbers come from
`scripts/runtime-refactor/style_audit.py` (static approximation: a class built dynamically is matched by its prefix).

## What it is

| | Before the cleanup | After |
|---|---|---|
| Lines / rules | 5,176 / 3,995 | 4,514 / 3,382 |
| Distinct classes | 1,495 | 1,240 |
| Design tokens (`styles/tokens.css`) | 62 defined, about 2,250 `var(--…)` uses | same |
| Hard-coded colors (243 distinct) | 377 | 343 |
| `!important` | 599 | 545 |
| Selectors defined more than once | 581 | 513 |
| Classes also styled inside a component's `<style scoped>` | 78 | 76 |

It is one global sheet imported in `main.ts` next to `tokens.css`. Vue's usual pattern is component-local
(`<style scoped>`) rules plus shared tokens; 109 of 153 components already do that. The global sheet exists mostly because the
legacy runtime builds HTML strings that cannot carry scoped styles.

## Who uses each class (after removing dead rules)

- **Runtime only, 636 classes.** Used by the legacy string renderers and dialogs (largest groups: `dashboard-*` 68, `rag-*` 42,
  `pdf-*` 40, `record-*` 38, `llm-*` 35, `compare-*` 27, `subset-*` 22, `operation-*` 19, `faq-*` 17). These must stay until
  each renderer is replaced. Some belong to renderers that are no longer reachable from the UI (legacy Record, Compare, FAQ,
  RAG pages; see PROGRESS.md), so they can go together with those renderers.
- **Vue only, 306 classes.** Styled globally but used only by Vue templates (`research-*` 93, `search-*` 86, `vector-*` 35,
  `shell-*` 15, `auth-*` 12, `user-*` 9). These are the mechanical candidates to move into each component's scoped styles.
- **Both, about 200.** The shared vocabulary (`btn`, `badge`, `chip`, `card`, form controls, status colors). These belong in a
  small base layer, not in any component.
- **Unused, 330 before the cleanup (85 remain).** No literal or dynamic-prefix match anywhere in `src` or `index.html`. The
  bulk came from views that were rebuilt in Vue (`vector-*` 61, `provider-*` 30, `researcher-*` 27, `language-*` 21, `dashboard-*`
  19). 613 rules that could never match were removed; the 85 left are kept only because a dynamic-prefix rule makes them
  uncertain.

## Problems worth knowing about

1. **Specificity by force.** 545 `!important` and 70 selectors with three or more combinators show rules fighting each other;
   this is what makes moving a rule risky (its winner may be a different rule).
2. **Duplicated selectors (513).** The same selector is defined in several places, so the effective style depends on source order
   (for example `.work-overview-card`, `.record-annotation-section`, `.filterrow`, `.workflow-steps`, and `:root` itself). Merge
   them when a component is moved, never before.
3. **Two homes for one class (76).** `.btn`, `.chip`, `.annotation-feed*`, `.compare-*` and others are styled both globally and in
   scoped blocks, so a component's look depends on both.
4. **Tokens are used, but colors still leak.** 343 hard-coded colors (243 distinct) sit beside 2,250 token uses, and four
   variables are used but never defined: `--brand-mark-size`, `--operation-dock-progress`, `--operation-stack-max-height`,
   `--panel-soft`. (The first three are set from code at run time; `--panel-soft` looks like a genuine gap.)
5. **Breakpoints are scattered.** More than a dozen different `max-width` values (520 to 1050 px) with several spellings
   (`@media(max-width:720px)` and `@media (max-width: 780px)`).

## How to change it safely

The legacy baseline (`tests/e2e/legacy-dom-baseline.spec.ts`) records computed styles (color, background, border, font,
padding, margin, in light and dark) for the dashboard, PDF Explorer and several dialogs, and the e2e suite runs accessibility
scans over the Storybook stories. A style change is safe when all of these are unchanged:

1. `npx playwright test -c playwright.legacy.config.ts` (computed styles and markup),
2. the full e2e suite (Storybook a11y sweeps, contrast checks) and the Storybook build,
3. no new variables used but undefined, and no rule moved out of source order relative to a rule it overrides.

Recommended order:

1. **Done here:** remove rules that can never match (`style_prune.py`), verified with the checks above.
2. **Vue-only classes into scoped styles**, one view at a time (Research, Search, Vector, shell, auth), keeping class names,
   merging duplicate selectors only inside the moved block, and re-running the checks per view.
3. **Base layer:** extract the shared vocabulary (`btn`, `badge`, `chip`, `card`, forms) into one small file next to
   `tokens.css`, resolving the 76 classes that have two homes.
4. **Renderer replacement:** as each legacy renderer becomes a Vue component, move its runtime-only classes into that
   component's scoped style in the same commit, so the dashboard and dialogs stop depending on the global sheet.
5. **Then** normalise breakpoints and replace hard-coded colors with tokens, and only then chip away at `!important`.
