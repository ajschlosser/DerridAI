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
- Backend `preparing` means a Record is waiting for enrichment. Only Records named in `metadata_active_tasks` are actively processing. The queue therefore keeps queued Records as **Preparing** with the original refresh icon and uses the animated **Enriching** treatment only for active Records.
- Queue counts are preferable to inferred percentages for the handoff: `ready`, `preparing`, and `issues` directly describe what the reviewer can act on.
- Activity history is evidence, not the current state. It belongs below the primary operational surface.
- Diagnostics are valuable for troubleshooting but should not compete with the next task during a healthy build.
- Warning/error notices remain visible outside Run details because they can require action.

## Progress

- [x] Confirmed PR #403 is merged and the Review remediation/spinner work is on `master`.
- [x] Audited the current Build workspace, primary status, activity timeline, workflow-presentation domain, and existing tests.
- [x] Created this implementation branch and design log.
- [x] Add progressive record counts to the primary status.
- [x] Rebalance Build actions around progressive Review handoff.
- [x] Collapse activity and diagnostics into secondary Run details.
- [x] Extend unit/Storybook/E2E coverage.
- [ ] Run and fix all frontend quality gates.
- [x] Correct processing semantics: only active task Records are Enriching; queued Records remain Preparing with the original icon.
- [ ] Record final validation and remaining follow-up work here.

## Implementation notes

- The primary status now receives queue-derived `ready`, queued `preparing`, active `enriching`, and `issues` counts from the same lifecycle/build state already used by Review.
- Active enrichment is counted by unique Record IDs in `metadata_active_tasks`; queued Preparing is the review `preparing` count minus those active Records.
- During enrichment/retry stages, those counts replace the less useful single "running tasks" fact with four record-level handoff states.
- Review moves ahead of Pause/Cancel in action order and becomes primary when either clean-ready or attention-required Records are available.
- The existing diagnostics root is reused as the **Run details** disclosure. `CorpusBuildActivity` is mounted inside it through an activity slot, so event history is not rendered until the user asks for operational detail.
- Warnings, failures, manifest gates, retry state, and segmentation intervention remain outside Run details because they can require immediate action.
- The existing stage rail and overall build progress remain in the canonical primary status; no second progress surface was introduced.
- A dedicated progressive-enrichment Storybook fixture now represents the full Build workspace, not only the status card.

## Non-goals

- Changing enrichment scheduling, concurrency, retry behavior, or queue calculation.
- Changing corpus publication-readiness rules.
- Adding new backend states or API fields.
- Redesigning the Review or Publish workspaces again in this PR.
