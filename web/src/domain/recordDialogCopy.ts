/* Copyright 2026 Aaron John Schlosser, PhD. */

type Tr = (key: string, fallback?: string) => string;
type Trf = (key: string, fallback: string, values?: Record<string, unknown>) => string;

/** Toasts and confirm copy owned by record dialogs. */
export function createRecordDialogCopy(tr: Tr, trf: Trf) {
  return {
    mergeNeedTwo: tr("records.toast.merge_need_two", "Open at least two JSONL files to merge"),
    selectFile: tr("records.toast.select_file", "Select at least one file"),
    merged: (tabs: number, records: string) =>
      trf("records.toast.merged", "Merged and replaced {tabs} tabs · {records} records", {
        tabs,
        records,
      }),
    loadFirst: tr("records.toast.load_first", "Load JSONL records first"),
    noScope: tr("records.toast.no_scope", "No records are in the selected scope"),
    alreadyValue: tr("records.toast.already_value", "Every target record already has that value"),
    bulkTitle: tr("records.toast.bulk_title", "Apply bulk field update?"),
    bulkMessage: (field: string, count: string) =>
      trf("records.toast.bulk_message", "Set {field} on {count} record(s)?", { field, count }),
    bulkConfirm: tr("records.toast.bulk_confirm", "Apply update"),
    bulkUpdated: (field: string, records: string, changes: string) =>
      trf(
        "records.toast.bulk_updated",
        "Updated {field} on {records} records · {changes} audited changes",
        { field, records, changes },
      ),
    noScopeOcr: tr("records.toast.no_scope_ocr", "No records in that scope"),
    ocrTitle: tr("records.toast.ocr_title", "Run OCR cleanup?"),
    ocrMessage: (count: string) =>
      trf("records.toast.ocr_message", "Run conservative OCR cleanup on {count} records?", { count }),
    ocrConfirm: tr("records.toast.ocr_confirm", "Run cleanup"),
    saveFailed: tr("records.toast.save_failed", "Could not save record"),
    saved: (count: number) =>
      trf("records.toast.saved", "Saved {count} tracked change(s)", { count }),
    noChanges: tr("records.toast.no_changes", "No changes to save"),
    parseFailed: tr("records.toast.parse_failed", "Could not parse edited record"),
    chromaUpdated: tr("records.toast.chroma_updated", "Chroma record updated"),
    chromaFailed: (error: string) =>
      trf("records.toast.chroma_failed", "Chroma update failed: {error}", { error }),
    noHistory: tr("records.toast.no_history", "This record has no update history"),
    nothingToRestore: tr("records.toast.nothing_to_restore", "No record fields needed restoring"),
    restoredFields: (count: number, label: string) =>
      trf("records.toast.restored_fields", "Restored {count} field(s) from {label}", { count, label }),
    restoreOriginalTitle: tr("records.toast.restore_original_title", "Restore original record?"),
    restoreOriginalMessage: tr(
      "records.toast.restore_original_message",
      "Restore every field to its state before the tracked update history? The restoration itself will be recorded, so you can move forward again later.",
    ),
    restoreOriginalConfirm: tr("records.toast.restore_original_confirm", "Restore original"),
    alreadyOriginal: tr(
      "records.toast.already_original",
      "The record already matches its original tracked state",
    ),
    restoredOriginal: (count: number) =>
      trf("records.toast.restored_original", "Restored original record state · {count} fields changed", {
        count,
      }),
    historyCleared: tr("records.toast.history_cleared", "Record update history cleared"),
    vectorRequired: tr("records.toast.vector_required", "Vector database required"),
    selectCollection: tr("records.toast.select_collection", "Select a Chroma collection first"),
    selectQueued: tr("records.toast.select_queued", "Select at least one queued record"),
    bulkEditTitle: tr("ui.bulk_edit", "Bulk edit field"),
  };
}
