# Corpus Builder concurrency, topology, and early-manifest UX

- Status: in progress
- Branch: `ux/corpus-builder-concurrency-setup-manifest`
- Scope: setup policy, build/review live-state presentation, realtime corpus summaries, and manifest timing.

## Objectives

1. Make the UI correct when several Records are enriching concurrently.
2. Let setup express explicit SourceUnit → Record → Page relationships instead of treating those as unrelated knobs.
3. Make the document manifest visible and editable before a build starts, so reviewer corrections influence segmentation and enrichment rather than arriving after them.
4. Keep the existing Setup / Build / Review / Publish workflow hierarchy and preserve authoritative backend state.

## Planned work

### Concurrency-safe processing

- Carry the bounded `metadata_active_tasks` list over the realtime corpus-build summary, not only aggregate running counts.
- Reconcile several active Record IDs at once in the queue and Build handoff.
- Present concurrent active work as a collection, never as one implied "current Record".
- Keep queued `preparing` work distinct from actively **Enriching** work.
- Preserve selection/focus when concurrent completions update queue membership.

### SourceUnit → Record → Page policy

Add an explicit topology relationship policy to the build request:

- `semantic`: current semantic segmentation and Record-size policy.
- `source_units`: deterministic Records made from a fixed number of SourceUnits.
- `source_units_per_record`: defaults to 1 when fixed-unit mode is selected.
- `records_per_page`: optional synthetic pagination grouping for sources whose pages are estimated/undefined.

The setup UI should make the common relationships legible, including:

- 1 SourceUnit = 1 Record
- N SourceUnits = 1 Record
- 1 Record = 1 synthetic Page
- N Records = 1 synthetic Page

Real/printed source pagination remains authoritative and is never silently replaced by synthetic pagination.

### Early editable manifest

- Reuse the full `DocumentManifestEditor` during Setup > Metadata.
- Seed it from deterministic ingest metadata.
- Store reviewer edits in the pre-build `document_metadata` request.
- Hide post-build-only controls such as reanalysis while editing the setup draft.
- Continue to use the same manifest contract after the build starts.

### Interaction consistency

- Normalize loading/empty/error affordances touched by this work.
- Preserve keyboard focus/selection across concurrent Record updates.
- Keep primary/secondary action hierarchy consistent with the prior Corpus Builder UX passes.
- Add unit, backend, Storybook/browser, and accessibility regressions.

## Design decisions

- Concurrency is represented by Record IDs, not only a count. Aggregate counts are useful for throughput; IDs are required to render the correct queue rows as active.
- Fixed SourceUnit grouping is deterministic and bypasses semantic boundary generation by design. It is an explicit user topology choice, not a hint.
- `records_per_page` only creates synthetic Record page labels when the source does not have authoritative pagination. It does not rewrite PDF/printed page evidence.
- The setup manifest is a draft of reviewer-supplied document metadata. Deterministic ingest values remain visible as the baseline; only reviewer changes are sent as overrides.
- Existing record-size controls remain available for semantic mode and as safety limits. Fixed-unit mode owns the primary Record boundary policy.

## Progress

- [x] Confirmed PR #404 is merged.
- [x] Audited Setup, source-unit policy, Record sizing, build lifecycle, realtime corpus summaries, queue processing states, and manifest workflow.
- [x] Created implementation branch and design log.
- [ ] Add realtime active-task identities for concurrent enrichment.
- [ ] Add fixed SourceUnit-to-Record topology policy to API and backend construction.
- [ ] Add optional Records-per-Page synthetic grouping for unpaginated/estimated sources.
- [ ] Add Setup topology relationship controls.
- [ ] Surface the full editable manifest before Build.
- [ ] Add interaction/focus resilience around concurrent queue updates.
- [ ] Add regression coverage and run quality gates.
- [ ] Record final validation and follow-up work.

## Non-goals

- Changing provider-side concurrency scheduling or task locking.
- Treating synthetic pages as physical PDF pages.
- Removing semantic segmentation; it remains the default.
- Automatically accepting Records because they were deterministically grouped.
