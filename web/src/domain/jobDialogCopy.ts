/* Copyright 2026 Aaron John Schlosser, PhD. */
import { bindCopy } from "../i18n/bindCopy";

type Tr = (key: string, fallback?: string) => string;
type Trf = (key: string, fallback: string, values?: Record<string, unknown>) => string;

/** Toasts and confirm copy owned by job dialogs, not inline English. */
export function createJobDialogCopy(translate: Tr, interpolate: Trf) {
  const { tr, trf } = bindCopy(translate, interpolate);
  return {
    operationRemoved: tr("jobs.toast.operation_removed"),
    loadDetailsFailed: (error: string) => trf("jobs.toast.load_details_failed", { error }),
    openResultFailed: tr("jobs.toast.open_result_failed"),
    renderResultFailed: tr("jobs.toast.render_result_failed"),
    refreshFailed: (error: string) => trf("jobs.toast.refresh_failed", { error }),
    discardTitle: tr("jobs.toast.discard_title"),
    discardMessage: tr("jobs.toast.discard_message"),
    discardConfirm: tr("jobs.toast.discard_confirm"),
    discardCancel: tr("jobs.toast.discard_cancel"),
    rejectedRemoved: tr("jobs.toast.rejected_removed"),
    rejectFailed: (error: string) => trf("jobs.toast.reject_failed", { error }),
    noResultsSelected: tr("jobs.toast.no_results_selected"),
    accepted: (results: number, fields: number, pending: number) =>
      trf("jobs.toast.accepted", { results, fields, pending }),
    localAppliedQueueFailed: (error: string) =>
      trf("jobs.toast.local_applied_queue_failed", { error }),
    selectToReject: tr("jobs.toast.select_to_reject"),
    rejectedRemain: (pending: number) => trf("jobs.toast.rejected_remain", { pending }),
    rejectSelectedFailed: (error: string) => trf("jobs.toast.reject_selected_failed", { error }),
    sourceGone: tr("jobs.toast.source_gone"),
    sourceGoneWorkspace: tr("jobs.toast.source_gone_workspace"),
    resultUnavailableTitle: tr("jobs.toast.result_unavailable_title"),
    resultUnavailable: tr("jobs.toast.result_unavailable"),
    configureProvider: tr("jobs.toast.configure_provider"),
    chooseProfile: tr("jobs.toast.choose_profile"),
    profileUnsupported: tr("jobs.toast.profile_unsupported"),
    selectModel: tr("jobs.toast.select_model"),
    gradeRequiresQa: tr("jobs.toast.grade_requires_qa"),
    startedBackground: (title: string) => trf("jobs.toast.started_background", { title }),
    failed: (title: string, error: string) => trf("jobs.toast.failed", { title, error }),
    invalidDraft: (error: string) => trf("jobs.toast.invalid_draft", { error }),
    chooseDestination: tr("jobs.toast.choose_destination"),
    jsonlGone: tr("jobs.toast.jsonl_gone"),
    chromaUpsertFailed: (error: string) => trf("jobs.toast.chroma_upsert_failed", { error }),
    draftAddedBoth: (id: string) => trf("jobs.toast.draft_added_both", { id }),
    draftAddedJsonl: (id: string) => trf("jobs.toast.draft_added_jsonl", { id }),
    draftAddedChroma: (id: string) => trf("jobs.toast.draft_added_chroma", { id }),
  };
}
