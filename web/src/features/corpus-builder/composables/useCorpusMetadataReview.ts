/* Copyright 2026 Aaron John Schlosser, PhD. */
import { computed, ref, type Ref } from "vue";
import {
  corpusBuilderApi,
  type CorpusBuild,
  type CorpusRecord,
  type SourceBlock,
} from "../../../api/corpus";
import type { ProviderProfile } from "../../../api/system";
import type { ReviewQueue } from "../../../types/corpus";
import type { ReviewViewport } from "./useCorpusReviewWorkspace";
import { reviewableMetadataFieldNames } from "../domain/recordMetadata";
import { isUsableMetadataSuggestion } from "../../../domain/metadataValues";

type MessageTone = "error" | "notice";
type I18nValues = Record<string, string | number>;

interface EditorialMemory {
  conventions: Record<string, { value: unknown; confirmed_records: number }>;
  examples: Record<
    string,
    Array<{ record_id: string; value: unknown; similarity: number; excerpt: string }>
  >;
  reset_at?: string | null;
  convention_count: number;
  example_count: number;
}

interface CorpusMetadataReviewOptions {
  currentBuild: Ref<CorpusBuild | null>;
  selectedRecord: Ref<CorpusRecord | null>;
  selectedRecordId: Ref<string>;
  records: Ref<CorpusRecord[]>;
  busy: Ref<string>;
  selectedEvidenceField: Ref<string>;
  reviewInspectorTab: Ref<"metadata" | "evidence" | "source">;
  selectedPdfPage: Ref<number>;
  sourceBlocks: Ref<SourceBlock[]>;
  selectedReviewIds: Ref<Set<string>>;
  reviewQueue: Ref<ReviewQueue>;
  recordQuery: Ref<string>;
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
  applyAuthoritativeRecord: (record: CorpusRecord, build?: CorpusBuild | null) => void;
  syncBuildInRail: (build: CorpusBuild) => void;
  registerBuildOperation: (build: CorpusBuild) => void;
  startPolling: () => void;
  refreshBuild: () => Promise<void>;
  refreshRecords: (reset?: boolean, preferredId?: string) => Promise<void>;
  recordMetadata: (record: CorpusRecord) => Record<string, unknown>;
  metadataDraftKey: (buildId: string, recordId: string) => string;
  setMessage: (message: string, tone?: MessageTone) => void;
  t: (key: string, fallback?: string) => string;
  tf: (key: string, fallbackOrValues?: string | I18nValues, values?: I18nValues) => string;
}

