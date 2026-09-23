/* Copyright 2026 Aaron John Schlosser, PhD. */

// The Record workspace: the record the Record view shows (loaded or from the database), moving between records, and the
// commands it sends (evidence, selection, citation and JSON copy, saving edits, annotations, the primary action). Moved
// verbatim from the legacy runtime; the runtime's state object and helpers are passed in as dependencies.
import { fullCitation, inlineCitation, mlaPageSpan } from "./citations";
import { compactRecordHistory, pdfLinks, recordPayload } from "./recordPayloads";
import { countOccurrences } from "./recordQuery";
import { cloneAuditValue } from "./recordValues";

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "activeFile"
  | "api"
  | "applyRecordChanges"
  | "canAccessPage"
  | "canUse"
  | "cleanRecord"
  | "copyJsonToClipboard"
  | "dbEvidenceKey"
  | "evidenceIsSelected"
  | "hasCapability"
  | "hasCorpusDb"
  | "isResearcher"
  | "linkPdfPage"
  | "loadStorePage"
  | "loadedPdfPagesForRecord"
  | "navigateTo"
  | "normalizedRecordAnnotation"
  | "openLoadedPdfPage"
  | "openPdfExplorerWorkspace"
  | "openRecordHistoryBrowser"
  | "openTouchup"
  | "pdfDisplayTitle"
  | "persistPrefs"
  | "refreshServerAnnotations"
  | "refreshStores"
  | "researcherDbRecords"
  | "reviewKey"
  | "searchByMetadata"
  | "selectedIndex"
  | "selectedRecord"
  | "setReviewSelected"
  | "shell"
  | "syncUrl"
  | "toast"
  | "toggleDbEvidence"
  | "toggleWorkspaceEvidence"
  | "tr"
  | "uid"
  | "unlinkAllPdfLinks"
  | "unlinkPdfLink"
  | "upsertRows"
  | "workspaceEvidenceKey";
type Deps = { state: Loose } & Record<Helper, Fn>;

