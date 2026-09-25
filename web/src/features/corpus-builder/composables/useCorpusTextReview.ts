/* Copyright 2026 Aaron John Schlosser, PhD. */
import { ref, type Ref } from "vue";
import { corpusBuilderApi, type CorpusBuild, type CorpusRecord } from "../../../api/corpus";
import type { ProviderProfile } from "../../../api/system";
import type { ReviewViewport } from "./useCorpusReviewWorkspace";

type MessageTone = "error" | "notice";

export interface CorpusTextTouchupResult {
  source_text: string;
  proposed_text: string;
  changes: string[];
  warnings: string[];
  provider: string;
  model: string;
  proposal_id?: string;
  run_id?: string;
  created_at?: string;
  status?: string;
  no_change: boolean;
}

interface CorpusTextReviewOptions {
  currentBuild: Ref<CorpusBuild | null>;
  selectedBuildId: Ref<string>;
  selectedRecord: Ref<CorpusRecord | null>;
  records: Ref<CorpusRecord[]>;
  busy: Ref<string>;
  sourceTranscriptionOpen: Ref<boolean>;
  llmActionProviderId: Ref<string>;
  llmActionModel: Ref<string>;
  selectedProviderId: Ref<string>;
  providerProfiles: Ref<ProviderProfile[]>;
  directProfilePayloadWithModel: (
    profileId: string,
    modelOverride?: string,
  ) => Record<string, unknown> | null;
  captureReviewViewport: () => ReviewViewport;
  restoreReviewViewport: (
    snapshot: ReviewViewport,
    options?: { record?: boolean; inspector?: boolean },
  ) => Promise<void>;
  queueRecordRequest: (
    recordId: string | readonly string[],
    fields: string[],
    request: (rebase: boolean) => Promise<unknown>,
    onFailure?: () => void | Promise<void>,
    retryOnFailure?: boolean,
  ) => void;
  textDraftKey: (buildId: string, recordId: string) => string;
  setMessage: (message: string, tone?: MessageTone) => void;
  t: (key: string, fallback?: string) => string;
}

