/* Copyright 2026 Aaron John Schlosser, PhD. */

// The Compare library: an index for finding a workspace record from a search-record key, and the paste-side library
// records for record comparison. Moved verbatim from the legacy runtime; the runtime's state object and helpers are
// passed in as dependencies.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "allRows"
  | "isResearcher"
  | "loadStorePage"
  | "memoCorpus"
  | "recordOptionLabel"
  | "refreshStores"
  | "researcherDbRecords";
type Deps = { state: Loose } & Record<Helper, Fn>;

export function createCompareLibrary(deps: Deps) {
  const {
    state,
    allRows,
    isResearcher,
    loadStorePage,
    memoCorpus,
    recordOptionLabel,
    refreshStores,
    researcherDbRecords,
  } = deps;
  function compareSearchIndex() {
    return memoCorpus("compare-search-index", () =>
      allRows().map(({ file, record, index }: Any) => {
        const labelText = recordOptionLabel(file, record, index);
        return {
          value: `${file.id}::${index}`,
          label: labelText,
          search: `${labelText} ${record.document_author || ""}`.toLocaleLowerCase(),
        };
      }),
    );
  }
  function lookupRecord(key: Any) {
    if (!key) return null;
    const [fid, i] = key.split("::");
    const f = state.files.find((x: Any) => x.id === fid);
    return f ? { file: f, index: +i, record: f.records[+i] } : null;
  }
  function getCompareLibrary() {
    if (isResearcher()) {
      return researcherDbRecords().map((record: Any) => {
        const id = String(record._chroma_id || record.record_id || "");
        const label = `${record.record_id || id} · ${record.work || ""}`;
        return {
          value: id,
          label,
          search: `${label} ${record.document_author || ""}`.toLocaleLowerCase(),
        };
      });
    }
    return compareSearchIndex();
  }
  function getCompareRecord(key: Any) {
    if (!key) return null;
    if (isResearcher()) {
      const record = researcherDbRecords().find(
        (item: Any) => String(item._chroma_id || item.record_id || "") === String(key),
      );
      if (!record) return null;
      const copy = { ...record };
      delete copy._chroma_id;
      delete copy._researcher_text_policy;
      return { record: copy, label: `${record.record_id || key} · ${record.work || ""}` };
    }
    const item = lookupRecord(key);
    if (!item?.record) return null;
    return { record: item.record, label: recordOptionLabel(item.file, item.record, item.index) };
  }
  async function ensureCompareLibrary() {
    if (!isResearcher()) return getCompareLibrary();
    if (!state.activeStore) {
      try {
        await refreshStores();
      } catch {
        /* stores may be unavailable */
      }
    }
    if (!state.storeRecords.length && state.activeStore) {
      state.storePageSize = Math.max(Number(state.storePageSize || 50), 100);
      try {
        await loadStorePage();
      } catch {
        /* page load is best-effort for Compare */
      }
    }
    return getCompareLibrary();
  }
  return {
    compareSearchIndex,
    lookupRecord,
    getCompareLibrary,
    getCompareRecord,
    ensureCompareLibrary,
  };
}
