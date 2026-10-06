<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.
-->

# Progressive loading UX progress

Checkpoint: 2026-10-06.

## Current state

The workspace-by-workspace progressive-loading audit is complete. The authoritative detailed record is [PROGRESSIVE_LOADING_UX_PLAN.md](PROGRESSIVE_LOADING_UX_PLAN.md); the corresponding navigation work is tracked in [CORPUS_BUILDER_NAVIGATION_PLAN.md](CORPUS_BUILDER_NAVIGATION_PLAN.md).

Every route surface is now classified. Independently useful server-data regions own their first-read, retained-refresh, changed-identity, and failure states. Changed resource identities do not silently inherit old rows, record text, evidence, schema drafts, source facts, or PDF page labels. Long-running mutations and jobs remain separate from read hydration.

The remaining aggregate dependencies are intentional: authentication/authorization may gate the authorized application shell; Pipeline Studio requires its definition catalog as structural vocabulary; Roles keeps roles/capabilities/account assignments atomic for membership-sensitive mutations. Semantic Map, Help, and initial Provider state are synchronous/local and therefore do not need artificial network loading states. Settings keeps asynchronous audio and pipeline reads local to their sections.

The final Corpus Builder/Source Explorer check binds PDF preview accessibility metadata, captions, and source-box overlays to the page that actually finished rendering rather than the page merely requested.

## Validation

Historical focused validation for Works, Record, Vector Stores, Search, Research, Response Library, Records, Annotations, Languages, Relationships, Users/Roles, Metadata Memory, Operations, Compare, System Data, Pipeline Studio, Sources, and Metadata Schemas is recorded in the detailed plan. Those checks include synthetic delayed reads, same-resource refresh failures, changed-identity races, authorization loss, request counts, retained DOM/drafts, narrow layouts, reduced motion, localization, Storybook/build/type checks, and WCAG scans where documented.

The completion branch adds a focused PDF evidence-viewer regression for requested-page versus rendered-page identity. Repository CI is the final merge gate for this branch. Synthetic readiness checks demonstrate behavior; they are not a production-latency benchmark or a claim of measured speedup.

Known accessibility exceptions explicitly recorded in historical checkpoints remain separate product debt; the progressive-loading work does not hide or disable those findings.

## Resume

No further workspace-loading boundary is queued. If CI finds a regression, fix the failing contract on the completion branch. Otherwise the audit is ready to merge. Future work should treat new loading boundaries as ordinary feature requirements rather than reopening this migration wholesale.
