# Metadata Schemas Refactor

Status: **In progress**  
Branch: `task/metadata-schemas-refactor`  
Primary goal: make Metadata Schemas a coherent, stable schema-authoring workspace while eliminating recurring form-control drift. WCAG 2.2 AA and complete i18n coverage are release requirements, not follow-up work.

## Why this refactor exists

The current Metadata Schemas UI combines several different jobs in one surface: schema-library management, schema identity, field browsing, field editing, document-field policy, prompt-group authoring, preview/testing, persistence state, import/export, and destructive actions. At the field level, a large editor currently expands inside a table row. At the styling level, Metadata Schemas still creates many native `input`, `select`, `textarea`, and checkbox controls directly and then adjusts them with component-local CSS. The application has a shared `UiField` wrapper and specialized controls such as `UiCombobox` and `UiTagPicker`, but it does not yet have a complete ordinary form-control primitive layer.

That combination has produced two recurring failures:

1. visual drift, especially different heights, padding, typography, widths, invalid states, and focus treatments for ordinary controls;
2. cognitive overload, because the user has to infer whether they are selecting a schema, editing a field, configuring prompt behavior, changing document policy, or testing an enrichment contract at any given moment.

This refactor fixes the underlying component and information-architecture problems instead of applying another page-local CSS pass.

## Non-negotiable constraints

- Preserve existing metadata-schema semantics and API contracts unless a change is necessary for accessibility, localization, or a documented correctness issue.
- Preserve stable semantic field identity independently from display labels.
- Preserve built-in schemas as read-only but duplicable.
- Preserve schema versioning, import/export validation, dirty-state behavior, and Ctrl/Cmd+S.
- Preserve the rule that build/run behavior is based on the pinned schema/contract snapshot rather than silently changing when a live schema changes.
- Preserve prompt-group semantics and document-field policy as distinct concepts.
- Preserve URL-safe schema/tab selection while excluding unsaved schema bodies from URL state.
- Use shared semantic design tokens. Do not add literal component colors or per-feature form-control dimensions.
- User-visible application copy must be externalized through the localization system.
- Built-in `en-US` and `fr-CA` dictionaries must remain structurally equivalent with placeholder parity.
- Source text, user-authored schema/prompt content, code identifiers, bibliographic data, and model output are not interface copy and must not be translated merely because the UI locale changes.
- WCAG 2.2 AA compliance is a release gate. Passing axe alone is insufficient.

## Target user workflow

The completed workspace should read clearly as:

1. Choose, create, import, or duplicate a schema.
2. See exactly which schema is being edited, whether it is read-only, and whether it has unsaved changes.
3. Work primarily in **Fields**.
4. Browse/search fields in a navigator.
5. Select a field and configure it in a persistent inspector.
6. Use progressive disclosure for advanced extraction, evidence/review, NLP, matching, and memory/retrieval settings.
7. Configure **Prompt groups / Enrichment groups** separately, with plain-language explanation that a group corresponds to one model evaluation call per record.
8. Configure system-owned **Document fields** separately from user-defined record metadata.
9. **Test schema** against a sample passage.
10. Save from a stable, obvious primary action.

## Implementation plan

### Phase 0 — baseline, branch, and inventory

- Work on `task/metadata-schemas-refactor`, created from the current `master`.
- Record the existing state of:
  - metadata-schema frontend tests;
  - locale dictionary and locale/accessibility floor tests;
  - design-token tests;
  - Storybook build;
  - production web build;
  - relevant Playwright/axe suites.
- Inventory all raw form controls under:
  - `web/src/components/MetadataSchemaEditor.vue`
  - `web/src/components/metadata-schemas/**`
- Inventory existing reusable primitives before adding new ones, especially:
  - `UiField`
  - `UiCombobox`
  - `UiTagPicker`
  - `UiButton`
  - `UiTabs`
  - `UiTooltip`
  - `UiStatusBadge`
  - any existing dialog, disclosure, list, sheet, or workspace primitives.
