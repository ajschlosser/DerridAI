/* Copyright 2026 Aaron John Schlosser, PhD. */

type Tr = (key: string, fallback?: string) => string;
type Trf = (key: string, fallback: string, values?: Record<string, unknown>) => string;

/** Toasts and confirm copy owned by job dialogs, not inline English. */
export function createJobDialogCopy(tr: Tr, trf: Trf) {
  return {
    operationRemoved: tr(
      "jobs.toast.operation_removed",
      "This operation was removed and has been cleared from the activity view",
    ),
    loadDetailsFailed: (error: string) =>
      trf("jobs.toast.load_details_failed", "Could not load operation details: {error}", { error }),
    openResultFailed: tr("jobs.toast.open_result_failed", "Could not open operation result"),
    renderResultFailed: tr("jobs.toast.render_result_failed", "Could not render operation result"),
    refreshFailed: (error: string) =>
      trf("jobs.toast.refresh_failed", "Could not refresh review results: {error}", { error }),
    discardTitle: tr("jobs.toast.discard_title", "Discard pending LLM review?"),
    discardMessage: tr(
      "jobs.toast.discard_message",
      "Discard all currently pending proposed changes, stop the review if it is still running, and remove this operation from the queue?",
    ),
    discardConfirm: tr("jobs.toast.discard_confirm", "Discard pending & remove"),
    discardCancel: tr("jobs.toast.discard_cancel", "Keep review"),
    rejectedRemoved: tr(
      "jobs.toast.rejected_removed",
      "LLM review rejected and removed from the operations queue",
    ),
    rejectFailed: (error: string) =>
      trf("jobs.toast.reject_failed", "Could not reject LLM review: {error}", { error }),
    noResultsSelected: tr("jobs.toast.no_results_selected", "No LLM results selected"),
    accepted: (results: number, fields: number, pending: number) =>
      trf(
        "jobs.toast.accepted",
        "Accepted {results} pending result(s) · {fields} tracked field changes · {pending} pending",
        { results, fields, pending },
      ),
    localAppliedQueueFailed: (error: string) =>
      trf(
        "jobs.toast.local_applied_queue_failed",
        "Local changes were applied, but the operation queue could not be updated: {error}",
        { error },
      ),
    selectToReject: tr("jobs.toast.select_to_reject", "Select proposed changes to reject"),
    rejectedRemain: (pending: number) =>
      trf(
        "jobs.toast.rejected_remain",
        "Rejected selected proposed changes · {pending} pending changes remain",
        { pending },
      ),
    rejectSelectedFailed: (error: string) =>
      trf("jobs.toast.reject_selected_failed", "Could not reject selected changes: {error}", { error }),
    sourceGone: tr("jobs.toast.source_gone", "The source record is no longer loaded"),
    sourceGoneWorkspace: tr(
      "jobs.toast.source_gone_workspace",
      "The source record is no longer loaded in this workspace",
    ),
    resultUnavailableTitle: tr("jobs.toast.result_unavailable_title", "Result unavailable"),
    resultUnavailable: tr(
      "jobs.toast.result_unavailable",
      "This completed LLM operation does not contain a retained result. Open full details to inspect the operation.",
    ),
    configureProvider: tr("jobs.toast.configure_provider", "Configure an LLM provider first"),
    chooseProfile: tr(
      "jobs.toast.choose_profile",
      "Choose an available provider profile before continuing.",
    ),
    profileUnsupported: tr(
      "jobs.toast.profile_unsupported",
      "The selected provider profile is not supported by this operation.",
    ),
    selectModel: tr("jobs.toast.select_model", "Select a model before continuing."),
    gradeRequiresQa: tr(
      "jobs.toast.grade_requires_qa",
      "A completed Research question and answer are required before grading.",
    ),
    startedBackground: (title: string) =>
      trf("jobs.toast.started_background", "{title} started in background", { title }),
    failed: (title: string, error: string) =>
      trf("jobs.toast.failed", "{title} failed: {error}", { title, error }),
    invalidDraft: (error: string) =>
      trf("jobs.toast.invalid_draft", "Invalid draft JSON: {error}", { error }),
    chooseDestination: tr(
      "jobs.toast.choose_destination",
      "Choose a JSONL file, a Chroma collection, or both.",
    ),
    jsonlGone: tr("jobs.toast.jsonl_gone", "Selected JSONL file is no longer loaded"),
    chromaUpsertFailed: (error: string) =>
      trf(
        "jobs.toast.chroma_upsert_failed",
        "Draft was added to JSONL where selected, but Chroma upsert failed: {error}",
        { error },
      ),
    draftAddedBoth: (id: string) =>
      trf("jobs.toast.draft_added_both", "Draft {id} added to JSONL and Chroma", { id }),
    draftAddedJsonl: (id: string) =>
      trf("jobs.toast.draft_added_jsonl", "Draft {id} added to JSONL", { id }),
    draftAddedChroma: (id: string) =>
      trf("jobs.toast.draft_added_chroma", "Draft {id} added to Chroma", { id }),
  };
}
