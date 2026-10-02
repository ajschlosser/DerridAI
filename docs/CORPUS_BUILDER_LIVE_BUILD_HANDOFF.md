# Corpus Builder live-build handoff UX

- Status: validation in progress
- Branch: `ux/corpus-builder-live-build-handoff`
- Scope: Corpus Builder Build workspace only; no backend workflow or persistence changes.

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
- During progressive enrichment, show record-level operational counts together: Ready for review, Enriching, Preparing, and Needs attention.
- Make Review the primary handoff as soon as reviewable Records exist; keep Pause/Cancel secondary.
- Keep publication readiness as the next action after automated processing settles.
- Treat manifest review, segmentation review, stopped builds, and other intervention states as actionable exceptions.
- Move the event timeline and technical diagnostics into a secondary Run details disclosure.
- Preserve all existing backend stages, queue semantics, pause/cancel/resume behavior, and review routing.
- Validate responsive layout, keyboard access, reduced-motion behavior, Storybook, unit tests, browser E2E, legacy regressions, and accessibility.

## Design notes

- Progressive enrichment is not a blocking monolithic job. The UI should expose useful Records as they become reviewable.
- Backend `preparing` means a Record is waiting for enrichment. Only Records named in `metadata_active_tasks` are actively processing. The queue therefore keeps queued Records as **Preparing** with the original refresh icon and uses the animated **Enriching** treatment only for active Records.
- Queue counts are preferable to inferred percentages for the handoff: `ready`, `preparing`, and `issues` directly describe what the reviewer can act on.
- Activity history is evidence, not the current state. It belongs below the primary operational surface.
- Diagnostics are valuable for troubleshooting but should not compete with the next task during a healthy build.
- Warning/error notices remain visible outside Run details because they can require action.

## Progress

- [x] Confirmed PR #403 is merged and the Review remediation/spinner work is on `master`.
- [x] Audited the current Build workspace, primary status, activity timeline, workflow-presentation domain, and existing tests.
- [x] Created this implementation branch and design log.
- [x] Added progressive record counts to the primary status.
- [x] Rebalanced Build actions around progressive Review handoff.
- [x] Collapsed activity and diagnostics into secondary Run details.
- [x] Extended unit, Storybook, and E2E coverage.
- [x] Corrected processing semantics: only active task Records are Enriching; queued Records remain Preparing with the original icon.
- [ ] Clear the final formatting gate on the documentation-only closeout commit.
- [ ] Record final green validation here.

## Implementation notes

- The primary status now receives queue-derived `ready`, queued `preparing`, active `enriching`, and `issues` counts from the same lifecycle/build state already used by Review.
- Active enrichment is counted by unique Record IDs in `metadata_active_tasks`; queued Preparing is the review `preparing` count minus those active Records.
- During enrichment/retry stages, those counts replace the less useful single "running tasks" fact with four record-level handoff states.
- Review moves ahead of Pause/Cancel in action order and becomes primary when either clean-ready or attention-required Records are available.
- The existing diagnostics root is reused as the **Run details** disclosure. `CorpusBuildActivity` is mounted inside it through an activity slot, so event history is not rendered until the user asks for operational detail.
- Warnings, failures, manifest gates, retry state, and segmentation intervention remain outside Run details because they can require immediate action.
- The existing stage rail and overall build progress remain in the canonical primary status; no second progress surface was introduced.
- A dedicated progressive-enrichment Storybook fixture now represents the full Build workspace, not only the status card.

## Validation notes

- Initial CI static/type failure: one updated unit test used `await` in a non-async callback. The callback was corrected; product code was unchanged.
- Next CI unit failure: the attention-only handoff test asserted the generic class `primary`, while the shared `UiButton` contract uses `variant-primary`. The assertion was corrected; the Review button was already rendering the intended primary variant.
- Processing semantics were refined so queued backend `preparing` Records remain **Preparing** with the existing refresh icon; only Record IDs present in `metadata_active_tasks` render as **Enriching** with an animated spinner.
- On head `8fa81073576c12a3b27ac8c687e1a14e68b96779`, lint, static/type checks, production build, both unit shards, both E2E shards, both legacy regression shards, the dedicated accessibility sweep, and all product behavior checks passed.
- That run failed only `format-check` because this Markdown file was not Prettier-normalized. This document update is the formatting-only correction.

## Active-processing coverage

The processing semantics are covered at unit, Storybook/browser, and accessibility levels:

- queued backend `preparing` Record → **Preparing**, original refresh icon, no animation
- Record present in `metadata_active_tasks` → **Enriching**, animated spinner
- Build handoff → separate Ready / Enriching / Preparing / Needs attention counts

## Non-goals

- Changing enrichment scheduling, concurrency, retry behavior, or queue calculation.
- Changing corpus publication-readiness rules.
- Adding new backend states or API fields.
- Redesigning the Review or Publish workspaces again in this PR.

## Follow-up

The next UX pass should be cross-cutting rather than another workspace rewrite: keyboard shortcuts, selection/focus persistence, normalized loading/empty/error states, narrow-screen behavior, and consistency of action placement across Setup, Build, Review, and Publish.