- Preserve existing test intent while identifying selectors that are coupled to the current expanding-table-row implementation.

### Phase 1 — establish a canonical form-control contract

Create a single ordinary-control styling contract owned by reusable UI primitives rather than Metadata Schemas.

The contract must own:

- control block size;
- horizontal/vertical padding;
- typography;
- border/radius;
- background and foreground surfaces;
- hover/focus/disabled/read-only/invalid states;
- focus ring;
- high-contrast and forced-colors behavior;
- density variants, only if there is a real product need.

Feature components may control layout width, grid position, and responsive arrangement, but they must not redefine the primitive height, padding, border, type scale, focus treatment, or invalid-state treatment.

Do not broadly rewrite legacy global `.control` behavior if that would destabilize unrelated views. It is acceptable to establish the canonical primitive contract and migrate Metadata Schemas first.

### Phase 2 — add missing native-semantic UI primitives

Add thin wrappers around native semantic HTML. Prefer native platform behavior over custom widgets.

Expected primitives:

- `UiInput.vue`
- `UiSelect.vue`
- `UiTextarea.vue`
- `UiCheckbox.vue` or `UiCheckboxField.vue`
- `UiFieldset.vue` only if it removes repeated fieldset/legend/help markup without obscuring semantics.

Requirements for the primitives:

- support `v-model`;
- forward relevant native attributes;
- expose `id`, `name`, `disabled`, `readonly` where applicable, `required`, `aria-invalid`, `aria-describedby`, and autocomplete/input attributes where applicable;
- retain native keyboard behavior;
- use semantic tokens only;
- meet focus-visible and non-text contrast requirements;
- remain usable in dark, increased-contrast, and forced-colors modes;
- remain usable with enlarged text and text-spacing overrides;
- avoid custom selects unless native select is functionally insufficient.

Refactor `UiField.vue` carefully. Its current wrapper-label model is appropriate for one simple native control but is not safe for arbitrary composite widgets with multiple interactive descendants. Add support for explicit control IDs and visible `<label for>` association while preserving compatibility with existing callers where practical.

Update `UiCombobox` and `UiTagPicker` so they can consume explicit labeling/description relationships from `UiField`, including `id`, `aria-labelledby`, `aria-describedby`, invalid state, and disabled state.

### Phase 3 — prevent recurrence

Add regression guards focused on Metadata Schemas:

- fail when ordinary raw text/search/number `input`, `select`, or `textarea` elements are introduced in feature components outside approved primitives;
- permit only documented exceptions such as a hidden file input used for import;
- migrate checkboxes to the shared checkbox primitive where practical;
- fail when Metadata Schemas reintroduces feature-local declarations that override canonical ordinary-control height/padding/border/font behavior.

The purpose is to make the current class of visual regression mechanically difficult to reintroduce.

### Phase 4 — refactor the schema workspace shell

Refactor `MetadataSchemaEditor.vue` so the current schema and save state are always explicit.

The workspace header should make these visible:

- current schema name;
- built-in/read-only vs editable state;
- version;
- saved/unsaved/new state;
- primary Save action.

New, Duplicate, Import, Export, and Delete remain available but should be visually subordinate to the primary edit/save workflow.

The saved-schema selector/library should become a compact, clearly labeled selection surface rather than visually competing with the editor. If its current table is not semantically justified after the new layout, replace it with list/navigation semantics.

Preserve:

- Ctrl/Cmd+S;
- before-unload warning behavior;
- built-in duplication flow;
- route-facing schema and tab selection;
- unsaved-body exclusion from URLs.

### Phase 5 — replace expandable field rows with navigator + inspector

`SchemaFieldsTable.vue` should stop embedding `SchemaFieldForm` inside a table row.

Target behavior:

- left/top field navigator with search/filter;
- clear group headings;
- concise field summaries such as label, type, group, and policy indicators;
- a persistent selected-field inspector on wide layouts;
- stacked navigator then inspector on narrow layouts;
- selected state conveyed semantically and visually, never by color alone.