export function createRecordWorkspace(deps: Deps) {
  const {
    state,
    activeFile,
    api,
    applyRecordChanges,
    canAccessPage,
    canUse,
    cleanRecord,
    copyJsonToClipboard,
    dbEvidenceKey,
    evidenceIsSelected,
    hasCapability,
    hasCorpusDb,
    isResearcher,
    linkPdfPage,
    loadStorePage,
    loadedPdfPagesForRecord,
    navigateTo,
    normalizedRecordAnnotation,
    openLoadedPdfPage,
    openPdfExplorerWorkspace,
    openRecordHistoryBrowser,
    openTouchup,
    pdfDisplayTitle,
    persistPrefs,
    refreshServerAnnotations,
    refreshStores,
    researcherDbRecords,
    reviewKey,
    searchByMetadata,
    selectedIndex,
    selectedRecord,
    setReviewSelected,
    shell,
    syncUrl,
    toast,
    toggleDbEvidence,
    toggleWorkspaceEvidence,
    tr,
    uid,
    unlinkAllPdfLinks,
    unlinkPdfLink,
    upsertRows,
    workspaceEvidenceKey,
  } = deps;
  function recordWorkspaceRecord(record: Any) {
    const out = recordPayload(record, { includeChromaId: true });
    delete out.updates;
    delete out.annotations;
    return cloneAuditValue(out);
  }
  async function researcherCurrentRecord() {
    try {
      await refreshServerAnnotations();
    } catch {
      // Best effort: keep going with what we have.
    }
    if (!state.activeStore) {
      try {
        await refreshStores();
      } catch {
        // Best effort: keep going with what we have.
      }
      if (!state.activeStore) return null;
    }
    let id = state.researcherRecordId;
    let record = researcherDbRecords().find(
      (item: Any) => String(item._chroma_id || item.record_id || "") === String(id),
    );
    if (!record && id) {
      try {
        record = await api(
          `/api/stores/${encodeURIComponent(state.activeStore)}/records/${encodeURIComponent(id)}`,
        );
      } catch {
        record = null;
      }
    }
    if (!record) {
      if (!state.storeRecords.length) {
        try {
          await loadStorePage();
        } catch {
          // Best effort: keep going with what we have.
        }
      }
      record = state.storeRecords[0] || null;
      id = String(record?._chroma_id || record?.record_id || "");
      state.researcherRecordId = id;
    }
    return record;
  }
  async function getRecordWorkspaceSnapshot() {
    if (isResearcher()) {
      const record = await researcherCurrentRecord();
      if (!record)
        return {
          available: false,
          mode: "database",
          reason: tr("research.no_records"),
        };
      const id = String(record._chroma_id || record.record_id || state.researcherRecordId || "");
      const list = researcherDbRecords();
      const currentIndex = list.findIndex(
        (item: Any) => String(item._chroma_id || item.record_id || "") === id,
      );
      const annotations = (state.serverAnnotations || [])
        .filter(
          (item: Any) =>
            String(item.store || "") === String(state.activeStore) &&
            String(item.record_id || "") === id,
        )
        .map((item: Any, index: Any) =>
          normalizedRecordAnnotation(item, index, { removable: false }),
        );
      const text = String(record.text || "");
      const q = String(state.recordFind || "");
      const key = dbEvidenceKey(state.activeStore, id);
      return {
        available: true,
        mode: "database",
        record: recordWorkspaceRecord(record),
        record_id: id,
        file_name: null,
        collection: state.activeStore || "",
        current_index: currentIndex,
        total: list.length,
        has_previous: currentIndex > 0,
        has_next: currentIndex >= 0 && currentIndex < list.length - 1,
        find_query: q,
        find_matches: countOccurrences(text, q),
        word_count: text.trim() ? text.trim().split(/\s+/).length : 0,
        character_count: text.length,
        evidence_selected: evidenceIsSelected(key),
        review_selected: false,
        annotations,
        pdf_links: [],
        history: [],
        history_count: 0,
        inline_citation: inlineCitation(record),
        full_citation: fullCitation(record),
        page_span: mlaPageSpan(record),
        capabilities: {
          edit: false,
          annotate: hasCapability("annotations.write"),
          evidence: hasCapability("evidence.select"),
          review: false,
          upsert: false,
          llm_review: false,
          pdf: false,
          history: false,
          copy: true,
        },
        pdf: { loaded: false, related: false, current_page: null, title: "", name: "" },
      };
    }
    const file = activeFile(),
      index = file ? selectedIndex(file) : 0,
      record = file?.records?.[index];
    if (!file || !record)
      return {
        available: false,
        mode: "workspace",
        reason: tr("record.no_record_selected"),
      };
    const pointer = { kind: "workspace", fileId: file.id, index };
    if (JSON.stringify(state.lastViewedRecord) !== JSON.stringify(pointer)) {
      state.lastViewedRecord = pointer;
      persistPrefs();
    }
    const text = String(record.text || "");
    const q = String(state.recordFind || "");
    const links = pdfLinks(record);
    const loadedPages = loadedPdfPagesForRecord(record);
    const related = Boolean(state.pdf.file && state.pdf.name && loadedPages.length);
    const annotations = (Array.isArray(record.annotations) ? record.annotations : []).map(
      (item: Any, annotationIndex: Any) =>
        normalizedRecordAnnotation(item, annotationIndex, { removable: true }),
    );
    const key = workspaceEvidenceKey(file, index);
    return {
      available: true,
      mode: "workspace",
      record: recordWorkspaceRecord(record),
      record_id: String(record.record_id || index + 1),
      file_id: file.id,
      file_name: file.name,
      collection: state.activeStore || "",
      current_index: index,
      total: file.records.length,
      has_previous: index > 0,
      has_next: index < file.records.length - 1,
      find_query: q,
      find_matches: countOccurrences(text, q),
      word_count: text.trim() ? text.trim().split(/\s+/).length : 0,
      character_count: text.length,
      evidence_selected: evidenceIsSelected(key),
      review_selected: state.reviewSelection.has(reviewKey(file, index)),
      annotations,
      pdf_links: cloneAuditValue(links),
      history: compactRecordHistory(record),
      history_count: Array.isArray(record.updates) ? record.updates.length : 0,
      inline_citation: inlineCitation(record),
      full_citation: fullCitation(record),
      page_span: mlaPageSpan(record),
      capabilities: {
        edit: canUse("editLocalRecords"),
        annotate: hasCapability("annotations.write"),
        evidence: hasCapability("evidence.select"),
        review: canUse("editLocalRecords"),
        upsert: canUse("manageCorpus") && hasCorpusDb(),
        llm_review: canUse("editLocalRecords"),
        pdf: canAccessPage("pdf"),
        history: canUse("editLocalRecords"),
        copy: true,
      },
      pdf: {
        loaded: Boolean(state.pdf.file && state.pdf.name),
        related,
        current_page: state.pdf.page || null,
        current_linked: related && loadedPages.includes(Number(state.pdf.page)),
        title: pdfDisplayTitle(),
        name: state.pdf.name || "",
        loaded_pages: loadedPages,
      },
    };
  }
  async function recordWorkspaceNavigate(delta: Any) {
    const step = Number(delta) || 0;
    if (!step) return getRecordWorkspaceSnapshot();
    if (isResearcher()) {
      const current = await researcherCurrentRecord();
      if (!current) return getRecordWorkspaceSnapshot();
      const id = String(current._chroma_id || current.record_id || "");
      const list = researcherDbRecords();
      const index = list.findIndex(
        (item: Any) => String(item._chroma_id || item.record_id || "") === id,
      );
      const next = list[index + step];
      if (next) {
        state.researcherRecordId = String(next._chroma_id || next.record_id || "");
        persistPrefs();
        syncUrl({ replace: true });
        shell();
      }
      return getRecordWorkspaceSnapshot();
    }
    const file = activeFile();
    if (!file) return getRecordWorkspaceSnapshot();
    const index = selectedIndex(file),
      next = Math.max(0, Math.min(file.records.length - 1, index + step));
    state.selected[file.id] = next;
    persistPrefs();
    syncUrl({ replace: true });
    shell();
    return getRecordWorkspaceSnapshot();
  }
  function setRecordWorkspaceFind(value: Any) {
    state.recordFind = String(value || "");
    persistPrefs();
    syncUrl({ replace: true });
    return state.recordFind;
  }
  async function toggleCurrentRecordEvidence() {
    if (isResearcher()) {
      const record = await researcherCurrentRecord();
      if (!record) return getRecordWorkspaceSnapshot();
      toggleDbEvidence(
        state.activeStore,
        String(record._chroma_id || record.record_id || ""),
        record,
      );
    } else {
      const file = activeFile();
      if (file) toggleWorkspaceEvidence(file, selectedIndex(file));
    }
    return getRecordWorkspaceSnapshot();
  }
  async function toggleCurrentRecordReviewSelection() {
    if (isResearcher()) return getRecordWorkspaceSnapshot();
    const file = activeFile();
    if (!file) return getRecordWorkspaceSnapshot();
    const index = selectedIndex(file);
    const selected = state.reviewSelection.has(reviewKey(file, index));
    setReviewSelected(file, index, !selected);
    shell();
    return getRecordWorkspaceSnapshot();
  }
  async function copyCurrentRecordCitation(kind = "inline") {
    const snapshot = await getRecordWorkspaceSnapshot();
    if (!snapshot?.available) return false;
    const text = kind === "full" ? snapshot.full_citation : snapshot.inline_citation;
    try {
      await navigator.clipboard.writeText(String(text || ""));
      toast(
        tr(
          kind === "full" ? "record.full_citation_copied" : "record.inline_citation_copied",
          kind === "full" ? "Full citation copied" : "Inline citation copied",
        ),
        { tone: "success" },
      );
      return true;
    } catch (error) {
      toast(`${tr("record.copy_failed")}: ${(error as Error).message}`, {
        tone: "danger",
      });
      return false;
    }
  }
  async function copyCurrentRecordJson() {
    if (isResearcher()) {
      const record = await researcherCurrentRecord();
      if (!record) return false;
      await copyJsonToClipboard(recordWorkspaceRecord(record), tr("record.record_json"));
      return true;
    }
    const record = selectedRecord();
    if (!record) return false;
    await copyJsonToClipboard(recordWorkspaceRecord(record), tr("record.record_json"));
    return true;
  }
  async function saveCurrentRecordChanges(changes = {}) {
    if (isResearcher() || !canUse("editLocalRecords"))
      throw new Error(tr("permissions.record_edit_denied"));
    const file = activeFile();
    if (!file) throw new Error(tr("record.no_record_selected"));
    const index = selectedIndex(file);
    const safe: Loose = {};
    for (const [field, value] of Object.entries(changes || {})) {
      if (field !== "updates" && !String(field).startsWith("_")) safe[field] = value;
    }
    const count = applyRecordChanges(file, index, safe, { source: "record_workspace" });
    shell();
    if (count) toast(tr("record.saved"), { tone: "success" });
    else toast(tr("record.no_changes"), { tone: "info" });
    return getRecordWorkspaceSnapshot();
  }
  async function addCurrentRecordAnnotation(payload: Loose = {}) {
    if (!hasCapability("annotations.write"))
      throw new Error(tr("permissions.annotations_denied"));
    const field = String(payload.field || "text"),
      quote = String(payload.quote || "").trim(),
      note = String(payload.note || "").trim(),
      tags = Array.isArray(payload.tags) ? payload.tags.map(String).filter(Boolean) : [];
    if (!quote && !note && !tags.length)
      throw new Error(tr("annotations.empty"));
    if (isResearcher()) {
      const record = await researcherCurrentRecord();
      if (!record) throw new Error(tr("record.no_record_selected"));
      await api("/api/annotations", {
        method: "POST",
        body: JSON.stringify({
          store: state.activeStore,
          record_id: String(record._chroma_id || record.record_id || ""),
          work: String(record.work || ""),
          page_start: record.page_start ?? null,
          page_end: record.page_end ?? null,
          field,
          quote,
          note,
          tags,
        }),
      });
      state.annotationsFetchedAt = 0;
      await refreshServerAnnotations(true);
      toast(tr("annotations.saved"), { tone: "success" });
      return getRecordWorkspaceSnapshot();
    }
    const file = activeFile();
    if (!file) throw new Error(tr("record.no_record_selected"));
    const index = selectedIndex(file),
      record = file.records[index];
    const shared = await api("/api/annotations", {
      method: "POST",
      body: JSON.stringify({
        store: state.activeStore || null,
        record_id: String(record._chroma_id || record.record_id || index + 1),
        work: String(record.work || ""),
        page_start: record.page_start ?? null,
        page_end: record.page_end ?? null,
        field,
        quote,
        note,
        tags,
      }),
    });
    const annotations = Array.isArray(record.annotations)
      ? record.annotations.map(cloneAuditValue)
      : [];
    annotations.push({
      id: uid(),
      shared_annotation_id: shared?.id || null,
      field,
      quote,
      note,
      tags,
      created_at: shared?.created_at || new Date().toISOString(),
      initiated_by: state.userContext?.username || null,
    });
    applyRecordChanges(file, index, { annotations }, { source: "annotation" });
    state.annotationsFetchedAt = 0;
    await refreshServerAnnotations(true);
    shell();
    toast(tr("annotations.saved"), { tone: "success" });
    return getRecordWorkspaceSnapshot();
  }
  async function removeCurrentRecordAnnotation(annotationId: Any) {
    if (isResearcher() || !canUse("editLocalRecords"))
      throw new Error(tr("permissions.record_edit_denied"));
    const file = activeFile();
    if (!file) throw new Error(tr("record.no_record_selected"));
    const index = selectedIndex(file),
      record = file.records[index];
    const annotations = Array.isArray(record.annotations)
      ? record.annotations.map(cloneAuditValue)
      : [];
    const at = annotations.findIndex(
      (item: Any, i: Any) =>
        String(item.id || item.shared_annotation_id || `annotation-${i}`) === String(annotationId),
    );
    if (at < 0) return getRecordWorkspaceSnapshot();
    const sharedId = annotations[at]?.shared_annotation_id;
    if (sharedId) {
      await api(`/api/annotations/${encodeURIComponent(sharedId)}`, { method: "DELETE" });
      state.annotationsFetchedAt = 0;
      await refreshServerAnnotations(true);
    }
    annotations.splice(at, 1);
    applyRecordChanges(file, index, { annotations }, { source: "annotation" });
    shell();
    toast(tr("annotations.removed"), { tone: "success" });
    return getRecordWorkspaceSnapshot();
  }
  async function currentRecordPrimaryAction(action: Any, payload: Loose = {}) {
    if (action === "upsert") {
      if (isResearcher() || !canUse("manageCorpus"))
        throw new Error(
          tr("permissions.corpus_denied"),
        );
      const file = activeFile();
      if (!file) return false;
      await upsertRows(
        [{ file, record: file.records[selectedIndex(file)], index: selectedIndex(file) }],
        "record",
      );
      return true;
    }
    if (action === "llm") {
      if (isResearcher() || !canUse("editLocalRecords"))
        throw new Error(
          tr("permissions.record_edit_denied"),
        );
      const file = activeFile();
      if (!file) return false;
      const index = selectedIndex(file);
      openTouchup([{ file, index, record: file.records[index], key: reviewKey(file, index) }]);
      return true;
    }
    if (action === "ocr") {
      if (isResearcher() || !canUse("editLocalRecords"))
        throw new Error(
          tr("permissions.record_edit_denied"),
        );
      const file = activeFile();
      if (!file) return false;
      cleanRecord(file, selectedIndex(file));
      return true;
    }
    if (action === "history") {
      if (isResearcher() || !canUse("editLocalRecords"))
        throw new Error(
          tr("permissions.record_edit_denied"),
        );
      const file = activeFile();
      if (!file) return false;
      openRecordHistoryBrowser(file, selectedIndex(file));
      return true;
    }
    if (action === "open_pdf") {
      if (!canAccessPage("pdf"))
        throw new Error(tr("permissions.pdf_denied"));
      const snapshot: Loose = await getRecordWorkspaceSnapshot();
      const link = snapshot?.pdf_links?.[Number(payload.index) || 0];
      if (!link) return false;
      if (state.pdf.file && link.pdf_file === state.pdf.name) openLoadedPdfPage(link.pdf_page);
      else {
        openPdfExplorerWorkspace();
        toast(
          tr(
            "record.open_pdf_first",
            `Open ${link.pdf_file} in PDF Explorer to jump to the linked page.`,
          ).replace("{file}", link.pdf_file),
          { tone: "info" },
        );
      }
      return true;
    }
    if (action === "pdf_explorer") {
      if (!canAccessPage("pdf"))
        throw new Error(tr("permissions.pdf_denied"));
      openPdfExplorerWorkspace();
      return true;
    }
    if (action === "link_pdf") {
      if (isResearcher()) return false;
      const file = activeFile();
      if (!file) return false;
      await linkPdfPage(file, selectedIndex(file), state.pdf.page);
      return true;
    }
    if (action === "remove_pdf") {
      if (isResearcher()) return false;
      const file = activeFile();
      if (!file) return false;
      const record = file.records[selectedIndex(file)],
        links = pdfLinks(record),
        link = links[Number(payload.index) || 0];
      if (link) unlinkPdfLink(file, selectedIndex(file), link);
      return true;
    }
    if (action === "remove_all_pdf") {
      if (isResearcher()) return false;
      const file = activeFile();
      if (!file) return false;
      unlinkAllPdfLinks(file, selectedIndex(file));
      return true;
    }
    return false;
  }
  function searchCurrentRecordMetadata(field: Any, value: Any, { contains = false } = {}) {
    return searchByMetadata(field, value, { contains });
  }
  function navigateRecordWorkspace(destination: Any) {
    if (["global", "works", "pdf"].includes(destination)) navigateTo(destination);
  }
  return {
    recordWorkspaceRecord,
    researcherCurrentRecord,
    getRecordWorkspaceSnapshot,
    recordWorkspaceNavigate,
    setRecordWorkspaceFind,
    toggleCurrentRecordEvidence,
    toggleCurrentRecordReviewSelection,
    copyCurrentRecordCitation,
    copyCurrentRecordJson,
    saveCurrentRecordChanges,
    addCurrentRecordAnnotation,
    removeCurrentRecordAnnotation,
    currentRecordPrimaryAction,
    searchCurrentRecordMetadata,
    navigateRecordWorkspace,
  };
}
