# Settings Overview Refactor

Status: In progress  
Branch: `task/settings-overview-refactor`  
Baseline: `master@c4b30fdb310a5606ae0d40b897b74326211aa4ac`  
Started: 2026-10-02

## Purpose

The System Settings experience has accumulated personal preferences, research defaults, retrieval engineering, provider status, infrastructure services, data-retention policy, backup/recovery, troubleshooting controls, and irreversible workspace destruction at roughly the same conceptual level. The result is technically navigable but unnecessarily difficult to scan, understand, and relate to the larger DerridAI workspace.

This refactor turns Settings into a coherent control plane organized by user intent. Settings should own defaults, policies, integration configuration, and preferences; dedicated workspaces should continue to own entities and operational workflows.

The implementation must preserve current role/capability behavior, persistence semantics, deep links, validation, unsaved-change protection, localization, and accessibility while reducing cognitive load and duplication.

## Product principles

1. **Task-oriented information architecture.** Organize by what the user is trying to configure, not by backend subsystem.
2. **Settings own defaults and policies.** Providers, Users/Roles, Languages, System Data, and corpus/vector-store workspaces remain the canonical places to manage their entities and operations.
3. **Progressive disclosure.** Advanced controls may collapse, but errors, uncertainty, authority, unsaved state, and consequential status must remain visible at the decision point.
4. **Explicit scope.** Prefer human-readable scopes such as “This browser,” “Workspace default,” “System-wide,” “Managed elsewhere,” and “Read only” over implementation-oriented persistence labels.
5. **Explain consequences.** Consequential settings should state what changes, whether existing/derived state becomes stale, whether the action is reversible, and whether authoritative research state is affected.
6. **Flatten ordinary forms.** Do not render every group as a visually equal card. Reserve cards for genuinely distinct objects/status summaries.
7. **Canonical navigation semantics.** Route-backed Settings categories should use links/navigation semantics rather than tab semantics.
8. **Search must be complete.** Every configurable setting or managed destination should come from a shared registry and be deep-linkable.
9. **Local status, not decorative status.** Save/progress/error state belongs next to the controls it describes. Avoid a permanent global “Saved” badge when several persistence domains exist.
10. **Danger is isolated.** Irreversible workspace destruction must live in a dedicated danger zone, separate from routine preferences and recovery actions.

## Target information architecture

### Overview

The default Settings landing page. It should answer:

- What can I configure?
- Is anything currently wrong or requiring attention?
- Where do I go for related management workspaces?

Overview should use compact category navigation surfaces with limited live context, not large decorative dashboard cards. Only actionable/exceptional states should be emphasized.

### Preferences

- Appearance
- Interface language
- Accessibility
- Desktop notifications
- Viewer/interface behavior

### Research & review

- Research output defaults
- Default provider profile for review
- Review preset
- Foreground/background run mode
- Evaluation/auto-grade defaults

### Retrieval & indexing

- Embedding provider/model
- Embedding connectivity
- Retrieval strategy
- Reranking
- Evidence budget
- Document language/retrieval scope
- Advanced retrieval tuning

### AI & language services

- Provider health summary with link to Providers
- Audio transcription service
- Document NLP language/resource packs

### Data & storage

- Canonical-vs-operational state explanation
- Retention policy
- Storage/system-data relationships
- Backup and restore

### Access & permissions

- Concise summary/gateway
- Links to Users and Roles
- Do not duplicate entity management already owned by those workspaces

### Troubleshooting & recovery

- Interface reset/recovery actions
- Upsert-suppression recovery
- Update/local-history cleanup where applicable
- Danger zone / start-from-scratch operation

## Migration map