Prefer semantic list/navigation markup with buttons for selection rather than clickable table rows if the surface is fundamentally a navigator rather than a data table.

Add-field behavior:

- create the field;
- select it;
- focus the first meaningful editable control, normally the label or field-name control depending on semantic constraints;
- preserve focus while typing;
- ensure deletion restores focus to a logical neighbor or Add field action.

### Phase 6 — reorganize the field inspector

Reorganize `SchemaFieldForm.vue` around user intent while preserving serialization and behavior.

Recommended sections:

**Basics**
- label;
- stable/editable key/name;
- type;
- group;
- role;
- scope;
- review visibility.

**Extraction**
- model/extraction instruction;
- controlled values;
- repeatable member structure when applicable.

**Evidence & review**
- evidence requirements;
- confidence/assessment behavior;
- review requirements.

**Linguistic guidance**
- POS hints;
- NER hints.

**Value matching**
- matching mode;
- order sensitivity;
- identity-kind behavior.

**Memory & retrieval**
- reviewed-precedent behavior;
- similarity threshold;
- maximum examples;
- match fields.

Use progressive disclosure for advanced sections, preferably native `details/summary` unless an existing accessible disclosure primitive is already canonical.

Every consequential setting must explain its downstream effect in localized plain language.

Do not silently conflate editable names/labels with stable semantic field identity.

### Phase 7 — clarify the remaining major areas

Keep the main areas distinct and rename/copy them where needed:

- **Fields** — primary workspace.
- **Document fields** — system-owned document/bibliographic policy, clearly not ordinary user-defined record metadata.
- **Prompt groups** or **Enrichment groups** — explain that one group maps to one model evaluation call per record.
- **Test schema** — explain that this validates/runs the current schema configuration against a sample passage.

Do not allow UI simplification to flatten these domain distinctions.

### Phase 8 — complete i18n audit

Every application-authored user-visible string in the changed workflow must be localized, including:

- headings;
- labels;
- buttons;
- placeholders;
- helper text;
- tooltips;
- status text;
- empty states;
- dialogs;
- validation errors;
- live-region announcements;
- screen-reader-only copy;
- generated default names such as copied schemas or new groups;
- count/state messages.

Preserve exact placeholder parity between `en-US` and `fr-CA`.

`useSchemaCopy()` scopes keys under `schemas.*`; generic regex-based tests may not detect every scoped or dynamic key. Add a dedicated schema-i18n test that:

- extracts literal keys passed through `useSchemaCopy`;
- prefixes them with `schemas.`;
- verifies they exist in both canonical dictionaries;
- covers dynamic schema enum keys separately, including field types, roles, visibility states, matching modes, document-field labels, POS/NER terminology, and other generated key families.

Regenerate `web/src/i18n/enUsDefaults.json` through the repository's canonical workflow.

If API validation currently exposes raw English messages as primary UI copy, prefer stable structured error codes/details mapped to locale keys. Do not merely translate arbitrary server exception strings in the client.

### Phase 9 — WCAG 2.2 AA implementation and verification

The completed workflow must satisfy the repository accessibility requirements and applicable WCAG 2.2 AA criteria.

Explicitly verify:

- complete keyboard-only operation;
- logical focus order;
- deterministic focus restoration after add/remove/dialog operations;
- no keyboard traps;
- visible focus in every supported theme;
- focus not obscured by sticky headers/toolbars;
- visible labels and matching programmatic names;
- correct `aria-describedby` and `aria-invalid` relationships;
- fieldset/legend semantics for grouped choices;
- composite control ARIA relationships;
- non-color-only states;
- text and non-text contrast;
- target size requirements or valid documented exceptions;
- narrow reflow to 320 CSS px equivalent;
- text-spacing overrides;
- zoom/enlarged text;
- reduced motion;
- dark mode;
- increased contrast;
- forced colors;
- live announcements for material save/error/status changes without inappropriate focus stealing.