export function useCorpusTextReview(options: CorpusTextReviewOptions) {
  const textDraft = ref("");
  const editingText = ref(false);
  const resolveSourceOnTextSave = ref(false);
  const llmTouchupOpen = ref(false);
  const llmTouchupResult = ref<CorpusTextTouchupResult>({
    source_text: "",
    proposed_text: "",
    changes: [],
    warnings: [],
    provider: "",
    model: "",
    no_change: false,
  });
  const llmTouchupError = ref("");

  function beginTextEdit(useTouchupProposal = false) {
    if (!options.selectedRecord.value) return;
    editingText.value = true;
    if (
      useTouchupProposal &&
      options.selectedRecord.value.text_touchup_proposal?.proposed_text
    ) {
      textDraft.value = options.selectedRecord.value.text_touchup_proposal.proposed_text;
    } else if (!textDraft.value) {
      textDraft.value = String(options.selectedRecord.value.text || "");
    }
  }

  function cancelTextEdit() {
    if (!options.selectedRecord.value) return;
    editingText.value = false;
    textDraft.value = String(options.selectedRecord.value.text || "");
    try {
      localStorage.removeItem(
        options.textDraftKey(
          options.selectedBuildId.value,
          options.selectedRecord.value.record_id,
        ),
      );
    } catch {
      // Browser storage is optional.
    }
  }

  async function saveReviewedText(resolveIssues = resolveSourceOnTextSave.value) {
    if (!options.currentBuild.value || !options.selectedRecord.value) return;
    const recordId = options.selectedRecord.value.record_id;
    const viewport = options.captureReviewViewport();
    const buildId = options.currentBuild.value.build_id;
    const expectedRevision = Number(options.selectedRecord.value.record_revision || 1);
    const text = textDraft.value;
    const row: CorpusRecord = {
      ...options.selectedRecord.value,
      text,
      text_length: text.length,
      record_revision: expectedRevision + 1,
    } as CorpusRecord;

    options.selectedRecord.value = row;
    const index = options.records.value.findIndex((item) => item.record_id === recordId);
    if (index >= 0) options.records.value.splice(index, 1, row);
    editingText.value = false;
    resolveSourceOnTextSave.value = false;
    try {
      localStorage.removeItem(options.textDraftKey(options.selectedBuildId.value, recordId));
    } catch {
      // Browser storage is optional.
    }

    await options.restoreReviewViewport(viewport, { record: true });
    options.queueRecordRequest(recordId, ["text"], (rebase) =>
      corpusBuilderApi.patchText(
        buildId,
        recordId,
        text,
        rebase ? undefined : expectedRevision,
        resolveIssues,
      ),
    );
  }

  async function markTextReviewed() {
    if (!options.selectedRecord.value) return;
    textDraft.value = String(options.selectedRecord.value.text || "");
    await saveReviewedText(false);
  }

  async function saveTextFromFocus(text: string, resolve: boolean) {
    textDraft.value = text;
    resolveSourceOnTextSave.value = resolve;
    await saveReviewedText(resolve);
  }

  async function saveSourceTranscription(text: string) {
    textDraft.value = text;
    resolveSourceOnTextSave.value = false;
    await saveReviewedText(false);
    options.sourceTranscriptionOpen.value = false;
  }

  function openLlmTouchup(text: string) {
    textDraft.value = text;
    editingText.value = true;
    llmTouchupError.value = "";
    llmTouchupResult.value = {
      source_text: options.selectedRecord.value?.text_touchup_proposal?.source_text || "",
      proposed_text: options.selectedRecord.value?.text_touchup_proposal?.proposed_text || "",
      changes: options.selectedRecord.value?.text_touchup_proposal?.changes || [],
      warnings: options.selectedRecord.value?.text_touchup_proposal?.warnings || [],
      provider: options.selectedRecord.value?.text_touchup_proposal?.provider || "",
      model: options.selectedRecord.value?.text_touchup_proposal?.model || "",
      proposal_id: options.selectedRecord.value?.text_touchup_proposal?.proposal_id,
      run_id: options.selectedRecord.value?.text_touchup_proposal?.run_id,
      created_at: options.selectedRecord.value?.text_touchup_proposal?.created_at,
      status: options.selectedRecord.value?.text_touchup_proposal?.status,
      no_change: false,
    };
    options.llmActionProviderId.value =
      options.llmActionProviderId.value ||
      options.selectedProviderId.value ||
      options.providerProfiles.value[0]?.id ||
      "";
    options.llmActionModel.value = String(
      options.providerProfiles.value.find(
        (profile) => profile.id === options.llmActionProviderId.value,
      )?.model || "",
    );
    llmTouchupOpen.value = true;
  }

  async function runLlmTouchup(
    instructions = "",
    profileId = options.llmActionProviderId.value,
    model = options.llmActionModel.value,
  ) {
    if (!options.currentBuild.value || !options.selectedRecord.value) return;
    options.busy.value = "text-touchup";
    llmTouchupError.value = "";
    llmTouchupOpen.value = true;
    try {
      const actionPayload = options.directProfilePayloadWithModel(profileId, model) || {
        provider_profile_id: profileId,
        model: model || undefined,
      };
      const result = await corpusBuilderApi.touchupText(
        options.currentBuild.value.build_id,
        options.selectedRecord.value.record_id,
        {
          ...actionPayload,
          instructions,
          text: textDraft.value || options.selectedRecord.value.text,
        },
      );
      llmTouchupResult.value = {
        source_text: result.source_text,
        proposed_text: result.proposed_text,
        changes: result.changes || [],
        warnings: result.warnings || [],
        provider: result.provider || "",
        model: result.model || "",
        proposal_id: result.proposal_id,
        run_id: result.run_id,
        created_at: result.created_at,
        status: "pending_review",
        no_change: Boolean(result.no_change),
      };
      options.selectedRecord.value = {
        ...options.selectedRecord.value,
        text_touchup_proposal: {
          status: "pending_review",
          proposal_id: result.proposal_id,
          run_id: result.run_id,
          source_text: result.source_text,
          proposed_text: result.proposed_text,
          changes: result.changes || [],
          warnings: result.warnings || [],
          provider: result.provider || "",
          model: result.model || "",
          created_at: result.created_at,
        },
      };
    } catch (exc) {
      llmTouchupError.value = exc instanceof Error ? exc.message : String(exc);
      options.setMessage(llmTouchupError.value, "error");
    } finally {
      options.busy.value = "";
    }
  }

  async function dismissLlmTouchup() {
    if (
      !options.currentBuild.value ||
      !options.selectedRecord.value ||
      !llmTouchupResult.value.proposal_id
    ) {
      return;
    }
    options.busy.value = "text-touchup-dismiss";
    try {
      const updated = await corpusBuilderApi.setTouchupProposalStatus(
        options.currentBuild.value.build_id,
        options.selectedRecord.value.record_id,
        "dismissed",
      );
      options.selectedRecord.value = updated;
      const index = options.records.value.findIndex(
        (row) => row.record_id === updated.record_id,
      );
      if (index >= 0) options.records.value.splice(index, 1, updated);
      llmTouchupOpen.value = false;
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  function applyLlmTouchup(text: string) {
    textDraft.value = text;
    editingText.value = true;
    llmTouchupOpen.value = false;
    options.setMessage(options.t("pdf_corpus.llm_touchup_applied"));
  }

  return {
    textDraft,
    editingText,
    resolveSourceOnTextSave,
    llmTouchupOpen,
    llmTouchupResult,
    llmTouchupError,
    beginTextEdit,
    cancelTextEdit,
    saveReviewedText,
    markTextReviewed,
    saveTextFromFocus,
    saveSourceTranscription,
    openLlmTouchup,
    runLlmTouchup,
    dismissLlmTouchup,
    applyLlmTouchup,
  };
}