export function useCorpusMetadataReview(options: CorpusMetadataReviewOptions) {
  const metadataSavingField = ref("");
  const metadataSavedField = ref("");
  const metadataDraft = ref("{}");
  const bulkMetadataOpen = ref(false);
  const metadataEnrichmentOpen = ref(false);
  const metadataEditorDirty = ref(false);
  const editorialMemoryOpen = ref(false);
  const editorialMemory = ref<EditorialMemory>({
    conventions: {},
    examples: {},
    convention_count: 0,
    example_count: 0,
  });
  const metadataRerunFamily = ref("all");
  const metadataHumanValues = ref<Record<string, Set<string>>>({});
  const metadataObservedValues = ref<Record<string, string[]>>({});

  const metadataKnownValues = computed<Record<string, string[]>>(() => {
    const out: Record<string, Set<string>> = {};
    for (const [field, values] of Object.entries(metadataObservedValues.value)) {
      for (const value of values) (out[field] ??= new Set()).add(value);
    }
    for (const row of options.records.value) {
      const source = row as unknown as Record<string, unknown>;
      const allowed = new Set(
        reviewableMetadataFieldNames(source, options.currentBuild.value?.schema || null),
      );
      for (const field of allowed) {
        const value = source[field];
        const values = Array.isArray(value) ? value : [value];
        for (const item of values) {
          if (!isUsableMetadataSuggestion(item)) continue;
          (out[field] ??= new Set()).add(item.trim());
        }
      }
    }
    for (const [field, values] of Object.entries(metadataHumanValues.value)) {
      for (const value of values) (out[field] ??= new Set()).add(value);
    }
    return Object.fromEntries(
      Object.entries(out).map(([field, values]) => [
        field,
        [...values].sort((a, b) => a.localeCompare(b)),
      ]),
    );
  });

  function rememberMetadataValues(field: string, value: unknown) {
    const values = Array.isArray(value) ? value : [value];
    for (const item of values) {
      if (!isUsableMetadataSuggestion(item)) continue;
      (metadataHumanValues.value[field] ??= new Set()).add(item.trim());
    }
  }

  function applyOptimisticMetadata(changes: Record<string, unknown>) {
    if (!options.currentBuild.value || !options.selectedRecord.value) return null;
    const buildId = options.currentBuild.value.build_id;
    const recordId = options.selectedRecord.value.record_id;
    const expectedRevision = Number(options.selectedRecord.value.record_revision || 1);
    const row: CorpusRecord = {
      ...options.selectedRecord.value,
      ...changes,
      record_revision: expectedRevision + 1,
    } as CorpusRecord;

    options.selectedRecord.value = row;
    metadataDraft.value = JSON.stringify(options.recordMetadata(row), null, 2);
    const index = options.records.value.findIndex((item) => item.record_id === recordId);
    if (index >= 0) options.records.value.splice(index, 1, row);
    metadataEditorDirty.value = false;
    try {
      localStorage.removeItem(options.metadataDraftKey(buildId, recordId));
    } catch {
      // Browser storage is optional.
    }
    return { buildId, recordId, expectedRevision };
  }

  async function saveMetadata() {
    if (!options.currentBuild.value || !options.selectedRecord.value) return;
    const viewport = options.captureReviewViewport();
    let changes: Record<string, unknown>;
    try {
      changes = JSON.parse(metadataDraft.value);
    } catch {
      options.setMessage(options.t("pdf_corpus.metadata_invalid"), "error");
      return;
    }
    const context = applyOptimisticMetadata(changes);
    if (!context) return;
    await options.restoreReviewViewport(viewport);
    options.queueRecordRequest(context.recordId, Object.keys(changes), (rebase) =>
      corpusBuilderApi.patchMetadata(
        context.buildId,
        context.recordId,
        changes,
        rebase ? undefined : context.expectedRevision,
      ),
    );
  }

  async function persistEvidence(field: string, blockIds: string[]) {
    if (!options.currentBuild.value || !options.selectedRecord.value) return;
    const viewport = options.captureReviewViewport();
    const existing = options.selectedRecord.value.metadata_evidence?.[field];
    const buildId = options.currentBuild.value.build_id;
    const recordId = options.selectedRecord.value.record_id;
    const expectedRevision = Number(options.selectedRecord.value.record_revision || 1);
    const evidence = {
      ...(options.selectedRecord.value.metadata_evidence || {}),
      [field]: {
        ...(existing || {}),
        block_ids: blockIds,
        confidence: existing?.confidence ?? 1,
        reason: existing?.reason || options.t("pdf_corpus.human_evidence_reason"),
      },
    };
    const row: CorpusRecord = {
      ...options.selectedRecord.value,
      metadata_evidence: evidence,
      record_revision: expectedRevision + 1,
    } as CorpusRecord;

    options.selectedRecord.value = row;
    metadataDraft.value = JSON.stringify(options.recordMetadata(row), null, 2);
    const index = options.records.value.findIndex((item) => item.record_id === recordId);
    if (index >= 0) options.records.value.splice(index, 1, row);
    await options.restoreReviewViewport(viewport);
    options.queueRecordRequest(recordId, [field], (rebase) =>
      corpusBuilderApi.patchEvidence(
        buildId,
        recordId,
        field,
        blockIds,
        existing?.confidence ?? 1,
        existing?.reason || options.t("pdf_corpus.human_evidence_reason"),
        rebase ? undefined : expectedRevision,
      ),
    );
  }

  async function assignEvidenceBlock(field: string, blockId: string) {
    if (!options.currentBuild.value || !options.selectedRecord.value || !field || !blockId) return;
    options.selectedEvidenceField.value = field;
    const existing = options.selectedRecord.value.metadata_evidence?.[field];
    const ids = new Set((existing?.block_ids || []).map(String));
    if (ids.has(blockId)) return;
    ids.add(blockId);
    await persistEvidence(field, Array.from(ids));
  }

  async function toggleEvidenceBlock(blockId: string) {
    if (
      !options.currentBuild.value ||
      !options.selectedRecord.value ||
      !options.selectedEvidenceField.value
    ) {
      return;
    }
    const field = options.selectedEvidenceField.value;
    const existing = options.selectedRecord.value.metadata_evidence?.[field];
    const ids = new Set((existing?.block_ids || []).map(String));
    if (ids.has(blockId)) ids.delete(blockId);
    else ids.add(blockId);
    await persistEvidence(field, Array.from(ids));
  }

  async function requeueCurrentRecord() {
    if (!options.currentBuild.value || !options.selectedRecord.value) return;
    options.busy.value = "record";
    try {
      const availableProfileIds = new Set(
        options.providerProfiles.value.map((profile) => profile.id),
      );
      const profileId =
        [options.llmActionProviderId.value, options.selectedProviderId.value].find(
          (id) => Boolean(id) && availableProfileIds.has(id),
        ) ||
        options.providerProfiles.value[0]?.id ||
        "";
      if (!profileId) throw new Error(options.t("pdf_corpus.no_provider_profile"));
      const actionPayload = options.directProfilePayloadWithModel(
        profileId,
        options.llmActionModel.value,
      ) || {
        provider_profile_id: profileId,
        model: options.llmActionModel.value || undefined,
      };
      await corpusBuilderApi.requeueMetadata(
        options.currentBuild.value.build_id,
        options.selectedRecord.value.record_id,
        actionPayload,
      );
      await options.refreshBuild();
      options.setMessage(options.t("pdf_corpus.requeue_requested"));
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  async function resolveMetadataField(field: string, value: unknown) {
    if (!options.currentBuild.value || !options.selectedRecord.value) return;
    rememberMetadataValues(field, value);
    const viewport = options.captureReviewViewport();
    metadataSavingField.value = field;
    metadataSavedField.value = "";
    const context = applyOptimisticMetadata({ [field]: value });
    if (!context) {
      metadataSavingField.value = "";
      return;
    }
    await options.restoreReviewViewport(viewport, { inspector: true });
    options.queueRecordRequest(
      context.recordId,
      [field],
      async (rebase) => {
        const result = await corpusBuilderApi.metadataDecision(
          context.buildId,
          context.recordId,
          field,
          value,
          rebase ? undefined : context.expectedRevision,
        );
        options.applyAuthoritativeRecord(result.record, result.build);
        if (options.selectedRecordId.value === context.recordId) {
          metadataSavingField.value = "";
          metadataSavedField.value = field;
        }
        return result;
      },
      () => {
        if (options.selectedRecordId.value === context.recordId) {
          metadataSavingField.value = "";
        }
      },
    );
  }

  async function resolveMetadataSuggestions(changes: Record<string, unknown>) {
    if (
      !options.currentBuild.value ||
      !options.selectedRecord.value ||
      !Object.keys(changes).length
    ) {
      return;
    }
    for (const [field, value] of Object.entries(changes)) {
      rememberMetadataValues(field, value);
    }
    const viewport = options.captureReviewViewport();
    const context = applyOptimisticMetadata(changes);
    if (!context) return;
    await options.restoreReviewViewport(viewport, { inspector: true });
    options.queueRecordRequest(context.recordId, Object.keys(changes), async (rebase) => {
      const result = await corpusBuilderApi.metadataDecisionBatch(
        context.buildId,
        context.recordId,
        changes,
        rebase ? undefined : context.expectedRevision,
      );
      options.applyAuthoritativeRecord(result.record, result.build);
      return result;
    });
  }

  async function resolveMetadataNoValue(field: string) {
    if (!options.currentBuild.value || !options.selectedRecord.value) return;
    const viewport = options.captureReviewViewport();
    metadataSavingField.value = field;
    metadataSavedField.value = "";
    const context = applyOptimisticMetadata({ [field]: null });
    if (!context) {
      metadataSavingField.value = "";
      return;
    }
    await options.restoreReviewViewport(viewport, { inspector: true });
    options.queueRecordRequest(
      context.recordId,
      [field],
      async (rebase) => {
        const result = await corpusBuilderApi.metadataDecision(
          context.buildId,
          context.recordId,
          field,
          null,
          rebase ? undefined : context.expectedRevision,
          true,
        );
        options.applyAuthoritativeRecord(result.record, result.build);
        if (options.selectedRecordId.value === context.recordId) {
          metadataSavingField.value = "";
          metadataSavedField.value = field;
        }
        return result;
      },
      () => {
        if (options.selectedRecordId.value === context.recordId) {
          metadataSavingField.value = "";
        }
      },
    );
  }

  async function clearMetadataSuggestionCache() {
    if (
      !window.confirm(
        options.t(
          "pdf_corpus.clear_metadata_cache_confirm",
          "Clear remembered metadata suggestions? This will not change reviewed records or their history.",
        ),
      )
    ) {
      return;
    }
    options.busy.value = "metadata-cache";
    try {
      const result = await corpusBuilderApi.clearAllMetadataCache();
      options.setMessage(
        options.tf(
          "pdf_corpus.metadata_cache_cleared",
          "Cleared {count} remembered suggestion(s).",
          { count: result.cleared },
        ),
      );
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  async function runMetadataEnrichment(payload: {
    providerProfileId: string;
    model: string;
    families: string[];
    scope: string;
    passes: number;
    recordIds: string[];
  }) {
    if (!options.currentBuild.value) return;
    options.busy.value = "metadata-enrichment";
    try {
      const actionPayload = options.directProfilePayloadWithModel(
        payload.providerProfileId,
        payload.model,
      ) || {
        provider_profile_id: payload.providerProfileId,
        model: payload.model || undefined,
      };
      options.currentBuild.value = await corpusBuilderApi.rerunMetadataEnrichment(
        options.currentBuild.value.build_id,
        {
          ...actionPayload,
          families: payload.families,
          scope: payload.scope,
          passes: payload.passes,
          record_ids: payload.recordIds,
        },
      );
      metadataEnrichmentOpen.value = false;
      options.syncBuildInRail(options.currentBuild.value);
      options.registerBuildOperation(options.currentBuild.value);
      options.startPolling();
      options.setMessage(options.t("pdf_corpus.metadata_enrichment_started"));
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  async function openEditorialMemory() {
    if (!options.currentBuild.value) return;
    options.busy.value = "editorial-memory";
    try {
      editorialMemory.value = await corpusBuilderApi.editorialMemory(
        options.currentBuild.value.build_id,
      );
      editorialMemoryOpen.value = true;
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  async function resetEditorialMemory() {
    if (!options.currentBuild.value) return;
    options.busy.value = "editorial-memory";
    try {
      editorialMemory.value = await corpusBuilderApi.resetEditorialMemory(
        options.currentBuild.value.build_id,
      );
      options.setMessage(options.t("pdf_corpus.editorial_memory_reset_done"));
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  function handleMetadataDirty(value: boolean) {
    metadataEditorDirty.value = value;
  }

  function showMetadataSource(field: string) {
    options.selectedEvidenceField.value = field;
    options.reviewInspectorTab.value = "source";
    const ids = options.selectedRecord.value?.metadata_evidence?.[field]?.block_ids || [];
    const first = options.sourceBlocks.value.find((block) => ids.includes(block.block_id));
    if (first) {
      options.selectedPdfPage.value = Number(first.page || options.selectedPdfPage.value);
    }
  }

  async function rerunMetadata() {
    if (!options.currentBuild.value || !options.selectedRecord.value) return;
    const viewport = options.captureReviewViewport();
    options.busy.value = "record";
    try {
      const profileId = options.llmActionProviderId.value || options.selectedProviderId.value;
      const payload = {
        ...(options.directProfilePayloadWithModel(profileId, options.llmActionModel.value) || {
          provider_profile_id: profileId,
          model: options.llmActionModel.value || undefined,
        }),
      } as Record<string, unknown>;
      if (metadataRerunFamily.value !== "all") {
        payload.families = [metadataRerunFamily.value];
      }
      const row = await corpusBuilderApi.rerunMetadata(
        options.currentBuild.value.build_id,
        options.selectedRecord.value.record_id,
        payload,
      );
      options.selectedRecord.value = row;
      metadataDraft.value = JSON.stringify(options.recordMetadata(row), null, 2);
      await options.refreshBuild();
      await options.refreshRecords(false, row.record_id);
      await options.restoreReviewViewport(viewport);
      options.reviewInspectorTab.value = "metadata";
      options.setMessage(
        metadataRerunFamily.value === "all"
          ? options.t("pdf_corpus.metadata_rerun")
          : options.tf("pdf_corpus.metadata_family_rerun", {
              family: options.t(
                `pdf_corpus.metadata_family.${metadataRerunFamily.value}`,
                metadataRerunFamily.value,
              ),
            }),
      );
    } catch (exc) {
      await options.restoreReviewViewport(viewport);
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  async function applyBulkMetadata(payload: {
    changes: Record<string, unknown>;
    applyToAll: boolean;
  }) {
    if (!options.currentBuild.value) return;
    options.busy.value = "bulk-metadata";
    try {
      const result = await corpusBuilderApi.bulkMetadata(
        options.currentBuild.value.build_id,
        payload.changes,
        {
          recordIds: payload.applyToAll ? [] : Array.from(options.selectedReviewIds.value),
          applyToAll: payload.applyToAll,
          reviewQueue: options.reviewQueue.value,
          query: options.recordQuery.value,
        },
      );
      bulkMetadataOpen.value = false;
      await options.refreshBuild();
      await options.refreshRecords(false, options.selectedRecordId.value);
      options.setMessage(
        options.tf("pdf_corpus.bulk_metadata_applied", {
          count: result.changed,
        }),
      );
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  return {
    metadataSavingField,
    metadataSavedField,
    metadataDraft,
    bulkMetadataOpen,
    metadataEnrichmentOpen,
    metadataEditorDirty,
    editorialMemoryOpen,
    editorialMemory,
    metadataRerunFamily,
    metadataHumanValues,
    metadataObservedValues,
    metadataKnownValues,
    rememberMetadataValues,
    saveMetadata,
    assignEvidenceBlock,
    toggleEvidenceBlock,
    requeueCurrentRecord,
    resolveMetadataField,
    resolveMetadataSuggestions,
    resolveMetadataNoValue,
    clearMetadataSuggestionCache,
    runMetadataEnrichment,
    openEditorialMemory,
    resetEditorialMemory,
    handleMetadataDirty,
    showMetadataSource,
    rerunMetadata,
    applyBulkMetadata,
  };
}