| Existing surface | Target |
| --- | --- |
| Workspace → Appearance | Preferences → Appearance |
| Workspace → About DerridAI | Overview footer/product information |
| Language & accessibility → Interface language | Preferences → Language & accessibility |
| Contrast | Preferences → Accessibility |
| Manage Languages | Contextual link to Languages workspace |
| Research defaults → Response language | Research & review → Research output defaults |
| Review & AI behavior → provider/preset/run mode | Research & review → Review execution |
| Auto-grade cached answers | Research & review → Evaluation defaults |
| Providers & models summary | AI & language services → Provider status |
| Audio transcription | AI & language services → Audio transcription |
| Embedding provider/model/path/test | Retrieval & indexing → Embeddings |
| RAG k/automatic sizing/top-N/reranker | Retrieval & indexing → Retrieval strategy |
| Evidence character budgets | Retrieval & indexing → Evidence budget |
| Document languages/retrieval routes | Retrieval & indexing → Retrieval scope |
| fetch_k/MMR/RRF/cross-encoder/decomposition | Retrieval & indexing → Advanced retrieval |
| Security/users/permissions | Access & permissions |
| NLP language packs | AI & language services → Document NLP resources |
| Data retention | Data & storage → Retention |
| Backup & restore | Data & storage → Backup & restore |
| Desktop notifications | Preferences → Notifications |
| Reset columns/panels/sidebar | Troubleshooting & recovery → Interface reset |
| Restore upsert suppressions | Troubleshooting & recovery |
| Clear update history | Troubleshooting & recovery |
| Start from scratch / NUKE | Troubleshooting & recovery → Danger zone |

## Interaction and layout direction

### Overview

Use a compact grid/list of destinations such as Preferences, Research & review, Retrieval & indexing, AI & language services, Data & storage, Access & permissions, and Troubleshooting & recovery. Each item should contain a concise description and, when useful, one or two live facts.

Examples of useful live context:

- current review provider and preset;
- embedding provider/model and reachability;
- provider/audio/NLP services requiring attention;
- retention policy summary;
- links to Users/Roles for administrators.

Do not visually emphasize normal “saved” or “read only” state.

### Category pages

Use a flatter structure:

`Page heading → subsection heading → setting rows/groups → actions/dividers`

Normal setting rows should contain:

- label;
- short explanation;
- optional scope/effect metadata;
- control;
- validation/status at the same decision point.

Limit ordinary form width to a readable control-plane width rather than stretching controls across the full application viewport.

### Navigation

Settings categories are canonical routes. Use actual navigation links with `aria-current="page"`, conventional browser behavior, and stable deep links.

On narrow screens, replace the desktop rail with a labeled accessible category control/drawer rather than merely hiding navigation.

### Search and settings registry

Replace the manually duplicated settings search index with a declarative registry from which navigation, overview metadata, search, breadcrumbs, and deep-link targets can derive.

A registry entry should be able to declare:

- stable id;
- category;
- subsection;
- localized title/help keys;
- keywords/synonyms;
- required role/capability;
- scope/persistence;
- risk level;
- target route/anchor;
- advanced state;
- managed-elsewhere destination when applicable.

Search selection should navigate to the exact destination, open advanced disclosure when necessary, and focus/highlight the relevant setting without unexpected focus theft.

### Save behavior

- Remove the always-visible global “Saved” state from the header.
- Show `Unsaved changes`, `Saving…`, `Saved`, and `Save failed` locally.
- Preserve drafts on validation/persistence failures.
- Preserve leave-page protection.
- Use a sticky action bar only while an explicit-save form is dirty.
- Keep immediate settings immediate only where intentional and clearly explained.

### Retrieval and indexing

Organize parameters conceptually:

- Candidate retrieval
- Reranking
- Evidence budget
- Language and route scope
- Advanced tuning

Advanced retrieval remains progressively disclosed, but deep links/search must open it automatically.

### Data retention

Present the policy in this order:

1. What is always kept/canonical.
2. What retention manages/operational.
3. Current system-wide policy.
4. Store-specific overrides.
5. Estimated effect of applying the saved policy.
6. Apply/reclaim actions with explicit consequences.

The UI must preserve DerridAI/cELF’s distinction between authoritative documentary/scholarly state and rebuildable/operational computational state.

### Danger zone

Move the workspace-destruction flow into a visually and semantically isolated danger zone. Explain:

- exactly what is destroyed;
- what remains;
- whether backup can reverse it;
- which persisted scopes are affected;
- irreversibility after confirmation.

Typed confirmation remains appropriate.

## Engineering direction

`SettingsView.vue` is large enough that the UX refactor should also decompose the implementation.

Prefer:

- a small Settings route shell;
- category views/components;
- a declarative settings registry;
- reusable `SettingRow` / settings-group primitives only where they remove meaningful duplication;
- presentation separated from persistence/domain logic;
- existing dedicated components such as retention/NLP packs retained and improved rather than duplicated.

All new visible copy must use localization keys/defaults. Maintain en-US/fr-CA parity.

## Accessibility and quality gates

The refactor must preserve or improve:

- WCAG 2.2 AA target;
- keyboard-only operation;
- visible focus;
- screen-reader labels/relationships;
- status not communicated by color alone;
- reduced-motion behavior;
- forced-colors/high-contrast support;
- light/dark themes;
- narrow-screen/reflow usability;
- text-spacing tolerance;
- fr-CA and long-string layouts;
- correct loading/error/empty/unavailable distinctions;
- sensitive state excluded from shareable URLs;
- capability/role visibility;
- unsaved-draft behavior.

## Acceptance criteria

- `/settings` lands on a useful Overview.
- Ordinary settings are reachable from Overview within at most two navigation decisions.
- Every registered setting/destination is searchable and deep-linkable.
- Route-backed categories use navigation/link semantics.
- Personal/browser, workspace-default, system-wide, read-only, and managed-elsewhere scopes are understandable without backend terminology.
- Dedicated workspaces are linked rather than duplicated.
- Retrieval controls are grouped by conceptual effect.
- Retention clearly distinguishes canonical and operational state.
- Destructive workspace reset is isolated in a danger zone.
- Existing role/capability behavior is preserved.
- Existing validation, failure, and unsaved-change guarantees remain intact.
- Settings implementation is decomposed enough that no new monolithic replacement is introduced.
- Storybook/component/E2E coverage is added or updated for the new primitives and responsive states.
- CI passes.

## Progress tracker

Legend: `[ ]` not started, `[~]` in progress, `[x]` complete.

### Phase 0 — Baseline and planning

- [x] Review current Settings implementation and supporting components.
- [x] Review routing, search registry, retention, NLP-pack, and existing Settings tests.
- [x] Review project UX/accessibility requirements relevant to navigation/progressive disclosure.
- [x] Create this implementation plan and progress tracker.
- [x] Create branch `task/settings-overview-refactor`.

### Phase 1 — Registry, routing, and shell

- [x] Design/implement declarative task-oriented Settings category registry.
- [x] Add Overview category and canonical `/settings/overview`.
- [x] Redirect bare `/settings` to Overview while preserving/canonicalizing old section deep links.
- [x] Convert category rail from tab semantics to ordinary navigation-link semantics.
- [x] Make role visibility registry-driven.
- [~] Unify category/search metadata completely; field-level search still has its own registry alongside category metadata.
- [x] Add exact route/anchor handling for search results, including automatic opening of advanced retrieval.
- [x] Update routing/settings-domain test definitions for the new routes and aliases.

### Phase 2 — Overview

- [x] Implement Settings Overview.
- [x] Add compact category navigation surfaces.
- [x] Add useful live context for research/review, retrieval, and provider/service readiness without decorative normal-state badges.
- [x] Move About/build information to Overview.
- [x] Add responsive behavior, researcher/admin variants, and Storybook/WCAG story coverage.

### Phase 3 — Preferences

- [x] Move appearance into Preferences.
- [x] Move interface language and contrast/accessibility into Preferences.
- [x] Move desktop notifications into Preferences; keep reset/recovery controls out of preferences.
- [~] Rework scope labels and save behavior; normal saved/read-only badges are suppressed and scopes are human-facing, but dirty-state action affordances can still be improved.
- [x] Preserve researcher access and existing browser persistence semantics.

### Phase 4 — Research & review

