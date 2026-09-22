/* Copyright 2026 Aaron John Schlosser, PhD. */

// Evidence and review selection: which workspace/database records are picked as Research evidence or marked for review.
// Moved verbatim from the legacy runtime; the runtime's state object and helpers are passed in as dependencies.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "fullCitation"
  | "hasCapability"
  | "inlineCitation"
  | "localRecordKey"
  | "persistPrefs"
  | "ragEvidenceRecordPayload"
  | "recordDbStatus"
  | "shellRefreshHook"
  | "storeReceipt"
  | "toast"
  | "tr"
  | "trf";
type Deps = { state: Loose } & Record<Helper, Fn>;

export function createEvidenceSelection(deps: Deps) {
  const {
    state,
    fullCitation,
    hasCapability,
    inlineCitation,
    localRecordKey,
    persistPrefs,
    ragEvidenceRecordPayload,
    recordDbStatus,
    shellRefreshHook,
    storeReceipt,
    toast,
    tr,
    trf,
  } = deps;
  function reviewKey(file: Any, index: Any) {
    return `${file.id}::${index}`;
  }
  function reviewItemFromKey(key: Any) {
    const split = String(key).lastIndexOf("::");
    if (split < 0) return null;
    const fileId = key.slice(0, split),
      index = Number(key.slice(split + 2));
    const file = state.files.find((f: Any) => f.id === fileId);
    if (!file || !Number.isInteger(index) || !file.records[index]) return null;
    return { file, index, record: file.records[index], key };
  }
  function selectedReviewItems() {
    return [...state.reviewSelection].map(reviewItemFromKey).filter(Boolean);
  }
  async function copyCitation(record: Any, kind = "inline") {
    const text = kind === "full" ? fullCitation(record) : inlineCitation(record);
    try {
      await navigator.clipboard.writeText(text);
      // Say exactly what reached the clipboard, so the reader can check it before pasting.
      toast(
        trf(
          kind === "full"
            ? "record.full_citation_copied_value"
            : "record.inline_citation_copied_value",
          kind === "full"
            ? "Copied full citation to the clipboard: {citation}"
            : "Copied inline citation to the clipboard: {citation}",
          { citation: text },
        ),
        { tone: "success", duration: 7000 },
      );
    } catch (error: Any) {
      toast(
        trf("record.copy_failed_reason", "Could not copy citation: {error}", {
          error: error?.message || String(error),
        }),
        { tone: "danger" },
      );
    }
  }
  function workspaceEvidenceKey(file: Any, index: Any) {
    return `workspace:${file.id}:${index}`;
  }
  function dbEvidenceKey(collection: Any, id: Any) {
    return `db:${collection}:${id}`;
  }
  function selectedEvidenceEntries() {
    return Object.values(state.selectedEvidence || {}).filter(Boolean);
  }
  function evidenceIsSelected(key: Any) {
    return Boolean(state.selectedEvidence?.[key]);
  }
  function setEvidence(key: Any, item: Any, selected = true) {
    if (!state.selectedEvidence || typeof state.selectedEvidence !== "object")
      state.selectedEvidence = {};
    if (selected) state.selectedEvidence[key] = item;
    else delete state.selectedEvidence[key];
    persistPrefs();
    shellRefreshHook();
  }
  function workspaceDbEvidenceTarget(file: Any, index: Any, record = file?.records?.[index]) {
    if (!record || !state.activeStore) return null;
    const status = recordDbStatus(file, index, record);
    if (!["synced", "exists"].includes(status.kind)) return null;
    const receipt = storeReceipt(state.activeStore, file, index);
    const key = localRecordKey(file, index);
    const confirmedId = state.storePresenceIds?.[state.activeStore]?.[key];
    const id = String(receipt?.chroma_id || confirmedId || record.record_id || "").trim();
    return id
      ? { collection: state.activeStore, id, key: dbEvidenceKey(state.activeStore, id) }
      : null;
  }
  function workspaceEvidenceSelectionKey(file: Any, index: Any) {
    const local = workspaceEvidenceKey(file, index);
    if (evidenceIsSelected(local)) return local;
    return workspaceDbEvidenceTarget(file, index)?.key || local;
  }
  function toggleWorkspaceEvidence(file: Any, index: Any) {
    if (!hasCapability("evidence.select")) {
      toast(tr("permissions.evidence_denied", "Your role cannot change selected evidence."), {
        tone: "warn",
      });
      return;
    }
    const record = file?.records?.[index];
    if (!record) return;
    const localKey = workspaceEvidenceKey(file, index);
    if (evidenceIsSelected(localKey)) {
      setEvidence(localKey, null, false);
      return;
    }
    const dbTarget = workspaceDbEvidenceTarget(file, index, record);
    if (dbTarget) {
      toggleDbEvidence(dbTarget.collection, dbTarget.id, record);
      return;
    }
    setEvidence(
      localKey,
      {
        key: localKey,
        kind: "workspace",
        file_id: file.id,
        index,
        record_id: record.record_id || "",
        work: record.work || "",
        page_start: record.page_start ?? record.page ?? null,
        page_end: record.page_end ?? null,
        speaker: record.speaker || null,
        position_holder: record.position_holder || null,
        stance: record.stance || null,
        discourse_role: record.discourse_role || null,
        target: record.target || null,
        proposition_status: record.proposition_status || null,
        inline_citation: record.inline_citation || null,
        text_preview: String(record.text || "")
          .replace(/\s+/g, " ")
          .trim()
          .slice(0, 280),
        label: `${record.record_id || `Record ${index + 1}`} · ${record.work || file.name}`,
      },
      true,
    );
  }
  function toggleDbEvidence(collection: Any, id: Any, record: Any = {}) {
    if (!hasCapability("evidence.select")) {
      toast(tr("permissions.evidence_denied", "Your role cannot change selected evidence."), {
        tone: "warn",
      });
      return;
    }
    if (!collection || !id) return;
    const key = dbEvidenceKey(collection, id);
    setEvidence(
      key,
      {
        key,
        kind: "db",
        collection,
        chroma_id: id,
        record_id: record.record_id || id,
        work: record.work || "",
        page_start: record.page_start ?? record.page ?? null,
        page_end: record.page_end ?? null,
        speaker: record.speaker || null,
        position_holder: record.position_holder || null,
        stance: record.stance || null,
        discourse_role: record.discourse_role || null,
        target: record.target || null,
        proposition_status: record.proposition_status || null,
        inline_citation: record.inline_citation || null,
        text_preview: String(record.text || "")
          .replace(/\s+/g, " ")
          .trim()
          .slice(0, 280),
        label: `${record.record_id || id} · ${record.work || collection}`,
      },
      !evidenceIsSelected(key),
    );
  }
  function clearSelectedEvidence() {
    if (!hasCapability("evidence.select")) {
      toast(tr("permissions.evidence_denied", "Your role cannot change selected evidence."), {
        tone: "warn",
      });
      return;
    }
    state.selectedEvidence = {};
    persistPrefs();
    shellRefreshHook();
  }
  function selectedEvidencePayload() {
    const payload = [];
    for (const item of selectedEvidenceEntries() as Any[]) {
      if (item.kind === "db")
        payload.push({ collection: item.collection, chroma_id: item.chroma_id });
      else if (item.kind === "workspace") {
        const file = state.files.find((file: Any) => file.id === item.file_id);
        const record = file?.records?.[Number(item.index)];
        if (record) payload.push({ record: ragEvidenceRecordPayload(record) });
      }
    }
    return payload;
  }
  function setReviewSelected(file: Any, index: Any, selected: Any) {
    const key = reviewKey(file, index);
    selected ? state.reviewSelection.add(key) : state.reviewSelection.delete(key);
    persistPrefs();
  }
  function clearReviewSelection() {
    state.reviewSelection.clear();
    persistPrefs();
  }
  return {
    reviewKey,
    reviewItemFromKey,
    selectedReviewItems,
    copyCitation,
    workspaceEvidenceKey,
    dbEvidenceKey,
    selectedEvidenceEntries,
    evidenceIsSelected,
    setEvidence,
    workspaceDbEvidenceTarget,
    workspaceEvidenceSelectionKey,
    toggleWorkspaceEvidence,
    toggleDbEvidence,
    clearSelectedEvidence,
    selectedEvidencePayload,
    setReviewSelected,
    clearReviewSelection,
  };
}
