/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

// The Works workspace: describing each work, loading what the Works view needs, and the commands it sends (search,
// overview, sync, metadata dialogs, review and remove actions). Moved verbatim from the legacy runtime; the runtime's
// state object and helpers are passed in as dependencies.
import { fullCitation } from "./citations";
import { currentFieldAssertions } from "./fieldAssertions";
import { metadataSchemasApi, type MetadataSchema } from "../api/metadataSchemas";
import { commonWorkValue, workCoverUrl, workMetadataPresentationRows } from "./workMetadata";
import { WORK_METADATA_LLM_FIELDS } from "./runtimeConstants";
import type { WorksDbStatusKind, WorksIndexFreshness } from "../types/works";

export const WORKS_SORTS = ["title-asc", "title-desc", "records-desc", "review-desc", "year-asc"];
/** The stable `workDbStatus()` kinds a Works filter may name. */
export const WORKS_DB_STATUSES: WorksDbStatusKind[] = [
  "changed",
  "synced",
  "exists",
  "absent",
  "unknown",
  "none",
];

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "allAnnotations"
  | "canUse"
  | "dbUnavailableReason"
  | "describeResearcherWork"
  | "display"
  | "hasCorpusDb"
  | "isResearcher"
  | "label"
  | "navigateTo"
  | "needsReviewItems"
  | "openMixedWorkValuesDialog"
  | "openRemoveWorkModal"
  | "openTouchup"
  | "openWorkMetadataEditor"
  | "openWorkMetadataLlmDialog"
  | "persistPrefs"
  | "providerProfiles"
  | "recordStores"
  | "refreshPresenceForRows"
  | "refreshServerAnnotations"
  | "refreshStoreWorks"
  | "refreshStores"
  | "searchByMetadata"
  | "setActiveStore"
  | "syncUrl"
  | "tr"
  | "uid"
  | "upsertRows"
  | "workDbStatus"
  | "workIndex"
  | "workInsightMetrics"
  | "worksBiblioValue";
type Deps = { state: Loose } & Record<Helper, Fn>;