Passing axe is required but not sufficient.

### Phase 10 — responsive behavior

Desktop may use a two-pane field navigator + inspector layout.

Narrow layouts must preserve all capabilities. They may stack or use an accessible drawer/sheet pattern only if that pattern already exists and preserves semantics. Do not hide advanced capabilities solely because the viewport is narrow.

Long French strings, status badges, chips, controlled values, prompt text, and help content must wrap without causing page-level horizontal scrolling.

### Phase 11 — Storybook and focused tests

Add Storybook coverage for all new primitives and representative schema states.

Primitive states should include:

- default;
- required;
- disabled;
- read-only where applicable;
- invalid;
- long label;
- long hint;
- long error;
- French-length copy;
- supported theme/contrast modes.

Metadata-schema stories should include:

- editable schema;
- built-in read-only schema;
- unsaved/new schema;
- empty field list;
- selected ordinary text field;
- choice field;
- repeatable field;
- evidence/review settings;
- matching/memory advanced settings;
- prompt-group editor;
- document-field policy;
- test-schema state.

Update frontend unit tests to assert behavior rather than old table-row DOM structure.

### Phase 12 — dedicated E2E accessibility/regression coverage

Add a Metadata Schemas Playwright suite against the actual routed application.

Cover at minimum:

- selecting a schema;
- duplicating a built-in schema;
- creating a field;
- selecting fields with keyboard;
- editing every major configuration category;
- deleting a field and verifying focus restoration;
- saving;
- validation failure;
- import/export where practical;
- prompt-group selection/editing;
- document-field policy;
- Test schema;
- `en-US` and `fr-CA`;
- narrow layout;
- text-spacing override;
- light/dark;
- increased contrast;
- forced colors;
- reduced motion;
- axe scans after representative interactive states.

Add a small set of visual snapshots for representative layout states so size/alignment regressions are caught.

### Phase 13 — remove obsolete feature-local form styling

After migration, remove Metadata Schemas CSS that duplicates primitive ownership, including local:

- control height rules;
- input/select/textarea padding;
- borders/radii;
- typography;
- focus styling;
- invalid styling;
- duplicated label-control presentation.

Feature CSS should be concerned with information architecture and layout, not ordinary control skinning.

### Phase 14 — documentation, traceability, and final validation

Update requirements/traceability documentation where this work closes existing partial/gap items. Update design-system documentation if the primitive contract changes. Document the rule that feature code composes `UiField` with native-semantic primitives instead of styling raw ordinary controls.

Before completion:

- sync with current `master`;
- run formatting;
- run lint/typecheck;
- run metadata-schema frontend tests;
- run locale dictionary and accessibility-floor tests;
- run design-token tests;
- build Storybook;
- build production web bundle;
- run targeted Playwright/axe coverage;
- run required full CI.

Do not weaken tests, suppress axe rules, or add broad exceptions merely to obtain a green build.

## Definition of done

| Area | Required state |
| --- | --- |
| Form consistency | Metadata Schemas uses shared ordinary-control primitives; feature-local control sizing/skinning is gone. |
| UX | The current schema, selected field, save state, and current configuration context are immediately understandable. |
| Field editing | Fields use navigator + inspector rather than an expanding form inside a table row. |
| Schema semantics | Existing serialization, stable identities, built-in behavior, prompt groups, document policy, memory/retrieval settings, and preview semantics remain intact. |
| i18n | All application-authored copy is externalized and present in both canonical built-in locales with placeholder parity. |
| French | Primary flows are explicitly tested in `fr-CA`, including long strings and narrow layouts. |
| Keyboard | Complete primary flow works without a pointer with predictable focus behavior. |
| Accessibility | WCAG 2.2 AA requirements are verified beyond automated axe checks. |
| Responsive | All core task capability remains available at narrow widths and with enlarged/translated text. |
| Themes | Light, dark, increased contrast, forced colors, and reduced motion are supported. |
| Regression prevention | Static tests prevent reintroduction of ad hoc controls and local primitive-style overrides in Metadata Schemas. |
| Storybook | New primitives and representative schema states have stories. |
| CI | Required test/build/lint/typecheck/accessibility gates are green. |

