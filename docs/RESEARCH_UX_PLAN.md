<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
# Research workspace UX redesign: implementation plan

The Research page (`web/src/views/ResearchView.vue`) works, but it is laid out
like a form followed by a report, not like a place where research happens.
This plan describes the problems and the target design, and splits the work
into phases that can each ship and be reviewed on their own.

## What is wrong today

1. **Evidence gets a narrow column.** `.research-workspace-grid` gives the
   answer `2.15fr` and the evidence `0.85fr` (310px at ≤1100px). The passage
   text, which is the thing a scholar actually reads to check a claim, is
   13px serif in a strip roughly 300px wide, under a 250px scrolling index.
2. **The inspector puts details before the passage.** In
   `ResearchEvidencePanel.vue` the order is: tag and work, then the attribution
   grid, then the passage, then citation and scores. The passage and its full
   citation should come first, with attribution right beside them. Rerank
   scores and topics are diagnostics.
3. **Runs ("threads") are hidden.** Past runs are only reachable through the
   "Runs" button in the composer, which opens a modal drawer. The pipeline bar
   shows only *active* runs. Going back and forth between two answers takes
   three clicks each way and covers the page.
4. **The composer always comes first.** When you open a finished run, the
   full composer (question, instructions, four context selectors, footer)
   sits above the answer, and the view scrolls past it with `scrollIntoView`.
   Reviewing a run and asking a new question are separate tasks but share the
   same vertical stack.
5. **Run identity is thin.** The answer header shows provider, model and time,
   but not the collection, the retrieval preset, whether the result is cached,
   or how many evidence records were cited versus retrieved. These are in the
   footer or the runs drawer.
6. **Citation to evidence is one way.** Inline citations open the evidence
   item, but the evidence item does not show where the answer cites it.

## Design principles

- **Evidence is a first-class reading surface**, not a sidebar. It gets at
  least as much width as the answer on wide screens.
- **Most important first:** passage → full citation (work, pages) → speaker /
  position holder / stance → diagnostics. Keep the provenance fields
  (`speaker`, `quoted_speaker`, `position_holder`) separate and labeled; never
  merge them.
- **Threads are always in view.** A persistent run list lets you switch
  answers in one click and keeps the URL (`/rag?job=`) as the address of a
  thread.
- **Separate asking from reviewing.** The composer collapses to a single
  question bar while a run is open, and expands on focus or when you choose
  "New question".
- Keep all current behavior: permissions, polling, evidence-only preset,
  researcher text restrictions, locale parity, keyboard access, tokens.

## Target layout (≥1280px)

```
┌ header: title · database count · pinned evidence ─────────────────────────┐
│ [ question bar (collapsed composer)                     ][Run][Settings] │
├──────────────┬───────────────────────────────┬────────────────────────────┤
│ Threads      │ Answer                        │ Evidence                   │
│ ● running…   │ question (h2)                 │ [E1][E2][E3]… tabs/strip   │
│ ✓ question A │ collection · preset · model   │ passage text (readable)    │
│ ✓ question B │ warnings                      │ Work, pp. 12–13 (citation) │
│ …            │ prose with citations          │ speaker · position · stance│
│ View all     │ footer actions                │ ▸ diagnostics              │
└──────────────┴───────────────────────────────┴────────────────────────────┘
```

- 1100–1280px: the thread rail collapses to icon-and-status width or moves
  above the answer as a horizontal strip; answer and evidence split 1:1.
- <1100px: single column; evidence follows the answer, the index becomes a
  horizontal strip, and choosing a citation scrolls to the passage.

## Phases

### Phase 1: evidence first (done)

- Change the answer/evidence grid to `minmax(0,1.25fr) minmax(380px,1fr)`,
  and stack the two below 1100px instead of squeezing evidence to 310px.
- Reorder the inspector: passage, full citation and pages, attribution
  (speaker, quoted speaker, position holder, stance, proposition status,
  discourse role, target), then a collapsed **Retrieval details** disclosure
  for collection, rerank score, topics and concepts.
- Passage text at the reading size (15px serif, 1.7 line height).
- Show which answer passages cite the active evidence item ("Cited 3× in the
  answer").
- Tests: Vitest component test for ordering, the cited count and the
  disclosure; update the e2e DOM baselines.

### Phase 2: thread rail (done)

- New `ResearchThreadList.vue`: a persistent list of retained runs (active
  first, then most recent), with status, collection and relative time. It
  reuses `researchJobDetail`, and for roles without `rag.jobs.own` it shows
  only the session jobs `ResearchView` already tracks.
- Selecting a thread uses `openJob` and also updates `/rag?job=<id>` with
  `router.replace`, so the URL can be shared and reloaded.
- The existing pipeline bar becomes the "running" group at the top of the
  rail; the runs drawer stays as "View all / manage" for remove and
  diagnostics.
- Keyboard: arrow keys between threads (roving tabindex), Enter to open.

### Phase 3: compact composer (done)

- While a run is open, the composer shows the question on one line, a summary
  (corpus, profile, retrieval preset, pinned evidence), **More options** and
  **Research**. The question can be edited and run from there. More options
  expands the full composer, and opening or starting a run collapses it
  again. **New question** in the thread list clears the open run.
- Ctrl/Cmd+Enter runs from the question field in both states.
- Removed the `scrollIntoView` calls that only skipped past the composer
  (on run, on opening a thread, and on loading `?job=`). The mobile jump to
  evidence and the New question focus are kept.
- Phase 2 note: the thread rail sits beside the answer from 1440px (not
  1280px), and the answer/evidence split stacks using a container query
  when its own width drops below 820px.

### Phase 4: run summary header (done)

- Under the question, the answer header shows a row of labeled chips:
  corpus (or "Evidence only"), retrieval preset, "N cited of M" evidence,
  provider and model, elapsed time, and Cached. A chip is left out when the
  run did not record that value; the preset is inferred from the run's own
  request (`job.request` or `result.rag_request`), never from the current
  composer settings.
- "Cited" counts evidence items whose deterministic `inline_citation`
  appears in the answer text.
- Copy, Analyze & grade, Re-run and Run details sit together in the header
  toolbar; the old footer is gone.
- Preset inference moved to `components/research/researchPreset.ts`, shared
  by the view, composer and answer header.

### Phase 5: polish and docs (done)

- Two-way highlighting: the active evidence item's citations are highlighted
  in the answer, and hovering or focusing an item in the evidence list
  previews its citations.
- `tests/e2e/research-theme-sweep.spec.ts` runs axe (WCAG 2.2 AA) over every
  Research story in light and dark.
- Research DOM baselines regenerated; the runs-drawer baseline now opens the
  drawer from the thread list.
- `docs/USER_GUIDE.md` describes the new layout.
- Release note: not written. 0.70.0 is already tagged, so this work needs a
  new version, and that is the release owner's call.

## Follow-ups

- The compact question shows the draft question, not the open thread's
  question; consider an explicit "Ask a follow-up" affordance.
- `ResearchPipelineBar.vue` is no longer used by the view; remove it and its
  story once nothing else needs it.

## Non-goals

- No backend or API contract changes are needed for phases 1–4.
- No change to how citations are matched (`inline_citation` from
  deterministic code).
