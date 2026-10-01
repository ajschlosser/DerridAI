# Works Refactor and Modernization Plan

This document consolidates the implementation proposals identified during review of the current Works workspace on the \`master\` branch. It covers information architecture, UX, visual design, performance, typing, metadata architecture, accessibility, responsive behavior, testing, documentation, and implementation sequencing.

## Implementation status

Work has started on the first data-model/performance tranche on \`task/works-refactor\`:

- split collection-scale \`WorksLibraryItem\` data from selected-work \`WorkDetail\` data;
- compute citation, full metadata, and insight graphs only for the selected admin work;
- pre-index annotation counts once per snapshot instead of rescanning annotations for every work;
- add a typed, first-class corpus/search-index freshness summary while preserving the distinction between known-current, merely-present, stale/absent, unknown, and unavailable records;
- add a lightweight full-corpus work identity scope so filtering the library no longer silently narrows Create Site's available export scope;
- centralize the existing work database status options and strengthen their TypeScript contract;
- move the Works composable behind an operation-specific typed service boundary instead of importing the general runtime facade directly;
- replace the hidden global-file-input query with an explicit shell-level corpus file-picker command;
- remove runtime DOM decoration from the Works rendering lifecycle and route semantic-map source discovery through a typed service;
- replace the two large corpus/database cards with a compact `Working corpus → Search index` relationship strip, expose freshness there, rename the maintenance action to “Update search index,” and localize the new English/French terminology;
- remove the hard-coded English empty-index label from the domain snapshot.

The next implementation step is to finish the remaining snapshot/metadata-discovery work, then replace Compact with a true List mode and expand deterministic search/faceting before the inspector and dialog decomposition passes.

## Implementation proposals

1. **[Information architecture] Make the Works library the dominant page surface.** Reduce the amount of architecture/status UI users must pass through before reaching the actual collection.

2. **[Information architecture] Replace the two large “Loaded corpus” / “Corpus database” cards with one compact relationship strip.** Present something closer to \`Working corpus → Search index\`, rather than two equally weighted cards.

3. **[Information architecture] Explicitly communicate authoritative versus derived state.** The loaded/reviewed corpus is scholarly state; the vector/search index is a rebuildable projection. The UI should not visually imply that the two are interchangeable.

4. **[Copy] Rename “Sync workspace” to “Update index” or “Update search index.”** “Sync” suggests bidirectional synchronization and is conceptually misleading for a derived index.

5. **[Status] Show index freshness rather than only two raw record counts.** For example: \`18,401 / 18,430 records current · 29 need updating\`.

6. **[Status] Add a meaningful stale/current state for the selected search index.** The user should be able to tell whether the derived index accurately represents the authoritative corpus.

7. **[Layout] Compress the entire top-of-page hierarchy.** Aim for header → compact corpus/index state → search/filter toolbar → library, rather than header → two large cards → toolbar → library.

8. **[Library] Preserve Cards mode as the visually browsable library mode.** Covers, titles, authors, and a few important states make sense here.

9. **[Library] Replace the existing “Compact” mode with a genuine dense List mode.** The current implementation mostly produces compressed cards rather than a fundamentally more scalable browsing mode.

10. **[Library] Make List mode structurally table-like.** Suggested columns: Work, Author/year, Records, Review, Index status, Actions.

11. **[Library] Keep a small cover thumbnail in List mode where useful.** It can preserve book identity without consuming card-level vertical space.

12. **[Shared UI architecture] Align List mode with the application's emerging shared data-workspace/table conventions.** Reuse a \`UiDataTable\`/table shell only where it removes genuine duplication rather than forcing Works into an inappropriate generic abstraction.

13. **[Search] Expand Works search beyond work title.** The current admin search essentially matches only \`item.work\` against the query.

14. **[Search] Search deterministic work-level metadata.** Include title, author, translator, publication year, publisher, editor, language, identifiers, and other appropriate bibliographic values.

15. **[Search] Do not turn library search into semantic/RAG retrieval.** This surface is for navigation within a known collection; predictable deterministic matching is preferable.

16. **[Filters] Replace the mostly hidden filter drawer state with visible filter chips once filters are applied.** For example: \`Jacques Derrida ×\`, \`Needs review ×\`, \`Index: changed ×\`.

17. **[Filters] Add a visible “Clear all” affordance alongside active filter chips.**

18. **[Filters] Make filters genuinely faceted.** Authors, language, year/range, review state, index state, and other available dimensions should behave like library facets rather than arbitrary form fields.

19. **[Researcher UX] Allow researcher-relevant bibliographic filters in researcher mode.** Author, date, language, etc. should not be unnecessarily admin-only.

20. **[Admin UX] Keep operational filters admin-specific where appropriate.** Index synchronization state and other corpus-management concerns do not need to appear to ordinary researchers.

21. **[Inspector] Keep the selected-work side inspector pattern.** That part of the redesign is directionally correct and avoids pushing the library down the page.

22. **[Inspector] Reorganize the inspector using progressive disclosure.** Suggested sequence: Identity → Corpus → Bibliographic metadata → Insights → Provenance/technical details.

23. **[Inspector] Show populated bibliographic fields by default instead of drawing a box for every possible field.** The current fixed metadata grid creates unnecessary visual noise.

24. **[Inspector] Add a “Show empty fields” control for administrators diagnosing metadata completeness.**

25. **[Inspector] Separate operational state from bibliography visually.** Index status, review state, and other system facts should not look like intrinsic bibliographic properties of the work.

26. **[Inspector] Keep the inspector masthead and primary actions sticky while its detail body scrolls.** Long metadata or insight sections should not make the main actions disappear.

27. **[Review UX] Upgrade the crude “N need review” number into a compact work-health summary.** For example: \`388 reviewed · 12 need review · 3 unresolved\`.

28. **[Review UX] If the underlying assertion model permits it, distinguish epistemic states.** Examples might include unresolved model assertions, disputed assertions, or human-reviewed values rather than flattening everything into one generic review count.

29. **[Review UX] Make each health-state count actionable.** Clicking \`12 need review\` should open exactly those records.

30. **[Review UX] Avoid turning work health into decorative gauges or dashboard clutter.** A compact actionable status summary is preferable.

31. **[Performance] Split the current \`WorksItem\` concept into cheap library summaries and expensive work details.** For example, \`WorksLibraryItem\` versus \`WorkDetail\`.

32. **[Performance] Stop computing \`workInsightMetrics()\` for every work on every Works snapshot.** Cards do not consume the insight data; calculate it when a work is selected.

33. **[Performance] Load full metadata/citation/insight detail only for the selected work.**

34. **[Performance] Pre-index annotation counts by work once.** \`describeAdminWork()\` currently filters all annotations independently for each work.

35. **[Performance] Cache expensive selected-work detail by a meaningful revision/signature.** Work insights and derived summaries can be reused until the relevant records actually change.

36. **[Performance] Add cancellation/race protection when rapidly switching selected works.** If detail retrieval becomes asynchronous, an old response must not overwrite the newly selected work.

37. **[Performance] Replace the \`revealed += 12\` / \`requestAnimationFrame\` progressive rendering mechanism with a scalable collection strategy.** For large libraries, use proper virtualization, windowing, or pagination rather than merely revealing already-computed results over several animation frames.

38. **[Performance] Add explicit large-corpus performance targets.** Test at realistic scales such as 250, 1,000, and several thousand works rather than only story fixtures containing a handful.

39. **[Architecture] Finish the Works migration away from \`runtime/runtime.js\`.** \`useWorksWorkspace.ts\` still openly identifies itself as a transitional compatibility boundary.

40. **[Architecture] Give the Works composable explicit typed services/stores rather than importing the general runtime facade.**

41. **[Architecture] Remove the \`Loose\`, \`Any\`, \`Fn\`, and generic helper-injection architecture from \`domain/worksWorkspace.ts\`.** Replace it incrementally with typed interfaces at actual domain seams.

42. **[Architecture] Keep \`domain/\` responsible for pure work/library rules and \`composables/\` or stores responsible for stateful orchestration.** Do not rebuild another Works monolith while removing the runtime dependency.

43. **[Architecture] Remove \`runtime.decorateDisabledControls()\` from the Works rendering lifecycle.** Disabled state, explanatory reasons, and accessibility should be represented by Vue component state directly.

44. **[Architecture] Replace \`document.querySelector("#fileInput")?.click()\` with an explicit corpus/file ingestion command or service.** Components should not depend on a hidden global DOM input owned elsewhere.

45. **[Metadata architecture] Remove the hard-coded \`metadataFields\` array from Works.** The current work description explicitly names source type, author, container, journal, volume, issue, publisher, translator, etc.

46. **[Metadata architecture] Derive displayed metadata from the metadata/schema/presentation contract.** This keeps Works compatible with the broader FieldAssertion/schema-driven direction instead of reintroducing hard-coded field knowledge.

47. **[Metadata architecture] Keep field identity separate from display labels.** Works should operate on stable field IDs and let presentation/i18n resolve labels.

48. **[Typing] Replace raw string status values such as \`changed\`, \`synced\`, \`exists\`, \`absent\`, \`unknown\`, and \`none\` with a typed domain enum/union exported from one place.**

49. **[Typing] Move status/filter option definitions out of \`WorksLibraryToolbar.vue\`.** UI components should receive typed available facets/statuses rather than independently knowing every operational state.

50. **[View decomposition] Stop allowing \`WorksView.vue\` to grow into another orchestration monolith.** It currently owns library composition, responsive inspector behavior, site export, semantic-map state/loading, store switching, and several lifecycle concerns.

51. **[View decomposition] Extract a \`WorkSemanticMapDialog.vue\`.** It should own loading work-map records, work/cross-work/record tabs, fallback sources, and dialog state.

52. **[View decomposition] Extract a \`useWorkSiteExport()\` composable or equivalent service boundary.** Export-option retrieval, busy/error state, Blob creation, filename handling, and download orchestration should not live in the page view.

53. **[View decomposition] Consider extracting responsive inspector behavior into a reusable composable if Records/Search or other surfaces need the same pattern.**

54. **[Accessibility] Replace the hand-built semantic-map \`<dialog>\` with the established \`UiDialog\` primitive.**

55. **[Accessibility] Add/use a proper shared tabs primitive rather than manually wiring \`role="tab"\` and \`role="tabpanel"\` in Works.**

56. **[Accessibility] Make the tab primitive support the expected keyboard model.** Arrow keys, Home/End as appropriate, deterministic focus movement, selected state, and panel association should be covered by tests.

57. **[Accessibility] Add forced-colors and high-contrast coverage for the semantic-map tabs/dialog.**

58. **[Responsive design] Replace JavaScript-only \`matchMedia("(min-width: 1100px)")\` layout decisions where practical with CSS/container-query-driven layout.** JavaScript should decide interaction mode only where necessary.

59. **[Responsive design] Use container queries for card/list/inspector adaptation rather than assuming the entire viewport determines available workspace width.**

60. **[Responsive design] Make the narrow inspector an intentional mobile/fullscreen detail experience rather than merely the desktop panel dropped into a generic large dialog.**

61. **[Library UX] Remove the duplicate “Add JSONL” card at the end of the work grid.** File ingestion is already exposed prominently in the header.

62. **[Copy] Stop presenting implementation formats such as “JSONL” more prominently than the user's task where that detail is not necessary.** Prefer “Add files” or “Add corpus files,” with format details where relevant.

63. **[Copy] Reconsider “Separate JSONL.”** A task-oriented label such as “Split files by work” or similar would be more comprehensible if that accurately describes the command.

64. **[Copy] Normalize “database,” “collection,” “store,” “Chroma collection,” and “index.”** The page currently exposes several implementation concepts that users should not have to reconcile.

65. **[Copy] Reserve “Search index” or another consistent product term for the derived corpus representation and use the technical Chroma collection name as secondary detail.**

66. **[i18n] Remove hard-coded English such as \`storesEmptyLabel: "No corpus Chroma collections"\` from the domain snapshot.** That text should come through the localization layer.

67. **[i18n] Audit every new status/filter term for French and long-string behavior.** The current work already has en-US/fr-CA coverage; the next redesign should preserve it.

68. **[Create Site] Fix the mismatch between \`snapshot.totalWorks\` and the filtered \`snapshot.works\` passed into \`CreateSiteDialog\`.** Search/filter state should not silently change export scope unless that is the intended behavior.

69. **[Create Site] Represent full-corpus and current-filter export scopes explicitly.** For example, “Create site…” could start with the entire corpus, while “Create site from 7 results” could be a separate context-specific action.

70. **[Create Site] Consider moving Create Site under a broader Publish/Export grouping.** It is a higher-level publication operation, not a routine library-management command.

71. **[Action hierarchy] Reorganize the header menu by user intent.** File management, metadata enrichment, publication/export, and destructive actions should not appear as an undifferentiated list.

72. **[Action hierarchy] Visually separate destructive commands such as “Remove entire work” from enrichment/indexing commands.** Use the destructive treatment supported by the menu/dialog system.

73. **[Action hierarchy] Stop overloading the “spark” icon.** It is currently used for conceptually different operations including metadata population, review/improvement, and semantic mapping. Use distinct icon semantics.

74. **[Selection UX] Decide explicitly what clicking an already selected work does.** Either keep it selected, toggle the inspector closed, or expose a clear close mechanism—but make the interaction deliberate and test it.

75. **[Selection/filter UX] Handle the case where filters hide the currently selected work.** Either clear selection or show a clear “Selected work is outside the current filters” state.

76. **[Selection/filter UX] Preserve selection across sort/view changes where the selected work remains in scope.**

77. **[Toolbar] Consider making the search/filter/sort toolbar sticky once the user scrolls into a large library.** Search and filtering should remain reachable without returning to the top.

78. **[Toolbar] Hide or simplify controls that have only one possible value.** For example, a corpus-index selector with exactly one available index need not consume the same attention as a genuine multi-index choice.

79. **[Toolbar] Use counts in facets where useful.** \`Needs review (12)\`, \`Jacques Derrida (18)\`, etc. help users predict filter results before applying them.

80. **[Search] Normalize case/Unicode/diacritics predictably.** Library lookup should behave sensibly across multilingual titles and names.

81. **[Search] Highlight matched terms in List/Card identity text when helpful.** Do this sparingly; avoid highlighting every metadata fragment.

82. **[Metadata UX] Give mixed values a clearer explanation.** \`MixedValueInspect\` is useful, but users should understand immediately that values differ across records and that inspecting them does not imply a single canonical work-level value.

83. **[Metadata UX] Add metadata-completeness information without turning it into another dashboard.** For example: “14 of 17 bibliographic fields populated” in the inspector, with the missing fields revealed on demand.

84. **[Provenance UX] Expose field-level provenance when relevant rather than only showing flattened display values.** For administrative/reviewer contexts, users should be able to distinguish model-inferred, deterministic, human-confirmed, disputed, and unresolved work metadata where that provenance exists.

85. **[Provenance UX] Do not rewrite historical inference/review into a single final-value presentation when users enter the audit view.** Preserve the distinction between earlier computational inference and later human review.

86. **[Status UX] Add concise explanations/tooltips for index states and review states.** Terms such as “changed,” “exists,” and “synced” are implementation-derived and are not inherently self-explanatory.

87. **[Error handling] Localize failures to the part of the page that failed.** Failure to load index status should not blank the work library; failure to fetch semantic-map records should not affect the inspector.

88. **[Loading] Avoid hiding the entire page during a store/index change.** Keep the header and library context stable and show a localized loading state in the affected index/status area when possible.

89. **[Loading] Preserve the current library while refreshing rather than flashing back to a full-page loading card.**

90. **[Empty states] Distinguish “no works exist,” “no works match,” “corpus unavailable,” and “search index unavailable.”** These are different states and should lead to different actions.

91. **[Empty states] Keep empty-state language task-oriented.** “No search index is configured” should explain what the user can still do and what action resolves the situation.

92. **[Information density] Reduce unnecessary nested borders/cards.** Header, context, toolbar, cards, inspector metadata tiles, and insight cards can currently produce excessive container-within-container visual chrome.

93. **[Visual design] Use book/catalog identity as the strongest visual motif.** Title, author, year, cover, edition/translation should dominate the visual hierarchy.

94. **[Visual design] Make operational state quieter.** Review/index badges matter, but they should not compete with the bibliographic identity of the work.

95. **[Visual design] Use whitespace more economically.** Keep clarity without making every informational group a large standalone card.

96. **[Visual design] Establish clearer typography levels between work title, bibliographic secondary data, counts, and operational status.** The page should be scannable from titles alone.

97. **[Visual design] Improve missing-cover treatment.** A restrained typographic/book-spine placeholder would look more intentional than a generic books icon occupying the same space as real cover art.

98. **[Visual design] Keep selected-state emphasis strong enough for split-view orientation but quieter than a destructive/warning state.** The current accent border/inset stripe is a good basis and can be refined.

99. **[Visual design] Avoid color as the only index/review-state discriminator.** Continue pairing tone with labels/icons for accessibility.

100. **[Keyboard UX] Ensure the library supports efficient keyboard traversal at scale.** Native tab navigation already works, but a dense List mode may benefit from a carefully designed row-navigation model if it can be implemented without violating familiar table semantics.

101. **[Keyboard UX] Restore focus reliably when closing the responsive inspector, changing modes, or removing a selected work.** The current close behavior already attempts this on wide screens; extend and formalize it.

102. **[Bulk workflows] Evaluate a multi-select mode for genuinely common work-level batch operations.** Candidates include metadata enrichment, index update, publication/site export, or review. Do not add selection merely because tables commonly have checkboxes; add it only for validated workflows.

103. **[Bulk workflows] If multi-select is added, use a contextual selection action bar rather than permanently adding another toolbar row.**

104. **[State persistence] Preserve the current URL-backed sort/filter/view behavior through the redesign.** This is valuable functionality and should not regress.

105. **[State persistence] Make new facet/filter state URL-safe and backward-compatible with existing saved Works links.**

106. **[State persistence] Keep ephemeral UI state out of the URL.** Dialog-open state, hover state, temporary menu expansion, etc. should not pollute bookmarkable workspace state.

107. **[Data model] Separate totals from filtered counts throughout the snapshot contract.** Maintain a clear distinction between all works, matching works, and rendered/windowed works.

108. **[Data model] Do not expose \`allWorks\` simply to fix Create Site if it doubles an expensive fully described object graph.** Add a lightweight scope/identity collection instead.

109. **[Data model] Make index freshness a domain object rather than deriving it piecemeal in components.** It might contain current count, stale count, absent count, last refresh, target collection, and availability.

110. **[Data model] Make work-review health a domain summary rather than recomputing it from loosely related fields in several components.**

111. **[Testing] Keep Storybook coverage for header, toolbar, cards/list rows, context/status strip, inspector, empty states, and unavailable-index states.**

112. **[Testing] Add Storybook states for long titles, multiple authors, missing year, missing cover, mixed metadata, many review records, zero review records, stale index, unavailable index, and incomplete bibliography.**

113. **[Testing] Maintain WCAG 2.2 AA Axe checks on each major Works component.**

114. **[Testing] Add explicit keyboard tests for List mode, filter chips, filter popover, inspector open/close, menus, and semantic-map tabs.**

115. **[Testing] Add French/long-string snapshots for the complete composed Works workspace, not only individual components.**

116. **[Testing] Add dark-mode, high-contrast, and forced-colors snapshots for the redesigned page.**

117. **[Testing] Add responsive snapshots at the important layout transitions: wide split view, medium single-column desktop/tablet, and narrow mobile dialog/detail view.**

118. **[Testing] Add integration coverage for search → filter → select work → inspect → clear filters.**

119. **[Testing] Add integration coverage for a selected work becoming excluded by a filter.**

120. **[Testing] Add integration coverage for switching the active search index and observing localized loading/error/current-state behavior.**

121. **[Testing] Add explicit tests for full-corpus versus filtered-scope Create Site behavior.**

122. **[Testing] Add performance/regression tests ensuring library search/filter/sort do not recalculate insight graphs for every work.**

123. **[Testing] Add regression coverage proving annotation counting is linear/pre-indexed rather than repeatedly scanning all annotations per work.**

124. **[Testing] Keep tests around URL restoration for sort, filters, selected work, and view mode as the state model evolves.**

125. **[Testing] Add accessibility tests for focus return after inspector/dialog close.**

126. **[Documentation] Update the User Guide once “sync,” “database,” “compact,” and other terminology changes.**

127. **[Documentation] Explain the corpus-versus-search-index distinction in product language, not Chroma implementation language.** The application architecture already treats vector stores as derived rather than canonical; the page and docs should agree.

128. **[Documentation] Document what each work-level status means and which actions change authoritative records versus derived indexes.**

129. **[Implementation sequencing] First optimize the snapshot/data model before adding more UI complexity.** Otherwise the prettier page will still perform unnecessary work on every keystroke/filter change.

130. **[Implementation sequencing] Second migrate Works off the legacy runtime boundary.** Do this through the existing domain seams rather than performing another wholesale rewrite.

131. **[Implementation sequencing] Third implement the compact corpus/index strip and terminology cleanup.**

132. **[Implementation sequencing] Fourth replace Compact with true List mode and introduce the enhanced search/facet toolbar.**

133. **[Implementation sequencing] Fifth restructure the inspector and work-health presentation.**

134. **[Implementation sequencing] Sixth extract semantic-map and site-export orchestration from \`WorksView.vue\`.**

135. **[Implementation sequencing] Seventh perform the responsive/accessibility/testing polish pass.**

136. **[Overall product direction] Treat Works as professional library/catalog software, not as an admin dashboard.** Strong bibliographic identity, immediate browsing/search, compact operational state, progressive disclosure, and minimal implementation jargon should be the governing design principles.

## Implementation priorities

The highest-value first tranche is:

- optimize the Works snapshot/data model and lazy-load selected-work detail;
- make index freshness a first-class domain concept;
- remove remaining legacy runtime ownership from Works;
- collapse corpus/index context into a compact relationship strip;
- replace Compact with a real List view;
- expand deterministic search and faceted filtering;
- restructure the inspector around progressive disclosure;
- extract semantic-map and site-export orchestration;
- preserve URL state, i18n, WCAG 2.2 AA, responsive behavior, and Storybook/Playwright coverage throughout.

## Design target

The Works page should behave like professional library/catalog software rather than an administrative dashboard. Bibliographic identity should dominate. Operational state should remain visible but secondary. Users should be able to locate a work, understand its scholarly and review state, inspect its metadata, and take the next relevant action without first interpreting internal storage architecture.
