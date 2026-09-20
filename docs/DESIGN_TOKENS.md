<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# Design tokens

Components take colours, type sizes and status styling from tokens, not literals. That is what lets one stylesheet serve light, dark, increased-contrast and forced-colors modes. The tokens live in two places:

- `web/src/style.css` defines the neutrals (`--bg`, `--card`, `--soft`, `--text`, `--muted`, `--line`, `--line-strong`) and the accent family (`--ui-accent*`), with their dark values under `html[data-color-scheme="dark"]`.
- `web/src/styles/tokens.css` defines everything built on top of them, described below.

## Colour

| Token                                  | Use                                                                                                    |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `--text`, `--text-2`, `--muted`        | Primary, secondary and tertiary text. `--text-2` sits between the other two.                           |
| `--card`, `--soft`, `--surface-raised` | Surfaces, from the page card to a raised panel.                                                        |
| `--line`, `--line-strong`              | Hairlines and stronger dividers.                                                                       |
| `--tone-{info,ok,warn,danger}-fg`      | Text and icons for a status. At least 4.5:1 on its own tint and on the surface.                        |
| `--tone-*-bg`                          | The tint behind a status.                                                                              |
| `--tone-*-border`                      | The outline of a control or badge that carries a status. At least 3:1 on the surface.                  |
| `--tone-*-edge`                        | A softer outline for a large container (a card or panel) that carries a status.                        |
| `--accent-fg`                          | The accent as text or an icon. Never use `--accent` for text: it is a fill and fails on dark surfaces. |
| `--accent-on`                          | Text (and knockout shapes) placed on a solid accent fill.                                              |
| `--ui-accent`, `--ui-accent-soft`      | The accent as a fill, and a tint of it. Both follow the chosen accent theme and the colour scheme.     |

Pick the token by what the colour means, not by how it looks. A warning card uses `--tone-warn-*` even if a neutral would be close, so it stays a warning in every mode.

## Type, space, elevation, motion

Sizes are `rem` so they follow the reader's font-size setting: `--fs-xs` (12px, the floor) up to `--fs-2xl`, with `--lh-*` line heights, `--fw-*` weights, `--font-ui`, `--font-reading` for record text and `--measure` for a comfortable line length. Spacing is `--space-1` to `--space-9`, radii are `--radius-*`, shadows are `--elev-1` to `--elev-3`, and motion is `--motion-fast`, `--motion-base` and `--ease-standard`. `prefers-reduced-motion` is honoured globally in `style.css`.

## Modes

- **Dark**: `html[data-color-scheme="dark"]` (set from the user's preference or the system).
- **Increased contrast**: `html[data-contrast="more"]` makes tone outlines take the text colour.
- **Forced colors**: `@media (forced-colors: active)` maps outlines to `CanvasText` and the focus ring to `Highlight`. Structure has to come from borders and text, so give status elements a border.

## Rules

1. Do not write a hex colour in a component or in `style.css`. Use a token, or add one to `tokens.css` with a test. `web/tests/frontend/design-token-usage.test.ts` fails if the number of literals goes up.
2. Do not fall back to a literal in `var(--x, #fff)`; the fallback is what shows when the token is missing, and it is always the light one.
3. Do not dim text with `opacity`. It lowers the contrast of everything inside; use a token for the muted state.
4. Anything that must stay the same in every mode (a status dot, a solid brand fill) may keep a literal, which is why the ratchet is not zero.

## Checking a change

```bash
cd web
npx vitest run tests/frontend/design-tokens.test.ts   # every tone and accent pair against WCAG
npm run test:e2e -- tests/e2e/corpus-builder-theme-sweep.spec.ts   # every Corpus Builder story, light and dark
```

`design-tokens.test.ts` reads the CSS itself, so changing a token value that breaks contrast fails there before it ships. The sweep runs axe over every Corpus Builder story in both colour schemes. Axe cannot judge text over a gradient or image, so also look at a changed screen in dark mode.

## Migrating old styles

`scripts/migrate-css-tokens.py` rewrites literal colours and `px` font sizes in CSS and Vue styles to these tokens. It reads each declaration with its selector, so a tint inside a `.risk`, `.warn`, `.error` or `.ok` rule becomes that tone, near-black text stays neutral text, and pale outlines stay hairlines. It is a dry run unless you pass `--apply`:

```bash
python3 scripts/migrate-css-tokens.py web/src/components/Foo.vue          # show what would change
python3 scripts/migrate-css-tokens.py --apply web/src/components/Foo.vue  # write it
```

It is a heuristic: it does not touch `rgba()`, `hsl()`, opacity, shadows, dark or saturated fills, or the fallback inside a `var()`, and it reports what it left. Review the diff, then check the result in dark as well as light. `tests/test_migrate_css_tokens.py` pins the mappings that earlier versions got wrong.
