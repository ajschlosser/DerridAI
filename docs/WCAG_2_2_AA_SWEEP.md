<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

# WCAG 2.2 AA Web Application Sweep

This document records the October 2026 WCAG 2.2 AA engineering sweep of the
DerridAI web application.

The sweep covers the routed Vue application, shared UI primitives, Corpus
Builder surfaces, relation and semantic-map interactions, authentication,
the published-site UI, Storybook accessibility coverage, and Playwright
accessibility tests.

This sweep intentionally lands only fixes with low or effectively zero product
impact. Work that needs broader interaction redesign, route-wide visual
verification, or assistive-technology testing is retained below as explicit
follow-up work.

This is an engineering compliance sweep, not a third-party accessibility
certification. Automated axe checks are necessary but cannot establish every
WCAG success criterion on their own.

## Remediations completed in this sweep

- [x] **WCAG 2.1.1 / 2.5.7:** Search result columns can be resized with Left
  and Right Arrow keys as well as pointer dragging. Shift uses a larger step.
- [x] **WCAG 2.5.7:** the movable Record popout can be repositioned with Arrow
  keys from its header instead of requiring dragging.
- [x] **WCAG 2.4.3:** the movable Record popout contains Tab focus and restores
  focus to the invoking control when it closes.
- [x] **WCAG 2.4.3:** the bulk metadata editor contains Tab focus and restores
  focus to the invoking control when it closes.
- [x] **WCAG 2.5.8:** legacy `.btn.tiny` controls now have a minimum
  24×24 CSS-pixel target, including operation-dock tiny actions.
- [x] **WCAG 2.5.8:** Run Guidance removable cue buttons are now
  24×24 CSS pixels.
- [x] Added regression coverage for keyboard Search column resizing,
  bulk-editor focus containment, and Run Guidance target size.

The repository already has broad axe coverage using WCAG 2.0, 2.1, and 2.2
A/AA tags across routed views, Storybook surfaces, Corpus Builder states, Help,
Operations, Records, Works, Compare, metadata schemas, progressive-loading
states, and the published static site.

Those checks remain part of the baseline but do not replace the manual criteria
below.

## Deferred WCAG TODOs

### P1 — 2.5.7 Dragging Movements

Files:

- `DocumentStructureConfigurator.vue`
- `DocumentLayoutRegionLayer.vue`

Adding a new document layout region is still a drag-to-draw interaction.
Existing regions can be moved and resized from the keyboard, but creation needs
a non-drag alternative.

TODO:

- Add an "add region" flow that creates a default rectangle or exposes numeric
  bounds.
- Keep keyboard refinement available after creation.

### P1 — 2.4.11 Focus Not Obscured (Minimum)

Areas:

- application shell
- operation dock
- sticky headers and footers
- drawers
- Focus Review
- dialogs

TODO:

- Run route-complete keyboard traversal with every fixed or sticky surface open.
- Verify focused controls are never fully hidden by overlays or viewport edges.
- Add browser regression tests for failures found.

### P1 — 1.4.10 Reflow / 1.4.12 Text Spacing

TODO:

- Expand the current representative checks to every substantive routed workflow.
- Test 320 CSS px equivalent width.
- Apply WCAG text-spacing overrides:
  - line height 1.5
  - paragraph spacing 2× font size
  - letter spacing 0.12em
  - word spacing 0.16em
- Fix clipping or overlap found by the expanded sweep.

### P1 — 2.5.8 Target Size (Minimum)

Areas:

- relation maps
- semantic maps
- bespoke compact icon controls
- nonstandard clickable SVG or grouped targets

TODO:

- Add rendered-hitbox tests.
- Provide a 24×24 target where needed.
- Otherwise satisfy the spacing exception or document the applicable exception.

### P2 — 1.4.11 Non-text Contrast and forced colors

TODO:

- Perform a manual high-contrast and forced-colors pass on custom SVG and
  canvas-like surfaces.
- Verify graph boundaries, focus indicators, status marks, and selection states.
- Add forced-colors stories or tests for failures found.

### P2 — 3.3.7 Redundant Entry

Areas:

- Corpus Builder
- capture and import
- administrative workflows

TODO:

- Review multi-step workflows for information entered more than once.
- Reuse or offer previously supplied values unless re-entry is essential,
  security-sensitive, or used to confirm data.

### P2 — 3.3.8 Accessible Authentication (Minimum)

File:

- `AuthScreen.vue`

TODO:

- Verify password-manager fill, paste, and browser autofill.
- Verify any deployment-specific MFA or identity-provider flow.

The in-repo username/password form uses appropriate autocomplete tokens and no
cognitive-function challenge, but deployment-specific authentication must be
tested before claiming full conformance.

### P2 — 3.2.6 Consistent Help

TODO:

- Verify Help access remains in a consistent relative location across every
  supported route, modal workspace, and narrow-screen shell state.

The Help Center coverage is broad, but this criterion needs route-level
consistency review rather than content coverage alone.

### P2 — screen-reader behavior

Criteria include 4.1.2, 4.1.3, and related interaction requirements.

TODO:

- Complete NVDA plus Firefox or Chrome passes.
- Complete VoiceOver plus Safari passes.
- Verify accessible names, state changes, live-region verbosity, modal
  boundaries, graph navigation, and focus return.

## Exit criteria for claiming 100% WCAG 2.2 AA

Do not describe the web application as fully WCAG 2.2 AA conformant until the
P1 and P2 items above have been completed or explicitly demonstrated to satisfy
an applicable WCAG exception.

Retain evidence that:

1. All configured axe/WCAG 2.2 AA suites pass in light and dark themes.
2. Route-complete keyboard-only traversal passes without traps, unreachable
   actions, or obscured focus.
3. Every substantive route passes 320 CSS px reflow and WCAG text-spacing
   checks.
4. Dragging functionality has a non-drag alternative unless dragging is
   essential.
5. Rendered pointer targets satisfy 2.5.8 or a documented exception.
6. Authentication and redundant-entry criteria are verified against the
   deployed workflow, not only component markup.
7. At least one Windows screen-reader/browser combination and VoiceOver/Safari
   complete the primary research, search, corpus-review, administration, and
   publication workflows.
