/* Copyright 2026 Aaron John Schlosser, PhD. */
import { bindCopy } from "../i18n/bindCopy";

type Tr = (key: string, fallback?: string) => string;
type Trf = (key: string, fallback: string, values?: Record<string, unknown>) => string;

/** Toasts and confirm copy owned by record dialogs. */
export function createRecordDialogCopy(translate: Tr, interpolate: Trf) {
  const { tr, trf } = bindCopy(translate, interpolate);
  return {
    mergeNeedTwo: tr("records.toast.merge_need_two"),
    selectFile: tr("records.toast.select_file"),
    merged: (tabs: number, records: string) =>
      trf("records.toast.merged", {
        tabs,
        records,
      }),
    loadFirst: tr("records.toast.load_first"),
    noScope: tr("records.toast.no_scope"),
    alreadyValue: tr("records.toast.already_value"),
    bulkTitle: tr("records.toast.bulk_title"),
    bulkMessage: (field: string, count: string) =>
      trf("records.toast.bulk_message", { field, count }),
    bulkConfirm: tr("records.toast.bulk_confirm"),
    bulkUpdated: (field: string, records: string, changes: string) =>
      trf("records.toast.bulk_updated", { field, records, changes }),
    noScopeOcr: tr("records.toast.no_scope_ocr"),
    ocrTitle: tr("records.toast.ocr_title"),
    ocrMessage: (count: string) => trf("records.toast.ocr_message", { count }),
    ocrConfirm: tr("records.toast.ocr_confirm"),
    saveFailed: tr("records.toast.save_failed"),
    saved: (count: number) => trf("records.toast.saved", { count }),
    noChanges: tr("records.toast.no_changes"),
    parseFailed: tr("records.toast.parse_failed"),
    chromaUpdated: tr("records.toast.chroma_updated"),
    chromaFailed: (error: string) => trf("records.toast.chroma_failed", { error }),
    noHistory: tr("records.toast.no_history"),
    nothingToRestore: tr("records.toast.nothing_to_restore"),
    restoredFields: (count: number, label: string) =>
      trf("records.toast.restored_fields", { count, label }),
    restoreOriginalTitle: tr("records.toast.restore_original_title"),
    restoreOriginalMessage: tr("records.toast.restore_original_message"),
    restoreOriginalConfirm: tr("records.toast.restore_original_confirm"),
    alreadyOriginal: tr("records.toast.already_original"),
    restoredOriginal: (count: number) =>
      trf("records.toast.restored_original", {
        count,
      }),
    historyCleared: tr("records.toast.history_cleared"),
    vectorRequired: tr("records.toast.vector_required"),
    selectCollection: tr("records.toast.select_collection"),
    selectQueued: tr("records.toast.select_queued"),
    bulkEditTitle: tr("ui.bulk_edit"),
  };
}