export function createWorksWorkspace(deps: Deps) {
  const {
    state,
    allAnnotations,
    canUse,
    dbUnavailableReason,
    describeResearcherWork,
    display,
    hasCorpusDb,
    isResearcher,
    label,
    navigateTo,
    needsReviewItems,
    openMixedWorkValuesDialog,
    openRemoveWorkModal,
    openTouchup,
    openWorkMetadataEditor,
    openWorkMetadataLlmDialog,
    persistPrefs,
    providerProfiles,
    recordStores,
    refreshPresenceForRows,
    refreshServerAnnotations,
    refreshStoreWorks,
    refreshStores,
    searchByMetadata,
    setActiveStore,
    syncUrl,
    tr,
    uid,
    upsertRows,
    workDbStatus,
    workIndex,
    workInsightMetrics,
    worksBiblioValue,
  } = deps;
  const workSearchCache = new WeakMap<object, string>();
  const workMetadataSchemaCache = new Map<string, MetadataSchema | null>();

  function schemaIdForRows(rows: Any[]): string {
    const ids = new Set<string>();
    for (const row of rows || []) {
      const explicit = String(row?.record?.schema_id || "").trim();
      if (explicit) ids.add(explicit);
      for (const assertion of currentFieldAssertions(row?.record || {})) {
        const id = String(assertion.schema_id || "").trim();
        if (id) ids.add(id);
      }
    }
    return ids.size === 1 ? [...ids][0] : "";
  }

  function workMetadataSchema(rows: Any[]): MetadataSchema | null {
    const schemaId = schemaIdForRows(rows);
    return schemaId ? workMetadataSchemaCache.get(schemaId) || null : null;
  }

  async function preloadWorkMetadataSchemas(rows: Any[]) {
    const ids = new Set<string>();
    for (const row of rows || []) {
      const explicit = String(row?.record?.schema_id || "").trim();
      if (explicit) ids.add(explicit);
      for (const assertion of currentFieldAssertions(row?.record || {})) {
        const id = String(assertion.schema_id || "").trim();
        if (id) ids.add(id);
      }
    }
    await Promise.all(
      [...ids].map(async (id) => {
        if (workMetadataSchemaCache.has(id)) return;
        try {
          workMetadataSchemaCache.set(id, await metadataSchemasApi.get(id));
        } catch {
          // Imported/legacy publications may reference a schema that is no
          // longer installed. Their FieldAssertion identities still provide
          // the compatibility path in workMetadataPresentationRows.
          workMetadataSchemaCache.set(id, null);
        }
      }),
    );
  }
  const librarySearchFields = [
    ...WORK_METADATA_LLM_FIELDS,
    "canonical_work_id",
    "original_language",
  ];

  function normalizeLibrarySearch(value: unknown): string {
    return String(value ?? "")
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase()
      .trim();
  }

  function appendSearchValue(values: string[], value: unknown) {
    if (Array.isArray(value)) {
      for (const item of value) appendSearchValue(values, item);
      return;
    }
    if (value === null || value === undefined || typeof value === "object") return;
    const normalized = normalizeLibrarySearch(value);
    if (normalized) values.push(normalized);
  }

  function adminWorkSearchText(item: Any): string {
    if (item && typeof item === "object") {
      const cached = workSearchCache.get(item);
      if (cached !== undefined) return cached;
    }
    const values: string[] = [];
    appendSearchValue(values, item?.work);
    appendSearchValue(values, [...(item?.authors || [])]);
    appendSearchValue(values, [...(item?.years || [])]);
    for (const row of item?.rows || []) {
      for (const field of librarySearchFields) appendSearchValue(values, row.record?.[field]);
    }
    const text = [...new Set(values)].join(" ");
    if (item && typeof item === "object") workSearchCache.set(item, text);
    return text;
  }

  function researcherWorkSearchText(item: Any): string {
    const values: string[] = [];
    appendSearchValue(values, item?.work);
    for (const field of librarySearchFields) appendSearchValue(values, item?.[field]);
    return [...new Set(values)].join(" ");
  }

  function worksSortValue() {
    return WORKS_SORTS.includes(state.worksSort) ? String(state.worksSort) : "title-asc";
  }
  /** The first four-digit year in a label, or null when the work has no defined year. */
  function workYear(item: Any): number | null {
    const match = String(item.year_label || "").match(/\d{4}/);
    return match ? Number(match[0]) : null;
  }
  function sortWorkItems(items: Any[]) {
    const byTitle = (a: Any, b: Any) => a.work.localeCompare(b.work);
    const sort = worksSortValue();
    const compare: (a: Any, b: Any) => number =
      sort === "title-desc"
        ? (a, b) => byTitle(b, a)
        : sort === "records-desc"
          ? (a, b) => b.count - a.count || byTitle(a, b)
          : sort === "review-desc"
            ? (a, b) => b.review - a.review || byTitle(a, b)
            : sort === "year-asc"
              ? (a, b) => {
                  const ya = workYear(a);
                  const yb = workYear(b);
                  if (ya === null || yb === null)
                    return ya === yb ? byTitle(a, b) : ya === null ? 1 : -1;
                  return ya - yb || byTitle(a, b);
                }
              : byTitle;
    return [...items].sort(compare);
  }
  function annotationCountsByWork() {
    const counts = new Map<string, number>();
    for (const annotation of allAnnotations()) {
      const work = String(annotation.work || "");
      if (!work) continue;
      counts.set(work, (counts.get(work) || 0) + 1);
    }
    return counts;
  }

  function describeAdminWork(
    item: Any,
    {
      detail = false,
      annotationCounts = null,
    }: { detail?: boolean; annotationCounts?: Map<string, number> | null } = {},
  ) {
    const publisher = worksBiblioValue(item.rows, "publisher");
    const translator = worksBiblioValue(item.rows, "translator");
    const year = commonWorkValue(item.rows, "publication_year");
    const base = {
      work: item.work,
      count: item.count,
      review: item.review,
      annotations: Number(annotationCounts?.get(String(item.work)) || 0),
      files: [...item.files],
      authors: [...item.authors],
      years: [...item.years].map(String),
      cover: workCoverUrl(item.rows),
      year_label: year.value ? String(year.value) : [...item.years].sort().join(", "),
      subtitle: "",
      publisher,
      translator,
      status: workDbStatus(item.rows, item.work),
      searchText: adminWorkSearchText(item),
    };
    if (!detail) return base;

    const metadata = workMetadataPresentationRows(item.rows, workMetadataSchema(item.rows)).map(
      (item) => ({
        field_id: item.field_id,
        field: item.field,
        field_label: label(item.field),
        mixed: item.mixed,
        value: item.mixed ? "" : String(display(item.value)),
        unique_count: item.unique_count,
        empty: item.empty,
      }),
    );
    return {
      ...base,
      citation: fullCitation(item.rows[0]?.record || { work: item.work }, { includePages: false }),
      metadata,
      insights: workInsightMetrics(item.rows, item.work).map((metric: Any) => ({
        id: metric.id,
        field: metric.field,
        title: metric.title,
        heading: metric.heading,
        type: metric.type === "pie" ? "pie" : "bars",
        values: metric.values.map((value: Any) => ({
          key: String(value.key),
          value: Number(value.value || 0),
          other: Boolean(value.other),
        })),
      })),
    };
  }

  function summarizeIndexFreshness(items: Any[]): WorksIndexFreshness {
    const freshness: WorksIndexFreshness = {
      state: "empty",
      totalRecords: 0,
      currentRecords: 0,
      changedRecords: 0,
      presentRecords: 0,
      absentRecords: 0,
      unknownRecords: 0,
      unavailableRecords: 0,
    };
    for (const item of items) {
      const count = Number(item.count || 0);
      freshness.totalRecords += count;
      switch (item.status?.kind as WorksDbStatusKind | undefined) {
        case "synced":
          freshness.currentRecords += count;
          break;
        case "changed":
          freshness.changedRecords += count;
          break;
        case "exists":
          freshness.presentRecords += count;
          break;
        case "absent":
          freshness.absentRecords += count;
          break;
        case "unknown":
          freshness.unknownRecords += count;
          break;
        default:
          freshness.unavailableRecords += count;
      }
    }
    if (!freshness.totalRecords) freshness.state = "empty";
    else if (freshness.unavailableRecords === freshness.totalRecords)
      freshness.state = "unavailable";
    else if (freshness.changedRecords || freshness.absentRecords) freshness.state = "stale";
    else if (freshness.presentRecords || freshness.unknownRecords || freshness.unavailableRecords)
      freshness.state = "unknown";
    else freshness.state = "current";
    return freshness;
  }

  function worksSnapshotBase(extra: Any) {
    const stores = recordStores().map((store: Any) => ({
      name: store.name,
      count: Number(store.count || 0),
    }));
    const activeStore = String(state.activeStore || "");
    const activeStoreInfo = stores.find((store: Any) => store.name === activeStore) || null;
    const noDbReason = dbUnavailableReason();
    return {
      query: String(state.worksSearch || ""),
      selectedWork: String(state.workOverview || ""),
      sort: worksSortValue(),
      filters: {
        needsReview: Boolean(state.worksNeedsReview),
        dbStatus: String(state.worksDbStatus || ""),
        author: String(state.worksAuthor || ""),
      },
      viewMode: ["list", "compact"].includes(String(state.worksView)) ? "list" : "cards",
      stores,
      activeStore,
      activeStoreCount: Number(activeStoreInfo?.count || 0),
      dbUnavailableReason: noDbReason,
      storesEmptyLabel: tr("works.no_search_indexes"),
      citationLabel: label("full_citation"),
      populateDisabledReason: "",
      syncAllDisabledReason: noDbReason || tr("works.select_collection"),
      corpusManageDeniedReason: tr("permissions.corpus_manage_denied"),
      hasProviderProfiles: providerProfiles().length > 0,
      shared: Boolean(new URLSearchParams(location.search).get("file")),
      error: "",
      ...extra,
    };
  }
  async function prepareWorksWorkspace() {
    if (isResearcher()) {
      try {
        await refreshStores();
        if (!state.activeStore && recordStores().length) state.activeStore = recordStores()[0].name;
        if (state.activeStore) await refreshStoreWorks(true);
      } catch (error) {
        return { error: (error as Error)?.message || String(error) };
      }
      try {
        await refreshServerAnnotations(true);
      } catch {
        /* annotations are best-effort */
      }
      return { error: "" };
    }
    try {
      await refreshServerAnnotations();
    } catch {
      /* annotations are best-effort */
    }
    try {
      const rows = [...workIndex().values()].flatMap((item) => item.rows || []);
      await preloadWorkMetadataSchemas(rows);
    } catch {
      /* schema enrichment is best-effort; assertion identity fallback remains */
    }
    if (Date.now() - Number(state.storesLastFetchedAt || 0) > 5000) {
      try {
        await refreshStores();
      } catch (error) {
        console.warn("Could not refresh vector stores for Works", error);
      }
    }
    if (hasCorpusDb() && state.storeWorksStore !== state.activeStore) {
      try {
        await refreshStoreWorks();
      } catch (error) {
        console.warn("Could not load work DB counts", error);
      }
    }
    try {
      const rows = [...workIndex().values()].slice(0, 24).flatMap((item) => item.rows.slice(0, 2));
      refreshPresenceForRows(rows);
    } catch {
      /* presence is best-effort */
    }
    return { error: "" };
  }
  function getWorksWorkspaceSnapshot() {
    const query = String(state.worksSearch || "");
    const hasProfiles = providerProfiles().length > 0;
    if (isResearcher()) {
      const stores = recordStores();
      const all = state.storeWorkStats || [];
      const researcherAuthor = String(state.worksAuthor || "");
      const items = sortWorkItems(
        all
          .map((item: Any) => ({
            ...describeResearcherWork(item, { selected: false }),
            searchText: researcherWorkSearchText(item),
            authors: item.document_author ? [String(item.document_author)] : [],
          }))
          .filter(
            (item: Any) =>
              (!query ||
                String(item.searchText || item.work).includes(normalizeLibrarySearch(query))) &&
              (!researcherAuthor || item.authors.includes(researcherAuthor)),
          ),
      );
      const selectedStat = all.find((item: Any) => item.work === state.workOverview) || null;
      return worksSnapshotBase({
        mode: "researcher",
        available: stores.length > 0,
        works: items,
        scopeWorks: all.map((item: Any) => ({
          work: String(item.work || ""),
          count: Number(item.count || 0),
          authors: item.document_author ? [String(item.document_author)] : [],
          year_label: String(item.publication_year || item.year || ""),
        })),
        selected: selectedStat ? describeResearcherWork(selectedStat, { selected: true }) : null,
        totalWorks: all.length,
        visibleWorks: items.length,
        totalRecords: all.reduce((sum: Any, item: Any) => sum + Number(item.count || 0), 0),
        indexFreshness: {
          state: "unavailable",
          totalRecords: all.reduce((sum: Any, item: Any) => sum + Number(item.count || 0), 0),
          currentRecords: 0,
          changedRecords: 0,
          presentRecords: 0,
          absentRecords: 0,
          unknownRecords: 0,
          unavailableRecords: all.reduce((sum: Any, item: Any) => sum + Number(item.count || 0), 0),
        },
        sourceFileCount: 0,
        totalReview: 0,
        authors: [
          ...new Set<string>(
            all.map((item: Any) => String(item.document_author || "").trim()).filter(Boolean),
          ),
        ].sort((a, b) => a.localeCompare(b)),
        capabilities: {
          canManageCorpus: false,
          canSync: false,
          canSyncAll: false,
          canPopulate: false,
        },
      });
    }
    const map = workIndex();
    if (state.workOverview && !map.has(state.workOverview)) state.workOverview = "";
    const selectedItem = state.workOverview ? map.get(state.workOverview) : null;
    const needle = normalizeLibrarySearch(query);
    const annotationCounts = annotationCountsByWork();
    const described = [...map.values()].map((item) =>
      describeAdminWork(item, { annotationCounts }),
    );
    const filters = {
      needsReview: Boolean(state.worksNeedsReview),
      dbStatus: String(state.worksDbStatus || ""),
      author: String(state.worksAuthor || ""),
    };
    const items = sortWorkItems(
      described.filter(
        (item: Any) =>
          (!query || String(item.searchText || item.work).includes(needle)) &&
          (!filters.needsReview || item.review > 0) &&
          (!filters.dbStatus || item.status.kind === filters.dbStatus) &&
          (!filters.author || item.authors.includes(filters.author)),
      ),
    );
    const totalRecords = described.reduce((sum: number, item: Any) => sum + item.count, 0);
    return worksSnapshotBase({
      mode: "admin",
      available: state.files.length > 0,
      works: items,
      scopeWorks: described.map((item: Any) => ({
        work: String(item.work || ""),
        count: Number(item.count || 0),
        authors: [...(item.authors || [])],
        year_label: String(item.year_label || ""),
      })),
      selected: selectedItem
        ? describeAdminWork(selectedItem, { detail: true, annotationCounts })
        : null,
      totalWorks: map.size,
      visibleWorks: items.length,
      totalRecords,
      indexFreshness: summarizeIndexFreshness(described),
      sourceFileCount: new Set(described.flatMap((item: Any) => item.files)).size,
      totalReview: described.reduce((sum: number, item: Any) => sum + item.review, 0),
      authors: [
        ...new Set<string>(described.flatMap((item: Any) => item.authors as string[])),
      ].sort((a, b) => a.localeCompare(b)),
      populateDisabledReason: hasProfiles
        ? tr("works.no_works_to_populate")
        : tr("works.no_provider_profiles_help"),
      capabilities: {
        canManageCorpus: canUse("manageCorpus"),
        canSync: hasCorpusDb(),
        canSyncAll: Boolean(state.activeStore && totalRecords && hasCorpusDb()),
        canPopulate: Boolean(hasProfiles && map.size),
      },
    });
  }
  function setWorksSearch(value: Any) {
    state.worksSearch = String(value || "");
    persistPrefs();
    syncUrl({ replace: true });
  }
  function setWorksOverview(work: Any) {
    state.workOverview = String(work || "");
    persistPrefs();
    syncUrl({ replace: true });
  }
  /** Sort, filter and density are safe workspace state: they persist and ride in the Works URL. */
  function setWorksView(patch: {
    sort?: string;
    needsReview?: boolean;
    dbStatus?: string;
    author?: string;
    viewMode?: string;
  }) {
    if (patch.sort !== undefined)
      state.worksSort = WORKS_SORTS.includes(patch.sort) ? patch.sort : "title-asc";
    if (patch.needsReview !== undefined) state.worksNeedsReview = Boolean(patch.needsReview);
    if (patch.dbStatus !== undefined) state.worksDbStatus = String(patch.dbStatus || "");
    if (patch.author !== undefined) state.worksAuthor = String(patch.author || "");
    if (patch.viewMode !== undefined)
      state.worksView = ["list", "compact"].includes(String(patch.viewMode)) ? "list" : "cards";
    persistPrefs();
    syncUrl({ replace: true });
  }
  async function setWorksStore(name: Any) {
    setActiveStore(name);
    if (isResearcher()) {
      state.workOverview = "";
      try {
        await refreshStoreWorks(true);
      } catch (error) {
        console.warn("Could not load work DB counts", error);
      }
    }
  }
  async function syncWork(work: Any) {
    const item = workIndex().get(String(work || ""));
    if (!item) return false;
    return upsertRows(item.rows, `work “${item.work}”`);
  }
  async function syncAllWorks() {
    const rows = [...workIndex().values()].flatMap((item) => item.rows);
    return upsertRows(rows, tr("works.all_records_label"));
  }
  function searchWorkRecords(work: Any, { needsReview = false } = {}) {
    state.globalSearchMode = "traditional";
    state.globalSearch = "";
    state.globalFilters = [
      { id: uid(), field: "work", op: "eq", value: String(work || "") },
      ...(needsReview ? [{ id: uid(), field: "needs_review", op: "eq", value: "true" }] : []),
    ];
    state.globalPage = 1;
    persistPrefs();
    navigateTo("global");
  }
  function searchWorkOverview(work: Any) {
    state.globalSearch = "";
    state.globalFilters = [{ id: uid(), field: "work", op: "eq", value: String(work || "") }];
    state.globalPage = 1;
    persistPrefs();
    navigateTo("global");
  }
  function openWorkMetadataEditorForVue(work: Any) {
    const item = workIndex().get(String(work || ""));
    if (item) openWorkMetadataEditor(item.work, item.rows);
  }
  function openWorkMetadataLlmDialogForVue(work: Any) {
    const item = workIndex().get(String(work || ""));
    if (item) openWorkMetadataLlmDialog([item]);
  }
  function openWorkAnnotations(work: Any) {
    state.annotationSearch = String(work || "");
    state.annotationView = "works";
    persistPrefs();
    navigateTo("annotations");
  }
  function populateAllWorksMetadata() {
    openWorkMetadataLlmDialog(
      [...workIndex().values()].sort((a, b) => a.work.localeCompare(b.work)),
    );
  }
  function inspectWorksMixedField(work: Any, field: Any) {
    const item = workIndex().get(String(work || ""));
    if (item) openMixedWorkValuesDialog(item.work, field, item.rows);
  }
  function searchWorksInsight(field: Any, value: Any) {
    searchByMetadata(field, value, { contains: ["persons", "concepts", "topics"].includes(field) });
  }
  function reviewFlaggedWork(work: Any) {
    openTouchup(needsReviewItems(workIndex().get(String(work || ""))?.rows || []));
  }
  function autoImproveWork(work: Any) {
    openTouchup(needsReviewItems(workIndex().get(String(work || ""))?.rows || []), "auto");
  }
  function removeEntireWork(work: Any) {
    const item = workIndex().get(String(work || ""));
    if (item) return openRemoveWorkModal(item.work, item.rows);
  }
  function browseResearcherWork(work: Any) {
    state.storeWork = String(work || state.workOverview || "");
    state.storeBrowseMode = "records";
    state.storePage = 1;
    persistPrefs();
    navigateTo("vector");
  }
  return {
    describeAdminWork,
    worksSnapshotBase,
    prepareWorksWorkspace,
    getWorksWorkspaceSnapshot,
    setWorksSearch,
    setWorksOverview,
    setWorksView,
    setWorksStore,
    syncWork,
    syncAllWorks,
    searchWorkRecords,
    searchWorkOverview,
    openWorkMetadataEditorForVue,
    openWorkMetadataLlmDialogForVue,
    openWorkAnnotations,
    populateAllWorksMetadata,
    inspectWorksMixedField,
    searchWorksInsight,
    reviewFlaggedWork,
    autoImproveWork,
    removeEntireWork,
    browseResearcherWork,
  };
}