- [x] Consolidate response language and review execution defaults under Research & review.
- [x] Separate evaluation defaults from review execution.
- [~] Clarify downstream effects and persistence scope; hierarchy is improved, but additional consequence copy remains useful.

### Phase 5 — Retrieval & indexing

- [x] Separate Embeddings, Retrieval strategy, Evidence budget, Retrieval scope, and Advanced tuning conceptually.
- [x] Preserve the existing embedding persistence/health-test implementation while moving it into the new category.
- [x] Improve advanced-control deep linking/search with exact control anchors.
- [x] Preserve existing validation/draft behavior in the implementation and regression tests.

### Phase 6 — AI & language services

- [x] Move provider summary/gateway.
- [x] Move audio transcription.
- [x] Move NLP language packs.
- [x] Keep Provider and Language entity management in their dedicated workspaces.

### Phase 7 — Data & storage

- [x] Move retention into Data & storage.
- [x] Make the canonical-vs-operational retention boundary permanently visible.
- [~] Improve policy summary/override/effect hierarchy; the canonical boundary is improved, while the dense override table still needs a final UX pass.
- [x] Move backup/restore.
- [x] Add explicit links to System Data and Corpus Data rather than duplicating those workspaces.

### Phase 8 — Access, troubleshooting, danger zone

- [x] Replace Security with an Access & permissions gateway.
- [x] Move UI recovery/reset tools into Troubleshooting & recovery.
- [x] Isolate destructive workspace reset in a dedicated danger zone.
- [~] Add explicit consequence/reversibility copy; the danger zone now points users to backup and retains irreversible-action warnings, with a final copy audit still pending.

### Phase 9 — Decomposition and cleanup

- [~] Decompose `SettingsView.vue`; Overview, navigation/search/section framing, Access, Data & storage, Troubleshooting, and AI & language services are now extracted components. Preferences, Research & review, and Retrieval & indexing still remain in the route view.
- [ ] Remove remaining duplicated field/search metadata by converging on one registry contract.
- [~] Keep domain/persistence logic separate from presentation; registry/domain work is separated, but category state/actions still live in `SettingsView.vue`.
- [x] Point Help coverage/canonical Settings route at Overview.
- [x] Update the User Guide for the new hierarchy and workspace ownership model.

### Phase 10 — Verification

- [ ] Run frontend unit tests.
- [ ] Run Settings E2E.
- [ ] Run keyboard/focus checks.
- [ ] Run axe/WCAG scans.
- [ ] Verify light/dark/high-contrast/forced-colors.
- [ ] Verify reduced motion.
- [ ] Verify mobile/narrow-screen/reflow.
- [ ] Verify fr-CA and long-string coverage.
- [ ] Run full relevant CI.
- [~] Final design/implementation audit against this document is in progress.

## Implementation notes

Record material deviations from this plan here rather than silently changing direction.

- 2026-10-02: Work started from latest `master` at `c4b30fdb310a5606ae0d40b897b74326211aa4ac`.
- 2026-10-02: Existing legacy URLs such as `/settings/workspace`, `/settings/review`, and `/settings/system` are accepted and canonicalized onto the new task-oriented categories instead of being broken.
- 2026-10-02: Settings category and Overview destinations use native link semantics with in-app interception for ordinary clicks. This preserves copy-link/open-in-new-tab behavior and keeps the standalone Storybook stories independent of a router plugin.
- 2026-10-02: Desktop notifications remain administrator-visible, matching the pre-refactor behavior; only their information-architecture location changed.
- 2026-10-02: The permanent/canonical retention boundary is now visible without opening a disclosure so destructive operational-retention controls cannot visually flatten canonical research state into disposable system history.
- 2026-10-02: AI & language services now render through `SettingsServicesPanel.vue`, removing duplicated provider/audio/NLP presentation from `SettingsView.vue` and reducing the route view from roughly 1,900 to roughly 1,775 lines. Category-level extraction remains ongoing.
- 2026-10-02: No local test suite has been executed from the GitHub connector environment. Phase 10 remains explicitly unverified until CI or a runnable checkout is available.