## Progress log

### 2026-10-03 — kickoff

- [x] Created branch `task/metadata-schemas-refactor` from current `master` (`1619f03f7fd87cb30b0a7f048359c4b513e1fa2e`).
- [x] Added this implementation plan and progress log.
- [x] Confirmed the current feature used `UiField`, `UiCombobox`, and `UiTagPicker` but lacked general `UiInput`, `UiSelect`, and `UiTextarea` primitives.
- [x] Confirmed Metadata Schemas contained direct native form controls and feature-local control sizing.
- [x] Confirmed the Fields surface expanded the full `SchemaFieldForm` inside table rows.
- [x] Confirmed the repository requirements explicitly target WCAG 2.2 AA and require en-US/fr-CA key/placeholder parity.

### 2026-10-03 — form foundation and first workspace refactor

- [x] Added a canonical ordinary-control stylesheet backed by semantic design tokens.
- [x] Added native-semantic `UiInput`, `UiSelect`, `UiTextarea`, and `UiCheckbox` primitives.
- [x] Added Storybook stories and focused primitive tests for the new form controls.
- [x] Extended `UiField` so visible labels can explicitly target native/simple composite controls instead of wrapping arbitrary interactive descendants.
- [x] Extended `UiTagPicker` with explicit input IDs, descriptions, invalid state, and visible-label integration.
- [x] Replaced the expanding field-table editor with a grouped field navigator and persistent field inspector.
- [x] Added deterministic focus behavior for adding and removing fields.
- [x] Reorganized field configuration into Basics, Extraction, Evidence & review, Linguistic guidance, Value matching, and Memory & retrieval, using native disclosure for advanced sections.
- [x] Migrated Metadata Schema identity, field, prompt-group, preview, and document-policy ordinary controls onto the shared primitives.
- [x] Removed feature-local `.control` sizing rules from the migrated Metadata Schemas components.
- [x] Replaced the schema-library table/clickable rows with semantic navigation and real buttons.
- [x] Added a desktop master/detail layout for schema library + editor with narrow-screen stacking.
- [x] Renamed the primary concepts in UI copy from generic “Prompts” / “Try it” toward “Prompt groups” / “Test schema”.
- [x] Added en-US and fr-CA copy for the new workflow and synchronized `enUsDefaults.json`.
- [x] Added a schema-specific i18n test for scoped literal keys plus generated document-field, POS/NER, and value-matching key families.
- [x] Added a regression test that rejects ordinary raw form controls and legacy local `.control` skins in Metadata Schemas, with the hidden file-import input as the documented exception.
- [x] Updated existing metadata-schema frontend tests for navigator/inspector semantics and readonly navigation.
- [ ] Extend `UiCombobox` with the same explicit visible-label/description contract where needed.
- [ ] Complete the remaining copy/ARIA audit and verify every helper/error relationship.
- [ ] Add representative Metadata Schemas Storybook states beyond the primitive stories.
- [ ] Add dedicated routed Playwright coverage for keyboard, axe, narrow reflow, text spacing, themes, increased contrast, forced colors, reduced motion, and fr-CA.
- [ ] Update user/developer documentation and requirements traceability after behavior stabilizes.
- [ ] Run formatter, typecheck, unit, locale, design-token, Storybook, production build, targeted Playwright/axe, and full CI validation.
- [ ] Open the PR once the first validation pass has identified and fixed compile/test regressions.

Validation note: this connector session can edit the GitHub branch but does not provide an executable repository checkout, so command-line validation has not yet been run here. The next validation pass will use repository CI and any available GitHub check results rather than treating code inspection as proof of a green build.
