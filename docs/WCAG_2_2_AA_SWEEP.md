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

This document records the October 2026 WCAG 2.2 AA sweep of the DerridAI web application. The sweep covers the routed Vue application, shared UI primitives, Corpus Builder surfaces, relation/semantic-map interactions, authentication, the published-site UI, Storybook accessibility coverage, and Playwright accessibility tests.

The changes in this sweep are intentionally limited to fixes that have low or effectively zero product impact. Items that require substantial interaction redesign, route-wide manual validation, or broad layout changes are retained below as explicit follow-up work.

This is an engineering compliance sweep, not a third-party accessibility certification. Automated axe checks are necessary but cannot establish every WCAG success criterion on their own.

## Remediations completed in this sweep

- [x] **WCAG 2.1.1 / 2.5.7 — keyboard alternatives for pointer interactions:** Search result columns can now be resized with Left/Right Arrow keys as well as pointer dragging, with a larger Shift-modified step.
- [x] **WCAG 2.5.7 — dragging movements:** the movable Record popout can now be repositioned with Arrow keys from its header instead of requiring dragging.
- [x] **WCAG 2.4.3 / modal keyboard behavior:** the movable Record popout contains Tab focus and restores focus to the invoking control when it closes.
- [x] **WCAG 2.4.3 / modal keyboard behavior:** the bulk metadata editor contains Tab focus and restores focus to the invoking control when it closes.
- [x] **WCAG 2.5.8 — target size:** legacy `.btn.tiny` controls now have a minimum 24×24 CSS-pixel target, including operation-dock tiny actions.
- [x] **WCAG 2.5.8 — target size:** Run Guidance removable cue buttons are now 24×24 CSS pixels.
- [x] Added regression coverage for keyboard Search column resizing, bulk-editor focus containment, and Run Guidance target size.

The repository already has broad axe coverage using WCAG 2.0/2.1/2.2 A/AA tags across routed views, Storybook surfaces, Corpus Builder states, Help, Operations, Records, Works, Compare, metadata schemas, progressive-loading states, and the published static site. Those checks remain part of the baseline but do not replace the manual criteria below.

## Deferred WCAG TODOs

These items are intentionally not folded into this low-impact sweep because they require larger UX changes, route-wide visual verification, or assistive-technology testing.

| Priority | Criterion | Area | TODO |
| --- | --- | --- | --- |
| P1 | **2.5.7 Dragging Movements** | `DocumentStructureConfigurator.vue` / `DocumentLayoutRegionLayer.vue` | Adding a new document layout region is still a drag-to-draw interaction. Existing regions can be moved/resized from the keyboard, but creation needs a non-drag alternative. Add an “add region” flow that creates a default rectangle or exposes numeric bounds, then supports keyboard refinement. |
| P1 | **2.4.11 Focus Not Obscured (Minimum)** | shell, operation dock, sticky headers/footers, drawers, Focus Review, dialogs | Run a route-complete keyboard traversal with every fixed/sticky surface open. Guarantee that focused controls are never fully hidden by the top bar, operation dock, sticky action bars, drawers, or viewport edges. Add browser tests for the regressions found. |
| P1 | **1.4.10 Reflow / 1.4.12 Text Spacing** | all substantive routes and dialogs | Expand the current representative checks to every routed workflow at 320 CSS px equivalent and with WCAG text-spacing overrides (line height 1.5, paragraph spacing 2× font size, letter spacing 0.12em, word spacing 0.16em). Fix clipping/overlap only where the expanded sweep finds it. |
| P1 | **2.5.8 Target Size (Minimum)** | SVG/graph nodes and bespoke compact controls | Add rendered-hitbox tests for relation maps, semantic maps, compact icon controls, and any nonstandard clickable SVG/group target. Either provide a 24×24 target, satisfy the spacing exception, or document the applicable exception. |
| P2 | **1.4.11 Non-text Contrast / forced colors** | semantic maps, relation graphs, custom status marks, focus indicators | Perform a manual high-contrast/forced-colors pass on custom SVG and canvas-like surfaces. Token and axe coverage cannot fully prove boundary/focus contrast for every graph state. Add forced-colors stories/tests for failures found. |
| P2 | **3.3.7 Redundant Entry** | Corpus Builder, capture/import, administration | Review multi-step workflows for information the user is asked to enter twice in the same process. Reuse or offer previously supplied values unless re-entry is essential, security-sensitive, or used to confirm data. |
| P2 | **3.3.8 Accessible Authentication (Minimum)** | `AuthScreen.vue` and deployment auth configuration | Verify password-manager fill, paste, browser autofill, and any deployed MFA/identity-provider flow. The in-repo username/password form uses appropriate autocomplete tokens and no cognitive-function challenge, but deployment-specific authentication must be tested before claiming full conformance. |
| P2 | **3.2.6 Consistent Help** | application shell and contextual help | Verify that Help access remains in a consistent relative location across every supported route, modal workspace, and narrow-screen shell state. The Help Center coverage is broad, but this criterion needs route-level consistency review rather than content coverage alone. |
| P2 | **4.1.2 / 4.1.3 and related screen-reader behavior** | complex dialogs, live status, relation/semantic surfaces | Complete NVDA + Firefox/Chrome and VoiceOver + Safari passes for accessible names, state changes, live-region verbosity, modal boundaries, graph navigation, and focus return. Automated accessibility trees do not establish the usability of these interactions. |

## Exit criteria for claiming 100% WCAG 2.2 AA

Do not describe the web application as fully WCAG 2.2 AA conformant until the P1/P2 items above have been completed or explicitly demonstrated to satisfy an applicable WCAG exception, and the following evidence is retained:

1. All configured axe/WCAG 2.2 AA suites pass in light and dark themes.
2. Route-complete keyboard-only traversal passes without traps, unreachable actions, or obscured focus.
3. Every substantive route passes 320 CSS px reflow and WCAG text-spacing checks.
4. Dragging functionality has a non-drag alternative unless the dragging movement is essential.
5. Rendered pointer targets satisfy 2.5.8 or a documented exception.
6. Authentication and redundant-entry criteria are verified against the deployed workflow, not only component markup.
7. At least one Windows screen-reader/browser combination and VoiceOver/Safari complete the primary research, search, corpus-review, administration, and publication workflows.
