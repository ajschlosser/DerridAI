# Corpus Builder live-build handoff UX

Status: in progress  
Branch: `ux/corpus-builder-live-build-handoff`  
Scope: Corpus Builder Build workspace only; no backend workflow or persistence changes.

## Objective

Make an active corpus build understandable at a glance and support progressive review while enrichment continues.

The Build workspace should answer, in order:

1. What is happening now?
2. How much useful work is already available?
3. What needs intervention?
4. What can I do next?
5. Where can I inspect operational detail if I need it?

## Planned changes

- Keep `CorpusBuildPrimaryStatus` as the canonical live-build state instead of adding another status card.
- During progressive enrichment, show record-level operational counts together: Ready for review, Enriching, and Needs attention.
- Make Review the primary handoff as soon as reviewable Records exist; keep Pause/Cancel secondary.
- Keep publication readiness as the next action after automated processing settles.
- Treat manifest review, segmentation review, stopped builds, and other intervention states as actionable exceptions.
- Move the event timeline and technical diagnostics into a secondary Run details disclosure.
- Preserve all existing backend stages, queue semantics, pause/cancel/resume behavior, and review routing.
- Validate responsive layout, keyboard access, reduced-motion behavior, Storybook, unit tests, browser E2E, legacy regressions, and accessibility.

## Design notes

- Progressive enrichment is not a blocking monolithic job. The UI should expose useful Records as they become reviewable.
- The record queue already distinguishes backend `preparing` rows as **Enriching** with a spinner. Build-level language should use the same mental model.
- Queue counts are preferable to inferred percentages for the handoff: `ready`, `preparing`, and `issues` directly describe what the reviewer can act on.
- Activity history is evidence, not the current state. It belongs below the primary operational surface.
- Diagnostics are valuable for troubleshooting but should not compete with the next task during a healthy build.
- Warning/error notices remain visible outside Run details because they can require action.

## Progress

- [x] Confirmed PR #403 is merged and the Review remediation/spinner work is on `master`.
- [x] Audited the current Build workspace, primary status, activity timeline, workflow-presentation domain, and existing tests.
- [x] Created this implementation branch and design log.
- [ ] Add progressive record counts to the primary status.
- [ ] Rebalance Build actions around progressive Review handoff.
- [ ] Collapse activity and diagnostics into secondary Run details.
- [ ] Extend unit/Storybook/E2E coverage.
- [ ] Run and fix all frontend quality gates.
- [ ] Record final validation and remaining follow-up work here.

## Non-goals

- Changing enrichment scheduling, concurrency, retry behavior, or queue calculation.
- Changing corpus publication-readiness rules.
- Adding new backend states or API fields.
- Redesigning the Review or Publish workspaces again in this PR.
