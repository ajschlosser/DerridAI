/* Copyright 2026 Aaron John Schlosser, PhD. */

// The Annotations workspace: gathering the local and shared annotations, describing them for the Annotations view, and the
// commands it sends (search, view, open a record or work, remove one). Moved verbatim from the legacy runtime; the
// runtime's state object and helpers are passed in as dependencies.
import { annotationMatches } from "./reviewPresentation";

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "allRows"
  | "api"
  | "applyRecordChanges"
  | "canUse"
  | "dateKeys"
  | "hasCapability"
  | "isResearcher"
  | "label"
  | "memoCorpus"
  | "navigateTo"
  | "notifyToast"
  | "persistFileNow"
  | "persistPrefs"
  | "recordStores"
  | "refreshStores"
  | "reviewItemFromKey"
  | "reviewKey"
  | "syncUrl"
  | "tr";
type Deps = { state: Loose } & Record<Helper, Fn>;

export function createAnnotationsWorkspace(deps: Deps) {
  const {
    state,
    allRows,
    api,
    applyRecordChanges,
    canUse,
    dateKeys,
    hasCapability,
    isResearcher,
    label,
    memoCorpus,
    navigateTo,
    notifyToast,
    persistFileNow,
    persistPrefs,
    recordStores,
    refreshStores,
    reviewItemFromKey,
    reviewKey,
    syncUrl,
    tr,
  } = deps;
  function serverAnnotationItems() {
    return (state.serverAnnotations || []).map((annotation: Any) => ({
      file: null,
      record: {
        record_id: annotation.record_id,
        work: annotation.work || "",
        page_start: annotation.page_start,
        page_end: annotation.page_end,
        _chroma_id: annotation.record_id,
      },
      index: null,
      annotation,
      annotationIndex: null,
      work: String(annotation.work || "(Untitled work)"),
      server: true,
      store: annotation.store || "",
    }));
  }
  async function refreshServerAnnotations(force = false) {
    if (isResearcher() && !hasCapability("annotations.read")) {
      state.serverAnnotations = [];
      state.serverAnnotationsStore = "";
      return [];
    }
    const storeName = isResearcher() ? String(state.activeStore || "") : "";
    if (
      !force &&
      Date.now() - Number(state.annotationsFetchedAt || 0) < 15000 &&
      (!isResearcher() || state.serverAnnotationsStore === storeName)
    )
      return state.serverAnnotations || [];
    try {
      const suffix = storeName ? `?store=${encodeURIComponent(storeName)}` : "";
      const data = await api(`/api/annotations${suffix}`);
      state.serverAnnotations = data.annotations || [];
      state.serverAnnotationsStore = storeName;
      state.annotationsFetchedAt = Date.now();
    } catch (error) {
      console.warn("Could not load shared annotations", error);
    }
    return state.serverAnnotations || [];
  }
  function allAnnotations() {
    const local = isResearcher()
      ? []
      : memoCorpus("annotations-all", () => {
          const items: Loose[] = [];
          for (const { file, record, index } of allRows()) {
            const annotations = Array.isArray(record.annotations) ? record.annotations : [];
            annotations.forEach((annotation: Any, annotationIndex: Any) =>
              items.push({
                file,
                record,
                index,
                annotation,
                annotationIndex,
                work: String(record.work || "(Untitled work)"),
                server: false,
              }),
            );
          }
          return items;
        });
    // Administrator annotations are mirrored to the shared annotation store so
    // researcher accounts can see them. Avoid showing the local + shared copy
    // twice in an administrator workspace.
    const mirroredIds = new Set(
      local.map((item: Any) => String(item.annotation?.shared_annotation_id || "")).filter(Boolean),
    );
    const shared = serverAnnotationItems().filter(
      (item: Any) => !mirroredIds.has(String(item.annotation?.id || "")),
    );
    return [...local, ...shared].sort(
      (a, b) =>
        new Date(b.annotation.created_at || 0).getTime() -
        new Date(a.annotation.created_at || 0).getTime(),
    );
  }
  function recentAnnotations(limit = 10) {
    return allAnnotations().slice(0, limit);
  }
  function annotationTimeline(days = 14) {
    const keys = dateKeys(days),
      counts = new Map<string, number>(keys.map((key: Any) => [key, 0]));
    for (const item of allAnnotations()) {
      const key = String(item.annotation?.created_at || "").slice(0, 10);
      if (counts.has(key)) counts.set(key, (counts.get(key) || 0) + 1);
    }
    return keys.map((key: Any) => ({ key, value: counts.get(key) || 0 }));
  }
  function getAnnotationsWorkspaceSnapshot() {
    const all = allAnnotations();
    const query = String(state.annotationSearch || "")
      .trim()
      .toLocaleLowerCase();
    const filtered = all.filter((item) => annotationMatches(item, query));
    const byWork = new Map();
    for (const item of filtered) {
      if (!byWork.has(item.work)) byWork.set(item.work, []);
      byWork.get(item.work).push(item);
    }
    return {
      query: String(state.annotationSearch || ""),
      view: state.annotationView === "recent" ? "recent" : "works",
      annotations: filtered.map(annotationWorkspaceItem),
      groups: [...byWork.entries()]
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([work, items]) => ({
          work,
          annotations: items.map(annotationWorkspaceItem),
          records: new Set(items.map((item: Any) => item.record?.record_id || item.index)).size,
        })),
      total: filtered.length,
    };
  }
  function annotationWorkspaceItem(item: Any) {
    const annotation = item.annotation || {};
    const canDeleteServer =
      item.server &&
      (state.userContext?.role === "admin" ||
        Number(annotation.user_id || 0) === Number(state.userContext?.id || -1));
    const canDeleteLocal = !item.server && canUse("editLocalRecords");
    return {
      id: String(
        annotation.id || `${item.file?.id || "annotation"}-${item.index}-${item.annotationIndex}`,
      ),
      record_id: String(item.record?.record_id || tr("nav.record")),
      work: item.work,
      field: annotation.field ? label(annotation.field) : tr("annotations.record_note"),
      quote: String(annotation.quote || ""),
      note: String(annotation.note || ""),
      tags: Array.isArray(annotation.tags) ? annotation.tags.map(String) : [],
      author: String(
        annotation.initiated_by || annotation.author || tr("annotations.unknown_author"),
      ),
      source: item.server
        ? annotation.store || tr("annotations.shared")
        : String(item.file?.name || ""),
      created_at: annotation.created_at || null,
      server: Boolean(item.server),
      removable: Boolean(canDeleteServer || canDeleteLocal),
      local_file_id: item.file?.id || null,
      local_index: item.index == null ? null : Number(item.index),
      local_annotation_index: item.annotationIndex == null ? null : Number(item.annotationIndex),
      shared_annotation_id: annotation.shared_annotation_id || null,
    };
  }
  async function loadAnnotationsWorkspace(force = false) {
    if (isResearcher() && !state.activeStore) {
      try {
        await refreshStores();
        state.activeStore = recordStores()[0]?.name || "";
      } catch (error) {
        console.warn("Could not select an annotations store", error);
      }
    }
    await refreshServerAnnotations(
      force || (isResearcher() && state.serverAnnotationsStore !== String(state.activeStore || "")),
    );
    return getAnnotationsWorkspaceSnapshot();
  }
  function setAnnotationsWorkspaceQuery(value: Any) {
    state.annotationSearch = String(value || "");
    persistPrefs();
    syncUrl({ replace: true });
  }
  function setAnnotationsWorkspaceView(value: Any) {
    state.annotationView = value === "recent" ? "recent" : "works";
    persistPrefs();
    syncUrl({ replace: true });
  }
  function openAnnotationsWorkspaceRecord(item: Any) {
    if (item.server) {
      state.activeStore = String(item.source || state.activeStore || "");
      state.researcherRecordId = String(item.record_id || "");
      persistPrefs();
      navigateTo("record");
      return;
    }
    navigateTo("record", { fileId: item.local_file_id, index: item.local_index });
  }
  function openAnnotationsWorkspaceWork(work: Any) {
    state.workOverview = String(work || "");
    persistPrefs();
    navigateTo("works");
  }
  async function removeAnnotationsWorkspaceItem(item: Any) {
    if (!item.removable) return;
    if (item.server) {
      await api(`/api/annotations/${encodeURIComponent(item.id)}`, { method: "DELETE" });
    } else {
      const local = reviewItemFromKey(reviewKey(item.local_file_id, item.local_index));
      const annotations = Array.isArray(local?.record?.annotations) ? local.record.annotations : [];
      const annotationIndex = Number(item.local_annotation_index);
      const annotation = Number.isInteger(annotationIndex) ? annotations[annotationIndex] : null;
      if (!local || !annotation) return;
      const sharedId = String(annotation.shared_annotation_id || "").trim();
      if (sharedId) {
        try {
          await api(`/api/annotations/${encodeURIComponent(sharedId)}`, { method: "DELETE" });
        } catch (error) {
          if (Number((error as Loose)?.status || 0) !== 404) throw error;
        }
      }
      applyRecordChanges(
        local.file,
        local.index,
        { annotations: annotations.filter((_: Any, index: Any) => index !== annotationIndex) },
        { source: "annotation-delete" },
      );
      await persistFileNow(local.file);
    }
    state.annotationsFetchedAt = 0;
    await refreshServerAnnotations(true);
    notifyToast(tr("annotations.removed"), { tone: "success" });
  }
  return {
    serverAnnotationItems,
    refreshServerAnnotations,
    allAnnotations,
    recentAnnotations,
    annotationTimeline,
    getAnnotationsWorkspaceSnapshot,
    annotationWorkspaceItem,
    loadAnnotationsWorkspace,
    setAnnotationsWorkspaceQuery,
    setAnnotationsWorkspaceView,
    openAnnotationsWorkspaceRecord,
    openAnnotationsWorkspaceWork,
    removeAnnotationsWorkspaceItem,
  };
}
