/* Copyright 2026 Aaron John Schlosser, PhD. */

// The Works workspace: describing each work, loading what the Works view needs, and the commands it sends (search,
// overview, sync, metadata dialogs, review and remove actions). Moved verbatim from the legacy runtime; the runtime's
// state object and helpers are passed in as dependencies.
import { fullCitation } from "./citations";
import { commonWorkValue, workCoverUrl } from "./workMetadata";

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
  function describeAdminWork(item: Any, { insights = false } = {}) {
    const publisher = worksBiblioValue(item.rows, "publisher");
    const translator = worksBiblioValue(item.rows, "translator");
    const year = commonWorkValue(item.rows, "publication_year");
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
      work: item.work,
      count: item.count,
      review: item.review,
      annotations: allAnnotations().filter(
        (annotation: Any) => String(annotation.work || "") === String(item.work),
      ).length,
      files: [...item.files],
      authors: [...item.authors],
      years: [...item.years].map(String),
      cover: workCoverUrl(item.rows),
      citation: fullCitation(item.rows[0]?.record || { work: item.work }, { includePages: false }),
      year_label: year.value ? String(year.value) : [...item.years].sort().join(", "),
      subtitle: "",
      publisher,
      translator,
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
      status: workDbStatus(item.rows, item.work),
      insights: insights
        ? workInsightMetrics(item.rows, item.work).map((metric: Any) => ({
            id: metric.id,
            field: metric.field,
            title: metric.title,
            heading: String(metric.title || "")
              .replace(" in the work", "")
              .replace(" mentioned in the work", ""),
            type: metric.type === "pie" ? "pie" : "bars",
            values: metric.values.map((value: Any) => ({
              key: String(value.key),
              value: Number(value.value || 0),
              other: Boolean(value.other),
            })),
          }))
        : [],
    };
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
      stores,
      activeStore,
      activeStoreCount: Number(activeStoreInfo?.count || 0),
      dbUnavailableReason: noDbReason,
      storesEmptyLabel: "No corpus Chroma collections",
      citationLabel: label("full_citation"),
      populateDisabledReason: "",
      syncAllDisabledReason:
        noDbReason || tr("works.select_collection", "Select a corpus collection first."),
      corpusManageDeniedReason: tr(
        "permissions.corpus_manage_denied",
        "Your role cannot load corpus files.",
      ),
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
      const items = (state.storeWorkStats || []).filter(
        (item: Any) =>
          !query || String(item.work).toLocaleLowerCase().includes(query.toLocaleLowerCase()),
      );
      const selectedStat = items.find((item: Any) => item.work === state.workOverview) || null;
      return worksSnapshotBase({
        mode: "researcher",
        available: stores.length > 0,
        works: items.map((item: Any) => describeResearcherWork(item, { selected: false })),
        selected: selectedStat ? describeResearcherWork(selectedStat, { selected: true }) : null,
        totalWorks: items.length,
        totalRecords: items.reduce((sum: Any, item: Any) => sum + Number(item.count || 0), 0),
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
    const items = [...map.values()]
      .filter((item) => !query || item.work.toLocaleLowerCase().includes(query.toLocaleLowerCase()))
      .sort((a, b) => a.work.localeCompare(b.work));
    const totalRecords = [...map.values()].reduce((sum, item) => sum + item.count, 0);
    return worksSnapshotBase({
      mode: "admin",
      available: state.files.length > 0,
      works: items.map((item) => describeAdminWork(item)),
      selected: selectedItem ? describeAdminWork(selectedItem, { insights: true }) : null,
      totalWorks: map.size,
      totalRecords,
      populateDisabledReason: hasProfiles
        ? tr("works.no_works_to_populate", "No works are available to populate.")
        : tr(
            "works.no_provider_profiles_help",
            "Create an LLM provider profile before populating work metadata.",
          ),
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
    return upsertRows(rows, tr("works.all_records_label", "records across all works"));
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
  function searchWork(work: Any) {
    searchWorkRecords(work);
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
    setWorksStore,
    syncWork,
    syncAllWorks,
    searchWorkRecords,
    searchWork,
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
