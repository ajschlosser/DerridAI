/* Copyright 2026 Aaron John Schlosser, PhD. */

// The Works workspace: describing each work, loading what the Works view needs, and the commands it sends (search,
// overview, sync, metadata dialogs, review and remove actions). Moved verbatim from the legacy runtime; the runtime's
// state object and helpers are passed in as dependencies.
import { fullCitation } from "./citations";
import { commonWorkValue, workCoverUrl } from "./workMetadata";
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
  | "uniqueWorkValues"
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
    uniqueWorkValues,
    upsertRows,
    workDbStatus,
    workIndex,
    workInsightMetrics,
    worksBiblioValue,
  } = deps;
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
    };
    if (!detail) return base;

    const metadataFields = [
      "source_type",
      "document_author",
      "container_title",
      "journal_title",
      "volume",
      "issue",
      "pages",
      "publisher",
      "publication_year",
      "edition",
      "translator",
      "editor",
      "publication_place",
      "isbn",
      "doi",
      "document_language",
      "original_language",
    ];
    return {
      ...base,
      citation: fullCitation(item.rows[0]?.record || { work: item.work }, { includePages: false }),
      metadata: metadataFields.map((field) => {
        const value = commonWorkValue(item.rows, field);
        return {
          field,
          field_label: label(field),
          mixed: Boolean(value.mixed),
          value: value.mixed ? "" : String(display(value.value)),
          unique_count: value.mixed ? uniqueWorkValues(item.rows, field).length : 0,
        };
      }),
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
    else if (freshness.unavailableRecords === freshness.totalRecords) freshness.state = "unavailable";
    else if (freshness.changedRecords || freshness.absentRecords) freshness.state = "stale";
    else if (
      freshness.presentRecords ||
      freshness.unknownRecords ||
      freshness.unavailableRecords
    )
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
      viewMode: state.worksView === "compact" ? "compact" : "cards",
      stores,
      activeStore,
      activeStoreCount: Number(activeStoreInfo?.count || 0),
      dbUnavailableReason: noDbReason,
      storesEmptyLabel: "No corpus Chroma collections",
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
      const needle = query.toLocaleLowerCase();
      const items = sortWorkItems(
        all
          .filter((item: Any) => !query || String(item.work).toLocaleLowerCase().includes(needle))
          .map((item: Any) => describeResearcherWork(item, { selected: false })),
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
          unavailableRecords: all.reduce(
            (sum: Any, item: Any) => sum + Number(item.count || 0),
            0,
          ),
        },
        sourceFileCount: 0,
        totalReview: 0,
        authors: [],
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
    const needle = query.toLocaleLowerCase();
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
          (!query || item.work.toLocaleLowerCase().includes(needle)) &&
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
      authors: [...new Set(described.flatMap((item: Any) => item.authors as string[]))].sort(
        (a, b) => a.localeCompare(b),
      ),
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
      state.worksView = patch.viewMode === "compact" ? "compact" : "cards";
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
